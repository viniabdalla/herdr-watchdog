"""Directed Gossip assignments and compact, exact-thread returns."""
from dataclasses import asdict
import json
import socket
from pathlib import Path
import time
import uuid

from . import bindings
from . import mission_native as native_backend
from .mission import accept_event, contact, SupersededReview
from .mission_launch import command, git, main_session, source_current, owned_worktree, ROOT
import shlex
import sys


class Gossip:
    def __init__(self, transport, nickname=None, *, session_context=None):
        self.room = transport['gossip']
        self.nickname = nickname or transport['nickname']
        self.session_context = session_context

    def invoke(self, *args):
        argv=['agent-gossip', *args, '--gossip', self.room, '--nickname', self.nickname]
        if self.session_context:argv += ['--session-context',self.session_context]
        return command(argv, timeout=15)

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


def publish_identity(run, role):
    graph = run['graph']
    leader = role == 'leader'
    part = run['transport'] if leader else run['participants'][role]
    native = run['main'] if leader else part['native']
    entry = {'instance':graph['instance'],'graph':graph['name'],'hash':graph['hash'],
             'node':role,'nickname':part['nickname'],'joined_at':int(time.time()),
             'host':socket.gethostname(),'harness':'Codex','status':'busy','native':native,
             'cwd':run.get('repo') if leader else part['worktree']}
    if leader:
        entry['leader']=True
    else:
        entry.update(invited_by=run['transport']['nickname'],model=part['model'],effort=part['effort'])
    gossip=Gossip(run['transport'],part['nickname'],session_context=part.get('gossip_context'))
    gossip.invoke('meta','merge','--merge',json.dumps(entry))
    document=json.loads(gossip.invoke('meta','get'))
    actual=document['document'].get(part['pubkey'],{})
    if any(actual.get(key)!=value for key,value in entry.items()):
        raise RuntimeError('Published graph identity did not match the pinned Gossip key')


def verify_graph(run, role, *, gossip=None):
    part=run['participants'][role]
    meta=json.loads((gossip or Gossip(run['transport'])).invoke('meta','get'))
    graph=run['graph'];absent=set(meta['absent'])
    live={key:value for key,value in meta['document'].items() if key not in absent and
          value.get('instance')==graph['instance'] and value.get('hash')==graph['hash']}
    leaders=[key for key,value in live.items() if value.get('leader') is True]
    if leaders != [run['transport']['pubkey']]:
        raise RuntimeError('Graph must have exactly one live approved leader')
    for key,node,native,nickname in ((run['transport']['pubkey'],'leader',run['main'],run['transport']['nickname']),
                                    (part['pubkey'],role,part['native'],part['nickname'])):
        entry=live.get(key,{})
        if (entry.get('node')!=node or entry.get('native')!=native or entry.get('nickname')!=nickname or
                entry.get('graph')!=graph['name']):
            raise RuntimeError('Graph role/native identity changed')
    if live[part['pubkey']].get('leader'):
        raise RuntimeError('Participant cannot appoint itself leader')


def verify_participant(run, role):
    if native_backend.enabled(run): return native_backend.verify_participant(run, role)
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
    verify_graph(run,role)
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
                part.pop('problem',None)
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
            proof_file=store.root/run['id']/(role+'-identity.json')
            if proof_file.exists():
                from .mission_identity import check_context
                proof=json.loads(proof_file.read_text())
                if proof['native']!=asdict(matching[0]) or proof['pubkey']!=peer['pubkey']:
                    raise RuntimeError('Participant bootstrap identity changed')
                check_context(proof['context'],proof['native'])
                expected={k:proof['context'][k] for k in ('session_id','generation','owner_pid','owner_start','boot_id')}
                if state.get('session_context')!=expected:
                    raise RuntimeError('Participant peer is not bound to its verified native context')
            elif run.get('identity_protocol')==2:
                raise RuntimeError('Waiting for native participant bootstrap and self-enrollment')
            part.update(native=asdict(matching[0]), pubkey=peer['pubkey'], available=True)
            if proof_file.exists():part['gossip_context']=proof['context']['context_file']
            verify_graph(run,role)
            part.pop('problem',None)
        except (OSError, ValueError, KeyError, StopIteration, RuntimeError) as error:
            part.pop('native',None)
            part.pop('pubkey',None)
            part['problem'] = str(error) or 'Waiting for the owned Gossip peer'
            part['available'] = False


def assignment(run, task_id):
    contract = next(t for t in run['brief']['tasks'] if t['id'] == task_id)
    part = run['participants']['worker']
    return json.dumps({'run_id': run['id'], 'task_id': task_id, 'title': run['tasks'][task_id]['title'],
        'repo':run['repo'], 'worktree':part['worktree'], 'base_sha':part.get('base_sha',run['brief']['base_sha']),
        **contract, 'return_to': {'main':run.get('main',{}), ('transport' if native_backend.enabled(run) else 'gossip'):run['transport']},
        'instructions':'Implement only this contract. Report concrete blockers. Return ordered commit SHAs and tests. '
            'No additional agents, global changes, target branch merges or pushes. Keep task ID for follow-ups. '
            'Result waits for independent QA and main approval; TODO remains unchanged.',
        'report_schema':{'run_id':run['id'],'task_id':task_id,'status':'working | blocked | result',
                         'summary':'Concrete progress or blocker','commits':['40-character SHA for result'],
                         'tests':['command and result for result']}})


def wake_participant(store, run, role, task_id, sent):
    """Queue one poll-only notice after Gossip delivery, with durable uncertainty."""
    wakes=run.setdefault('wakes',{})
    if sent.get('wake_id'):
        previous=wakes[sent['wake_id']]
        if previous['delivery']=='queued':return previous
        raise RuntimeError('Agent notification '+previous['delivery']+'; inspect the exact queue before retrying')
    identity=str(uuid.uuid4());sent['wake_id']=identity
    wake={'role':role,'task_id':task_id,'delivery':'pending','created':time.time(),
          'recipient':run['participants'][role].get('native')}
    wakes[identity]=wake;store.save(run)
    try:
        main_session(run)
        native=verify_participant(run,role)
        if native.kind!='codex':raise RuntimeError('Agent notification requires a Codex participant')
        uuid.UUID(native.session)
        wake['recipient']=asdict(native)
        message=(f"Watchdog coordination for run {run['id']}, existing Gossip task {task_id}. "
            f"Poll via {shlex.join([sys.executable,str(ROOT/'watchdog'),'mission','receive','--run',run['id'],'--role',role,'--state-dir',str(store.root)])}. "
            'Read only new messages on that existing task. If the poll is empty or a message was already handled, '
            'do not repeat implementation or review. This notification is not another task; the contract remains in Gossip.')
        wake.update(delivery='sending',updated=time.time());store.save(run)
        receipt=bindings.engine().queue(native,message)
        uuid.UUID(receipt)
        wake.update(delivery='queued',receipt=receipt,updated=time.time());store.save(run)
        return wake
    except Exception as error:
        if wake['delivery']=='sending':wake['delivery']='uncertain'
        wake.update(problem=str(error),updated=time.time())
        for task in run['tasks'].values():
            if role=='qa' or task.get('gossip_task')==task_id:
                task.update(state='blocked',summary='Message delivered; agent notification needs attention',updated=time.time())
        store.save(run)
        raise RuntimeError('Agent notification '+wake['delivery']+'; inspect the exact queue before retrying: '+str(error)) from error


def dispatch(store, identity, task_id):
    if native_backend.enabled(store.load(identity)): return native_backend.dispatch(store, identity, task_id)
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
        wake_participant(store,run,'worker',task['gossip_task'],task)
        return run


def followup(store, identity, task_id, text):
    if native_backend.enabled(store.load(identity)): return native_backend.followup(store, identity, task_id, text)
    if not text.strip():raise RuntimeError('Follow-up text is required')
    with store.lock(identity):
        run=store.load(identity);main_session(run);source_current(run);verify_participant(run,'worker')
        owned_worktree(run,'worker')
        task=run['tasks'][task_id]
        if not task.get('gossip_task') or task['state']=='done':raise RuntimeError('No active correlated task')
        if task.get('followup_delivery') in ('sending','uncertain'):
            raise RuntimeError('Previous follow-up is uncertain; inspect the peer before any retry')
        prior=[task,*task.get('guidance',[])]
        if any(record.get('wake_id') and run['wakes'][record['wake_id']]['delivery']!='queued' for record in prior):
            raise RuntimeError('Previous agent notification is unconfirmed; inspect the exact queue before another follow-up')
        guidance={'text':text,'task_id':task['gossip_task'],'created':time.time(),'delivery':'sending'}
        task.setdefault('guidance',[]).append(guidance)
        task['followup_delivery']='sending';store.save(run)
        try:
            Gossip(run['transport']).call(run['participants']['worker']['nickname'],
                json.dumps({'run_id':identity,'task_id':task_id,'clarification':text,
                            'contract':assignment(run,task_id),'scope_change_allowed':False}),task_id=task['gossip_task'],expected_key=run['participants']['worker']['pubkey'])
        except Exception:
            guidance.update(delivery='uncertain',updated=time.time())
            task['followup_delivery']='uncertain';store.save(run);raise
        guidance.update(delivery='sent',updated=time.time())
        task.update(followup_delivery='sent',state='working',summary='Guidance sent; waiting for the agent',updated=time.time())
        task.pop('accepted_result',None);task.pop('result',None);run['qa']=None
        run['result_version']=run.get('result_version',0)+1
        store.save(run)
        wake_participant(store,run,'worker',task['gossip_task'],guidance)
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
    if native_backend.enabled(store.load(identity)): return native_backend.tick(store, identity)
    with store.lock(identity):
        run=store.load(identity)
        if run['phase'] not in ('active','blocked'):return run
        main_session(run)
        source_current(run)
        gossip=Gossip(run['transport']);peers=gossip.peers()
        run.pop('monitor_problem',None)
        contact(run,{p['pubkey'] for p in peers if not p.get('quiet')})
        register(run,store,peers)
        for event in gossip.poll(run.get('cursor',0)):
            try:
                body=event.get('body')
                acknowledgement=(event.get('kind')=='status-update' and event.get('state')=='working' and
                    (body is None or isinstance(body,str) and not body.strip()))
                owner=next(((role,p) for role,p in run['participants'].items() if
                    p.get('pubkey')==event.get('pubkey') and p['nickname']==event.get('author')),None)
                correlated=(event.get('task_id') is not None and
                    (owner and owner[0]=='qa' and event.get('task_id')==run.get('qa_task') or
                     owner and owner[0]=='worker' and any(t.get('gossip_task')==event.get('task_id') for t in run['tasks'].values())))
                if (event.get('event')=='task' and event.get('kind') in ('status-update','artifact','artifact-update')
                        and correlated and not acknowledgement and
                        (not owner[1].get('native') or not owner[1].get('available'))):
                    raise RuntimeError('Participant native identity or contact unavailable; report retained for inspection')
                accept_event(run,event)
            except RuntimeError as error:
                # A correlated malformed report stays visible and cannot imply completion.
                run.setdefault('report_errors',{})[event.get('task_id','unknown')]=str(error)
                run['events'][event['id']]={'delivery':'pending','received':time.time(),
                    'rejected':{key:event.get(key) for key in ('author','pubkey','task_id','body')},
                    'report':{'status':'blocked','summary':str(error),'task_id':event.get('task_id')}}
            run['cursor']=max(run.get('cursor',0),event.get('seq',0))
        run['monitor_updated']=time.time();store.save(run)
        forward(store,run)
        return run


def verify_result_commits(run, candidate):
    """Require each reported change in the candidate, allowing clean cherry-picks."""
    repo = run['repo']
    if git(repo,'merge-base',run['brief']['base_sha'],candidate) != run['brief']['base_sha']:
        raise RuntimeError('Candidate does not contain the approved base')
    for task in run['tasks'].values():
        for sha in task['result']['commits']:
            if git(repo,'merge-base',sha,candidate) == sha:
                continue
            parents = git(repo,'rev-list','--parents','-n','1',sha).split()
            if len(parents) != 2:
                raise RuntimeError('Candidate does not contain the reported merge/root commit ' + sha)
            equivalent = git(repo,'cherry',candidate,sha,parents[1]).splitlines()
            if equivalent != ['- ' + sha]:
                raise RuntimeError('Candidate does not contain worker result commit ' + sha)


def review(store, identity, candidate, context=None):
    if native_backend.enabled(store.load(identity)): return native_backend.review(store, identity, candidate, context)
    with store.lock(identity):
        run=store.load(identity);main_session(run);source_current(run);verify_participant(run,'qa')
        owned_worktree(run,'qa')
        if run.get('qa_task') and run.get('qa_delivery') == 'sent' and not run.get('qa_finished'):
            raise RuntimeError('QA review is still in progress; wait for its result or blocker')
        if any(not t.get('result') or t['state'] not in ('review','blocked') for t in run['tasks'].values()):
            raise RuntimeError('Every selected task needs implementation evidence before QA')
        resolved=git(run['repo'],'rev-parse',candidate+'^{commit}')
        if resolved != candidate:raise RuntimeError('QA requires the full exact candidate SHA')
        verify_result_commits(run,candidate)
        if run.get('qa_delivery') in ('sending','uncertain'):
            raise RuntimeError('QA assignment delivery is uncertain; inspect it before retrying')
        part=run['participants']['qa']
        if git(part['worktree'],'status','--porcelain'):
            raise RuntimeError('QA worktree is not clean')
        run['operation']='checkout QA candidate';store.save(run)
        git(part['worktree'],'checkout','--detach',candidate)
        run['candidate']=candidate;run['qa']=None;run['qa_finished']=False;run['qa_delivery']='sending'
        run['review_contract']={'id':str(uuid.uuid4()),'candidate':candidate,
            'base_sha':run['brief']['base_sha'],'context':context,
            'version':run.get('result_version',0),'verified_commits':True}
        store.save(run)
        text=json.dumps({'run_id':identity,'review_id':run['review_contract']['id'],'candidate':candidate,
            'base_sha':run['brief']['base_sha'],'context':context,'repo':run['repo'],'worktree':part['worktree'],
            'tasks':run['brief']['tasks'],'results':{k:t['result'] for k,t in run['tasks'].items()},
            'instructions':'Review the complete integrated candidate at exactly this SHA. Do not write source. '
                'Use owned wd-test resources only. Return reproducible findings and independent evidence.',
            'report_schema':{'run_id':identity,'review_id':run['review_contract']['id'],'status':'qa','candidate':candidate,'verdict':'pass | fail',
                             'summary':'Findings and limitations','tests':['command and observed result']}})
        try:
            run['qa_task']=Gossip(run['transport']).call(part['nickname'],text,task_id=run.get('qa_task'),label='Check integrated result',expected_key=part['pubkey'])
        except Exception:
            run['qa_delivery']='uncertain';store.save(run);raise
        run['qa_delivery']='sent';run['operation']=None
        for task in run['tasks'].values():task.update(state='review',agent='qa',updated=time.time(),summary='QA is checking '+candidate)
        store.save(run)
        wake_participant(store,run,'qa',run['qa_task'],run['review_contract'])
        return run


def verify_publisher(store, run, role):
    """Verify the local Gossip signer; only the receiving host checks native PIDs."""
    part=run['participants'][role]
    if not part.get('pubkey') or not part.get('native'):
        raise RuntimeError('Publisher has no registered participant identity')
    state=json.loads((store.root/run['id']/(role+'-gossip.json')).read_text())
    if (state.get('gossip')!=run['transport']['gossip'] or state.get('nickname')!=part['nickname'] or
            state.get('pubkey')!=part['pubkey']):
        raise RuntimeError('Publisher local Gossip identity differs from its assignment')
    verify_graph(run,role,gossip=Gossip(run['transport'],part['nickname'],session_context=part.get('gossip_context')))


def report(store, identity, role, data, *, via_broker=True):
    run=store.load(identity)
    if native_backend.enabled(run):
        from .mission_broker import request
        return request(store,identity,role,'report',report=data)
    source_current(run)
    if role not in ('worker','qa') or role not in run['participants']:
        raise RuntimeError('Report requires an assigned worker or QA role')
    if not isinstance(data,dict):raise RuntimeError('Report must be a JSON object')
    if data.get('run_id') != identity:raise RuntimeError('Report belongs to another run')
    proof=store.root/identity/(role+'-identity.json')
    if via_broker and proof.exists() and json.loads(proof.read_text()).get('broker'):
        from .mission_broker import request
        return request(store,identity,role,'report',report=data)
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
    try:
        if not accept_event(trial,event):raise RuntimeError('Report did not match the assignment')
    except SupersededReview:
        # Main must learn that the old attempt ended so it can safely request
        # a new exact candidate. The receiving reducer still rejects approval.
        pass
    verify_publisher(store,run,role)
    args=['a2a','artifact'] if data['status'] in ('result','qa') else ['a2a','status','--state','input-required' if data['status']=='blocked' else 'working']
    return Gossip(run['transport'],part['nickname'],session_context=part.get('gossip_context')).invoke(*args,'--task-id',task_id,'--text',json.dumps(data))
