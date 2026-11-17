"""Directed Gossip assignments and compact, exact-thread returns."""
from dataclasses import asdict
import json
from pathlib import Path
import time
import uuid

from . import bindings
from .mission import accept_event, contact
from .mission_launch import command, git, main_session, source_current, owned_worktree


class Gossip:
    def __init__(self, transport, nickname=None):
        self.room = transport['gossip']
        self.nickname = nickname or transport['nickname']

    def invoke(self, *args):
        return command(['agent-gossip', *args, '--gossip', self.room, '--nickname', self.nickname], timeout=15)

    def peers(self):
        return json.loads(self.invoke('peers'))['peers']

    def poll(self, after):
        return json.loads(self.invoke('poll', '--after', str(after)))

    def call(self, peer, text, *, task_id=None, label='Watchdog task', expected_key=None):
        if expected_key is not None:
            matches = [p for p in self.peers() if p['nickname'] == peer]
            if len(matches) != 1 or matches[0]['pubkey'] != expected_key or matches[0].get('quiet'):
                raise RuntimeError('Gossip recipient identity changed or is ambiguous')
        args = ['a2a','call','--to',peer,'--text',text,'--timeout-secs','10','--label',label]
        if task_id:
            args += ['--task-id', task_id]
        value = json.loads(self.invoke(*args))
        try:
            returned = value['result']['task']['id']
            uuid.UUID(returned)
        except (KeyError, ValueError, TypeError) as error:
            raise RuntimeError('Gossip task receipt is missing or malformed; delivery is uncertain') from error
        if task_id and returned != task_id:
            raise RuntimeError('Gossip returned a different task identity')
        return returned


def verify_participant(run, role):
    part = run['participants'][role]
    native = part.get('native')
    if not native or not part.get('pubkey') or not part.get('available'):
        raise RuntimeError(role + ' native identity or Gossip contact is unavailable')
    runtime = bindings.engine()
    binding = runtime.Binding(**native)
    runtime.verify(binding)
    if (binding.account != part['account'] or binding.pane != run['resources'][role]['pane_id'] or
            binding.terminal != run['resources'][role]['terminal_id']):
        raise RuntimeError(role + ' identity changed')
    return binding


def register(run, store, peers):
    """Pin only peers launched by this run, matched to their owned native terminal."""
    for role, part in run['participants'].items():
        exit_file = store.root / run['id'] / (role + '-exit.json')
        if exit_file.exists():
            part['exit'] = json.loads(exit_file.read_text())
            part['available'] = False
            part['problem'] = 'Participant exited; completion was not inferred'
            continue
        if part.get('native'):
            try:
                verify_participant(run, role)
            except RuntimeError as error:
                part['available'] = False;part['problem'] = str(error)
            continue
        try:
            state = json.loads((store.root/run['id']/(role+'-gossip.json')).read_text())
            if state.get('nickname') != part['nickname'] or state.get('gossip') != run['transport']['gossip']:
                raise RuntimeError('Participant Gossip identity differs')
            peer = next(p for p in peers if p['pubkey'] == state['pubkey'] and p['nickname'] == part['nickname'])
            candidates, _ = bindings.discover(Path(part['worktree']))
            matching = [b for b in candidates if b.kind == 'codex' and b.account == part['account'] and
                        b.pane == run['resources'][role]['pane_id'] and b.terminal == run['resources'][role]['terminal_id']]
            if len(matching) != 1:
                raise RuntimeError('Native account/thread registration is unavailable or ambiguous')
            bindings.verify(matching[0])
            part.update(native=asdict(matching[0]), pubkey=peer['pubkey'], available=True)
            part.pop('problem',None)
        except (OSError, ValueError, KeyError, StopIteration, RuntimeError) as error:
            part['problem'] = str(error) or 'Waiting for the owned Gossip peer'
            part['available'] = False


def assignment(run, task_id):
    contract = next(t for t in run['brief']['tasks'] if t['id'] == task_id)
    part = run['participants']['worker']
    return json.dumps({'run_id': run['id'], 'task_id': task_id, 'title': run['tasks'][task_id]['title'],
        'repo':run['repo'], 'worktree':part['worktree'], 'base_sha':part.get('base_sha',run['brief']['base_sha']),
        **contract, 'return_to': {'main':run['main'] if 'main' in run else {}, 'gossip':run['transport']},
        'instructions':'Implement only this contract. Report concrete blockers. Return ordered commit SHAs and tests. '
            'No additional agents, global changes, target branch merges or pushes. Keep task ID for follow-ups. '
            'Result waits for independent QA and main approval; TODO remains unchanged.',
        'report_schema':{'run_id':run['id'],'task_id':task_id,'status':'working | blocked | result',
                         'summary':'Concrete progress or blocker','commits':['40-character SHA for result'],
                         'tests':['command and result for result']}})


def dispatch(store, identity, task_id):
    with store.lock(identity):
        run=store.load(identity);main_session(run);source_current(run)
        if run['phase'] != 'active':raise RuntimeError('Run is not active')
        task=run['tasks'][task_id]
        if task.get('delivery') or task.get('gossip_task'):
            raise RuntimeError('Assignment already sent or uncertain; inspect it and use followup')
        contract=next(t for t in run['brief']['tasks'] if t['id']==task_id)
        if any(not run['tasks'][key].get('accepted_result') for key in contract['dependencies']):
            raise RuntimeError('Task dependencies need reviewed results accepted by main')
        if any(other.get('gossip_task') and not other.get('accepted_result') for key,other in run['tasks'].items() if key!=task_id):
            raise RuntimeError('The worker already has an assignment awaiting main review')
        verify_participant(run,'worker')
        part=run['participants']['worker']
        owned_worktree(run,'worker')
        if git(part['worktree'],'status','--porcelain'):
            raise RuntimeError('Worker worktree must be clean before a new contract')
        head=git(part['worktree'],'rev-parse','HEAD')
        if head != run.get('worker_head',run['brief']['base_sha']):
            raise RuntimeError('Worker base changed outside the accepted contract')
        part['base_sha']=head
        task['delivery']='sending';store.save(run)
        try:
            task['gossip_task']=Gossip(run['transport']).call(part['nickname'],assignment(run,task_id),label=task['title'][:100], expected_key=part['pubkey'])
        except Exception as error:
            task.update(delivery='uncertain',state='blocked',summary=str(error),agent='worker',updated=time.time())
            store.save(run);raise
        task.update(delivery='sent',state='working',agent='worker',summary='Assignment delivered',updated=time.time())
        store.save(run)
        return run


def followup(store, identity, task_id, text):
    if not text.strip():raise RuntimeError('Follow-up text is required')
    with store.lock(identity):
        run=store.load(identity);main_session(run);source_current(run);verify_participant(run,'worker')
        owned_worktree(run,'worker')
        task=run['tasks'][task_id]
        if not task.get('gossip_task') or task['state']=='done':raise RuntimeError('No active correlated task')
        if task.get('followup_delivery') in ('sending','uncertain'):
            raise RuntimeError('Previous follow-up is uncertain; inspect the peer before any retry')
        task['followup_delivery']='sending';store.save(run)
        try:
            Gossip(run['transport']).call(run['participants']['worker']['nickname'],
                json.dumps({'run_id':identity,'task_id':task_id,'clarification':text,
                            'contract':assignment(run,task_id),'scope_change_allowed':False}),task_id=task['gossip_task'],expected_key=run['participants']['worker']['pubkey'])
        except Exception:
            task['followup_delivery']='uncertain';store.save(run);raise
        task.update(followup_delivery='sent',state='working',summary=text,updated=time.time())
        task.pop('accepted_result',None);task.pop('result',None);run['qa']=None
        store.save(run)
        return run


def forward(store, run):
    for event_id, event in run['events'].items():
        if event['delivery'] != 'pending':continue
        session=main_session(run)
        event['delivery']='sending';store.save(run)
        message = ('Watchdog run '+run['id']+' event '+event_id+'\n'+
                   json.dumps(event['report'],ensure_ascii=False)+'\n'
                   'Result is evidence awaiting review. Use mission inspect for owned resources. '
                   'TODO was not changed. Keep follow-ups on the same run/task IDs.')
        try:
            session.runtime.queue(session.binding,message)
        except Exception:
            event['delivery']='uncertain';store.save(run)
            raise RuntimeError('Main summary delivery is uncertain; it was not resent')
        event['delivery']='sent';store.save(run)


def tick(store, identity):
    with store.lock(identity):
        run=store.load(identity)
        if run['phase'] not in ('active','blocked'):return run
        main_session(run)
        gossip=Gossip(run['transport']);peers=gossip.peers()
        run.pop('monitor_problem',None)
        contact(run,{p['pubkey'] for p in peers if not p.get('quiet')})
        register(run,store,peers)
        for event in gossip.poll(run.get('cursor',0)):
            try:
                accept_event(run,event)
            except RuntimeError as error:
                # A correlated malformed report stays visible and cannot imply completion.
                run['reason']=str(error)
                run['events'][event['id']]={'delivery':'pending','received':time.time(),
                    'report':{'status':'blocked','summary':str(error),'task_id':event.get('task_id')}}
            run['cursor']=max(run.get('cursor',0),event.get('seq',0))
        run['monitor_updated']=time.time();store.save(run)
        forward(store,run)
        return run


def review(store, identity, candidate):
    with store.lock(identity):
        run=store.load(identity);main_session(run);source_current(run);verify_participant(run,'qa')
        owned_worktree(run,'qa')
        if run.get('qa_task') and run.get('qa_delivery') == 'sent' and not run.get('qa_finished'):
            raise RuntimeError('QA review is still in progress; wait for its result or blocker')
        if any(not t.get('result') or t['state'] not in ('review','blocked') for t in run['tasks'].values()):
            raise RuntimeError('Every selected task needs implementation evidence before QA')
        resolved=git(run['repo'],'rev-parse',candidate+'^{commit}')
        if resolved != candidate:raise RuntimeError('QA requires the full exact candidate SHA')
        if run.get('qa_delivery') in ('sending','uncertain'):
            raise RuntimeError('QA assignment delivery is uncertain; inspect it before retrying')
        part=run['participants']['qa']
        if git(part['worktree'],'status','--porcelain'):
            raise RuntimeError('QA worktree is not clean')
        run['operation']='checkout QA candidate';store.save(run)
        git(part['worktree'],'checkout','--detach',candidate)
        run['candidate']=candidate;run['qa']=None;run['qa_finished']=False;run['qa_delivery']='sending';store.save(run)
        text=json.dumps({'run_id':identity,'candidate':candidate,'repo':run['repo'],'worktree':part['worktree'],
            'tasks':run['brief']['tasks'],'results':{k:t['result'] for k,t in run['tasks'].items()},
            'instructions':'Review the complete integrated candidate at exactly this SHA. Do not write source. '
                'Use owned wd-test resources only. Return reproducible findings and independent evidence.',
            'report_schema':{'run_id':identity,'status':'qa','candidate':candidate,'verdict':'pass | fail',
                             'summary':'Findings and limitations','tests':['command and observed result']}})
        try:
            run['qa_task']=Gossip(run['transport']).call(part['nickname'],text,task_id=run.get('qa_task'),label='Check integrated result',expected_key=part['pubkey'])
        except Exception:
            run['qa_delivery']='uncertain';store.save(run);raise
        run['qa_delivery']='sent';run['operation']=None
        for task in run['tasks'].values():task.update(state='review',agent='qa',updated=time.time(),summary='QA is checking '+candidate)
        store.save(run)
        return run


def report(store, identity, role, data):
    run=store.load(identity)
    native=verify_participant(run,role)
    if data.get('run_id') != identity:raise RuntimeError('Report belongs to another run')
    part=run['participants'][role]
    from .mission import require_summary
    require_summary(data)
    if role=='qa':
        task_id=run.get('qa_task')
    else:
        task_id=run['tasks'][data['task_id']].get('gossip_task')
    if not task_id:raise RuntimeError('No correlated Gossip assignment')
    # Validate the report using exactly the receiving reducer before sending it.
    trial=json.loads(json.dumps(run))
    event={'id':str(uuid.uuid4()),'event':'task','kind':'artifact','author':part['nickname'],
           'pubkey':part['pubkey'],'task_id':task_id,'body':json.dumps(data)}
    if not accept_event(trial,event):raise RuntimeError('Report did not match the assignment')
    args=['a2a','artifact'] if data['status'] in ('result','qa') else ['a2a','status','--state','input-required' if data['status']=='blocked' else 'working']
    return Gossip(run['transport'],part['nickname']).invoke(*args,'--task-id',task_id,'--text',json.dumps(data))
