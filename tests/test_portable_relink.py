"""Religar spec 2026-11-25 L17,24-26,38,40: isolated platform boundary."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class PortableRelinkTests(unittest.TestCase):
    def test_missing_left_undone_uses_bundled_runtime(self):
        # L24-26: no optional Linux identity engine needed on Codex path.
        from watchdog_app import bindings
        bindings.engine.cache_clear()
        with patch.dict(os.environ, {'WATCHDOG_LEFT_UNDONE_ROOT': '/missing'}), patch.object(bindings.shutil, 'which', return_value=None):
            self.assertEqual(bindings.engine().__name__, 'watchdog_app.portable_runtime')
        bindings.engine.cache_clear()

    def test_history_is_exact_and_project_comes_from_metadata(self):
        # L17,26: account + exact session; independent of caller cwd.
        from watchdog_app import portable_runtime as runtime
        with tempfile.TemporaryDirectory(prefix='wd space ') as tmp:
            root = Path(tmp); history = root/'sessions/rollout-B.jsonl'
            history.parent.mkdir(); history.write_text(json.dumps({'type':'session_meta','payload':{'id':'B','cwd':tmp}})+'\n')
            self.assertEqual(runtime.resolve_history('codex', root, 'B'), history)
            binding = runtime.Binding('codex','B',tmp,'w:p','t','w',str(history),1,'1')
            self.assertEqual(runtime.binding_project(binding), root)
            with self.assertRaises(RuntimeError): runtime.resolve_history('codex', root, '../B')

    def test_process_info_portable_and_denied_environment_fails_closed(self):
        # L17,26: macOS cannot always expose another process environment.
        from watchdog_app import portable_runtime as runtime
        from types import SimpleNamespace
        process = SimpleNamespace(name=lambda:'codex.exe',create_time=lambda:123.5,
                                  environ=lambda:{'HERDR_PANE_ID':'w:p','CODEX_HOME':'/account'})
        fake = SimpleNamespace(Process=lambda pid:process, Error=OSError)
        with patch.object(runtime, 'platform', 'win32'), patch.object(runtime, 'psutil', fake):
            self.assertEqual(runtime.process_info(42)['started'], '123.5')
            self.assertEqual(runtime.process_info(42)['account'], str(Path('/account').resolve()))
        fake.Process = lambda pid: (_ for _ in ()).throw(OSError('access denied'))
        with patch.object(runtime, 'psutil', fake):
            with self.assertRaises(RuntimeError): runtime.process_info(42)

    def test_installed_skill_and_launcher_work_with_spaces_without_symlinks(self):
        # L24-26,38: real installer/launcher, private account, no clipboard.
        with tempfile.TemporaryDirectory(prefix='wd install space ') as tmp:
            root = Path(tmp); account = root/'codex account'; bindir = root/'bin dir'
            env = dict(os.environ, CODEX_HOME=str(account))
            args = [sys.executable,str(ROOT/'install.py'),'--no-plugin','--skip-dependencies','--bin-dir',str(bindir)]
            for _ in range(2):
                result = subprocess.run(args,env=env,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
            text = (account/'skills/religar/SKILL.md').read_text()
            self.assertIn('LU-<ref>',text); self.assertIn('religar',text)
            result = subprocess.run([str(bindir/'watchdog'),'--help'],cwd=tmp,env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            result = subprocess.run([sys.executable,str(ROOT/'uninstall.py'),'--no-plugin','--bin-dir',str(bindir)],env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertFalse((account/'skills/religar').exists())
            self.assertFalse((bindir/'watchdog').exists())

    def test_installer_preserves_foreign_skill(self):
        # L24: installation preserves unrelated account resources.
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); skill=root/'account/skills/religar/SKILL.md'
            skill.parent.mkdir(parents=True);skill.write_text('owned by user')
            result=subprocess.run([sys.executable,str(ROOT/'install.py'),'--no-plugin','--skip-dependencies','--bin-dir',str(root/'bin')],env=dict(os.environ,CODEX_HOME=str(root/'account')),capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('Refusing to overwrite another skill',result.stderr)
            self.assertEqual(skill.read_text(),'owned by user')
            self.assertFalse((root/'bin/watchdog').exists())

class NativeRuntimeBoundaryTests(unittest.TestCase):
    def test_real_fake_binary_rejects_stale_announced_session(self):
        # Spec L17-18,36,40: effective B and announced A are independent.
        from watchdog_app import portable_runtime as runtime
        with tempfile.TemporaryDirectory(prefix='wd native space ') as tmp:
            root=Path(tmp);history=root/'sessions/rollout-B.jsonl'
            history.parent.mkdir();history.write_text(json.dumps({'type':'session_meta','payload':{'id':'B','cwd':tmp}})+'\n')
            binary=root/'fake herdr'
            binary.write_text('#!'+sys.executable+'\n'+'''import json,os,sys
if sys.argv[1:3]==['agent','get']:
 print(json.dumps({'result':{'agent':{'pane_id':'w:p','terminal_id':'t','agent':'codex','agent_session':{'kind':'id','value':os.environ['ANNOUNCED']}}}}))
else:
 print(json.dumps({'result':{'process_info':{'foreground_processes':[{'pid':42}]}}}))
''');binary.chmod(0o755)
            binding=runtime.Binding('codex','B',tmp,'w:p','t','w',str(history),42,'123')
            proc=dict(pid=42,started='123',kind='codex',pane='w:p',account=tmp)
            with patch.dict(os.environ,HERDR_BIN_PATH=str(binary),ANNOUNCED='B'),patch.object(runtime,'process_info',return_value=proc):
                self.assertEqual(runtime.verify(binding)['agent_session']['value'],'B')
                with patch.dict(os.environ,ANNOUNCED='A'):
                    with self.assertRaisesRegex(RuntimeError,'identity changed'):runtime.verify(binding)
                with patch.object(runtime,'process_info',return_value=dict(proc,started='124')):
                    with self.assertRaisesRegex(RuntimeError,'Process or account'):runtime.verify(binding)

    def test_runtime_setup_selects_os_dependencies(self):
        # L24,26: installer resolves Windows curses and portable process reader.
        from watchdog_app import installation
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);python=root/'.watchdog-runtime/bin/python'
            python.parent.mkdir(parents=True);python.touch()
            with patch.object(installation,'ROOT',root),patch.object(installation.subprocess,'run') as run:
                self.assertEqual(installation.runtime_python(),python)
                self.assertIn('psutil>=5.9,<8',run.call_args_list[0].args[0])

    def test_windows_launcher_quotes_python_and_checkout(self):
        from watchdog_app.installation import launcher_text
        text=launcher_text(Path('C:/Program Files/Python/python.exe'),windows=True)
        self.assertIn('"C:/Program Files/Python/python.exe" "',text)
        self.assertIn('" %*',text)

class PluginPanelTests(unittest.TestCase):
    def test_plugin_tasks_creates_binding_before_opening_ui(self):
        # Spec L12,24,26,38: actual plugin pane must open bound Tasks.
        from watchdog_app import plugin_panel
        from watchdog_app.portable_runtime import Binding
        from watchdog_app.store import Store
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); binding=Binding('codex','B',tmp,'w:leader','t','w','history',42,'1')
            with patch.dict(os.environ,{'HERDR_PANE_ID':'','WATCHDOG_PANE':'','WATCHDOG_SESSION':''}),patch.object(plugin_panel.bindings,'discover',return_value=([binding],[])),patch.object(plugin_panel.bindings,'verify'),patch.object(plugin_panel,'Store',return_value=Store(root/'state')),patch.object(plugin_panel,'launch') as launch:
                self.assertEqual(plugin_panel.main(['tasks','--repo',tmp]),0)
                file=launch.call_args.args[2]
                self.assertEqual(json.loads(file.read_text())['binding']['session'],'B')

class PortableProcessTests(unittest.TestCase):
    def test_native_foreground_excludes_detached_servers(self):
        # L17,26: macOS/Windows native foreground, independent of Unix process groups.
        from watchdog_app import portable_runtime as runtime
        def native(*args):
            if args[:2]==('agent','list'):return {'agents':[{'pane_id':'w:p','agent':'codex'}]}
            return {'process_info':{'foreground_processes':[{'pid':42}]}}
        proc=dict(pid=42,started='123',kind='codex',pane='w:p',account='/account')
        with patch.object(runtime,'herdr',side_effect=native),patch.object(runtime,'process_info',return_value=proc):
            self.assertEqual(runtime.processes(),[proc])


if __name__ == '__main__': unittest.main()
