"""Provider port: launch-time contracts and authenticated reports, no LU state."""
import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import test_mission_fresh as fresh_tests
from watchdog_app import mission_launch, mission_native


class ProviderTests(unittest.TestCase):
    setUp = fresh_tests.FreshLaunchTests.setUp
    fresh = fresh_tests.FreshLaunchTests.fresh

    def test_claude_fresh_launch_has_contract_before_terminal_starts(self):
        self.fresh()
        self.brief['participants']['worker'].update(kind='claude', model='sonnet', effort='high')
        run = mission_launch.launch(self.store, self.run_id, self.brief, confirmed=True, api=self.api)
        part = run['participants']['worker']
        self.assertEqual(part['kind'], 'claude')
        task = next(iter(run['tasks'].values()))
        attempt = task['attempt_id']
        delivery = run['deliveries'][attempt]
        self.assertEqual(delivery['method'], 'launch')
        self.assertEqual(delivery['state'], 'sending')
        self.assertEqual(delivery['payload']['allowed_files'], ['a.py'])
        self.assertNotIn('receipt', delivery)
        prompt = mission_native.participant_prompt(self.store, run, 'worker')
        self.assertIn(attempt, prompt)
        self.assertIn('enroll', prompt)
        self.assertNotIn('explicit queued contract', prompt)

    def test_provider_validation_rejects_unknown_and_claude_legacy_team(self):
        self.fresh()
        for kind in ('unknown', ''):
            self.brief['participants']['worker']['kind'] = kind
            with self.assertRaisesRegex(RuntimeError, 'provider|kind'):
                mission_launch.validate_brief(self.run, self.brief)
        self.run.pop('provisioning'); self.run['execution_mode'] = 'team'
        self.brief.pop('provisioning'); self.brief['execution_mode'] = 'team'
        self.brief['participants']['worker']['kind'] = 'claude'
        self.brief['participants']['qa'] = dict(self.brief['participants']['worker'], kind='codex')
        with self.assertRaisesRegex(RuntimeError, 'fresh|Claude'):
            mission_launch.validate_brief(self.run, self.brief)

    def test_provider_commands_isolate_accounts_and_do_not_resume(self):
        from watchdog_app.mission_fresh import provider_command
        part = {'kind':'claude','account':'/chosen/claude', 'executable':'/usr/bin/claude',
                'worktree':'/worktree','model':'sonnet','effort':'high'}
        with patch.dict(os.environ, {'CODEX_HOME':'/wrong', 'CODEX_THREAD_ID':'inherited',
                                    'CLAUDECODE':'nested', 'CLAUDE_CONFIG_DIR':'/wrong'}):
            argv, env = provider_command(part, 'standalone brief', self.store, self.run)
        self.assertEqual(argv[:3], ['/usr/bin/claude', '--model', 'sonnet'])
        self.assertIn('bypassPermissions', argv)
        self.assertEqual(argv[-1], 'standalone brief')
        self.assertEqual(env['CLAUDE_CONFIG_DIR'], '/chosen/claude')
        self.assertNotIn('CODEX_THREAD_ID', env)
        self.assertNotIn('CODEX_HOME', env)
        self.assertNotIn('CLAUDECODE', env)
        self.assertNotIn('resume', argv)

    def test_monitor_does_not_invalidate_pending_frontend_registration(self):
        self.fresh()
        run = mission_launch.launch(self.store, self.run_id, self.brief, confirmed=True, api=self.api)
        attempt = run['participants']['worker']['startup_attempt']
        mission_native.reconcile_intents(run)
        self.assertEqual(run['deliveries'][attempt]['state'], 'sending')
        self.assertEqual(next(iter(run['tasks'].values()))['delivery'], 'sending')

    def test_claude_bootstrap_report_uses_real_socket_and_process_ancestry(self):
        from dataclasses import asdict
        from types import SimpleNamespace
        import uuid
        from test_actions import FakeBinding
        from watchdog_app import mission_broker, mission_transport
        self.fresh()
        self.brief['participants']['worker'].update(kind='claude', model='sonnet')
        run = mission_launch.launch(self.store, self.run_id, self.brief, confirmed=True, api=self.api)
        pane = run['resources']['worker']
        actor = FakeBinding(kind='claude', session=str(uuid.uuid4()), account=str(self.root),
                            pane=pane['pane_id'], terminal=pane['terminal_id'],
                            pid=os.getpid(), started=mission_broker.process(os.getpid())[1])
        runtime = SimpleNamespace(Binding=FakeBinding, verify=lambda b:{'agent_status':'working'})
        child = SimpleNamespace(pid=os.getpid(), poll=lambda:None)
        with patch.object(mission_native.bindings, 'engine', return_value=runtime), \
                patch.object(mission_native.bindings, 'discover', return_value=([actor], [])), \
                patch.object(mission_transport, 'main_session', side_effect=RuntimeError('leader offline')):
            proof = mission_native.bootstrap(self.store, self.run_id, 'worker', child)
            broker = mission_broker.Broker(self.store, self.run_id, 'worker', proof, child)
            try:
                with patch.dict(os.environ, {'CODEX_THREAD_ID':'unrelated-codex-thread'}):
                    result = mission_broker.request(self.store, self.run_id, 'worker', 'enroll')
                    self.assertTrue(result['published'])
                    current = self.store.load(self.run_id)
                    task_id = next(iter(current['tasks']))
                    attempt = current['tasks'][task_id]['attempt_id']
                    self.assertTrue(mission_native.delivery_receipt(current, 'worker', attempt, task_id=task_id)[0])
                    report = {'run_id':self.run_id, 'task_id':task_id, 'attempt_id':attempt,
                              'event_id':str(uuid.uuid4()), 'status':'blocked', 'summary':'Need fixture'}
                    receipt = mission_broker.request(self.store, self.run_id, 'worker', 'report', report=report)
                    self.assertTrue(receipt['persisted'])
                    self.assertEqual(receipt['notification'], 'pending')
                    self.assertFalse((self.repo/'TODO.md').read_text().count('[x]'))
                with self.assertRaises(RuntimeError):
                    broker.execute(1, os.getuid(), {'run':self.run_id, 'role':'worker', 'session':actor.session,
                                                   'method':'report', 'data':{'report':report}})
            finally:
                broker.close()

    def test_claude_followup_starts_new_attempt_at_clean_worker_head(self):
        from watchdog_app.mission_fresh import retry
        from test_mission_launch import git
        self.fresh()
        self.brief['participants']['worker'].update(kind='claude', model='sonnet')
        run = mission_launch.launch(self.store, self.run_id, self.brief, confirmed=True, api=self.api)
        old_part = copy.deepcopy(run['participants']['worker'])
        task_id = next(iter(run['tasks']))
        old_attempt = run['tasks'][task_id]['attempt_id']
        run['tasks'][task_id].update(delivery='sent', state='blocked')
        self.store.save(run)
        worktree = Path(old_part['worktree'])
        (worktree/'a.py').write_text('print(2)\n')
        git(worktree, 'commit', '-am', 'wip: checkpoint')
        checkpoint = git(worktree, 'rev-parse', 'HEAD')
        new = retry(self.store, self.run_id, task_id, 'Continue from the checkpoint', api=self.api)
        new_part = new['participants']['worker']
        self.assertNotEqual(new_part['worktree'], old_part['worktree'])
        self.assertEqual(git(new_part['worktree'], 'rev-parse', 'HEAD'), checkpoint)
        self.assertTrue(worktree.is_dir())
        self.assertNotEqual(new['tasks'][task_id]['attempt_id'], old_attempt)
        self.assertIn(old_attempt, new['tasks'][task_id]['attempt_history'])
        payload = new['deliveries'][new['tasks'][task_id]['attempt_id']]['payload']
        self.assertEqual(payload['base_sha'], checkpoint)
        self.assertEqual(payload['clarification'], 'Continue from the checkpoint')

    def test_claude_followup_refuses_dirty_or_uncertain_work_without_changing_attempt(self):
        from watchdog_app.mission_fresh import retry
        self.fresh()
        self.brief['participants']['worker'].update(kind='claude', model='sonnet')
        run = mission_launch.launch(self.store, self.run_id, self.brief, confirmed=True, api=self.api)
        task_id = next(iter(run['tasks']))
        before = self.store.path(self.run_id).read_bytes()
        with self.assertRaisesRegex(RuntimeError, 'uncertain|confirmed'):
            retry(self.store, self.run_id, task_id, 'Continue', api=self.api)
        self.assertEqual(self.store.path(self.run_id).read_bytes(), before)
        run['tasks'][task_id]['delivery'] = 'sent'; self.store.save(run)
        (Path(run['participants']['worker']['worktree'])/'dirty').touch()
        with self.assertRaisesRegex(RuntimeError, 'clean'):
            retry(self.store, self.run_id, task_id, 'Continue', api=self.api)
        self.assertEqual(self.store.load(self.run_id)['tasks'][task_id]['attempt_id'], run['tasks'][task_id]['attempt_id'])
