"""Painel de acompanhamento, despacho confirmado e verificação pelo líder."""
from dataclasses import asdict
import json
import os
from pathlib import Path
import tempfile
import subprocess
import time
import unittest

from test_artifacts_yazi import Terminal, SCRIPT
from test_actions import FakeBinding
from test_tasks_ui import BOUND_SCRIPT
from watchdog_app.tasks_ui import verification_prompt
from watchdog_app.todo import Snapshot

ROOT = SCRIPT.parents[1]
FAKE_HERDR = '''#!/usr/bin/env python3
import json, os, sys
with open(os.environ['HERDR_LOG'], 'a') as f:
    f.write(json.dumps(sys.argv[1:]) + '\\n')
'''


class TasksMonitorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.original = ('## In progress\n\n## Next\n- [ ] T2 — Worker de áudio\n  Resumo: Assume a fila.\n'
                         '- [ ] T3 — Número desconhecido\n## Done\n- [x] Old completion\n')
        (self.repo / 'TODO.md').write_text(self.original)
        bin_dir = self.repo / 'bin'; bin_dir.mkdir()
        (bin_dir / 'herdr').write_text(FAKE_HERDR); (bin_dir / 'herdr').chmod(0o755)
        self.log = self.repo / 'herdr.log'
        self.env = {k: v for k, v in os.environ.items() if k != 'WATCHDOG_FULL_CONTROLS'}
        self.env.update(TERM='xterm-256color', WATCHDOG_STATE_DIR=str(self.repo / 'state'),
                        PATH=str(bin_dir) + os.pathsep + os.environ['PATH'], HERDR_LOG=str(self.log),
                        HERDR_BIN_PATH=str(bin_dir / 'herdr'), XDG_STATE_HOME=str(self.repo/'xdg'))

    def unbound(self):
        terminal = Terminal(['python3', str(SCRIPT), 'tasks', '--repo', str(self.repo)], self.env)
        self.addCleanup(terminal.close)
        return terminal

    def bound(self):
        history = self.repo / 'record.jsonl'; history.write_text('')
        binding = self.repo / 'binding.json'
        binding.write_text(json.dumps({'repo': str(self.repo), 'binding': asdict(FakeBinding(history=str(history)))}))
        terminal = Terminal(['python3', '-c', BOUND_SCRIPT, str(self.repo), str(binding), str(ROOT / 'tests')], self.env)
        self.addCleanup(terminal.close)
        return terminal

    def test_monitor_buttons_are_shown(self):
        # Spec #1 L29,129: despacho disponível; gravação manual removida.
        # Spec #1 L127-128,168: nomes distintos de curador/líder nos dois modos.
        terminal = self.unbound()
        self.assertTrue(terminal.wait_for('Verify Leader v'), terminal.output.decode(errors='replace'))
        self.assertTrue(terminal.wait_for('v: Verify Leader'), terminal.output.decode(errors='replace'))
        screen = terminal.output.decode(errors='replace')
        self.assertIn('Review Curator r', screen)
        self.assertIn('r: Review Curator', screen)
        self.assertIn('v: Verify Leader', screen)
        self.assertIn('Despachar p', screen)
        self.assertNotIn('Acompanhar no Progress g', screen)
        self.assertIn('Quit q', screen)
        for gone in ('Agents m', 'Send s', 'Done d', 'Start i', 'Next n', 'Orchestrate o',
                     'Clean sessions c', 'Auditoria A'):
            self.assertNotIn(gone, screen)

    def test_full_controls_keeps_named_curator_and_leader_actions(self):
        # Spec #1, lines 127–128 and 168; T2 acceptance: both control modes.
        self.env['WATCHDOG_FULL_CONTROLS'] = '1'
        terminal = self.bound()
        self.assertTrue(terminal.wait_for('Verify Leader v'), terminal.output.decode(errors='replace'))
        self.assertTrue(terminal.wait_for('v: Verify Leader'), terminal.output.decode(errors='replace'))
        screen = terminal.output.decode(errors='replace')
        self.assertIn('Review Curator r', screen)
        self.assertIn('r: Review Curator', screen)
        self.assertIn('v: Verify Leader', screen)
        os.write(terminal.master, b' v')
        self.assertTrue(terminal.wait_for('Verify Leader · pedir verificação ao líder'),
                        terminal.output.decode(errors='replace'))
        self.assertFalse(self.log.exists())
        self.assertEqual((self.repo / 'TODO.md').read_text(), self.original)

    def test_disabled_keys_do_nothing_and_selection_still_works(self):
        terminal = self.unbound()
        self.assertTrue(terminal.wait_for('Verify Leader v'))
        os.write(terminal.master, b' ')
        self.assertTrue(terminal.wait_for('1 task(s) selected'), terminal.output.decode(errors='replace'))
        os.write(terminal.master, b'dsinomcDPA0C')
        time.sleep(1)
        screen = terminal.output.decode(errors='replace')
        for absent in ('Confirm completion', 'Confirm send', 'Moved selected', 'No conversation binding', 'Agents aberto'):
            self.assertNotIn(absent, screen)
        self.assertEqual((self.repo / 'TODO.md').read_text(), self.original)

    def test_dispatched_selection_is_reopened_in_progress(self):
        # Spec #1 L44,153-154: grupo confirmado no Tasks aparece no Progress real.
        for args in (('init', '-q', '-b', 'integration'), ('add', 'TODO.md'),
                     ('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'base')):
            subprocess.run(['git', '-C', str(self.repo), *args], check=True, capture_output=True)
        terminal = self.bound()
        self.assertTrue(terminal.wait_for('Despachar p'))
        os.write(terminal.master, b' j p')
        self.assertTrue(terminal.wait_for('Confirmar despacho'), terminal.output.decode(errors='replace'))
        os.write(terminal.master, b'y')
        self.assertTrue(terminal.wait_for('Despacho enviado'), terminal.output.decode(errors='replace'))
        progress = Terminal(['python3', str(SCRIPT), 'progress', '--repo', str(self.repo),
                             '--binding-file', str(self.repo / 'offline-session.json')], self.env)
        self.addCleanup(progress.close)
        self.assertTrue(progress.wait_for('0 de 2 concluídas · 0%'), progress.output.decode(errors='replace'))
        self.assertEqual((self.repo / 'TODO.md').read_text(), self.original)

    def test_verify_requires_selection(self):
        terminal = self.bound()
        self.assertTrue(terminal.wait_for('Verify Leader v'))
        os.write(terminal.master, b'v')
        self.assertTrue(terminal.wait_for('Selection is empty'), terminal.output.decode(errors='replace'))
        self.assertFalse(self.log.exists())

    def test_verify_previews_then_types_prompt_into_main_session_pane(self):
        # Spec #1, lines 128 and 168: Verify Leader preview, with fake Herdr.
        terminal = self.bound()
        self.assertTrue(terminal.wait_for('Verify Leader v'))
        os.write(terminal.master, b' v')
        self.assertTrue(terminal.wait_for('Verify Leader · pedir verificação ao líder'), terminal.output.decode(errors='replace'))
        self.assertTrue(terminal.wait_for('project:p4'))
        self.assertFalse(self.log.exists(), 'nothing is sent before confirmation')
        os.write(terminal.master, b'y')
        self.assertTrue(terminal.wait_for('Pedido de verificação enviado'), terminal.output.decode(errors='replace'))
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertEqual(calls[0][:3], ['pane', 'send-text', 'project:p4'])
        self.assertIn('T2 — Worker de áudio', calls[0][3])
        self.assertEqual(calls[1], ['pane', 'send-keys', 'project:p4', 'enter'])
        self.assertEqual((self.repo / 'TODO.md').read_text(), self.original)

    def test_verify_cancel_sends_nothing(self):
        terminal = self.bound()
        self.assertTrue(terminal.wait_for('Verify Leader v'))
        os.write(terminal.master, b' v')
        self.assertTrue(terminal.wait_for('Verify Leader · pedir verificação ao líder'))
        os.write(terminal.master, b'\x1b')
        self.assertTrue(terminal.wait_for('Cancelled'))
        self.assertFalse(self.log.exists())

    def test_prompt_is_a_single_line_listing_titles(self):
        tasks = Snapshot.parse(self.repo, self.original.encode()).tasks
        prompt = verification_prompt([t for t in tasks if not t.done])
        self.assertNotIn('\n', prompt)
        self.assertIn('T2 — Worker de áudio; T3 — Número desconhecido', prompt)
        self.assertIn('pronta (com evidência) ou não pronta', prompt)


if __name__ == '__main__':
    unittest.main()
