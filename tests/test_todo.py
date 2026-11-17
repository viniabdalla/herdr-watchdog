from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from watchdog_app.todo import Snapshot, change


TEXT = ('---\nstatus: ativo\natualizado: 2026-11-16\n---\n# TODO\n\n'
        '## Em andamento\n- [ ] Work already started\n\n'
        '## Próximo\n- [ ] Add task colors\n  Preserve this continuation.\n'
        '- [ ] Check login\n\n## Bloqueado\n\n## Feito\n- [x] Existing completion\n'
        '\n## Notes\nKeep this paragraph.\n```md\n## Next\n- [ ] Example only\n```\n')


class TodoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        (self.repo / 'TODO.md').write_text(TEXT)
        self.state = self.repo / 'state'

    def test_completion_preserves_metadata_notes_and_continuations(self):
        before = Snapshot.read(self.repo)
        self.assertEqual(len(before.tasks), 4)
        task = next(t for t in before.tasks if t.text.startswith('Add task colors'))
        after = change(before, [{'kind': 'done', 'id': task.id}], self.state)
        moved = next(t for t in after.tasks if 'Add task colors' in t.text)
        self.assertTrue(moved.done)
        self.assertEqual(moved.section, 'Done')
        content = (self.repo / 'TODO.md').read_text()
        self.assertIn('status: ativo', content)
        self.assertIn('Keep this paragraph.', content)
        self.assertIn('  Preserve this continuation.', content)
        self.assertIn('- [ ] Example only', content)
        self.assertTrue(list((self.state / 'todo-backups').rglob('*.md')))

    def test_blocked_reason_moves_task_to_blocked_section(self):
        before = Snapshot.read(self.repo)
        task = next(t for t in before.tasks if t.text == 'Check login')
        after = change(before, [{'kind': 'blocked', 'id': task.id, 'reason': 'Codex login expired'}], self.state)
        task = next(t for t in after.tasks if t.text.startswith('Check login'))
        self.assertEqual(task.section, 'Blocked')
        self.assertIn('Codex login expired', task.text)
        self.assertFalse(task.done)

    def test_external_edit_prevents_any_write(self):
        before = Snapshot.read(self.repo)
        path = self.repo / 'TODO.md'
        path.write_text(TEXT + '\nUser edit\n')
        expected = path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, 'changed'):
            change(before, [{'kind': 'done', 'id': before.tasks[0].id}], self.state)
        self.assertEqual(path.read_bytes(), expected)

    def test_conflicting_actions_and_completed_selection_are_rejected(self):
        before = Snapshot.read(self.repo)
        with self.assertRaises(RuntimeError):
            change(before, [{'kind': 'done', 'id': before.tasks[0].id},
                            {'kind': 'blocked', 'id': before.tasks[0].id, 'reason': 'wait'}], self.state)
        with self.assertRaises(RuntimeError):
            change(before, [{'kind': 'done', 'id': before.tasks[-1].id}], self.state)
        self.assertEqual((self.repo / 'TODO.md').read_text(), TEXT)

    def test_addition_cannot_inject_markdown_sections_or_reopen_same_title(self):
        before = Snapshot.read(self.repo)
        for text in ('New task\n## Done\n- [x] Injected', 'Existing completion'):
            with self.subTest(text=text), self.assertRaises(RuntimeError):
                change(before, [{'kind': 'add', 'text': text}], self.state)

    def test_todo_symlink_cannot_write_another_file(self):
        (self.repo / 'TODO.md').unlink()
        other = self.repo / 'other.md'
        other.write_text(TEXT)
        (self.repo / 'TODO.md').symlink_to(other)
        with self.assertRaisesRegex(RuntimeError, 'symlink'):
            Snapshot.read(self.repo)

    def test_crlf_and_nonmetadata_prose_are_preserved(self):
        text = TEXT + '\natualizado: this is unrelated prose\n'
        (self.repo / 'TODO.md').write_bytes(text.replace('\n', '\r\n').encode())
        before = Snapshot.read(self.repo)
        change(before, [{'kind': 'start', 'id': before.tasks[1].id}], self.state)
        raw = (self.repo / 'TODO.md').read_bytes()
        self.assertNotIn(b'\n', raw.replace(b'\r\n', b''))
        self.assertIn(b'atualizado: this is unrelated prose', raw)

    def test_completion_after_a_heading_without_final_newline_keeps_task(self):
        (self.repo / 'TODO.md').write_text('## Next\n- [ ] Keep me\n\n## Done')
        before = Snapshot.read(self.repo)
        after = change(before, [{'kind': 'done', 'id': before.tasks[0].id}], self.state)
        self.assertEqual(len(after.tasks), 1)
        self.assertTrue(after.tasks[0].done)
        self.assertIn('Keep me', after.tasks[0].text)

    def test_edit_arriving_at_commit_is_preserved_and_reported(self):
        from watchdog_app import todo
        path = self.repo / 'TODO.md';snapshot = Snapshot.read(self.repo)
        external = TEXT + '\nLast-moment external edit\n'
        real = todo.exchange
        injected = []
        def competing_save(source, target):
            if not injected:
                path.write_text(external);injected.append(True)
            return real(source, target)
        with patch.object(todo, 'exchange', side_effect=competing_save):
            with self.assertRaisesRegex(RuntimeError, 'changed'):
                change(snapshot, [{'kind': 'done', 'id': snapshot.tasks[0].id}], self.state)
        self.assertEqual(path.read_text(), external)
        self.assertTrue(any(p.read_text()==external for p in (self.state/'todo-backups').rglob('*.md')))

    def test_second_editor_save_during_rollback_is_retained(self):
        from watchdog_app import todo
        path = self.repo / 'TODO.md';snapshot = Snapshot.read(self.repo)
        first = TEXT + '\nFirst competing save\n'
        latest = TEXT + '\nSecond competing save\n'
        real = todo.exchange
        calls = []
        def competing_save(source, target):
            calls.append(True)
            if len(calls) == 1: path.write_text(first)
            if len(calls) == 2: path.write_text(latest)
            return real(source, target)
        with patch.object(todo, 'exchange', side_effect=competing_save):
            with self.assertRaisesRegex(RuntimeError, 'changed'):
                change(snapshot, [{'kind': 'done', 'id': snapshot.tasks[0].id}], self.state)
        self.assertEqual(path.read_text(), latest)
        versions = [p.read_text() for p in (self.state/'todo-backups').rglob('*.md')]
        self.assertIn(first, versions)
        self.assertIn(latest, versions)
