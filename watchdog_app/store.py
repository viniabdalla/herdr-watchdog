"""Watchdog-owned state and locks; no writes to Left Undone's folder."""
from contextlib import contextmanager
from dataclasses import asdict
import fcntl
import json
import os
from pathlib import Path
import time


def state_root():
    return Path(os.environ.get('WATCHDOG_STATE_DIR', str(
        Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) /
        'herdr-watchdog')))


def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_suffix('.tmp.' + str(os.getpid()))
    try:
        temporary.write_text(json.dumps(value, indent=2))
        temporary.chmod(0o600)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


class Store:
    def __init__(self, root=None):
        self.root = Path(root) if root is not None else state_root()

    @contextmanager
    def lock(self, binding):
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (self.root / (binding.key + '.lock')).open('a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            yield

    def load(self, binding, repo):
        file = self.root / (binding.key + '.json')
        if file.exists():
            state = json.loads(file.read_text())
            if state['repo'] != str(repo.resolve()):
                raise RuntimeError('This conversation already watches another project; use that project folder')
            if any(state['binding'][k] != getattr(binding, k) for k in ('kind', 'session', 'account')):
                raise RuntimeError('Stored conversation identity differs; state was not reused')
            state['binding'] = asdict(binding)
            return state
        state = {'version': 1, 'repo': str(repo.resolve()), 'binding': asdict(binding),
                 'panes': {}, 'yazi_client_id': str(time.time_ns()), 'layout': self.preference()}
        legacy = self.root / 'preview.json'
        if legacy.exists():
            old = json.loads(legacy.read_text())
            conversation = old.get('conversation', {})
            if (old.get('repo') == state['repo'] and conversation.get('pane_id') == binding.pane
                    and conversation.get('terminal_id') == binding.terminal):
                state['panes'] = old.get('panes', {})
                state['yazi_client_id'] = old.get('yazi_client_id', state['yazi_client_id'])
                state['adopted_preview'] = True
        return state

    def save(self, binding, state):
        atomic(self.root / (binding.key + '.json'), state)

    def preference(self):
        try:
            value = json.loads((self.root / 'preferences.json').read_text())['layout']
            return value if type(value) is int and value in (1, 2, 3, 4) else 2
        except (OSError, ValueError, KeyError, TypeError):
            return 2

    def remember(self, preset):
        if preset not in (1, 2, 3, 4):
            raise ValueError('Unknown layout')
        atomic(self.root / 'preferences.json', {'layout': preset})
