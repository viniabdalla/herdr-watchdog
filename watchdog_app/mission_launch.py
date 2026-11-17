"""Explicit-brief launcher. Persist intent before every external mutation; never retry."""
from dataclasses import asdict
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
import sys
import time

from .actions import Session
from .herdr import Herdr
from .store import atomic
from .todo import Snapshot

ROOT = Path(__file__).resolve().parents[1]


def command(argv, *, cwd=None, timeout=20, env=None):
    try:
        result = subprocess.run([str(a) for a in argv], cwd=cwd, env=env,
                                capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError('Command timed out; outcome is uncertain and was not retried') from error
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or 'Command failed')
    return result.stdout.strip()


def git(repo, *args):
    return command(['git', '-C', repo, *args],
                   env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')})


def main_session(run):
    session = Session(run['binding_file'], Path(run['repo']))
    if asdict(session.binding) != run['main']:
        raise RuntimeError('Main conversation identity changed; run was not redirected')
    session.verify()
    return session


def graph_read(args, repo=None):
    try:
        return command(['agent-graph','graph',*args],cwd=repo)
    except RuntimeError as error:
        if 'not found' not in str(error):
            raise
        return command(['agent-graph','graph',*args],cwd=Path.home())


def role_context(role, repo):
    return graph_read(['node-up','tropico-coding-team/' + role],repo)


def validate_brief(run, brief):
    if brief.get('run_id') != run['id'] or brief.get('repo') != run['repo']:
        raise RuntimeError('Brief run/project identity differs')
    if not re.fullmatch('[0-9a-f]{40}', brief.get('base_sha', '')):
        raise RuntimeError('Brief needs a full committed base SHA')
    if set(brief.get('participants', {})) != {'worker', 'qa'}:
        raise RuntimeError('Exactly one approved worker and QA are required')
    for participant in brief['participants'].values():
        for field in ('account', 'executable'):
            value = participant.get(field)
            if not isinstance(value, str) or not Path(value).is_absolute():
                raise RuntimeError('Participant ' + field + ' must be an explicit absolute path')
        if not Path(participant['account']).is_dir() or not os.access(participant['executable'], os.X_OK):
            raise RuntimeError('Approved account or executable is unavailable')
        if not isinstance(participant.get('model'), str) or not participant['model'].strip():
            raise RuntimeError('An explicit participant model is required')
        if participant.get('effort') not in ('low', 'medium', 'high', 'xhigh'):
            raise RuntimeError('An explicit reasoning effort is required: low, medium, high or xhigh')
    tasks = brief.get('tasks')
    if not isinstance(tasks, list) or len(tasks) != len(run['tasks']) or {t.get('id') for t in tasks} != set(run['tasks']):
        raise RuntimeError('Brief must cover exactly the confirmed task snapshot')
    dependencies = {}
    for task in tasks:
        for field in ('allowed_files', 'acceptance', 'tests'):
            values = task.get(field)
            if not isinstance(values, list) or not values or any(not isinstance(v,str) or not v.strip() for v in values):
                raise RuntimeError('Every task needs explicit ' + field)
        for value in task['allowed_files']:
            path = PurePosixPath(value)
            if path.is_absolute() or '..' in path.parts or value in ('.', '*', '**') or path.parts[0] == '.git':
                raise RuntimeError('Allowed files must be bounded paths relative to the project')
        deps = task.get('dependencies')
        if not isinstance(deps, list) or any(d not in run['tasks'] or d == task['id'] for d in deps):
            raise RuntimeError('Dependencies must name other selected tasks')
        dependencies[task['id']] = set(deps)
    visited = set()
    while len(visited) < len(tasks):
        ready = {key for key, deps in dependencies.items() if deps <= visited} - visited
        if not ready:
            raise RuntimeError('Dependency cycle in brief')
        visited.update(ready)


def source_current(run):
    if Snapshot.read(run['repo']).digest != run['source_digest']:
        raise RuntimeError('Task list changed; request a fresh contract')


def owned_worktree(run, role):
    part = run['participants'][role]
    path = Path(part['worktree'])
    if path.is_symlink() or str(path.resolve()) != str(path):
        raise RuntimeError('Owned worktree path changed')
    if git(path, 'rev-parse', '--show-toplevel') != str(path):
        raise RuntimeError('Owned worktree root changed')
    common = git(run['repo'], 'rev-parse', '--path-format=absolute', '--git-common-dir')
    if git(path, 'rev-parse', '--path-format=absolute', '--git-common-dir') != common:
        raise RuntimeError('Worktree no longer belongs to this repository')
    if 'branch' in part:
        expected = part['branch'] or 'HEAD'
        if git(path, 'rev-parse', '--abbrev-ref', 'HEAD') != expected:
            raise RuntimeError('Owned worktree branch changed')
    return path


def clean_base(run, brief):
    snapshot = Snapshot.read(run['repo'])
    if snapshot.digest != run['source_digest']:
        raise RuntimeError('Task list changed; request a fresh contract')
    snapshot.selected(run['tasks'])
    if git(run['repo'], 'status', '--porcelain'):
        raise RuntimeError('Launch requires a clean committed repository')
    if git(run['repo'], 'rev-parse', 'HEAD') != brief['base_sha']:
        raise RuntimeError('Repository no longer matches the approved base SHA')


def create_gossip(run, store):
    if 'graph' not in run:
        digest = graph_read(['hash','tropico-coding-team'],run.get('repo'))
        if not re.fullmatch('[0-9a-f]{64}',digest):
            raise RuntimeError('Agent Graph hash is unavailable')
        run['graph']={'name':'tropico-coding-team','hash':digest,'instance':run['id']}
    folder = store.root / run['id'];folder.mkdir(mode=0o700, exist_ok=True)
    path = folder / 'gossip.json'
    try:
        context = json.loads(command(['agent-gossip', 'context', 'show']))
    except RuntimeError as error:
        if 'no native task context;' not in str(error):
            raise
        context = None
    if context is not None:
        main = run['main']
        if (context.get('owner_pid') != main['pid'] or
                context.get('session_id') != main['session'] or
                str(context.get('owner_start')) != str(main['started'])):
            raise RuntimeError('Gossip context identity differs from the approved main')
        path = Path(context['state_file'])
        if not path.is_absolute():
            raise RuntimeError('Gossip context state path must be absolute')
    nick = 'wd-main-' + run['id'][:8]
    command(['agent-gossip', 'create', '--name', 'wd-' + run['id'][:8], '--nickname', nick,
             '--lookup', 'mdns', '--transport', 'udp', '--owner-pid', str(run['main']['pid']),
             '--state-file', path])
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            state = json.loads(path.read_text())
            if state.get('ready') and state.get('gossip'):
                run['transport']={'gossip': state['gossip'], 'nickname': nick, 'pubkey':state['pubkey']}
                from .mission_transport import publish_identity
                publish_identity(run,'leader')
                return run['transport']
        except (OSError, ValueError):
            pass
        time.sleep(.1)
    raise RuntimeError('Gossip startup was not confirmed; inspect the retained state file')


def start_monitor(run, store):
    folder = store.root / run['id']
    with (folder / 'monitor.log').open('a') as stream:
        proc = subprocess.Popen([sys.executable, str(ROOT/'watchdog'), 'mission', 'watch',
                                 '--run', run['id'], '--state-dir', str(store.root)],
                                stdin=subprocess.DEVNULL, stdout=stream, stderr=stream,
                                start_new_session=True)
    return proc.pid


def launch(store, identity, brief, *, confirmed=False, api=None):
    if not confirmed:
        raise RuntimeError('Explicit launch confirmation is required')
    with store.lock(identity):
        run = store.load(identity)
        if run['phase'] != 'requested' or run.get('operation'):
            raise RuntimeError('Run already launched or interrupted; inspect its retained resources')
        if run['request_delivery'] != 'sent':
            raise RuntimeError('Coordination request delivery is uncertain; inspect the exact main queue')
        main_session(run)
        validate_brief(run, brief)
        clean_base(run, brief)
        contexts = {r: role_context(r, run['repo']) for r in ('worker', 'qa')}
        api = api or Herdr(run.get('herdr_session'))
        run['brief'] = brief
        folder = store.root / identity;folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        def intent(operation):
            main_session(run)
            run['operation'] = operation
            store.save(run)
        try:
            run['phase'] = 'launching'
            for role in ('worker', 'qa'):
                branch = 'watchdog/' + identity + '/' + role
                worktree = folder / role
                run['participants'][role] = dict(brief['participants'][role],
                    worktree=str(worktree), branch=branch if role == 'worker' else None,
                    nickname='wd-' + role + '-' + identity[:8], role_context=contexts[role])
                intent('create ' + role + ' worktree')
                args = ['worktree', 'add'] + (['-b', branch] if role == 'worker' else ['--detach'])
                git(run['repo'], *args, str(worktree), brief['base_sha'])
                run['participants'][role]['base_sha'] = brief['base_sha']
                store.save(run)
            intent('create gossip')
            run['transport'] = create_gossip(run, store)
            intent('create execution tab')
            pane = api.call('tab', 'create', '--workspace', run['main']['workspace'], '--cwd',
                            run['participants']['worker']['worktree'], '--label',
                            'Watchdog run ' + identity[:8], '--no-focus')['root_pane']
            run['resources']['worker'] = pane
            run['tab'] = pane['tab_id'];store.save(run)
            intent('split execution tab')
            api.checked(pane)
            run['resources']['qa'] = api.call('pane', 'split', pane['pane_id'], '--direction', 'right',
                '--cwd', run['participants']['qa']['worktree'], '--no-focus')['pane']
            store.save(run)
            for role in ('worker', 'qa'):
                pane = run['resources'][role]
                api.checked(pane)
                info = api.call('pane','process-info','--pane',pane['pane_id'])['process_info']
                deadline = time.monotonic() + 1
                while any(p['pid'] != info['shell_pid'] for p in info['foreground_processes']) and time.monotonic() < deadline:
                    time.sleep(.05)
                    info = api.call('pane','process-info','--pane',pane['pane_id'])['process_info']
                if any(p['pid'] != info['shell_pid'] for p in info['foreground_processes']):
                    raise RuntimeError('Owned execution pane is busy; nothing was overwritten')
                api.call('pane', 'rename', pane['pane_id'], 'Watchdog ' + role.upper())
                intent('start ' + role)
                argv = [sys.executable, str(ROOT/'watchdog'), 'mission', 'participant',
                        '--run', identity, '--role', role, '--state-dir', str(store.root)]
                api.call('pane', 'run', pane['pane_id'], shlex.join(argv))
            run['phase'] = 'active';run['operation'] = 'start monitor';store.save(run)
            run['monitor_pid'] = start_monitor(run, store)
            run['operation'] = None;store.save(run)
            return run
        except Exception as error:
            run['phase'] = 'blocked';run['reason'] = str(error)
            for task in run['tasks'].values():
                task.update(state='blocked', summary=str(error), updated=time.time())
            store.save(run)
            raise


def open_run(run, api=None):
    if not run.get('tab') or set(run['resources']) != {'worker', 'qa'}:
        raise RuntimeError('Execution tab has not been created completely')
    api = api or Herdr(run.get('herdr_session'))
    for pane in run['resources'].values():
        live = api.checked(pane)
        if live['tab_id'] != run['tab'] or live['workspace_id'] != run['main']['workspace']:
            raise RuntimeError('Execution pane moved; refusing to focus an unrelated tab')
    return api.call('tab', 'focus', run['tab'])


def participant(store, identity, role):
    run = store.load(identity);part = run['participants'][role]
    pane = run['resources'][role]
    if os.environ.get('HERDR_PANE_ID') != pane['pane_id']:
        raise RuntimeError('Participant started in the wrong pane')
    Herdr(run.get('herdr_session')).checked(pane)
    marker = store.root / identity / (role + '-started.json')
    try:
        with marker.open('x') as stream:
            json.dump({'pane': pane, 'pid': os.getpid(), 'started': time.time()}, stream)
    except FileExistsError as error:
        raise RuntimeError('Participant launch already attempted; inspect its owned pane before recovery') from error
    transport = run['transport']
    # Join is owned by this wrapper. It remains alive while the Codex child runs.
    command(['agent-gossip', 'join', transport['gossip'], '--nickname', part['nickname'],
             '--owner-pid', str(os.getpid()), '--state-file',
             str(store.root / identity / (role + '-gossip.json'))])
    prompt = (part['role_context'] + '\n\nWatchdog Mission Control participant. '
        'Only the main conversation talks to the user. No extra agents, main merges, pushes, '
        'global config edits or server stops. Poll Gossip for your directed assignment before doing work. '
        'Use --long --max-secs 40, never --bell. Keep the same Gossip task ID on follow-ups. '
        'No source changes before receiving a task. Return structured JSON via the Watchdog report command.\n'
        'Always use the absolute controller report command below; it receives fixes independently of your assigned checkout.\n'
        f"Run: {identity}\nRole: {role}\nWorktree: {part['worktree']}\n"
        f"Graph identity: {json.dumps(run.get('graph',{}))}\n"
        'Watchdog publishes your graph entry only after verifying your native account/thread and Gossip key.\n'
        f"Poll: agent-gossip poll --gossip {transport['gossip']} --nickname {part['nickname']}\n"
        f"Report: {shlex.join([sys.executable, str(ROOT/'watchdog'), 'mission', 'report', '--run', identity, '--role', role, '--state-dir', str(store.root), '--file', 'REPORT.json'])}\n"
        'Report schema will be included with the assignment. The launcher is not a planner. '
        'Do not contact or recruit unrelated peers. Do not close a task before main approves it.')
    env = {k:v for k,v in os.environ.items() if not k.startswith(('CODEX_', 'AI_MEMORY_', 'OPENAI_', 'ANTHROPIC_', 'CLAUDE_CODE_')) and k != 'CLAUDECODE'}
    env['CODEX_HOME'] = part['account']
    runtime_dir = '/tmp/agent-gossip-' + str(os.getuid())
    argv = [part['executable'], '-C', part['worktree'], '--model', part['model'],
            '--sandbox', 'workspace-write', '--ask-for-approval', 'never', '--add-dir', runtime_dir,
            '--add-dir', str(store.root), '--add-dir', git(run['repo'], 'rev-parse', '--path-format=absolute', '--git-common-dir'),
            '-c', 'sandbox_workspace_write.network_access=true',
            '-c', 'model_reasoning_effort=' + json.dumps(part['effort']), prompt]
    child = subprocess.Popen(argv, env=env)
    try:
        return child.wait()
    finally:
        # Do not infer success from exit and never kill another process.
        atomic(store.root / identity / (role + '-exit.json'),
               {'code': child.returncode, 'at': time.time()})
