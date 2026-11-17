"""Reuse Left Undone's identity engine without opening its database for writes."""
import importlib
import os
from pathlib import Path
import shutil
import sys
from functools import lru_cache


class ChoiceRequired(RuntimeError):
    def __init__(self, choices):
        super().__init__('Choose the conversation to watch')
        self.choices = choices


def select(candidates, *, pane=None, session=None, thread=None):
    selected = list(candidates)
    if pane:
        selected = [b for b in selected if b.pane == pane]
    identity = session or (thread if not pane else None)
    if identity:
        selected = [b for b in selected if b.session == identity]
    if not selected:
        raise RuntimeError('No verified conversation matches. Check Herdr native registration with '
                           '`left-undone list`; recover the current conversation if needed.')
    if len(selected) != 1:
        raise ChoiceRequired(selected)
    return selected[0]


@lru_cache(maxsize=1)
def engine():
    roots = []
    if os.environ.get('WATCHDOG_LEFT_UNDONE_ROOT'):
        roots.append(Path(os.environ['WATCHDOG_LEFT_UNDONE_ROOT']).expanduser())
    executable = shutil.which('left-undone')
    if executable:
        roots.extend(Path(executable).resolve().parents)
    for root in roots:
        if (root / 'left_undone/runtime.py').is_file():
            sys.path.insert(0, str(root))
            try:
                return importlib.import_module('left_undone.runtime')
            finally:
                sys.path.pop(0)
    raise RuntimeError('Left Undone identity engine is missing. Install left-undone, or set '
                       'WATCHDOG_LEFT_UNDONE_ROOT to its checkout folder.')


def lu_state():
    return Path(os.environ.get('LEFT_UNDONE_STATE_DIR', str(
        Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) /
        'left-undone-herdr')))


def discover(repo):
    runtime = engine()
    candidates, errors = runtime.candidates()
    repository = importlib.import_module('left_undone.repository')
    return repository.repository_sessions(candidates, repo, lu_state()), errors


def project_for(binding):
    engine()
    repository = importlib.import_module('left_undone.repository')
    return repository.binding_project(binding, lu_state())


def verify(binding):
    try:
        return engine().verify(binding)
    except RuntimeError as error:
        raise RuntimeError('Conversation identity changed or is unavailable. Reopen Watchdog '
                           'and select the conversation again. Left Undone detail: ' + str(error)) from error


def native_companion_alive(pane, file):
    engine()
    app = importlib.import_module('left_undone.app')
    return app.panel_process_alive(pane, file)


def companion(binding, herdr):
    """Find an already opened panel for this exact binding. Never open LU state."""
    import json
    try:
        root = lu_state()
        data = json.loads((root / (binding.key + '.binding.json')).read_text())
        if any(data.get(k) != getattr(binding, k) for k in
               ('kind', 'session', 'account', 'pane', 'terminal', 'pid', 'started')):
            return None
        mapping = json.loads((root / (binding.key + '.pane.json')).read_text())
        live = herdr.call('pane', 'get', mapping['pane'])['pane']
        if (live['terminal_id'] == mapping['terminal'] and
                native_companion_alive(live['pane_id'], root / (binding.key + '.binding.json'))):
            return live
    except (OSError, ValueError, KeyError, RuntimeError):
        pass
    return None
