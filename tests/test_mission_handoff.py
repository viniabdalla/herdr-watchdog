"""Handoff public APIs on real Git/RunStore; native identity is the external stub.

No model sessions, production leadership transfer or Gossip operations.
"""
import copy
from dataclasses import asdict
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import unittest
import uuid
from unittest.mock import patch

from test_actions import FakeBinding
import test_mission_native_transport as native_tests
from test_mission_launch import git
from watchdog_app import bindings, mission_cli, mission_launch, mission_handoff as handoff
from watchdog_app import mission_transport as transport
from watchdog_app.actions import Session


class HandoffTests(unittest.TestCase):
    def setUp(self):
        fixture=native_tests.NativeTransportTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        self.fixture=fixture;self.store=fixture.store;self.repo=fixture.repo;self.identity=fixture.identity
        self.folder=self.repo.parent
        self.old=FakeBinding(session=str(uuid.uuid4()),account=fixture.bindings['worker'].account,
            pane='main-old',terminal='main-old-terminal',pid=1001,started='111')
        self.new=FakeBinding(session=str(uuid.uuid4()),account=self.old.account,
            pane='main-new',terminal='main-new-terminal',pid=1002,started='222')
        self.old_file=self.folder/'old-binding.json';self.target=self.folder/'new-binding.json'
        self.write_binding(self.old_file,self.old);self.write_binding(self.target,self.new)
        run=self.store.load(self.identity);run.update(main=asdict(self.old),binding_file=str(self.old_file))
        self.store.save(run)
        self.registry={b.session:asdict(b) for b in [self.old,self.new,*fixture.bindings.values()]}
        self.status={};self.projects={}
        def verify(binding):
            if asdict(binding)!=self.registry.get(binding.session):raise RuntimeError('Native identity changed')
            return {'agent_status':self.status.get(binding.session,'idle')}
        fixture.runtime.verify=verify
        fixture.runtime.queue=lambda b,text:self.record_queue(b,text)
        self.queues=[]
        for p in (patch.object(bindings,'project_for',side_effect=lambda b:self.projects.get(b.session,self.repo)),
                  patch.object(mission_launch,'Session',Session),
                  patch.object(transport,'main_session',side_effect=mission_launch.main_session)):
            p.start();self.addCleanup(p.stop)
        self.capsule_file=self.folder/'capsule.json'
        self.original_todo=(self.repo/'TODO.md').read_bytes()

    def write_binding(self,path,binding):
        path.write_text(json.dumps({'repo':str(self.repo),'binding':asdict(binding)}))

    def record_queue(self,binding,text):
        self.fixture.runtime.verify(binding)
        self.queues.append((binding.session,json.loads(text.split('\n',1)[1])))
        return str(uuid.uuid4())

    def export(self,**kwargs):
        return handoff.export(self.store,self.identity,self.capsule_file,**kwargs)

    def preview(self):
        return handoff.preview(self.store,self.identity,self.capsule_file,self.target)

    def adopt(self,offer,**kwargs):
        return handoff.adopt(self.store,self.identity,self.capsule_file,self.target,offer['offer_id'],**kwargs)

    def test_bounded_export_is_read_only_and_excludes_raw_history_credentials_and_attachment_content(self):
        run=self.store.load(self.identity)
        for n in range(200):
            run['tasks']['extra-'+str(n)]={'title':'Task '+str(n),'state':'ready','summary':'x'*9000,'agent':'main'}
        run['unrelated_secret']='NEVER_EXPORT_THIS_SECRET'
        run['participants']['worker']['role_context']='RAW_TRANSCRIPT_DO_NOT_EXPORT'*9000
        self.store.save(run)
        sidecar=self.folder/'sidecar.json';sidecar.write_text('{"secret":"SIDE_SECRET"}')
        before=self.store.path(self.identity).read_bytes()
        capsule=self.export(attachments=[sidecar])
        raw=self.capsule_file.read_bytes()
        self.assertLessEqual(len(raw),65536)
        self.assertGreater(capsule['tasks_omitted'],0)
        self.assertEqual(capsule['task_count'],202)
        self.assertIn('sha256',capsule['attachments'][0])
        for secret in (b'NEVER_EXPORT_THIS_SECRET',b'RAW_TRANSCRIPT_DO_NOT_EXPORT',b'SIDE_SECRET'):
            self.assertNotIn(secret,raw)
        self.assertEqual(self.store.path(self.identity).read_bytes(),before)
        self.assertEqual((self.repo/'TODO.md').read_bytes(),self.original_todo)
        self.assertIn('Do not redo implementation',capsule['continuation_prompt'])

    def test_explicit_preview_and_adoption_consume_once_without_changing_work_or_binding_files(self):
        transport.dispatch(self.store,self.identity,self.fixture.task)
        before=self.store.load(self.identity)
        self.export();offer=self.preview()
        self.assertEqual(self.store.load(self.identity),before,'Preview must not change run ownership')
        with self.assertRaisesRegex(RuntimeError,'confirm'):self.adopt(offer)
        old_bytes=self.old_file.read_bytes();new_bytes=self.target.read_bytes()
        result=self.adopt(offer,confirmed=True)
        run=self.store.load(self.identity)
        self.assertEqual(result['main'],asdict(self.new))
        self.assertEqual(run['main'],asdict(self.new));self.assertEqual(run['binding_file'],str(self.target))
        for field in ('tasks','participants','resources','tab','candidate','qa','source_digest'):
            self.assertEqual(run.get(field),before.get(field))
        self.assertEqual(run['leader_generation'],1)
        self.assertEqual(self.old_file.read_bytes(),old_bytes);self.assertEqual(self.target.read_bytes(),new_bytes)
        with self.assertRaisesRegex(RuntimeError,'consumed|stale'):self.adopt(offer,confirmed=True)
        self.assertEqual(len(run['leader_handoffs']),1)

    def test_modified_capsule_or_expired_offer_cannot_be_adopted(self):
        self.export();offer=self.preview()
        capsule=json.loads(self.capsule_file.read_text());capsule['continuation_prompt']='Redo everything'
        self.capsule_file.write_text(json.dumps(capsule))
        with self.assertRaisesRegex(RuntimeError,'modified|digest'):self.adopt(offer,confirmed=True)
        self.export();offer=self.preview()
        with patch.object(handoff.time,'time',return_value=offer['expires']+1):
            with self.assertRaisesRegex(RuntimeError,'expired'):self.adopt(offer,confirmed=True)
        self.assertEqual(self.store.load(self.identity)['main'],asdict(self.old))

    def test_wrong_project_account_thread_terminal_or_shared_role_is_rejected(self):
        self.export()
        for field,value in [('session',str(uuid.uuid4())),('account','/other-account'),('terminal','moved')]:
            with self.subTest(field=field):
                changed=copy.deepcopy(self.new);setattr(changed,field,value);self.write_binding(self.target,changed)
                with self.assertRaises(RuntimeError):self.preview()
        self.write_binding(self.target,self.new);self.projects[self.new.session]=self.folder/'foreign'
        with self.assertRaisesRegex(RuntimeError,'project'):self.preview()
        self.projects.clear()
        changed=copy.deepcopy(self.new);changed.account='/other-approved-account'
        self.registry[changed.session]=asdict(changed);self.write_binding(self.target,changed)
        with self.assertRaisesRegex(RuntimeError,'account'):self.preview()
        self.registry[self.new.session]=asdict(self.new)
        for binding in [self.old,*self.fixture.bindings.values()]:
            self.write_binding(self.target,binding)
            with self.assertRaisesRegex(RuntimeError,'role|frontend|distinct|leader'):self.preview()

    def test_changed_binding_source_after_preview_is_rejected_even_if_new_identity_is_valid(self):
        self.export();offer=self.preview()
        replacement=copy.deepcopy(self.new);replacement.session=str(uuid.uuid4())
        self.registry[replacement.session]=asdict(replacement);self.write_binding(self.target,replacement)
        with self.assertRaisesRegex(RuntimeError,'changed|source'):self.adopt(offer,confirmed=True)

    def test_dirty_project_or_owned_worktree_and_changed_head_block_adoption(self):
        self.export()
        (self.repo/'a.py').write_text('uncommitted\n')
        with self.assertRaisesRegex(RuntimeError,'dirty|clean'):self.preview()
        git(self.repo,'restore','a.py')
        worker=Path(self.store.load(self.identity)['participants']['worker']['worktree'])
        (worker/'owned-change.py').write_text('in progress\n')
        with self.assertRaisesRegex(RuntimeError,'dirty|clean'):self.preview()
        (worker/'owned-change.py').unlink()
        git(self.repo,'commit','--allow-empty','-qm','newer head')
        with self.assertRaisesRegex(RuntimeError,'Git|head|changed'):self.preview()

    def test_active_or_uncertain_delivery_intents_and_pending_notifications_block_adoption(self):
        original=self.store.load(self.identity)
        for state in ('sending','uncertain'):
            for field in ('task','qa','delivery','notification'):
                with self.subTest(state=state,field=field):
                    run=copy.deepcopy(original)
                    if field=='task':run['tasks'][self.fixture.task].update(delivery=state,attempt_id=str(uuid.uuid4()))
                    elif field=='qa':run.update(qa_delivery=state,qa_task=str(uuid.uuid4()))
                    elif field=='delivery':run['deliveries']={'attempt':{'state':state}}
                    else:run['events']={'event':{'delivery':state,'report':{'summary':'Pending evidence'}}}
                    self.store.save(run);self.export()
                    with self.assertRaisesRegex(RuntimeError,'delivery|notification|intent'):self.preview()
        run=copy.deepcopy(original);run['events']={'event':{'delivery':'pending','report':{'summary':'Not yet forwarded'}}}
        self.store.save(run);self.export()
        with self.assertRaisesRegex(RuntimeError,'notification'):self.preview()

    def test_new_report_stales_export_and_reports_after_adoption_route_to_new_main(self):
        transport.dispatch(self.store,self.identity,self.fixture.task)
        self.export();stale_offer=self.preview()
        report=self.fixture.report();self.fixture.record(report)
        self.assertEqual(self.queues[-1][0],self.old.session)
        with self.assertRaisesRegex(RuntimeError,'stale|snapshot|evidence'):self.adopt(stale_offer,confirmed=True)
        self.export();offer=self.preview();self.adopt(offer,confirmed=True)
        self.fixture.record(self.fixture.report('blocked',summary='A concrete blocker'))
        self.assertEqual(self.queues[-1][0],self.new.session)
        run=self.store.load(self.identity)
        self.assertEqual(run['events'][report['event_id']]['recipient'],asdict(self.old))
        self.assertEqual(len(run['events']),2)
        self.assertEqual((self.repo/'TODO.md').read_bytes(),self.original_todo)

    def test_qa_candidate_verdict_and_other_selected_work_survive_transfer(self):
        run=self.fixture._single_task_review()
        self.fixture.record(self.fixture._qa_report(run),'qa')
        before=self.store.load(self.identity)
        self.export();self.adopt(self.preview(),confirmed=True)
        after=self.store.load(self.identity)
        for field in ('qa','qa_finished','qa_task','review_contract','candidate','tasks','brief'):
            self.assertEqual(after[field],before[field])
        self.assertEqual(after['phase'],'active')

    def test_attachment_changes_and_legacy_adoption_are_rejected(self):
        sidecar=self.folder/'sidecar.json';sidecar.write_text('{"status":"result"}')
        self.export(attachments=[sidecar]);offer=self.preview()
        sidecar.write_text('{"status":"blocked"}')
        with self.assertRaisesRegex(RuntimeError,'attachment|changed'):self.adopt(offer,confirmed=True)
        run=self.store.load(self.identity);run['transport']={'gossip':'legacy-room'};self.store.save(run)
        before=self.store.path(self.identity).read_bytes();capsule=self.export()
        self.assertFalse(capsule['adoptable'])
        with self.assertRaisesRegex(RuntimeError,'legacy|native'):self.preview()
        self.assertEqual(self.store.path(self.identity).read_bytes(),before)

    def test_crash_after_atomic_ownership_commit_cannot_replay_the_offer(self):
        self.export();offer=self.preview();save=self.store.save
        def interrupted(run):save(run);raise SystemExit('Lost reply after durable ownership update')
        with patch.object(self.store,'save',side_effect=interrupted):
            with self.assertRaises(SystemExit):self.adopt(offer,confirmed=True)
        run=self.store.load(self.identity)
        self.assertEqual(run['main'],asdict(self.new));self.assertEqual(len(run['leader_handoffs']),1)
        with self.assertRaisesRegex(RuntimeError,'consumed|stale'):self.adopt(offer,confirmed=True)

    def test_cli_exports_previews_and_confirms_only_the_isolated_fixture(self):
        common=['--run',self.identity,'--state-dir',str(self.store.root),'--file',str(self.capsule_file)]
        with redirect_stdout(io.StringIO()):
            self.assertEqual(mission_cli.main(['handoff-export',*common]),0)
        output=io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(mission_cli.main(['handoff-preview',*common,'--binding-file',str(self.target)]),0)
        offer=json.loads(output.getvalue())
        with redirect_stdout(io.StringIO()):
            self.assertEqual(mission_cli.main(['handoff-adopt',*common,'--binding-file',str(self.target),
                '--offer',offer['offer_id'],'--confirm']),0)
        self.assertEqual(self.store.load(self.identity)['main'],asdict(self.new))

    def test_review_and_resource_export_are_allowlisted_instead_of_dumping_context(self):
        run=self.store.load(self.identity)
        run['review_contract']={'id':'review','candidate':self.fixture.base,'context':'PRIVATE_REVIEW_TRANSCRIPT'*5000,'version':1}
        run['resources']['worker']['launch_command']='PRIVATE_COMMAND_CREDENTIAL'
        self.store.save(run)
        self.export();raw=self.capsule_file.read_bytes()
        self.assertNotIn(b'PRIVATE_REVIEW_TRANSCRIPT',raw)
        self.assertNotIn(b'PRIVATE_COMMAND_CREDENTIAL',raw)

    def test_export_cannot_overwrite_the_run_ledger_binding_or_owned_worktree(self):
        before=self.store.path(self.identity).read_bytes()
        for path in (self.store.path(self.identity),self.old_file,
                     Path(self.store.load(self.identity)['participants']['worker']['worktree'])/'capsule.json'):
            with self.subTest(path=path):
                with self.assertRaisesRegex(RuntimeError,'output|Output|outside|source'):
                    handoff.export(self.store,self.identity,path)
        self.assertEqual(self.store.path(self.identity).read_bytes(),before)

    def test_adoption_rechecks_idle_native_status_at_the_commit_boundary(self):
        self.export();offer=self.preview();verify=Session.verify;calls=[0]
        def changing(session):
            live=verify(session)
            if session.binding.session==self.new.session:
                calls[0]+=1
                if calls[0]>=3:return {'agent_status':'working'}
            return live
        with patch.object(Session,'verify',changing):
            with self.assertRaisesRegex(RuntimeError,'idle|busy|changed'):
                self.adopt(offer,confirmed=True)
        self.assertEqual(self.store.load(self.identity)['main'],asdict(self.old))

    def test_other_workspace_or_same_frontend_thread_cannot_displace_existing_team_navigation(self):
        self.export()
        for field,value in [('workspace','another-workspace'),('pid',self.old.pid)]:
            with self.subTest(field=field):
                changed=copy.deepcopy(self.new);setattr(changed,field,value)
                self.registry[changed.session]=asdict(changed);self.write_binding(self.target,changed)
                with self.assertRaisesRegex(RuntimeError,'workspace|frontend|leader'):self.preview()

    def test_expiry_is_checked_again_after_slow_native_verification(self):
        self.export();offer=self.preview();verify=Session.verify;calls=[0];clock=[handoff.time.time()]
        def slow(session):
            live=verify(session)
            if session.binding.session==self.new.session:
                calls[0]+=1
                if calls[0]>=3:clock[0]=offer['expires']+1
            return live
        with patch.object(Session,'verify',slow),patch.object(handoff.time,'time',side_effect=lambda:clock[0]):
            with self.assertRaisesRegex(RuntimeError,'expired'):self.adopt(offer,confirmed=True)
        self.assertEqual(self.store.load(self.identity)['main'],asdict(self.old))

    def test_report_during_commit_gets_explicit_busy_then_retries_once_to_new_owner(self):
        transport.dispatch(self.store,self.identity,self.fixture.task)
        self.export();offer=self.preview();report=self.fixture.report();save=self.store.save
        def during_commit(run):
            with self.assertRaisesRegex(RuntimeError,'busy'):
                self.fixture.record(report)
            save(run)
        with patch.object(self.store,'save',side_effect=during_commit):self.adopt(offer,confirmed=True)
        self.assertFalse(self.store.load(self.identity)['events'])
        result=self.fixture.record(report);self.assertTrue(result['persisted'])
        self.assertEqual(self.queues[-1][0],self.new.session)
        self.assertEqual(len(self.store.load(self.identity)['events']),1)

    def fresh_actor(self,role,run,*,purpose=None):
        binding=copy.deepcopy(self.fixture.bindings[role])
        binding.session=str(uuid.uuid4());binding.pid+=2000
        self.registry[binding.session]=asdict(binding)
        run['participants'][role].update(native=asdict(binding),generation=str(uuid.uuid4()))
        if purpose:run['participants'][role]['purpose']=purpose
        return binding

    def test_each_later_task_requires_new_executor_at_preceding_accepted_commit(self):
        first=self.fixture.task;second=next(k for k in self.store.load(self.identity)['tasks'] if k!=first)
        transport.dispatch(self.store,self.identity,first)
        worker=Path(self.store.load(self.identity)['participants']['worker']['worktree'])
        (worker/'a.py').write_text('print(2)\n');git(worker,'add','a.py');git(worker,'commit','-qm','accepted predecessor')
        accepted=git(worker,'rev-parse','HEAD')
        self.fixture.record(self.fixture.report('result',commits=[accepted],tests=['Observed fixture check']))
        with redirect_stdout(io.StringIO()):
            self.assertEqual(mission_cli.main(['accept-result','--run',self.identity,'--state-dir',str(self.store.root),
                                              '--task',first,'--confirm']),0)
        count=len(self.queues)
        with self.assertRaisesRegex(RuntimeError,'fresh|conversation|session'):
            transport.dispatch(self.store,self.identity,second)
        self.assertEqual(len(self.queues),count)
        run=self.store.load(self.identity);fresh=self.fresh_actor('worker',run);self.store.save(run)
        transport.dispatch(self.store,self.identity,second)
        self.assertEqual(self.queues[-1][0],fresh.session)
        self.assertEqual(self.queues[-1][1]['base_sha'],accepted)
        self.assertEqual(self.queues[-1][1]['session_policy']['executor'],'one task per conversation')

    def test_each_review_requires_new_qa_conversation_even_at_same_candidate(self):
        run=self.fixture._single_task_review();self.fixture.record(self.fixture._qa_report(run),'qa')
        count=len(self.queues)
        with self.assertRaisesRegex(RuntimeError,'fresh|conversation|session'):
            transport.review(self.store,self.identity,self.fixture.base)
        self.assertEqual(len(self.queues),count)
        run=self.store.load(self.identity);fresh=self.fresh_actor('qa',run);self.store.save(run)
        reviewed=transport.review(self.store,self.identity,self.fixture.base)
        self.assertEqual(self.queues[-1][0],fresh.session)
        self.assertNotEqual(reviewed['review_contract']['id'],run['review_contract']['id'])

    def test_probes_need_shared_registry_and_dedicated_disposable_conversation(self):
        from watchdog_app.mission import RunStore
        transport.dispatch(self.store,self.identity,self.fixture.task)
        probe_store=RunStore(self.folder/'probe-runs');probe=copy.deepcopy(self.store.load(self.identity))
        probe['id']=str(uuid.uuid4());probe.pop('worker_head',None);probe['events']={};probe['deliveries']={}
        probe['tasks']={self.fixture.task:{'title':'Probe fixture','state':'ready','summary':'','agent':'main','updated':0}}
        probe['brief']['tasks']=[dict(probe['brief']['tasks'][0],purpose='probe')]
        probe['participants']['worker']['purpose']='probe';probe_store.save(probe)
        with self.assertRaisesRegex(RuntimeError,'shared'):transport.dispatch(probe_store,probe['id'],self.fixture.task)
        probe['session_policy']={'registry_dir':str(probe_store.root/'isolated-policy')};probe_store.save(probe)
        with self.assertRaisesRegex(RuntimeError,'shared'):transport.dispatch(probe_store,probe['id'],self.fixture.task)
        probe['session_policy']={'registry_dir':str(self.store.root/'session-policy')};probe_store.save(probe)
        count=len(self.queues)
        with self.assertRaisesRegex(RuntimeError,'fresh|purpose|conversation'):
            transport.dispatch(probe_store,probe['id'],self.fixture.task)
        self.assertEqual(len(self.queues),count)
        fresh=self.fresh_actor('worker',probe,purpose='probe')
        fresh.pane='probe-pane';fresh.terminal='probe-terminal';self.registry[fresh.session]=asdict(fresh)
        path=self.folder/'probe-worktree';git(self.repo,'worktree','add','-b','probe-only',str(path),self.fixture.base)
        probe['participants']['worker'].update(native=asdict(fresh),worktree=str(path),branch='probe-only')
        probe['resources']['worker'].update(pane_id=fresh.pane,terminal_id=fresh.terminal)
        probe_store.save(probe);transport.dispatch(probe_store,probe['id'],self.fixture.task)
        self.assertEqual(self.queues[-1][0],fresh.session)
        reused=copy.deepcopy(probe);reused['id']=str(uuid.uuid4())
        reused['participants']['worker']['purpose']='implementation';reused['brief']['tasks'][0]['purpose']='implementation'
        probe_store.save(reused)
        with self.assertRaisesRegex(RuntimeError,'fresh|purpose|conversation'):
            transport.dispatch(probe_store,reused['id'],self.fixture.task)

    def test_capsule_from_old_reuse_policy_is_stale_even_with_its_valid_old_seal(self):
        value=self.export();value.pop('session_policy',None)
        self.capsule_file.write_text(json.dumps(value))
        seal_path=handoff.record_path(self.store,self.identity,value['handoff_id'])
        seal=json.loads(seal_path.read_text());seal['capsule_sha256']=handoff.digest(value);seal_path.write_text(json.dumps(seal))
        with self.assertRaisesRegex(RuntimeError,'policy|fresh'):self.preview()

    def test_executor_cannot_be_declared_as_a_qa_review_actor(self):
        run=self.store.load(self.identity)
        run['participants']['worker']['purpose']='qa';run['brief']['tasks'][0]['purpose']='qa'
        self.store.save(run)
        with self.assertRaisesRegex(RuntimeError,'role|purpose'):
            transport.dispatch(self.store,self.identity,self.fixture.task)
        self.assertFalse(self.queues)

    def claim_path(self,binding,run=None):
        import hashlib
        run=run or self.store.load(self.identity)
        key=hashlib.sha256((binding.account+'\0'+binding.session).encode()).hexdigest()
        return handoff.registry_path(self.store,run)/(key+'.json')

    def test_replaced_completed_qa_history_rejects_main_even_without_its_claim_file(self):
        run=self.store.load(self.identity);run['participants']['qa']['native']=asdict(self.new)
        run['resources']['qa'].update(pane_id=self.new.pane,terminal_id=self.new.terminal);self.store.save(run)
        reviewed=self.fixture._single_task_review();self.fixture.record(self.fixture._qa_report(reviewed),'qa')
        run=self.store.load(self.identity);fresh=self.fresh_actor('qa',run)
        fresh.pane='replacement-qa';fresh.terminal='replacement-qa-terminal'
        self.registry[fresh.session]=asdict(fresh);run['participants']['qa']['native']=asdict(fresh)
        run['resources']['qa'].update(pane_id=fresh.pane,terminal_id=fresh.terminal);self.store.save(run)
        path=self.claim_path(self.new);self.assertTrue(path.exists());path.unlink()  # pre-registry retained history
        self.export()
        with self.assertRaisesRegex(RuntimeError,'history|purpose|fresh'):self.preview()
        self.assertEqual(self.store.load(self.identity)['qa']['verdict'],'pass')
        self.assertEqual(self.store.load(self.identity)['main'],asdict(self.old))

    def test_prior_qa_claim_between_preview_and_commit_blocks_adoption_and_new_preview(self):
        self.export();offer=self.preview()
        other=copy.deepcopy(self.store.load(self.identity));other['participants']['qa']['native']=asdict(self.new)
        handoff.claim_session(self.store,other,'qa','another-review',self.fixture.base)
        with self.assertRaisesRegex(RuntimeError,'purpose|claim|fresh'):self.adopt(offer,confirmed=True)
        with self.assertRaisesRegex(RuntimeError,'purpose|claim|fresh'):self.preview()
        self.assertEqual(self.store.load(self.identity)['main'],asdict(self.old))

    def test_A_to_B_to_A_is_rejected_by_retained_leader_history(self):
        self.export();self.adopt(self.preview(),confirmed=True)
        path=self.claim_path(self.old)
        if path.exists():path.unlink()  # prove the authoritative ownership audit is checked too
        self.export()
        with self.assertRaisesRegex(RuntimeError,'leader|history|fresh'):
            handoff.preview(self.store,self.identity,self.capsule_file,self.old_file)
        run=self.store.load(self.identity);self.assertEqual(run['main'],asdict(self.new))
        self.assertEqual(run['leader_generation'],1)

    def assert_main_purpose_not_reused(self,purpose):
        from watchdog_app.mission import RunStore
        self.export();self.adopt(self.preview(),confirmed=True)
        other=copy.deepcopy(self.store.load(self.identity));other['id']=str(uuid.uuid4())
        other['leader_handoffs']=[];other['deliveries']={}
        distinct=copy.deepcopy(self.old);distinct.session=str(uuid.uuid4());distinct.pid+=5000
        other['main']=asdict(distinct)
        role='qa' if purpose=='qa' else 'worker'
        other['participants'][role].update(native=asdict(self.new),purpose=purpose)
        other['session_policy']={'registry_dir':str(self.store.root/'session-policy')}
        store=RunStore(self.folder/('repurpose-'+purpose))
        with self.assertRaisesRegex(RuntimeError,'main|purpose|fresh|conversation'):
            handoff.claim_session(store,other,role,str(uuid.uuid4()),self.fixture.base,purpose=purpose)
        self.assertEqual(json.loads(self.claim_path(self.new).read_text())['purpose'],'main')

    def test_adopted_main_cannot_become_worker_in_shared_registry(self):
        self.assert_main_purpose_not_reused('implementation')

    def test_adopted_main_cannot_become_qa_in_shared_registry(self):
        self.assert_main_purpose_not_reused('qa')

    def test_adopted_main_cannot_become_probe_in_shared_registry(self):
        self.assert_main_purpose_not_reused('probe')

    def test_final_main_reservation_locks_out_a_competing_role_claim(self):
        self.export();offer=self.preview();verify=Session.verify;calls=[0]
        competing=copy.deepcopy(self.store.load(self.identity));competing['participants']['qa']['native']=asdict(self.new)
        def race(session):
            live=verify(session)
            if session.binding.session==self.new.session:
                calls[0]+=1
                if calls[0]==3:
                    with self.assertRaisesRegex(RuntimeError,'busy|reserved|main'):
                        handoff.claim_session(self.store,competing,'qa','racing-review',self.fixture.base)
            return live
        with patch.object(Session,'verify',race):self.adopt(offer,confirmed=True)
        self.assertEqual(calls[0],3)
        self.assertEqual(self.store.load(self.identity)['main'],asdict(self.new))
        self.assertEqual(json.loads(self.claim_path(self.new).read_text())['purpose'],'main')

    def test_precommit_crash_reserves_main_and_fails_closed_without_owner_change(self):
        self.export();offer=self.preview()
        with patch.object(self.store,'save',side_effect=SystemExit('before ownership save')):
            with self.assertRaises(SystemExit):self.adopt(offer,confirmed=True)
        self.assertEqual(self.store.load(self.identity)['main'],asdict(self.old))
        self.assertEqual(json.loads(self.claim_path(self.new).read_text())['purpose'],'main')
        with self.assertRaisesRegex(RuntimeError,'reserved|main|purpose|fresh'):self.adopt(offer,confirmed=True)

    def test_current_main_is_reserved_before_task_delivery_and_cannot_change_purpose(self):
        transport.dispatch(self.store,self.identity,self.fixture.task)
        self.assertEqual(json.loads(self.claim_path(self.old).read_text())['purpose'],'main')
        other=copy.deepcopy(self.store.load(self.identity));other['participants']['qa']['native']=asdict(self.old)
        with self.assertRaisesRegex(RuntimeError,'main|leader|purpose|fresh'):
            handoff.claim_session(self.store,other,'qa','illegal-main-review',self.fixture.base)


    def test_worker_and_probe_registry_claims_reject_main_before_offer(self):
        for purpose in ('implementation','probe'):
            with self.subTest(purpose=purpose):
                other=copy.deepcopy(self.store.load(self.identity))
                other['participants']['worker'].update(native=asdict(self.new),purpose=purpose)
                # Explicit canonical registry is outside this fixture's isolated store.
                from watchdog_app.mission import RunStore
                separate=RunStore(self.folder/('prior-'+purpose))
                other['session_policy']={'registry_dir':str(self.store.root/'session-policy')}
                handoff.claim_session(separate,other,'worker','prior-task',self.fixture.base,purpose=purpose)
                self.export()
                with self.assertRaisesRegex(RuntimeError,'purpose|fresh'):self.preview()
                self.claim_path(self.new).unlink()  # independent fixture subcase

    def test_old_session_policy_version_cannot_be_resealed_into_current_adoption(self):
        value=self.export();value['session_policy']['version']=1
        handoff.atomic(self.capsule_file,value)
        seal=handoff.record_path(self.store,self.identity,value['handoff_id'])
        record=json.loads(seal.read_text());record['capsule_sha256']=handoff.digest(value);handoff.atomic(seal,record)
        with self.assertRaisesRegex(RuntimeError,'policy.*stale'):self.preview()
