"""Native planning produces a proposal, never implementation completion evidence."""
import io
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import test_mission_fresh as fresh_tests
from watchdog_app import mission_launch, mission


class PlanTests(unittest.TestCase):
    setUp = fresh_tests.FreshLaunchTests.setUp
    fresh = fresh_tests.FreshLaunchTests.fresh

    def test_native_codex_plan_uses_selected_executable_and_read_only_preset(self):
        from watchdog_app import mission_plan
        from test_mission_port_recovery import appserver
        executable = appserver(self.root)
        job = {'model':'model', 'effort':'high', 'cwd':str(self.repo), 'executable':executable}
        result = mission_plan.codex_plan(job, {}, 'Plan only', lambda q:None)
        self.assertEqual(result, 'A real subprocess proposal')
        requests = [json.loads(line) for line in (self.repo/'requests.jsonl').read_text().splitlines()]
        self.assertEqual(next(m for m in requests if m.get('method')=='thread/start')['params']['sandbox'], 'read-only')
        self.assertEqual(next(m for m in requests if m.get('method')=='turn/start')['params']['collaborationMode']['mode'], 'plan')

    def test_plan_record_keeps_todo_open_and_cannot_pass_leader_review(self):
        from watchdog_app import mission_plan, mission_single
        self.fresh(); self.run['purpose']='plan'; self.brief['purpose']='plan'; self.store.save(self.run)
        run = mission_launch.launch(self.store, self.run_id, self.brief, confirmed=True, api=self.api)
        with patch.object(mission_plan, 'run', return_value='1. Add behavior\n2. Verify it'), \
                patch.object(mission_plan, 'notify', return_value=None):
            mission_plan.participant(self.store, self.run_id)
        run = self.store.load(self.run_id)
        self.assertTrue(all(t.get('plan') for t in run['tasks'].values()))
        self.assertTrue(all(not t.get('result') for t in run['tasks'].values()))
        self.assertNotIn('[x]', (self.repo/'TODO.md').read_text())
        self.assertEqual(mission.run_status(run)['label'], 'Plano pronto')
        with self.assertRaises(RuntimeError): mission_single.verify_candidate(run, self.base)

    def test_planner_that_changes_source_is_rejected_with_evidence_retained(self):
        from watchdog_app import mission_plan
        self.fresh(); self.run['purpose']='plan'; self.brief['purpose']='plan'; self.store.save(self.run)
        run = mission_launch.launch(self.store, self.run_id, self.brief, confirmed=True, api=self.api)
        def changed(*args):
            (Path(run['participants']['worker']['worktree'])/'a.py').write_text('changed')
            return 'A plan'
        with patch.object(mission_plan, 'run', side_effect=changed), patch.object(mission_plan, 'notify', return_value=None):
            mission_plan.participant(self.store, self.run_id)
        retained = self.store.load(self.run_id)
        self.assertTrue(all(t['state']=='blocked' and not t.get('plan') for t in retained['tasks'].values()))
        self.assertEqual((Path(run['participants']['worker']['worktree'])/'a.py').read_text(), 'changed')

    def test_ready_plan_opens_owned_tab_without_a_live_native_worker(self):
        self.run['main']['workspace'] = 'wd-test'; self.session.binding.workspace = 'wd-test'
        self.fresh(); self.run['purpose']='plan'; self.brief['purpose']='plan'; self.store.save(self.run)
        run=mission_launch.launch(self.store, self.run_id, self.brief, confirmed=True, api=self.api)
        mission_launch.open_run(run, self.api)
        self.assertIn(('tab','focus',run['tab']), self.api.calls)
        self.api.panes[run['resources']['worker']['pane_id']]['terminal_id']='replacement'
        with self.assertRaises(RuntimeError): mission_launch.open_run(run, self.api)
