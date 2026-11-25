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

    def test_manifest_installs_skill_and_boots_relevant_actions(self):
        # Spec L24-26,38,40: consume TOML meaning and run installer/boot, no UI/network.
        import contextlib
        import io
        import json
        import runpy
        import shutil
        import subprocess
        import sys
        try:
            import tomllib
        except ImportError:  # Python 3.10; declared in requirements-test.txt.
            import tomli as tomllib
        from watchdog_app import installation
        source=Path(__file__).resolve().parents[1]
        manifest=tomllib.loads((source/'herdr-plugin.toml').read_text())
        self.assertTrue({'linux','macos','windows'} <= set(manifest['platforms']))
        panes={entry['id']:entry for entry in manifest['panes']}
        actions={entry['id']:entry for entry in manifest['actions']}
        entries=[(actions['open'],['open']),(panes['picker'],['pick']),
                 (panes['tasks'],['plugin-panel','tasks']),
                 (panes['progress'],['plugin-panel','progress']),
                 (panes['artifacts'],['plugin-panel','artifacts'])]
        with tempfile.TemporaryDirectory(prefix='wd plugin space ') as tmp:
            root=Path(tmp);account=root/'account';bindir=root/'bin'
            shutil.copy(source/'plugin-boot.py',root)
            shutil.copy(source/'install.py',root)
            skill=root/'skills/religar';skill.mkdir(parents=True)
            shutil.copy(source/'skills/religar/SKILL.md',skill)
            python=installation.python_path(root/'.watchdog-runtime')
            python.parent.mkdir(parents=True)
            # Stand-in for installed runtime: execute the program it receives.
            python.write_text('#!'+sys.executable+'\nimport os,sys\nos.environ["WATCHDOG_TEST_RUNTIME"]="installed"\nos.execv(sys.executable,[sys.executable,*sys.argv[1:]])\n')
            python.chmod(0o755)
            (root/'watchdog').write_text('import json,os,sys\nprint(json.dumps(dict(args=sys.argv[1:],runtime=os.environ.get("WATCHDOG_TEST_RUNTIME"))))\n')
            env=dict(os.environ,WATCHDOG_TEST_RUNTIME='',CODEX_HOME=str(account),WATCHDOG_STATE_DIR=str(root/'state'),XDG_STATE_HOME=str(root/'xdg'))
            with contextlib.redirect_stdout(io.StringIO()),patch.dict(os.environ,env),patch.object(installation,'ROOT',root), \
                 patch.object(installation,'runtime_python',return_value=python), \
                 patch.object(installation.subprocess,'run'):
                # Execute the manifest's installation entry; unrelated builds may coexist.
                builds=[b for b in manifest['build'] if 'install.py' in b['command']]
                self.assertTrue(builds,'manifest must install Religar')
                for entry in builds:
                    command=entry['command']
                    script=command.index('install.py')
                    with patch.object(sys,'argv',[str(root/'install.py'),*command[script+1:],'--bin-dir',str(bindir)]):
                        runpy.run_path(str(root/'install.py'),run_name='__main__')
            self.assertTrue((account/'skills/religar/SKILL.md').is_file())
            launch=subprocess.run([str(bindir/'watchdog'),'religar','reference'],env=env,text=True,capture_output=True)
            self.assertEqual(launch.returncode,0,launch.stderr)
            self.assertEqual(json.loads(launch.stdout),dict(args=['religar','reference'],runtime='installed'))
            for entry,expected in entries:
                with self.subTest(entry=entry['id']):
                    command=entry['command']
                    result=subprocess.run([sys.executable,*command[1:],'--repo',str(root/'project space')],
                                          cwd=root,env=env,text=True,capture_output=True)
                    self.assertEqual(result.returncode,0,result.stderr)
                    self.assertEqual(json.loads(result.stdout),dict(args=[*expected,'--repo',str(root/'project space')],runtime='installed'))
            python.unlink()
            result=subprocess.run([sys.executable,str(root/'plugin-boot.py'),'plugin-panel','tasks'],env=env,text=True,capture_output=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('install.py',result.stderr)

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
