from dataclasses import dataclass
import json
from pathlib import Path
import tempfile
import unittest

from watchdog_app.store import Store


@dataclass
class Binding:
    pane: str = 'project:p4'
    terminal: str = 'conversation-terminal'
    session: str = 'verified-session'
    kind: str = 'codex'
    account: str = '/example/account'
    key: str = 'test-key'


class StoreTests(unittest.TestCase):
    def test_only_matching_preview_is_adopted(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            preview = {'repo': str(root), 'panes': {'tasks': {'pane_id': 'tasks'}},
                       'conversation': {'pane_id': 'wrong-pane', 'terminal_id': 'conversation-terminal'},
                       'yazi_client_id': '1234'}
            (root / 'preview.json').write_text(json.dumps(preview))
            store = Store(root)
            self.assertEqual(store.load(Binding(), root)['panes'], {})
            preview['conversation']['pane_id'] = 'project:p4'
            (root / 'preview.json').write_text(json.dumps(preview))
            state = store.load(Binding(), root)
            self.assertEqual(state['panes']['tasks']['pane_id'], 'tasks')
            self.assertEqual(state['yazi_client_id'], '1234')

    def test_successful_layout_preference_survives_new_session(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder))
            self.assertEqual(store.preference(), 2)
            store.remember(4)
            self.assertEqual(Store(Path(folder)).preference(), 4)

    def test_state_from_another_project_is_not_reused(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder))
            binding = Binding()
            state = store.load(binding, Path(folder))
            store.save(binding, state)
            with self.assertRaisesRegex(RuntimeError, 'project'):
                store.load(binding, Path('/another/project'))
