"""Spec #1, ponto A: terminal real, TODO/estado/Herdr isolados."""
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import shutil
import tempfile
import unittest
from unittest.mock import patch

from test_actions import FakeBinding
from test_artifacts_yazi import Terminal, SCRIPT
from test_tasks_ui import BOUND_SCRIPT, ROOT
from watchdog_app import long_run
from watchdog_app.progress_ui import rows


class GroupDispatchTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.repo = Path(folder.name)
        def git(*args):
            return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True).strip()
        self.git = git
        git('init', '-q', '-b', 'integration')
        git('config', 'user.name', 'Fixture')
        git('config', 'user.email', 'fixture@example.invalid')
        (self.repo / 'TODO.md').write_text('## Next\n' + ''.join(f'- [ ] {x}\n' for x in 'ABCDEF'))
        (self.repo / 'AGENTS.md').write_text('## Dispatch\nBranch de integração: `integration`\n')
        git('add', 'TODO.md', 'AGENTS.md')
        git('commit', '-qm', 'base')
        self.base = git('rev-parse', 'HEAD')
        git('checkout', '-qb', 'executor')
        git('commit', '--allow-empty', '-qm', 'executor only')
        binding = self.repo / 'binding.json'
        binding.write_text(json.dumps({'repo': str(self.repo), 'binding': asdict(FakeBinding())}))
        herdr = self.repo / 'herdr-fake'
        herdr.write_text('#!/usr/bin/env python3\nimport json,sys\nfrom pathlib import Path\n'
                         'with (Path(__file__).parent/"commands.jsonl").open("a") as f: f.write(json.dumps(sys.argv[1:])+"\\n")\n'
                         'print(json.dumps({"result":{}}))\n')
        herdr.chmod(0o755)
        self.env = dict(os.environ, TERM='xterm-256color', WATCHDOG_STATE_DIR=str(self.repo/'state'),
                        HERDR_BIN_PATH=str(herdr))
        self.env.pop('WATCHDOG_FULL_CONTROLS', None)
        self.binding = binding

    def open(self, full=False, kind='codex'):
        value = json.loads(self.binding.read_text())
        value['binding']['kind'] = kind
        self.binding.write_text(json.dumps(value))
        env = dict(self.env)
        if full:
            env['WATCHDOG_FULL_CONTROLS'] = '1'
        terminal = Terminal(['python3', '-B', '-c', BOUND_SCRIPT, str(self.repo),
                             str(self.binding), str(ROOT/'tests')], env)
        self.addCleanup(terminal.close)
        self.assertTrue(terminal.wait_for('Despachar p'), terminal.output.decode(errors='replace'))
        return terminal

    def wait(self, terminal, text):
        self.assertTrue(terminal.wait_for(text), terminal.output.decode(errors='replace'))

    def commands(self):
        file = self.repo / 'commands.jsonl'
        return [json.loads(line) for line in file.read_text().splitlines()] if file.exists() else []

    def dispatch(self, terminal, selection, expected=None):
        terminal.output = b''
        os.write(terminal.master, selection + b'p')
        self.wait(terminal, 'Confirmar despacho')
        self.wait(terminal, 'project:p4')
        if expected:
            self.wait(terminal, expected)
        before = len(self.commands())
        os.write(terminal.master, b'y')
        self.wait(terminal, 'Despacho enviado')
        commands = self.commands()[before:]
        self.assertEqual(commands[0][:3], ['pane', 'send-text', 'project:p4'])
        self.assertEqual(commands[1], ['pane', 'send-keys', 'project:p4', 'Enter'])
        return commands[0][3]

    def test_first_dispatch_preview_cancel_then_delivery_group_and_integration_base(self):
        # Spec #1 L29,49,65-66,139,153-154: no effects before confirmation.
        for full, kind in ((False, 'codex'), (True, 'claude'), (False, 'other')):
            with self.subTest(full=full, kind=kind):
                state = self.repo/'state'
                shutil.rmtree(state, ignore_errors=True)
                terminal = self.open(full, kind)
                before = self.commands()
                os.write(terminal.master, b' j j p')
                self.wait(terminal, 'Confirmar despacho')
                self.wait(terminal, 'docs/dispatch.md')
                self.wait(terminal, 'AGENTS.md')
                os.write(terminal.master, b'\x1b')
                self.wait(terminal, 'Cancelled')
                self.assertEqual(self.commands(), before)
                with patch.dict(os.environ, self.env):
                    self.assertIsNone(long_run.load(self.repo))
                message = self.dispatch(terminal, b'', 'Concluir')
                self.assertIn('## Dispatch', message)
                self.assertIn('somente', message)
                self.assertEqual(message.startswith('/goal '), kind in ('codex', 'claude'))
                with patch.dict(os.environ, self.env):
                    self.assertEqual(len(long_run.load(self.repo)), 3)
                    self.assertIn('0 de 3', '\n'.join(text for text, _, _ in rows(self.repo)))
                    metadata = json.loads(long_run.path_for(self.repo).read_text())
                self.assertEqual(metadata['base'], self.base)
                self.assertEqual(metadata['integration_branch'], 'integration')
                # Spec #1 L50,53-54: updates use the same ordinary delivery for every harness.
                self.assertEqual(self.dispatch(terminal, b'jjj ', 'Grupo atualizado'),
                                 'Grupo atualizado: +D')
                terminal.close()

    def test_dispatch_adds_and_deduplicates_preserving_base(self):
        # Spec #1 L44-46,139,155-156: open group accumulates; base is immutable.
        terminal = self.open()
        self.dispatch(terminal, b' j j ', 'Concluir')
        with patch.dict(os.environ, self.env):
            file = long_run.path_for(self.repo)
            state = json.loads(file.read_text())
            state['future_ticket'] = {'keep': True}
            file.write_text(json.dumps(state))
        self.git('update-ref', 'refs/heads/integration', self.git('rev-parse', 'HEAD'))
        self.assertEqual(self.dispatch(terminal, b'jjj j j ', 'Grupo atualizado'),
                         'Grupo atualizado: +D, +E, +F')
        self.dispatch(terminal, b' ')
        with patch.dict(os.environ, self.env):
            self.assertEqual(len(long_run.load(self.repo)), 6)
            self.assertIn('0 de 6', '\n'.join(text for text, _, _ in rows(self.repo)))
            self.assertEqual(json.loads(long_run.path_for(self.repo).read_text())['base'], self.base)
            self.assertEqual(long_run.record(self.repo)['future_ticket'], {'keep': True})

    def test_manual_group_action_is_gone(self):
        # Spec #1 L129,168: g no longer writes a group, in either controls mode.
        for full in (False, True):
            terminal = self.open(full)
            os.write(terminal.master, b' g')
            self.wait(terminal, '1 task(s) selected')
            self.assertNotIn(b'Acompanhar no Progress g', terminal.output)
            with patch.dict(os.environ, self.env):
                self.assertIsNone(long_run.load(self.repo))
            terminal.close()

    def test_legacy_list_group_remains_readable_and_dispatch_preserves_its_members(self):
        # Spec #1 L44-46,151: existing group persists across dispatch and format upgrade.
        legacy = ['title:A', 'title:B']
        with patch.dict(os.environ, self.env):
            file = long_run.path_for(self.repo)
            file.parent.mkdir(parents=True)
            file.write_text(json.dumps(legacy))
            self.assertEqual(long_run.load(self.repo), legacy)
        terminal = self.open()
        self.dispatch(terminal, b'jj ')
        with patch.dict(os.environ, self.env):
            self.assertEqual(long_run.load(self.repo), ['title:A', 'title:B', 'title:C'])
            self.assertIn('0 de 3', '\n'.join(text for text, _, _ in rows(self.repo)))

    def test_completed_group_waits_for_dispatch_then_starts_new_base(self):
        # Spec #1 L47,139,157: keep 3/3 until the next confirmed dispatch.
        terminal = self.open()
        self.dispatch(terminal, b' j j ')
        terminal.close()
        todo = self.repo / 'TODO.md'
        todo.write_text(todo.read_text().replace('[ ] A', '[x] A').replace('[ ] B', '[x] B').replace('[ ] C', '[x] C'))
        self.git('update-ref', 'refs/heads/integration', self.git('rev-parse', 'HEAD'))
        with patch.dict(os.environ, self.env):
            self.assertIn('3 de 3', '\n'.join(text for text, _, _ in rows(self.repo)))
        terminal = self.open()
        self.dispatch(terminal, b'jjj ', 'Concluir')
        with patch.dict(os.environ, self.env):
            self.assertEqual(long_run.load(self.repo), ['title:D'])
            self.assertEqual(long_run.record(self.repo)['base'], self.git('rev-parse', 'integration'))

    def test_new_session_reissues_goal_for_saved_open_group(self):
        # Spec #1 L123,138: a saved group does not imply a goal in a new session.
        terminal = self.open()
        self.dispatch(terminal, b' ')
        terminal.close()
        value = json.loads(self.binding.read_text())
        value['binding']['session'] = 'after-clear'
        self.binding.write_text(json.dumps(value))
        terminal = self.open()
        self.assertTrue(self.dispatch(terminal, b'j ', 'Concluir').startswith('/goal '))
        self.assertEqual(self.dispatch(terminal, b'jj ', 'Grupo atualizado'), 'Grupo atualizado: +C')
        with patch.dict(os.environ, self.env):
            self.assertEqual(long_run.load(self.repo), ['title:A', 'title:B', 'title:C'])

    def test_progress_reset_empties_group_and_next_preview_is_goal(self):
        # Spec #1 L48,158: Progress reset also invalidates the goal and base.
        terminal = self.open()
        self.dispatch(terminal, b' j j ')
        progress = Terminal(['python3', str(SCRIPT), 'progress', '--repo', str(self.repo)], self.env)
        self.addCleanup(progress.close)
        self.wait(progress, '0 de 3')
        self.wait(progress, 'z: zerar grupo')
        os.write(progress.master, b'z')
        self.wait(progress, 'Grupo zerado')
        with patch.dict(os.environ, self.env):
            self.assertFalse(long_run.load(self.repo))
        self.assertTrue(self.dispatch(terminal, b' ', 'Concluir').startswith('/goal '))
        with patch.dict(os.environ, self.env):
            self.assertEqual(long_run.load(self.repo), ['title:A'])
