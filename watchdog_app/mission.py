"""Mission Control's durable intent and evidence ledger (never edits TODO.md)."""
from contextlib import contextmanager
from dataclasses import asdict
import fcntl
import json
from pathlib import Path
import time
import uuid

from .store import atomic, state_root
from .todo import locked
from .mission_scope import capture, overlaps

LABELS = {'ready': 'Ready to start', 'working': 'Working', 'blocked': 'Needs help',
          'review': 'Checking the result', 'done': 'Done', 'unavailable': 'Unavailable',
          'closed': 'Closed'}
FINISHED = ('done', 'closed')
STALL_SECONDS = 20 * 60


def alive(pid):
    return bool(pid) and (Path('/proc') / str(pid)).exists()


def last_activity(run):
    stamps = [run.get('created', 0), run.get('monitor_updated', 0), run.get('observed', 0)]
    stamps += [t.get('updated', 0) for t in run['tasks'].values()]
    stamps += [e.get('received', 0) for e in (run.get('events') or {}).values()]
    return max(stamps)


def stalled(run, *, now=None):
    """A forgotten run: unfinished, no live monitor and no activity for a while."""
    if run['phase'] in FINISHED or run.get('operation'):
        return False
    if run['phase'] in ('active', 'blocked') and alive(run.get('monitor_pid')):
        return False
    now = time.time() if now is None else now
    return now - last_activity(run) > STALL_SECONDS


def accepted_in_todo(run, snapshot):
    """Every selected task now appears completed in TODO.md (the user's acceptance)."""
    done = {t.text for t in snapshot.tasks if t.done}
    return bool(run['tasks']) and all(t['title'] in done for t in run['tasks'].values())


def run_status(run, *, now=None):
    """One honest state for the whole run: label, detail, colour and section."""
    phase, tasks = run['phase'], list(run['tasks'].values())
    when = time.strftime('%H:%M', time.localtime(last_activity(run)))
    if phase == 'done':
        return dict(key='done', label='Done', detail='accepted', section='Done', color='done', finished=True)
    if phase == 'closed':
        return dict(key='closed', label='Closed', detail=run.get('closed', {}).get('reason', ''),
                    section=None, color='unavailable', finished=True)
    if phase in ('requested', 'launching') and stalled(run, now=now):
        return dict(key='stalled', label='Stalled', detail='no activity since ' + when +
                    ' · close it in Progress (x)', section='Blocked', color='blocked', finished=False)
    if phase == 'requested':
        detail = ('request not confirmed · inspect the main queue' if run.get('request_delivery') != 'sent'
                  else 'main is preparing the brief')
        return dict(key='preparing', label='Preparing', detail=detail, section='Next', color='ready', finished=False)
    if phase == 'launching':
        return dict(key='preparing', label='Preparing', detail='opening the team · ' + (run.get('operation') or ''),
                    section='Next', color='ready', finished=False)
    problem = run.get('reason') or run.get('monitor_problem')
    if phase == 'blocked' or any(t['state'] == 'blocked' for t in tasks):
        blocked = next((t['summary'] for t in tasks if t['state'] == 'blocked'), problem or '')
        return dict(key='decision', label='Needs your decision', detail=blocked[:160],
                    section='Blocked', color='blocked', finished=False)
    if stalled(run, now=now):
        return dict(key='stalled', label='Stalled', detail='no activity since ' + when +
                    ' · close it in Progress (x)', section='Blocked', color='blocked', finished=False)
    qa = run.get('qa') or {}
    if tasks and all(t['state'] in ('review', 'done') for t in tasks):
        if qa.get('verdict') == 'pass' and run.get('qa_finished'):
            return dict(key='decision', label='Waiting for approval', detail='QA passed ' +
                        str(run.get('candidate') or '')[:8], section='Blocked', color='review', finished=False)
        return dict(key='verifying', label='Verifying', detail='QA is checking the result',
                    section='In progress', color='review', finished=False)
    if problem:
        return dict(key='running', label='Running', detail='monitor: ' + problem[:140],
                    section='In progress', color='working', finished=False)
    return dict(key='running', label='Running', detail='last update ' + when,
                section='In progress', color='working', finished=False)


def close(store, identity, reason):
    """Retire a run without deleting evidence; finished runs never block new work."""
    with store.lock(identity):
        run = store.load(identity)
        if run['phase'] in FINISHED:
            return run
        now = time.time()
        run['closed'] = {'from_phase': run['phase'], 'reason': reason, 'at': now}
        run['phase'] = 'closed'
        for task in run['tasks'].values():
            if task['state'] != 'done':
                task.update(state='closed', summary='Run closed: ' + reason, updated=now)
        store.save(run)
        return run


def blocking(store, repo, scope, tasks, snapshot):
    """Split overlapping unfinished runs into settled (auto-closable) and live ones."""
    settle, live = [], []
    for previous in store.list(repo):
        if previous['phase'] in FINISHED or not overlaps(previous, scope, tasks):
            continue
        if accepted_in_todo(previous, snapshot):
            settle.append((previous, 'tasks were accepted as Done in TODO'))
        elif stalled(previous):
            settle.append((previous, 'stalled with no activity since ' +
                           time.strftime('%H:%M', time.localtime(last_activity(previous)))))
        else:
            live.append(previous)
    return settle, live


class SupersededReview(RuntimeError):
    """A finished review is retained as stale evidence, never approval."""


class RunStore:
    def __init__(self, root=None):
        self.root = Path(root) if root is not None else state_root() / 'runs'

    def path(self, identity):
        if str(uuid.UUID(identity)) != identity:
            raise RuntimeError('Invalid run identity')
        return self.root / (identity + '.json')

    def load(self, identity):
        return json.loads(self.path(identity).read_text())

    def save(self, run):
        atomic(self.path(run['id']), run)

    def list(self, repo):
        result = []
        for path in self.root.glob('*.json'):
            run = json.loads(path.read_text())
            if run['repo'] == str(Path(repo).resolve()):
                result.append(run)
        return sorted(result, key=lambda run: run['created'], reverse=True)

    @contextmanager
    def lock(self, identity):
        path = self.path(identity).with_suffix('.lock')
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with path.open('a') as stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise RuntimeError('This run is busy; wait for its current operation') from error
            yield


def request(session, snapshot, ids, *, confirmed=False, store=None, checkpoint=None):
    if not confirmed:
        raise RuntimeError('Explicit confirmation is required')
    store = store or RunStore()
    with session.routing(), locked(snapshot.repo):
        snapshot.assert_current()
        tasks = snapshot.selected(ids)
        scope = capture(snapshot, tasks)
        session.verify()
        if session.binding.kind != 'codex':
            raise RuntimeError('Orchestrate needs an exact Codex thread')
        settle, live = blocking(store, snapshot.repo, scope, tasks, snapshot)
        if live:
            raise RuntimeError('These tasks already have a running team ' + live[0]['id'][:8] +
                               '. Follow it in Progress, or close it there with x to start over.')
        for previous, reason in settle:
            close(store, previous['id'], reason)
        now = time.time()
        from .mission_native import boot_id
        run = {'transport': {'kind':'native','boot_id':boot_id()}, 'version': 1, 'id': str(uuid.uuid4()), 'repo': str(snapshot.repo),
               'created': now, 'main': asdict(session.binding), 'binding_file': str(session.file.resolve()),
               'source_digest': snapshot.digest, 'scope': scope, 'phase': 'requested', 'request_delivery': 'sending',
               'participants': {}, 'resources': {}, 'events': {}, 'cursor': 0, 'candidate': None, 'qa': None,
               'tasks': {t.id: {'title': t.text, 'state': 'ready', 'agent': 'main', 'updated': now,
                                'summary': 'Waiting for the main conversation to prepare the brief'} for t in tasks}}
        if checkpoint:
            run['checkpoint'] = checkpoint
        snapshot.assert_current()
        store.save(run)
        message = (f"Watchdog Mission Control run {run['id']} was explicitly confirmed.\n"
                   f"Project: {run['repo']}\nMain: {session.binding.session}\n"
                   + (f"Committed checkpoint (use as base_sha): {checkpoint['sha']}\n" if checkpoint else '') +
                   'Approved team: one new Codex worker and one new Codex QA, in one execution tab.\n'
                   'Prepare an explicit brief with allowed files, acceptance criteria, test commands, '
                   'dependencies, clean base SHA and the approved accounts/executable. '
                   'Use `watchdog mission template --run ' + run['id'] + '` for the JSON contract, '
                   'then `watchdog mission launch --run ' + run['id'] + ' --brief FILE --confirm`.\n'
                   'Coordinate; delegate implementation. No extra agents. Never merge or push by hand and never ask '
                   'the user to review branches: when QA passes, run the approve command Watchdog sends you; it merges '
                   'the approved work into the project branch and pushes it. '
                   'Dispatch does not complete TODO. Return compact results and concrete blockers.\n'
                   + '\n'.join(f"{t.id}: {t.text}" for t in tasks))
        try:
            session.runtime.queue(session.binding, message)
        except Exception as error:
            run['request_delivery'] = 'uncertain'
            run['reason'] = 'Coordination request delivery was not confirmed; inspect the exact main queue before recovery'
            store.save(run)
            raise RuntimeError(run['reason']) from error
        run['request_delivery'] = 'sent'
        store.save(run)
        return run


def require_summary(report):
    text = report.get('summary')
    if not isinstance(text, str) or not text.strip() or len(text) > 8000:
        raise RuntimeError('A concrete summary is required (up to 8000 characters)')


def accept_event(run, event, *, now=None):
    """Accept only a correlated, pinned peer's structured result, once."""
    event_id = event.get('id')
    if not event_id or event_id in run['events'] or event.get('event') != 'task':
        return False
    native = run.get('transport', {}).get('kind') == 'native'
    if native:
        role = event.get('role')
        part = run['participants'].get(role, {})
        if (event.get('transport') != 'native' or not part.get('enrolled') or
                event.get('actor') != part.get('native') or not part.get('generation') or
                event.get('generation') != part['generation']): return False
    else:
        role = next((role for role, p in run['participants'].items()
                     if p.get('pubkey') == event.get('pubkey') and p['nickname'] == event.get('author')), None)
    if role is None:
        return False
    native_id = event.get('task_id')
    task_id = next((key for key, task in run['tasks'].items() if task.get('attempt_id' if native else 'gossip_task') == native_id), None)
    qa_event = role == 'qa' and native_id == run.get('qa_task') and native_id is not None
    if not qa_event and (role != 'worker' or task_id is None):
        return False
    if event.get('kind') not in ('status-update', 'artifact', 'artifact-update'):
        return False
    body = event.get('body')
    if (event.get('kind') == 'status-update' and event.get('state') == 'working'
            and (body is None or isinstance(body,str) and not body.strip())):
        return False  # Normal transport acknowledgement, not implementation evidence.
    try:
        report = json.loads(event.get('body', ''))
    except (ValueError, TypeError) as error:
        raise RuntimeError('Expected a structured JSON report; completion was not inferred') from error
    if not isinstance(report, dict) or report.get('run_id') != run['id']:
        raise RuntimeError('Report run identity differs')
    require_summary(report)
    if native and (not native_id or report.get('attempt_id') != native_id or report.get('event_id') != event_id):
        raise RuntimeError('Native report attempt or event identity differs')
    now = time.time() if now is None else now
    if qa_event:
        contract = run.get('review_contract') or {}
        if not contract or report.get('review_id') != contract.get('id'):
            raise RuntimeError('QA report belongs to another review attempt')
        if report.get('candidate') != run.get('candidate'):
            raise RuntimeError('QA report does not match the exact candidate')
        if report.get('status') == 'qa':
            if report.get('verdict') not in ('pass', 'fail') or not report.get('tests'):
                raise RuntimeError('QA requires a verdict and test evidence')
        elif report.get('status') != 'blocked' and not (native and report.get('status') == 'working'):
            raise RuntimeError('QA reports must contain qa or blocked status')
        if contract.get('version') != run.get('result_version', 0):
            run['qa_finished'] = True
            raise SupersededReview('QA review was superseded by newer implementation evidence')
        if native and run.get('qa_finished'):
            raise RuntimeError('QA attempt is terminal; main must request a new review')
        if report.get('status') == 'qa':
            run['qa'] = report
        run['qa_finished'] = report.get('status') != 'working'
        for task in run['tasks'].values():
            if task['state'] != 'done':
                task.update(state='review' if report.get('verdict') == 'pass' or report.get('status') == 'working' else 'blocked',
                            summary=report['summary'], agent='qa', updated=now)
    else:
        if report.get('task_id') != task_id:
            raise RuntimeError('Report task identity differs')
        task = run['tasks'][task_id]
        status = report.get('status')
        if status not in ('working', 'blocked', 'result') or task['state'] == 'done':
            raise RuntimeError('Invalid task transition')
        if status == 'result':
            commits, tests = report.get('commits'), report.get('tests')
            if (not isinstance(commits, list) or not commits or
                    any(not isinstance(c, str) or len(c) != 40 or any(x not in '0123456789abcdef' for x in c) for c in commits)
                    or not isinstance(tests, list) or not tests or any(not isinstance(t, str) or not t.strip() for t in tests)):
                raise RuntimeError('Result requires ordered full commit SHAs and test evidence')
            task['result'] = report
            run['qa'] = None  # New implementation invalidates any older QA.
        run['result_version'] = run.get('result_version', 0) + 1
        task.pop('accepted_result', None)
        if status != 'result':
            task.pop('result', None)
            run['qa'] = None
        task.update(state={'result': 'review'}.get(status, status), summary=report['summary'],
                    agent='worker', updated=now)
    run.get('report_errors', {}).pop(native_id, None)
    run['events'][event_id] = {'report': report, 'delivery': 'pending', 'received': now}
    if native: run['events'][event_id].update(role=role, generation=event['generation'], actor=event['actor'])
    return True


def contact(run, live_keys, *, now=None):
    now = time.time() if now is None else now
    for participant in run['participants'].values():
        participant['available'] = participant.get('pubkey') in live_keys
        if participant['available']:
            participant['last_seen'] = now
    run['observed'] = now


def task_view(run, task_id, *, now=None):
    task = dict(run['tasks'][task_id])
    now = time.time() if now is None else now
    participant = run['participants'].get(task['agent'])
    unavailable = participant and (not participant.get('available', False) or now - run.get('observed', 0) > 45)
    state = 'unavailable' if unavailable and task['state'] != 'done' else task['state']
    task['label'] = LABELS[state]
    task['color'] = state
    if unavailable and task['state'] != 'done':
        task['summary'] = 'Contact unavailable; last report: ' + task.get('summary', '')
    return task


def finish(run, candidate, *, confirmed=False):
    if not confirmed:
        raise RuntimeError('Explicit approval is required')
    qa = run.get('qa') or {}
    contract = run.get('review_contract') or {}
    if (run.get('qa_finished') is not True or qa.get('status') != 'qa' or
            not contract.get('verified_commits') or
            contract.get('version') != run.get('result_version', 0) or
            qa.get('review_id') != contract.get('id') or
            contract.get('candidate') != candidate or run.get('candidate') != candidate or qa.get('candidate') != candidate or
            qa.get('verdict') != 'pass' or not qa.get('tests') or
            any(not t.get('result') or t['state'] != 'review' for t in run['tasks'].values())):
        raise RuntimeError('Completion requires every result and passing QA for this exact candidate')
    for task in run['tasks'].values():
        task.update(state='done', summary='QA passed; main approved ' + candidate, updated=time.time())
    run['phase'] = 'done'
