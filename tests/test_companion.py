from dataclasses import asdict
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from watchdog_app import bindings
from watchdog_app.app import reconcile_companion


class CompanionTests(unittest.TestCase):
    def test_idle_shell_is_not_adopted_as_working_left_undone(self):
        binding = SimpleNamespace(key='key', kind='codex', session='session',
                                  account='account', pane='conversation', terminal='convo-terminal',
                                  pid=123, started='456')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = {k: v for k, v in vars(binding).items() if k != 'key'}
            (root / 'key.binding.json').write_text(json.dumps(data))
            (root / 'key.pane.json').write_text(json.dumps({'pane': 'lu', 'terminal': 'terminal'}))
            api = SimpleNamespace(call=lambda *a: {'pane': {'pane_id': 'lu', 'terminal_id': 'terminal'}})
            with patch.object(bindings, 'lu_state', return_value=root), \
                    patch.object(bindings, 'native_companion_alive', return_value=False):
                self.assertIsNone(bindings.companion(binding, api))

    def test_companion_replacement_and_removal_drop_the_old_ownership(self):
        for replacement in ({'pane_id': 'new', 'terminal_id': 'new-terminal'}, None):
            with self.subTest(replacement=replacement):
                state = {'panes': {'left_undone': {'pane_id': 'closed-old-pane'}}}
                with patch.object(bindings, 'companion', return_value=replacement):
                    reconcile_companion(None, None, state)
                self.assertEqual(state['panes'], {'left_undone': replacement} if replacement else {})
