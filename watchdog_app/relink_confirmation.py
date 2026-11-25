"""Manual Codex identity proof; only Watchdog state is written here."""
from dataclasses import asdict
import importlib
import json
from pathlib import Path
import shlex
import sys
import time
import uuid

from watchdog_app import bindings
from watchdog_app.store import atomic
from watchdog_app.todo import locked


def path_for(file):
    return Path(file).with_suffix('.relink.json')


def required(session, candidate):
    old = session.binding
    return (old.kind == candidate.kind == 'codex' and
            (old.pane, old.session) == (candidate.pane, candidate.session))


def blocked(session):
    if not session.file:
        return False
    path = path_for(session.file)
    if not path.exists():
        return False
    attempt = json.loads(path.read_text())
    return (attempt['state'] in ('pending', 'ready') or
            (attempt['state'] != 'confirmed' and attempt.get('helper_started', False)))


def begin(session, candidate):
    from watchdog_app.leader_link import choices
    if candidate not in choices(session):
        raise RuntimeError('O líder mudou; confira novamente a lista de Religar')
    path = path_for(session.file)
    attempt = dict(id=uuid.uuid4().hex, marker='LU-' + uuid.uuid4().hex,
                   state='pending', created=time.time(), repo=str(session.repo),
                   binding_file=str(session.file.resolve()), target=asdict(candidate))
    with locked(path, root=path.parent):
        atomic(path, attempt)
    return attempt


def instruction(attempt):
    # Absolute entry point works even when the conversation has another cwd.
    launcher = Path(__file__).resolve().parents[1] / 'watchdog'
    command = shlex.join([str(launcher), 'confirm-session', attempt['binding_file'], attempt['id']])
    return ('Publique em comentário apenas ' + attempt['marker'] +
            ' e depois execute, nesta conversa e com acesso completo: ' + command +
            '. Não altere CODEX_THREAD_ID nem informe um UUID manualmente.')


def cancel(session, attempt):
    path = path_for(session.file)
    with locked(path, root=path.parent):
        value = json.loads(path.read_text())
        if value['id'] == attempt['id'] and value['state'] != 'confirmed':
            value['state'] = 'cancelled'
            atomic(path, value)


def validate(session, attempt, actor):
    target = attempt['target']
    if any(getattr(actor, key) != target[key] for key in
           ('kind', 'account', 'pane', 'terminal', 'workspace', 'pid', 'started')):
        raise RuntimeError('O destino da confirmação mudou')
    session.runtime.verify(actor)
    if Path(bindings.project_for(actor)).resolve() != session.repo:
        raise RuntimeError('O projeto da confirmação mudou')


def produce(file, attempt_id):
    """Called by the chosen conversation, never by the Tasks process."""
    bindings.engine()
    recovery = importlib.import_module('left_undone.recovery')
    path = path_for(file)
    with locked(path, root=path.parent):
        attempt = json.loads(path.read_text())
        if attempt['id'] != attempt_id or attempt['state'] != 'pending':
            raise RuntimeError('Tentativa cancelada ou substituída')
        attempt['helper_started'] = True
        atomic(path, attempt)
    try:
        actor = recovery.recover(attempt['marker'])
        from watchdog_app.actions import Session
        session = Session(file, attempt['repo'], allow_unavailable=True, follow=True)
        validate(session, attempt, actor)
        result = dict(state='ready', proof=asdict(actor))
    except (RuntimeError, OSError, ValueError, KeyError, TypeError) as error:
        result = dict(state='failed', error=str(error))
    with locked(path, root=path.parent):
        current = json.loads(path.read_text())
        if current['id'] != attempt_id or current['state'] != 'pending':
            raise RuntimeError('Tentativa cancelada ou substituída')
        current.update(result)
        atomic(path, current)
    return current['state'] == 'ready'


def finish(session, attempt):
    from watchdog_app.leader_link import connect
    path = path_for(session.file)
    with locked(path, root=path.parent):
        value = json.loads(path.read_text())
        if value['id'] != attempt['id'] or value['state'] != 'ready':
            raise RuntimeError(value.get('error', 'Prova ausente; confirme na conversa ou tente novamente'))
        actor = session.runtime.Binding(**value['proof'])
        validate(session, value, actor)
        successor = connect(session, actor)
        successor.verify()
        persisted = json.loads(successor.file.read_text())
        if persisted['binding'] != asdict(actor):
            raise RuntimeError('O vínculo salvo não corresponde à sessão confirmada')
        value['state'] = 'confirmed'
        atomic(path, value)
    return successor


def main(argv=None):
    file, attempt_id = list(sys.argv[1:] if argv is None else argv)
    try:
        if not produce(file, attempt_id):
            print('Sessão não confirmada')
            return 1
        print('Prova produzida. Volte ao Tasks e pressione Enter para conferir.')
        return 0
    except (RuntimeError, OSError, ValueError, KeyError, TypeError) as error:
        print('Sessão não confirmada: ' + str(error))
        return 1
