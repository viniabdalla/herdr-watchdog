"""Confirmed native submissions, serialized across panels and executors."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

from .herdr import Herdr
from .store import atomic


def pending_path(pane, session=None):
    # All writers share this namespace regardless of project or worktree.
    root = Path(os.environ.get('XDG_STATE_HOME', str(Path.home()/'.local/state')))/'herdr-watchdog/pane-locks'
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    endpoint = (str(Path.home()/'.config/herdr/sessions'/session/'herdr.sock') if session else
                os.environ.get('HERDR_SOCKET_PATH', str(Path.home()/'.config/herdr/herdr.sock')))
    key = hashlib.sha256((endpoint+'\0'+pane).encode()).hexdigest()
    return root/(key+'.pending.json')


@contextmanager
def pane_lock(pane, session=None, *, deadline=None):
    pending = pending_path(pane, session)
    with pending.with_name(pending.name.removesuffix('.pending.json')+'.lock').open('a') as stream:
        while True:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if deadline is not None and time.monotonic() >= deadline:
                    raise DeliveryPending('Aguardando a entrega anterior ao mesmo pane')
                time.sleep(.05)
        yield pending


def identity(agent):
    session = agent['agent_session']
    if not agent['agent'] or not session or session['kind'] != 'id' or not session['value']:
        raise RuntimeError('Identidade nativa indisponível')
    return (agent['pane_id'], agent['terminal_id'], agent['agent'], session['value'])


def check_binding(agent, binding):
    if identity(agent) != (binding.pane, binding.terminal, binding.kind, binding.session):
        raise RuntimeError('O líder mudou; confira o vínculo antes de enviar')


def composer(screen):
    """Require an empty visible composer; dim placeholder text is not a draft.

    Inspect styled cells, not a search for the prompt text in scrollback. Wrapped
    composer rows share its background. Unknown layouts fail closed.
    """
    rows = []
    dim = False
    background = None
    for line in screen.splitlines():
        cells = []
        for part in re.split(r'(\x1b\[[0-9;]*m)', line):
            if part.startswith('\x1b['):
                codes = [int(x or '0') for x in part[2:-1].split(';')]
                i = 0
                while i < len(codes):
                    code = codes[i]
                    if code == 0: dim, background = False, None
                    elif code == 2: dim = True
                    elif code == 22: dim = False
                    elif code == 49: background = None
                    elif code == 48 and i+1 < len(codes):
                        end = i+5 if codes[i+1] == 2 else i+3
                        background = tuple(codes[i:end]); i = end-1
                    elif 40 <= code <= 47 or 100 <= code <= 107: background = (code,)
                    elif code == 38 and i+1 < len(codes):
                        i += 4 if codes[i+1] == 2 else 2
                    i += 1
            else:
                cells.extend((char, dim, background) for char in part)
        rows.append(cells)
    candidates = [(n, i) for n, row in enumerate(rows) for i, cell in enumerate(row)
                  if cell[0] in ('›', '❯') and all(c[0].isspace() for c in row[:i])]
    if not candidates:
        return None
    n, i = candidates[-1]
    bg = rows[n][i][2]
    if bg is not None:
        start = n
        while start > 0 and any(c[2] == bg for c in rows[start-1]):
            start -= 1
        n, i = next((row, col) for row, col in candidates if start <= row <= n)
    content = [rows[n][i+1:]]
    for row in rows[n+1:]:
        if not any(c[0].strip() for c in row):
            if bg is None: break
            continue
        if bg is None or any(c[0].strip() and c[2] != bg for c in row):
            break
        margin = i+2  # marker plus its separator; continuation rows repeat this gutter
        if len(row) >= margin and all(c[0].isspace() for c in row[:margin]):
            row = row[margin:]
        content.append(row)
    if all(not char.strip() or dim for row in content for char, dim, _ in row):
        return []
    text = [''.join(c[0] for c in row).rstrip() for row in content]
    if text and text[0].startswith(' '): text[0] = text[0][1:]
    return text



class DeliveryPending(RuntimeError):
    """Saved delivery is waiting; this is not an acknowledgement of submission."""


def matches(rows, text):
    if not rows: return False
    # Soft wraps can elide a word separator or split a word; hard breaks
    # preserve a newline. The TUI gutter has already been removed by composer().
    return re.fullmatch(r'(?:\n| |)'.join(re.escape(row) for row in rows), text) is not None


def live(api, pane, pinned):
    agent = api.call('agent', 'get', pane)['agent']
    if identity(agent) != tuple(pinned):
        raise RuntimeError('Identidade do líder mudou; entrega suspensa')
    return agent


def surface(api, pane):
    return composer(api.output('agent', 'read', pane, '--source', 'visible', '--format', 'ansi'))


# This bounds confirmation after a side effect, not legitimate waiting for a draft.
CONFIRM_TIMEOUT = 2.0


def suspend(job, pending, error, rows=None):
    if job['phase'] != 'uncertain':
        job.update(uncertain_phase=job['phase'], phase='uncertain', error=str(error),
                   observed_composer=rows, suspended_at=time.time())
        atomic(pending, job)


def advance(api, job, pending, *, deadline=None):
    pane, text = job['pane'], job['text']
    stable = 0
    def consumed():
        live(api, pane, job['identity'])
        callback = job.get('on_confirm')
        if callback:
            path = Path(callback['path'])
            if json.loads(path.read_text()) == callback['expected']:
                atomic(path, callback['value'])
        pending.unlink()
        return 'consumed'
    while True:
        if deadline is not None and time.monotonic() >= deadline:
            raise DeliveryPending('Entrega guardada, aguardando confirmação em '+str(pending))
        agent = live(api, pane, job['identity'])
        rows = surface(api, pane)
        phase = job['phase']
        progress = (phase, len(job.get('keys', [])))
        if phase == 'uncertain':
            raise RuntimeError('Entrega suspensa; reconcilie explicitamente o registro '+str(pending))
        # Old R1 jobs start one persisted observation window on their first resume.
        if phase != 'waiting' and 'confirmation_started_at' not in job:
            job['confirmation_started_at'] = time.time(); atomic(pending, job)
        def check_timeout():
            if phase != 'waiting' and time.time() - job['confirmation_started_at'] >= CONFIRM_TIMEOUT:
                error = 'Confirmação ausente após colar; reconciliação explícita necessária'
                suspend(job, pending, error, rows)
                raise RuntimeError(error)
        if agent['agent_status'] not in ('idle', 'done', 'working'):
            check_timeout()
            time.sleep(.05 if deadline is not None else .25)
            continue
        if phase == 'waiting':
            if rows == [] and agent['agent_status'] in ('idle', 'done', 'working'):
                # Recheck both identity and the empty surface immediately before paste.
                live(api, pane, job['identity'])
                if surface(api, pane) != []: continue
                job.update(phase='pasting', confirmation_started_at=time.time()); atomic(pending, job)
                api.call('pane', 'send-text', pane, text)
        elif phase == 'pasting':
            if matches(rows, text):
                job.update(phase='materialized', confirmation_started_at=time.time()); atomic(pending, job)
        elif phase in ('materialized', 'submitting'):
            if phase == 'submitting' and rows == []:
                return consumed()
            if not matches(rows, text):
                error = 'O rascunho mudou; nenhum texto foi apagado ou reenviado'
                suspend(job, pending, error, rows)
                raise RuntimeError(error)
            stable += 1
            keys = job.get('keys', [])
            elapsed = time.time() - job.get('last_key_at', 0)
            if phase == 'materialized' or (stable >= 2 and elapsed >= .25 and len(keys) < 2):
                key = job['enter']
                if keys and agent['agent'] == 'codex' and agent['agent_status'] == 'working' and not text.startswith(('/', '$')):
                    key = 'Tab'
                # A fallback can only act on our exact still-materialized message.
                live(api, pane, job['identity'])
                rows = surface(api, pane)
                if phase == 'submitting' and rows == []:
                    return consumed()
                if not matches(rows, text):
                    error = 'O rascunho mudou antes da tecla; entrega suspensa'
                    suspend(job, pending, error, rows)
                    raise RuntimeError(error)
                job.update(phase='submitting', keys=keys+[key], last_key_at=time.time(),
                           confirmation_started_at=time.time())
                atomic(pending, job)
                api.call('pane', 'send-keys', pane, key)
                stable = 0
        else:
            raise RuntimeError('Entrega suspensa; confira o registro '+str(pending))
        # After a slow mutation, read its result before judging the deadline.
        # Valid observations and stage/key progress always take precedence.
        if progress == (job['phase'], len(job.get('keys', []))):
            check_timeout()
        time.sleep(.05 if deadline is not None else .25)


def background_waiter(pending):
    # The detached process only continues this saved handshake; never pastes a
    # second copy. It owns the same pane lease and records errors beside the job.
    log = pending.with_suffix('.log')
    with log.open('a') as output:
        process = subprocess.Popen([sys.executable, '-m', 'watchdog_app.pane_delivery', 'resume', str(pending)],
            cwd=Path(__file__).resolve().parents[1], stdin=subprocess.DEVNULL,
            stdout=output, stderr=output, start_new_session=True)
    return process.pid


def oldest(queued, pending):
    prefix = pending.name.removesuffix('.pending.json')+'.queued.'
    jobs = sorted(pending.parent.glob(prefix+'*.json'))
    return not jobs or queued == jobs[0]


def send(pane, text, *, api=None, binding=None, timeout=30, background=True, on_confirm=None, enter='Enter'):
    api = api or Herdr()
    pending = pending_path(pane, api.session)
    queued = None
    claimed = False
    try:
        agent = api.call('agent', 'get', pane)['agent']
        pinned = identity(agent)
        if pinned[0] != pane: raise RuntimeError('Pane de destino mudou')
        if binding is not None: check_binding(agent, binding)
        job = dict(version=1, delivery_id=uuid.uuid4().hex, pane=pane, session=api.session, identity=pinned, text=text,
                   phase='waiting', on_confirm=on_confirm, enter=enter)
        prefix = pending.name.removesuffix('.pending.json')
        queued = pending.with_name(prefix+'.queued.'+str(time.time_ns())+'.'+uuid.uuid4().hex+'.json')
        # Save before waiting for the lease: concurrent B survives even while A
        # is waiting for a human draft and owns the pane indefinitely.
        atomic(queued, job)
        deadline = time.monotonic()+timeout
        with pane_lock(pane, api.session, deadline=deadline):
            if pending.exists() or not oldest(queued, pending):
                raise DeliveryPending('Entrega guardada atrás da anterior em '+str(queued))
            queued.replace(pending); claimed = True
            return advance(api, job, pending, deadline=deadline)
    except DeliveryPending as error:
        record = pending if claimed else queued
        if background and record is not None:
            pid = background_waiter(record)
            raise DeliveryPending(str(error)+' · registro '+str(record)+' · espera em segundo plano PID '+str(pid)) from error
        raise
    except (RuntimeError, OSError, ValueError, KeyError, TypeError) as error:
        if claimed and pending.exists():
            suspend(job, pending, error)
        raise RuntimeError('Envio não confirmado ao pane '+pane+'; nada foi apagado ou reenviado: '+str(error)) from error


def resume(record):
    record = Path(record)
    job = json.loads(record.read_text())
    while True:
        with pane_lock(job['pane'], job['session']) as pending:
            if record != pending:
                prefix = pending.name.removesuffix('.pending.json')+'.queued.'
                if record.parent != pending.parent or not record.name.startswith(prefix):
                    raise RuntimeError('Registro fora da trava do pane')
                if not record.exists(): return 0
                if pending.exists() or not oldest(record, pending):
                    wait = True
                else:
                    record.replace(pending); record = pending; wait = False
            else:
                if not pending.exists(): return 0
                wait = False
            if not wait:
                job = json.loads(pending.read_text())
                try:
                    advance(Herdr(job['session']), job, pending)
                except Exception as error:
                    suspend(job, pending, error)
                    raise
                return 0
        # Do not hold the lease while waiting behind another saved delivery.
        time.sleep(.25)


def reconcile(record, resolution, evidence):
    """Operator reconciliation, never automatic consumption or a second paste.

    Retiring requires the operator to establish that any delayed paste has settled.
    The original job and observations are archived before the FIFO is released.
    """
    record = Path(record)
    original = json.loads(record.read_text())
    if not evidence.strip(): raise RuntimeError('Informe a evidência da reconciliação')
    with pane_lock(original['pane'], original['session']) as pending:
        if record != pending: raise RuntimeError('Reconcilie somente o registro pendente do pane')
        job = json.loads(pending.read_text())
        if job != original: raise RuntimeError('O registro mudou durante a espera; releia antes de reconciliar')
        if job['phase'] != 'uncertain': raise RuntimeError('Suspenda a entrega antes de reconciliar')
        api = Herdr(job['session'])
        observed = api.call('agent', 'get', job['pane'])['agent']
        observed_identity = identity(observed)
        rows = surface(api, job['pane'])
        if resolution == 'materialized':
            if observed_identity != tuple(job['identity']):
                raise RuntimeError('Identidade mudou; somente retirada explícita é permitida')
            if job.get('uncertain_phase') != 'pasting' or not matches(rows, job['text']):
                raise RuntimeError('Continuação exige o texto próprio inteiro e suspensão durante paste')
        elif resolution != 'retired':
            raise RuntimeError('Resolução desconhecida')
        archive = pending.with_name(pending.name.removesuffix('.pending.json')+
                                    '.reconciled.'+str(time.time_ns())+'.json')
        atomic(archive, dict(job=job, resolution=resolution, evidence=evidence,
                             observed_composer=rows, observed_identity=observed_identity, reconciled_at=time.time()))
        if resolution == 'retired':
            # Explicit cancellation is NOT an acknowledgement; on_confirm never runs.
            pending.unlink()
        else:
            job.update(phase='materialized', confirmation_started_at=time.time(),
                       reconciliation=str(archive))
            atomic(pending, job)
    return 0


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Recuperação de entrega pelo pane')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('resume').add_argument('record')
    recovery = commands.add_parser('reconcile')
    recovery.add_argument('record')
    recovery.add_argument('--resolution', choices=('materialized', 'retired'), required=True)
    recovery.add_argument('--evidence', required=True)
    args = parser.parse_args()
    raise SystemExit(resume(args.record) if args.command == 'resume' else
                     reconcile(args.record, args.resolution, args.evidence))
