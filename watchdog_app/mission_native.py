"""Exact Codex queue + local durable events. No Gossip dependency.

The owned host wrapper authenticates reports via the typed broker; native claims
from JSON or a same-UID socket alone are never sufficient authorization.
"""
from dataclasses import asdict
import json
import os
from pathlib import Path
import time
import uuid

from . import bindings
from .mission import accept_event, SupersededReview
from .store import atomic

LIMIT = 65536


def enabled(run):
    return run.get('transport', {}).get('kind') == 'native'


def boot_id():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def owner():
    from .mission_broker import process
    return {'pid':os.getpid(),'started':process(os.getpid())[1]}


def verify_participant(run, role, *, enrolling=False):
    part = run['participants'][role]
    native = part.get('native')
    if not native or not part.get('generation') or not enrolling and not part.get('enrolled'):
        raise RuntimeError(role+' native enrollment is unavailable')
    if part.get('boot_id') != boot_id() or run['transport'].get('boot_id') != boot_id():
        raise RuntimeError('Native actor belongs to another boot')
    from .mission_broker import process
    host = part.get('bridge_owner', {})
    if not host or process(host['pid'])[1] != host['started']:
        raise RuntimeError('Native host wrapper exited or changed identity')
    pane = run['resources'][role]
    if (native['kind'] != 'codex' or native['account'] != part['account'] or
            native['pane'] != pane['pane_id'] or native['terminal'] != pane['terminal_id']):
        raise RuntimeError('Native actor account or terminal changed')
    uuid.UUID(native['session'])
    binding = bindings.engine().Binding(**native)
    bindings.verify(binding)
    return binding


def check_proof(run, role, proof):
    part = run['participants'][role]
    if (not enabled(run) or proof.get('transport') != 'native' or
            proof.get('run_id') != run['id'] or proof.get('role') != role or
            any(proof.get(key) != part.get(key) for key in ('native','generation','boot_id','bridge_owner'))):
        raise RuntimeError('Native actor role, generation or binding changed')
    return verify_participant(run, role, enrolling=True)


def register(run, store):
    for role, part in run['participants'].items():
        try:
            if (store.root/run['id']/(role+'-exit.json')).exists():
                raise RuntimeError('Participant exited; completion was not inferred')
            verify_participant(run, role)
            part['available'] = True; part['last_seen'] = time.time()
            part.pop('problem', None)
        except (RuntimeError, OSError, ValueError, KeyError) as error:
            part['available'] = False; part['problem'] = str(error)
    run['observed'] = time.time()


def contract(run, task_id, attempt):
    from .mission_transport import assignment
    value = json.loads(assignment(run, task_id))
    value['attempt_id'] = attempt
    value['report_schema'].update(attempt_id=attempt, event_id='Stable UUID per report; reuse on retry')
    return value


def deliver(store, run, role, attempt, payload):
    """One durable intent before queueing. A missing receipt never permits resend."""
    from . import mission_transport as transport
    binding = verify_participant(run, role)
    transport.main_session(run)
    transport.source_current(run)
    message = 'Watchdog native assignment\n'+json.dumps(payload, ensure_ascii=False)
    if len(message.encode()) > LIMIT: raise RuntimeError('Native assignment exceeds the bounded message size')
    record = {'role':role, 'attempt_id':attempt, 'recipient':asdict(binding),
              'generation':run['participants'][role]['generation'], 'payload':payload,
              'state':'sending', 'created':time.time()}
    if attempt in run.setdefault('deliveries', {}): raise RuntimeError('Assignment already attempted')
    run['deliveries'][attempt] = record; store.save(run)
    try:
        receipt = bindings.engine().queue(binding, message)
        uuid.UUID(receipt)
    except Exception as error:
        record.update(state='uncertain', problem=str(error)); store.save(run)
        raise RuntimeError('Native assignment delivery is uncertain; inspect the exact queue, do not resend') from error
    record.update(state='sent', receipt=receipt); store.save(run)
    return record


def dispatch(store, identity, task_id):
    from . import mission_transport as transport
    with store.lock(identity):
        run = store.load(identity); transport.main_session(run); transport.source_current(run)
        if run['phase'] != 'active': raise RuntimeError('Run is not active')
        task = run['tasks'][task_id]
        if task.get('delivery') or task.get('attempt_id'): raise RuntimeError('Assignment already sent or uncertain')
        item = next(t for t in run['brief']['tasks'] if t['id'] == task_id)
        if any(not run['tasks'][d].get('accepted_result') for d in item['dependencies']):
            raise RuntimeError('Task dependencies need reviewed results accepted by main')
        if any(t.get('attempt_id') and not t.get('accepted_result') for k,t in run['tasks'].items() if k != task_id):
            raise RuntimeError('Worker already has an assignment awaiting main review')
        verify_participant(run, 'worker')
        path = transport.owned_worktree(run, 'worker')
        head = transport.git(path, 'rev-parse', 'HEAD')
        if transport.git(path, 'status', '--porcelain'): raise RuntimeError('Worker worktree must be clean')
        if head != run.get('worker_head', run['brief']['base_sha']): raise RuntimeError('Worker base changed')
        run['participants']['worker']['base_sha'] = head
        attempt = str(uuid.uuid4()); payload = contract(run, task_id, attempt)
        from .mission_handoff import claim_session
        payload['session_policy']=claim_session(store,run,'worker',task_id,head,purpose=item.get('purpose','implementation'))
        task.update(attempt_id=attempt, delivery='sending'); store.save(run)
        try: deliver(store, run, 'worker', attempt, payload)
        except Exception:
            task.update(delivery='uncertain',state='blocked',summary='Native delivery needs inspection',updated=time.time())
            store.save(run); raise
        task.update(delivery='sent', state='working', agent='worker', summary='Assignment delivered', updated=time.time())
        store.save(run); return run


def followup(store, identity, task_id, text):
    from . import mission_transport as transport
    if not text.strip(): raise RuntimeError('Follow-up text is required')
    with store.lock(identity):
        run=store.load(identity);transport.main_session(run);transport.source_current(run)
        task=run['tasks'][task_id]
        if not task.get('attempt_id') or task['state']=='done':raise RuntimeError('No active native assignment')
        if task.get('delivery')!='sent':raise RuntimeError('Previous delivery is uncertain; inspect it before a follow-up')
        transport.owned_worktree(run,'worker');verify_participant(run,'worker')
        attempt=str(uuid.uuid4());payload=contract(run,task_id,attempt);payload['clarification']=text
        from .mission_handoff import claim_session
        payload['session_policy']=claim_session(store,run,'worker',task_id,payload['base_sha'],purpose=payload.get('purpose','implementation'))
        task.setdefault('attempt_history',[]).append(task['attempt_id'])
        task.update(attempt_id=attempt,delivery='sending')
        task.pop('result',None);task.pop('accepted_result',None);run['qa']=None
        run['result_version']=run.get('result_version',0)+1
        store.save(run)
        try:deliver(store,run,'worker',attempt,payload)
        except Exception:
            task.update(delivery='uncertain',state='blocked',summary='Follow-up delivery is uncertain',updated=time.time())
            store.save(run);raise
        task.update(delivery='sent',state='working',agent='worker',summary='Guidance delivered',updated=time.time())
        store.save(run);return run


def forward(store, run):
    from . import mission_transport as transport
    for event_id, event in run['events'].items():
        if event['delivery'] != 'pending': continue
        # Identity failure before send is safe to retry verification on a later tick.
        session = transport.main_session(run)
        message = 'Watchdog native report\n'+json.dumps({'run_id':run['id'],'event_id':event_id,
            'report':event['report'],'rejected':event.get('rejected'),'notice':'Evidence awaits review. TODO was not changed.'},ensure_ascii=False)
        if len(message.encode()) > LIMIT: raise RuntimeError('Native notification exceeds message size')
        event['delivery']='sending';store.save(run)
        try:
            receipt=session.runtime.queue(session.binding,message);uuid.UUID(receipt)
        except Exception as error:
            event.update(delivery='uncertain',notification_problem=str(error));store.save(run)
            continue
        event.update(delivery='sent',receipt=receipt,recipient=asdict(session.binding));store.save(run)


def delivery_receipt(run, role, attempt, *, task_id=None):
    """Trust a committed receipt only for this exact role, actor and contract."""
    record=run.get('deliveries',{}).get(attempt)
    if not isinstance(record,dict):return False,'Queue receipt is missing: no delivery record for this intent'
    try:
        receipt=record.get('receipt')
        valid_receipt=isinstance(receipt,str) and str(uuid.UUID(receipt))==receipt
    except ValueError:valid_receipt=False
    if record.get('state')!='sent' or not valid_receipt:
        return False,'Queue receipt is missing or uncertain; inspect the exact thread queue'
    part=run['participants'][role]
    if (not attempt or record.get('attempt_id')!=attempt or record.get('role')!=role or
            not part.get('generation') or record.get('generation')!=part['generation'] or
            not part.get('native') or record.get('recipient')!=part['native']):
        return False,'Queue receipt recipient, role, generation or attempt differs from the current intent'
    payload=record.get('payload')
    if (not isinstance(payload,dict) or payload.get('run_id')!=run['id'] or payload.get('attempt_id')!=attempt):
        return False,'Queue receipt contract run or attempt differs from the current intent'
    if role=='worker':
        if payload.get('task_id')!=task_id:return False,'Queue receipt task differs from the current intent'
    else:
        review=run.get('review_contract') or {}
        if (not review.get('id') or payload.get('review_id')!=review['id'] or
                payload.get('candidate')!=review.get('candidate') or
                payload.get('candidate')!=run.get('candidate')):
            return False,'Queue receipt review or candidate differs from the current intent'
    return True,''


def reconcile_intents(run):
    # The task/review intent is committed before deliver() even creates its own
    # record. Conversely deliver() commits a receipt before its caller finalizes.
    # Reconcile both windows without ever submitting a queue message.
    for record in run.get('deliveries',{}).values():
        if record['state']=='sending':
            record.update(state='uncertain',problem='Interrupted queue delivery; inspect before recovery')
    for key,task in run['tasks'].items():
        if task.get('delivery')!='sending':continue
        attempt=task.get('attempt_id')
        sent,problem=delivery_receipt(run,'worker',attempt,task_id=key)
        task['delivery']='sent' if sent else 'uncertain'
        if sent:
            reported=any(e.get('role')=='worker' and not e.get('rejected') and
                e['report'].get('attempt_id')==attempt for e in run['events'].values())
            if not reported:
                task.update(state='working',agent='worker',summary='Assignment delivered; committed receipt recovered',updated=time.time())
        else:
            task.update(state='blocked',agent='worker',summary='Delivery needs inspection: '+problem,updated=time.time())
            record=run.get('deliveries',{}).get(attempt)
            if record is not None:record.update(state='uncertain',problem=problem)
    if run.get('qa_delivery')=='sending':
        attempt=run.get('qa_task');sent,problem=delivery_receipt(run,'qa',attempt)
        run['qa_delivery']='sent' if sent else 'uncertain'
        if sent:
            run.pop('qa_delivery_problem',None)
            if run.get('operation')=='checkout QA candidate':run['operation']=None
            review=run.get('review_contract') or {}
            reported=any(e.get('role')=='qa' and not e.get('rejected') and
                e['report'].get('attempt_id')==attempt for e in run['events'].values())
            if not reported and review.get('version')==run.get('result_version',0):
                for task in run['tasks'].values():
                    if task['state']!='done':task.update(state='review',agent='qa',
                        summary='QA is checking '+run['candidate'],updated=time.time())
        else:
            run['qa_delivery_problem']=problem;run['qa']=None
            for task in run['tasks'].values():
                if task['state']!='done':task.update(state='blocked',agent='qa',
                    summary='QA delivery needs inspection: '+problem,updated=time.time())
            record=run.get('deliveries',{}).get(attempt)
            if record is not None:record.update(state='uncertain',problem=problem)


def tick(store, identity):
    from . import mission_transport as transport
    with store.lock(identity):
        run=store.load(identity)
        if run['phase'] not in ('active','blocked'):return run
        transport.main_session(run)
        transport.source_current(run)
        register(run,store)
        reconcile_intents(run)
        for event in run['events'].values():
            if event['delivery']=='sending':event.update(delivery='uncertain',notification_problem='Interrupted notification; not resent')
        run['monitor_updated']=time.time();run.pop('monitor_problem',None);store.save(run)
        forward(store,run);return run


def handle(store, identity, role, proof, method, data, *, recheck=None):
    """Host broker only: its immutable proof and live caller ancestry precede this."""
    from . import mission_transport as transport
    with store.lock(identity):
        run=store.load(identity);check_proof(run,role,proof)
        if recheck is not None:recheck()
        part=run['participants'][role]
        part.update(available=True,last_seen=time.time());run['observed']=time.time()
        if not isinstance(data,dict):raise RuntimeError('Native operation data must be an object')
        if method != 'report':transport.source_current(run)
        if method=='enroll' and not data:
            part.update(enrolled=True,available=True);store.save(run)
            return {'published':True,'transport':'native','role':role,'session':part['native']['session']}
        if not part.get('enrolled'):raise RuntimeError('Native role must enroll first')
        if method=='poll' and set(data)=={'after'} and type(data['after']) is int and data['after']>=0:
            return [dict(seq=i+1,attempt_id=key,contract=d['payload'],state=d['state'])
                    for i,(key,d) in enumerate(run.get('deliveries',{}).items())
                    if i>=data['after'] and d['role']==role][:1]
        if method!='report' or set(data)!={'report'}:raise RuntimeError('Unsupported native operation or data')
        report=data['report']
        if not isinstance(report,dict) or len(json.dumps(report).encode())>LIMIT//2:
            raise RuntimeError('Native report is malformed or too large')
        event_id=report.get('event_id')
        try:
            if str(uuid.UUID(event_id))!=event_id:raise ValueError()
        except (ValueError,TypeError,AttributeError) as error:raise RuntimeError('Native report requires a stable event UUID') from error
        previous=run['events'].get(event_id)
        if previous:
            if (previous['report']!=report or previous.get('role')!=role or
                    previous.get('generation')!=proof['generation']):raise RuntimeError('Event identity was reused for different evidence')
            return {'event_id':event_id,'persisted':True,'duplicate':True,'notification':previous['delivery']}
        transport.source_current(run)
        delivery=run.get('deliveries',{}).get(report.get('attempt_id'),{})
        if (delivery.get('role')!=role or delivery.get('generation')!=proof['generation'] or
                delivery.get('recipient')!=proof['native']):
            raise RuntimeError('Report attempt recipient or actor generation differs')
        event={'id':event_id,'event':'task','kind':'artifact','transport':'native','role':role,
               'actor':proof['native'],'generation':proof['generation'],
               'task_id':report.get('attempt_id'),'body':json.dumps(report)}
        try:
            if not accept_event(run,event):raise RuntimeError('Native report did not match the assignment attempt')
        except SupersededReview as error:
            # Preserve ended stale QA as rejected evidence, never approval.
            run['events'][event_id]={'report':report,'delivery':'pending','received':time.time(),
                'role':role,'generation':proof['generation'],'rejected':str(error)}
        store.save(run)
        try:forward(store,run)
        except (RuntimeError,OSError,ValueError) as error:
            run['events'][event_id]['notification_problem']=str(error);store.save(run)
        return {'event_id':event_id,'persisted':True,'notification':run['events'][event_id]['delivery']}


def review(store, identity, candidate, context=None):
    from . import mission_transport as transport
    with store.lock(identity):
        run=store.load(identity);transport.main_session(run);transport.source_current(run)
        verify_participant(run,'qa');transport.owned_worktree(run,'qa')
        if run.get('qa_delivery') in ('sending','uncertain'):raise RuntimeError('QA assignment delivery is uncertain')
        if run.get('qa_task') and not run.get('qa_finished'):raise RuntimeError('QA review is still in progress')
        if any(not t.get('result') or t['state'] not in ('review','blocked') for t in run['tasks'].values()):
            raise RuntimeError('Every selected task needs implementation evidence before QA')
        if transport.git(run['repo'],'rev-parse',candidate+'^{commit}')!=candidate:
            raise RuntimeError('QA requires the full exact candidate SHA')
        transport.verify_result_commits(run,candidate)
        path=run['participants']['qa']['worktree']
        if transport.git(path,'status','--porcelain'):raise RuntimeError('QA worktree is not clean')
        from .mission_handoff import claim_session
        review_id=str(uuid.uuid4())
        policy=claim_session(store,run,'qa',review_id,candidate)
        run['operation']='checkout QA candidate';store.save(run)
        transport.git(path,'checkout','--detach',candidate)
        attempt=str(uuid.uuid4())
        run.update(candidate=candidate,qa=None,qa_finished=False,qa_delivery='sending',qa_task=attempt)
        run['review_contract']={'id':review_id,'candidate':candidate,'base_sha':run['brief']['base_sha'],
            'context':context,'version':run.get('result_version',0),'verified_commits':True}
        payload={'run_id':identity,'attempt_id':attempt,'review_id':run['review_contract']['id'],
            'candidate':candidate,'base_sha':run['brief']['base_sha'],'repo':run['repo'],'worktree':path,
            'tasks':run['brief']['tasks'],'results':{k:t['result'] for k,t in run['tasks'].items()},
            'session_policy':policy,'context':context,'instructions':'Review the complete integrated candidate at exactly this SHA. Do not write source.',
            'report_schema':{'run_id':identity,'attempt_id':attempt,'review_id':run['review_contract']['id'],
                'event_id':'Stable UUID per report','candidate':candidate,'status':'qa | blocked | working',
                'verdict':'pass | fail for qa','summary':'Findings and limitations','tests':['Observed evidence']}}
        store.save(run)
        try:deliver(store,run,'qa',attempt,payload)
        except Exception:run['qa_delivery']='uncertain';store.save(run);raise
        run.update(qa_delivery='sent',operation=None)
        for task in run['tasks'].values():task.update(state='review',agent='qa',updated=time.time(),summary='QA is checking '+candidate)
        store.save(run);return run


def participant_prompt(store, run, role):
    from .mission_launch import ROOT
    import shlex, sys
    identity=run['id'];part=run['participants'][role]
    command=[sys.executable,str(ROOT/'watchdog'),'mission']
    scope=['--run',identity,'--role',role,'--state-dir',str(store.root)]
    return (part['role_context']+'\nNative Mission Control participant. Only main talks to the user. '
        'Wait for your role-identity.json (host bootstrap can take 45 seconds), then enroll from THIS conversation. '
        'No source edits before an explicit queued contract. Queue delivery targets this exact thread/account. '
        'Never change CODEX_THREAD_ID, forge a peer, use pane text injection or operate Gossip. '
        'Reports require the supplied run/task/attempt IDs and a stable event_id UUID per report; '
        'reuse that UUID on retry. A result awaits main and independent QA; it does not complete TODO.\n'
        f"Run: {identity}\nRole: {role}\nWorktree: {part['worktree']}\n"
        'Enroll: '+shlex.join(command+['enroll']+scope)+'\n'
        'Receive: '+shlex.join(command+['receive']+scope)+' --after 0\n'
        'Report: '+shlex.join(command+['report']+scope+['--file','/tmp/watchdog-'+role+'-'+identity+'-report.json'])+'\n'
        'One executor conversation handles only one logical task and its corrections. Main supplies a NEW executor for every later task at the preceding accepted commit, a NEW QA conversation for each review, and dedicated disposable conversations for probes, never real task executors. Never transfer a full transcript or create actors yourself. '
        'Use the scoped host bridge. Read only new native messages when notified; do not spin or repeat work. '
        'Do not close tasks or edit source outside the assigned contract.')


def bootstrap(store, identity, role, child, *, timeout=45):
    from .mission_launch import owned_worktree, source_current
    run=store.load(identity);part=run['participants'][role];pane=run['resources'][role]
    source_current(run)
    owned_worktree(run,role)
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if child.poll() is not None:raise RuntimeError('Participant exited before native registration')
        candidates,_=bindings.discover(Path(part['worktree']))
        matches=[b for b in candidates if b.kind=='codex' and b.account==part['account'] and
            b.pane==pane['pane_id'] and b.terminal==pane['terminal_id'] and b.pid==child.pid]
        if len(matches)==1:
            binding=matches[0];bindings.verify(binding)
            if part.get('native') and part['native']!=asdict(binding):
                raise RuntimeError('Native bootstrap differs from the explicitly pinned actor')
            break
        time.sleep(.1)
    else:raise RuntimeError('Native registration timed out; owned terminal retained')
    proof={'transport':'native','run_id':identity,'role':role,'native':asdict(binding),
        'generation':str(uuid.uuid4()),'boot_id':boot_id(),'bridge_owner':owner(),
        'broker':str(store.root/identity/(role+'-broker.sock'))}
    with store.lock(identity):
        run=store.load(identity)
        if not enabled(run):raise RuntimeError('Transport changed during bootstrap')
        source_current(run)
        part=run['participants'][role]
        if part.get('generation'):raise RuntimeError('Native actor already bootstrapped; inspect its existing proof')
        part.update(native=proof['native'],generation=proof['generation'],boot_id=proof['boot_id'],bridge_owner=proof['bridge_owner'],
                    enrolled=False,available=False)
        check_proof(run,role,proof);store.save(run)
        atomic(store.root/identity/(role+'-identity.json'),proof)
    return proof


def host_bridge(store, identity, role, *, confirmed=False):
    """Attach only to an explicitly pinned idle actor, without restart or migration.

    This is a host operator path for a NEW/disposable native ledger using approved
    existing actors. It never converts an existing Gossip ledger or signals a PID.
    """
    from . import mission_transport as transport
    from .mission_broker import Broker
    if not confirmed:raise RuntimeError('Explicit idle bridge confirmation is required')
    with store.lock(identity):
        run=store.load(identity)
        if not enabled(run):raise RuntimeError('Idle bridge requires a separate native run; legacy runs are preserved')
        transport.main_session(run);transport.source_current(run)
        if role not in ('worker','qa') or run['phase']!='active':raise RuntimeError('Active assigned native role required')
        part=run['participants'][role];expected=part.get('native')
        if not expected:raise RuntimeError('Idle bridge requires the explicitly pinned native binding')
        if any(d['role']==role for d in run.get('deliveries',{}).values()):
            raise RuntimeError('Idle bridge refuses dispatched or uncertain work')
        if part.get('generation'):raise RuntimeError('Host bridge already attempted; inspect its retained proof')
        transport.owned_worktree(run,role)
        binding=bindings.engine().Binding(**expected)
        if bindings.verify(binding).get('agent_status') not in ('idle','done'):
            raise RuntimeError('Actor must be idle; a busy actor is never restarted')
    class ExistingActor:
        pid=binding.pid
        def poll(self):
            try:bindings.verify(binding);return None
            except (RuntimeError,OSError):return 1
    actor=ExistingActor()
    proof=bootstrap(store,identity,role,actor)
    if bindings.verify(binding).get('agent_status') not in ('idle','done'):
        raise RuntimeError('Actor became busy during idle attachment; retained proof needs inspection')
    return Broker(store,identity,role,proof,actor)


def serve(store, identity, role, *, confirmed=False):
    bridge=host_bridge(store,identity,role,confirmed=confirmed)
    try:
        while bridge.child.poll() is None:time.sleep(.5)
    except KeyboardInterrupt:pass
    finally:
        bridge.close()
        with store.lock(identity):
            run=store.load(identity);part=run['participants'][role]
            if part.get('generation')==bridge.proof['generation']:
                part.update(enrolled=False,available=False,problem='Native host bridge stopped')
                store.save(run)
    return 0
