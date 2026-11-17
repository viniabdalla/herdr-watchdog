from types import SimpleNamespace
import unittest

from watchdog_app.bindings import ChoiceRequired, select


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.old = SimpleNamespace(pane='old:p1', session='old-session')
        self.current = SimpleNamespace(pane='project:p4', session='current-thread')

    def test_thread_identity_ignores_stale_inherited_pane(self):
        self.assertIs(select([self.old, self.current], thread='current-thread'), self.current)

    def test_explicit_pane_and_session_must_both_match(self):
        with self.assertRaises(RuntimeError):
            select([self.old, self.current], pane='old:p1', session='current-thread')

    def test_missing_current_thread_never_selects_another_conversation(self):
        with self.assertRaises(RuntimeError):
            select([self.old], thread='current-thread')

    def test_multiple_conversations_require_a_choice(self):
        with self.assertRaises(ChoiceRequired) as caught:
            select([self.old, self.current])
        self.assertEqual(caught.exception.choices, [self.old, self.current])

    def test_no_candidate_is_an_actionable_error(self):
        with self.assertRaisesRegex(RuntimeError, 'native'):
            select([])


if __name__ == '__main__':
    unittest.main()
