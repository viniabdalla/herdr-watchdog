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
try:
    import tomllib
except ImportError:  # Python 3.10 remains supported without extra dependencies.
    tomllib=None
from urllib.parse import urlsplit
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


SETTLED=('released','closed')


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
    _,pending=owned_changes(repo,[])
    owned=['TODO.md',*sorted(pending-{'TODO.md'})]
    return {'remote':remote,'branch':target,'owned_paths':owned,'integrate':[],
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
        if not isinstance(value[key],list) or (key=='integrate' and len(value[key])>32) or any(not isinstance(s,str) or not s or len(s)>240 for s in value[key]):
            raise RuntimeError('Invalid '+key+' in cleanup scope')
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


def validate_memory_scope(value):
    if (not isinstance(value,dict) or set(value)!={'workspace','project'} or
            any(not isinstance(v,str) or not v or v!=v.strip() or len(v)>128 or
                not all(c.isprintable() for c in v) for v in value.values())):
        raise RuntimeError('ai-memory scope needs bounded nonempty workspace and project names')
    return dict(value)


def scope_marker(raw):
    text=raw.decode('utf-8-sig')
    if tomllib is not None:return tomllib.loads(text)
    # Deliberately only the common two top-level strings on Python 3.10.
    # Reject tables/multiline/duplicate keys instead of guessing TOML context.
    values={}
    pattern=r'''(workspace|project)\s*=\s*("(?:[^"\\\r\n]|\\(?:["\\bfnrt]|u[0-9a-fA-F]{4}))*"|'[^'\r\n]*')\s*(?:#.*)?'''
    for line in text.splitlines():
        line=line.strip()
        if not line or line.startswith('#'):continue
        match=re.fullmatch(pattern,line)
        if not match or match[1] in values:
            raise RuntimeError('Python 3.10 scope marker has unsupported or ambiguous TOML; use unique top-level workspace/project strings')
        values[match[1]]=json.loads(match[2]) if match[2].startswith('"') else match[2][1:-1]
    return values


def memory_scope(repo):
    """Existing ai-memory routing convention, made explicit for the static MCP."""
    repo=Path(repo).resolve()
    for parent in (repo,*repo.parents):
        marker=parent/'.ai-memory.toml'
        if not marker.exists():continue
        if marker.is_symlink():raise RuntimeError('ai-memory scope marker must be a regular file')
        with marker.open('rb') as stream:raw=stream.read(16385)
        if len(raw)>16384:raise RuntimeError('ai-memory scope marker exceeds bounds')
        data=scope_marker(raw)
        if 'workspace' in data and 'project' in data:
            return validate_memory_scope({k:data[k] for k in ('workspace','project')})
        break
    for remote in ('upstream','origin'):
        try:url=git(repo,'remote','get-url',remote)
        except RuntimeError:continue
        path=None
        if '://' in url:
            try:
                parsed=urlsplit(url)
                if parsed.scheme in ('https','http','ssh','git') and parsed.hostname:path=parsed.path
            except ValueError:pass
        else:
            match=re.fullmatch(r'(?:[^/@:]+@)?([^/:]{2,}):([^\\]+)',url)
            if match:path=match[2]
        if not path:continue  # Local filesystem/bare remotes are not hosted identity.
        path=path.strip('/').lower()
        if path.endswith('.git'):path=path[:-4]
        project=re.sub('-+','-',''.join(c if c.isalnum() or c in '-_.' else '-' for c in path)).strip('-')
        if project:return validate_memory_scope({'workspace':'default','project':project})
    return validate_memory_scope({'workspace':'default','project':repo.name.lower()})


def request(session,policy,*,confirmed=False,store=None,automatic=False):
    if not confirmed:raise RuntimeError('Explicit cleanup confirmation is required')
    store=store or Store();live=session.verify()
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
            if previous['state'] not in SETTLED:
                raise RuntimeError('Clean sessions '+previous['operation_id'][:8]+' is '+previous['state']+'; press c to retry or close it')
        native_boundary(store,session.repo)
        leader_dir=live.get('foreground_cwd') or live.get('cwd') or session.repo
        if Path(git(leader_dir,'rev-parse','--show-toplevel')).resolve()!=session.repo:
            raise RuntimeError('Leader directory does not identify the selected Git worktree')
        approved=policy_for(session,policy)
        op={'version':1,'operation_id':str(uuid.uuid4()),'repo':str(session.repo),'binding_file':str(session.file),
            'source':asdict(session.binding),'memory_scope':memory_scope(session.repo),'base_sha':git(session.repo,'rev-parse','HEAD'),'policy':approved,
            'automatic':automatic,'state':'pending','stage':'preparation','effects':{},'created':time.time(),
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
            'Call the ACTUAL ai-memory MCP tool memory_handoff_begin with explicit workspace+project '+json.dumps(op['memory_scope'],sort_keys=True)+', plus summary (2–3 sentences), open_questions (short strings), next_steps (unfinished tasks/next actions) and files_touched. Include this operation UUID in the saved summary. Immediately call the read-only memory_handoff_list with the SAME explicit workspace+project and verify the returned exact handoff ID is present in that scope. Only then attest memory_handoff_list_verified=true and copy this exact memory_scope in the prepared reply. These are your attestations of actual MCP responses, not an independent service audit. Never omit scope, guess whether this client is session-aware, or use the server current/last active project. Keep operator sharing default; if explicit-scope verification fails, report blocked. '
            'If ai-memory or preparation is unavailable, report kind blocked with reason instead; do not invent a handoff ID. '
            'For references, supply at most 8 existing ABSOLUTE regular-file paths: no :line/#line citations, no directories, no duplicate references. Verify each path first; use [] if no verified paths are available. Exact absolute file-path example for this project: '+json.dumps(str(session.repo/'TODO.md'))+'. Do not append a line number or fragment. '
            'No full transcripts. This is a project baton transfer; legacy runs remain historical export-only. '
            'The backend commits authorized owned files, fast-forwards only listed pinned branches, pushes to the explicit destination, verifies a checkpoint, and opens a fresh dedicated leader. '
            'You remain leader until actual successor receipt and your explicit release.\n'
            +reply_instructions(op,'prepared',{'todo_reconciled':True,'memory_handoff_id':'ACTUAL_ID','memory_scope':op['memory_scope'],
                'memory_handoff_list_verified':True,'summary':'Concise continuation',
                'open_questions':[],'unfinished_tasks':[],'next_steps':[],'references':[]}))
        if automatic:
            prompt += ('\nIn your prepared JSON also include owned_paths: the subset of the candidate '
                       'paths in the authorized scope that you verified belongs to this work. Include '
                       'TODO.md for reconciliation. Leave unrelated changes for their owner. '
                       'If ownership needs a user decision report blocked.')
        try:queue(store,op,'prepare',session.binding,prompt)
        except Exception as error:op.update(state='partial',problem='Preparation delivery uncertain: '+str(error));save(store,op)
        return op


def completed_reply(store,op,who,kind,binding):
    """Only post-request completed assistant events from the pinned native history."""
    bindings.verify(binding)
    mark=op['history'][who];p=Path(binding.history);s=p.stat()
    if p.is_symlink() or (s.st_ino,s.st_dev)!=(mark['inode'],mark['device']) or s.st_size<mark['offset']:
        raise RuntimeError('Native receipt history was replaced or truncated')
    found=[]
    offset=mark['offset']
    with p.open('rb') as stream:
        stream.seek(mark['offset'])
        while stream.tell()<s.st_size:
            line=stream.readline(s.st_size-stream.tell())
            if not line.endswith(b'\n'):break
            offset=stream.tell()
            row=json.loads(line)
            if not isinstance(row,dict):continue
            payload=row.get('payload',{})
            if not isinstance(payload,dict):continue
            if row.get('type')!='event_msg' or payload.get('type')!='task_complete':continue
            text=payload.get('last_agent_message','')
            if not isinstance(text,str) or not text.startswith(PREFIX):continue
            if len(text)>LIMIT:raise RuntimeError('Native receipt exceeds size bound')
            value=json.loads(text[len(PREFIX):])
            if value.get('operation_id')!=op['operation_id']:continue
            if value.get('token')!=op['tokens'][kind]:raise RuntimeError('Receipt operation token differs')
            if value.get('kind')=='blocked':
                raise LeaderBlocked('Leader reports blocked: '+str(value.get('reason','Preparation unavailable'))[:500])
            if value.get('token')!=op['tokens'][kind] or value.get('kind')!=kind:
                raise RuntimeError('Receipt operation token or phase differs')
            found.append({'value':value,'turn_id':payload.get('turn_id'),'sha256':handoff.digest(row)})
    if len(found)>1:raise RuntimeError('Duplicate native confirmations require inspection')
    if found:return found[0]
    mark['offset']=offset;save(store,op)
    return None


def source_session(op):
    session=Session(op['binding_file'],Path(op['repo']))
    current=asdict(session.binding)
    if current!=op['source']:
        state=handoff.read_json(op['binding_file'])
        original=op['source']
        if (original not in state.get('reopened',[]) or
                any(current[k]!=original[k] for k in ('kind','session','account','workspace','history'))):
            raise RuntimeError('Current leader binding was replaced')
        op.setdefault('original_source',original)
        op['source']=current
    return session


def checkpoint_current(op):
    repo=op['repo'];policy=op['policy']
    if (git(repo,'symbolic-ref','--short','HEAD')!=policy['branch'] or
        handoff.digest(git(repo,'remote','get-url','--push',policy['remote']))!=policy['remote_digest']):
        raise RuntimeError('Approved branch or push remote changed')
    if op.get('checkpoint'):
        if git(repo,'rev-parse','HEAD')!=op['checkpoint'] or owned_changes(repo,op.get('checkpoint_paths',policy['owned_paths']))[0]:
            raise RuntimeError('Checkpoint is stale or its owned files changed')
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


def git_names(repo,*args):
    """Read NUL-separated names without trimming filename whitespace."""
    try:
        result=subprocess.run(['git','-C',str(repo),*args],capture_output=True,
            timeout=20,env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')})
    except subprocess.TimeoutExpired as error:
        raise RuntimeError('Git ownership inspection timed out; no retry') from error
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace').strip() or 'Git ownership inspection failed')
    return {os.fsdecode(name) for name in result.stdout.split(b'\0') if name}


def owned_changes(repo,allowed):
    # Compare HEAD/index and index/worktree independently. A restored worktree
    # can hide an unowned staged entry from a single worktree-versus-HEAD diff.
    changed=git_names(repo,'diff','--cached','--name-only','--no-renames','-z','HEAD')
    changed.update(git_names(repo,'diff','--name-only','--no-renames','-z'))
    changed.update(git_names(repo,'ls-files','--others','--exclude-standard','-z'))
    # Files outside the authorized list are never committed; they stay untouched
    # in the worktree (e.g. a note another conversation dropped meanwhile).
    return changed&set(allowed),changed-set(allowed)


def verify_preparation_commits(repo,base,head,allowed):
    """Every new commit must descend linearly from base and touch only owned files."""
    if base==head:return
    parent=base
    for line in git(repo,'rev-list','--reverse','--parents',base+'..'+head).splitlines():
        commit,*parents=line.split()
        if parents!=[parent]:
            raise RuntimeError('Branch history diverged during preparation; review the worktree')
        files=git_names(repo,'diff','--name-only','--no-renames','-z',parent,commit)
        outside=files-set(allowed)
        if outside:
            raise RuntimeError('Concurrent commit includes files outside the handoff: '+', '.join(sorted(outside)))
        parent=commit
    if parent!=head:
        raise RuntimeError('Branch history changed during preparation; review the worktree')


def prepare_checkpoint(store,op,receipt):
    v=receipt['value']
    if not v.get('memory_handoff_id') or v['memory_handoff_id']=='ACTUAL_ID':
        raise RuntimeError('ai-memory handoff unavailable; memory was not transferred')
    scope=validate_memory_scope(v.get('memory_scope'))
    if scope!=op['memory_scope'] or v.get('memory_handoff_list_verified') is not True:
        raise RuntimeError('ai-memory scope must match the explicit request and have exact-ID list verification attested')
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
    allowed=policy['owned_paths']
    if op.get('automatic'):
        selected=v.get('owned_paths')
        if not isinstance(selected,list) or 'TODO.md' not in selected or any(not isinstance(p,str) or p not in allowed for p in selected):
            raise RuntimeError('Leader must identify owned files within the proposed handoff scope')
        allowed=selected
    verify_preparation_commits(repo,op['base_sha'],git(repo,'rev-parse','HEAD'),allowed)
    changed,unowned=owned_changes(repo,allowed)
    op['checkpoint_paths']=allowed
    if unowned:op['left_uncommitted']=sorted(unowned)[:32]
    for name in changed:
        p=repo/name
        if p.is_symlink() or not p.resolve().is_relative_to(repo):raise RuntimeError('Owned file path was replaced')
    op['preparation']={k:v[k] for k in ('summary','memory_handoff_id','memory_scope','memory_handoff_list_verified','open_questions','unfinished_tasks','next_steps')}
    op['preparation_receipt']=receipt;save(store,op)
    if changed:
        effect(store,op,'stage-owned',lambda:git(repo,'--literal-pathspecs','add','--',*sorted(changed)))
        # Recheck after staging, then constrain Git's commit pathspec as well:
        # a concurrent unrelated index entry must never enter this commit.
        if owned_changes(repo,allowed)[0]!=changed:raise RuntimeError('Owned files changed while staging')
        effect(store,op,'commit-owned',lambda:git(repo,'--literal-pathspecs','commit','--only','-m',
            'Clean sessions: reconcile owned project checkpoint','--',*sorted(changed)))
    head=git(repo,'rev-parse','HEAD')
    verify_preparation_commits(repo,op['base_sha'],head,allowed)
    for ref,sha in policy['integration_heads'].items():
        if git(repo,'rev-parse','--verify',ref+'^{commit}')!=sha:raise RuntimeError('Approved integration branch changed')
        if git(repo,'rev-parse','HEAD')!=head:raise RuntimeError('Branch changed before integration')
        effect(store,op,'integrate:'+ref,lambda:git(repo,'merge','--ff-only',sha))
        merged=git(repo,'rev-parse','HEAD')
        if merged not in (head,sha):raise RuntimeError('Branch changed during integration')
        head=merged
    if owned_changes(repo,allowed)[0]:raise RuntimeError('Owned files are dirty after integration')
    effect(store,op,'push',lambda:git(repo,'push',policy['remote'],head+':refs/heads/'+policy['branch']))
    remote=git(repo,'ls-remote','--heads',git(repo,'remote','get-url','--push',policy['remote']),'refs/heads/'+policy['branch']).split()
    if not remote or remote[0]!=head:raise RuntimeError('Push checkpoint not verified')
    op['checkpoint']=head
    context={'version':1,'operation_id':op['operation_id'],'project':op['repo'],'checkpoint':head,
             'continuation_file':str(folder(store,op['operation_id'])/'continuation.json'),
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


def predates_leader(agent,source,api):
    """Recognize an already-running Codex process in a different Herdr pane."""
    pane=agent.get('pane_id')
    if not pane or pane==source['pane']:return False
    info=api.call('pane','process-info','--pane',pane)['process_info']
    processes=info.get('foreground_processes',[])
    if len(processes)!=1:return False
    process=processes[0]
    argv=process.get('argv',[])
    if process.get('name')!='codex' or not argv or 'resume' in argv:return False
    try:
        stat=Path('/proc',str(process['pid']),'stat').read_text()
        started=int(stat.rsplit(')',1)[1].split()[19])
        return started<int(source['started'])
    except (OSError,KeyError,IndexError,ValueError):
        return False


def predecessor_exited(op, api):
    """Distinguish a closed leader from a busy, unregistered or resumed thread."""
    source=op['source']
    try:
        stat=Path('/proc',str(source['pid']),'stat').read_text()
    except FileNotFoundError:
        pass
    else:
        if stat.rsplit(')',1)[1].split()[19]==str(source['started']):
            return False
    state=handoff.read_json(op['binding_file'])
    if state.get('binding')!=source or state.get('ownership') in ('released','transferring'):
        return False
    panes=api.call('pane','list')['panes']
    if any(pane['pane_id']==source['pane'] for pane in panes):
        return False
    agents=api.call('agent','list')['agents']
    for agent in agents:
        if agent.get('agent')!='codex':continue
        sid=(agent.get('agent_session') or {}).get('value')
        if sid==source['session']:return False
        if not sid and agent.get('workspace_id')==source['workspace'] and not predates_leader(agent,source,api):
            return False
    return True


def transfer(store,op,api):
    old=bindings.engine().Binding(**op['source'])
    new=bindings.engine().Binding(**op['target'])
    def verify_leaders():
        verify_successor(op,new)
        if op.get('predecessor_exit'):
            if not op.get('receiver_receipt') or not predecessor_exited(op,api):
                raise RuntimeError('Cannot confirm predecessor exit and successor receipt')
        elif source_session(op).verify().get('agent_status') not in ('idle','done'):
            raise RuntimeError('Predecessor must finish its release turn')
        if bindings.verify(new).get('agent_status') not in ('idle','done'):
            raise RuntimeError('Successor must finish its receipt turn')
    verify_leaders()
    checkpoint_current(op);native_boundary(store,Path(op['repo']))
    state=handoff.read_json(op['binding_file'])
    for role,pane in state.get('panes',{}).items():
        if role!='left_undone':api.panel(pane,op['repo'])
    api.checked(op['pane'])
    rs=RunStore(store.root/'runs');run=policy_run(store,op)
    with handoff.session_leases(rs,run,[op['source'],op['target']]) as slots:
        handoff.reserve_current_main(run,slots);handoff.fresh_main(run,op['target'],slots)
        verify_leaders()
        checkpoint_current(op)
        # Intent is saved before reservation / Store mutation. Interrupted rebind
        # is visible and blocked; it never activates both coordinators.
        op['effects']['rebind']={'state':'sending'};save(store,op)
        handoff.write_claim(slots,op['target'],handoff.main_claim(run))
        op['new_binding_file']=store.transfer(op['binding_file'],old,new,Path(op['repo']),op['operation_id'],api=api)
    op['effects']['rebind']['state']='sent';save(store,op)
    queue(store,op,'activation',new,
          f"Clean sessions {op['operation_id']}: leadership transfer was verified; Watchdog panel ownership and Orchestrate now target your exact thread {new.session}. "
          f"Verified checkpoint {op['checkpoint']}; binding {op['new_binding_file']}. You are the project leader. Keep unfinished tasks open and preserve existing actors/panes.")
    op.update(state='released',stage='released');save(store,op)


def validate_memory_receipt(op,value):
    """Validate the receiver's explicit hook/tool attestation, retaining its source."""
    evidence=value.get('memory_receipt')
    if not isinstance(evidence,dict):raise RuntimeError('Explicit ai-memory receipt evidence is required')
    if evidence.get('operation_id')!=op['operation_id'] or evidence.get('project')!=op['repo']:
        raise RuntimeError('ai-memory receipt operation/project does not match continuation')
    if validate_memory_scope(evidence.get('memory_scope'))!=op['preparation']['memory_scope']:
        raise RuntimeError('ai-memory receipt scope differs from the saved predecessor scope')
    common={'method','operation_id','project','memory_scope'}
    if evidence.get('method')=='session_start_hook':
        excerpt=evidence.get('operation_excerpt')
        if (set(evidence)!=common|{'operation_excerpt'} or not isinstance(excerpt,str) or
                len(excerpt)>1000 or op['operation_id'] not in excerpt):
            raise RuntimeError('ai-memory SessionStart receipt needs matching operation content; no tool acceptance is inferred')
    elif evidence.get('method')=='exact_id_tool_accept':
        if (set(evidence)!=common|{'accepted_handoff_id'} or
                evidence.get('accepted_handoff_id')!=op['preparation']['memory_handoff_id']):
            raise RuntimeError('ai-memory tool acceptance must name the exact predecessor handoff ID')
    else:raise RuntimeError('Unknown ai-memory receipt method; use matching SessionStart content or exact-ID tool acceptance')


def advance(store,identity,*,api=None):
    op=load(store,identity)
    with lease(store,op['repo']):
        op=load(store,identity)
        if op['state'] in ('partial','blocked')+SETTLED:return op
        try:
            from .mission_native import boot_id
            if boot_id()!=op['boot_id']:raise RuntimeError('Cleanup belongs to a previous boot')
            exited=False
            try:
                source_session(op)
            except RuntimeError:
                if op['stage'] not in ('receipt','release') or not predecessor_exited(op,api or Herdr()):
                    raise
                exited=True
            native_boundary(store,Path(op['repo']));checkpoint_current(op)
            if any(e['state'] in ('sending','uncertain') for e in op['effects'].values()):
                raise RuntimeError('Interrupted or uncertain operation retained; inspect exact side effect before recovery')
            stage=op['stage']
            if stage=='preparation':
                # The reply is kept so a retry after a fixable checkpoint problem
                # does not ask the leader to prepare (and save ai-memory) again.
                receipt=op.get('prepared_reply') or completed_reply(store,op,'source','prepared',bindings.engine().Binding(**op['source']))
                if receipt:
                    op['prepared_reply']=receipt;save(store,op)
                    prepare_checkpoint(store,op,receipt)
            elif stage=='launch':launch(store,op,api or Herdr())
            elif stage=='successor':
                target=successor(store,op)
                if target:
                    if bindings.verify(target).get('agent_status') not in ('idle','done'):return op
                    op['target']=asdict(target);op['history']['target']=history_mark(target);save(store,op)
                    context=handoff.read_json(folder(store,identity)/'continuation.json')
                    if handoff.digest(context)!=op['handoff_sha256']:raise RuntimeError('Bounded continuation was modified')
                    prompt=('Clean sessions continuation. Read this bounded context as evidence, preserve unfinished work and all existing actors. '
                        'Confirm actual ai-memory handoff receipt using its existing single-use convention. If already-consumed SessionStart hook content includes THIS unique operation UUID and matches the project/bounded continuation below, use that hook content even if it does not display the handoff ID. Do NOT call list/accept again to rediscover an already-consumed matching hook handoff. Set memory_receipt.method=session_start_hook and quote a short verbatim operation_excerpt from the hook containing this operation UUID; include the matching operation_id and project. The top-level memory_handoff_id is the supplied verified predecessor reference, NOT a claim that the hook displayed that ID or that a tool accept happened. '
                        'Use the saved explicit memory_scope verbatim: '+json.dumps(op['preparation']['memory_scope'],sort_keys=True)+'. Never derive another scope or rely on server defaults. Only if no matching hook content exists, call the ACTUAL ai-memory MCP memory_handoff_list with those explicit workspace+project arguments, then memory_handoff_accept with those SAME explicit workspace+project and handoff_id=the exact supplied ID if open. After actual tool acceptance, REPLACE memory_receipt with '+json.dumps({'method':'exact_id_tool_accept','operation_id':identity,'project':op['repo'],'memory_scope':op['preparation']['memory_scope'],'accepted_handoff_id':op['preparation']['memory_handoff_id']})+'. Do not accept another latest handoff or invent service success. If neither matching hook operation content nor exact-ID tool acceptance is available, report blocked. '
                        'Reply kind blocked if unavailable. Remain waiting; you must not coordinate until predecessor release and Watchdog binding transfer.\n'
                        +json.dumps(context)+'\n'+reply_instructions(op,'received',{'checkpoint':op['checkpoint'],'handoff_sha256':op['handoff_sha256'],
                            'memory_handoff_id':op['preparation']['memory_handoff_id'],
                            'memory_receipt':{'method':'session_start_hook','operation_id':identity,'project':op['repo'],
                                'memory_scope':op['preparation']['memory_scope'],
                                'operation_excerpt':'REPLACE with verbatim SessionStart hook content containing this operation UUID'}}))
                    queue(store,op,'continuation',target,prompt);op['stage']='receipt';save(store,op)
            elif stage=='receipt':
                target=bindings.engine().Binding(**op['target']);verify_successor(op,target)
                receipt=op.get('receiver_receipt') or completed_reply(store,op,'target','received',target)
                if receipt:
                    v=receipt['value']
                    if any(v.get(k)!=expected for k,expected in {'checkpoint':op['checkpoint'],'handoff_sha256':op['handoff_sha256'],
                            'memory_handoff_id':op['preparation']['memory_handoff_id']}.items()):
                        raise RuntimeError('Correlated successor receipt does not match checkpoint/context/ai-memory')
                    validate_memory_receipt(op,v)
                    op['receiver_receipt']=receipt;op['state']='received'
                    if exited:
                        op['predecessor_exit']={'session':op['source']['session'],'at':time.time()}
                        op['stage']='release';save(store,op)
                        if bindings.verify(target).get('agent_status') in ('idle','done'):
                            transfer(store,op,api or Herdr())
                        return op
                    op['history']['source']=history_mark(bindings.engine().Binding(**op['source']));save(store,op)
                    prompt=(f"Verified successor receipt for Clean sessions {identity}; checkpoint {op['checkpoint']}; successor {target.session}. "
                        'Relinquish project coordination now; preserve all panes and agents. After this completed release response remain parked. '
                        'Watchdog will transfer Tasks/Progress/Orchestrate ownership; do not change TODO or Git.'
                        +reply_instructions(op,'released',{'checkpoint':op['checkpoint'],'successor':target.session}))
                    queue(store,op,'release',bindings.engine().Binding(**op['source']),prompt)
                    op['stage']='release';save(store,op)
            elif stage=='release':
                target=bindings.engine().Binding(**op['target']);verify_successor(op,target)
                if not exited and op.pop('predecessor_exit',None) and 'release' not in op['effects']:
                    op['stage']='receipt';save(store,op)
                    return op
                if exited and op.get('receiver_receipt'):
                    if bindings.verify(target).get('agent_status') not in ('idle','done'):return op
                    op['predecessor_exit']={'session':op['source']['session'],'at':time.time()}
                    save(store,op);transfer(store,op,api or Herdr())
                    return op
                receipt=op.get('release_receipt') or completed_reply(store,op,'source','released',bindings.engine().Binding(**op['source']))
                if receipt:
                    if receipt['value'].get('checkpoint')!=op['checkpoint'] or receipt['value'].get('successor')!=target.session:
                        raise RuntimeError('Predecessor release does not match exact successor/checkpoint')
                    op['release_receipt']=receipt;save(store,op);transfer(store,op,api or Herdr())
            else:raise RuntimeError('Unknown cleanup stage')
        except (RuntimeError,OSError,ValueError,KeyError,TypeError) as error:
            op.update(state='blocked' if isinstance(error,LeaderBlocked) else 'partial',problem=str(error));save(store,op)
        return op


def retry(store,identity):
    """Resume a partial operation from the step that failed; side effects are never repeated."""
    op=load(store,identity)
    with lease(store,op['repo']):
        op=load(store,identity)
        if op['state']!='partial':raise RuntimeError('Only a partial operation can be retried; close this one instead')
        unsure=[k for k,e in op['effects'].items() if e['state'] in ('sending','uncertain')]
        if unsure:raise RuntimeError('Step '+', '.join(unsure)+' may have half-run; close this operation instead of retrying')
        from .mission_native import boot_id
        op.setdefault('retries',[]).append({'at':time.time(),'problem':op.get('problem')})
        op.update(state='pending',boot_id=boot_id());op.pop('problem',None);save(store,op)
        return op


def close(store,identity,reason='closed by user in Tasks'):
    """Stop a stuck operation so new work can flow; its record stays as evidence."""
    op=load(store,identity)
    with lease(store,op['repo']):
        op=load(store,identity)
        if op['state'] in SETTLED:return op
        if op['effects'].get('rebind',{}).get('state') in ('sending','uncertain'):
            raise RuntimeError('Panel transfer was interrupted mid-way; inspect the binding files before closing')
        op['closed']={'at':time.time(),'reason':reason,'state':op['state'],'stage':op['stage'],'problem':op.get('problem')}
        op['state']='closed';save(store,op)
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
    argv=[policy['executable'],'-C',op['repo'],'--model',policy['model'],'--yolo',
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
