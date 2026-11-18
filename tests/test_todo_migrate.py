import copy
from pathlib import Path
import tempfile
import unittest
import uuid
from unittest.mock import patch

from watchdog_app import todo_migrate as migrate
from watchdog_app.mission import RunStore
from watchdog_app.todo import Snapshot
from test_todo_format import TEXT, KEY, OTHER


LEGACY = ('---\nstatus: ativo\n---\n# Tarefas\n\n## Próximo\n'
          '- [ ] Resolver áudios\n  Resumo: Continuar o atendimento.\n'
          '  Preservar a fila.\n  Aceite: Recuperar áudios com evidência.\n'
          '\n## Feito\n- [x] 2026-11-17 Correção aprovada abc123\n  Evidência literal.\n'
          '\n## Notas\nNão remover esta nota.\n```md\n- [ ] Somente exemplo\n```\n')


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / 'repo'
        self.repo.mkdir()
        self.state = Path(self.temp.name) / 'state'
        self.store = RunStore(self.state / 'runs')
        self.write(LEGACY)

    def write(self, text):
        (self.repo / 'TODO.md').write_bytes(text.encode())
        return Snapshot.read(self.repo)

    def preview(self, **kwargs):
        return migrate.preview(Snapshot.read(self.repo), store=self.store, **kwargs)

    def apply(self, proposal, confirmed=True):
        return migrate.apply(Snapshot.read(self.repo), proposal, store=self.store,
                             root=self.state, confirmed=confirmed)

    def run_record(self, phase='active', tasks=None):
        run = {'id': str(uuid.uuid4()), 'repo': str(self.repo), 'created': 1,
               'phase': phase, 'tasks': tasks or {Snapshot.read(self.repo).tasks[0].id: {}}}
        self.store.save(run)
        return run

    def test_preview_is_read_only_and_migration_preserves_history_notes_and_mapping(self):
        before = (self.repo / 'TODO.md').read_bytes()
        proposal = self.preview()
        self.assertEqual((self.repo / 'TODO.md').read_bytes(), before)
        self.assertEqual(proposal['kind'], 'legacy')
        self.assertEqual(len(proposal['tasks']), 1)
        result = self.apply(proposal)
        self.assertEqual(result.format_version, 1)
        self.assertEqual(len(result.tasks), 2)
        task, history = result.tasks
        self.assertEqual(task.id, proposal['tasks'][0]['id'])
        self.assertEqual(task.summary, 'Continuar o atendimento.')
        self.assertEqual(task.origin, 'legado-nao-confirmado')
        self.assertIn('Preservar a fila.', task.execution)
        self.assertIn('Recuperar áudios', task.acceptance)
        self.assertTrue(history.historical)
        self.assertTrue(history.done)
        self.assertIn('- [x] 2026-11-17 Correção aprovada abc123\n  Evidência literal.\n', result.raw.decode())
        self.assertIn('Não remover esta nota.', result.raw.decode())
        self.assertEqual(result.migrations[0]['source_digest'], proposal['source_digest'])
        self.assertEqual(result.migrations[0]['ids'], {proposal['tasks'][0]['old_id']: task.id})
        backups = list((self.state / 'todo-backups').rglob('*.md'))
        self.assertTrue(any(p.read_bytes() == before for p in backups))

    def test_missing_fields_are_not_invented_and_can_be_filled_explicitly(self):
        self.write('## Next\n- [ ] Investigar\n')
        proposal = self.preview()
        task = proposal['tasks'][0]
        self.assertEqual(task['summary'], '')
        self.assertEqual(task['acceptance'], '')
        with self.assertRaisesRegex(RuntimeError, 'Resumo|campo'):
            self.apply(proposal)
        task.update(summary='Identificar o defeito para recuperar o serviço.',
                    execution='Reproduzir e diagnosticar.', acceptance='Demonstrar a causa com evidência.')
        self.assertEqual(self.apply(proposal).tasks[0].summary, task['summary'])

    def test_confirmation_and_exact_source_and_project_are_required(self):
        proposal = self.preview()
        before = (self.repo / 'TODO.md').read_bytes()
        with self.assertRaisesRegex(RuntimeError, 'confirm'):
            self.apply(proposal, False)
        for field, value in [('repo', '/another/project'), ('source_digest', '0' * 64),
                             ('version', 2), ('original', 'different')]:
            changed = copy.deepcopy(proposal)
            changed[field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.apply(changed)
        self.assertEqual((self.repo / 'TODO.md').read_bytes(), before)

    def test_unfinished_runs_block_migration_and_their_bytes_never_change(self):
        proposal = self.preview()
        for phase in ('requested', 'launching', 'active', 'blocked'):
            run = self.run_record(phase)
            path = self.store.path(run['id'])
            before = path.read_bytes()
            with self.assertRaisesRegex(RuntimeError, run['id']):
                self.apply(proposal)
            self.assertEqual(path.read_bytes(), before)
            run['phase'] = 'closed'
            self.store.save(run)
        result = self.apply(proposal)
        self.assertEqual(result.format_version, 1)

    def test_concurrent_edit_after_preview_prevents_any_write(self):
        proposal = self.preview()
        snap = self.write(LEGACY + '\nNova nota\n')
        with self.assertRaisesRegex(RuntimeError, 'changed|alterad|origem'):
            self.apply(proposal)
        self.assertEqual((self.repo / 'TODO.md').read_bytes(), snap.raw)

    def test_migration_refuses_lost_details_duplicate_ids_or_removed_tasks(self):
        for mutation in ('details', 'id', 'remove', 'unknown'):
            proposal = self.preview()
            if mutation == 'details':
                proposal['tasks'][0]['execution'] = 'Apagar conteúdo anterior'
            elif mutation == 'id':
                proposal['tasks'][0]['id'] = 'wrong'
            elif mutation == 'remove':
                proposal['tasks'] = []
            else:
                proposal['tasks'][0]['unexpected'] = 'ignored?'
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                self.apply(proposal)

    def test_identity_change_is_explicit_logged_and_blocks_affected_live_runs(self):
        self.write(TEXT)
        with self.assertRaisesRegex(RuntimeError, 'identidade|ID|migrado'):
            self.preview()
        proposal = self.preview(task_id=KEY, new_id=OTHER)
        self.assertEqual(proposal['kind'], 'identity')
        run = self.run_record(tasks={KEY: {}})
        run['scope'] = {'version': 2}
        self.store.save(run)
        with self.assertRaisesRegex(RuntimeError, run['id']):
            self.apply(proposal)
        run['phase'] = 'closed'
        self.store.save(run)
        result = self.apply(proposal)
        self.assertEqual(result.tasks[0].id, OTHER)
        self.assertEqual(result.tasks[0].title, 'Resolver o áudio')
        self.assertEqual(result.migrations[-1]['ids'], {KEY: OTHER})
        with self.assertRaisesRegex(RuntimeError, 'aposentado|identidade'):
            migrate.preview(result, task_id=OTHER, new_id=KEY, store=self.store)

    def test_stale_selection_and_save_race_remain_protected(self):
        proposal = self.preview()
        snapshot = Snapshot.read(self.repo)
        real = __import__('watchdog_app.todo', fromlist=['exchange']).exchange
        competing = LEGACY + '\nEdição concorrente\n'
        calls = []
        def race(source, target):
            if not calls:
                calls.append(True)
                target.write_text(competing)
            return real(source, target)
        with patch('watchdog_app.todo.exchange', side_effect=race):
            with self.assertRaisesRegex(RuntimeError, 'changed'):
                migrate.apply(snapshot, proposal, confirmed=True, store=self.store, root=self.state)
        self.assertEqual((self.repo / 'TODO.md').read_text(), competing)

    def test_crlf_and_no_final_newline_are_preserved_in_backup(self):
        for original in (LEGACY.replace('\n', '\r\n'), LEGACY.rstrip('\n')):
            self.write(original)
            snap = Snapshot.read(self.repo)
            result = self.apply(self.preview())
            self.assertEqual(len(result.tasks), 2)
            self.assertEqual((self.state / 'todo-backups' /
                __import__('hashlib').sha256(str(self.repo).encode()).hexdigest() /
                (snap.digest + '.md')).read_bytes(), original.encode())
