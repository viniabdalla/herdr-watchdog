"""Confirmed operator transitions; preserve old actors and never retry uncertain starts."""
import copy
import shlex
import sys
import time
import uuid
from pathlib import Path

from .mission import RunStore
from .mission_launch import main_session, source_current, owned_worktree, git, ROOT
from .herdr import Herdr


def prepare_team(store, identity, *, confirmed=False):
    """Seal a pending multi-task team as one bundle at the current clean checkpoint."""
    if not confirmed: raise RuntimeError('Explicit team preparation confirmation is required')
    with store.lock(identity):
        run=store.load(identity); main_session(run); source_current(run)
        if (run.get('execution_mode','team')!='team' or run['phase']!='requested' or
                run.get('operation') or run.get('participants') or run.get('resources') or
                run.get('deliveries') or run.get('request_delivery')!='sent' or
                any(t.get('attempt_id') or t.get('result') for t in run['tasks'].values())):
            raise RuntimeError('Only an undispatched pending team can be prepared')
        if git(run['repo'],'status','--porcelain'):
            raise RuntimeError('Commit the project changes before preparing the team checkpoint')
        head=git(run['repo'],'rev-parse','HEAD')
        previous=copy.deepcopy(run.get('checkpoint'))
        if previous and previous.get('sha') != head:
            run.setdefault('checkpoint_history',[]).append(previous)
        run.update(grouping='together' if len(run['tasks'])>1 else 'single',
                   checkpoint={'sha':head,'created':False,'files':[]},
                   prepared_at=time.time())
        store.save(run)
        return run


def renew_qa(store, identity, candidate, *, confirmed=False, api=None):
    """Provision one NEW QA after a terminal review. Old process and proof are retained."""
    if not confirmed: raise RuntimeError('Explicit new QA confirmation is required')
    from .mission_transport import verify_result_commits
    api=api or Herdr()
    with store.lock(identity):
        run=store.load(identity);main_session(run);source_current(run)
        if (run.get('transport',{}).get('kind')!='native' or
                run.get('execution_mode','team')!='team' or run['phase']!='active' or run.get('operation')):
            raise RuntimeError('New QA requires a settled active native team')
        refresh=run.get('qa_refresh',{})
        if refresh.get('state') in ('creating','starting','uncertain'):
            raise RuntimeError('QA startup already attempted; inspect its retained proof, do not retry')
        old=run['participants']['qa']; pane=run['resources']['qa']
        record=run.get('deliveries',{}).get(run.get('qa_task'),{})
        if (not run.get('qa_finished') or record.get('state')!='sent' or
                record.get('recipient')!=old.get('native')):
            raise RuntimeError('Current QA must have a finished, confirmed review before replacement')
        if any(not t.get('result') or t['state'] not in ('review','blocked') for t in run['tasks'].values()):
            raise RuntimeError('Every selected task needs a committed result before new QA')
        if git(run['repo'],'rev-parse',candidate+'^{commit}')!=candidate:
            raise RuntimeError('New QA requires the full exact candidate SHA')
        verify_result_commits(run,candidate)
        old_path=owned_worktree(run,'qa')
        if git(old_path,'status','--porcelain'):raise RuntimeError('Old QA worktree is dirty; preserve and inspect it')
        live=api.checked(pane)
        if live['tab_id']!=run['tab']:raise RuntimeError('Old QA pane moved; inspect it before provisioning')
        incarnation=str(uuid.uuid4())
        folder=store.root/identity/('qa-'+incarnation)
        run['qa_refresh']={'id':incarnation,'state':'creating','candidate':candidate,'worktree':str(folder),'at':time.time()}
        run['operation']='provision new QA';store.save(run)
        try:
            git(run['repo'],'worktree','add','--detach',str(folder),candidate)
            new=api.call('pane','split',pane['pane_id'],'--direction','down','--cwd',str(folder),'--no-focus')['pane']
            run['qa_refresh']['resource']=new;store.save(run)
            if new['pane_id']==pane['pane_id'] or new['terminal_id']==pane['terminal_id']:
                raise RuntimeError('New QA requires a distinct terminal')
            if new['tab_id']!=run['tab'] or new['workspace_id']!=run['main']['workspace']:
                raise RuntimeError('New QA was created outside the approved execution tab')
            report=run.get('qa') or next((e['report'] for e in reversed(list(run.get('events',{}).values()))
                if e.get('role')=='qa' and e.get('report',{}).get('attempt_id')==run.get('qa_task')
                and e['report'].get('status')=='qa'),None)
            run.setdefault('qa_history',[]).append({'participant':copy.deepcopy(old),'resource':copy.deepcopy(pane),
                'review_contract':copy.deepcopy(run.get('review_contract')),'report':copy.deepcopy(report),
                'review_task':run.get('qa_task'),'at':time.time()})
            part=copy.deepcopy(run['brief']['participants']['qa'])
            part.update(worktree=str(folder),branch=None,base_sha=candidate,incarnation=incarnation,
                        role_context=old.get('role_context','You are the assigned QA. No source edits or extra agents.'))
            run['participants']['qa']=part;run['resources']['qa']=new
            run['qa_refresh']['state']='starting';store.save(run)
            api.call('pane','rename',new['pane_id'],'Watchdog QA '+incarnation[:8])
            argv=[sys.executable,str(ROOT/'watchdog'),'mission','participant','--run',identity,
                  '--role','qa','--state-dir',str(store.root),'--incarnation',incarnation]
            api.call('pane','run',new['pane_id'],shlex.join(argv))
            run['qa_refresh']['state']='started';run['operation']=None;store.save(run)
            return run
        except Exception as error:
            run['qa_refresh'].update(state='uncertain',problem=str(error))
            store.save(run)
            raise RuntimeError('New QA start is uncertain; inspect retained resources without retry: '+str(error)) from error
