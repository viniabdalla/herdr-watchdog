import copy
import json
from pathlib import Path
import tempfile
import unittest
from watchdog_app import verification as v
RUN='cb0a2492-8455-45ed-ba2b-1b3b39638fdb'
SHA='a'*40
class VerificationTests(unittest.TestCase):
    def test_dispatch_alone_is_incomplete_and_does_not_invent_stages(self):
        data=v.assess(RUN,[dict(observed_at=1,status='preparing'),dict(observed_at=2,status='running')],dict(id=RUN,phase='active',tasks={}))
        self.assertEqual(data['observed_stages'],['preparing','running'])
        self.assertFalse(data['complete']);self.assertIn('verifying',data['missing_stages'])
        self.assertFalse(data['exact_candidate_qa'])
    def test_same_candidate_review_and_integration_gates_required(self):
        observations=[dict(observed_at=i+1,status=status) for i,status in enumerate(('preparing','running','verifying','decision'))]
        run=dict(id=RUN,phase='done',candidate=SHA,result_version=1,tasks={'task':dict(state='done',result={'commits':[SHA]})},
                 qa=dict(verdict='pass',candidate=SHA),qa_finished=True,
                 qa_contract=dict(candidate=SHA,result_version=1),approved=dict(candidate=SHA),integration=dict(candidate=SHA,status='pushed'))
        result=v.assess(RUN,observations,run)
        # Synthetic observation alone is never evidence of real model or native queue.
        self.assertEqual(result['evidence_kind'],'read-only ledger assessment')
        other=copy.deepcopy(run);other['qa']['candidate']='b'*40
        self.assertFalse(v.assess(RUN,observations,other)['exact_candidate_qa'])
        other=copy.deepcopy(run);other['candidate']=None
        self.assertFalse(v.assess(RUN,observations,other)['complete'])
    def test_ordering_and_partial_logs_are_not_silently_accepted(self):
        data=v.assess(RUN,[dict(observed_at=1,status='running'),dict(observed_at=2,status='preparing')],dict(id=RUN,phase='active',tasks={}))
        self.assertFalse(data['ordered'])
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'obs';p.write_text('{"status":"running","observed_at":1}\n{"status":')
            result=v.read_observations(p)
            self.assertTrue(result['incomplete']);self.assertEqual(len(result['records']),1)
    def test_wrong_run_or_excessive_input_refused(self):
        with self.assertRaises(RuntimeError):v.assess(RUN,[],dict(id='wrong'))
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'obs';p.write_bytes(b'x'*(v.LIMIT+1))
            with self.assertRaises(RuntimeError):v.read_observations(p)

    def test_passing_exact_candidate_ledger_can_complete_ordered_fixture_only(self):
        qa=dict(status='qa',verdict='pass',candidate=SHA,review_id='r',tests=['fixture tests passed'])
        run=dict(id=RUN,phase='done',candidate=SHA,result_version=2,qa=qa,qa_finished=True,
            review_contract=dict(candidate=SHA,id='r',version=2,verified_commits=True),
            tasks={'task':dict(state='done',result={'commits':[SHA]})},
            integration=dict(candidate=SHA,head=SHA,how='fast-forward',pushed=True))
        observations=[dict(observed_at=i+1,status=status,candidate=SHA)
            for i,status in enumerate(('preparing','running','verifying','decision'))]
        result=v.assess(RUN,observations,run)
        self.assertTrue(result['complete']);self.assertTrue(result['exact_candidate_qa'])
        self.assertTrue(result['pushed'])
        run['review_contract']['version']=1
        self.assertFalse(v.assess(RUN,observations,run)['complete'])
