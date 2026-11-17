"""Progress consumes verified session evidence and refreshes in an actual PTY."""
from dataclasses import asdict
import json
import os
from pathlib import Path
import shlex
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_actions import FakeBinding
from test_artifacts_yazi import Terminal, SCRIPT
from test_session_progress import codex_call, codex_result
from watchdog_app import bindings
from watchdog_app.progress_ui import rows
from watchdog_app.session_progress import Progress


BOOT = '''import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,sys.argv[3])
from test_actions import FakeBinding
from watchdog_app import bindings
repo=Path(sys.argv[1])
bindings.engine=lambda:SimpleNamespace(Binding=FakeBinding,verify=lambda b:{'agent_status':'idle'})
bindings.project_for=lambda b:repo
import runpy
script=Path(sys.argv[3]).parent/'tools/watchdog-preview.py'
sys.argv=[str(script),'progress','--repo',str(repo),'--binding-file',sys.argv[2]]
runpy.run_path(str(script),run_name='__main__')
'''


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.repo=Path(self.temp.name)
        (self.repo/'TODO.md').write_text('## Next\n- [ ] Project task\n## Done\n- [x] Old task\n')
        self.history=self.repo/'native.jsonl';self.history.touch()
        self.binding=FakeBinding(history=str(self.history))
        self.file=self.repo/'binding.json'
        self.file.write_text(json.dumps({'repo':str(self.repo),'binding':asdict(self.binding)}))
        self.live=True;self.project=self.repo
        def verify(b):
            if not self.live:raise RuntimeError('gone')
            return {'agent_status':'idle'}
        runtime=SimpleNamespace(Binding=FakeBinding,verify=verify)
        self.addCleanup(patch.stopall)
        patch.object(bindings,'engine',return_value=runtime).start()
        patch.object(bindings,'project_for',side_effect=lambda b:self.project).start()
        self.progress=Progress(self.repo,self.file)

    def append(self,*records):
        with self.history.open('a') as f:
            for r in records:f.write(json.dumps(r)+'\n')

    def test_unbound_empty_and_missing_are_distinct_without_fake_percent(self):
        self.assertEqual(Progress(self.repo).poll().state,'unavailable')
        self.assertEqual(self.progress.poll().state,'no_checklist')
        self.history.unlink();view=self.progress.poll()
        self.assertEqual(view.state,'unavailable');self.assertIsNone(view.total)
        source=rows(self.repo,SimpleNamespace(list=lambda repo:[]),progress=self.progress)
        text='\n'.join(s[0] for s in source)
        self.assertIn('1/2 tasks complete',text)
        self.assertNotIn('0/0',text)

    def test_identity_and_project_gates_hide_previously_valid_plan(self):
        self.append(codex_call(),codex_result());self.assertEqual(self.progress.poll().total,2)
        self.live=False;self.assertEqual(self.progress.poll().state,'unavailable')
        self.live=True;self.project=self.repo/'another'
        self.assertEqual(self.progress.poll().state,'unavailable')
        self.project=self.repo
        data=json.loads(self.file.read_text());data['repo']=str(self.repo/'other');self.file.write_text(json.dumps(data))
        self.assertEqual(self.progress.poll().state,'unavailable')

    def test_source_replacement_and_partial_data_hide_stale_plan(self):
        self.append(codex_call(),codex_result());self.assertEqual(self.progress.poll().total,2)
        with self.history.open('a') as f:f.write('{"type":')
        view=self.progress.poll();self.assertEqual(view.state,'catching_up');self.assertIsNone(view.total)
        self.history.write_text('{}\n')
        self.assertEqual(self.progress.poll().state,'no_checklist')

    def test_pty_refreshes_native_plan_and_new_turn_preserves_project_counts(self):
        terminal=Terminal(['python3','-B','-c',BOOT,str(self.repo),str(self.file),str(SCRIPT.parents[1]/'tests')],
            dict(os.environ,TERM='xterm-256color',WATCHDOG_STATE_DIR=str(self.repo/'state')))
        self.addCleanup(terminal.close)
        self.assertTrue(terminal.wait_for('No checklist'),terminal.output.decode(errors='replace'))
        self.append(codex_call(),codex_result())
        self.assertTrue(terminal.wait_for('Inspect fixtures'),terminal.output.decode(errors='replace'))
        self.assertTrue(terminal.wait_for('0/2'),terminal.output.decode(errors='replace'))
        self.assertIn(b'93m',terminal.output)
        self.append({'type':'event_msg','payload':{'type':'task_started','turn_id':'new-turn'}})
        terminal.output=b''
        self.assertTrue(terminal.wait_for('No checklist'),terminal.output.decode(errors='replace'))
        os.write(terminal.master,b'q');self.assertEqual(terminal.process.wait(timeout=3),0)
        self.assertEqual((self.repo/'TODO.md').read_text(),'## Next\n- [ ] Project task\n## Done\n- [x] Old task\n')

    def test_launcher_passes_explicit_binding_to_progress(self):
        from watchdog_app.app import ensure_panels
        commands={};started=set()
        def call(*args):
            if args[:2]==('pane','rename'):return {}
            if args[:2]==('pane','run'):
                commands[args[2]]=shlex.split(args[3]);started.add(args[2]);return {}
            raise AssertionError(args)
        state={'binding':{'workspace':'w'},'binding_file':str(self.file),'repo':str(self.repo),
            'yazi_client_id':'123','panes':{r:{'pane_id':r} for r in ('tasks','progress','artifacts','files')}}
        api=SimpleNamespace(call=call,checked=lambda pane:pane)
        with patch('watchdog_app.app.panel_process',side_effect=lambda api,pane,role,state:(role in started,[])):
            ensure_panels(api,state,lambda:None)
        argv=commands['progress']
        self.assertEqual(argv[argv.index('--binding-file')+1],str(self.file))

    def test_discarded_rows_hide_previous_plan_until_fresh_native_success(self):
        self.append(codex_call(),codex_result());self.assertEqual(self.progress.poll().total,2)
        with self.history.open('a') as f:f.write('{bad row}\n')
        view=self.progress.poll()
        self.assertEqual(view.state,'unsupported');self.assertIsNone(view.total)
        self.append(codex_call('fresh'),codex_result('fresh'))
        self.assertEqual(self.progress.poll().total,2)

    def test_replay_after_invalid_gap_cannot_revive_known_previous_plan(self):
        self.append(codex_call(),codex_result());self.assertEqual(self.progress.poll().total,2)
        with self.history.open('a') as f:f.write('broken\n')
        self.append(codex_call(),codex_result())
        self.assertIsNone(self.progress.poll().total)
