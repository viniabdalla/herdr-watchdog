import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from watchdog_app import long_run
from watchdog_app.progress_ui import rows
from watchdog_app.todo import Snapshot, change
from watchdog_app.todo_format import render


class LongRunTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.repo = Path(folder.name)
        self.file = self.repo / 'TODO.md'
        env = patch.dict(os.environ, WATCHDOG_STATE_DIR=str(self.repo / 'state'))
        env.start()
        self.addCleanup(env.stop)
        self.file.write_text('## Next\n- [ ] T2 — Worker (#3)\n- [ ] Outra tarefa\n## Done\n')

    def select(self):
        snapshot = Snapshot.read(self.repo)
        long_run.save(snapshot, [task.id for task in snapshot.tasks])

    def test_project_bar_is_first_until_group_is_selected(self):
        self.file.write_text('## Next\n- [ ] A\n- [ ] B\n## Done\n- [x] C\n- [x] D\n')
        def lines():
            return [line for line, _, _ in rows(self.repo, width=30)]
        project = 'Projeto · 2 de 4 concluídas'
        self.assertEqual(lines()[0], project)
        self.assertRegex(lines()[1], r'^\[█+░+\] 50%$')
        snapshot = Snapshot.read(self.repo)
        long_run.save(snapshot, [snapshot.tasks[0].id])
        rendered = lines()
        self.assertEqual(rendered[0], 'Long run')
        self.assertRegex(rendered[2], r'^\[░+\]$')
        self.assertEqual(rendered[4], project)
        self.assertRegex(rendered[5], r'^\[█+░+\] 50%$')
        self.assertLessEqual(len(rendered[5]), 28)

    def test_empty_project_has_empty_bar(self):
        self.file.write_text('## Next\n')
        rendered = [line for line, _, _ in rows(self.repo)]
        self.assertEqual(rendered[0], 'Projeto · nenhuma tarefa')
        self.assertRegex(rendered[1], r'^\[░+\]$')

    def test_persistent_fixed_group_survives_done_reorder_and_reopening(self):
        self.select()
        self.file.write_text('## Next\n- [ ] Nova\n- [ ] Outra tarefa\n## Done\n'
                             '- [x] 2026-11-25 T2 (#3) Worker verificado\n')
        def progress():
            return '\n'.join(line for line, _, _ in rows(self.repo))
        self.assertIn('1 de 2 concluídas · 50% · falta 1', progress())
        snapshot = Snapshot.read(self.repo)
        change(snapshot, [{'kind': 'done', 'id': snapshot.tasks[1].id}])
        self.assertIn('2 de 2 concluídas · 100% · faltam 0', progress())
        self.file.write_text('## Next\n- [ ] Outra tarefa\n- [ ] Nova\n## Done\n'
                             '- [x] T2 (#3) Worker verificado\n')
        self.assertIn('1 de 2 concluídas · 50%', progress())

    def test_ambiguous_or_missing_task_never_inflates_completion(self):
        self.select()
        self.file.write_text('## Done\n- [x] Outra tarefa\n- [x] Outra tarefa\n')
        lines = '\n'.join(line for line, _, _ in rows(self.repo))
        self.assertIn('0 de 2 concluídas', lines)
        self.assertIn('2 sem correspondência única', lines)
        sibling = self.repo / 'sibling'
        sibling.mkdir()
        self.assertIsNone(long_run.load(sibling))

    def test_ambiguous_replacement_keeps_previous_group(self):
        self.select()
        previous = long_run.load(self.repo)
        self.file.write_text('## Next\n- [ ] Igual\n- [ ] Igual\n')
        snapshot = Snapshot.read(self.repo)
        with self.assertRaisesRegex(RuntimeError, 'ambígu'):
            long_run.save(snapshot, [snapshot.tasks[0].id])
        self.assertEqual(previous, long_run.load(self.repo))

    def test_uuid_keeps_renamed_task_and_does_not_match_reused_title(self):
        values = dict(id='9f4cdfb9-3b30-4d69-a178-aa3ff61301a6', summary='Resumo',
                      execution='Detalhes', origin='pedido-humano', acceptance='Aceite')
        header = '---\nwatchdog_todo: 1\n---\n'
        self.file.write_text(header + '## Next\n' + render('Original', values))
        self.select()
        another = dict(values, id='e3baa94c-fb87-4c53-b688-70d38c5c8263')
        self.file.write_text(header + '## Next\n' + render('Original', another)
                             + '## Done\n' + render('Alterada', values, done=True))
        self.assertTrue(any('1 de 1' in line and '100%' in line for line, _, _ in rows(self.repo)))
