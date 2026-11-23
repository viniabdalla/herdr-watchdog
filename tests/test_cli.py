import os
from pathlib import Path
import subprocess
import unittest

from test_artifacts_yazi import Terminal

ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def test_audit_cli_is_discoverable_and_requires_explicit_selection(self):
        help_result = subprocess.run(['python3', str(ROOT/'watchdog'), 'audit', '--help'], capture_output=True, text=True)
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn('somente leitura', help_result.stdout)
        self.assertIn('--model', help_result.stdout)
        result = subprocess.run(['python3', str(ROOT/'watchdog'), 'audit', 'open', '--confirm'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('--binding-file', result.stderr)

    def test_background_picker_preserves_explicit_session_and_layout(self):
        from watchdog_app.app import open_selector
        from types import SimpleNamespace
        api = SimpleNamespace(call=lambda *args: args)
        command = open_selector(api, ROOT, pane='pane', session='requested-session', preset=4)
        self.assertIn('WATCHDOG_SESSION=requested-session', command)
        self.assertIn('WATCHDOG_LAYOUT=4', command)
    def test_layout_list_is_available_without_a_conversation(self):
        result = subprocess.run(['python3', str(ROOT / 'watchdog'), 'layout', '--list'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Column + bottom strip', result.stdout)
        self.assertIn('Slim column + tab', result.stdout)

    def test_invalid_layout_fails_before_any_conversation_lookup(self):
        result = subprocess.run(['python3', str(ROOT / 'watchdog'), 'layout', '9'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('layout', result.stderr.lower())

    def test_panel_selector_can_choose_agents_and_cancel(self):
        for keys, expected in ((b'\r', 'CHOICE=agents'), (b'\x1b', 'CHOICE=None')):
            with self.subTest(keys=keys):
                script = ('import curses; from watchdog_app.panes import choose_panel; '
                          'print("CHOICE="+str(curses.wrapper(choose_panel)))')
                terminal = Terminal(['python3', '-c', script], dict(os.environ, TERM='xterm-256color'))
                try:
                    self.assertTrue(terminal.wait_for('Escolher painel'), terminal.output.decode(errors='replace'))
                    os.write(terminal.master, keys)
                    self.assertTrue(terminal.wait_for(expected), terminal.output.decode(errors='replace'))
                    self.assertEqual(terminal.process.wait(timeout=3), 0)
                finally:
                    terminal.close()

    def test_picker_accepts_keyboard_selection_and_cancel(self):
        for keys, expected in ((b'j\r', 'CHOICE=3'), (b'\x1b', 'CHOICE=None')):
            with self.subTest(keys=keys):
                script = ('import curses; from watchdog_app.picker import choose_layout; '
                          'print("CHOICE="+str(curses.wrapper(choose_layout,2)))')
                terminal = Terminal(['python3', '-c', script], dict(os.environ, TERM='xterm-256color'))
                try:
                    self.assertTrue(terminal.wait_for('Choose layout'), terminal.output.decode(errors='replace'))
                    os.write(terminal.master, keys)
                    self.assertTrue(terminal.wait_for(expected), terminal.output.decode(errors='replace'))
                    self.assertEqual(terminal.process.wait(timeout=3), 0)
                finally:
                    terminal.close()

    def test_project_setup_commands_require_explicit_project_and_action(self):
        for command in ('project-instructions','project-plan','artifacts'):
            result=subprocess.run(['python3','-B',str(ROOT/'watchdog'),command,'--help'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('--repo',result.stdout)
            result=subprocess.run(['python3','-B',str(ROOT/'watchdog'),command],capture_output=True,text=True)
            self.assertEqual(result.returncode,2)

    def test_instruction_cli_requires_confirmed_unchanged_displayed_preview(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            repo=Path(folder);preview=repo/'preview.json'
            env=dict(os.environ,WATCHDOG_STATE_DIR=str(repo/'state'))
            def run(*args):
                return subprocess.run(['python3','-B',str(ROOT/'watchdog'),'project-instructions',*args,
                                       '--repo',str(repo)],env=env,capture_output=True,text=True)
            result=run('preview');self.assertEqual(result.returncode,0,result.stderr)
            preview.write_text(result.stdout)
            self.assertEqual(run('apply','--preview-file',str(preview)).returncode,1)
            self.assertFalse((repo/'AGENTS.md').exists())
            result=run('apply','--preview-file',str(preview),'--confirm')
            self.assertEqual(result.returncode,0,result.stderr);self.assertIn('+++ AGENTS.md',result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'],'current')
            self.assertEqual(run('apply','--preview-file',str(preview),'--confirm').returncode,1)
            self.assertIn('Agent reading: manual-unobserved',run('check','--human').stdout)
