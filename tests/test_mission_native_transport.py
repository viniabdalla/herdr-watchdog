"""Native backend: real Git/RunStore, stub only the external Codex identity/queue."""
import copy
from dataclasses import asdict
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import patch

from test_actions import FakeBinding
import test_mission_launch as launch_tests
from test_mission_launch import git
from watchdog_app import mission_transport as transport
from watchdog_app import mission_native as native
from watchdog_app.mission import finish


class NativeTransportTests(unittest.TestCase):
    def setUp(self):
        fixture=launch_tests.LaunchTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        self.fixture=fixture;fixture.brief.pop('transport',None)
        with patch.object(launch_tests.launch,'create_gossip',side_effect=FileNotFoundError('agent-gossip missing')), \
                patch.object(launch_tests.launch,'role_context',side_effect=AssertionError('No graph CLI on native launch')):
            self.run=fixture.start()
        self.store=fixture.store;self.identity=fixture.run_id
        self.repo=fixture.repo;self.base=fixture.base
        self.calls=[];self.status='idle';self.fail_queue=False;self.receipt=str(uuid.uuid4())
        def verify(binding):return {'agent_status':self.status}
        def queue(binding,text):
            run=self.store.load(self.identity)
            if binding.session != self.run['main']['session']:
                self.assertTrue(any(d['state']=='sending' and d['recipient']==asdict(binding) for d in run['deliveries'].values()))
            else:self.assertTrue(any(e['delivery']=='sending' for e in run['events'].values()))
            self.calls.append((binding,json.loads(text.split('\n',1)[1]) if '\n' in text else text))
            if self.fail_queue:raise RuntimeError('queue receipt timed out')
            return self.receipt
        self.runtime=SimpleNamespace(Binding=FakeBinding,verify=verify,queue=queue)
        for p in (patch.object(native.bindings,'engine',return_value=self.runtime),
                  patch.object(transport.Gossip,'invoke',side_effect=AssertionError('Gossip unavailable'))):
            p.start();self.addCleanup(p.stop)
        self.bindings={}
        for role in ('worker','qa'):
            pane=self.run['resources'][role]
            b=FakeBinding(session=str(uuid.uuid4()),account=self.run['participants'][role]['account'],
                          pane=pane['pane_id'],terminal=pane['terminal_id'])
            self.bindings[role]=b
            self.run['participants'][role].update(native=asdict(b),generation=str(uuid.uuid4()),
                boot_id=native.boot_id(),bridge_owner=native.owner(),enrolled=True,available=True)
        self.store.save(self.run)
        self.main=SimpleNamespace(binding=FakeBinding(),runtime=self.runtime)
        p=patch.object(transport,'main_session',return_value=self.main);p.start();self.addCleanup(p.stop)
        self.task=next(iter(self.run['tasks']))

    def proof(self,role='worker'):
        part=self.store.load(self.identity)['participants'][role]
        return {'transport':'native','run_id':self.identity,'role':role,'native':part['native'],
                'generation':part['generation'],'boot_id':part['boot_id'],'bridge_owner':part['bridge_owner']}

    def report(self,status='working',**extra):
        run=self.store.load(self.identity)
        return {'run_id':self.identity,'task_id':self.task,'attempt_id':run['tasks'][self.task]['attempt_id'],
                'event_id':str(uuid.uuid4()),'status':status,'summary':'Observed native progress',**extra}

    def record(self,report,role='worker'):
        return native.handle(self.store,self.identity,role,self.proof(role),'report',{'report':report})

    def test_default_launch_needs_no_gossip_or_graph_command(self):
        self.assertEqual(self.run['transport']['kind'],'native')
        self.assertEqual(self.run['identity_protocol'],3)
        self.assertFalse(any('gossip' in call for call in self.fixture.api.calls))
        self.assertEqual(git(self.repo,'rev-parse','HEAD'),self.base)

    def test_idle_and_busy_exact_thread_contract_delivery_is_durable_once(self):
        run=transport.dispatch(self.store,self.identity,self.task)
        first=run['tasks'][self.task]['attempt_id']
        b,message=self.calls[0]
        self.assertEqual(b,self.bindings['worker'])
        self.assertEqual(message['attempt_id'],first)
        self.assertEqual(message['base_sha'],self.base)
        self.assertEqual(message['task_id'],self.task)
        self.assertEqual(run['deliveries'][first]['receipt'],self.receipt)
        with self.assertRaisesRegex(RuntimeError,'already|uncertain'):transport.dispatch(self.store,self.identity,self.task)
        self.status='working'
        run=transport.followup(self.store,self.identity,self.task,'Use the existing fixture')
        self.assertNotEqual(run['tasks'][self.task]['attempt_id'],first)
        self.assertEqual(self.calls[-1][0],self.bindings['worker'])
        self.assertEqual(self.calls[-1][1]['clarification'],'Use the existing fixture')
        self.assertEqual(len(self.calls),2)

    def test_timeout_and_interrupted_intent_are_uncertain_without_retry(self):
        self.fail_queue=True
        with self.assertRaisesRegex(RuntimeError,'uncertain'):transport.dispatch(self.store,self.identity,self.task)
        with self.assertRaisesRegex(RuntimeError,'already|uncertain'):transport.dispatch(self.store,self.identity,self.task)
        self.assertEqual(len(self.calls),1)
        run=self.store.load(self.identity)
        delivery=next(iter(run['deliveries'].values()));self.assertEqual(delivery['state'],'uncertain')
        delivery['state']='sending';self.store.save(run)
        transport.tick(self.store,self.identity)
        self.assertEqual(next(iter(self.store.load(self.identity)['deliveries'].values()))['state'],'uncertain')
        self.assertEqual(len(self.calls),1)

    def test_report_is_persisted_then_forwarded_to_main_and_replay_is_noop(self):
        transport.dispatch(self.store,self.identity,self.task)
        report=self.report();receipt=self.record(report)
        self.assertEqual(receipt['event_id'],report['event_id'])
        run=self.store.load(self.identity)
        self.assertEqual(run['tasks'][self.task]['state'],'working')
        self.assertEqual(run['events'][report['event_id']]['delivery'],'sent')
        self.assertEqual(self.calls[-1][0],self.main.binding)
        count=len(self.calls);version=run['result_version']
        self.record(report)
        self.assertEqual(len(self.calls),count)
        self.assertEqual(self.store.load(self.identity)['result_version'],version)
        with self.assertRaisesRegex(RuntimeError,'reused'):self.record(dict(report,summary='Changed'))
        self.assertEqual((self.repo/'TODO.md').read_text(),'## Next\n- [ ] First\n- [ ] Second\n')

    def test_wrong_stale_actor_attempt_role_and_boot_are_rejected(self):
        transport.dispatch(self.store,self.identity,self.task);report=self.report()
        for field,value in [('generation','other'),('boot_id','other'),('role','qa')]:
            proof=self.proof();proof[field]=value
            with self.assertRaises(RuntimeError):native.handle(self.store,self.identity,'worker',proof,'report',{'report':report})
        with self.assertRaisesRegex(RuntimeError,'attempt'):self.record(dict(report,attempt_id=str(uuid.uuid4())))
        with self.assertRaises(RuntimeError):self.record(report,'qa')
        self.assertFalse(self.store.load(self.identity)['events'])

    def test_report_survives_uncertain_notification_and_monitor_never_resends(self):
        transport.dispatch(self.store,self.identity,self.task);report=self.report('blocked')
        self.fail_queue=True
        receipt=self.record(report)
        self.assertEqual(receipt['notification'],'uncertain')
        self.fail_queue=False;count=len(self.calls)
        transport.tick(self.store,self.identity);self.record(report)
        self.assertEqual(len(self.calls),count)
        self.assertIn(report['event_id'],self.store.load(self.identity)['events'])

    def test_pending_forward_resumes_after_restart_without_duplicate_report(self):
        transport.dispatch(self.store,self.identity,self.task);report=self.report()
        with patch.object(transport,'main_session',side_effect=RuntimeError('main unavailable')):
            self.assertEqual(self.record(report)['notification'],'pending')
        transport.tick(self.store,self.identity)
        run=self.store.load(self.identity)
        self.assertEqual(run['events'][report['event_id']]['delivery'],'sent')
        self.assertEqual(len(run['events']),1)

    def test_exact_qa_candidate_and_no_fabricated_partial_run_gate(self):
        transport.dispatch(self.store,self.identity,self.task)
        self.record(self.report('result',commits=[self.base],tests=['Observed base check']))
        with self.assertRaisesRegex(RuntimeError,'Every selected'):transport.review(self.store,self.identity,self.base)
        # Independent one-task test run scope, not a fake result for the second task.
        run=self.store.load(self.identity);run['tasks']={self.task:run['tasks'][self.task]}
        run['brief']['tasks']=[run['brief']['tasks'][0]];self.store.save(run)
        run=transport.review(self.store,self.identity,self.base)
        contract=run['review_contract'];self.assertEqual(contract['candidate'],self.base)
        report={'run_id':self.identity,'event_id':str(uuid.uuid4()),'attempt_id':run['qa_task'],
                'review_id':contract['id'],'candidate':self.base,'status':'qa','verdict':'pass',
                'summary':'Independent test verdict','tests':['Observed QA check']}
        for changed in ({'candidate':'f'*40},{'verdict':'maybe'},{'review_id':str(uuid.uuid4())}):
            with self.assertRaises(RuntimeError):self.record(dict(report,**changed),'qa')
        self.record(report,'qa')
        run=self.store.load(self.identity);finish(run,self.base,confirmed=True)
        self.assertEqual(run['phase'],'done')
        self.assertEqual((self.repo/'TODO.md').read_text(),'## Next\n- [ ] First\n- [ ] Second\n')

    def test_replacement_actor_cannot_report_a_previous_actor_assignment(self):
        transport.dispatch(self.store,self.identity,self.task);report=self.report()
        run=self.store.load(self.identity)
        run['participants']['worker']['generation']=str(uuid.uuid4())
        self.store.save(run)
        with self.assertRaisesRegex(RuntimeError,'recipient|generation|attempt'):self.record(report)

    def test_native_socket_enrollment_receive_and_report_are_role_scoped(self):
        from watchdog_app.mission_broker import Broker,process,request
        run=self.store.load(self.identity)
        b=self.bindings['worker'];b.pid=os.getpid();b.started=process(b.pid)[1]
        run['participants']['worker'].update(native=asdict(b),enrolled=False)
        self.store.save(run)
        folder=self.store.root/self.identity
        proof=self.proof();proof['broker']=str(folder/'native-test.sock')
        (folder/'worker-identity.json').write_text(json.dumps(proof))
        broker=Broker(self.store,self.identity,'worker',proof,SimpleNamespace(poll=lambda:None))
        self.addCleanup(broker.close)
        with patch.dict(os.environ,{'CODEX_THREAD_ID':b.session}):
            self.assertEqual(request(self.store,self.identity,'worker','enroll')['transport'],'native')
            transport.dispatch(self.store,self.identity,self.task)
            inbox=request(self.store,self.identity,'worker','poll',after=0)
            self.assertEqual(inbox[0]['contract']['task_id'],self.task)
            self.assertEqual(request(self.store,self.identity,'worker','poll',after=inbox[-1]['seq']),[])
            report=self.report()
            result=request(self.store,self.identity,'worker','report',report=report)
            self.assertTrue(result['persisted'])
            with self.assertRaisesRegex(RuntimeError,'Unsupported'):
                request(self.store,self.identity,'worker','shell',command='echo forbidden')
            with self.assertRaisesRegex(RuntimeError,'too large'):
                request(self.store,self.identity,'worker','report',report={'text':'x'*140000})
        with patch.dict(os.environ,{'CODEX_THREAD_ID':'wrong-thread'}):
            with self.assertRaisesRegex(RuntimeError,'assigned native'):
                request(self.store,self.identity,'worker','poll',after=0)
        self.assertIn(report['event_id'],self.store.load(self.identity)['events'])

    def test_existing_actor_bridge_requires_explicit_idle_boundary_and_preserves_legacy(self):
        with self.assertRaisesRegex(RuntimeError,'confirmation'):
            native.host_bridge(self.store,self.identity,'worker')
        run=self.store.load(self.identity);run['participants']['worker'].pop('generation');self.store.save(run)
        self.status='working'
        with self.assertRaisesRegex(RuntimeError,'idle'):
            native.host_bridge(self.store,self.identity,'worker',confirmed=True)
        self.status='idle'
        run=self.store.load(self.identity);run['transport']={'gossip':'legacy'};self.store.save(run)
        with self.assertRaisesRegex(RuntimeError,'native'):
            native.host_bridge(self.store,self.identity,'worker',confirmed=True)
        self.assertEqual(self.store.load(self.identity)['transport'],{'gossip':'legacy'})

    def test_idle_host_bridge_enrolls_same_pinned_actor_without_restart(self):
        from watchdog_app.mission_broker import request
        run=self.store.load(self.identity)
        part=run['participants']['worker'];expected=part['native']
        for key in ('generation','bridge_owner','boot_id'):part.pop(key,None)
        part['enrolled']=False;self.store.save(run)
        with patch.object(native.bindings,'discover',return_value=([self.bindings['worker']],[])):
            bridge=native.host_bridge(self.store,self.identity,'worker',confirmed=True)
        self.addCleanup(bridge.close)
        # The test frontend's descendants use real SO_PEERCRED ancestry in the other
        # socket test; this verifies idle attachment pins the exact existing identity.
        self.assertEqual(bridge.proof['native'],expected)
        self.assertEqual(self.store.load(self.identity)['participants']['worker']['native'],expected)
        self.assertTrue(bridge.child.poll() is None)

    def test_qa_working_is_not_a_finished_or_failed_review(self):
        transport.dispatch(self.store,self.identity,self.task)
        self.record(self.report('result',commits=[self.base],tests=['Observed check']))
        run=self.store.load(self.identity);run['tasks']={self.task:run['tasks'][self.task]}
        run['brief']['tasks']=[run['brief']['tasks'][0]];self.store.save(run)
        run=transport.review(self.store,self.identity,self.base)
        report={'run_id':self.identity,'event_id':str(uuid.uuid4()),'attempt_id':run['qa_task'],
                'review_id':run['review_contract']['id'],'candidate':self.base,'status':'working',
                'summary':'Reviewing actual candidate'}
        self.record(report,'qa');run=self.store.load(self.identity)
        self.assertFalse(run['qa_finished']);self.assertIsNone(run['qa'])
        self.assertEqual(run['tasks'][self.task]['state'],'review')

    def test_native_broker_rechecks_client_liveness_before_persisting_report(self):
        from watchdog_app.mission_broker import Broker
        transport.dispatch(self.store,self.identity,self.task);report=self.report()
        broker=Broker.__new__(Broker);broker.store=self.store;broker.identity=self.identity
        broker.role='worker';broker.proof=self.proof();broker.child=SimpleNamespace(poll=lambda:None)
        message={'run':self.identity,'role':'worker','session':broker.proof['native']['session'],
                 'method':'report','data':{'report':report}}
        with patch('watchdog_app.mission_broker.authorize',side_effect=['old-start','changed-start']):
            with self.assertRaisesRegex(RuntimeError,'caller exited|recycled'):
                broker.execute(123,os.getuid(),message)
        self.assertFalse(self.store.load(self.identity)['events'])

    def test_native_report_notification_uncertainty_is_visible_in_progress(self):
        from watchdog_app.progress_ui import rows
        transport.dispatch(self.store,self.identity,self.task);self.fail_queue=True
        self.record(self.report('blocked'))
        text='\n'.join(row[0] for row in rows(self.repo,self.store))
        self.assertIn('Main notification uncertain',text)

    def test_report_from_previous_attempt_after_followup_is_rejected(self):
        transport.dispatch(self.store,self.identity,self.task);old=self.report('blocked')
        transport.followup(self.store,self.identity,self.task,'Current fixture only')
        with self.assertRaisesRegex(RuntimeError,'attempt'):
            self.record(old)
        self.assertFalse(self.store.load(self.identity)['events'])

    def test_superseded_qa_is_retained_as_rejected_evidence_in_main_notification(self):
        transport.dispatch(self.store,self.identity,self.task)
        self.record(self.report('result',commits=[self.base],tests=['Observed check']))
        run=self.store.load(self.identity);run['tasks']={self.task:run['tasks'][self.task]}
        run['brief']['tasks']=[run['brief']['tasks'][0]];self.store.save(run)
        run=transport.review(self.store,self.identity,self.base)
        report={'run_id':self.identity,'event_id':str(uuid.uuid4()),'attempt_id':run['qa_task'],
                'review_id':run['review_contract']['id'],'candidate':self.base,'status':'qa',
                'verdict':'pass','summary':'Stale QA evidence','tests':['Observed old check']}
        transport.followup(self.store,self.identity,self.task,'Fix the required issue')
        self.record(report,'qa')
        run=self.store.load(self.identity)
        self.assertIsNone(run['qa']);self.assertTrue(run['qa_finished'])
        self.assertIn('superseded',self.calls[-1][1]['rejected'])

    def test_plain_cli_report_uses_the_native_scoped_bridge_without_gossip(self):
        from watchdog_app import mission_cli
        from contextlib import redirect_stdout
        import io
        transport.dispatch(self.store,self.identity,self.task)
        report=self.report();path=self.repo.parent/'report.json';path.write_text(json.dumps(report))
        with patch('watchdog_app.mission_broker.request',side_effect=lambda store,identity,role,method,**data:
                   native.handle(store,identity,role,self.proof(role),method,data)),redirect_stdout(io.StringIO()):
            result=mission_cli.main(['report','--run',self.identity,'--role','worker',
                    '--state-dir',str(self.store.root),'--file',str(path)])
        self.assertEqual(result,0)
        self.assertIn(report['event_id'],self.store.load(self.identity)['events'])

    def test_native_enroll_missing_bridge_never_falls_through_to_gossip(self):
        from watchdog_app import mission_identity
        (self.store.root/self.identity/'worker-identity.json').write_text(json.dumps(self.proof()))
        with patch.object(mission_identity,'command',side_effect=AssertionError('Gossip command forbidden')):
            with self.assertRaisesRegex(RuntimeError,'bridge'):
                mission_identity.enroll(self.store,self.identity,'worker')

    def test_native_enroll_rejects_non_object_data(self):
        with self.assertRaisesRegex(RuntimeError,'data'):
            native.handle(self.store,self.identity,'worker',self.proof(),'enroll',[])
