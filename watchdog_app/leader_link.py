"""Verified leader transitions owned by Watchdog, without modifying Left Undone."""
from pathlib import Path
import uuid

from . import bindings
from .herdr import Herdr
from .store import Store


def choices(session):
    if not session.binding:
        raise RuntimeError('No conversation binding. Open this panel with watchdog first.')
    candidates, _ = bindings.discover(session.repo)
    result = []
    for candidate in candidates:
        if candidate.workspace != session.binding.workspace:
            continue
        try:
            session.runtime.verify(candidate)
            if Path(bindings.project_for(candidate)).resolve() == session.repo:
                result.append(candidate)
        except (RuntimeError, OSError, ValueError, TypeError):
            continue
    return result


def connect(session, candidate):
    """Explicit choice may change panes; revalidate the entire identity at selection."""
    from .actions import Session
    from .relink import guard
    guard(session.file)
    if candidate not in choices(session):
        raise RuntimeError('O líder mudou; confira novamente a lista de Religar')
    with session.routing():
        session.runtime.verify(candidate)
        api = Herdr()
        api.checked({'pane_id':candidate.pane, 'terminal_id':candidate.terminal})
        if candidate == session.binding:
            return session
        target = Store(session.file.parent).transfer(session.file, session.binding, candidate,
                                                    session.repo, str(uuid.uuid4()), api=api)
    return Session(target, session.repo)


def follow(session):
    """Follow a new session only inside the same verified pane and terminal."""
    old = session.binding
    try:
        session.runtime.verify(old)
    except RuntimeError:
        pass
    else:
        session.verify()  # Ownership/project failures never authorize a new leader.
        return session
    candidates = choices(session)
    # A predecessor still advertised elsewhere cannot be silently superseded.
    if any((b.kind, b.account, b.session) == (old.kind, old.account, old.session)
           for b in candidates):
        raise RuntimeError('Conversation identity is unavailable; use Religar')
    same = [b for b in candidates if b.pane == old.pane and b.terminal == old.terminal]
    if len(same) != 1:
        raise RuntimeError('Conversation identity is unavailable; use Religar')
    new = same[0]
    # /clear retains the process. A distinct live predecessor requires a choice.
    same_process = (new.kind, new.account, new.pid, new.started) == (old.kind, old.account, old.pid, old.started)
    if not same_process and (Path('/proc') / str(old.pid)).exists():
        raise RuntimeError('Conversation identity is unavailable; old process is still alive. Use Religar')
    return connect(session, new)
