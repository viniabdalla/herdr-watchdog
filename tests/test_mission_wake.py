"""Coordination notifications target verified native threads, never pane input."""
from dataclasses import asdict
import json
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import patch

from test_actions import FakeBinding
import test_mission_transport
from watchdog_app import mission_transport as transport
from watchdog_app.progress_ui import rows


class WakeTests(unittest.TestCase):
    def setUp(self):
        test_mission_transport.TransportTests.setUp(self)
        self.native={role:FakeBinding(session=str(uuid.uuid4()),account='/test/'+role,
            pane=role+'-pane',terminal=role+'-terminal') for role in ('worker','qa')}
        self.run['resources']={}
        for role,native in self.native.items():
            self.run['participants'][role].update(native=asdict(native),account=native.account,
                available=True,worktree=str(self.repo))
            self.run['resources'][role]={'pane_id':native.pane,'terminal_id':native.terminal}
        self.store.save(self.run)
        self.status='idle';self.switched=None;self.fail_queue=False;self.notifications=[]
        self.native_task=str(uuid.uuid4());self.receipt=str(uuid.uuid4())
        def verify(binding):
            if self.switched and binding==self.native[self.switched]:raise RuntimeError('Native identity changed')
            return {'agent_status':self.status}
        def queue(binding,message):
            verify(binding)
            persisted=self.store.load(self.run['id'])
            self.assertTrue(any(w['delivery']=='sending' and w['recipient']==asdict(binding)
                                for w in persisted['wakes'].values()))
            self.notifications.append((binding,message))
            if self.fail_queue:raise RuntimeError('queue timeout')
            return self.receipt
        runtime=SimpleNamespace(Binding=FakeBinding,verify=verify,queue=queue)
        for p in (patch.object(transport.bindings,'engine',return_value=runtime),
                  patch.object(transport,'verify_graph')):
            p.start();self.addCleanup(p.stop)

    def assert_notification(self,run,role,record):
        self.assertEqual(len(self.notifications),1)
        recipient,message=self.notifications[0]
        self.assertEqual(recipient,self.native[role])
        self.assertIn(self.native_task,message)
        self.assertIn('Poll',message)
        self.assertIn('already handled',message)
        self.assertIn('not another task',message)
        wake=run['wakes'][record['wake_id']]
        self.assertEqual(wake['delivery'],'queued')
        self.assertEqual(wake['receipt'],self.receipt)
        self.assertNotIn('consumed',wake)

    def test_idle_dispatch_queues_exact_thread_once_after_correlated_send(self):
        with patch.object(transport.Gossip,'call',return_value=self.native_task) as send:
            run=transport.dispatch(self.store,self.run['id'],'task')
            self.assert_notification(run,'worker',run['tasks']['task'])
            transport.wake_participant(self.store,run,'worker',self.native_task,run['tasks']['task'])
            with self.assertRaisesRegex(RuntimeError,'already'):
                transport.dispatch(self.store,self.run['id'],'task')
        self.assertEqual(send.call_count,1)
        self.assertEqual(len(self.notifications),1)
        self.assertEqual((self.repo/'TODO.md').read_text(),'## Next\n- [ ] Work\n')

    def test_busy_followup_queues_only_a_poll_notice_on_same_thread_and_task(self):
        self.status='working'
        self.run['tasks']['task'].update(gossip_task=self.native_task,state='blocked',delivery='sent')
        self.store.save(self.run)
        with patch.object(transport.Gossip,'call',return_value=self.native_task) as send:
            run=transport.followup(self.store,self.run['id'],'task','Use the approved fixture path')
        self.assertEqual(send.call_args.kwargs['task_id'],self.native_task)
        self.assertEqual(json.loads(send.call_args.args[1])['clarification'],'Use the approved fixture path')
        self.assert_notification(run,'worker',run['tasks']['task']['guidance'][-1])
        self.assertNotIn('Use the approved fixture path',self.notifications[0][1])

    def test_exact_candidate_review_notifies_verified_qa(self):
        candidate=self.run['brief']['base_sha']
        self.run['tasks']['task'].update(state='review',result={'commits':[candidate],'tests':['passed']})
        self.store.save(self.run)
        with patch.object(transport.Gossip,'call',return_value=self.native_task):
            run=transport.review(self.store,self.run['id'],candidate)
        self.assert_notification(run,'qa',run['review_contract'])
        self.assertIsNone(run['qa'])

    def test_identity_change_after_gossip_send_retains_pending_wake_without_queue(self):
        for changed in ('source','recipient'):
            with self.subTest(changed=changed):
                self.switched=None;self.store.save(self.run)
                def send(*_,**__):
                    self.switched='worker' if changed=='recipient' else None
                    return self.native_task
                source=[self.session,RuntimeError('Main identity changed')] if changed=='source' else [self.session,self.session]
                with patch.object(transport.Gossip,'call',side_effect=send),patch.object(transport,'main_session',side_effect=source):
                    with self.assertRaisesRegex(RuntimeError,'notification'):
                        transport.dispatch(self.store,self.run['id'],'task')
                run=self.store.load(self.run['id'])
                self.assertEqual(run['tasks']['task']['delivery'],'sent')
                self.assertEqual(run['tasks']['task']['state'],'blocked')
                self.assertEqual(next(iter(run['wakes'].values()))['delivery'],'pending')
                self.assertFalse(self.notifications)
                self.assertIn('Agent notification pending','\n'.join(r[0] for r in rows(self.repo,self.store)))

    def test_uncertain_queue_is_retained_without_repeating_wake_or_gossip(self):
        self.fail_queue=True
        self.run['tasks']['task'].update(gossip_task=self.native_task,state='blocked',delivery='sent')
        self.store.save(self.run)
        with patch.object(transport.Gossip,'call',return_value=self.native_task) as send:
            with self.assertRaisesRegex(RuntimeError,'uncertain'):
                transport.followup(self.store,self.run['id'],'task','Approved clarification')
            with self.assertRaisesRegex(RuntimeError,'notification'):
                transport.followup(self.store,self.run['id'],'task','Approved clarification')
        run=self.store.load(self.run['id']);record=run['tasks']['task']['guidance'][-1]
        wake=run['wakes'][record['wake_id']]
        self.assertEqual(wake['delivery'],'uncertain')
        self.assertEqual(wake['recipient'],asdict(self.native['worker']))
        with self.assertRaisesRegex(RuntimeError,'uncertain'):
            transport.wake_participant(self.store,run,'worker',self.native_task,record)
        self.assertEqual(send.call_count,1)
        self.assertEqual(len(self.notifications),1)
        self.assertIn('Agent notification uncertain','\n'.join(r[0] for r in rows(self.repo,self.store)))
