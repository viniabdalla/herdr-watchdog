"""Isolated preparation: issue #42 lines 16-23; research lines 8-10, 108-121.

Point A: preview/confirmation. Point B: resulting files and preservation.
"""
import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from watchdog_app import project_instructions as pi


class TodoSetupTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name) / 'project'
        self.repo.mkdir()
        env = patch.dict(os.environ, WATCHDOG_STATE_DIR=str(Path(tmp.name) / 'state'))
        env.start()
        self.addCleanup(env.stop)

    def tracker(self, text='# Tracker\n\n## When a skill says "publish to the issue tracker"\n\nPublish here.\n\n## Other\n\nKeep this.\n'):
        path = self.repo / 'docs/agents/issue-tracker.md'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def test_preview_and_confirmation_create_only_missing_rules(self):
        # #42:19; research:8-10,110-121: missing rule + embedded portable skeleton.
        tracker = self.tracker()
        plan = pi.preview(self.repo)
        self.assertFalse((self.repo / 'AGENTS.md').exists())
        self.assertFalse((self.repo / 'docs/agents/todo.md').exists())
        with self.assertRaises(RuntimeError):
            pi.apply(self.repo, plan)
        pi.apply(self.repo, plan, confirmed=True)
        agents = (self.repo / 'AGENTS.md').read_text()
        self.assertIn('## Agent skills\n', agents)
        self.assertIn('### TODO\n', agents)
        self.assertIn('See `docs/agents/todo.md`', agents)
        rule = (self.repo / 'docs/agents/todo.md').read_text()
        self.assertIn('watchdog_todo: 1', rule)
        self.assertIn('## Próximo', rule)
        self.assertNotIn('/home/tropico/', rule)
        self.assertFalse((self.repo / 'TODO.md').exists())
        self.assertLess(tracker.read_text().index('Depois de publicar'), tracker.read_text().index('## Other'))
        again = pi.preview(self.repo)
        self.assertTrue(all(not f['diff'] for f in again['files']))

    def test_existing_sections_preserved_and_missing_sections_appended(self):
        # #42:20; research:9: preserve custom text, install pointer in Agent skills.
        agents = b'# Custom\r\n\r\n## Agent skills\r\n\r\n### Other\r\nCustom rule.\r\n\r\n## Dispatch\r\nNever change.\r\n'
        (self.repo / 'AGENTS.md').write_bytes(agents)
        tracker = self.tracker()
        original = tracker.read_text()
        rule = self.repo / 'docs/agents/todo.md'
        rule.write_text('# Custom TODO\n\n## Manutenção\n\nMy maintenance.\n')
        pi.apply(self.repo, pi.preview(self.repo), confirmed=True)
        installed = (self.repo / 'AGENTS.md').read_bytes()
        self.assertIn(b'### TODO', installed)
        self.assertLess(installed.index(b'### TODO'), installed.index(b'## Dispatch'))
        self.assertIn(b'Never change.\r\n', installed)
        data = rule.read_text()
        self.assertTrue(data.startswith('# Custom TODO\n\n## Manutenção\n\nMy maintenance.\n'))
        self.assertEqual(data.count('## Manutenção'), 1)
        self.assertIn('## Quem cria e quando', data)
        self.assertIn('Publish here.', tracker.read_text())
        self.assertTrue(tracker.read_text().endswith(original[original.index('## Other'):]))

    def test_missing_tracker_warns_in_json_and_human_output_without_creating_it(self):
        # #42:21: missing tracker must remain missing; warn to use setup skill.
        plan = pi.preview(self.repo)
        self.assertIn('/setup-matt-pocock-skills', ' '.join(plan.get('warnings', [])))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(pi.main(['preview', '--repo', str(self.repo), '--human']), 0)
        self.assertIn('/setup-matt-pocock-skills', output.getvalue())
        pi.apply(self.repo, plan, confirmed=True)
        self.assertFalse((self.repo / 'docs/agents/issue-tracker.md').exists())

    def test_stale_tracker_and_symlinked_docs_refused_before_writes(self):
        # #42:20: preservation includes concurrent edits and indirect paths.
        tracker = self.tracker()
        plan = pi.preview(self.repo)
        tracker.write_text('Edited while preview was open.\n')
        with self.assertRaises(RuntimeError):
            pi.apply(self.repo, plan, confirmed=True)
        self.assertFalse((self.repo / 'AGENTS.md').exists())
        tracker.unlink()
        (self.repo / 'docs/agents').rmdir()
        (self.repo / 'docs').rmdir()
        outside = self.repo.parent / 'outside'
        outside.mkdir()
        (self.repo / 'docs').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(RuntimeError):
            pi.preview(self.repo)
        self.assertEqual(list(outside.iterdir()), [])

    def test_custom_existing_todo_pointer_and_trigger_section_are_preserved(self):
        # #42:20; research:110-121: do not replace custom existing sections.
        original = '# Rules\n\n## Agent skills\n\n### TODO\n\nCustom TODO: docs/agents/todo.md.\n'
        (self.repo / 'AGENTS.md').write_text(original)
        tracker = self.tracker('# Tracker\n\n## Custom tracker\nPreserve me.\n')
        pi.apply(self.repo, pi.preview(self.repo), confirmed=True)
        agents = (self.repo / 'AGENTS.md').read_text()
        self.assertTrue(agents.startswith(original))
        self.assertEqual(agents.count('### TODO'), 1)
        self.assertTrue(tracker.read_text().startswith('# Tracker\n\n## Custom tracker\nPreserve me.\n'))
        self.assertIn('## When a skill says "publish to the issue tracker"', tracker.read_text())
        self.assertIn('Depois de publicar os tickets', tracker.read_text())
        self.assertEqual(pi.check(self.repo)['status'], 'current')

    def test_new_tracker_after_preview_requires_fresh_confirmation(self):
        # #42:19-21: changed scope needs a fresh preview before any creation.
        plan = pi.preview(self.repo)
        self.tracker()
        with self.assertRaises(RuntimeError):
            pi.apply(self.repo, plan, confirmed=True)
        self.assertFalse((self.repo / 'AGENTS.md').exists())

    def test_mixed_newlines_in_existing_sections_remain_byte_exact(self):
        # #42:20: adding missing sections must preserve even mixed user newlines.
        original = b'# Custom\r\nOne LF here.\n'
        rule = self.repo / 'docs/agents/todo.md'
        self.tracker()
        rule.write_bytes(original)
        pi.apply(self.repo, pi.preview(self.repo), confirmed=True)
        self.assertTrue(rule.read_bytes().startswith(original))
