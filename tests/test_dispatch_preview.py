"""Spec #1 L76,86,159,161: dependency decisions at the real terminal boundary."""
import os
import unittest
from unittest.mock import patch

import test_group_dispatch as group_tests
from watchdog_app import long_run


class PreviewTests(unittest.TestCase):
    setUp = group_tests.GroupDispatchTests.setUp
    open = group_tests.GroupDispatchTests.open
    wait = group_tests.GroupDispatchTests.wait
    commands = group_tests.GroupDispatchTests.commands

    def todo(self, text):
        (self.repo / 'TODO.md').write_text(text)
        self.original = text

    def test_classifies_selection_and_completed_dependency_is_free(self):
        # Spec #1 L76,159: current TODO state, including Feito, controls eligibility.
        self.todo('## Next\n- [ ] A\n- [ ] B\n  Bloqueado por: A.\n'
                  '- [ ] C\n  Bloqueado por: D.\n- [ ] E\n  Bloqueado por: Vini.\n'
                  '- [ ] F\n  Bloqueado por: G.\n- [ ] D\n## Done\n- [x] G\n')
        terminal = self.open()
        os.write(terminal.master, b' j j j j p')
        for label in ('A: livre', 'B: espera outra da seleção', 'C: espera fora da seleção',
                      'E: depende do Vini', 'F: livre'):
            self.wait(terminal, label)
        self.assertFalse(self.commands())
        self.assertEqual((self.repo/'TODO.md').read_text(), self.original)

    def test_no_free_task_requires_explicit_override_or_cancel(self):
        # Spec #1 L76,159: ordinary confirmation cannot bypass the blocked selection.
        self.todo('## Next\n- [ ] B\n  Bloqueado por: A.\n- [ ] A\n')
        terminal = self.open()
        os.write(terminal.master, b' p')
        self.wait(terminal, 'Nenhuma tarefa livre')
        os.write(terminal.master, b'y\r')
        self.wait(terminal, 'Mandar assim mesmo')
        self.assertFalse(self.commands())
        with patch.dict(os.environ, self.env):
            self.assertIsNone(long_run.load(self.repo))
        os.write(terminal.master, b'\x1b')
        self.wait(terminal, 'Cancelled')
        self.assertFalse(self.commands())
        os.write(terminal.master, b'p!')
        self.wait(terminal, 'Despacho enviado')
        self.assertEqual(len(self.commands()), 2)

    def test_include_dependency_returns_to_preview_before_confirmation(self):
        # Spec #1 L76,151,159: inclusion only expands selection, never sends implicitly.
        self.todo('## Next\n- [ ] B\n  Bloqueado por: A.\n- [ ] A\n')
        terminal = self.open()
        os.write(terminal.master, b' pi')
        self.wait(terminal, 'A: livre')
        self.wait(terminal, 'outra da seleção')
        self.assertFalse(self.commands())
        os.write(terminal.master, b'y')
        self.wait(terminal, 'Despacho enviado')
        with patch.dict(os.environ, self.env):
            self.assertEqual(len(long_run.load(self.repo)), 2)
        self.assertEqual((self.repo/'TODO.md').read_text(), self.original)

    def test_missing_project_instructions_warn_without_preventing_delivery(self):
        # Spec #1 L86,161: missing Dispatch/import are warnings, not a gate.
        (self.repo/'AGENTS.md').write_text('# Project\n')
        terminal = self.open()
        os.write(terminal.master, b' p')
        self.wait(terminal, 'sem seção Dispatch')
        self.wait(terminal, 'sem import do AGENTS.md')
        os.write(terminal.master, b'y')
        self.wait(terminal, 'Despacho enviado')
        self.assertEqual(len(self.commands()), 2)

    def test_current_uuid_and_ticket_identity_free_only_completed_dependencies(self):
        # Spec #1 L76,151,159: stable IDs survive renames, T1 must not match T10.
        from watchdog_app.todo_format import render
        ids = [f'00000000-0000-4000-8000-{n:012d}' for n in range(1, 5)]
        def task(index, title, execution='Trabalhar', done=False):
            return render(title, dict(id=ids[index], summary=title, execution=execution,
                                      acceptance='Verificar', origin='pedido-humano'), done=done)
        self.todo('---\nwatchdog_todo: 1\n---\n## Próximo\n' +
                  task(0, 'T2 (#3) Consumidor', 'Bloqueado por: ' + ids[2] + ', T1 (#2).') +
                  task(1, 'T10 (#11) Outro ticket') +
                  '## Feito\n' + task(2, 'Dependência renomeada', done=True) +
                  task(3, 'T1 (#2) Concluído', done=True))
        (self.repo/'CLAUDE.md').write_text('@AGENTS.md\n')
        terminal = self.open()
        os.write(terminal.master, b' p')
        self.wait(terminal, 'T2 (#3) Consumidor: livre')
        os.write(terminal.master, b'y')
        self.wait(terminal, 'Despacho enviado')
        with patch.dict(os.environ, self.env):
            self.assertEqual(long_run.load(self.repo), ['id:' + ids[0]])

    def test_cyclic_selection_needs_override_and_stale_todo_cannot_be_sent(self):
        # Spec #1 L76,151,159: selected dependencies are not free; stale offers cannot send.
        self.todo('## Next\n- [ ] A\n  Bloqueado por: B.\n- [ ] B\n  Bloqueado por: A.\n')
        terminal = self.open()
        os.write(terminal.master, b' j p')
        self.wait(terminal, 'Nenhuma tarefa livre')
        os.write(terminal.master, b'y\r')
        self.wait(terminal, 'Mandar assim mesmo')
        self.assertFalse(self.commands())
        (self.repo/'TODO.md').write_text(self.original.replace('A.', 'Vini.'))
        self.wait(terminal, 'confirmation cancelled')
        os.write(terminal.master, b'!')
        self.assertFalse(self.commands())
        with patch.dict(os.environ, self.env):
            self.assertIsNone(long_run.load(self.repo))
