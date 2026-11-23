"""A Together contract covers every selected task, without completing TODO."""
import copy
import unittest
from unittest.mock import patch

import test_mission_fresh as fresh_tests
import test_mission_native_transport as native_tests
from watchdog_app import mission_launch, mission_native, mission_fresh


class BundleLaunchTests(unittest.TestCase):
    setUp = fresh_tests.FreshLaunchTests.setUp

    def test_together_launch_keeps_both_task_ids_in_one_contract(self):
        self.run.update(execution_mode='single', provisioning='fresh', grouping='together')
        self.brief.update(execution_mode='single', provisioning='fresh', grouping='together', transport='native')
        self.brief['participants'].pop('qa')
        self.store.save(self.run)
        run = mission_launch.launch(self.store, self.run_id, self.brief, confirmed=True, api=self.api)
        self.assertEqual(set(run['tasks']), set(self.run['tasks']))
        self.assertEqual(len(run['deliveries']), 1)
        record = next(iter(run['deliveries'].values()))
        self.assertEqual({t['id'] for t in record['payload']['members']}, set(run['tasks']))
        self.assertEqual({t['attempt_id'] for t in run['tasks'].values()}, {record['attempt_id']})
        self.assertEqual(set(run['participants']), {'worker'})


class BundleReportTests(unittest.TestCase):
    setUp = native_tests.NativeTransportTests.setUp
    proof = native_tests.NativeTransportTests.proof
    record = native_tests.NativeTransportTests.record
    report = native_tests.NativeTransportTests.report

    def bundle(self):
        self.run.update(execution_mode='single', provisioning='fresh', grouping='together')
        self.run['participants'].pop('qa'); self.run['resources'].pop('qa')
        mission_fresh.prepare(self.run)
        proof = {key:self.run['participants']['worker'][key] for key in ('native', 'generation')}
        mission_fresh.attach(self.run, proof)
        self.store.save(self.run)

    def test_partial_bundle_result_cannot_mark_all_tasks_ready_for_review(self):
        self.bundle()
        with self.assertRaisesRegex(RuntimeError, 'cover|bundle|selected'):
            self.record(self.report('result', commits=[self.base], tests=['Passed'], covered_tasks=[self.task]))
        run = self.store.load(self.identity)
        self.assertTrue(all(not t.get('result') for t in run['tasks'].values()))

    def test_complete_bundle_result_and_blocker_propagate_once(self):
        self.bundle()
        covered = list(self.run['tasks'])
        report = self.report('result', commits=[self.base], tests=['Passed'], covered_tasks=covered)
        self.record(report)
        run = self.store.load(self.identity)
        self.assertTrue(all(t['state']=='review' and t['result']==report for t in run['tasks'].values()))
        version = run['result_version']; self.record(report)
        self.assertEqual(self.store.load(self.identity)['result_version'], version)
        self.record(self.report('blocked'))
        run = self.store.load(self.identity)
        self.assertTrue(all(t['state']=='blocked' and not t.get('result') for t in run['tasks'].values()))
        self.assertNotIn('[x]', (self.repo/'TODO.md').read_text())


import test_actions
from watchdog_app import mission
from watchdog_app.todo import Snapshot


class GroupRequestTests(unittest.TestCase):
    setUp = test_actions.ActionTests.setUp

    def tasks(self):
        (self.repo/'TODO.md').write_text('## Next\n- [ ] First\n- [ ] Second\n')
        snapshot = Snapshot.read(self.repo)
        return snapshot, {t.id for t in snapshot.tasks}

    def test_separate_requests_queue_one_parent_message_and_keep_distinct_runs(self):
        snapshot, ids = self.tasks()
        runs = mission.request_batch(self.session, snapshot, ids, confirmed=True, grouping='separate')
        self.assertEqual(len(runs), 2)
        self.assertEqual(len(self.delivered), 1)
        self.assertTrue(all(len(r['tasks'])==1 and r['request_delivery']=='sent' for r in runs))
        self.assertEqual(set().union(*(set(r['tasks']) for r in runs)), ids)
        self.assertTrue(all(r['id'] in self.delivered[0][2] for r in runs))
        self.assertEqual((self.repo/'TODO.md').read_bytes(), snapshot.raw)

    def test_together_plan_request_pins_purpose_and_full_selection(self):
        snapshot, ids = self.tasks()
        runs = mission.request_batch(self.session, snapshot, ids, confirmed=True, grouping='together', purpose='plan')
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]['purpose'], 'plan')
        self.assertEqual(set(runs[0]['tasks']), ids)
        self.assertIn('plan only', self.delivered[0][2])

    def test_failed_batch_send_is_retained_and_cannot_be_blindly_repeated(self):
        snapshot, ids = self.tasks()
        def failed(*args): raise RuntimeError('receipt lost')
        self.session.runtime.queue = failed
        with self.assertRaises(RuntimeError):
            mission.request_batch(self.session, snapshot, ids, confirmed=True, grouping='separate')
        runs = mission.RunStore().list(self.repo)
        self.assertEqual(len(runs), 2)
        self.assertTrue(all(r['request_delivery']=='uncertain' for r in runs))
        with self.assertRaises(RuntimeError):
            mission.request_batch(self.session, snapshot, ids, confirmed=True, grouping='separate')
        self.assertEqual(len(mission.RunStore().list(self.repo)), 2)


import test_single_dispatch_ui


class GroupUITests(unittest.TestCase):
    setUp = test_single_dispatch_ui.DispatchUITests.setUp

    def test_plan_key_offers_grouping_and_separate_dispatch_keeps_todo_open(self):
        self.ui.selected = {t.id for t in self.ui.snapshot.tasks}
        self.ui.handle('P')
        self.assertEqual(self.ui.mode, 'grouping')
        self.assertEqual({r[2] for r in self.ui.body() if r[2]}, {'together', 'separate'})
        self.ui.draw(); self.ui.handle('down'); self.ui.draw(); self.ui.handle('enter')
        self.assertEqual(self.ui.mode, 'confirm')
        self.assertIn('planejamento', '\n'.join(r[0] for r in self.ui.body()).lower())
        self.assertFalse(self.f.messages)
        self.ui.draw(); self.ui.handle('y')
        runs = mission.RunStore().list(self.f.repo)
        self.assertEqual(len(runs), 2)
        self.assertTrue(all(r['purpose']=='plan' and len(r['tasks'])==1 for r in runs))
        self.assertEqual(len(self.f.messages), 1)
        self.assertTrue(all(not t.done for t in Snapshot.read(self.f.repo).tasks))


class ClaudeLeaderTests(unittest.TestCase):
    setUp = test_actions.ActionTests.setUp

    def claude(self):
        import json
        from watchdog_app.actions import Session
        data=json.loads(self.file.read_text()); data['binding']['kind']='claude'
        self.file.write_text(json.dumps(data)); self.session=Session(self.file, self.repo)

    def test_fresh_dispatch_from_idle_claude_uses_verified_send(self):
        self.claude(); snapshot=Snapshot.read(self.repo)
        runs=mission.request_batch(self.session, snapshot, {snapshot.tasks[0].id}, confirmed=True)
        self.assertEqual(len(runs), 1)
        self.assertEqual(self.delivered[0][0], 'send')
        self.assertEqual(runs[0]['main']['kind'], 'claude')

    def test_busy_claude_leader_creates_no_request(self):
        self.claude(); self.busy=True; snapshot=Snapshot.read(self.repo)
        with self.assertRaises(RuntimeError):
            mission.request_batch(self.session, snapshot, {snapshot.tasks[0].id}, confirmed=True)
        self.assertFalse(self.delivered)
        self.assertFalse(mission.RunStore().list(self.repo))
