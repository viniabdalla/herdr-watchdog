"""Religar spec L24-26,38,40: file locking and Windows launch boundaries."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch


class PlatformCompatTests(unittest.TestCase):
    def test_windows_lock_starts_at_same_byte_and_maps_contention(self):
        from watchdog_app import compat
        native=Mock(LK_NBLCK=2,LK_NBRLCK=3,LK_UNLCK=0,LK_LOCK=1,LK_RLCK=4)
        with tempfile.TemporaryFile('a+') as stream, patch.object(compat,'_windows',True), patch.object(compat,'_msvcrt',native):
            stream.write('abc');stream.flush()
            compat.flock(stream,compat.LOCK_EX|compat.LOCK_NB)
            self.assertEqual(stream.tell(),0)
            native.locking.assert_called_once_with(stream.fileno(),2,1)
            native.locking.side_effect=OSError(13,'busy')
            with self.assertRaises(BlockingIOError):compat.flock(stream,compat.LOCK_EX|compat.LOCK_NB)

    def test_windows_directory_sync_is_skipped(self):
        from watchdog_app import compat
        with patch.object(compat,'_windows',True),patch.object(compat.os,'open') as opened:
            compat.fsync_directory(Path('/not-opened'))
            opened.assert_not_called()

    def test_manifest_covers_all_platforms_and_bootstraps_dependencies(self):
        import re
        root=Path(__file__).resolve().parents[1]
        text=(root/'herdr-plugin.toml').read_text()
        self.assertIn('platforms = ["linux", "macos", "windows"]',text)
        commands=re.findall(r'^command = (.+)$',text,re.M)
        self.assertEqual(len(commands),6)
        for command in commands[1:]:
            self.assertIn('plugin-boot.py',command)

    def test_windows_command_quoting_preserves_paths_with_spaces(self):
        from watchdog_app.compat import shell_command
        self.assertEqual(shell_command(['C:\\Program Files\\Python\\python.exe','C:\\My App\\watchdog','panel','tasks'],windows=True), '& "C:\\Program Files\\Python\\python.exe" "C:\\My App\\watchdog" "panel" "tasks"')

    def test_tasks_start_without_sighup(self):
        # L24-26,38: Windows must reach the curses Tasks entry.
        from types import SimpleNamespace
        from watchdog_app import tasks_ui
        signals=SimpleNamespace(SIGTERM=15,signal=Mock())
        with patch.object(tasks_ui,'signal',signals),patch.object(tasks_ui.curses,'wrapper') as wrapper:
            tasks_ui.run(Path('/temporary'))
            wrapper.assert_called_once()
            signals.signal.assert_called_once()

    def test_atomic_windows_writes_and_reopens_state(self):
        # L18,26,40: no O_DIRECTORY requirement on Windows save path.
        from watchdog_app import compat
        from watchdog_app.store import atomic
        import json
        with tempfile.TemporaryDirectory() as tmp,patch.object(compat,'_windows',True):
            file=Path(tmp)/'binding.json'
            atomic(file,{'session':'B'})
            self.assertEqual(json.loads(file.read_text()),{'session':'B'})

    def test_transcript_read_without_unix_open_flags(self):
        # L12,24-26: Progress/Tasks must reopen native history on Windows.
        from watchdog_app.transcripts import Reader,evidence_tail
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'history.jsonl';file.write_text('{"type":"session_meta"}\n')
            with patch.object(os,'O_NONBLOCK',create=True,new=0),patch.object(os,'O_NOFOLLOW',create=True,new=0):
                # Windows has neither; delete both to expose accidental direct lookup.
                del os.O_NONBLOCK;del os.O_NOFOLLOW
                self.assertEqual(len(Reader(file).read().records),1)
                self.assertEqual(len(evidence_tail(file)['records']),1)
