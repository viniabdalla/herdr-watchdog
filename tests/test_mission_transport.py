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
        self.run.update(id='9c6e1ad3-c0c9-4e05-b4dc-b367753ce3e1',repo=str(self.repo),
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
        with patch.object(transport.Gossip,'call',side_effect=lambda *a,**k:calls.append((a,k)) or 'existing'), patch.object(transport,'verify_participant'):
            transport.followup(self.store,self.run['id'],'task','Use the existing test fixture')
        self.assertEqual(calls[0][1]['task_id'],'existing')
        self.assertIn('Use the existing test fixture',calls[0][0][1])
        self.assertEqual(self.store.load(self.run['id'])['tasks']['task']['gossip_task'],'existing')

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
