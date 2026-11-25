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
        if progress != (job['phase'], len(job.get('keys', []))):
            job['last_progress_at'] = time.time()
            atomic(pending, job)
        time.sleep(.05 if deadline is not None else .25)


STALL_TIMEOUT = 120


def queue_state_path(pending):
    return pending.with_name(pending.name.removesuffix('.pending.json')+'.stalled.json')


def queued_paths(pending):
    return sorted(pending.parent.glob(pending.name.removesuffix('.pending.json')+'.queued.*.json'))


def queue_notice(pane, session=None):
    path = queue_state_path(pending_path(pane, session))
    try:
        state = json.loads(path.read_text())
        return 'Fila travada · perguntei ao líder' if state['status'] == 'confirmed' else ''
    except FileNotFoundError:
        return ''


def check_stalled(pending):
    """Called under the pane lease. Persist intent before replacing the front.

    A restart finishes that same transition and handshake, never a second notice.
    All original entries remain available until the leader's explicit decision.
    """
    state_path = queue_state_path(pending)
    if state_path.exists():
        state = json.loads(state_path.read_text())
        if state['status'] != 'prepared': return
    else:
        if not pending.exists(): return
        job = json.loads(pending.read_text())
        if job.get('stall_notice'): return  # no recursive escalation
        now = time.time()
        progress_at = job.get('last_progress_at')
        if progress_at is None:
            # Legacy records have neither timestamps nor IDs. Observe them in a
            # sidecar so even the original serialized file remains untouched.
            observed_path = pending.with_name(pending.name.removesuffix('.pending.json')+'.progress.json')
            fingerprint = reconciliation_id(job, pending)
            observed = json.loads(observed_path.read_text()) if observed_path.exists() else {}
            if observed.get('fingerprint') != fingerprint:
                atomic(observed_path,dict(fingerprint=fingerprint,at=now))
                return
            progress_at = observed['at']
        elapsed = now - progress_at
        if elapsed <= STALL_TIMEOUT: return
        sources = queued_paths(pending)
        queued = [json.loads(path.read_text()) for path in sources]
        summary = lambda item: ' '.join(item['text'].split())[:180]
        text = (f"Fila travada no seu pane {job['pane']}: a entrega da frente ({summary(job)}) "
                f"está parada há {int(elapsed)} s. Atrás dela: " +
                ('; '.join(summary(item) for item in queued) or 'nenhuma entrega') +
                '. Siga "Fila travada" no padrão do dispatch e me diga o que precisa da atenção do Vini.')
        archive = pending.with_name(pending.name.removesuffix('.pending.json')+'.stalled.'+uuid.uuid4().hex)
        state = dict(status='prepared', archive=str(archive), front=job, queued=queued,
                     queue_sources=[str(path) for path in sources],
                     front_serialized=pending.read_text(),queue_serialized=[path.read_text() for path in sources],
                     notice=dict(version=1,delivery_id=uuid.uuid4().hex,pane=job['pane'],
                                 session=job['session'],identity=job['identity'],text=text,
                                 phase='waiting',enter='Enter',stall_notice=True,last_progress_at=now))
        atomic(state_path, state)
    archive = Path(state['archive']); archive.mkdir(exist_ok=True, mode=0o700)
    archive_original(archive/'front.json', state['front_serialized'])
    for i,raw in enumerate(state['queue_serialized']):
        archive_original(archive/f'queued-{i:08d}.json',raw)
    atomic(archive/'queue.json', state['queued'])
    # Prepared is a recoverable write-ahead record, protected by the same lease.
    notice = state['notice']
    awaiting = dict(state, status='awaiting')
    confirmed = dict(state, status='confirmed')
    notice = dict(notice, on_confirm=dict(path=str(state_path),expected=awaiting,value=confirmed))
    atomic(pending, notice)
    atomic(state_path, awaiting)



def archive_original(path, raw):
    temporary = path.with_suffix('.original.tmp')
    with temporary.open('w') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.chmod(0o600)
    temporary.replace(path)


def reconciliation_id(job, source):
    """Legacy IDs live in the decision view; original records stay byte-for-byte."""
    return job.get('delivery_id') or 'legacy-'+hashlib.sha256(
        (str(source)+'\0'+json.dumps(job,sort_keys=True)).encode()).hexdigest()[:24]


def same_request(a, b):
    return all(a.get(key) == b.get(key) for key in ('text','on_confirm','identity','enter'))


def queue_snapshot(pane, session=None):
    with pane_lock(pane, session) as pending:
        state = json.loads(queue_state_path(pending).read_text())
        entries = [(pending,state['front'])] + list(zip(state['queue_sources'],state['queued']))
        return [dict(id=reconciliation_id(job,str(source)),job=job) for source,job in entries]


def resolve_queue(pane, keep, evidence, session=None):
    """Explicit leader decision. Archive all originals before releasing any copy."""
    if not evidence.strip(): raise RuntimeError('Informe a evidência da reconciliação')
    with pane_lock(pane, session) as pending:
        state_path = queue_state_path(pending)
        state = json.loads(state_path.read_text())
        if state['status'] != 'confirmed' or pending.exists():
            raise RuntimeError('Aguarde a confirmação do aviso ao líder')
        paths = queued_paths(pending)
        jobs = [state['front']] + [json.loads(path.read_text()) for path in paths]
        ids = [reconciliation_id(job, source) for job,source in zip(jobs,[str(pending)]+[str(path) for path in paths])]
        snapshot_ids = {reconciliation_id(state['front'],str(pending))}
        snapshot_ids.update(reconciliation_id(job,source) for job,source in
                            zip(state['queued'],state['queue_sources']))
        if len(ids) != len(set(ids)) or set(keep) - set(ids):
            raise RuntimeError('Decisão não corresponde à fila atual; releia os registros')
        # The decision only retires items the leader saw in the stalled snapshot.
        # Later arrivals survive even when absent from --keep.
        selected = [job for job,key in zip(jobs,ids) if key in keep or key not in snapshot_ids]
        selected = [job for i,job in enumerate(selected)
                    if not any(same_request(later,job) for later in selected[i+1:])]
        api = Herdr(session)
        for job in selected: live(api, pane, job['identity'])
        if surface(api, pane) != []:
            raise RuntimeError('Rascunho presente; preserve-o antes de liberar a fila')
        archive = Path(state['archive'])
        for path in paths: archive_original(archive/('decision-'+path.name),path.read_text())
        atomic(archive/'decision.json', dict(evidence=evidence,keep=keep,jobs=jobs,resolved_at=time.time()))
        # Reuse queued filenames. Recovery of a partial decision is idempotent:
        # the original snapshot is saved before removing any queued entry.
        state.update(status='resolving',selected=selected,paths=[str(path) for path in paths])
        atomic(state_path,state)
        finish_resolution(pending,state_path,state)
    return 0


def finish_resolution(pending, state_path, state):
    for path in state['paths']: Path(path).unlink(missing_ok=True)
    prefix = pending.name.removesuffix('.pending.json')
    for i,job in enumerate(state['selected']):
        job = dict(job,phase='waiting',keys=[],last_progress_at=time.time())
        for key in ('confirmation_started_at','uncertain_phase','error','observed_composer','suspended_at'):
            job.pop(key,None)
        atomic(pending.with_name(prefix+f'.queued.0000000000000000000.recovered.{i:08d}.json'),job)
    state_path.unlink()



def recover_notice(pane, incident, action, recovery_id, evidence, *, session=None, not_delivered=False):
    """Explicit non-delivery decision; never infer a receipt from an empty field.

    The incident path and operator-supplied recovery ID pin the decision across
    restarts. A replay of that command finishes its intent, never rearms twice.
    Changed identities may only close the obsolete incident, without input.
    """
    if not evidence.strip() or not recovery_id.strip():
        raise RuntimeError('Informe identificação e evidência da recuperação')
    if action not in ('rearm','close'): raise RuntimeError('Recuperação desconhecida')
    archive = Path(incident).resolve()
    receipt_path = archive/('notice-recovery.'+hashlib.sha256(recovery_id.encode()).hexdigest()+'.json')
    request = dict(pane=pane,session=session,incident=str(archive),action=action,
                   recovery_id=recovery_id,evidence=evidence,not_delivered=not_delivered)
    with pane_lock(pane,session) as pending:
        state_path = queue_state_path(pending)
        receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else None
        if receipt and receipt['request'] != request:
            raise RuntimeError('ID de recuperação já usado por outra decisão')
        state = json.loads(state_path.read_text()) if state_path.exists() else None
        if state and state['status'] == 'recovering-notice':
            if state['recovery']['receipt'] != str(receipt_path):
                raise RuntimeError('Há outra recuperação em andamento; retome a decisão salva')
            finish_notice_recovery(pending,state_path,state)
            return 0
        if receipt and receipt['status'] == 'complete': return 0
        if not state or state['archive'] != str(archive) or state['status'] != 'awaiting':
            raise RuntimeError('Incidente mudou ou não aguarda recuperação; releia os registros')
        notice = json.loads(pending.read_text())
        if not notice.get('stall_notice') or notice['phase'] != 'uncertain':
            raise RuntimeError('Recuperação exige o próprio aviso suspenso')
        api = Herdr(session)
        agent = api.call('agent','get',pane)['agent']
        observed = identity(agent)
        if observed[0] != pane: raise RuntimeError('Pane de destino mudou')
        rows = surface(api,pane)
        if rows is None: raise RuntimeError('Compositor não verificável; recuperação suspensa')
        same_identity = observed == tuple(notice['identity'])
        if action == 'rearm':
            if not same_identity:
                raise RuntimeError('Identidade mudou; encerre documentalmente o incidente obsoleto')
            if not not_delivered:
                raise RuntimeError('Confirme NÃO entrega no histórico e encerramento do paste anterior')
            if matches(rows,notice['text']):
                raise RuntimeError('Aviso materializado; use a reconciliação R1, sem novo paste')
        elif same_identity:
            raise RuntimeError('Encerramento documental exige identidade antiga obsoleta')
        paths = queued_paths(pending)
        jobs = [json.loads(path.read_text()) for path in paths]
        # Closing never retargets obsolete requests or acknowledges their callbacks.
        # Every original remains archived. Current requests keep their FIFO order.
        selected = [job for job in jobs if tuple(job['identity']) == observed] if action == 'close' else []
        retired = [job for job in jobs if tuple(job['identity']) != observed] if action == 'close' else []
        receipt = dict(request=request,status='prepared',notice_serialized=pending.read_text(),
                       observed_identity=observed,observed_composer=rows,not_delivered=not_delivered,
                       retired=retired,prepared_at=time.time())
        for path in paths: archive_original(archive/('recovery-'+receipt_path.stem+'-'+path.name),path.read_text())
        atomic(receipt_path,receipt)
        rearmed = dict(notice,phase='waiting',keys=[],last_progress_at=time.time())
        for key in ('on_confirm','confirmation_started_at','uncertain_phase','error',
                    'observed_composer','suspended_at','last_key_at'):
            rearmed.pop(key,None)
        state.update(status='recovering-notice',recovery=dict(receipt=str(receipt_path),action=action,
                     notice=rearmed,paths=[str(path) for path in paths],selected=selected))
        atomic(state_path,state)
        finish_notice_recovery(pending,state_path,state)
    return 0


def finish_notice_recovery(pending, state_path, state):
    """Under the pane lease, complete a durable decision before any pane input."""
    plan = state['recovery']
    receipt_path = Path(plan['receipt'])
    receipt = json.loads(receipt_path.read_text())
    if plan['action'] == 'rearm':
        awaiting = dict(state,status='awaiting')
        awaiting.pop('recovery')
        awaiting.setdefault('notice_recoveries',[]).append(str(receipt_path))
        confirmed = dict(awaiting,status='confirmed')
        notice = dict(plan['notice'],on_confirm=dict(path=str(state_path),expected=awaiting,value=confirmed))
        atomic(pending,notice)
        # If interrupted here, the recovering marker blocks all pane writers.
        atomic(receipt_path,dict(receipt,status='complete',completed_at=time.time()))
        atomic(state_path,awaiting)
    else:
        # No key, paste or callback. This is cancellation, not a delivery receipt.
        pending.unlink(missing_ok=True)
        atomic(receipt_path,dict(receipt,status='complete',completed_at=time.time()))
        finish_resolution(pending,state_path,dict(state,paths=plan['paths'],selected=plan['selected']))


def watch(record):
    """Durable pane monitor; uncertainty does not kill the only waiting process."""
    record = Path(record)
    try:
        job = json.loads(record.read_text())
    except FileNotFoundError:
        return 0
    while True:
        with pane_lock(job['pane'], job['session']) as pending:
            state_path = queue_state_path(pending)
            if state_path.exists():
                state = json.loads(state_path.read_text())
                if state['status'] == 'resolving': finish_resolution(pending,state_path,state)
                elif state['status'] == 'recovering-notice': finish_notice_recovery(pending,state_path,state)
            check_stalled(pending)
            if not pending.exists() and not state_path.exists():
                paths = queued_paths(pending)
                if not paths: return 0
                front = json.loads(paths[0].read_text())
                front['last_progress_at'] = time.time()
                atomic(paths[0], front)
                paths[0].replace(pending)
            if pending.exists():
                front = json.loads(pending.read_text())
                if front['phase'] != 'uncertain':
                    try:
                        advance(Herdr(front['session']),front,pending,deadline=time.monotonic()+1)
                    except DeliveryPending:
                        pass
                    except (RuntimeError,OSError,ValueError,KeyError,TypeError) as error:
                        suspend(front,pending,error)
        time.sleep(.25)


def background_waiter(pending):
    # The detached process only continues this saved handshake; never pastes a
    # second copy. It owns the same pane lease and records errors beside the job.
    log = pending.with_suffix('.log')
    with log.open('a') as output:
        process = subprocess.Popen([sys.executable, '-m', 'watchdog_app.pane_delivery', 'watch', str(pending)],
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
                   phase='waiting', on_confirm=on_confirm, enter=enter, last_progress_at=time.time())
        prefix = pending.name.removesuffix('.pending.json')
        queued = pending.with_name(prefix+'.queued.'+str(time.time_ns())+'.'+uuid.uuid4().hex+'.json')
        # Save before waiting for the lease: concurrent B survives even while A
        # is waiting for a human draft and owns the pane indefinitely.
        atomic(queued, job)
        deadline = time.monotonic()+timeout
        with pane_lock(pane, api.session, deadline=deadline):
            if pending.exists() or queue_state_path(pending).exists() or not oldest(queued, pending):
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
            if background: background_waiter(pending)
        raise RuntimeError('Envio não confirmado ao pane '+pane+'; nada foi apagado ou reenviado: '+str(error)) from error


def resume(record):
    record = Path(record)
    job = json.loads(record.read_text())
    while True:
        with pane_lock(job['pane'], job['session']) as pending:
            state_path = queue_state_path(pending)
            if state_path.exists():
                state = json.loads(state_path.read_text())
                if state['status'] == 'recovering-notice':
                    finish_notice_recovery(pending,state_path,state)
            if record != pending:
                prefix = pending.name.removesuffix('.pending.json')+'.queued.'
                if record.parent != pending.parent or not record.name.startswith(prefix):
                    raise RuntimeError('Registro fora da trava do pane')
                if not record.exists(): return 0
                if pending.exists() or queue_state_path(pending).exists() or not oldest(record, pending):
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
        state_path = queue_state_path(pending)
        if state_path.exists() and json.loads(state_path.read_text())['status'] == 'recovering-notice':
            raise RuntimeError('Recuperação em andamento; retome a decisão salva antes de reconciliar')
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
        elif resolution == 'consumed':
            if not job.get('stall_notice') or observed_identity != tuple(job['identity']) or rows != []:
                raise RuntimeError('Confirmação manual exige aviso da trava, identidade e compositor vazio')
        elif resolution != 'retired':
            raise RuntimeError('Resolução desconhecida')
        archive = pending.with_name(pending.name.removesuffix('.pending.json')+
                                    '.reconciled.'+str(time.time_ns())+'.json')
        atomic(archive, dict(job=job, resolution=resolution, evidence=evidence,
                             observed_composer=rows, observed_identity=observed_identity, reconciled_at=time.time()))
        if resolution == 'consumed':
            callback = job['on_confirm']
            path = Path(callback['path'])
            if json.loads(path.read_text()) == callback['expected']:
                atomic(path,callback['value'])
            pending.unlink()
        elif resolution == 'retired':
            if job.get('stall_notice'):
                raise RuntimeError('O aviso da trava exige confirmação explícita; não pode ser retirado')
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
    commands.add_parser('watch').add_argument('record')
    snapshot_parser = commands.add_parser('queue-snapshot')
    snapshot_parser.add_argument('--pane', required=True)
    snapshot_parser.add_argument('--session')
    queue_recovery = commands.add_parser('resolve-queue')
    queue_recovery.add_argument('--pane', required=True)
    queue_recovery.add_argument('--session')
    queue_recovery.add_argument('--keep', nargs='*', default=[])
    queue_recovery.add_argument('--evidence', required=True)
    notice_recovery = commands.add_parser('recover-notice')
    notice_recovery.add_argument('--pane',required=True)
    notice_recovery.add_argument('--session')
    notice_recovery.add_argument('--incident',required=True)
    notice_recovery.add_argument('--action',choices=('rearm','close'),required=True)
    notice_recovery.add_argument('--recovery-id',required=True)
    notice_recovery.add_argument('--evidence',required=True)
    notice_recovery.add_argument('--not-delivered',action='store_true')
    recovery = commands.add_parser('reconcile')
    recovery.add_argument('record')
    recovery.add_argument('--resolution', choices=('materialized', 'retired', 'consumed'), required=True)
    recovery.add_argument('--evidence', required=True)
    args = parser.parse_args()
    if args.command == 'recover-notice':
        raise SystemExit(recover_notice(args.pane,args.incident,args.action,args.recovery_id,args.evidence,
                                       session=args.session,not_delivered=args.not_delivered))
    if args.command == 'queue-snapshot':
        print(json.dumps(queue_snapshot(args.pane,args.session),ensure_ascii=False,indent=2))
        raise SystemExit(0)
    if args.command == 'resolve-queue':
        raise SystemExit(resolve_queue(args.pane,args.keep,args.evidence,args.session))
    if args.command == 'watch': raise SystemExit(watch(args.record))
    raise SystemExit(resume(args.record) if args.command == 'resume' else
                     reconcile(args.record, args.resolution, args.evidence))
