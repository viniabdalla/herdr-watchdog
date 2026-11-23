from dataclasses import asdict, replace
import json
from pathlib import Path
import tempfile
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from test_actions import FakeBinding
from watchdog_app import curate
from watchdog_app.todo import Snapshot
from watchdog_app.todo_format import render
ID='9f4cdfb9-3b30-4d69-a178-aa3ff61301a6'
class CuratorValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.repo=Path(self.tmp.name)
        env=patch.dict(os.environ,{'WATCHDOG_STATE_DIR':str(self.repo/'state')});env.start();self.addCleanup(env.stop)
        (self.repo/'TODO.md').write_text('---\nwatchdog_todo: 1\n---\n## Next\n'+render('Colors',dict(id=ID,summary='Colors',origin='pedido-humano',execution='Details',acceptance='Verify colors')))
        self.snap=Snapshot.read(self.repo);self.log=self.repo/'real-selected.jsonl'
        self.binding=FakeBinding(history=str(self.log));self.session=SimpleNamespace(repo=self.repo,binding=self.binding,verify=lambda:None)
        self.reply('Colors implemented and tests passed.')
    def reply(self,text):self.log.write_text(json.dumps(dict(type='event_msg',payload=dict(type='task_complete',turn_id='t',last_agent_message=text)))+'\n')
    def output(self,quote):return dict(done=[dict(id=ID,evidence=quote)],blocked=[],add=[])
    def test_replay_is_labelled_and_never_calls_model_or_changes_task_before_selection(self):
        with patch.object(curate,'ask_codex',side_effect=AssertionError('no model')):
            result=curate.validate_existing(self.session,self.snap,self.output('Colors implemented and tests passed.'))
        self.assertEqual(result['observation'],'bounded-replay; no curator model invoked')
        self.assertEqual((self.repo/'TODO.md').read_bytes(),self.snap.raw)
        curate.apply_review(self.session,self.snap,result,set())
        self.assertEqual((self.repo/'TODO.md').read_bytes(),self.snap.raw)
        self.assertTrue(curate.apply_review(self.session,self.snap,result,{0}).tasks[0].done)
    def test_unsupported_and_contradicted_completion_withheld(self):
        for text in ['Colors still pending.','Colors implemented. Colors are not done.','Colors partially implemented.','Unrelated feature implemented.','Colors não concluído.','Colors implemented. Colors remains unfinished.']:
            result=curate.validate_proposals(self.output(text),self.snap,text)
            self.assertFalse(result['actions'],text);self.assertTrue(result['rejected'])
    def test_recipient_stale_source_and_partial_refused(self):
        result=curate.validate_existing(self.session,self.snap,self.output('Colors implemented and tests passed.'))
        self.session.binding=replace(self.binding,session='different')
        with self.assertRaises(RuntimeError):curate.apply_review(self.session,self.snap,result,{0})
        self.session.binding=self.binding
        with self.log.open('a') as f:f.write('{"type":')
        with self.assertRaises(RuntimeError):curate.apply_review(self.session,self.snap,result,{0})
        with self.assertRaises(RuntimeError):curate.validate_existing(self.session,self.snap,self.output('Colors implemented and tests passed.'))
    def test_duplicate_proposals_and_blocking_without_impediment_withheld(self):
        raw=self.output('Colors implemented and tests passed.');raw['done']*=2
        self.assertFalse(curate.validate_proposals(raw,self.snap,'Colors implemented and tests passed.')['actions'])
        raw=dict(done=[],blocked=[dict(id=ID,reason='Waiting',evidence='Colors are next.')],add=[])
        self.assertFalse(curate.validate_proposals(raw,self.snap,'Colors are next.')['actions'])

    def test_bound_conversation_cannot_apply_other_project_snapshot(self):
        self.session.repo=self.repo/'another-project'
        with self.assertRaises(RuntimeError):
            curate.validate_existing(self.session,self.snap,self.output('Colors implemented and tests passed.'))
