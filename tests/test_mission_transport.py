import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from watchdog_app import mission_transport as transport
from watchdog_app.mission import RunStore
import test_mission
from test_mission_launch import git


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='wd-test-bridge-');self.addCleanup(self.temp.cleanup)
        self.repo=Path(self.temp.name)/"repo";self.repo.mkdir()
        git(self.repo,"init","-q");git(self.repo,"config","user.email","test@example.invalid");git(self.repo,"config","user.name","Test")
        (self.repo/"TODO.md").write_text("## Next\n- [ ] Work\n")
        git(self.repo,"add","TODO.md");git(self.repo,"commit","-qm","base")
        self.store=RunStore(Path(self.temp.name)/"runs")
        fixture=test_mission.StateTests();fixture.setUp();self.run=fixture.run
        self.run.update(id='9c6e1ad3-c0c9-4e05-b4dc-b367753ce3e1',created=1,repo=str(self.repo),
            transport={'gossip':'room','nickname':'main'},cursor=0,source_digest=__import__('hashlib').sha256((self.repo/'TODO.md').read_bytes()).hexdigest(),brief={'tasks':[{
                'id':'task','dependencies':[],'allowed_files':['a.py'],'acceptance':['Works'],'tests':['python -m unittest']}], 'base_sha':git(self.repo,'rev-parse','HEAD')})
        self.run['tasks']['task']['state']='ready'
        self.run['tasks']['task'].pop('gossip_task')
        self.run['participants']['worker'].update(native={'session':'native'},available=True,worktree=str(self.repo),base_sha=git(self.repo,'rev-parse','HEAD'))
        self.store.save(self.run)
        self.delivered=[]
        self.session=SimpleNamespace(verify=lambda:None,binding=object(),runtime=SimpleNamespace(queue=lambda b,t:self.delivered.append(t)))
        self.patch=patch.object(transport,'main_session',return_value=self.session);self.patch.start();self.addCleanup(self.patch.stop)

    def test_assignment_timeout_is_not_automatically_resent(self):
        def failed(*args,**kw):raise RuntimeError('timeout')
        with patch.object(transport.Gossip,'call',side_effect=failed), patch.object(transport,'verify_participant'):
            with self.assertRaises(RuntimeError):transport.dispatch(self.store,self.run['id'],'task')
            with self.assertRaisesRegex(RuntimeError,'uncertain|already'):
                transport.dispatch(self.store,self.run['id'],'task')
        self.assertEqual(self.store.load(self.run['id'])['tasks']['task']['delivery'],'uncertain')

    def test_followup_uses_same_gossip_task_without_changing_contract(self):
        self.run['tasks']['task'].update(gossip_task='existing',state='blocked',delivery='sent')
        self.store.save(self.run)
        calls=[]
        guidance='Use /tmp/wd-test-fixture/input.json.\nRun WATCHDOG_GOSSIP_TEST=1 python -m unittest; preserve sandbox settings.'
        with patch.object(transport.Gossip,'call',side_effect=lambda *a,**k:calls.append((a,k)) or 'existing'), patch.object(transport,'verify_participant'):
            transport.followup(self.store,self.run['id'],'task',guidance)
        self.assertEqual(calls[0][1]['task_id'],'existing')
        self.assertEqual(json.loads(calls[0][0][1])['clarification'],guidance)
        task=self.store.load(self.run['id'])['tasks']['task']
        self.assertEqual(task['gossip_task'],'existing')
        from watchdog_app.progress_ui import rows
        primary='\n'.join(row[0] for row in rows(self.repo,self.store))
        self.assertIn('Guidance sent; waiting for the agent',primary)
        self.assertNotIn('/tmp/wd-test-fixture',primary)
        self.assertNotIn('WATCHDOG_GOSSIP_TEST',primary)
        self.assertEqual(task['guidance'][-1]['text'],guidance)
        self.assertEqual(task['guidance'][-1]['task_id'],'existing')
        self.assertEqual(task['guidance'][-1]['delivery'],'sent')

    def test_uncertain_followup_preserves_guidance_without_automatic_retry(self):
        self.run['tasks']['task'].update(gossip_task='existing',state='blocked',delivery='sent')
        self.store.save(self.run)
        with patch.object(transport.Gossip,'call',side_effect=RuntimeError('timeout')) as send,patch.object(transport,'verify_participant'):
            with self.assertRaisesRegex(RuntimeError,'timeout'):
                transport.followup(self.store,self.run['id'],'task','Use the approved fixture')
            with self.assertRaisesRegex(RuntimeError,'uncertain'):
                transport.followup(self.store,self.run['id'],'task','Use the approved fixture')
        self.assertEqual(send.call_count,1)
        task=self.store.load(self.run['id'])['tasks']['task']
        self.assertEqual(len(task['guidance']),1)
        self.assertEqual(task['guidance'][0]['text'],'Use the approved fixture')
        self.assertEqual(task['guidance'][0]['delivery'],'uncertain')

    def test_bridge_queues_compact_event_once_and_never_on_switched_main(self):
        run=self.run
        run['events']['event']={'delivery':'pending','report':{'status':'blocked','summary':'Need test fixture','task_id':'task'},'received':1}
        self.store.save(run)
        transport.forward(self.store,run)
        self.assertEqual(len(self.delivered),1)
        transport.forward(self.store,run)
        self.assertEqual(len(self.delivered),1)
        run['events']['other']=copy.deepcopy(run['events']['event']);run['events']['other']['delivery']='pending'
        with patch.object(transport,'main_session',side_effect=RuntimeError('identity changed')):
            with self.assertRaises(RuntimeError):transport.forward(self.store,run)
        self.assertEqual(len(self.delivered),1)
        self.assertEqual(run['events']['other']['delivery'],'pending')

    def test_peer_task_response_must_have_uuid_before_recording_delivery(self):
        gossip=transport.Gossip({'gossip':'room','nickname':'main'})
        with patch.object(transport,'command',return_value='{"result":{}}'):
            with self.assertRaises(RuntimeError):gossip.call('worker','brief')

    def test_dependencies_and_another_busy_task_block_dispatch(self):
        self.run['brief']['tasks'][0]['dependencies']=['prior']
        self.run['tasks']['prior']={'state':'working','result':{},'gossip_task':'prior-native'}
        self.store.save(self.run)
        with patch.object(transport,'verify_participant'), self.assertRaisesRegex(RuntimeError,'depend|working'):
            transport.dispatch(self.store,self.run['id'],'task')

    def test_changed_todo_and_changed_worker_base_block_new_assignment(self):
        (self.repo/'TODO.md').write_text('## Next\n- [ ] Changed\n')
        with patch.object(transport,'verify_participant'), self.assertRaisesRegex(RuntimeError,'Task list changed'):
            transport.dispatch(self.store,self.run['id'],'task')
        git(self.repo,'restore','TODO.md')
        git(self.repo,'commit','--allow-empty','-qm','unexpected new head')
        with patch.object(transport,'verify_participant'), self.assertRaisesRegex(RuntimeError,'base'):
            transport.dispatch(self.store,self.run['id'],'task')

    def test_changed_gossip_nickname_binding_fails_before_send(self):
        gossip=transport.Gossip({'gossip':'room','nickname':'main'})
        with patch.object(gossip,'peers',return_value=[{'nickname':'worker','pubkey':'foreign'}]), self.assertRaisesRegex(RuntimeError,'identity'):
            gossip.call('worker','brief',expected_key='approved')

    def test_qa_cannot_switch_candidate_while_review_is_running(self):
        self.run.update(qa_task='active-review',qa_delivery='sent',candidate='a'*40,qa=None)
        self.run['tasks']['task'].update(result={'commits':['a'*40],'tests':['passed']},state='review')
        self.store.save(self.run)
        with patch.object(transport,'verify_participant'),patch.object(transport,'owned_worktree'),self.assertRaisesRegex(RuntimeError,'QA review is still in progress'):
            transport.review(self.store,self.run['id'],'b'*40)

    def test_empty_working_ack_is_not_a_report_and_malformed_error_recovers(self):
        self.run['tasks']['task'].update(gossip_task='native-task',state='working')
        self.store.save(self.run)
        base={'event':'task','kind':'status-update','state':'working','author':'worker','pubkey':'key','task_id':'native-task'}
        ack=dict(base,id='ack',seq=1,body='')
        bad=dict(base,id='bad',seq=2,body='This is not a structured implementation report')
        good=dict(base,id='good',seq=3,body=json.dumps({'run_id':self.run['id'],'task_id':'task','status':'working','summary':'Running tests'}))
        with patch.object(transport,'register'),patch.object(transport,'forward'),patch.object(transport.Gossip,'peers',return_value=[{'pubkey':'key'}]),patch.object(transport.Gossip,'poll',side_effect=[[ack],[bad],[good]]):
            after=transport.tick(self.store,self.run['id'])
            self.assertFalse(after.get('reason'))
            self.assertFalse(after.get('report_errors'))
            self.assertEqual(after['events'],{})
            after=transport.tick(self.store,self.run['id'])
            self.assertIn('native-task',after.get('report_errors',{}))
            after=transport.tick(self.store,self.run['id'])
            self.assertFalse(after.get('report_errors'))
            self.assertEqual(after['tasks']['task']['summary'],'Running tests')

    def test_superseded_qa_report_still_notifies_main_that_attempt_ended(self):
        self.run.update(candidate='a'*40,qa_task='qa-native',qa_finished=False,result_version=2,
            review_contract={'id':'review-A','candidate':'a'*40,'version':1,'verified_commits':True})
        self.store.save(self.run)
        report={'run_id':self.run['id'],'status':'qa','candidate':'a'*40,'review_id':'review-A',
                'verdict':'pass','summary':'A review ended, now superseded','tests':['A suite passed']}
        sent=[]
        with patch.object(transport,'verify_participant'),patch.object(transport.Gossip,'invoke',side_effect=lambda *a:sent.append(a)):
            transport.report(self.store,self.run['id'],'qa',report)
        self.assertEqual(sent[0][:2],('a2a','artifact'))
        self.assertIn('qa-native',sent[0])

    def test_native_identity_loss_blocks_report_even_from_pinned_gossip_key(self):
        self.run['tasks']['task'].update(gossip_task='native-task',state='working')
        self.run.update(qa_task='qa-native',candidate='a'*40,qa_finished=False,
            review_contract={'id':'review-A','candidate':'a'*40,'version':0,'verified_commits':True})
        reports={
            'worker':{'task_id':'task','status':'result','commits':['a'*40],'tests':['passed']},
            'qa':{'status':'qa','candidate':'a'*40,'review_id':'review-A','verdict':'pass','tests':['passed']}}
        for role,report in reports.items():
            with self.subTest(role=role):
                self.store.save(self.run)
                self.delivered.clear()
                native_task='native-task' if role=='worker' else 'qa-native'
                key=self.run['participants'][role]['pubkey']
                event={'id':'result-after-switch','seq':1,'event':'task','kind':'artifact-update',
                       'author':role,'pubkey':key,'task_id':native_task,
                       'body':json.dumps({'run_id':self.run['id'],'summary':'New identity claims result',**report})}
                def lost_identity(run,*_):
                    run['participants'][role].update(available=False,problem='Native identity changed')
                with patch.object(transport,'register',side_effect=lost_identity),patch.object(transport.Gossip,'peers',return_value=[{'pubkey':key}]),patch.object(transport.Gossip,'poll',return_value=[event]):
                    after=transport.tick(self.store,self.run['id'])
                self.assertEqual(after['tasks'],self.run['tasks'])
                self.assertIsNone(after['qa'])
                self.assertFalse(after['qa_finished'])
                self.assertIn('identity',after['report_errors'][native_task])
                self.assertEqual(after['events']['result-after-switch']['rejected']['body'],event['body'])
                self.assertEqual(len(self.delivered),1)
                self.assertIn('report retained for inspection',self.delivered[0])
                self.assertNotIn('New identity claims result',self.delivered[0])
