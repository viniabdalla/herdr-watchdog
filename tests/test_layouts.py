import os
from pathlib import Path
import tempfile
import time
import unittest

from watchdog_app.herdr import Herdr
from watchdog_app.layouts import arrange
from watchdog_app.app import ensure_panels


@unittest.skipUnless(os.environ.get('WATCHDOG_HERDR_TEST') == '1',
                     'set WATCHDOG_HERDR_TEST=1 to use the isolated wd-test server')
class LayoutTests(unittest.TestCase):
    def setUp(self):
        self.api = Herdr(session='wd-test')
        created = self.api.call('workspace', 'create', '--cwd', '/tmp',
                                '--label', 'Watchdog layout test', '--no-focus')
        self.workspace = created['workspace']['workspace_id']
        self.conversation = created['root_pane']
        self.other = self.api.call('pane', 'split', self.conversation['pane_id'],
                                   '--direction', 'right', '--no-focus')['pane']
        self.panes = {}
        for name in ('tasks', 'progress', 'artifacts', 'files', 'left_undone'):
            self.panes[name] = self.api.call('pane', 'split', self.other['pane_id'],
                                              '--direction', 'down', '--no-focus')['pane']

    def tearDown(self):
        self.api.call('workspace', 'close', self.workspace)

    def test_four_presets_preserve_terminals_and_unrelated_pane(self):
        before = self.api.call('pane', 'list', '--workspace', self.workspace)['panes']
        terminals = {p['terminal_id'] for p in before}
        for preset in (2, 1, 3, 4, 2):
            with self.subTest(preset=preset):
                arrange(self.api, self.conversation, self.panes, preset)
                after = self.api.call('pane', 'list', '--workspace', self.workspace)['panes']
                self.assertEqual({p['terminal_id'] for p in after}, terminals)
                other = self.api.checked(self.other)
                self.assertEqual(other['tab_id'], self.other['tab_id'])
                convo = self.api.checked(self.conversation)
                files = self.api.checked(self.panes['files'])
                lu = self.api.checked(self.panes['left_undone'])
                self.assertEqual(files['tab_id'], lu['tab_id'])
                tree = self.api.export(convo['tab_id'])['root']
                if preset == 2:
                    self.assertEqual(tree['direction'], 'down')
                    self.assertEqual(tree['first']['first']['pane_id'], convo['pane_id'])
                    self.assertEqual(tree['first']['second']['first']['pane_id'], self.panes['tasks']['pane_id'])
                    self.assertEqual(tree['second']['first']['pane_id'], self.panes['artifacts']['pane_id'])
                    self.assertEqual(tree['second']['second']['first']['pane_id'], files['pane_id'])
                    self.assertEqual(tree['second']['second']['second']['pane_id'], lu['pane_id'])
                elif preset == 1:
                    self.assertEqual(tree['direction'], 'right')
                    self.assertEqual(tree['first']['pane_id'], convo['pane_id'])
                elif preset == 3:
                    self.assertEqual(tree['type'], 'pane')
                    dashboard = self.api.export(files['tab_id'])['root']
                    self.assertEqual(dashboard['direction'], 'right')
                    self.assertEqual(dashboard['first']['first']['pane_id'], self.panes['tasks']['pane_id'])
                else:
                    self.assertEqual(tree['direction'], 'right')
                    self.assertNotEqual(files['tab_id'], convo['tab_id'])

    def test_reused_pane_id_is_rejected_before_moving_anything(self):
        self.panes['tasks']['terminal_id'] = 'replaced-terminal'
        before = self.api.call('pane', 'list', '--workspace', self.workspace)['panes']
        with self.assertRaisesRegex(RuntimeError, 'terminal'):
            arrange(self.api, self.conversation, self.panes, 2)
        after = self.api.call('pane', 'list', '--workspace', self.workspace)['panes']
        self.assertEqual({p['pane_id']: p['tab_id'] for p in before},
                         {p['pane_id']: p['tab_id'] for p in after})

    def test_interrupted_panel_initialization_resumes_the_unstarted_panel(self):
        with tempfile.TemporaryDirectory(prefix='wd-resume-launch-') as folder:
            state = {'binding': {'workspace': self.workspace}, 'repo': folder,
                     'panes': {'tasks': self.panes['tasks']},
                     'yazi_client_id': str(time.time_ns())}
            # This owned terminal exists, but interruption prevented its command.
            ensure_panels(self.api, state, lambda: None)
            result = self.api.call('pane', 'process-info', '--pane',
                                   self.panes['tasks']['pane_id'])['process_info']
            self.assertTrue(any(p['name'].startswith('python') for p in result['foreground_processes']),
                            'the saved Tasks shell was skipped instead of initialized')

    def test_a_busy_repurposed_panel_is_left_untouched(self):
        pane = self.panes['tasks']
        self.api.call('pane', 'run', pane['pane_id'], 'sleep 20')
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            info = self.api.call('pane', 'process-info', '--pane', pane['pane_id'])['process_info']
            if any(p['name'] == 'sleep' for p in info['foreground_processes']):break
            time.sleep(.05)
        state = {'binding': {'workspace': self.workspace}, 'repo': '/tmp',
                 'panes': {'tasks': pane}, 'yazi_client_id': '123'}
        with self.assertRaisesRegex(RuntimeError, 'another command'):
            ensure_panels(self.api, state, lambda: None)
        info = self.api.call('pane', 'process-info', '--pane', pane['pane_id'])['process_info']
        self.assertTrue(any(p['name'] == 'sleep' for p in info['foreground_processes']))


class LayoutWithoutYaziTests(unittest.TestCase):
    def test_all_presets_place_the_available_panels_without_files(self):
        from unittest.mock import Mock
        for preset in (1, 2, 3, 4):
            with self.subTest(preset=preset):
                panes = {name: {'pane_id': name, 'tab_id': 'tab'} for name in
                         ('tasks', 'progress', 'artifacts', 'left_undone')}
                conversation = {'pane_id': 'leader', 'workspace_id': 'work', 'tab_id': 'tab'}
                api = Mock()
                api.checked.side_effect = lambda pane: pane

                def call(*args):
                    if args[:2] == ('pane', 'list'):
                        return {'panes': []}
                    if args[:2] == ('pane', 'move'):
                        return {'move_result': {'changed': True, 'pane': panes[args[2]]}}
                    return {}
                api.call.side_effect = call
                arrange(api, conversation, panes, preset)
                moved = {args.args[2] for args in api.call.call_args_list if args.args[:2] == ('pane', 'move')}
                self.assertEqual(moved, set(panes))
