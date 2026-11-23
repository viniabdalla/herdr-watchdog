import json
import os
from pathlib import Path
import tempfile
import unittest
from watchdog_app import project_plans as pp
from watchdog_app.todo_format import render

ID='9f4cdfb9-3b30-4d69-a178-aa3ff61301a6'
class PlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.repo=Path(self.tmp.name)
        self.todo='---\nwatchdog_todo: 1\n---\n## Next\n'+render('Plain task',dict(id=ID,summary='Summary',origin='pedido-humano',execution='Details',acceptance='Checks'))
        (self.repo/'TODO.md').write_text(self.todo)
        self.task=dict(id=ID,allowed_files=['src/app.py'],acceptance=['check behavior'],tests=['echo untrusted'],dependencies=[])
        self.path=self.repo/'plan.json';self.write([self.task])
    def write(self,tasks):self.path.write_text(json.dumps(dict(format='watchdog-plan-v1',tasks=tasks)))
    def test_explicit_bounded_plan_produces_data_only_contracts(self):
        result=pp.preview(self.repo,'plan.json',format='watchdog-plan-v1')
        self.assertEqual(result['contracts'][0]['id'],ID);self.assertIn('Plain task',result['preview'])
        self.assertFalse(result['authorized']);self.assertEqual((self.repo/'TODO.md').read_text(),self.todo)
        pp.assert_current(self.repo,result)
        self.path.write_text('{}')
        with self.assertRaises(RuntimeError):pp.assert_current(self.repo,result)
    def test_unknown_duplicate_scope_escape_symlink_and_cycles_refused(self):
        for update in [dict(id='unknown'),dict(allowed_files=[]),dict(allowed_files=['../oops']),dict(allowed_files=['/tmp/oops']),dict(dependencies=[ID])]:
            self.write([{**self.task,**update}])
            with self.assertRaises(RuntimeError):pp.preview(self.repo,'plan.json',format='watchdog-plan-v1')
        self.write([self.task,self.task])
        with self.assertRaises(RuntimeError):pp.preview(self.repo,'plan.json',format='watchdog-plan-v1')
        self.path.unlink();self.path.symlink_to('/etc/passwd')
        with self.assertRaises(RuntimeError):pp.preview(self.repo,'plan.json',format='watchdog-plan-v1')
    def test_wrong_format_oversized_and_stale_todo_refused(self):
        with self.assertRaises(RuntimeError):pp.preview(self.repo,'plan.json',format='markdown')
        result=pp.preview(self.repo,'plan.json',format='watchdog-plan-v1')
        (self.repo/'TODO.md').write_text(self.todo+'\n')
        with self.assertRaises(RuntimeError):pp.assert_current(self.repo,result)
        self.path.write_bytes(b' '* (pp.LIMIT+1))
        with self.assertRaises(RuntimeError):pp.preview(self.repo,'plan.json',format='watchdog-plan-v1')

    def test_large_todo_summary_cannot_expand_output_without_bound(self):
        (self.repo/'TODO.md').write_text(self.todo.replace('    Summary','    '+('x'*(2*1024*1024))))
        with self.assertRaisesRegex(RuntimeError,'output'):
            pp.preview(self.repo,'plan.json',format='watchdog-plan-v1')
