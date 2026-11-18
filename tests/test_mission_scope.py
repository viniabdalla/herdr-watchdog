"""Selected scope with real temporary TODO/Git/RunStore; native UI/model fixtures only."""
import copy
from dataclasses import asdict
import json
import io
import os
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import patch

from test_actions import FakeBinding
import test_mission_launch as launch_tests
from test_mission_launch import git
from watchdog_app import mission, mission_launch as launch, mission_native as native
from watchdog_app import mission_transport as transport, mission_cli, mission_handoff as handoff, bindings
from watchdog_app.actions import Session
from watchdog_app.todo import Snapshot


class ScopeTests(unittest.TestCase):
    def setUp(self):
        fixture = launch_tests.LaunchTests(); fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture; self.repo = fixture.repo; self.store = fixture.store
        self.store.path(fixture.run_id).unlink()  # Fixture ledger is legacy, never migrate it.
        self.original = '## Next\n- [ ] First\n  Keep exact notes.\n- [ ] Second\n'
        self.write(self.original)
        git(self.repo, 'add', 'TODO.md'); git(self.repo, 'commit', '-qm', 'selected notes')
        self.base = git(self.repo, 'rev-parse', 'HEAD')
        self.calls = []
        def queue(binding, text):
            self.calls.append((binding, text))
            return str(uuid.uuid4())
        self.runtime = SimpleNamespace(Binding=FakeBinding, verify=lambda b: {'agent_status':'idle'}, queue=queue)
        binding = FakeBinding(session=str(uuid.uuid4()),account=str(fixture.root))
        binding_file = fixture.root/'binding.json'
        binding_file.write_text(json.dumps({'repo':str(self.repo),'binding':asdict(binding)}))
        for p in (patch.dict('os.environ', {'WATCHDOG_STATE_DIR':str(fixture.root/'state')}),
                  patch.object(bindings,'engine',return_value=self.runtime),
                  patch.object(bindings,'project_for',return_value=self.repo)):
            p.start(); self.addCleanup(p.stop)
        self.session = Session(binding_file,self.repo)
        p = patch.object(launch,'Session',return_value=self.session)
        p.start(); self.addCleanup(p.stop)

    def write(self, text):
        (self.repo/'TODO.md').write_text(text)

    def request(self, count=1):
        snap = Snapshot.read(self.repo)
        return mission.request(self.session, snap, [t.id for t in snap.tasks[:count]], confirmed=True, store=self.store)

    def start(self, count=1, dependent=False):
        self.run = self.request(count); self.identity = self.run['id']; self.task = next(iter(self.run['tasks']))
        self.brief = copy.deepcopy(self.fixture.brief)
        self.brief.update(transport='native', run_id=self.identity, base_sha=self.base)
        self.brief['tasks'] = [dict(self.fixture.brief['tasks'][0], id=k) for k in self.run['tasks']]
        if dependent:
            self.brief['tasks'][1]['dependencies'] = [self.task]
        self.run = launch.launch(self.store, self.identity, self.brief, confirmed=True, api=self.fixture.api)
        self.bindings = {}
        for role in ('worker','qa'):
            pane = self.run['resources'][role]
            binding = FakeBinding(session=str(uuid.uuid4()), account=self.run['participants'][role]['account'],
                                  pane=pane['pane_id'], terminal=pane['terminal_id'])
            self.bindings[role] = binding
            self.run['participants'][role].update(native=asdict(binding), generation=str(uuid.uuid4()),
                boot_id=native.boot_id(), bridge_owner=native.owner(), enrolled=True, available=True)
        self.store.save(self.run)
        for p in (patch.object(native.bindings,'engine',return_value=self.runtime),
                  patch.object(transport,'main_session',return_value=self.session),
                  patch.object(mission_cli,'main_session',return_value=self.session)):
            p.start(); self.addCleanup(p.stop)
        self.calls.clear()
        return self.run

    def report(self, status='working', role='worker', **extra):
        run = self.store.load(self.identity); part = run['participants'][role]
        proof = dict(transport='native', run_id=self.identity, role=role,
                     **{k:part[k] for k in ('native','generation','boot_id','bridge_owner')})
        report = dict(run_id=self.identity, task_id=self.task, attempt_id=run['tasks'][self.task]['attempt_id'],
                      event_id=str(uuid.uuid4()), status=status, summary='Observed test evidence')
        report.update(extra)
        return native.handle(self.store, self.identity, role, proof, 'report', {'report':report})

    def cli(self, action, *args):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return mission_cli.main([action, '--run',self.identity,'--state-dir',str(self.store.root),*args])

    def test_new_request_pins_exact_blocks_and_preserves_original_digest_and_ids(self):
        run = self.request(); saved = copy.deepcopy(run)
        self.write('# Ideas\n\n'+self.original.replace('- [ ] Second', '- [x] Changed unrelated task'))
        launch.source_current(run)
        self.assertEqual(run, saved)
        self.assertEqual(self.store.load(run['id']), saved)
        self.assertNotEqual(Snapshot.read(self.repo).tasks[0].id, next(iter(run['tasks'])))
        self.assertIn('scope', run)

    def test_unrelated_insert_delete_rename_reorder_headings_notes_and_completion(self):
        run = self.request()
        variants = [
            '# Ideas\n## Next\n- [ ] New idea\n'+self.original.split('## Next\n')[1],
            self.original.replace('- [ ] Second\n', ''),
            self.original.replace('- [ ] Second\n', '- [ ] Renamed\n  Unselected note\n'),
            '## Next\n- [x] Second\n- [ ] First\n  Keep exact notes.\n',
            self.original+'\n## Done\n- [x] Unrelated\n',
        ]
        for text in variants:
            with self.subTest(text=text):
                self.write(text); launch.source_current(run)

    def test_selected_changes_and_ambiguity_require_new_contract(self):
        run = self.request()
        variants = [
            self.original.replace('First','Changed'),
            self.original.replace('- [ ] First\n  Keep exact notes.\n',''),
            self.original.replace('- [ ] First','- [x] First'),
            self.original.replace('## Next','## In progress'),
            self.original.replace('Keep exact notes.','Changed notes.'),
            self.original.replace('  Keep','    Keep'),
            self.original+'- [ ] First\n  Keep exact notes.\n',
            self.original+'## Blocked\n- [ ] First\n  Keep exact notes.\n',
        ]
        for text in variants:
            with self.subTest(text=text):
                self.write(text)
                with self.assertRaisesRegex(RuntimeError,'scope|selected|contract|ambiguous'):
                    launch.source_current(run)

    def test_duplicate_request_after_row_shift_never_queues_or_creates_ledger(self):
        first = self.request()
        self.write('# Ideas\n'+self.original)
        with self.assertRaisesRegex(RuntimeError,'already'):
            self.request()
        self.assertEqual(len(self.calls),1)
        self.assertEqual([r['id'] for r in self.store.list(self.repo)],[first['id']])

    def test_ambiguous_initial_selection_never_queues(self):
        self.write(self.original+'- [ ] First\n  Keep exact notes.\n')
        with self.assertRaisesRegex(RuntimeError,'ambiguous'):
            self.request()
        self.assertEqual(self.calls,[])
        self.assertEqual(self.store.list(self.repo),[])

    def test_stale_request_still_checks_entire_confirmation_snapshot(self):
        snap = Snapshot.read(self.repo)
        self.write(self.original+'- [ ] Unrelated but unconfirmed\n')
        with self.assertRaisesRegex(RuntimeError,'changed'):
            mission.request(self.session,snap,[snap.tasks[0].id],confirmed=True,store=self.store)
        self.assertFalse(self.calls)
        self.assertFalse(self.store.list(self.repo))

    def test_unknown_and_malformed_scope_fail_closed_and_legacy_is_never_upgraded(self):
        run = self.request()
        for invalid in (None, {}, {'version':99,'tasks':{}}, {'version':True,'tasks':{}},
                        {'version':1,'tasks':{}}, {'version':1,'tasks':[]},
                        {'version':1,'tasks':{next(iter(run['tasks'])):{'block':7,'section':'Next'}}}):
            with self.subTest(scope=invalid):
                bad = dict(run,scope=invalid)
                with self.assertRaisesRegex(RuntimeError,'scope'):
                    launch.source_current(bad)
        legacy = copy.deepcopy(run); legacy.pop('scope')
        before = copy.deepcopy(legacy); launch.source_current(legacy)
        self.write('# Ideas\n'+self.original)
        with self.assertRaisesRegex(RuntimeError,'changed'):
            launch.source_current(legacy)
        self.assertEqual(legacy,before)

    def test_todo_only_edits_do_not_block_launch_clean_check(self):
        # Regression: adding ideas to TODO.md while the main prepares the brief
        # must not make the launch fail with a dirty-repository error.
        run = self.request(); self.write('# Ideas\n'+self.original)
        brief = copy.deepcopy(self.fixture.brief)
        brief.update(transport='native',run_id=run['id'],base_sha=self.base)
        launch.clean_base(self.store.load(run['id']),brief)

    def test_initial_launch_still_requires_clean_repo_before_native_resources(self):
        run = self.request(); (self.repo/'other.py').write_text('dirty = True\n')
        brief = copy.deepcopy(self.fixture.brief)
        brief.update(transport='native',run_id=run['id'],base_sha=self.base)
        brief['tasks'] = [dict(brief['tasks'][0],id=next(iter(run['tasks'])))]
        with self.assertRaisesRegex(RuntimeError,'clean'):
            launch.launch(self.store,run['id'],brief,confirmed=True,api=self.fixture.api)
        self.assertFalse(self.fixture.api.calls)
        self.assertFalse(self.store.load(run['id'])['participants'])

    def test_new_scope_end_to_end_with_dirty_unrelated_todo_and_exact_qa(self):
        run = self.start(); original_scope = copy.deepcopy(run['scope'])
        transport.dispatch(self.store,self.identity,self.task)
        self.write('# New ideas\n'+self.original.replace('- [ ] Second','- [x] Different unrelated task'))
        transport.tick(self.store,self.identity)
        transport.followup(self.store,self.identity,self.task,'Clarify only this task')
        path = run['participants']['worker']['worktree']
        (Path(path)/'a.py').write_text('print(2)\n')
        git(path,'add','a.py'); git(path,'commit','-qm','worker result')
        candidate = git(path,'rev-parse','HEAD')
        self.report('result',commits=[candidate],tests=['python a.py: 2'])
        self.assertEqual(self.cli('accept-result','--task',self.task,'--confirm'),0)
        review = transport.review(self.store,self.identity,candidate)
        self.report('qa',role='qa',attempt_id=review['qa_task'],review_id=review['review_contract']['id'],
                    candidate=candidate,verdict='pass',tests=['independent controlled fixture review'])
        self.assertEqual(self.cli('approve','--candidate',candidate,'--confirm'),0)
        final = self.store.load(self.identity)
        self.assertEqual(final['phase'],'done')
        self.assertEqual(final['scope'],original_scope)
        self.assertEqual(set(final['tasks']),{self.task})
        self.assertIn('New ideas',(self.repo/'TODO.md').read_text())
        self.assertNotEqual(git(self.repo,'status','--porcelain'),'')

    def test_selected_mutation_blocks_monitor_report_and_delivery_before_side_effects(self):
        run = self.start()
        transport.dispatch(self.store,self.identity,self.task)
        before = self.store.load(self.identity); count = len(self.calls)
        self.write(self.original.replace('exact notes','new requirements'))
        operations = [
            lambda: transport.followup(self.store,self.identity,self.task,'Cannot send'),
            lambda: self.report('result',commits=[self.base],tests=['test evidence']),
            lambda: transport.tick(self.store,self.identity),
            lambda: launch.ensure_monitor(self.store,self.identity),
            lambda: native.deliver(self.store,before,'worker',str(uuid.uuid4()),{}),
        ]
        for operation in operations:
            with self.subTest(operation=operation):
                with self.assertRaisesRegex(RuntimeError,'scope'):
                    operation()
                self.assertEqual(self.store.load(self.identity),before)
                self.assertEqual(len(self.calls),count)

    def test_selected_mutation_blocks_dispatch_before_queue_or_session_claim(self):
        self.start(); before = self.store.load(self.identity)
        self.write(self.original.replace('First','Changed'))
        with self.assertRaisesRegex(RuntimeError,'scope'):
            transport.dispatch(self.store,self.identity,self.task)
        self.assertEqual(self.store.load(self.identity),before)
        self.assertFalse(self.calls)
        self.assertFalse((self.store.root/'session-policy').exists())

    def test_selected_mutation_blocks_qa_checkout_acceptance_and_approval(self):
        run = self.start(); transport.dispatch(self.store,self.identity,self.task)
        self.report('result',commits=[self.base],tests=['base evidence'])
        before = self.store.load(self.identity)
        self.write(self.original.replace('First','Changed'))
        with self.assertRaisesRegex(RuntimeError,'scope'):
            transport.review(self.store,self.identity,self.base)
        self.assertEqual(self.cli('accept-result','--task',self.task,'--confirm'),1)
        self.assertEqual(self.cli('approve','--candidate',self.base,'--confirm'),1)
        self.assertEqual(self.store.load(self.identity),before)
        self.assertEqual(git(run['participants']['qa']['worktree'],'rev-parse','HEAD'),self.base)

    def test_unrelated_edits_cannot_bypass_worker_or_qa_cleanliness(self):
        run = self.start(); self.write('# Unrelated\n'+self.original)
        worker = Path(run['participants']['worker']['worktree'])
        (worker/'a.py').write_text('dirty worker')
        with self.assertRaisesRegex(RuntimeError,'clean'):
            transport.dispatch(self.store,self.identity,self.task)
        self.assertFalse(self.calls)
        git(worker,'restore','a.py')
        transport.dispatch(self.store,self.identity,self.task)
        self.report('result',commits=[self.base],tests=['base evidence'])
        qa = Path(run['participants']['qa']['worktree'])
        (qa/'a.py').write_text('dirty QA')
        count = len(self.calls)
        with self.assertRaisesRegex(RuntimeError,'clean'):
            transport.review(self.store,self.identity,self.base)
        self.assertEqual(len(self.calls),count)
        (worker/'a.py').write_text('dirty result')
        self.assertEqual(self.cli('accept-result','--task',self.task,'--confirm'),1)
        self.assertFalse(self.store.load(self.identity)['tasks'][self.task].get('accepted_result'))

    def test_request_rechecks_confirmation_after_native_identity_verification(self):
        snap = Snapshot.read(self.repo)
        self.session.verify = lambda: self.write('# Changed during verification\n'+self.original)
        with self.assertRaisesRegex(RuntimeError,'changed'):
            mission.request(self.session,snap,[snap.tasks[0].id],confirmed=True,store=self.store)
        self.assertFalse(self.calls)
        self.assertFalse(self.store.list(self.repo))

    def test_selected_reordering_keeps_dependency_ids_and_accepted_head_sequencing(self):
        self.start(count=2,dependent=True)
        keys = list(self.run['tasks']); second = keys[1]
        self.write('## Next\n- [ ] Second\n- [ ] New idea\n- [ ] First\n  Keep exact notes.\n')
        with self.assertRaisesRegex(RuntimeError,'dependencies'):
            transport.dispatch(self.store,self.identity,second)
        self.assertFalse(self.calls)
        transport.dispatch(self.store,self.identity,self.task)
        worker = Path(self.run['participants']['worker']['worktree'])
        (worker/'a.py').write_text('print(3)\n')
        git(worker,'add','a.py'); git(worker,'commit','-qm','first task')
        head = git(worker,'rev-parse','HEAD')
        self.report('result',commits=[head],tests=['first task evidence'])
        with self.assertRaisesRegex(RuntimeError,'dependencies'):
            transport.dispatch(self.store,self.identity,second)
        self.assertEqual(self.cli('accept-result','--task',self.task,'--confirm'),0)
        # A fresh executor identity is supplied by the simulated host, as required.
        run = self.store.load(self.identity)
        fresh = dict(run['participants']['worker']['native'],session=str(uuid.uuid4()),pid=223)
        run['participants']['worker'].update(native=fresh,generation=str(uuid.uuid4()))
        self.store.save(run)
        result = transport.dispatch(self.store,self.identity,second)
        payload = self.calls[-1][1].split('\n',1)[1]
        payload = json.loads(payload)
        self.assertEqual(payload['base_sha'],head)
        self.assertEqual(payload['task_id'],second)
        self.assertEqual(payload['dependencies'],[self.task])
        self.assertEqual(set(result['tasks']),set(keys))

    def test_selected_dependency_mutation_blocks_even_first_task_delivery(self):
        self.start(count=2,dependent=True)
        before = self.store.load(self.identity)
        self.write(self.original.replace('Second','Changed dependent task'))
        with self.assertRaisesRegex(RuntimeError,'scope'):
            transport.dispatch(self.store,self.identity,self.task)
        self.assertEqual(self.store.load(self.identity),before)
        self.assertFalse(self.calls)

    def test_invalid_selected_dependencies_never_start_native_resources(self):
        run = self.request(); brief = copy.deepcopy(self.fixture.brief)
        brief.update(transport='native',run_id=run['id'],base_sha=self.base)
        brief['tasks'] = [dict(brief['tasks'][0],id=next(iter(run['tasks'])),dependencies=['unselected'])]
        with self.assertRaisesRegex(RuntimeError,'Dependencies'):
            launch.launch(self.store,run['id'],brief,confirmed=True,api=self.fixture.api)
        self.assertFalse(self.fixture.api.calls)
        self.assertFalse(self.store.load(run['id'])['participants'])

    def test_new_request_overlap_with_legacy_shifted_task_is_conservative_without_migration(self):
        run = self.request(); run.pop('scope'); self.store.save(run)
        before = self.store.path(run['id']).read_bytes()
        self.write('# New idea above old rows\n'+self.original)
        with self.assertRaisesRegex(RuntimeError,'already'):
            self.request()
        self.assertEqual(self.store.path(run['id']).read_bytes(),before)
        self.assertEqual(len(self.calls),1)

    def test_bootstrap_rejects_selected_mutation_before_discovery_or_proof(self):
        self.start(); self.write(self.original.replace('First','Changed'))
        child = SimpleNamespace(poll=lambda: None,pid=os.getpid())
        before = self.store.load(self.identity)
        with patch.object(native.bindings,'discover',side_effect=AssertionError('must not discover')):
            with self.assertRaisesRegex(RuntimeError,'scope'):
                native.bootstrap(self.store,self.identity,'worker',child,timeout=.1)
        self.assertEqual(self.store.load(self.identity),before)
        self.assertFalse((self.store.root/self.identity/'worker-identity.json').exists())

    def test_handoff_with_unrelated_dirty_source_todo_preserves_owned_clean_gates(self):
        self.start()
        new = FakeBinding(session=str(uuid.uuid4()),account=self.session.binding.account,
                          pane='new-main',terminal='new-main-terminal',pid=999)
        target = self.fixture.root/'new-binding.json'
        target.write_text(json.dumps({'repo':str(self.repo),'binding':asdict(new)}))
        capsule = self.fixture.root/'capsule.json'
        self.write('# Unrelated idea\n'+self.original)
        with patch.object(bindings,'project_for',return_value=self.repo):
            handoff.export(self.store,self.identity,capsule)
            offer = handoff.preview(self.store,self.identity,capsule,target)
            (self.repo/'a.py').write_text('dirty source code')
            with self.assertRaisesRegex(RuntimeError,'dirty|scope'):
                handoff.adopt(self.store,self.identity,capsule,target,offer['offer_id'],confirmed=True)
            git(self.repo,'restore','a.py')
            (self.repo/'untracked.py').write_text('untracked source code')
            with self.assertRaisesRegex(RuntimeError,'dirty|scope'):
                handoff.adopt(self.store,self.identity,capsule,target,offer['offer_id'],confirmed=True)
            (self.repo/'untracked.py').unlink()
            worker = Path(self.run['participants']['worker']['worktree'])
            (worker/'a.py').write_text('dirty worker')
            with self.assertRaisesRegex(RuntimeError,'dirty|clean'):
                handoff.adopt(self.store,self.identity,capsule,target,offer['offer_id'],confirmed=True)
            git(worker,'restore','a.py')
            self.write(self.original.replace('First','Changed selected task'))
            with self.assertRaisesRegex(RuntimeError,'scope'):
                handoff.adopt(self.store,self.identity,capsule,target,offer['offer_id'],confirmed=True)
            self.write('# Unrelated idea\n'+self.original)
            result = handoff.adopt(self.store,self.identity,capsule,target,offer['offer_id'],confirmed=True)
            self.assertEqual(result['main'],asdict(new))
        self.assertEqual(self.store.load(self.identity)['scope'],self.run['scope'])

    def test_handoff_rechecks_dirty_source_exception_at_ownership_commit(self):
        self.start()
        new = FakeBinding(session=str(uuid.uuid4()),account=self.session.binding.account,
                          pane='new-main',terminal='new-main-terminal',pid=999)
        target = self.fixture.root/'new-binding.json'
        target.write_text(json.dumps({'repo':str(self.repo),'binding':asdict(new)}))
        capsule = self.fixture.root/'capsule.json'
        self.write('# Unrelated idea\n'+self.original)
        with patch.object(bindings,'project_for',return_value=self.repo):
            handoff.export(self.store,self.identity,capsule)
            offer = handoff.preview(self.store,self.identity,capsule,target)
            before = self.store.load(self.identity)
            verify = native.verify_participant; count = 0
            def race(run,role):
                nonlocal count
                count += 1
                if count == 3:
                    (self.repo/'a.py').write_text('changed during ownership verification')
                return verify(run,role)
            with patch.object(handoff.native,'verify_participant',side_effect=race):
                with self.assertRaisesRegex(RuntimeError,'dirty|scope|Git'):
                    handoff.adopt(self.store,self.identity,capsule,target,offer['offer_id'],confirmed=True)
            self.assertEqual(self.store.load(self.identity),before)
