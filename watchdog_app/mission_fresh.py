"""Launch-time briefs adapted from Left Undone dispatch; all state belongs to Watchdog."""
import json
import os
import time
import uuid


def enabled(run):
    return run.get('execution_mode') == 'single' and run.get('provisioning') == 'fresh'


def prepare(run):
    """Persist this return value before starting a frontend; no receipt is invented."""
    from .mission_native import contract
    if not enabled(run) or not run['tasks'] or len(run['tasks']) != 1 and run.get('grouping') != 'together':
        raise RuntimeError('Launch-time contracts require one fresh executor task')
    task_id = next(iter(run['tasks']))
    task = run['tasks'][task_id]
    if task.get('attempt_id'):
        raise RuntimeError('Launch assignment already prepared; inspect its retained intent')
    attempt = str(uuid.uuid4())
    payload = contract(run, task_id, attempt)
    if run.get('purpose') == 'plan':
        payload['instructions'] = 'Prepare a plan only. Do not implement, commit, push or complete tasks.'
        payload.pop('report_schema', None)
    if run.get('clarification'): payload['clarification'] = run['clarification']
    run['participants']['worker']['startup_attempt'] = attempt
    for member in run['tasks'].values():
        member.update(attempt_id=attempt, delivery='sending')
    run.setdefault('deliveries', {})[attempt] = {
        'method':'launch', 'role':'worker', 'attempt_id':attempt, 'payload':payload,
        'state':'sending', 'created':time.time()}


def attach(run, proof):
    """A verified frontend acknowledges launch; enrollment is still required to report."""
    part = run['participants']['worker']
    attempt = part.get('startup_attempt')
    record = run.get('deliveries', {}).get(attempt)
    if not record or record.get('state') != 'sending' or record.get('method') != 'launch':
        raise RuntimeError('Launch contract intent changed before native registration')
    record.update(state='sent', recipient=proof['native'], generation=proof['generation'],
                  launch_receipt={'pid':proof['native']['pid'], 'started':proof['native']['started']})
    for task in run['tasks'].values():
        task.update(delivery='sent', state='working', agent='worker',
                    summary='Contrato entregue ao iniciar o executor', updated=time.time())


def provider_command(part, prompt, store, run):
    """Port LU's provider selection while retaining WD's Codex sandbox and isolated Git tree."""
    from .mission_launch import git
    env = {k:v for k,v in os.environ.items()
           if not k.startswith(('CODEX_', 'AI_MEMORY_', 'OPENAI_', 'ANTHROPIC_', 'CLAUDE_CODE_'))
           and k not in ('CLAUDECODE', 'CLAUDE_CONFIG_DIR')}
    kind = part.get('kind', 'codex')
    if kind == 'claude':
        env['CLAUDE_CONFIG_DIR'] = part['account']
        return [part['executable'], '--model', part['model'], '--effort', part['effort'],
                '--permission-mode', 'bypassPermissions', '--', prompt], env
    if kind != 'codex':
        raise RuntimeError('Unknown executor provider')
    env['CODEX_HOME'] = part['account']
    return [part['executable'], '-C', part['worktree'], '--model', part['model'],
            '--sandbox', 'workspace-write', '--ask-for-approval', 'never',
            '--add-dir', str(store.root), '--add-dir', git(run['repo'], 'rev-parse', '--path-format=absolute', '--git-common-dir'),
            '-c', 'sandbox_workspace_write.network_access=true',
            '-c', 'model_reasoning_effort=' + json.dumps(part['effort']), prompt], env


def artifact(run, role, suffix):
    attempt = run['participants'][role].get('startup_attempt')
    return role + ('-' + attempt if attempt else '') + '-' + suffix


def retry(store, identity, task_id, text, *, api=None):
    """Claude has no thread queue: preserve the old actor and start a fresh attempt."""
    import copy
    from .mission_launch import main_session, source_current, owned_worktree, git, launch, clean_base
    if not text.strip(): raise RuntimeError('Follow-up text is required')
    with store.lock(identity):
        run = store.load(identity); main_session(run); source_current(run)
        if not enabled(run) or run['phase'] not in ('active', 'blocked') or run.get('operation'):
            raise RuntimeError('Fresh follow-up requires a settled launch')
        clean_base(run, run['brief'])
        task = run['tasks'][task_id]
        if task.get('delivery') != 'sent' or not task.get('attempt_id'):
            raise RuntimeError('Previous launch is uncertain; inspect its confirmed delivery first')
        path = owned_worktree(run, 'worker')
        if git(path, 'status', '--porcelain'): raise RuntimeError('Follow-up needs a clean committed worker checkpoint')
        head = git(path, 'rev-parse', 'HEAD')
        git(path, 'merge-base', '--is-ancestor', run['brief']['base_sha'], head)
        previous = copy.deepcopy(run)
        run['replacement_previous'] = previous
        run.setdefault('actor_history', []).append({'participants':copy.deepcopy(run['participants']),
            'resources':copy.deepcopy(run['resources']), 'tab':run.get('tab'), 'at':time.time()})
        for task in run['tasks'].values():
            task.setdefault('attempt_history', []).append(task['attempt_id'])
            for key in ('attempt_id', 'delivery', 'result', 'accepted_result', 'plan'): task.pop(key, None)
            task.update(state='ready', agent='main', summary='Preparing a fresh follow-up', updated=time.time())
        run.update(worker_head=head, clarification=text, participants={}, resources={}, phase='requested',
                   operation='replace fresh executor', qa=None, candidate=None,
                   result_version=run.get('result_version', 0)+1)
        run.pop('leader_review', None)
        store.save(run)
    try:
        return launch(store, identity, run['brief'], confirmed=True, api=api, replacement=True)
    except Exception as error:
        with store.lock(identity):
            current = store.load(identity)
            if current.get('operation') == 'replace fresh executor' and current.get('replacement_previous'):
                restored = current['replacement_previous']
                restored.setdefault('replacement_failures', []).append({'at':time.time(), 'reason':str(error)})
                store.save(restored)
        raise


def leader_ready(session):
    live = session.verify()
    if session.binding.kind == 'claude' and live.get('agent_status') not in ('idle', 'done'):
        raise RuntimeError('Claude leader is busy; wait until idle before dispatching')
    if session.binding.kind not in ('codex', 'claude'):
        raise RuntimeError('Unsupported leader provider')


def send_to_leader(session, message, *, receipt_required=False):
    """LU's idle Claude delivery; Codex continues using its exact-thread queue."""
    if session.binding.kind == 'claude':
        leader_ready(session)
        session.runtime.send(session.binding, message)
        return {'notification_method':'verified-idle-send'}
    receipt = session.runtime.queue(session.binding, message)
    if receipt_required: uuid.UUID(receipt)
    return {'receipt':receipt, 'notification_method':'queue'}
