"""Spec #1, ponto A: Implementar aqui pelo terminal e Herdr isolados."""
import os
import unittest
from unittest.mock import patch

import test_group_dispatch as fixtures
from watchdog_app import long_run


class ImplementHereTests(unittest.TestCase):
    setUp = fixtures.GroupDispatchTests.setUp
    open = fixtures.GroupDispatchTests.open
    wait = fixtures.GroupDispatchTests.wait
    commands = fixtures.GroupDispatchTests.commands
    dispatch = fixtures.GroupDispatchTests.dispatch

    def test_preview_and_delivery_implement_in_leader_session_for_both_controls_and_harnesses(self):
        # Spec #1 L29,43,87,138,160: wrong action/phrase or lost acceptance source fails.
        for full, kind in ((False, 'codex'), (True, 'claude'), (False, 'other')):
            with self.subTest(full=full, kind=kind):
                with patch.dict(os.environ, self.env):
                    long_run.path_for(self.repo).unlink(missing_ok=True)
                terminal = self.open(full, kind)
                os.write(terminal.master, b' h')
                self.wait(terminal, 'Modo: Implementar aqui')
                self.wait(terminal, 'Implementar nesta')
                self.wait(terminal, 'project:p4')
                before = len(self.commands())
                os.write(terminal.master, b'y')
                self.wait(terminal, 'Despacho enviado')
                sent = self.commands()[before:]
                self.assertEqual(sent[0][:3], ['pane', 'send-text', 'project:p4'])
                message = sent[0][3]
                self.assertIn('Implementar nesta sessão', message)
                self.assertIn('ponteiros de aceite', message)
                self.assertIn('worktree própria', message)
                self.assertNotIn('Despache um executor', message)
                self.assertEqual(message.startswith('/goal '), kind in ('codex', 'claude'))
                self.assertEqual(sent[1], ['pane', 'send-keys', 'project:p4', 'Enter'])
                with patch.dict(os.environ, self.env):
                    self.assertEqual(long_run.load(self.repo), ['title:A'])
                terminal.close()

    def test_cancel_preserves_selection_group_and_allows_dispatch_mode_afterwards(self):
        # Spec #1 L29,42-46,151: cancel sends nothing; either mode accumulates the same group.
        terminal = self.open()
        original = (self.repo / 'TODO.md').read_bytes()
        os.write(terminal.master, b' h')
        self.wait(terminal, 'Modo: Implementar aqui')
        os.write(terminal.master, b'\x1b')
        self.wait(terminal, 'Cancelled')
        self.assertEqual(self.commands(), [])
        with patch.dict(os.environ, self.env):
            self.assertIsNone(long_run.load(self.repo))
        self.dispatch(terminal, b'', 'Modo: Despachar')
        terminal.output = b''
        os.write(terminal.master, b'j h')
        self.wait(terminal, 'Modo: Implementar aqui')
        os.write(terminal.master, b'y')
        self.wait(terminal, 'Despacho enviado')
        with patch.dict(os.environ, self.env):
            self.assertEqual(long_run.load(self.repo), ['title:A', 'title:B'])
        self.assertEqual((self.repo / 'TODO.md').read_bytes(), original)

    def test_including_dependency_rebuilds_classification_without_changing_implement_here_mode(self):
        # Spec #1 L29,43,51,87,138,159-160: inclusion keeps the chosen execution mode.
        original = '## Next\n- [ ] B\n  Bloqueado por: A.\n- [ ] A\n'
        (self.repo / 'TODO.md').write_text(original)
        for full in (False, True):
            with self.subTest(full=full):
                with patch.dict(os.environ, self.env):
                    long_run.path_for(self.repo).unlink(missing_ok=True)
                before = len(self.commands())
                terminal = self.open(full)
                os.write(terminal.master, b' h')
                self.wait(terminal, 'Modo: Implementar aqui')
                self.wait(terminal, 'B: espera fora da seleção')
                self.wait(terminal, 'Nenhuma tarefa livre')
                terminal.output = b''
                os.write(terminal.master, b'i')
                self.wait(terminal, 'A: livre')
                self.wait(terminal, 'outra da seleção')
                self.assertNotIn(b'Despachar', terminal.output)
                self.assertEqual(len(self.commands()), before)
                with patch.dict(os.environ, self.env):
                    self.assertIsNone(long_run.load(self.repo))
                os.write(terminal.master, b'y')
                self.wait(terminal, 'Despacho enviado')
                sent = self.commands()[before:]
                self.assertEqual(len(sent), 2)
                self.assertIn('Implementar nesta sessão', sent[0][3])
                self.assertNotIn('Despache um executor', sent[0][3])
                with patch.dict(os.environ, self.env):
                    self.assertEqual(long_run.load(self.repo), ['title:B', 'title:A'])
                self.assertEqual((self.repo / 'TODO.md').read_text(), original)
                terminal.close()
