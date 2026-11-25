"""Fresh single launch uses real Git worktrees and only substitutes Herdr/process boundaries."""
import copy
from pathlib import Path
import unittest
from unittest.mock import patch

import test_mission_launch as launch_tests
from test_mission_launch import git
from watchdog_app import mission_launch, mission_cli


class FreshLaunchTests(unittest.TestCase):
    setUp = launch_tests.LaunchTests.setUp

    def fresh(self):
        self.run['execution_mode'] = 'single'
        self.run['provisioning'] = 'fresh'
        self.run['tasks'] = dict(list(self.run['tasks'].items())[:1])
        self.store.save(self.run)
        self.brief.update(execution_mode='single', provisioning='fresh', transport='native')
        self.brief['participants'].pop('qa')
        self.brief['tasks'] = self.brief['tasks'][:1]

    def test_fresh_single_creates_only_worker_and_never_attaches_existing_actor(self):
        self.fresh()
        with patch('watchdog_app.mission_single.launch_existing', side_effect=AssertionError('existing actor')):
            run = mission_launch.launch(self.store, self.run_id, self.brief, confirmed=True, api=self.api)
        self.assertEqual(set(run['participants']), {'worker'})
        self.assertEqual(set(run['resources']), {'worker'})
        self.assertEqual(git(run['participants']['worker']['worktree'], 'rev-parse', 'HEAD'), self.base)
        self.assertEqual(git(self.repo, 'rev-parse', 'HEAD'), self.base)
        self.assertFalse(any(a[:2] == ('pane', 'split') for a in self.api.calls))
        with self.assertRaisesRegex(RuntimeError, 'already|inspect'):
            mission_launch.launch(self.store, self.run_id, self.brief, confirmed=True, api=self.api)

    def test_template_does_not_require_existing_executor(self):
        self.fresh()
        template = mission_cli.template(self.run)
        self.assertEqual(template['provisioning'], 'fresh')
        self.assertEqual(set(template['participants']), {'worker'})
        self.assertIn('model', template['participants']['worker'])
        self.assertNotIn('native', template['participants']['worker'])

    def test_fresh_single_checks_model_effort_and_provisioning_before_launch(self):
        self.fresh()
        for key, value in [('model', ''), ('effort', 'invalid')]:
            wrong = copy.deepcopy(self.brief)
            wrong['participants']['worker'][key] = value
            with self.assertRaises(RuntimeError): mission_launch.validate_brief(self.run, wrong)
        wrong = copy.deepcopy(self.brief); wrong['provisioning'] = 'existing'
        with self.assertRaises(RuntimeError): mission_launch.validate_brief(self.run, wrong)
        self.assertFalse(self.api.calls)

    def test_fresh_dirty_base_rejected_without_resources(self):
        self.fresh()
        (self.repo/'dirty.py').write_text('preserve')
        with self.assertRaisesRegex(RuntimeError, 'clean'):
            mission_launch.launch(self.store, self.run_id, self.brief, confirmed=True, api=self.api)
        self.assertFalse(self.api.calls)
        self.assertEqual((self.repo/'dirty.py').read_text(), 'preserve')


import test_actions
from watchdog_app import mission
from watchdog_app.todo import Snapshot


class FreshRequestTests(unittest.TestCase):
    setUp = test_actions.ActionTests.setUp

    def test_fresh_request_pins_provisioning_without_existing_executor(self):
        snapshot = Snapshot.read(self.repo)
        run = mission.request(self.session, snapshot, {snapshot.tasks[0].id}, confirmed=True,
                              mode='single', provisioning='fresh')
        self.assertEqual(run['provisioning'], 'fresh')
        self.assertNotIn('executor', run)
        self.assertIn('fresh executor', self.delivered[0][2])
        self.assertEqual((self.repo/'TODO.md').read_bytes(), snapshot.raw)

    def test_unknown_provisioning_fails_without_delivery(self):
        snapshot = Snapshot.read(self.repo)
        with self.assertRaises(RuntimeError):
            mission.request(self.session, snapshot, {snapshot.tasks[0].id}, confirmed=True,
                            mode='single', provisioning='guess')
        self.assertFalse(self.delivered)


import test_single_dispatch_ui


class FreshUITests(unittest.TestCase):
    setUp = test_single_dispatch_ui.DispatchUITests.setUp

    def test_new_agent_is_offered_and_confirmation_keeps_todo_open(self):
        self.ui.handle('D')
        self.assertIn('fresh', [row[2] for row in self.ui.body()])
        self.ui.confirm('fresh'); self.ui.draw()
        self.assertIn('Novo executor', '\n'.join(row[0] for row in self.ui.body()))
        self.assertFalse(self.f.messages)
        self.ui.handle('y')
        runs = mission.RunStore().list(self.f.repo)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]['provisioning'], 'fresh')
        self.assertNotIn('executor', runs[0])
        self.assertFalse(Snapshot.read(self.f.repo).tasks[0].done)

    def test_fresh_planning_menu_cancels_without_a_request(self):
        self.ui.handle('P'); self.ui.draw()
        self.assertEqual(self.ui.mode, 'confirm')
        self.ui.handle('escape')
        self.assertFalse(self.f.messages)
