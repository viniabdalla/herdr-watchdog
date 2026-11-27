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
        self.assertTrue(data.startswith('before\n'+pi.BEGIN));self.assertIn(pi.END+'\nafter',data)

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

    def test_unclosed_fences_in_either_file_refuse_preview_without_mutations(self):
        for name in pi.NAMES:
            other=next(item for item in pi.NAMES if item!=name)
            for fence in ('```text','~~~text','````python','~~~~'):
                with self.subTest(name=name,fence=fence):
                    for item in pi.NAMES:(self.repo/item).unlink(missing_ok=True)
                    raw=('# Rules\n'+fence+'\nexample left open\n').encode()
                    (self.repo/name).write_bytes(raw)
                    with self.assertRaises(RuntimeError):pi.preview(self.repo)
                    self.assertEqual((self.repo/name).read_bytes(),raw)
                    self.assertFalse((self.repo/other).exists())

    def test_unsafe_old_or_tampered_preview_fails_before_any_file_write(self):
        import difflib
        import copy
        for name in pi.NAMES:
            other=next(item for item in pi.NAMES if item!=name)
            for fence in ('```text','~~~text'):
                for payload in ('old','tampered'):
                    with self.subTest(name=name,fence=fence,payload=payload):
                        for item in pi.NAMES:(self.repo/item).unlink(missing_ok=True)
                        stale=pi.preview(self.repo)
                        raw=('# Rules\n'+fence+'\nexample left open\n').encode()
                        (self.repo/name).write_bytes(raw)
                        # Shape of a preview emitted by the old unsafe append path.
                        plan=copy.deepcopy(stale)
                        entry=next(item for item in plan['files'] if item['path']==name)
                        after=raw.decode()+entry['after']
                        entry.update(before_hash=pi.digest(raw),after=after,after_hash=pi.digest(after.encode()),status='outdated',
                            diff=''.join(difflib.unified_diff(raw.decode().splitlines(True),after.splitlines(True),fromfile=name,tofile=name)))
                        if payload=='tampered':plan['files'][0]['after']+='tampered'
                        with self.assertRaises(RuntimeError):pi.apply(self.repo,plan,confirmed=True)
                        self.assertEqual((self.repo/name).read_bytes(),raw)
                        self.assertFalse((self.repo/other).exists())

    def test_closed_fences_are_preserved_and_managed_context_must_stay_outside(self):
        for name in pi.NAMES:
            for fence in ('```','~~~'):
                with self.subTest(name=name,fence=fence):
                    for item in pi.NAMES:(self.repo/item).unlink(missing_ok=True)
                    raw=('# Rules\n'+fence+'text\nexample\n'+fence+'\n').encode()
                    (self.repo/name).write_bytes(raw);plan=pi.preview(self.repo)
                    pi.apply(self.repo,plan,confirmed=True)
                    self.assertTrue((self.repo/name).read_bytes().startswith(raw))
                    self.assertEqual(pi.check(self.repo)['status'],'current')
                    invalid=raw+fence.encode()+b'\n'+pi.BEGIN.encode()+b'\nold\n'+pi.END.encode()+b'\n'+fence.encode()+b'\n'
                    (self.repo/name).write_bytes(invalid)
                    with self.assertRaises(RuntimeError):pi.preview(self.repo)
                    self.assertEqual((self.repo/name).read_bytes(),invalid)
