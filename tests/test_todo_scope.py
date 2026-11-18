import copy
from pathlib import Path
import tempfile
import unittest

from watchdog_app import mission_scope as scope
from watchdog_app.mission import accepted_in_todo
from watchdog_app.tasks_ui import remap
from watchdog_app.todo import Snapshot
from test_todo_format import TEXT, KEY, OTHER, BLOCK
import test_mission_scope as legacy_fixtures
from test_mission_launch import git


class StableScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.snapshot = Snapshot.parse(self.repo, TEXT.encode())
        self.run = {'repo': str(self.repo), 'tasks': {KEY: {'title': self.snapshot.tasks[0].text}},
                    'scope': scope.capture(self.snapshot, self.snapshot.tasks)}

    def parse(self, text):
        return Snapshot.parse(self.repo, text.encode())

    def test_new_scope_pins_stable_id_and_format_and_exact_approved_content(self):
        self.assertEqual(self.run['scope']['version'], 2)
        self.assertEqual(self.run['scope']['format'], 1)
        saved = copy.deepcopy(self.run)
        current = self.parse(TEXT.replace('## Próximo', '# Nota\n\n## Próximo'))
        self.assertEqual(scope.resolve(self.run, current)[KEY].id, KEY)
        self.assertEqual(self.run, saved)

    def test_edits_keep_identity_but_require_explicit_contract_review(self):
        for text in (TEXT.replace('Resolver o áudio', 'Corrigir áudios'),
                     TEXT.replace('Investigar a fila.', 'Apagar a fila.'),
                     TEXT.replace(KEY, OTHER),
                     TEXT.replace('## Próximo', '## Em andamento')):
            with self.subTest(text=text):
                with self.assertRaisesRegex(RuntimeError, 'scope|contrato|identidade'):
                    scope.resolve(self.run, self.parse(text))

    def test_overlap_uses_uuid_even_when_title_and_details_change(self):
        current = self.parse(TEXT.replace('Resolver o áudio', 'Corrigir áudios'))
        new = scope.capture(current, current.tasks)
        self.assertTrue(scope.overlaps(self.run, new, current.tasks))
        self.assertFalse(scope.overlaps(self.run, scope.capture(
            self.parse(TEXT.replace(KEY, OTHER)), self.parse(TEXT.replace(KEY, OTHER)).tasks),
            self.parse(TEXT.replace(KEY, OTHER)).tasks))

    def test_done_acceptance_uses_stable_identity_not_changed_title(self):
        current = self.parse(TEXT.replace('## Próximo', '## Feito')
                             .replace('- [ ] Resolver', '- [x] Resolver')
                             .replace('Resolver o áudio', 'Áudios recuperados'))
        self.assertTrue(accepted_in_todo(self.run, current))
        self.assertFalse(accepted_in_todo(self.run, self.parse(current.raw.decode().replace(KEY, OTHER))))

    def test_remap_keeps_selection_on_move_but_cancels_edited_contract(self):
        self.assertEqual(remap(self.snapshot, self.parse(TEXT.replace('# TODO', '# TODO\nNota')), {KEY}), {KEY})
        self.assertIsNone(remap(self.snapshot, self.parse(TEXT.replace('Investigar', 'Rever')), {KEY}))

    def test_malformed_v2_scope_or_mismatched_embedded_uuid_never_falls_back(self):
        for mutate in ('format', 'id', 'version', 'empty', 'bool'):
            run = copy.deepcopy(self.run)
            if mutate == 'format':
                run['scope']['format'] = 2
            elif mutate == 'id':
                run['scope']['tasks'][KEY]['block'] = BLOCK.replace(KEY, OTHER)
            elif mutate == 'empty':
                run['scope']['tasks'] = {}
            elif mutate == 'bool':
                run['scope']['format'] = True
            else:
                run['scope']['version'] = 9
            with self.subTest(mutate=mutate), self.assertRaisesRegex(RuntimeError, 'scope'):
                scope.resolve(run, self.snapshot)

    def test_legacy_scope_is_not_upgraded_and_migration_requires_new_contract(self):
        snap = self.parse('## Next\n- [ ] Original\n')
        key = snap.tasks[0].id
        run = {'repo': str(self.repo), 'tasks': {key: {'title': snap.tasks[0].text}},
               'scope': scope.capture(snap, snap.tasks)}
        saved = copy.deepcopy(run)
        self.assertEqual(run['scope']['version'], 1)
        scope.resolve(run, self.parse('# Note\n' + snap.raw.decode()))
        with self.assertRaisesRegex(RuntimeError, 'scope|migra'):
            scope.resolve(run, self.snapshot)
        self.assertEqual(run, saved)


class StableRunIntegrationTests(unittest.TestCase):
    """Real temporary Git/run storage; only model and host identities are fixtures."""
    def setUp(self):
        fixture = legacy_fixtures.ScopeTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        fixture.write(TEXT)
        git(fixture.repo, 'add', 'TODO.md')
        git(fixture.repo, 'commit', '-qm', 'versioned TODO')
        fixture.base = git(fixture.repo, 'rev-parse', 'HEAD')

    def test_request_launch_dispatch_preserves_uuid_and_full_technical_content(self):
        f = self.fixture
        run = f.start()
        self.assertEqual(set(run['tasks']), {KEY})
        self.assertEqual(run['scope']['version'], 2)
        self.assertIn('    - [ ] Verificar', run['tasks'][KEY]['title'])
        self.assertIn('Aceite:', run['tasks'][KEY]['title'])
        before = copy.deepcopy(run)
        f.write(TEXT.replace('Investigar', 'Apagar'))
        with self.assertRaisesRegex(RuntimeError, 'scope'):
            legacy_fixtures.transport.dispatch(f.store, f.identity, KEY)
        self.assertEqual(f.store.load(f.identity), before)
        self.assertFalse(f.calls)
        f.write(TEXT)
        legacy_fixtures.transport.dispatch(f.store, f.identity, KEY)
        payload = f.calls[-1][1]
        self.assertIn(KEY, payload)
        self.assertIn('Demonstrar recuperação', payload)
        self.assertEqual(f.store.load(f.identity)['tasks'][KEY]['state'], 'working')
