"""Explicit task routing through the same verified native binding engine."""
from contextlib import contextmanager
from dataclasses import asdict
import json
from pathlib import Path

from . import bindings
from .todo import locked
from .store import correlated


class Busy(RuntimeError):
    def __init__(self, can_queue):
        super().__init__('The conversation is working. Queue explicitly or wait until it is idle.')
        self.can_queue = can_queue


class Session:
    def __init__(self, file, repo, *, follow=False, allow_unavailable=False):
        self.file = Path(file) if file else None
        self.repo = Path(repo).resolve()
        self.binding = None
        self.runtime = None
        if self.file:
            data = json.loads(self.file.read_text())
            if Path(data['repo']).resolve() != self.repo:
                raise RuntimeError('Binding belongs to another project')
            self.runtime = bindings.engine()
            self.binding = self.runtime.Binding(**data['binding'])
            try:
                self.verify()
            except RuntimeError as unavailable:
                if not follow:
                    raise
                from .leader_link import follow as follow_leader
                try:
                    successor = follow_leader(self)
                    self.file, self.binding, self.runtime = successor.file, successor.binding, successor.runtime
                except RuntimeError:
                    if not allow_unavailable:
                        raise unavailable

    @property
    def label(self):
        if not self.binding:
            return 'Unbound · open this panel with watchdog'
        return f'{self.binding.kind} · {self.binding.pane} · {self.binding.session[:8]}'

    def verify(self):
        if self.binding is None:
            raise RuntimeError('No conversation binding. Open this panel with watchdog first.')
        data = json.loads(self.file.read_text())
        if data.get('ownership') in ('released', 'transferring'):
            raise RuntimeError('Panel ownership was released; follow the verified successor in Tasks')
        if Path(data['repo']).resolve() != self.repo:
            raise RuntimeError('Conversation binding changed; reopen Tasks before sending or reviewing')
        if data.get('binding') != asdict(self.binding):
            stored = self.runtime.Binding(**data['binding'])
            same = lambda b: (b.kind, b.account, b.session)
            if same(stored) != same(self.binding):
                raise RuntimeError('Conversation binding changed; reopen Tasks before sending or reviewing')
            self.binding = stored  # Same conversation reopened in another pane.
        try:
            live = self.runtime.verify(self.binding)
        except RuntimeError as error:
            if not self.reattach():
                raise RuntimeError('Conversation identity is unavailable: the watched conversation is closed or replaced. '
                                   'Reopen it (codex resume ' + self.binding.session + ') in this project and Watchdog follows it.') from error
            live = self.runtime.verify(self.binding)
        project = bindings.project_for(self.binding)
        if project is None or Path(project).resolve() != self.repo:
            raise RuntimeError('Conversation project association changed; reopen Watchdog')
        return live

    def reattach(self):
        """Refresh the same conversation inside the original pane and terminal."""
        from .store import Store, atomic
        if (Path('/proc') / str(self.binding.pid)).exists():
            return False  # The original process still runs: a different pane is not a reopen.
        try:
            candidates, _ = bindings.discover(self.repo)
        except Exception:
            return False
        same = [b for b in candidates if (b.kind, b.account, b.session, b.pane, b.terminal) ==
                (self.binding.kind, self.binding.account, self.binding.session, self.binding.pane, self.binding.terminal)]
        if len(same) != 1 or not isinstance(getattr(same[0], 'key', None), str):
            return False
        with Store(self.file.parent).lock(same[0]):
            data = json.loads(self.file.read_text())
            if data.get('ownership') in ('released', 'transferring') or data.get('binding') != asdict(self.binding):
                return False
            data.setdefault('reopened', []).append(data['binding'])
            data['reopened'] = data['reopened'][-5:]
            data['binding'] = asdict(same[0])
            atomic(self.file, data)
        self.binding = same[0]
        return True

    @classmethod
    def for_panel(cls, file, repo, *, allow_unavailable=False):
        """Follow only correlated Watchdog redirects; the final identity is live verified."""
        current = Path(file)
        for _ in range(16):
            data = json.loads(current.read_text())
            if Path(data['repo']).resolve() != Path(repo).resolve():
                raise RuntimeError('Panel redirect belongs to another project')
            if data.get('ownership') != 'released':
                return cls(current, repo, follow=True, allow_unavailable=allow_unavailable)
            from .relink_confirmation import blocked_file
            if blocked_file(current, transfer=data.get('outgoing_transfer_operation', data.get('transfer_operation'))):
                if allow_unavailable:
                    return cls(current, repo, follow=True, allow_unavailable=True)
                raise RuntimeError('Sessão não confirmada; use Religar')
            target = Path(data['successor_binding_file'])
            if target.is_symlink() or target.parent.resolve() != current.parent.resolve():
                raise RuntimeError('Successor binding must stay in Watchdog state')
            value = json.loads(target.read_text())
            if not correlated(data, value):
                raise RuntimeError('Successor panel transfer correlation changed')
            current = target
        raise RuntimeError('Panel redirect chain is cyclic or too long')

    def successor_file(self):
        """UI-only explicit redirect. Existing dispatch jobs never retarget silently."""
        if not self.file:
            return None
        data = json.loads(self.file.read_text())
        target = data.get('successor_binding_file')
        if data.get('ownership') != 'released' or not target:
            return None
        from .relink_confirmation import blocked_file
        if blocked_file(self.file, transfer=data.get('outgoing_transfer_operation', data.get('transfer_operation'))):
            return None
        path = Path(target)
        if path.is_symlink() or path.parent.resolve() != self.file.parent.resolve():
            raise RuntimeError('Successor binding must stay in Watchdog state')
        value = json.loads(path.read_text())
        if (not correlated(data, value) or
                (data['binding'] != asdict(self.binding) and asdict(self.binding) not in data.get('reopened', []))):
            raise RuntimeError('Successor panel transfer correlation changed')
        return Session.for_panel(path, self.repo).file

    @contextmanager
    def routing(self):
        """Serialize new coordination/task sends against a project leader transfer."""
        from .clean_sessions import SETTLED, lease, operations
        from .store import Store
        if not self.file:
            self.verify()
        store = Store(self.file.parent)
        with lease(store, self.repo):
            for operation in operations(store, self.repo):
                if operation['state'] not in SETTLED:
                    raise RuntimeError('Clean sessions '+operation['state']+'; press c in Tasks to retry or close it before sending new work')
            yield

    def dispatch(self, snapshot, ids, queued=False):
        with self.routing(), locked(snapshot.repo):
            snapshot.assert_current()
            tasks = snapshot.selected(ids)
            live = self.verify()
            if self.binding.kind != 'codex':
                raise RuntimeError('Claude task delivery needs a thread-addressed transport; sending is unavailable')
            if not queued and live.get('agent_status') == 'working':
                raise Busy(True)
            if live.get('agent_status') not in ('working', 'idle', 'done'):
                raise RuntimeError('Conversation is not ready to receive tasks')
            message = (f'Please work on these project tasks for {self.repo.name} ({self.repo}):\n\n' +
                       '\n'.join('- ' + task.text for task in tasks) +
                       '\n\nReport what is completed and any concrete blockers. '
                       'Sending this request does not mark the tasks complete.')
            try:
                # Native queue targets the full thread UUID in its own account.
                # A pane prompt could switch sessions after verification.
                return self.runtime.queue(self.binding, message)
            except RuntimeError as error:
                raise RuntimeError('Delivery was not confirmed. Check the Codex queue before retrying; '
                                   'nothing was resent automatically.') from error
