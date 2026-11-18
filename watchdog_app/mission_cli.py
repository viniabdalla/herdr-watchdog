"""Operator CLI for approved runs; no inferred plans or automatic target merges."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

from .mission import RunStore, finish, FINISHED
from .mission_launch import launch, main_session, open_run, participant, git, owned_worktree, source_current
from . import mission_transport as transport


def template(run):
    return {'transport':run.get('transport',{}).get('kind','native'),'run_id':run['id'],'repo':run['repo'],'base_sha':git(run['repo'],'rev-parse','HEAD'),
        'participants':{role:{'account':run['main']['account'],
            'executable':str(Path.home()/'.local/share/mise/installs/codex/latest/bin/codex'),
            'model':'gpt-6.1-sol','effort':'medium','purpose':'qa' if role=='qa' else 'implementation'} for role in ('worker','qa')},
        'tasks':[{'id':key,'allowed_files':[],'acceptance':[],'tests':[],'dependencies':[]}
                 for key in run['tasks']]}


def accepted(store, identity):
    """Close a run whose selected tasks the user already accepted as Done in TODO."""
    from .mission import accepted_in_todo, close
    from .todo import Snapshot
    run=store.load(identity)
    if run['phase'] in FINISHED:return True
    try:snapshot=Snapshot.read(run['repo'])
    except (OSError,RuntimeError,UnicodeError):return False
    if accepted_in_todo(run,snapshot):
        close(store,identity,'tasks were accepted as Done in TODO');return True
    return False


def watch(store, identity):
    # One monitor per run, independently of the short-lived launcher process.
    import fcntl
    with (store.root/identity/'monitor.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('This run already has a monitor')
        while True:
            try:
                if accepted(store,identity):return
                run=transport.tick(store,identity)
                if run['phase'] in FINISHED:return
                # Only the first independent task is automatic. Main accepts its
                # result and supplies a fresh verified executor for every later task.
                if run['phase']=='active' and not any(t.get('delivery') for t in run['tasks'].values()):
                    if run['participants']['worker'].get('native') and run['participants']['worker'].get('available'):
                        first=next(t['id'] for t in run['brief']['tasks'] if not t['dependencies'])
                        transport.dispatch(store,identity,first)
            except (RuntimeError,OSError,ValueError,KeyError) as error:
                try:
                    with store.lock(identity):
                        run=store.load(identity);run['monitor_problem']=str(error);store.save(run)
                except RuntimeError:pass
                print(str(error),file=sys.stderr,flush=True)
            time.sleep(2)


def main(argv):
    os.umask(0o077)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('list','inspect','template','launch','monitor','watch','poll','open',
                                         'handoff-export','handoff-preview','handoff-adopt','participant','native-host','enroll','receive','recover-unstarted','recover-identity','dispatch','followup','report','accept-result','review','approve'))
    parser.add_argument('--run')
    parser.add_argument('--repo',type=Path,default=Path.cwd())
    parser.add_argument('--state-dir',type=Path,help='Watchdog run ledger directory')
    parser.add_argument('--brief',type=Path)
    parser.add_argument('--transport',choices=('native','gossip'),help='New runs default to native; legacy Gossip is explicit')
    parser.add_argument('--file',type=Path)
    parser.add_argument('--task')
    parser.add_argument('--role',choices=('worker','qa'))
    parser.add_argument('--text')
    parser.add_argument('--candidate')
    parser.add_argument('--after',type=int,default=0)
    parser.add_argument('--binding-file',type=Path)
    parser.add_argument('--context-file',type=Path)
    parser.add_argument('--attachment',type=Path,action='append',default=[])
    parser.add_argument('--offer',help='Exact handoff preview offer UUID')
    parser.add_argument('--confirm',action='store_true')
    parser.add_argument('--resume',action='store_true',help='Reuse verified clean worktrees after a pre-network context rejection')
    args=parser.parse_args(argv);store=RunStore(args.state_dir)
    try:
        if args.action=='list':result=store.list(args.repo)
        else:
            if not args.run:parser.error('--run is required')
            if args.action in ('dispatch','followup','accept-result') and not args.task:parser.error('--task is required')
            if args.action in ('review','approve') and not args.candidate:parser.error('--candidate is required')
            if args.action in ('participant','native-host','enroll','receive','recover-unstarted','recover-identity','report') and not args.role:parser.error('--role is required')
            if args.action=='launch' and not args.brief:parser.error('--brief is required')
            if args.action=='report' and not args.file:parser.error('--file is required')
            if args.action=='followup' and not args.text:parser.error('--text is required')
            if args.action in ('handoff-export','handoff-preview','handoff-adopt'):
                from . import mission_handoff
                if not args.file:parser.error('--file is required for handoff')
                if args.action=='handoff-export':
                    result=mission_handoff.export(store,args.run,args.file,context_file=args.context_file,attachments=args.attachment)
                else:
                    if not args.binding_file:parser.error('--binding-file is required')
                    if args.action=='handoff-preview':result=mission_handoff.preview(store,args.run,args.file,args.binding_file)
                    else:
                        if not args.offer:parser.error('--offer is required for adoption')
                        result=mission_handoff.adopt(store,args.run,args.file,args.binding_file,args.offer,confirmed=args.confirm)
            elif args.action=='inspect':result=store.load(args.run)
            elif args.action=='template':result=template(store.load(args.run))
            elif args.action=='launch':
                brief=json.loads(args.brief.read_text())
                if args.transport:brief['transport']=args.transport
                result=launch(store,args.run,brief,confirmed=args.confirm,resume=args.resume)
            elif args.action=='monitor':
                from .mission_launch import ensure_monitor
                result=ensure_monitor(store,args.run)
            elif args.action=='watch':return watch(store,args.run) or 0
            elif args.action=='poll':result=transport.tick(store,args.run)
            elif args.action=='open':result=open_run(store.load(args.run))
            elif args.action=='participant':return participant(store,args.run,args.role)
            elif args.action=='native-host':
                from .mission_native import serve
                return serve(store,args.run,args.role,confirmed=args.confirm)
            elif args.action=='recover-unstarted':
                from .mission_identity import recover_unstarted
                result=recover_unstarted(store,args.run,args.role,confirmed=args.confirm)
            elif args.action=='recover-identity':
                from .mission_identity import recover_role
                result=recover_role(store,args.run,args.role,confirmed=args.confirm)
            elif args.action=='receive':
                from .mission_broker import request
                result=request(store,args.run,args.role,'poll',after=args.after)
            elif args.action=='enroll':
                from .mission_identity import enroll
                result=enroll(store,args.run,args.role)
            elif args.action=='dispatch':result=transport.dispatch(store,args.run,args.task)
            elif args.action=='followup':result=transport.followup(store,args.run,args.task,args.text)
            elif args.action=='report':result=transport.report(store,args.run,args.role,json.loads(args.file.read_text()))
            elif args.action=='review':result=transport.review(store,args.run,args.candidate,context=args.text)
            elif args.action in ('approve','accept-result'):
                with store.lock(args.run):
                    result=store.load(args.run);main_session(result);source_current(result)
                    if args.action=='approve':finish(result,args.candidate,confirmed=args.confirm)
                    else:
                        task=result['tasks'][args.task]
                        if not args.confirm or not task.get('result') or task['state']!='review':
                            raise RuntimeError('Confirm acceptance of a returned result before dispatching dependent work')
                        path=owned_worktree(result,'worker')
                        head=git(path,'rev-parse','HEAD')
                        if git(path,'status','--porcelain') or head != task['result']['commits'][-1]:
                            raise RuntimeError('Worker result does not match its clean committed head')
                        result['worker_head']=head
                        task['accepted_result']=True
                    store.save(result)
        print(json.dumps(result,indent=2));return 0
    except (RuntimeError,OSError,ValueError,KeyError,TypeError) as error:
        print('Watchdog: '+str(error),file=sys.stderr);return 1
