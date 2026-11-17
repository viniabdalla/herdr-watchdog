"""Snapshot-based TODO.md edits. No task is changed from a stale selection."""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
import ctypes
import fcntl
import hashlib
import os
from pathlib import Path
import re
import stat
import tempfile
import unicodedata
import uuid

from .store import state_root

SECTIONS = ('In progress', 'Next', 'Blocked', 'Done')
ALIASES = {'in progress': 'In progress', 'em andamento': 'In progress',
           'next': 'Next', 'proximo': 'Next', 'blocked': 'Blocked',
           'bloqueado': 'Blocked', 'done': 'Done', 'feito': 'Done'}
TASK = re.compile(r'^(\s*[-*] )\[([ xX])\] (.+?)\s*$')


def plain(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text)
                   if not unicodedata.combining(c)).lower()


@dataclass(frozen=True)
class Task:
    id: str
    section: str
    text: str
    done: bool
    start: int
    end: int
    title: str


@dataclass(frozen=True)
class Snapshot:
    repo: Path
    raw: bytes
    digest: str
    tasks: tuple

    @classmethod
    def read(cls, repo):
        repo = Path(repo).resolve()
        path = repo / 'TODO.md'
        if path.is_symlink():
            raise RuntimeError('TODO.md is a symlink; edit the real project file instead')
        raw = path.read_bytes()
        lines = raw.decode('utf-8').splitlines(keepends=True)
        tasks = []
        section = None
        fence = None
        for index, line in enumerate(lines):
            mark = re.match(r'^\s*(`{3,}|~{3,})(.*)$', line)
            if mark:
                token = mark[1]
                if fence is None:
                    fence = token
                elif token[0] == fence[0] and len(token) >= len(fence) and not mark[2].strip():
                    fence = None
                continue
            if fence:
                continue
            if line.startswith('## '):
                section = ALIASES.get(plain(line[3:].strip()))
            match = TASK.match(line)
            if not match or not section:
                continue
            end = index + 1
            while end < len(lines) and lines[end].strip() and lines[end][0].isspace() and not TASK.match(lines[end]):
                end += 1
            text = ' '.join([match[3]] + [s.strip() for s in lines[index + 1:end]])
            key = hashlib.sha256((str(index) + '\0' + ''.join(lines[index:end])).encode()).hexdigest()
            tasks.append(Task(key, section, text, match[2].lower() == 'x' or section == 'Done',
                              index, end, match[3]))
        return cls(repo, raw, hashlib.sha256(raw).hexdigest(), tuple(tasks))

    def selected(self, ids):
        ids = set(ids)
        chosen = [task for task in self.tasks if task.id in ids]
        if len(chosen) != len(ids) or any(t.done for t in chosen) or not chosen:
            raise RuntimeError('Selection is empty, completed or no longer matches the task list')
        return chosen

    def assert_current(self):
        current = Snapshot.read(self.repo)
        if current.digest != self.digest:
            raise RuntimeError('Task list changed; review and select the tasks again')
        return current


def single_line(value, label='Task'):
    if not isinstance(value, str) or not value.strip() or len(value) > 500:
        raise RuntimeError(label + ' text is empty or too long')
    if any(not c.isprintable() for c in value):
        raise RuntimeError(label + ' must be a single line of printable text')
    return value.strip()


@contextmanager
def locked(repo, root=None):
    root = Path(root) if root is not None else state_root()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    key = hashlib.sha256(str(repo).encode()).hexdigest()
    with (root / ('todo-' + key + '.lock')).open('a') as file:
        fcntl.flock(file, fcntl.LOCK_EX)
        yield root


def exchange(source, target):
    """Swap two names atomically so a concurrent editor's version can be inspected."""
    libc = ctypes.CDLL(None, use_errno=True)
    rename = getattr(libc, 'renameat2', None)
    if rename is None:
        raise RuntimeError('Atomic TODO exchange is unavailable on this platform')
    if rename(-100, os.fsencode(source), -100, os.fsencode(target), 2):
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code))


def preserve(path, backup):
    # Keep the inode too: an editor may still have it open for writing.
    destination = backup / (uuid.uuid4().hex + '.md')
    try:
        os.replace(path, destination)
    except OSError:
        destination.write_bytes(Path(path).read_bytes())
        destination.chmod(0o600)
        # Keep the original name if moving across filesystems is unavailable.


def change(snapshot, actions, root=None):
    """Apply a confirmed set, all or nothing, preserving the original document."""
    with locked(snapshot.repo, root) as root:
        snapshot.assert_current()
        lines = snapshot.raw.decode('utf-8').splitlines(keepends=True)
        newline = '\r\n' if b'\r\n' in snapshot.raw else '\n'
        by_id = {t.id: t for t in snapshot.tasks}
        removed, inserts, touched = set(), {}, set()
        titles = {re.sub(r'^\d{4}-\d{2}-\d{2} ', '', t.title).casefold() for t in snapshot.tasks}
        for action in actions:
            kind = action['kind']
            if kind == 'add':
                text = single_line(action['text'])
                if text.casefold() in titles:
                    raise RuntimeError('Task is already recorded; closed tasks are not reopened')
                titles.add(text.casefold())
                inserts.setdefault('Next', []).append('- [ ] ' + text + newline)
                continue
            if kind not in ('done', 'blocked', 'start', 'next'):
                raise RuntimeError('Unknown task action')
            key = action['id']
            if key in touched or key not in by_id or by_id[key].done:
                raise RuntimeError('Task action conflicts with the current selection')
            touched.add(key)
            task = by_id[key]
            removed.update(range(task.start, task.end))
            title = task.title.split(' — Blocked: ', 1)[0]
            section = {'done': 'Done', 'blocked': 'Blocked', 'start': 'In progress', 'next': 'Next'}[kind]
            if kind == 'blocked':
                title += ' — Blocked: ' + single_line(action['reason'], 'Blocker')
            if kind == 'done':
                title = date.today().isoformat() + ' ' + title
            content = ('- [x] ' if kind == 'done' else '- [ ] ') + title + newline
            content += ''.join(lines[task.start + 1:task.end])
            inserts.setdefault(section, []).append(content)
        if not actions:
            return snapshot
        output = [line for index, line in enumerate(lines) if index not in removed]
        # Find real section headings, excluding fenced examples just as the reader does.
        for section, additions in inserts.items():
            fence = None
            position = None
            for index, line in enumerate(output):
                mark = re.match(r'^\s*(`{3,}|~{3,})(.*)$', line)
                if mark:
                    if fence is None:
                        fence = mark[1]
                    elif mark[1][0] == fence[0] and len(mark[1]) >= len(fence) and not mark[2].strip():
                        fence = None
                    continue
                if not fence and line.startswith('## ') and ALIASES.get(plain(line[3:].strip())) == section:
                    position = index + 1
                    break
            if position is None:
                if output and not output[-1].endswith(('\n', '\r')):
                    output[-1] += newline
                output.extend([newline, '## ' + section + newline])
                position = len(output)
            if position and not output[position - 1].endswith(('\n', '\r')):
                output[position - 1] += newline
            output[position:position] = additions
        result = ''.join(output)
        metadata = result.splitlines(keepends=True)
        if metadata and metadata[0].strip() == '---':
            for index in range(1, len(metadata)):
                if metadata[index].strip() == '---':
                    break
                if metadata[index].startswith('atualizado:'):
                    ending = '\r\n' if metadata[index].endswith('\r\n') else '\n'
                    metadata[index] = 'atualizado: ' + date.today().isoformat() + ending
            result = ''.join(metadata)
        backup = root / 'todo-backups' / hashlib.sha256(str(snapshot.repo).encode()).hexdigest()
        backup.mkdir(parents=True, exist_ok=True, mode=0o700)
        archived = backup / (snapshot.digest + '.md')
        if not archived.exists():
            archived.write_bytes(snapshot.raw)
            archived.chmod(0o600)
        path = snapshot.repo / 'TODO.md'
        mode = stat.S_IMODE(path.stat().st_mode)
        fd, temporary = tempfile.mkstemp(prefix='.watchdog-todo-', dir=snapshot.repo)
        exchanged = False
        try:
            with os.fdopen(fd, 'wb') as file:
                file.write(result.encode('utf-8'))
                file.flush()
                os.fsync(file.fileno())
            os.chmod(temporary, mode)
            snapshot.assert_current()
            exchange(temporary, path)
            exchanged = True
            displaced = Path(temporary).read_bytes()
            if displaced != snapshot.raw:
                # Restore the competing save. If another editor saves during
                # rollback, preserve that newer version and restore it instead.
                expected = result.encode('utf-8')
                for _ in range(8):
                    candidate = Path(temporary).read_bytes()
                    saved = backup / (uuid.uuid4().hex + '.md')
                    saved.write_bytes(candidate)
                    saved.chmod(0o600)
                    exchange(temporary, path)
                    displaced = Path(temporary).read_bytes()
                    if displaced == expected:
                        break
                    expected = candidate
                raise RuntimeError('Task list changed during save; competing versions preserved in ' + str(backup))
        finally:
            if exchanged and Path(temporary).exists():
                preserve(temporary, backup)
            else:
                Path(temporary).unlink(missing_ok=True)
        return Snapshot.read(snapshot.repo)
