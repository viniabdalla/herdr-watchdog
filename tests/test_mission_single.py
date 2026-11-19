"""Single execution uses real temporary Git and substitutes native host boundaries."""
import copy
from contextlib import redirect_stdout, redirect_stderr
import io
from dataclasses import asdict, replace
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import patch

import test_mission_launch
from test_actions import FakeBinding
from watchdog_app import mission, mission_launch, mission_cli, mission_native
from watchdog_app import mission_single as single


class SingleTests(unittest.TestCase):
    def setUp(self):
        fixture = test_mission_launch.LaunchTests()
        fixture.setUp(); self.addCleanup(fixture.doCleanups)
        self.f = fixture
        self.repo, self.store, self.run = fixture.repo, fixture.store, fixture.run
        self.base = fixture.base
        self.worktree = fixture.root / 'existing-worker'
        test_mission_launch.git(self.repo, 'worktree', 'add', '-b', 'existing-worker', str(self.worktree), self.base)
        self.worker = replace(FakeBinding(), session=str(uuid.uuid4()), account=str(fixture.root),
                              pane='wd-test:existing', terminal='existing-terminal', pid=456)
        self.executor = {'binding':asdict(self.worker), 'worktree':str(self.worktree), 'branch':'existing-worker'}
        self.run['execution_mode'] = 'single'; self.run['executor'] = self.executor
        key = next(iter(self.run['tasks'])); self.run['tasks'] = {key:self.run['tasks'][key]}; self.key = key
        self.brief = copy.deepcopy(fixture.brief)
        self.brief.update(execution_mode='single', transport='native', participants={'worker':{
            'account':self.worker.account, 'native':asdict(self.worker), 'worktree':str(self.worktree),
            'branch':'existing-worker', 'purpose':'implementation'}})
        self.brief['tasks'] = self.brief['tasks'][:1]
        self.store.save(self.run)
        self.messages = []
        self.live = {'agent_status':'idle', 'cwd':str(self.worktree)}
        self.engine = SimpleNamespace(Binding=FakeBinding, verify=lambda b, **kw:self.live,
            candidates=lambda:([self.worker], []), queue=self.queue)
        self.f.session.runtime = self.engine
        for p in (patch('watchdog_app.bindings.engine',return_value=self.engine),
                  patch('watchdog_app.bindings.project_for',return_value=self.worktree)):
            p.start(); self.addCleanup(p.stop)

    def queue(self, binding, message):
        self.messages.append((asdict(binding), message)); return str(uuid.uuid4())

    def active_result(self):
        (self.worktree/'a.py').write_text('print(2)\n')
        test_mission_launch.git(self.worktree, 'add', 'a.py')
        test_mission_launch.git(self.worktree, 'commit', '-qm', 'implementation')
        self.candidate = test_mission_launch.git(self.worktree,'rev-parse','HEAD')
        self.run.update(phase='active', brief=self.brief, result_version=1, transport={'kind':'native'},
            participants={'worker':dict(self.brief['participants']['worker'],base_sha=self.base)},
            resources={'worker':{'pane_id':self.worker.pane,'terminal_id':self.worker.terminal,
                'tab_id':'existing-tab','workspace_id':self.worker.workspace}})
        self.run['tasks'][self.key].update(state='review', result={'commits':[self.candidate], 'tests':['python a.py: 2']})
        self.store.save(self.run)
        self.evidence = {'run_id':self.run['id'], 'candidate':self.candidate,'result_version':1,
                         'verdict':'pass','summary':'Reviewed complete diff and ran python a.py', 'tests':['python a.py: 2']}

    def review(self, **kwargs):
        with patch.object(mission_native,'verify_participant',return_value=self.worker):
            return single.review(self.store,self.run['id'],self.candidate,self.evidence,confirmed=True,**kwargs)

    def test_brief_requires_explicit_mode_and_exact_selected_worker(self):
        mission_launch.validate_brief(self.run,self.brief)
        wrong=copy.deepcopy(self.brief); wrong['participants']['qa']={}
        with self.assertRaises(RuntimeError):mission_launch.validate_brief(self.run,wrong)
        wrong=copy.deepcopy(self.brief); wrong['participants']['worker']['native']['session']=str(uuid.uuid4())
        with self.assertRaisesRegex(RuntimeError,'executor|recipient'):mission_launch.validate_brief(self.run,wrong)
        wrong=copy.deepcopy(self.brief); wrong['execution_mode']='team'
        with self.assertRaises(RuntimeError):mission_launch.validate_brief(self.run,wrong)

    def test_launch_attaches_existing_actor_without_new_worktree_pane_or_qa(self):
        with patch.object(single,'start_bridge',return_value=1234):
            run=mission_launch.launch(self.store,self.run['id'],self.brief,confirmed=True,api=self.f.api)
        self.assertEqual(set(run['participants']),{'worker'})
        self.assertEqual(run['participants']['worker']['native'],asdict(self.worker))
        self.assertEqual(run['participants']['worker']['worktree'],str(self.worktree))
        self.assertFalse(self.f.api.calls)
        self.assertEqual(len(self.messages),1)
        self.assertIn('enroll',self.messages[0][1])
        self.assertNotIn('NEW QA conversation',self.messages[0][1])
        self.assertEqual(self.messages[0][0],asdict(self.worker))
        with self.assertRaises(RuntimeError):mission_launch.launch(self.store,self.run['id'],self.brief,confirmed=True)

    def test_uncertain_enrollment_notification_is_retained_not_resent(self):
        self.engine.queue=lambda *args:(_ for _ in ()).throw(RuntimeError('receipt lost'))
        with patch.object(single,'start_bridge',return_value=1234) as start:
            with self.assertRaisesRegex(RuntimeError,'uncertain'):
                mission_launch.launch(self.store,self.run['id'],self.brief,confirmed=True,api=self.f.api)
            run=self.store.load(self.run['id'])
            self.assertEqual(run['enrollment_delivery'],'uncertain')
            self.assertEqual(run['phase'],'blocked')
            with self.assertRaises(RuntimeError):mission_launch.launch(self.store,self.run['id'],self.brief,confirmed=True)
            self.assertEqual(start.call_count,1)

    def test_executor_requires_idle_distinct_session_and_clean_isolated_matching_base(self):
        single.validate_executor(self.repo,self.run['main'],self.executor,base=self.base)
        for field,value in [('session',self.run['main']['session']),('pane',self.run['main']['pane']),('pid',self.run['main']['pid'])]:
            wrong=copy.deepcopy(self.executor); wrong['binding'][field]=value
            with self.assertRaises(RuntimeError):single.validate_executor(self.repo,self.run['main'],wrong)
        self.live['agent_status']='working'
        with self.assertRaisesRegex(RuntimeError,'idle|ocioso'):single.validate_executor(self.repo,self.run['main'],self.executor)
        self.live['agent_status']='idle'
        (self.worktree/'dirty').write_text('preserve')
        with self.assertRaisesRegex(RuntimeError,'clean|limpa'):single.validate_executor(self.repo,self.run['main'],self.executor)
        (self.worktree/'dirty').unlink()
        with self.assertRaisesRegex(RuntimeError,'base'):single.validate_executor(self.repo,self.run['main'],self.executor,base='a'*40)
        self.live['cwd']=str(self.repo)
        with self.assertRaises(RuntimeError):single.validate_executor(self.repo,self.run['main'],self.executor)

    def test_template_preserves_recipient_and_team_default_still_requires_qa(self):
        template=mission_cli.template(self.run)
        self.assertEqual(set(template['participants']),{'worker'})
        self.assertEqual(template['participants']['worker']['native'],asdict(self.worker))
        team=copy.deepcopy(self.run); team.pop('execution_mode'); team.pop('executor')
        self.assertEqual(set(mission_cli.template(team)['participants']),{'worker','qa'})
        with self.assertRaises(RuntimeError):mission_launch.validate_brief(team,self.brief)

    def test_review_requires_evidence_for_full_exact_candidate_and_explicit_confirmation(self):
        self.active_result()
        with self.assertRaisesRegex(RuntimeError,'confirm'):single.review(self.store,self.run['id'],self.candidate,self.evidence)
        for field,value in [('candidate',self.base),('result_version',0),('tests',[]),('tests',['']),('summary',''),('verdict','unknown')]:
            old=copy.deepcopy(self.evidence); old[field]=value
            with patch.object(mission_native,'verify_participant',return_value=self.worker):
                with self.assertRaises(RuntimeError):single.review(self.store,self.run['id'],self.candidate,old,confirmed=True)
        reviewed=self.review()
        self.assertEqual(reviewed['leader_review']['reviewer'],self.run['main'])
        self.assertEqual(reviewed['leader_review']['candidate'],self.candidate)
        self.assertTrue(single.review_valid(reviewed,self.candidate))
        self.assertIn('líder',mission.run_status(reviewed)['detail'])
        mission.finish(reviewed,self.candidate,confirmed=True)
        self.assertEqual(reviewed['phase'],'done')
        self.assertEqual((self.repo/'TODO.md').read_text(),'## Next\n- [ ] First\n- [ ] Second\n')

    def test_new_evidence_or_leader_identity_invalidates_review_and_qa_cannot_replace_it(self):
        self.active_result(); reviewed=self.review()
        for field,value in [('result_version',2),('main',dict(self.run['main'],session='successor'))]:
            stale=copy.deepcopy(reviewed); stale[field]=value
            with self.assertRaises(RuntimeError):mission.finish(stale,self.candidate,confirmed=True)
        stale=copy.deepcopy(reviewed); stale['leader_review']=None; stale['qa']={'verdict':'pass'}
        with self.assertRaises(RuntimeError):mission.finish(stale,self.candidate,confirmed=True)
        with self.assertRaises(RuntimeError):mission.finish(reviewed,self.base,confirmed=True)

    def test_review_rejects_dirty_or_different_worker_head_and_unreported_candidate(self):
        self.active_result()
        (self.worktree/'dirty').write_text('preserve')
        with self.assertRaisesRegex(RuntimeError,'clean'):self.review()
        (self.worktree/'dirty').unlink()
        test_mission_launch.git(self.worktree,'commit','--allow-empty','-qm','new work')
        with self.assertRaisesRegex(RuntimeError,'head|candidate'):self.review()

    def test_native_result_leader_review_and_cli_approval_integrate_only_exact_candidate(self):
        from watchdog_app import mission_transport as transport
        from watchdog_app.mission_native import boot_id, owner
        run = copy.deepcopy(self.run)
        run.update(phase='active', brief=self.brief, transport={'kind':'native','boot_id':boot_id()},
            participants={'worker':dict(self.brief['participants']['worker'],base_sha=self.base,
                generation=str(uuid.uuid4()),boot_id=boot_id(),bridge_owner=owner(),enrolled=True,available=True)},
            resources={'worker':{'pane_id':self.worker.pane,'terminal_id':self.worker.terminal}})
        self.store.save(run)
        dispatched=transport.dispatch(self.store,run['id'],self.key)
        self.assertEqual(set(dispatched['participants']),{'worker'})
        (self.worktree/'a.py').write_text('print(2)\n')
        import subprocess
        observed=subprocess.run(['python3','a.py'],cwd=self.worktree,capture_output=True,text=True,check=True)
        self.assertEqual(observed.stdout,'2\n')
        test_mission_launch.git(self.worktree,'add','a.py');test_mission_launch.git(self.worktree,'commit','-qm','result')
        candidate=test_mission_launch.git(self.worktree,'rev-parse','HEAD')
        part=dispatched['participants']['worker']
        proof={k:part[k] for k in ('native','generation','boot_id','bridge_owner')}
        proof.update(transport='native',run_id=run['id'],role='worker')
        report={'run_id':run['id'],'task_id':self.key,'event_id':str(uuid.uuid4()),
            'attempt_id':dispatched['tasks'][self.key]['attempt_id'],'status':'result',
            'summary':'Implemented and checked output','commits':[candidate],'tests':['python3 a.py: output 2, exit 0'],
            'verdict':'pass', 'candidate':candidate}
        mission_native.handle(self.store,run['id'],'worker',proof,'report',{'report':report})
        self.assertIn('leader-review',self.messages[-1][1])
        self.assertNotIn('QA passed',self.messages[-1][1])
        returned=self.store.load(run['id'])
        self.assertEqual(returned['tasks'][self.key]['state'],'review')
        self.assertNotIn('leader_review',returned)
        argv=['approve','--run',run['id'],'--candidate',candidate,'--confirm','--state-dir',str(self.store.root)]
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(mission_cli.main(argv),1)
        self.assertEqual(test_mission_launch.git(self.repo,'rev-parse','HEAD'),self.base)
        evidence={'run_id':run['id'],'candidate':candidate,'result_version':returned['result_version'],
            'verdict':'pass','summary':'Leader reviewed diff and observed output', 'tests':['python3 a.py: 2, exit 0']}
        single.review(self.store,run['id'],candidate,evidence,confirmed=True)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(mission_cli.main(argv),0)
        self.assertEqual(test_mission_launch.git(self.repo,'rev-parse','HEAD'),candidate)
        self.assertEqual(self.store.load(run['id'])['phase'],'done')
        self.assertFalse(self.store.load(run['id'])['integration']['pushed'])
        self.assertEqual((self.repo/'TODO.md').read_text(),'## Next\n- [ ] First\n- [ ] Second\n')

    def test_known_actor_is_not_reserved_by_two_runs(self):
        single.available(self.store,self.repo,self.executor,excluding=self.run['id'])
        with self.assertRaisesRegex(RuntimeError,'reserved'):single.available(self.store,self.repo,self.executor)

    def test_open_single_run_focuses_only_verified_existing_pane(self):
        self.active_result()
        with patch.object(mission_native,'verify_participant',return_value=self.worker):
            with patch.object(self.f.api,'call',return_value={}) as call:
                mission_launch.open_run(self.run,self.f.api)
                call.assert_called_once_with('agent','focus',self.worker.pane)

    def test_single_host_exits_when_run_finishes_without_stopping_existing_actor(self):
        self.run.update(phase='active', participants={'worker':{'generation':'host-generation'}})
        self.store.save(self.run)
        closed=[]; sleeps=[]
        bridge=SimpleNamespace(child=SimpleNamespace(poll=lambda:None), proof={'generation':'host-generation'},close=lambda:closed.append(True))
        def pause(seconds):
            sleeps.append(seconds)
            if len(sleeps)>1:raise RuntimeError('Host kept running after completed run')
            run=self.store.load(self.run['id']);run['phase']='done';self.store.save(run)
        with patch.object(mission_native,'host_bridge',return_value=bridge), patch.object(mission_native.time,'sleep',side_effect=pause):
            mission_native.serve(self.store,self.run['id'],'worker',confirmed=True)
        self.assertEqual(closed,[True])
        self.assertEqual(len(sleeps),1)

    def test_actor_with_previous_task_purpose_is_rejected_before_host_attachment(self):
        with patch.object(single,'start_bridge',return_value=1234):
            mission_launch.launch(self.store,self.run['id'],self.brief,confirmed=True,api=self.f.api)
        prior=self.store.load(self.run['id']);prior['phase']='done';self.store.save(prior)
        self.run['id']=str(uuid.uuid4()); self.brief['run_id']=self.run['id'];self.store.save(self.run)
        with patch.object(single,'start_bridge',return_value=1234) as host:
            with self.assertRaisesRegex(RuntimeError,'reserved|fresh|another task'):
                mission_launch.launch(self.store,self.run['id'],self.brief,confirmed=True,api=self.f.api)
            host.assert_not_called()

    def test_failed_review_never_allows_approval(self):
        self.active_result(); self.evidence['verdict']='fail'; self.evidence['summary']='Found missing validation'
        reviewed=self.review()
        self.assertEqual(reviewed['tasks'][self.key]['state'],'blocked')
        with self.assertRaises(RuntimeError):mission.finish(reviewed,self.candidate,confirmed=True)

if __name__=='__main__':unittest.main()
