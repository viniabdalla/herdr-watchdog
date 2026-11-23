import tempfile
import os
from unittest.mock import patch
from pathlib import Path
import unittest
from watchdog_app import project_instructions as pi

class InstructionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.repo=Path(self.tmp.name)
        env=patch.dict(os.environ,{"WATCHDOG_STATE_DIR":str(self.repo/"state")});env.start();self.addCleanup(env.stop)
    def test_preview_apply_preserves_bytes_and_is_idempotent(self):
        original=b'# Rules\r\nUser rules stay byte-for-byte.\r\n'
        (self.repo/'AGENTS.md').write_bytes(original)
        plan=pi.preview(self.repo)
        self.assertIn('+',plan['files'][0]['diff'])
        self.assertFalse((self.repo/'CLAUDE.md').exists())
        with self.assertRaises(RuntimeError):pi.apply(self.repo,plan,confirmed=False)
        pi.apply(self.repo,plan,confirmed=True)
        self.assertTrue((self.repo/'AGENTS.md').read_bytes().startswith(original))
        self.assertEqual(pi.check(self.repo)['status'],'current')
        again=pi.preview(self.repo);pi.apply(self.repo,again,confirmed=True)
        self.assertTrue(all(not f['diff'] for f in again['files']))
        self.assertEqual(again['agent_reading'],'manual-unobserved')
    def test_stale_or_forged_preview_refused(self):
        plan=pi.preview(self.repo)
        (self.repo/'CLAUDE.md').write_text('new user rule')
        with self.assertRaises(RuntimeError):pi.apply(self.repo,plan,confirmed=True)
        self.assertFalse((self.repo/'AGENTS.md').exists())
        plan=pi.preview(self.repo);plan['files'][0]['after']='malicious'
        with self.assertRaises(RuntimeError):pi.apply(self.repo,plan,confirmed=True)
    def test_markers_symlinks_conflicts_refused(self):
        for text in [pi.BEGIN,pi.END+pi.BEGIN,pi.BEGIN+'\n'+pi.BEGIN+'\n'+pi.END,
                     '<!-- watchdog-todo:broken -->']:
            (self.repo/'AGENTS.md').write_text(text)
            with self.assertRaises(RuntimeError):pi.preview(self.repo)
        (self.repo/'AGENTS.md').unlink();(self.repo/'AGENTS.md').symlink_to('/tmp/no-rule')
        with self.assertRaises(RuntimeError):pi.preview(self.repo)
    def test_outdated_replaces_only_managed_body(self):
        (self.repo/'AGENTS.md').write_text('before\n'+pi.BEGIN+'\nold\n'+pi.END+'\nafter')
        self.assertEqual(pi.check(self.repo)['status'],'outdated')
        plan=pi.preview(self.repo);pi.apply(self.repo,plan,confirmed=True)
        data=(self.repo/'AGENTS.md').read_text()
        self.assertTrue(data.startswith('before\n'+pi.BEGIN));self.assertTrue(data.endswith(pi.END+'\nafter'))

    def test_unmanaged_conflicting_copy_and_fenced_markers_are_refused(self):
        for text in ['Watchdog TODO instructions v0\nexisting unmanaged rules',
                     '```\n'+pi.BEGIN+'\nold\n'+pi.END+'\n```']:
            (self.repo/'AGENTS.md').write_text(text)
            with self.assertRaises(RuntimeError):pi.preview(self.repo)

    def test_concurrent_editor_is_not_overwritten_during_exchange(self):
        (self.repo/'AGENTS.md').write_text('user rules\n')
        plan=pi.preview(self.repo);original=pi.exchange;calls=[]
        def race(source,target):
            if not calls:
                calls.append(True);Path(target).write_text('concurrent rules\n')
            return original(source,target)
        with patch.object(pi,'exchange',side_effect=race):
            with self.assertRaises(RuntimeError):pi.apply(self.repo,plan,confirmed=True)
        self.assertEqual((self.repo/'AGENTS.md').read_text(),'concurrent rules\n')
        self.assertFalse((self.repo/'CLAUDE.md').exists())
