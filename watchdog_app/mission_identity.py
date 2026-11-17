"""Bootstrap on the host, then publish only from the participant's own request."""
from dataclasses import asdict
import json
from pathlib import Path
import time

from . import bindings
from .mission_launch import command, owned_worktree
from .store import atomic


def check_context(context, native):
    if (context.get('session_id') != native['session'] or
            context.get('owner_pid') != native['pid'] or
            str(context.get('owner_start')) != str(native['started'])):
        raise RuntimeError('Gossip context does not match the verified native participant')
    for key in ('context_file', 'state_file'):
        if not isinstance(context.get(key), str) or not Path(context[key]).is_absolute():
            raise RuntimeError('Gossip context paths must be absolute')


def bootstrap(store, identity, role, child, *, timeout=45):
    """Called by the owned Herdr wrapper, outside the child Codex sandbox.

    Never clear or replace CODEX_THREAD_ID to perform another task's operations.
    Gossip itself checks that the wrapper may bind the independently verified PID.
    """
    run=store.load(identity);part=run['participants'][role];pane=run['resources'][role]
    from . import mission_native
    if mission_native.enabled(run):return mission_native.bootstrap(store,identity,role,child,timeout=timeout)
    owned_worktree(run,role)
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if child.poll() is not None:
            raise RuntimeError('Participant exited before native identity registration')
        candidates,_=bindings.discover(Path(part['worktree']))
        matching=[b for b in candidates if b.kind=='codex' and b.account==part['account'] and
                  b.pane==pane['pane_id'] and b.terminal==pane['terminal_id'] and b.pid==child.pid]
        if len(matching)==1:
            binding=matching[0];bindings.verify(binding)
            break
        time.sleep(.1)
    else:
        raise RuntimeError('Native participant registration timed out; owned terminal retained')
    native=asdict(binding)
    context=json.loads(command(['agent-gossip','context','bind','--session-id',binding.session,
                                '--owner-pid',str(binding.pid)]))
    check_context(context,native)
    bindings.verify(binding)
    command(['agent-gossip','join',run['transport']['gossip'],'--nickname',part['nickname'],
             '--owner-pid',str(binding.pid),'--state-file',context['state_file'],
             '--session-context',context['context_file']])
    state=json.loads(Path(context['state_file']).read_text())
    if (not state.get('ready') or state.get('gossip')!=run['transport']['gossip'] or
            state.get('nickname')!=part['nickname'] or not state.get('pubkey')):
        raise RuntimeError('Participant Gossip startup identity differs')
    expected={k:context[k] for k in ('session_id','generation','owner_pid','owner_start','boot_id')}
    if state.get('session_context')!=expected:
        raise RuntimeError('Participant Gossip peer is not owned by its native context')
    folder=store.root/identity
    atomic(folder/(role+'-gossip.json'),state)
    proof={'native':native,'context':context,'pubkey':state['pubkey'],
           'broker':str(folder/(role+'-broker.sock'))}
    atomic(folder/(role+'-identity.json'),proof)
    return proof


def enroll(store, identity, role):
    """Run inside the assigned Codex request; signing as another task is forbidden."""
    from .mission_transport import publish_identity, verify_graph, Gossip
    run=store.load(identity);part=run['participants'][role]
    proof=json.loads((store.root/identity/(role+'-identity.json')).read_text())
    if proof.get('broker'):
        from .mission_broker import request
        return request(store,identity,role,'enroll')
    if run.get('transport',{}).get('kind')=='native':
        raise RuntimeError('Native enrollment requires its authenticated host bridge')
    native=proof['native'];context=json.loads(command(['agent-gossip','context','show']))
    check_context(context,native)
    if context!=proof['context']:
        raise RuntimeError('Participant context generation changed; host must reverify')
    pane=run['resources'][role]
    if (native['account']!=part['account'] or native['pane']!=pane['pane_id'] or
            native['terminal']!=pane['terminal_id']):
        raise RuntimeError('Participant native binding differs from its assigned terminal/account')
    state=json.loads(Path(context['state_file']).read_text())
    if (state.get('pubkey')!=proof['pubkey'] or state.get('nickname')!=part['nickname'] or
            state.get('gossip')!=run['transport']['gossip']):
        raise RuntimeError('Participant local Gossip signer changed')
    part.update(native=native,pubkey=proof['pubkey'])
    publish_identity(run,role)
    verify_graph(run,role,gossip=Gossip(run['transport'],part['nickname']))
    return {'role':role,'session':native['session'],'pubkey':proof['pubkey'],'published':True}


def recover_role(store, identity, role, *, confirmed=False, api=None):
    """Restart an undispatched, owned actor in its original conversation and terminal.

    Every side effect has a durable intent. A failed/uncertain recovery is inspected,
    never repeated. No worktree, branch, room or source file is removed.
    """
    import os
    import signal
    import shlex
    import sys
    from .mission_launch import main_session, source_current, git, ROOT
    from .herdr import Herdr
    if not confirmed:
        raise RuntimeError('Explicit participant recovery confirmation is required')
    with store.lock(identity):
        run=store.load(identity);main_session(run);source_current(run)
        if role not in ('worker','qa') or run['phase']!='active':
            raise RuntimeError('Only an active run participant can be recovered')
        if run.get('transport',{}).get('kind')=='native':
            raise RuntimeError('Native actor transition requires a verified idle host wrapper; no automatic restart')
        if any(t.get('delivery') or t.get('gossip_task') for t in run['tasks'].values()) or run.get('qa_task'):
            raise RuntimeError('Recovery refuses dispatched work; inspect its exact task first')
        part=run['participants'][role]
        previous=part.get('identity_recovery')
        if previous and previous.get('state')!='started':
            raise RuntimeError('Participant recovery already attempted; inspect its retained intent')
        path=owned_worktree(run,role)
        if git(path,'status','--porcelain') or git(path,'rev-parse','HEAD')!=run['brief']['base_sha']:
            raise RuntimeError('Recovery requires the clean original worker/QA base')
        pane=run['resources'][role];api=api or Herdr(run.get('herdr_session'));api.checked(pane)
        candidates,_=bindings.discover(path)
        matching=[b for b in candidates if b.kind=='codex' and b.account==part['account'] and
                  b.pane==pane['pane_id'] and b.terminal==pane['terminal_id']]
        if len(matching)!=1:raise RuntimeError('Recovery native identity is missing or ambiguous')
        binding=matching[0];bindings.verify(binding)
        folder=store.root/identity
        marker=json.loads((folder/(role+'-started.json')).read_text())
        state=json.loads((folder/(role+'-gossip.json')).read_text())
        status=Path('/proc')/str(binding.pid)/'status'
        parent=next(int(line.split()[1]) for line in status.read_text().splitlines() if line.startswith('PPid:'))
        if (parent!=marker['pid'] or marker['pane']['terminal_id']!=pane['terminal_id'] or
                state.get('gossip')!=run['transport']['gossip'] or state.get('nickname')!=part['nickname']):
            raise RuntimeError('Recovery actor or peer differs from its owned resources')
        if state.get('session_context'):
            proof=json.loads((folder/(role+'-identity.json')).read_text())
            if proof['native']!=asdict(binding) or proof['pubkey']!=state['pubkey']:
                raise RuntimeError('Recovery native context proof differs')
            check_context(proof['context'],asdict(binding))
            expected={k:proof['context'][k] for k in ('session_id','generation','owner_pid','owner_start','boot_id')}
            if state['session_context']!=expected or state['owner_pid']!=binding.pid:
                raise RuntimeError('Recovery peer context changed')
        elif state.get('owner_pid')!=marker['pid'] or previous:
            raise RuntimeError('Recovery wrapper ownership is ambiguous')
        if previous:part.setdefault('identity_recovery_history',[]).append(previous)
        run['identity_protocol']=2
        part['identity_recovery']={'state':'stopping','native':asdict(binding),'at':time.time()}
        store.save(run)
        # This exact Codex was created by this run, has no assignment, and will
        # resume the same thread. Never signal its shell, Herdr, or another agent.
        bindings.verify(binding)
        os.kill(binding.pid,signal.SIGTERM)
    deadline=time.monotonic()+20
    while time.monotonic()<deadline:
        live=api.checked(pane)
        if live['tab_id']!=run['tab']:raise RuntimeError('Owned recovery pane moved')
        info=api.call('pane','process-info','--pane',pane['pane_id'])['process_info']
        busy=any(p['pid']!=info['shell_pid'] for p in info['foreground_processes'])
        daemon=Path('/proc')/str(state['pid'])/'stat'
        daemon_live=daemon.exists() and daemon.read_text().rsplit(')',1)[1].split()[0]!='Z'
        if not busy and not daemon_live:break
        time.sleep(.1)
    else:raise RuntimeError('Owned actor or Gossip peer has not exited; recovery intent retained')
    with store.lock(identity):
        run=store.load(identity);main_session(run);part=run['participants'][role]
        archive=folder/('identity-recovery-'+role+'-'+str(__import__('uuid').uuid4()));archive.mkdir(mode=0o700)
        for suffix in ('started.json','exit.json','gossip.json','identity.json','bootstrap-error.json'):
            source=folder/(role+'-'+suffix)
            if source.exists():source.rename(archive/source.name)
        part['resume_session']=binding.session
        part.pop('native',None);part.pop('pubkey',None);part['available']=False
        part['identity_recovery']['state']='starting';store.save(run)
        argv=[sys.executable,str(ROOT/'watchdog'),'mission','participant','--run',identity,
              '--role',role,'--state-dir',str(store.root)]
        from .mission_terminal import reset_owned_shell
        reset_owned_shell(api,pane)
        api.checked(pane);api.call('pane','run',pane['pane_id'],shlex.join(argv))
        part['identity_recovery']['state']='started';store.save(run)
        return {'run':identity,'role':role,'pane':pane['pane_id'],'tab':run['tab'],
                'resume_session':binding.session,'started':True}


def recover_unstarted(store,identity,role,*,confirmed=False,api=None):
    """Repair only a retained recovery whose pane command never started a wrapper."""
    import shlex
    import sys
    from .mission_launch import main_session,source_current,git,ROOT
    from .mission_terminal import reset_owned_shell
    from .herdr import Herdr
    if not confirmed:raise RuntimeError('Explicit recovery confirmation is required')
    with store.lock(identity):
        run=store.load(identity);main_session(run);source_current(run)
        part=run['participants'][role];recovery=part.get('identity_recovery',{})
        if recovery.get('state')!='started' or recovery.get('terminal_repair') not in (None,'sent'):
            raise RuntimeError('No unstarted recovery is eligible; inspect its intent')
        if run.get('transport',{}).get('kind')=='native':
            raise RuntimeError('Native actor transition requires a verified idle host wrapper; no automatic restart')
        if any(t.get('delivery') or t.get('gossip_task') for t in run['tasks'].values()) or run.get('qa_task'):
            raise RuntimeError('Recovery refuses dispatched work')
        folder=store.root/identity
        if (folder/(role+'-started.json')).exists():
            raise RuntimeError('Wrapper already started; no second process was launched')
        path=owned_worktree(run,role)
        if git(path,'status','--porcelain') or git(path,'rev-parse','HEAD')!=run['brief']['base_sha']:
            raise RuntimeError('Recovery requires the clean original base')
        pane=run['resources'][role];api=api or Herdr(run.get('herdr_session'));live=api.checked(pane)
        if live['tab_id']!=run['tab']:raise RuntimeError('Owned recovery tab changed')
        info=api.call('pane','process-info','--pane',pane['pane_id'])['process_info']
        if any(p['pid']!=info['shell_pid'] for p in info['foreground_processes']):
            raise RuntimeError('Owned shell is busy; no recovery command was sent')
        if part.get('resume_session')!=recovery['native']['session']:
            raise RuntimeError('Retained conversation identity changed')
        if recovery.get('terminal_repair'):
            recovery.setdefault('terminal_repair_history',[]).append({'state':recovery['terminal_repair'],'at':time.time()})
        recovery['terminal_repair']='starting';store.save(run)
        reset_owned_shell(api,pane)
        argv=[sys.executable,str(ROOT/'watchdog'),'mission','participant','--run',identity,
              '--role',role,'--state-dir',str(store.root)]
        api.checked(pane);api.call('pane','run',pane['pane_id'],shlex.join(argv))
        recovery['terminal_repair']='sent';store.save(run)
        return {'role':role,'pane':pane['pane_id'],'resume_session':part['resume_session'],'started':True}
