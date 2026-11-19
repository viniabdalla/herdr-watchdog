"""Explicit existing-executor mode; the leader reviews exact committed evidence."""
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

from . import bindings
from .mission import FINISHED, require_summary


def is_single(run):
    return run.get('execution_mode', 'team') == 'single'


def validate_executor(repo, main, executor, *, base=None):
    from .mission_launch import git
    if not isinstance(executor, dict) or not isinstance(executor.get('binding'), dict):
        raise RuntimeError('Select an explicit verified executor')
    actor = executor['binding']
    if actor.get('kind') != 'codex':
        raise RuntimeError('Single execution requires an exact Codex executor')
    try: uuid.UUID(actor['session'])
    except (ValueError, KeyError, TypeError) as error:
        raise RuntimeError('Executor requires a valid exact thread UUID') from error
    if any(actor.get(k) == main.get(k) for k in ('session', 'pane', 'terminal', 'pid')):
        raise RuntimeError('Executor must be distinct from the leader')
    live = bindings.verify(bindings.engine().Binding(**actor))
    if live.get('agent_status') not in ('idle', 'done'):
        raise RuntimeError('Executor must be idle; nothing was queued')
    path = Path(executor['worktree'])
    if (not path.is_absolute() or path.is_symlink() or str(path.resolve()) != str(path) or
            path.resolve() == Path(repo).resolve()):
        raise RuntimeError('Executor needs a separate isolated worktree')
    cwd = live.get('foreground_cwd') or live.get('cwd') or bindings.project_for(bindings.engine().Binding(**actor))
    if not cwd or git(cwd, 'rev-parse', '--show-toplevel') != str(path):
        raise RuntimeError('Executor worktree no longer matches its verified session')
    if git(path, 'rev-parse', '--show-toplevel') != str(path):
        raise RuntimeError('Executor worktree root changed')
    common = git(repo, 'rev-parse', '--path-format=absolute', '--git-common-dir')
    if git(path, 'rev-parse', '--path-format=absolute', '--git-common-dir') != common:
        raise RuntimeError('Executor belongs to another repository')
    # A normal clone or submodule is not an isolated worktree of this repository.
    if git(path, 'rev-parse', '--path-format=absolute', '--git-dir') == common:
        raise RuntimeError('Executor needs a linked isolated worktree')
    branch = git(path, 'rev-parse', '--abbrev-ref', 'HEAD')
    if branch != executor.get('branch'):
        raise RuntimeError('Executor branch changed')
    if git(path, 'status', '--porcelain'):
        raise RuntimeError('Executor worktree must be clean')
    if base and git(path, 'rev-parse', 'HEAD') != base:
        raise RuntimeError('Executor head differs from the approved base')
    return live


def choices(repo, main):
    from .mission_launch import git
    actors, errors = bindings.engine().candidates()
    result = []
    for actor in actors:
        try:
            live = bindings.verify(actor)
            cwd = live.get('foreground_cwd') or live.get('cwd') or bindings.project_for(actor)
            path = git(cwd, 'rev-parse', '--show-toplevel') if cwd else ''
            executor = {'binding': asdict(actor), 'worktree': path,
                        'branch': git(path, 'rev-parse', '--abbrev-ref', 'HEAD')}
            validate_executor(repo, main, executor)
            result.append(executor)
        except (RuntimeError, OSError, ValueError, KeyError, TypeError):
            continue
    return result, errors


def available(store, repo, executor, *, excluding=None):
    actor = executor['binding']
    for run in store.list(repo):
        if run['id'] == excluding or run['phase'] in FINISHED:
            continue
        for part in run.get('participants', {}).values():
            other = part.get('native', {})
            if (other.get('account'), other.get('session')) == (actor['account'], actor['session']):
                raise RuntimeError('Executor already belongs to unfinished run ' + run['id'][:8])
        other = run.get('executor', {}).get('binding', {})
        if (other.get('account'), other.get('session')) == (actor['account'], actor['session']):
            raise RuntimeError('Executor already reserved by run ' + run['id'][:8])


def start_bridge(store, run):
    """Attach a host to an existing idle actor; never start/restart the actor."""
    from .mission_launch import ROOT
    folder = store.root / run['id']
    with (folder / 'worker-host.log').open('a') as stream:
        host = subprocess.Popen([sys.executable, str(ROOT/'watchdog'), 'mission', 'native-host',
            '--run', run['id'], '--role', 'worker', '--state-dir', str(store.root), '--confirm'],
            stdin=subprocess.DEVNULL, stdout=stream, stderr=stream, start_new_session=True)
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if host.poll() is not None:
            raise RuntimeError('Executor host attachment failed; inspect worker-host.log; actor preserved')
        proof_file = folder / 'worker-identity.json'
        if proof_file.exists():
            proof = json.loads(proof_file.read_text())
            if Path(proof['broker']).exists():
                return host.pid
        time.sleep(.05)
    raise RuntimeError('Executor host attachment is uncertain; inspect retained host before retrying')


def launch_existing(store, identity, brief, *, api=None):
    from .mission_launch import main_session, validate_brief, clean_base, start_monitor
    from .mission_native import boot_id, participant_prompt
    with store.lock(identity):
        run = store.load(identity)
        if run['phase'] != 'requested' or run.get('operation'):
            raise RuntimeError('Run already launched or interrupted; inspect its retained resources')
        if run['request_delivery'] != 'sent':
            raise RuntimeError('Coordination request delivery is uncertain')
        main_session(run); validate_brief(run, brief); clean_base(run, brief)
        executor = run['executor']
        live = validate_executor(run['repo'], run['main'], executor, base=brief['base_sha'])
        available(store, run['repo'], executor, excluding=identity)
        # Live agent metadata is verified by the native identity engine. No pane mutation.
        pane = {'pane_id':executor['binding']['pane'], 'terminal_id':executor['binding']['terminal'],
                'workspace_id':executor['binding']['workspace'], 'tab_id':live.get('tab_id')}
        part = dict(brief['participants']['worker'], base_sha=brief['base_sha'],
                    role_context='You are the assigned worker. Accept only the explicit coordinator contract.')
        run.update(brief=brief, participants={'worker':part}, resources={'worker':pane},
            transport={'kind':'native','boot_id':boot_id()}, identity_protocol=3,
            phase='active', operation='attach existing executor')
        folder = store.root / identity; folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        if brief.get('session_policy'):
            run['session_policy'] = brief['session_policy']
        from .mission_handoff import claim_session
        claim_session(store, run, 'worker', next(iter(run['tasks'])), brief['base_sha'])
        store.save(run)
    # host_bridge locks this ledger itself; never hold its lock while waiting for it.
    try:
        host_pid = start_bridge(store, run)
        with store.lock(identity):
            run = store.load(identity); main_session(run)
            from .mission_launch import source_current
            source_current(run)
            actor = bindings.engine().Binding(**executor['binding'])
            if bindings.verify(actor).get('agent_status') not in ('idle', 'done'):
                raise RuntimeError('Executor became busy during attachment; actor preserved')
            run['host_pid'] = host_pid
            run['enrollment_delivery'] = 'sending'; run['operation'] = 'notify existing executor'; store.save(run)
            try:
                receipt = bindings.engine().queue(actor, participant_prompt(store, run, 'worker'))
                uuid.UUID(receipt)
            except Exception as error:
                run['enrollment_delivery'] = 'uncertain'; store.save(run)
                raise RuntimeError('Executor enrollment notification is uncertain; inspect exact queue; do not resend') from error
            run.update(enrollment_delivery='sent', enrollment_receipt=receipt, operation='start monitor'); store.save(run)
            run['monitor_pid'] = start_monitor(run, store)
            run['operation'] = None; store.save(run)
            return run
    except Exception as error:
        with store.lock(identity):
            run = store.load(identity)
            run.update(phase='blocked', reason=str(error))
            for task in run['tasks'].values():
                task.update(state='blocked', summary=str(error), updated=time.time())
            store.save(run)
        raise


def verify_candidate(run, candidate):
    from .mission_launch import owned_worktree, git
    from .mission_transport import verify_result_commits
    if not is_single(run) or run.get('transport', {}).get('kind') != 'native':
        raise RuntimeError('Leader review requires explicit native single-executor mode')
    if run['phase'] != 'active' or any(not t.get('result') or t['state'] not in ('review', 'blocked') for t in run['tasks'].values()):
        raise RuntimeError('Every selected task needs implementation evidence before leader review')
    if not isinstance(candidate, str) or len(candidate) != 40 or git(run['repo'], 'rev-parse', candidate+'^{commit}') != candidate:
        raise RuntimeError('Leader review requires the full exact candidate SHA')
    from .mission_native import verify_participant
    verify_participant(run, 'worker')
    path = owned_worktree(run, 'worker')
    if git(path, 'status', '--porcelain'):
        raise RuntimeError('Worker worktree must be clean for review and approval')
    if git(path, 'rev-parse', 'HEAD') != candidate:
        raise RuntimeError('Worker head differs from the reviewed candidate')
    verify_result_commits(run, candidate)


def review_valid(run, candidate):
    review = run.get('leader_review') or {}
    return bool(is_single(run) and run.get('candidate') == candidate and review.get('candidate') == candidate and
        review.get('result_version') == run.get('result_version', 0) and review.get('reviewer') == run['main'] and
        review.get('verified_commits') is True and review.get('verdict') == 'pass' and review.get('tests') and
        review.get('summary') and all(t.get('result') and t['state'] == 'review' for t in run['tasks'].values()))


def review(store, identity, candidate, evidence, *, confirmed=False):
    from .mission_launch import main_session, source_current
    if not confirmed:
        raise RuntimeError('Explicit leader review confirmation is required')
    with store.lock(identity):
        run = store.load(identity); main_session(run); source_current(run)
        if not isinstance(evidence, dict):
            raise RuntimeError('Leader review requires structured evidence')
        if (evidence.get('run_id') != identity or evidence.get('candidate') != candidate or
                type(evidence.get('result_version')) is not int or evidence['result_version'] != run.get('result_version', 0)):
            raise RuntimeError('Leader evidence run, candidate or result version differs')
        require_summary(evidence)
        tests = evidence.get('tests')
        if (evidence.get('verdict') not in ('pass', 'fail') or not isinstance(tests, list) or not tests or
                any(not isinstance(t, str) or not t.strip() for t in tests)):
            raise RuntimeError('Leader review requires a verdict and observed test evidence')
        verify_candidate(run, candidate)
        run['candidate'] = candidate
        run['leader_review'] = dict(evidence, reviewer=run['main'], verified_commits=True,
                                    id=str(uuid.uuid4()), at=time.time())
        for task in run['tasks'].values():
            task.update(state='review' if evidence['verdict']=='pass' else 'blocked', agent='main',
                        summary='Revisão do líder: '+evidence['summary'], updated=time.time())
        store.save(run)
        return run
