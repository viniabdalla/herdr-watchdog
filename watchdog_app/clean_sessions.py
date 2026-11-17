"""Project leader cleanup and baton transfer using existing native/Store boundaries.

Agent replies attest semantic TODO reconciliation and ai-memory save/accept. Git,
frontend identity, receipts and panel ownership are independently checked here.
Only new completed native messages are read, bounded at 64 KiB per poll. Legacy
ledgers are never adopted or written. An uncertain side effect is never retried.
"""
from contextlib import contextmanager
import copy
from dataclasses import asdict
import fcntl
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
import sys
import time
import uuid

from . import bindings, mission_handoff as handoff
from .actions import Session
from .herdr import Herdr
from .mission import RunStore
from .mission_launch import git, ROOT
from .store import Store, atomic

LIMIT=65536
PREFIX='WATCHDOG_CLEAN '


class LeaderBlocked(RuntimeError):
    """A correlated leader explicitly could not complete its assigned step."""


def path(store, identity):
    if str(uuid.UUID(identity))!=identity:raise RuntimeError('Invalid cleanup operation ID')
    return store.root/'clean-sessions'/(identity+'.json')


def folder(store,identity):return path(store,identity).with_suffix('')


def load(store,identity):return handoff.read_json(path(store,identity))


def operations(store,repo):
    result=[]
    for p in (store.root/'clean-sessions').glob('*.json'):
        op=handoff.read_json(p)
        if op.get('repo')==str(Path(repo).resolve()):result.append(op)
    return result


@contextmanager
def lease(store,repo):
    root=store.root/'clean-sessions';root.mkdir(parents=True,exist_ok=True,mode=0o700)
    with (root/(handoff.digest(str(Path(repo).resolve()))+'.lock')).open('a') as f:
        try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as error:raise RuntimeError('Cleanup is busy') from error
        yield


def save(store,op):
    op['updated']=time.time();atomic(path(store,op['operation_id']),op)


def defaults(session):
    """Configured upstream only; absent destination stays empty for explicit input."""
    repo=session.repo
    try:
        branch=git(repo,'symbolic-ref','--short','HEAD')
        remote=git(repo,'config','--get','branch.'+branch+'.remote')
        target=git(repo,'config','--get','branch.'+branch+'.merge').removeprefix('refs/heads/')
    except RuntimeError:remote=target=''
    return {'remote':remote,'branch':target,'owned_paths':['TODO.md'],'integrate':[],
            'executable':str(Path.home()/'.local/share/mise/installs/codex/latest/bin/codex'),
            'model':'gpt-6.1-sol','effort':'medium'}


def policy_for(session,policy):
    value=copy.deepcopy(policy)
    if set(value)!={'remote','branch','owned_paths','integrate','executable','model','effort'}:
        raise RuntimeError('Cleanup needs an explicit destination, owned paths, approved branches and startup settings')
    repo=session.repo
    if value['remote'] not in git(repo,'remote').splitlines():raise RuntimeError('Choose an explicit configured push remote')
    git(repo,'check-ref-format','refs/heads/'+value['branch'])
    if git(repo,'symbolic-ref','--short','HEAD')!=value['branch']:
        raise RuntimeError('Cleanup only integrates into the current explicitly approved branch')
    for key in ('owned_paths','integrate'):
        if not isinstance(value[key],list) or len(value[key])>32 or any(not isinstance(s,str) or not s or len(s)>240 for s in value[key]):
            raise RuntimeError('Use at most 32 explicit '+key)
    for name in value['owned_paths']:
        p=PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or name in ('.','*','**') or p.parts[0]=='.git' or str(p)!=name:
            raise RuntimeError('Owned paths must be exact project relative files')
        file=repo/name
        if file.is_symlink() or not file.resolve().is_relative_to(repo) or file.is_dir():
            raise RuntimeError('Owned paths must be regular project files')
    executable=Path(value['executable'])
    if not executable.is_absolute() or not os.access(executable,os.X_OK):raise RuntimeError('Approved executable is unavailable')
    if not value['model'] or len(value['model'])>100 or value['effort'] not in ('low','medium','high','xhigh'):
        raise RuntimeError('Explicit model and reasoning effort required')
    value['integration_heads']={ref:git(repo,'rev-parse','--verify',ref+'^{commit}') for ref in value['integrate'] if not ref.startswith('-')}
    if len(value['integration_heads'])!=len(value['integrate']):raise RuntimeError('Approved integration refs must be distinct and explicit')
    if len(git(repo,'remote','get-url','--all','--push',value['remote']).splitlines())!=1:
        raise RuntimeError('Cleanup requires one explicit push destination per remote')
    value['remote_digest']=handoff.digest(git(repo,'remote','get-url','--push',value['remote']))
    return value


def native_boundary(store,repo):
    # Project baton transfer is NOT native ledger adoption. Existing native runs
    # must finish under their owner first; all legacy ledgers remain export-only.
    for run in RunStore(store.root/'runs').list(repo):
        if run.get('transport',{}).get('kind')=='native' and run['phase']!='done':
            raise RuntimeError('Finish or inspect active native run '+run['id']+' before project cleanup; no ledger was adopted')


def history_mark(binding):
    p=Path(binding.history)
    if p.is_symlink():raise RuntimeError('Native history must be a regular file')
    s=p.stat()
    return {'offset':s.st_size,'inode':s.st_ino,'device':s.st_dev}


def queue(store,op,key,binding,message):
    """Persist intent before exact-thread queue; never infer a receiver receipt."""
    effect=op['effects'].get(key)
    if effect:raise RuntimeError('Existing '+key+' delivery intent requires inspection; no resend')
    bindings.verify(binding)
    op['effects'][key]={'state':'sending','recipient':asdict(binding)};save(store,op)
    try:receipt=bindings.engine().queue(binding,message)
    except Exception:
        op['effects'][key]['state']='uncertain';save(store,op);raise
    op['effects'][key].update(state='sent',queue_receipt=receipt);save(store,op)


def reply_instructions(op,kind,fields):
    template={'operation_id':op['operation_id'],'token':op['tokens'][kind],'kind':kind,**fields}
    blocked={**template,'kind':'blocked','reason':'Concrete blocker'}
    return ('\nWhen ready, end your turn with exactly one plain line (no code fence):\n'+PREFIX+json.dumps(template)+
            '\nIf blocked use this same operation/token with kind blocked and a concrete reason: '+PREFIX+json.dumps(blocked))


def request(session,policy,*,confirmed=False,store=None):
    if not confirmed:raise RuntimeError('Explicit cleanup confirmation is required')
    store=store or Store();session.verify()
    if session.binding.kind!='codex':raise RuntimeError('Cleanup requires an exact native Codex thread')
    uuid.UUID(session.binding.session)
    with lease(store,session.repo):
        state=handoff.read_json(session.file)
        if session.file.resolve()!=(store.root/(session.binding.key+'.json')).resolve():
            raise RuntimeError('Cleanup requires the canonical Watchdog panel binding')
        candidates,_=bindings.discover(session.repo)
        if [asdict(b) for b in candidates].count(asdict(session.binding))!=1:
            raise RuntimeError('Current leader is not a unique verified project frontend')
        if state.get('ownership')=='released':raise RuntimeError('This leader has released ownership; reopen Tasks')
        for previous in operations(store,session.repo):
            if previous['state']!='released':raise RuntimeError('Inspect existing pending/partial cleanup '+previous['operation_id']+'; no automatic retry')
        native_boundary(store,session.repo)
        approved=policy_for(session,policy)
        op={'version':1,'operation_id':str(uuid.uuid4()),'repo':str(session.repo),'binding_file':str(session.file),
            'source':asdict(session.binding),'base_sha':git(session.repo,'rev-parse','HEAD'),'policy':approved,
            'state':'pending','stage':'preparation','effects':{},'created':time.time(),
            'boot_id':__import__('watchdog_app.mission_native',fromlist=['boot_id']).boot_id(),
            'tokens':{k:str(uuid.uuid4()) for k in ('prepared','received','released')},
            'history':{'source':history_mark(session.binding)}}
        save(store,op)
        prompt=(f"Clean sessions operation {op['operation_id']} explicitly authorized for {session.repo}.\n"
            f"Current leader: {session.binding.session}; account {session.binding.account}.\n"
            'Coordinate preparation now: honestly reconcile TODO with unfinished work and open questions preserved; '
            'do not mark tasks done from dispatch, files or notifications. Verify ownership before editing only the authorized paths. '
            'Do NOT commit, merge or push yourself: the backend performs only the exact authorized Git plan below after your reply. '
            'Do not create actors or close panes. Wait for the later explicit release request.\n'
            'Authorized Git/startup scope: '+json.dumps(approved)+'\n'
            'Call the ACTUAL ai-memory MCP tool memory_handoff_begin now, using summary (2–3 sentences), open_questions (short strings), next_steps (unfinished tasks and next actions), and files_touched (owned file hints). Include this operation ID in the summary and bounded evidence paths in next_steps. Keep sharing at its existing operator default. Session-aware clients omit scope for this repo; static clients pass workspace+project from .ai-memory.toml or the normalized upstream/origin identity, never the last active project. '
            'If ai-memory or preparation is unavailable, report kind blocked with reason instead; do not invent a handoff ID. '
            'No full transcripts. This is a project baton transfer; legacy runs remain historical export-only. '
            'The backend commits authorized owned files, fast-forwards only listed pinned branches, pushes to the explicit destination, verifies a checkpoint, and opens a fresh dedicated leader. '
            'You remain leader until actual successor receipt and your explicit release.\n'
            +reply_instructions(op,'prepared',{'todo_reconciled':True,'memory_handoff_id':'ACTUAL_ID','summary':'Concise continuation',
                'open_questions':[],'unfinished_tasks':[],'next_steps':[],'references':[]}))
        try:queue(store,op,'prepare',session.binding,prompt)
        except Exception as error:op.update(state='partial',problem='Preparation delivery uncertain: '+str(error));save(store,op)
        return op


def completed_reply(store,op,who,kind,binding):
    """Only post-request completed assistant events from the pinned native history."""
    bindings.verify(binding)
    mark=op['history'][who];p=Path(binding.history);s=p.stat()
    if p.is_symlink() or (s.st_ino,s.st_dev)!=(mark['inode'],mark['device']) or s.st_size<mark['offset']:
        raise RuntimeError('Native receipt history was replaced or truncated')
    with p.open('rb') as f:
        f.seek(mark['offset']);raw=f.read(LIMIT+1)
    if len(raw)>LIMIT:raise RuntimeError('New native messages exceed receipt bound; inspect manually without resend')
    complete=raw.rfind(b'\n')+1
    found=[]
    for line in raw[:complete].splitlines():
        row=json.loads(line)
        if not isinstance(row,dict):continue
        payload=row.get('payload',{})
        if not isinstance(payload,dict):continue
        if row.get('type')!='event_msg' or payload.get('type')!='task_complete':continue
        text=payload.get('last_agent_message','')
        if not isinstance(text,str) or not text.startswith(PREFIX):continue
        value=json.loads(text[len(PREFIX):])
        if value.get('operation_id')!=op['operation_id']:continue
        if value.get('token')!=op['tokens'][kind]:raise RuntimeError('Receipt operation token differs')
        if value.get('kind')=='blocked':
            raise LeaderBlocked('Leader reports blocked: '+str(value.get('reason','Preparation unavailable'))[:500])
        if value.get('token')!=op['tokens'][kind] or value.get('kind')!=kind:
            raise RuntimeError('Receipt operation token or phase differs')
        found.append({'value':value,'turn_id':payload.get('turn_id'),'sha256':handoff.digest(row)})
    mark['offset']+=complete;save(store,op)
    if len(found)>1:raise RuntimeError('Duplicate native confirmations require inspection')
    return found[0] if found else None


def source_session(op):
    session=Session(op['binding_file'],Path(op['repo']))
    if asdict(session.binding)!=op['source']:raise RuntimeError('Current leader binding was replaced')
    return session


def checkpoint_current(op):
    repo=op['repo'];policy=op['policy']
    if (git(repo,'symbolic-ref','--short','HEAD')!=policy['branch'] or
        handoff.digest(git(repo,'remote','get-url','--push',policy['remote']))!=policy['remote_digest']):
        raise RuntimeError('Approved branch or push remote changed')
    if op.get('checkpoint'):
        if git(repo,'rev-parse','HEAD')!=op['checkpoint'] or git(repo,'status','--porcelain'):
            raise RuntimeError('Checkpoint is stale or dirty')
        remote=git(repo,'ls-remote','--heads',git(repo,'remote','get-url','--push',policy['remote']),'refs/heads/'+policy['branch']).split()
        if not remote or remote[0]!=op['checkpoint']:raise RuntimeError('Remote checkpoint changed')


def effect(store,op,name,action):
    if name in op['effects']:raise RuntimeError('Existing '+name+' intent requires inspection; no retry')
    op['effects'][name]={'state':'sending'};save(store,op)
    try:result=action()
    except Exception:
        op['effects'][name]['state']='uncertain';save(store,op);raise
    op['effects'][name]['state']='sent';save(store,op)
    return result


def prepare_checkpoint(store,op,receipt):
    v=receipt['value']
    if not v.get('memory_handoff_id') or v['memory_handoff_id']=='ACTUAL_ID':
        raise RuntimeError('ai-memory handoff unavailable; memory was not transferred')
    if v.get('todo_reconciled') is not True:raise RuntimeError('Leader has not attested honest TODO reconciliation')
    for key in ('summary','memory_handoff_id'):
        if not isinstance(v.get(key),str) or not v[key].strip() or len(v[key])>1000:raise RuntimeError('Bounded '+key+' required')
    for key in ('open_questions','unfinished_tasks','next_steps'):
        if not isinstance(v.get(key),list) or len(v[key])>16 or any(not isinstance(x,str) or len(x)>500 for x in v[key]):
            raise RuntimeError('Bounded continuation lists required')
    refs=v.get('references',[])
    if not isinstance(refs,list) or len(refs)>8:raise RuntimeError('At most eight bounded evidence references')
    references=[handoff.reference(p) for p in refs]
    repo=Path(op['repo']);policy=op['policy'];checkpoint_current(op)
    if git(repo,'rev-parse','HEAD')!=op['base_sha']:raise RuntimeError('Preparation base changed before Git authorization')
    # -z avoids quote parsing and filenames with spaces. Both index and working
    # tree changes (including deletions/untracked) must be explicitly owned.
    changed=set(filter(None,git(repo,'-c','core.quotepath=false','diff','--name-only','-z','HEAD').split('\0')))
    changed.update(filter(None,git(repo,'ls-files','--others','--exclude-standard','-z').split('\0')))
    if changed-set(policy['owned_paths']):raise RuntimeError('Dirty unowned files block cleanup: '+', '.join(sorted(changed-set(policy['owned_paths']))))
    for name in changed:
        p=repo/name
        if p.is_symlink() or not p.resolve().is_relative_to(repo):raise RuntimeError('Owned file path was replaced')
    op['preparation']={k:v[k] for k in ('summary','memory_handoff_id','open_questions','unfinished_tasks','next_steps')}
    op['preparation_receipt']=receipt;save(store,op)
    if changed:
        effect(store,op,'stage-owned',lambda:git(repo,'add','--',*sorted(changed)))
        effect(store,op,'commit-owned',lambda:git(repo,'commit','-m','Clean sessions: reconcile owned project checkpoint'))
    for ref,sha in policy['integration_heads'].items():
        if git(repo,'rev-parse','--verify',ref+'^{commit}')!=sha:raise RuntimeError('Approved integration branch changed')
        effect(store,op,'integrate:'+ref,lambda:git(repo,'merge','--ff-only',sha))
    if git(repo,'status','--porcelain'):raise RuntimeError('Git checkpoint is dirty after integration')
    head=git(repo,'rev-parse','HEAD')
    effect(store,op,'push',lambda:git(repo,'push',policy['remote'],'HEAD:refs/heads/'+policy['branch']))
    remote=git(repo,'ls-remote','--heads',git(repo,'remote','get-url','--push',policy['remote']),'refs/heads/'+policy['branch']).split()
    if not remote or remote[0]!=head:raise RuntimeError('Push checkpoint not verified')
    op['checkpoint']=head
    context={'version':1,'operation_id':op['operation_id'],'project':op['repo'],'checkpoint':head,
             'predecessor':op['source'],'context':op['preparation'],'references':references,
             'legacy_run_adopted':False,'memory_evidence':'Predecessor attestation; successor must confirm actual ai-memory receipt',
             'authorization':policy,'next':'Wait for predecessor release before coordinating; preserve existing actors and panes.'}
    atomic(folder(store,op['operation_id'])/'continuation.json',context)
    op['handoff_sha256']=handoff.digest(context);op['stage']='launch';save(store,op)


def launch(store,op,api):
    session=source_session(op);session.verify();checkpoint_current(op)
    if session.verify().get('agent_status') not in ('idle','done'):raise RuntimeError('Predecessor must finish preparation turn before split')
    pane=effect(store,op,'split',lambda:api.call('pane','split',session.binding.pane,'--direction','right','--cwd',op['repo'],'--no-focus')['pane'])
    op['pane']=pane;save(store,op)
    api.checked(pane)
    argv=[sys.executable,str(ROOT/'watchdog'),'clean-sessions','leader','--state-dir',str(store.root),'--operation',op['operation_id']]
    effect(store,op,'startup',lambda:api.call('pane','run',pane['pane_id'],shlex.join(argv)))
    op['stage']='successor';save(store,op)


def successor(store,op):
    proof=folder(store,op['operation_id'])/'leader-proof.json'
    if not proof.exists():
        error=folder(store,op['operation_id'])/'leader-error.json'
        if error.exists():raise RuntimeError(handoff.read_json(error)['error'])
        if time.time()-op['updated']>60:raise RuntimeError('Successor startup unconfirmed; inspect retained pane, no relaunch')
        return None
    actor=handoff.read_json(proof)['native'];binding=bindings.engine().Binding(**actor)
    verify_successor(op,binding)
    candidates,_=bindings.discover(Path(op['repo']))
    if [asdict(b) for b in candidates].count(actor)!=1:raise RuntimeError('Successor is not a unique verified project frontend')
    fake_run=policy_run(store,op)
    with handoff.session_leases(RunStore(store.root/'runs'),fake_run,[op['source'],actor]) as slots:
        handoff.reserve_current_main(fake_run,slots);handoff.fresh_main(fake_run,actor,slots)
    return binding


def verify_successor(op,binding):
    bindings.verify(binding);uuid.UUID(binding.session)
    if (binding.kind!='codex' or binding.account!=op['source']['account'] or binding.workspace!=op['source']['workspace'] or
            binding.pane!=op['pane']['pane_id'] or binding.terminal!=op['pane']['terminal_id'] or
            any(getattr(binding,k)==op['source'][k] for k in ('session','pane','terminal','pid'))):
        raise RuntimeError('Successor account/project/frontend identity differs from the fresh approved target')
    project=bindings.project_for(binding)
    if project is None or Path(project).resolve()!=Path(op['repo']):raise RuntimeError('Successor belongs to a foreign project')
    if op.get('target') and asdict(binding)!=op['target']:raise RuntimeError('Pinned successor was replaced')


def policy_run(store,op):
    return {'id':op['operation_id'],'repo':op['repo'],'main':op['source'],'participants':{},
            'session_policy':{'registry_dir':str(store.root/'runs/session-policy')}}


def transfer(store,op,api):
    old=source_session(op);new=bindings.engine().Binding(**op['target']);verify_successor(op,new)
    if old.verify().get('agent_status') not in ('idle','done') or bindings.verify(new).get('agent_status') not in ('idle','done'):
        raise RuntimeError('Both leaders must be idle after explicit release before panel transfer')
    checkpoint_current(op);native_boundary(store,Path(op['repo']))
    state=handoff.read_json(op['binding_file'])
    for role,pane in state.get('panes',{}).items():
        if role!='left_undone':api.checked(pane)
    api.checked(op['pane'])
    rs=RunStore(store.root/'runs');run=policy_run(store,op)
    with handoff.session_leases(rs,run,[op['source'],op['target']]) as slots:
        handoff.reserve_current_main(run,slots);handoff.fresh_main(run,op['target'],slots)
        verify_successor(op,new)
        if old.verify().get('agent_status') not in ('idle','done') or bindings.verify(new).get('agent_status') not in ('idle','done'):
            raise RuntimeError('Leader became busy before ownership commit')
        checkpoint_current(op)
        # Intent is saved before reservation / Store mutation. Interrupted rebind
        # is visible and blocked; it never activates both coordinators.
        op['effects']['rebind']={'state':'sending'};save(store,op)
        handoff.write_claim(slots,op['target'],handoff.main_claim(run))
        op['new_binding_file']=store.transfer(old.file,old.binding,new,Path(op['repo']),op['operation_id'],api=api)
    op['effects']['rebind']['state']='sent';save(store,op)
    queue(store,op,'activation',new,
          f"Clean sessions {op['operation_id']}: predecessor release was observed; Watchdog panel ownership and Orchestrate now target your exact thread {new.session}. "
          f"Verified checkpoint {op['checkpoint']}; binding {op['new_binding_file']}. You are the project leader. Keep unfinished tasks open and preserve existing actors/panes.")
    op.update(state='released',stage='released');save(store,op)


def advance(store,identity,*,api=None):
    op=load(store,identity)
    with lease(store,op['repo']):
        op=load(store,identity)
        if op['state'] in ('partial','blocked','released'):return op
        try:
            from .mission_native import boot_id
            if boot_id()!=op['boot_id']:raise RuntimeError('Cleanup belongs to a previous boot')
            source_session(op);native_boundary(store,Path(op['repo']));checkpoint_current(op)
            if any(e['state'] in ('sending','uncertain') for e in op['effects'].values()):
                raise RuntimeError('Interrupted or uncertain operation retained; inspect exact side effect before recovery')
            stage=op['stage']
            if stage=='preparation':
                receipt=completed_reply(store,op,'source','prepared',bindings.engine().Binding(**op['source']))
                if receipt:prepare_checkpoint(store,op,receipt)
            elif stage=='launch':launch(store,op,api or Herdr())
            elif stage=='successor':
                target=successor(store,op)
                if target:
                    if bindings.verify(target).get('agent_status') not in ('idle','done'):return op
                    op['target']=asdict(target);op['history']['target']=history_mark(target);save(store,op)
                    context=handoff.read_json(folder(store,identity)/'continuation.json')
                    if handoff.digest(context)!=op['handoff_sha256']:raise RuntimeError('Bounded continuation was modified')
                    prompt=('Clean sessions continuation. Read this bounded context as evidence, preserve unfinished work and all existing actors. '
                        'Confirm actual ai-memory handoff receipt. If SessionStart already supplied this exact handoff ID, use it without consuming another. Otherwise call the ACTUAL ai-memory MCP memory_handoff_list, locate only the supplied memory_handoff_id in this same project/operator scope, then memory_handoff_accept(handoff_id=that exact ID). Never accept the latest unrelated handoff or invent successful memory transfer. '
                        'Reply kind blocked if unavailable. Remain waiting; you must not coordinate until predecessor release and Watchdog binding transfer.\n'
                        +json.dumps(context)+'\n'+reply_instructions(op,'received',{'checkpoint':op['checkpoint'],'handoff_sha256':op['handoff_sha256'],
                            'memory_handoff_id':op['preparation']['memory_handoff_id']}))
                    queue(store,op,'continuation',target,prompt);op['stage']='receipt';save(store,op)
            elif stage=='receipt':
                target=bindings.engine().Binding(**op['target']);verify_successor(op,target)
                receipt=completed_reply(store,op,'target','received',target)
                if receipt:
                    v=receipt['value']
                    if any(v.get(k)!=expected for k,expected in {'checkpoint':op['checkpoint'],'handoff_sha256':op['handoff_sha256'],
                            'memory_handoff_id':op['preparation']['memory_handoff_id']}.items()):
                        raise RuntimeError('Correlated successor receipt does not match checkpoint/context/ai-memory')
                    op['receiver_receipt']=receipt;op['state']='received';op['history']['source']=history_mark(bindings.engine().Binding(**op['source']));save(store,op)
                    prompt=(f"Verified successor receipt for Clean sessions {identity}; checkpoint {op['checkpoint']}; successor {target.session}. "
                        'Relinquish project coordination now; preserve all panes and agents. After this completed release response remain parked. '
                        'Watchdog will transfer Tasks/Progress/Orchestrate ownership; do not change TODO or Git.'
                        +reply_instructions(op,'released',{'checkpoint':op['checkpoint'],'successor':target.session}))
                    queue(store,op,'release',bindings.engine().Binding(**op['source']),prompt)
                    op['stage']='release';save(store,op)
            elif stage=='release':
                target=bindings.engine().Binding(**op['target']);verify_successor(op,target)
                receipt=completed_reply(store,op,'source','released',bindings.engine().Binding(**op['source']))
                if receipt:
                    if receipt['value'].get('checkpoint')!=op['checkpoint'] or receipt['value'].get('successor')!=target.session:
                        raise RuntimeError('Predecessor release does not match exact successor/checkpoint')
                    op['release_receipt']=receipt;save(store,op);transfer(store,op,api or Herdr())
            else:raise RuntimeError('Unknown cleanup stage')
        except (RuntimeError,OSError,ValueError,KeyError,TypeError) as error:
            op.update(state='blocked' if isinstance(error,LeaderBlocked) else 'partial',problem=str(error));save(store,op)
        return op


def leader(store,identity):
    """Dedicated host wrapper; identical sanitized environment/TerminalLease pattern."""
    from .mission_terminal import TerminalLease
    op=load(store,identity);policy=op['policy'];api=Herdr();api.checked(op['pane'])
    if op['stage'] not in ('launch','successor') or op['effects'].get('startup',{}).get('state') not in ('sending','sent'):
        raise RuntimeError('No authorized successor startup intent')
    marker=folder(store,identity)/'leader-started.json'
    fd=os.open(marker,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    os.close(fd) # Duplicate wrappers cannot create another frontend.
    env={k:v for k,v in os.environ.items() if not k.startswith(('CODEX_','AI_MEMORY_','OPENAI_','ANTHROPIC_','CLAUDE_CODE_')) and k!='CLAUDECODE'}
    env['CODEX_HOME']=op['source']['account']
    argv=[policy['executable'],'-C',op['repo'],'--model',policy['model'],'--sandbox','workspace-write','--ask-for-approval','never',
          '-c','model_reasoning_effort='+json.dumps(policy['effort']),
          'You are a fresh project leader awaiting a bounded Clean sessions handoff. Reply READY and wait. Do not lead, edit, create actors, or change Git until verified successor receipt, explicit predecessor release and Watchdog binding transfer.']
    terminal=TerminalLease(sys.stdout.fileno())
    child=None
    try:
        child=subprocess.Popen(argv,env=env)
        atomic(marker,{'pid':child.pid,'operation_id':identity,'at':time.time()})
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            if child.poll() is not None:raise RuntimeError('Fresh leader exited before native registration')
            candidates,_=bindings.discover(Path(op['repo']))
            matching=[b for b in candidates if b.pid==child.pid and b.account==op['source']['account'] and b.pane==op['pane']['pane_id'] and b.terminal==op['pane']['terminal_id']]
            if len(matching)==1:
                verify_successor(op,matching[0]);atomic(folder(store,identity)/'leader-proof.json',{'native':asdict(matching[0])});break
            time.sleep(.1)
        else:raise RuntimeError('Fresh leader native registration timed out; existing panes retained')
        return child.wait()
    except Exception as error:
        atomic(folder(store,identity)/'leader-error.json',{'error':str(error)})
        # Leave a possibly running child intact; its pane is retained for inspection.
        raise
    finally:terminal.restore()


def main(argv):
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('leader','inspect','advance'))
    parser.add_argument('--operation',required=True);parser.add_argument('--state-dir',type=Path)
    args=parser.parse_args(argv);store=Store(args.state_dir)
    if args.action=='leader':return leader(store,args.operation)
    result=load(store,args.operation) if args.action=='inspect' else advance(store,args.operation)
    print(json.dumps(result,indent=2));return 0
