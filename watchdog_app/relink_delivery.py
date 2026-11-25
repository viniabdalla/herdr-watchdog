"""Religar invocation transport, separate from the core's session proof.

No background replay: Tasks advances a durable invocation under the common pane
lease. A fence stops older queue workers until identity has been proved.
"""
from contextlib import nullcontext
from dataclasses import asdict
import json
from pathlib import Path
import re
import time

from . import bindings, pane_delivery as transport
from .herdr import Herdr
from .portable_runtime import project_root
from .store import atomic, state_root


def record_path(ref):
    if not re.fullmatch('[0-9a-f]{32}', ref):
        raise RuntimeError('Referência de Religar inválida')
    root = state_root()
    return root/'relink-deliveries'/(ref+'.json')


def fence_path(pending):
    return pending.with_suffix('.relink.json')


def skill_available(repo, candidate):
    roots = [Path(candidate.account).expanduser()/'skills', Path.home()/'.agents/skills']
    roots += [p/'.agents/skills' for p in (Path(repo).resolve(), *Path(repo).resolve().parents)]
    return any((p/'religar/SKILL.md').is_file() for p in roots)


def validate(candidate, repo, api):
    """Validate the live destination, allowing an obsolete advertised session."""
    agent = api.call('agent', 'get', candidate.pane)['agent']
    transport.check_binding(agent, candidate)
    runtime = bindings.engine()
    process = runtime.process_info(candidate.pid)
    if not process or any(process.get(k) != v for k, v in (
            ('kind', candidate.kind), ('account', candidate.account),
            ('pane', candidate.pane), ('started', candidate.started))):
        raise RuntimeError('Processo ou conta do destino mudou')
    foreground = api.call('pane', 'process-info', '--pane', candidate.pane)['process_info']['foreground_processes']
    if candidate.pid not in [p['pid'] for p in foreground]:
        raise RuntimeError('Agente do destino não está em primeiro plano')
    live = api.checked({'pane_id':candidate.pane, 'terminal_id':candidate.terminal})
    cwd = live.get('foreground_cwd') or live.get('cwd')
    if cwd and project_root(cwd) != project_root(repo):
        raise RuntimeError('Projeto do destino mudou')
    if not cwd:
        project = bindings.project_for(candidate)
        if not project or project_root(project) != project_root(repo):
            raise RuntimeError('Projeto do destino não identificado')
    return agent


def choices(session):
    """Codex needs live process/project identity; its old history is no proof."""
    from .leader_link import choices as verified_choices
    result = [b for b in verified_choices(session) if b.kind != 'codex']
    runtime = bindings.engine()
    api = Herdr()
    processes = runtime.processes()
    for agent in api.call('agent', 'list')['agents']:
        if agent.get('agent') != 'codex' or agent.get('workspace_id') != session.binding.workspace:
            continue
        matches = [p for p in processes if p.get('kind') == 'codex' and p.get('pane') == agent['pane_id']]
        sid = agent.get('agent_session') or {}
        if len(matches) != 1 or sid.get('kind') != 'id' or not sid.get('value'):
            continue
        p = matches[0]
        # The advertised history can be obsolete or absent. It is never proof.
        b = runtime.Binding(kind='codex', session=sid['value'], account=p['account'],
            pane=agent['pane_id'], terminal=agent['terminal_id'], workspace=agent['workspace_id'],
            history='', pid=p['pid'], started=p['started'])
        try:
            validate(b, session.repo, api)
        except (RuntimeError, OSError, ValueError, KeyError, TypeError):
            continue
        result.append(b)
    return result


def start(session, candidate, begin, *, api=None):
    """Pause prior writers before beginning the core's proof window."""
    api = api or Herdr()
    if not skill_available(session.repo, candidate):
        raise RuntimeError('Skill $religar indisponível no destino ' + candidate.pane)
    with transport.pane_lock(candidate.pane, api.session, deadline=time.monotonic()+2) as pending:
        fence = fence_path(pending)
        if fence.exists():
            previous = json.loads(fence.read_text())['ref']
            old_path = record_path(previous)
            old = json.loads(old_path.read_text()) if old_path.exists() else {}
            if old.get('state') not in ('failed', 'cancelled', 'confirmed') or old.get('unresolved'):
                raise RuntimeError('Religar anterior ainda protege este pane; confira a entrega pendente')
        validate(candidate, session.repo, api)
        ref = begin(session, candidate)
        atomic(fence, dict(ref=ref))
        prepare(ref, candidate, session.repo, api=api, _pending=pending)
        return ref


def prepare(ref, candidate, repo, *, api=None, _pending=None):
    api = api or Herdr()
    if not skill_available(repo, candidate):
        raise RuntimeError('Skill $religar indisponível no destino ' + candidate.pane)
    validate(candidate, repo, api)
    lease = nullcontext(_pending) if _pending is not None else transport.pane_lock(
        candidate.pane, api.session, deadline=time.monotonic()+2)
    with lease as pending:
        fence = fence_path(pending)
        if fence.exists() and json.loads(fence.read_text()).get('ref') != ref:
            raise RuntimeError('Religar anterior ainda protege este pane; confira a entrega pendente')
        path = record_path(ref)
        if path.exists():
            return
        # Fence precedes authorization: an interrupted prepare fails closed.
        atomic(fence, dict(ref=ref))
        atomic(path, dict(ref=ref, candidate=asdict(candidate), repo=str(repo),
            session=api.session, state='waiting', notice='Aguardando destino · '+candidate.pane))


def step(ref, attempt, *, api=None, read_attempt=None):
    path = record_path(ref)
    if not path.exists():
        return dict(state='uncertain', notice='Envio não preparado; invocação não será repetida')
    job = json.loads(path.read_text())
    api = api or Herdr(job['session'])
    candidate = bindings.engine().Binding(**job['candidate'])
    with transport.pane_lock(candidate.pane, api.session, deadline=time.monotonic()+.05) as pending:
        job = json.loads(path.read_text())
        if read_attempt is not None:
            attempt = read_attempt(ref)
        def save(state, notice):
            if state in ('pasting', 'materialized', 'submitting', 'uncertain'):
                job['unresolved'] = True
            elif state in ('sent', 'confirmed'):
                job['unresolved'] = False
            job.update(state=state, notice=notice); atomic(path, job)
            return job
        old = pending.exists() or transport.queue_state_path(pending).exists() or bool(transport.queued_paths(pending))
        if attempt['state'] in ('cancelled','failed','confirmed'):
            # Never release an older job into the still-obsolete native identity.
            if (not old and not job.get('unresolved', job['state'] in ('pasting', 'materialized', 'submitting', 'uncertain'))) or attempt['state'] == 'confirmed':
                fence=fence_path(pending)
                if fence.exists() and json.loads(fence.read_text()).get('ref') == ref:
                    fence.unlink()
            return save(attempt['state'], attempt.get('notice', attempt['state']))
        if job['state'] in ('sent','uncertain','cancelled','failed','confirmed'):
            return job
        if old:
            paths = ([pending] if pending.exists() else []) + transport.queued_paths(pending)
            safe = not transport.queue_state_path(pending).exists() and all(
                (lambda value: value.get('phase') == 'waiting' and not value.get('keys')
                 and not value.get('confirmation_started_at'))(json.loads(p.read_text())) for p in paths)
            if not safe:
                return save(job['state'], 'Aguardando entrega anterior em voo ou incerta; confira a fila antes de Religar')
            held = path.with_suffix('.held')
            held.mkdir(parents=True, exist_ok=True)
            for item in paths:
                item.replace(held/item.name)
            job['held'] = str(held)
            atomic(path, job)
        try:
            agent = validate(candidate, job['repo'], api)
            rows = transport.surface(api, candidate.pane)
            text = '$religar '+ref
            state = job['state']
            if state == 'waiting':
                if not skill_available(job['repo'], candidate):
                    return save('failed', 'Skill $religar indisponível no destino ' + candidate.pane)
                if agent['agent_status'] not in ('idle','done'):
                    return save(state, 'Aguardando agente ocupado · '+candidate.pane)
                if rows != []:
                    return save(state, 'Aguardando rascunho livre · '+candidate.pane)
                # Recheck immediately before the only paste.
                validate(candidate, job['repo'], api)
                if transport.surface(api, candidate.pane) != []:
                    return save(state, 'Aguardando rascunho livre · '+candidate.pane)
                save('pasting', 'Aguardando materialização · '+candidate.pane)
                job['started_at']=time.time();atomic(path,job)
                api.call('pane','send-text',candidate.pane,text)
            elif state == 'pasting':
                if transport.matches(rows,text):
                    save('materialized','Invocação visível · '+candidate.pane)
                elif rows:
                    return save('uncertain','Entrega incerta: rascunho alterado; sem repetição')
                elif time.time()-job['started_at'] > transport.CONFIRM_TIMEOUT:
                    return save('uncertain','Entrega incerta: materialização não confirmada; sem repetição')
            elif state == 'materialized':
                if not transport.matches(rows,text):
                    return save('uncertain','Entrega incerta: rascunho alterado; sem repetição')
                if agent['agent_status'] not in ('idle','done'):
                    return save(state,'Aguardando agente ocupado · '+candidate.pane)
                validate(candidate,job['repo'],api)
                if not transport.matches(transport.surface(api,candidate.pane),text):
                    return save('uncertain','Entrega incerta antes de Enter; sem repetição')
                save('submitting','Aguardando consumo · '+candidate.pane)
                job['started_at']=time.time();atomic(path,job)
                api.call('pane','send-keys',candidate.pane,'Enter')
            elif state == 'submitting':
                if rows == []:
                    return save('sent','Invocação enviada · '+candidate.pane+' · aguardando confirmação da skill')
                if not transport.matches(rows,text) or time.time()-job['started_at'] > transport.CONFIRM_TIMEOUT:
                    return save('uncertain','Entrega incerta após Enter; sem repetição')
            return job
        except (RuntimeError,OSError,ValueError,KeyError,TypeError) as error:
            return save('uncertain' if job['state'] != 'waiting' else 'failed', str(error))
