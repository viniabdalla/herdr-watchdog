import curses
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from watchdog_app.tasks_ui import TasksUI
from watchdog_app.todo import Snapshot
from watchdog_app.mission import RunStore
import uuid
from test_todo_format import TEXT, KEY
from test_artifacts_yazi import Terminal, SCRIPT


class Screen:
    def __init__(self, width=50):
        self.width = width
        self.lines = {}
    def getmaxyx(self): return 32, self.width
    def erase(self): self.lines.clear()
    def addnstr(self, y, x, text, n, attr): self.lines.setdefault(y, []).append(text[:n])
    def refresh(self): pass


class DisclosureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        p = patch.dict(os.environ, WATCHDOG_STATE_DIR=str(self.repo / 'state'))
        p.start(); self.addCleanup(p.stop)
        self.path = self.repo / 'TODO.md'
        self.path.write_text(TEXT)
        self.ui = TasksUI(Screen(), self.repo, None)
        self.addCleanup(self.ui.job.close)
        self.ui.refresh()

    def body(self):
        return '\n'.join(text for text, _, _ in self.ui.body())

    def test_collapsed_rows_show_title_only_without_summary_metadata_or_technical_content(self):
        body = self.body()
        self.assertIn('▸ Resolver o áudio', body)
        for hidden in ('Recuperar os áudios', 'Investigar', 'Aceite', KEY, 'pedido-humano'):
            self.assertNotIn(hidden, body)

    def test_enter_toggles_formatted_summary_and_status_without_selection_or_file_changes(self):
        before = self.path.read_bytes()
        self.ui.draw()
        self.ui.handle('enter')
        body = self.body()
        self.assertIn('▾ Resolver o áudio', body)
        self.assertIn('Resumo:', body)
        self.assertIn('Recuperar os áudios para continuar o atendimento.', body)
        self.assertIn('Situação: Pendente', body)
        self.assertNotIn('Investigar', body)
        self.assertFalse(self.ui.selected)
        self.ui.handle('enter')
        self.assertNotIn('Resumo:', self.body())
        self.assertEqual(before, self.path.read_bytes())

    def test_mouse_arrow_toggles_and_checkbox_still_selects(self):
        self.ui.draw()
        target = next(t for t in self.ui.targets if t[3] == ('toggle', KEY))
        x, y, _, _ = target
        with patch('curses.getmouse', return_value=(0, x, y, 0, curses.BUTTON1_CLICKED)):
            self.ui.handle(self.ui.mouse())
        self.assertIn('Resumo:', self.body())
        self.assertFalse(self.ui.selected)
        self.ui.draw()
        target = next(t for t in self.ui.targets if t[3] == ('item', KEY))
        x, y, _, _ = target
        with patch('curses.getmouse', return_value=(0, x, y, 0, curses.BUTTON1_CLICKED)):
            self.ui.handle(self.ui.mouse())
        self.assertEqual(self.ui.selected, {KEY})

    def test_arrow_keys_and_narrow_panel_keep_technical_instructions_for_confirmation_only(self):
        self.ui.screen.width = 28
        self.ui.draw()
        self.ui.handle('right')
        self.ui.draw()
        self.assertIn('Resumo:', self.body())
        self.ui.handle('left')
        self.assertNotIn('Resumo:', self.body())
        self.ui.handle(' ')
        self.ui.confirm('done')
        self.assertIn('Investigar a fila.', self.body())
        self.assertIn('Demonstrar recuperação', self.body())

    def test_legacy_summary_is_extracted_without_exposing_other_indented_lines(self):
        self.path.write_text('## Next\n- [ ] Tarefa antiga\n'
                             '  Resumo: Explicar o benefício.\n  Segredo técnico que fica no envio.\n')
        self.ui.refresh(); self.ui.draw(); self.ui.handle('enter')
        self.assertIn('Explicar o benefício.', self.body())
        self.assertNotIn('Segredo técnico', self.body())
        self.assertIn('Segredo técnico', self.ui.snapshot.tasks[0].text)

    def test_expansion_survives_versioned_summary_update_without_retaining_stale_selection(self):
        self.ui.draw(); self.ui.handle('enter'); self.ui.handle(' ')
        self.path.write_text(TEXT.replace('continuar o atendimento', 'recuperar o atendimento'))
        self.ui.refresh()
        self.assertIn('recuperar o atendimento', self.body())
        self.assertFalse(self.ui.selected)

    def test_live_run_guard_uses_uuid_even_after_task_text_changes(self):
        run = {'id': str(uuid.uuid4()), 'repo': str(self.repo), 'created': 1,
               'phase': 'active', 'scope': {'version': 2}, 'tasks': {KEY: {'title': 'Texto aprovado anterior'}}}
        RunStore().save(run)
        self.assertEqual(self.ui.in_live_run({KEY})['id'], run['id'])


class DisclosureTerminalTests(unittest.TestCase):
    def test_actual_terminal_enter_and_mouse_open_summary_without_selecting(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            (repo / 'TODO.md').write_text(TEXT)
            terminal = Terminal(['python3', str(SCRIPT), 'tasks', '--repo', str(repo)],
                                dict(os.environ, TERM='xterm-256color', WATCHDOG_STATE_DIR=str(repo / 'state')))
            self.addCleanup(terminal.close)
            self.assertTrue(terminal.wait_for('Space: select'))
            self.assertNotIn(b'Investigar', terminal.output)
            self.assertNotIn(b'Recuperar os', terminal.output)
            os.write(terminal.master, b'\r')
            self.assertTrue(terminal.wait_for('Resumo:'), terminal.output.decode(errors='replace'))
            self.assertNotIn(b'Investigar', terminal.output)
            terminal.output = b''
            os.write(terminal.master, b'\x1bOD')
            self.assertTrue(terminal.wait_for('▸'), terminal.output.decode(errors='replace'))
            terminal.output = b''
            os.write(terminal.master, b'\x1b[<0;5;9M\x1b[<0;5;9m')
            self.assertTrue(terminal.wait_for('Resumo:'), terminal.output.decode(errors='replace'))
            self.assertNotIn(b'1 task(s) selected', terminal.output)
            self.assertEqual((repo / 'TODO.md').read_text(), TEXT)
