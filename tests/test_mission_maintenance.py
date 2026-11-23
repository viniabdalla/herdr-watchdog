"""Real Git/ledger tests for explicit QA renewal and pending bundle preparation."""
import copy
import unittest
from unittest.mock import patch

import test_mission_native_transport as native_tests
from watchdog_app import mission_native as native, mission_transport as transport
from watchdog_app.mission_launch import git


class MaintenanceTests(unittest.TestCase):
    setUp = native_tests.NativeTransportTests.setUp
    proof = native_tests.NativeTransportTests.proof
    record = native_tests.NativeTransportTests.record
    report = native_tests.NativeTransportTests.report

    def ready(self):
        self.run['tasks'] = {self.task:self.run['tasks'][self.task]}
        self.run['brief']['tasks'] = [t for t in self.run['brief']['tasks'] if t['id']==self.task]
        self.store.save(self.run)
        transport.dispatch(self.store,self.identity,self.task)
        self.record(self.report('result',commits=[self.base],tests=['Observed pass']))
        native.review(self.store,self.identity,self.base)
        r=self.store.load(self.identity)
        self.record(dict(run_id=self.identity,attempt_id=r['qa_task'],review_id=r['review_contract']['id'],
                         event_id='ebaa290a-9655-402a-a88c-ac58bf49b3cd',candidate=self.base,
                         status='qa',verdict='fail',summary='Needs correction',tests=['Observed failure']),role='qa')
        r=self.store.load(self.identity)
        r['main']['workspace']=r['resources']['qa']['workspace_id'];self.store.save(r)
        return r

    def test_new_qa_preserves_old_actor_and_uses_separate_worktree_and_pane(self):
        from watchdog_app.mission_maintenance import renew_qa
        old=self.ready(); api=self.fixture.api
        before=copy.deepcopy(old['participants']['qa']);old_proof=self.proof('qa')
        # Fixture split returns one deterministic new terminal.
        api.panes[old['resources']['qa']['pane_id']]=old['resources']['qa']
        original=api.call
        def call(*args):
            if args[:2]==('pane','split'):
                p=dict(old['resources']['qa'],pane_id='new-qa',terminal_id='new-qa-terminal')
                api.panes[p['pane_id']]=p;api.calls.append(args);return {'pane':p}
            return original(*args)
        api.call=call
        with patch('watchdog_app.mission_maintenance.main_session'),patch('watchdog_app.mission_maintenance.source_current'):
            r=renew_qa(self.store,self.identity,self.base,confirmed=True,api=api)
        self.assertEqual(r['qa_history'][-1]['participant'],before)
        self.assertEqual(r['qa_history'][-1]['resource'],old['resources']['qa'])
        self.assertNotEqual(r['participants']['qa']['worktree'],before['worktree'])
        self.assertEqual(git(r['participants']['qa']['worktree'],'rev-parse','HEAD'),self.base)
        self.assertNotIn('native',r['participants']['qa'])
        from watchdog_app.mission_fresh import artifact
        self.assertNotEqual(artifact(r,'qa','exit.json'),'qa-exit.json')
        with self.assertRaises(RuntimeError):native.check_proof(r,'qa',old_proof)
        self.assertEqual(r['resources']['qa']['pane_id'],'new-qa')
        self.assertFalse(any(c[:2] in [('pane','close'),('agent','send-keys')] for c in api.calls))
        calls=len(api.calls)
        with self.assertRaises(RuntimeError):renew_qa(self.store,self.identity,self.base,confirmed=True,api=api)
        self.assertEqual(len(api.calls),calls)

    def test_new_qa_requires_confirmation_and_finished_review(self):
        from watchdog_app.mission_maintenance import renew_qa
        r=self.ready(); r['qa_finished']=False; self.store.save(r)
        count=len(self.fixture.api.calls)
        with patch('watchdog_app.mission_maintenance.main_session'),patch('watchdog_app.mission_maintenance.source_current'):
            with self.assertRaises(RuntimeError):renew_qa(self.store,self.identity,self.base,api=self.fixture.api)
            with self.assertRaises(RuntimeError):renew_qa(self.store,self.identity,self.base,confirmed=True,api=self.fixture.api)
        self.assertEqual(len(self.fixture.api.calls),count)
        self.assertEqual(self.store.load(self.identity)['participants'],r['participants'])

    def test_uncertain_qa_launch_is_retained_without_automatic_retry(self):
        from watchdog_app.mission_maintenance import renew_qa
        old=self.ready();self.fixture.api.fail=('pane','run')
        api=self.fixture.api;original=api.call
        def call(*args):
            if args[:2]==('pane','split'):
                p=dict(old['resources']['qa'],pane_id='fresh-qa',terminal_id='fresh-terminal')
                api.panes[p['pane_id']]=p;api.calls.append(args);return {'pane':p}
            return original(*args)
        api.call=call
        with patch('watchdog_app.mission_maintenance.main_session'),patch('watchdog_app.mission_maintenance.source_current'):
            with self.assertRaises(RuntimeError):renew_qa(self.store,self.identity,self.base,confirmed=True,api=self.fixture.api)
            r=self.store.load(self.identity)
            self.assertEqual(r['qa_refresh']['state'],'uncertain')
            n=len(self.fixture.api.calls)
            with self.assertRaises(RuntimeError):renew_qa(self.store,self.identity,self.base,confirmed=True,api=self.fixture.api)
            self.assertEqual(n,len(self.fixture.api.calls))

    def test_preparation_requires_confirmation_and_untouched_pending_run(self):
        from watchdog_app.mission_maintenance import prepare_team
        r=copy.deepcopy(self.run);r.update(phase='requested',participants={},resources={},deliveries={})
        self.store.save(r)
        with patch('watchdog_app.mission_maintenance.main_session'),patch('watchdog_app.mission_maintenance.source_current'):
            with self.assertRaises(RuntimeError):prepare_team(self.store,self.identity,confirmed=False)
            ready=prepare_team(self.store,self.identity,confirmed=True)
            self.assertEqual(ready['grouping'],'together')
            self.assertEqual(set(ready['tasks']),set(r['tasks']))
            self.assertEqual(ready['checkpoint']['sha'],self.base)
            ready['phase']='active';self.store.save(ready)
            with self.assertRaises(RuntimeError):prepare_team(self.store,self.identity,confirmed=True)


class TeamBundleTests(unittest.TestCase):
    setUp = native_tests.NativeTransportTests.setUp
    proof = native_tests.NativeTransportTests.proof
    record = native_tests.NativeTransportTests.record
    report = native_tests.NativeTransportTests.report

    def test_team_bundle_dispatch_and_followup_pin_all_members(self):
        self.run['grouping']='together';self.run['brief']['grouping']='together';self.store.save(self.run)
        r=transport.dispatch(self.store,self.identity,self.task)
        ids=set(r['tasks']);attempt=r['tasks'][self.task]['attempt_id']
        self.assertEqual({t.get('attempt_id') for t in r['tasks'].values()},{attempt})
        self.assertEqual({t['id'] for t in self.calls[-1][1]['members']},ids)
        r=transport.followup(self.store,self.identity,self.task,'Correct the bundle')
        self.assertEqual(len({t.get('attempt_id') for t in r['tasks'].values()}),1)
        with self.assertRaises(RuntimeError):
            self.record(self.report('result',commits=[self.base],tests=['Pass'],covered_tasks=[self.task]))
        self.assertFalse(any(t.get('result') for t in self.store.load(self.identity)['tasks'].values()))
        self.record(self.report('result',commits=[self.base],tests=['Pass'],covered_tasks=list(ids)))
        r=self.store.load(self.identity)
        self.assertTrue(all(t.get('result') for t in r['tasks'].values()))
        native.review(self.store,self.identity,self.base)
        self.assertEqual(self.calls[-1][1]['candidate'],self.base)


class TeamRequestTests(unittest.TestCase):
    from test_actions import ActionTests
    setUp=ActionTests.setUp

    def test_multi_task_team_is_one_explicit_bundle(self):
        from watchdog_app.mission import request
        from watchdog_app.todo import Snapshot
        (self.repo/'TODO.md').write_text('## Next\n- [ ] First\n- [ ] Second\n')
        s=Snapshot.read(self.repo)
        r=request(self.session,s,{t.id for t in s.tasks},mode='team',confirmed=True,grouping='together')
        self.assertEqual(r.get('grouping'),'together')
        self.assertIn('TOGETHER',self.delivered[-1][2])
