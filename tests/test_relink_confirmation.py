"""Spec #17 L17,32-36,40,44-48: manual confirmation in an isolated PTY."""
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import unittest

import test_leader_link as fixture


class ConfirmationTests(unittest.TestCase):
    def setUp(self):
        fixture.LeaderLinkTests.setUp(self)
        if os.environ.get('WATCHDOG_FULL_CONTROLS') == '1':
            self.env['WATCHDOG_FULL_CONTROLS'] = '1'

    open = fixture.LeaderLinkTests.open
    live = fixture.LeaderLinkTests.live
    wait = fixture.LeaderLinkTests.wait

    def test_same_advertised_id_requires_confirmation_and_cancel_is_not_success(self):
        # #17 L32,40,44,48: actual B, advertised A are independent.
        (self.repo/'effective.json').write_text(json.dumps(asdict(replace(self.old,session='B'))))
        terminal = self.open()
        os.write(terminal.master,b'L\r')
        self.wait(terminal,'Confirme a sessão no Codex de')
        self.assertNotIn(b'L\xc3\xadder ligado',terminal.output)
        self.assertEqual(json.loads(self.file.read_text())['binding'],asdict(self.old))
        os.write(terminal.master,b'\x1b')
        self.wait(terminal,'Sessão não confirmada')
        self.assertEqual(json.loads(self.file.read_text())['binding'],asdict(self.old))


    def test_copy_keeps_complete_instruction_in_narrow_panel(self):
        # #17 L22,33,36: copying must not inherit physical display line breaks.
        import fcntl
        import struct
        import termios
        clipboard=self.repo/'clipboard'
        command=self.repo/'wl-copy'
        command.write_text('#!/bin/sh\ncat > '+str(clipboard)+'\n')
        command.chmod(0o755)
        self.env['PATH']=str(self.repo)+os.pathsep+self.env['PATH']
        t=self.open()
        fcntl.ioctl(t.master,termios.TIOCSWINSZ,struct.pack('HHHH',30,40,0,0))
        attempt=self.attempt(t)
        os.write(t.master,b'c');self.wait(t,'Instrução copiada')
        copied=clipboard.read_text()
        self.assertIn(attempt['marker'],copied)
        self.assertIn(str(Path(__file__).resolve().parents[1]/'watchdog'),copied)
        self.assertIn('confirm-session',copied)
        self.assertNotIn('\n',copied)
        self.assertIsNone(t.process.poll())

    def prepare_native(self):
        """Real recovery algorithm, fake OS/process/Herdr boundaries only."""
        import shutil
        from watchdog_app import bindings
        try:
            runtime = bindings.engine()
        except RuntimeError as error:
            self.skipTest('Optional native recovery integration: ' + str(error))
        native_root = Path(runtime.__file__).parent
        package = self.repo/'native/left_undone'
        package.mkdir(parents=True)
        (package/'__init__.py').write_text('')
        for name in ('recovery.py',):
            shutil.copyfile(native_root/name, package/name)
        (package/'language.py').write_text('def tr(text):return text\n')
        (package/'runtime.py').write_text(NATIVE_RUNTIME)
        (package/'repository.py').write_text(
            "import os\nfrom pathlib import Path\n"
            "def binding_project(b,state):return Path(os.environ['RELIGAR_FIXTURE'])\n"
            "def repository_sessions(items,repo,state):return items\n")
        self.old = replace(self.old, session='11111111-1111-4111-8111-111111111111',
                           account=str(self.repo/'account'), history=str(self.repo/'history.jsonl'))
        self.store.save(self.old,self.store.load(self.old,self.repo))
        self.file=self.store.root/(self.old.key+'.json')
        self.live(self.old)
        Path(self.old.account).mkdir()
        hook = Path(self.old.account)/'herdr-agent-state.sh'
        hook.write_text('#!/bin/sh\nexec python3 "$RELIGAR_FIXTURE/hook.py"\n')
        (self.repo/'hook.py').write_text(
            "import json,os\nfrom pathlib import Path\np=Path(os.environ['RELIGAR_FIXTURE'])\n"
            "if not (p/'stale').exists():\n"
            " (p/'live.json').write_text(json.dumps([json.loads((p/'effective.json').read_text())]))\n")
        (self.repo/'effective.json').write_text(json.dumps(asdict(self.old)))
        fake = self.repo/'native-herdr'
        fake.write_text(NATIVE_HERDR)
        fake.chmod(0o755)
        self.native_env = dict(self.env, WATCHDOG_LEFT_UNDONE_ROOT=str(package.parent),
                               RELIGAR_FIXTURE=str(self.repo), HERDR_BIN_PATH=str(fake),
                               CODEX_THREAD_ID=self.old.session,
                               PYTHONPATH=str(Path(__file__).parent)+os.pathsep+str(Path(__file__).resolve().parents[1]),
                               LEFT_UNDONE_STATE_DIR=str(self.repo/'unused-lu'))

    def attempt(self, terminal):
        os.write(terminal.master,b'L\r')
        self.wait(terminal,'Confirme a sessão no Codex de')
        path = self.file.with_suffix('.relink.json')
        return json.loads(path.read_text())

    def prove(self, attempt, *, marker=True, visible=True, ambiguous=False):
        from datetime import datetime, timezone
        import subprocess
        if marker:
            Path(self.old.history).write_text(json.dumps(dict(timestamp=datetime.now(timezone.utc).isoformat(),
                type='response_item',payload=dict(type='message',role='assistant',phase='commentary',
                content=[dict(type='output_text',text=attempt['marker'])])))+'\n')
        else:
            Path(self.old.history).write_text('')
        (self.repo/'visible').write_text(attempt['marker'] if visible else '')
        if ambiguous:
            (self.repo/'ambiguous').touch()
        launcher = Path(__file__).resolve().parents[1]/'watchdog'
        return subprocess.run([str(launcher),'confirm-session',str(self.file),attempt['id']],
                              env=self.native_env,cwd='/',text=True,capture_output=True,timeout=12)

    def test_confirm_A_with_real_marker_recovery_repeats_and_reopens(self):
        # #17 L17,25,33-36,46: accepting a bare ID or bypassing marker breaks this.
        self.prepare_native()
        t = self.open(self.old)
        from watchdog_app import long_run
        from watchdog_app.store import atomic
        from unittest.mock import patch
        with patch.dict(os.environ,self.env):
            group_path=long_run.path_for(self.repo)
            atomic(group_path,dict(members=['title:A','title:B'],modes={'title:A':'here'},
                                   base='fixed-base',mission='existing-goal'))
        group_before=group_path.read_bytes()
        before = self.file.read_bytes()
        for repeat in range(2):
            t.output=b''
            attempt=self.attempt(t)
            result=self.prove(attempt)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            os.write(t.master,b'\r')
            self.wait(t,'Líder ligado · project:p4 · 11111111')
            self.assertEqual(self.file.read_bytes(),before)
            self.assertEqual(group_path.read_bytes(),group_before)
        t.close()
        reopened=self.open()
        self.wait(reopened,'11111111')
        commands=(self.repo/'commands.jsonl').read_text()
        self.assertNotIn('send-text',commands)
        self.assertNotIn('send-keys',commands)
        self.assertFalse((self.repo/'unused-lu').exists())

    def test_missing_ambiguous_wrong_pane_and_changed_terminal_fail(self):
        # #17 L33-35,47: no proof means no success, regardless of advertised UUID.
        self.prepare_native()
        for case in ('absent','ambiguous','pane','terminal','stale'):
            with self.subTest(case=case):
                self.live(self.old)
                for name in ('ambiguous','stale'):
                    (self.repo/name).unlink(missing_ok=True)
                actor=self.old
                if case=='pane':actor=replace(actor,pane='project:p9')
                if case=='terminal':actor=replace(actor,terminal='changed')
                if case=='stale':
                    actor=replace(actor,session='22222222-2222-4222-8222-222222222222')
                    (self.repo/'stale').touch()
                (self.repo/'effective.json').write_text(json.dumps(asdict(actor)))
                self.native_env['CODEX_THREAD_ID']=actor.session
                t=self.open()
                attempt=self.attempt(t)
                result=self.prove(attempt,marker=case!='absent',ambiguous=case=='ambiguous')
                self.assertNotEqual(result.returncode,0,result.stdout+result.stderr)
                if case=='ambiguous':
                    proof=json.loads(self.file.with_suffix('.relink.json').read_text())
                    self.assertIn('multiple panes',proof['error'])
                t.output=b'';os.write(t.master,b'\r')
                self.wait(t,'Sessão não confirmada')
                self.assertNotIn('Líder ligado',t.output.decode(errors='replace'))
                self.assertEqual(json.loads(self.file.read_text())['binding'],asdict(self.old))
                t.close()

    def test_cancel_without_helper_preserves_normal_follow(self):
        # #17 L35,54: cancelling an unused attempt must preserve ordinary follow.
        from unittest.mock import patch
        from types import SimpleNamespace
        from watchdog_app.actions import Session
        t=self.open()
        self.attempt(t)
        os.write(t.master,b'\x1b');self.wait(t,'Sessão não confirmada')
        new=replace(self.old,session='22222222-2222-4222-8222-222222222222')
        self.live(new)
        def verify(actor):
            if actor!=new:raise RuntimeError('changed')
            return {}
        runtime=SimpleNamespace(Binding=fixture.Binding,verify=verify)
        with patch.dict(os.environ,self.env),patch('watchdog_app.bindings.engine',return_value=runtime), \
             patch('watchdog_app.bindings.discover',return_value=([new],[])), \
             patch('watchdog_app.bindings.project_for',return_value=self.repo):
            self.assertEqual(Session.for_panel(self.file,self.repo).binding,new)
        self.assertNotIn('Líder ligado',t.output.decode(errors='replace'))


    def test_clipboard_backend_errors_keep_confirmation_open(self):
        # #17 L22,26: clipboard failure leaves an instruction and a usable retry.
        import subprocess
        from types import SimpleNamespace
        from unittest.mock import patch
        from watchdog_app.tasks_ui import TasksUI
        ui=TasksUI.__new__(TasksUI)
        ui.screen=SimpleNamespace(getmaxyx=lambda:(30,40))
        ui.mode='relink_confirm'
        ui.pending=dict(marker='LU-'+'a'*32,binding_file='/tmp/test-binding.json',
                        id='attempt',target=dict(pane='project:p4'))
        ui.notice=''
        for failure in (subprocess.CalledProcessError(1,['wl-copy']),
                        subprocess.TimeoutExpired(['wl-copy'],3)):
            with self.subTest(failure=type(failure).__name__), \
                 patch('shutil.which',return_value='/fake/wl-copy'), \
                 patch('subprocess.run',side_effect=failure):
                self.assertTrue(ui.handle('c'))
                self.assertEqual(ui.mode,'relink_confirm')
                self.assertIn('Não foi possível copiar',ui.notice)


NATIVE_RUNTIME = '''import json,os
from pathlib import Path
from test_leader_link import Binding
root=Path(os.environ['RELIGAR_FIXTURE'])
def effective():return json.loads((root/'effective.json').read_text())
def processes():
 b=effective();p={k:b[k] for k in ('kind','account','pane','pid','started')}
 return [p,dict(p,pane='project:p9',pid=p['pid']+1)] if (root/'ambiguous').exists() else [p]
def process_info(pid):return processes()[0]
def process_environment(pid):return dict(os.environ,HERDR_ENV='1',HERDR_SOCKET_PATH='fake',HERDR_PANE_ID=effective()['pane'] if pid==effective()['pid'] else 'project:p9')
def resolve_history(kind,account,session):return effective()['history']
def raw_herdr(*args,env=None):
 b=effective() if args[:2]==('pane','process-info') else json.loads((root/'live.json').read_text())[0]
 if args[:2]==('pane','process-info'):return {'process_info':{'foreground_processes':[{'pid':p['pid']} for p in processes()]}}
 return {'agent':dict(agent='codex',pane_id=args[2],terminal_id=b['terminal'],workspace_id=b['workspace'],agent_session={'kind':'id','value':b['session']})}
def verify_live(binding,live):
 if (binding.pane,binding.terminal,binding.session)!=(live['pane_id'],live['terminal_id'],live['agent_session']['value']):raise RuntimeError('Native identity differs')
def candidates():return [Binding(**b) for b in json.loads((root/'live.json').read_text())],[]
def verify(b,**kw):
 if b not in candidates()[0]:raise RuntimeError('identity changed')
 return {'agent_status':'idle'}
'''
NATIVE_HERDR = '''#!/usr/bin/env python3
import os,sys
from pathlib import Path
if sys.argv[1:3]!=['pane','read']:raise SystemExit(1)
print((Path(os.environ['RELIGAR_FIXTURE'])/'visible').read_text())
'''
