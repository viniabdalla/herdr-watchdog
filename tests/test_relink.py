"""Religar spec 2026-11-25 L17-20,32-40: isolated core and CLI boundary."""
from dataclasses import asdict, replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_leader_link import Binding
from watchdog_app.store import Store


class RelinkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.env = patch.dict(os.environ, WATCHDOG_STATE_DIR=str(self.repo/'state'),
                              CODEX_THREAD_ID='12345678-1234-1234-1234-123456789abc')
        self.env.start(); self.addCleanup(self.env.stop)
        self.old = Binding(account=str(self.repo/'account'), history=str(self.repo/'A.jsonl'))
        self.new = replace(self.old, session=os.environ['CODEX_THREAD_ID'], history=str(self.repo/'B.jsonl'))
        self.store = Store(); self.store.save(self.old, self.store.load(self.old,self.repo))
        self.file = self.store.root/(self.old.key+'.json')
        self.runtime = SimpleNamespace(Binding=Binding, resolve_history=lambda *a:Path(self.new.history),
                                       verify=lambda b:{})
        self.session = SimpleNamespace(binding=self.old,file=self.file,repo=self.repo,runtime=self.runtime)
        self.api = SimpleNamespace(checked=lambda p:dict(p,workspace_id='project'),
                                   panel=lambda p,r:p)
        self.calls=[]; self.advertised=self.old.session
        def call(*args):
            self.calls.append(args)
            if args==('agent','list'):return {'agents':[{'pane_id':self.old.pane,'agent':'codex'}]}
            if args[:2]==('agent','get'):
                return {'agent':dict(agent='codex',pane_id=self.old.pane,terminal_id=self.old.terminal,
                    workspace_id=self.old.workspace, agent_session={'kind':'id','value':self.advertised})}
            if args[:2]==('pane','process-info'):
                return {'process_info':{'foreground_processes':[{'pid':self.old.pid}]}}
            if args[:2]==('pane','report-agent-session'):
                if not getattr(self,'stuck',False):self.advertised=self.new.session
                return {}
            raise AssertionError(args)
        self.api.call=call
        self.api.output=lambda *a:'LU-'+self.ref
        self.patches=[patch('watchdog_app.bindings.engine',return_value=self.runtime),
                      patch('watchdog_app.relink._api',return_value=self.api),
                      patch('watchdog_app.relink.process_proof',return_value=None)]
        from watchdog_app import relink
        self.real_process_proof=relink.process_proof
        for p in self.patches:p.start();self.addCleanup(p.stop)
        self.relink=relink
        self.ref=self.relink.begin(self.session,self.old)
        self.history()
        self.calls.clear()

    def history(self, phase='commentary', marker=None):
        rows=[{'type':'session_meta','payload':{'id':self.new.session,'cwd':str(self.repo)}},
              {'type':'response_item','timestamp':datetime.now(timezone.utc).isoformat(),
               'payload':{'type':'message','role':'assistant','phase':phase,
                          'content':[{'type':'output_text','text':marker or 'LU-'+self.ref}]}}]
        Path(self.new.history).write_text(''.join(json.dumps(r)+'\n' for r in rows))

    def test_confirmed_reopens_same_full_identity_and_repeated_command_is_noop(self):
        # Spec L18,20,32,34,37: native reread, one transfer, untouched group/requests.
        from watchdog_app.store import atomic
        state=json.loads(self.file.read_text());state['requests']=[{'session':'A'}]
        atomic(self.file,state)
        result=self.relink.complete(self.ref)
        self.assertEqual(result['state'],'confirmed')
        target=json.loads(Path(result['successor']).read_text())
        self.assertEqual(target['binding'],asdict(self.new))
        self.assertEqual(target['requests'],state['requests'])
        calls=list(self.calls)
        self.assertEqual(self.relink.complete(self.ref),result)
        self.assertEqual(self.calls,calls)
        self.assertEqual(self.relink.pending_for(self.file),self.ref)
        report=next(c for c in self.calls if c[:2]==('pane','report-agent-session'))
        self.assertIn('herdr:codex',report);self.assertIn('clear',report)

    def test_native_success_still_advertising_A_is_a_real_negative(self):
        # Spec L18,36,40: successful report is insufficient if reread remains A.
        self.stuck=True
        with self.assertRaisesRegex(RuntimeError,'registro'):
            self.relink.complete(self.ref)
        self.assertEqual(self.relink.read(self.ref)['state'],'failed')
        self.assertNotIn('ownership',json.loads(self.file.read_text()))

    def test_cancel_and_new_attempt_reject_late_proof(self):
        # Spec L19,35: cancellation and supersession invalidate late responses.
        self.relink.cancel(self.ref)
        with self.assertRaises(RuntimeError):self.relink.complete(self.ref)
        newref=self.relink.begin(self.session,self.old)
        third=self.relink.begin(self.session,self.old)
        self.assertEqual(self.relink.read(newref)['state'],'cancelled')
        self.assertEqual(self.relink.pending_for(self.file),third)
        self.assertFalse(any(c[:2]==('pane','report-agent-session') for c in self.calls))

    def test_user_or_old_marker_is_not_a_proof(self):
        # Spec L17,33,36: only recent assistant commentary in this exact session.
        self.history(phase='final')
        with self.assertRaisesRegex(RuntimeError,'comentário'):self.relink.complete(self.ref)
        self.assertEqual(self.calls,[])

    def test_interrupted_transfer_is_resumable_without_second_group(self):
        # Spec L19,34,36,40: resume after relinquishment and before target save.
        with patch.object(Store,'save',side_effect=OSError('disk full')):
            with self.assertRaisesRegex(OSError,'disk full'):self.relink.complete(self.ref)
        self.assertEqual(self.relink.read(self.ref)['state'],'transferring')
        self.assertEqual(json.loads(self.file.read_text())['ownership'],'transferring')
        result=self.relink.complete(self.ref)
        self.assertEqual(result['state'],'confirmed')
        self.assertEqual(json.loads(Path(result['successor']).read_text())['binding'],asdict(self.new))

    def test_other_pane_marker_and_replaced_terminal_are_rejected(self):
        # Spec L17,33,35: history marker alone and a replacement terminal are insufficient.
        self.api.output=lambda *a:'other pane has marker'
        with self.assertRaisesRegex(RuntimeError,'visível'):self.relink.complete(self.ref)
        self.assertEqual(self.relink.read(self.ref)['state'],'failed')
        self.assertFalse(any(c[:2]==('pane','report-agent-session') for c in self.calls))

    def test_auto_connect_is_blocked_while_skill_attempt_is_pending(self):
        # Spec L19,35: a pending proof owns the transition; no silent move races it.
        from watchdog_app.leader_link import connect
        with self.assertRaisesRegex(RuntimeError,'Religar'):
            connect(self.session,self.new)
        self.assertNotIn('ownership',json.loads(self.file.read_text()))

    def test_source_identity_is_captured_and_invalid_reference_does_not_traverse(self):
        # Spec L16,26: ref resolves in normal state independently of command cwd.
        for ref in ('../outside','Ｆ'*32,'a'*31):
            with self.assertRaises(RuntimeError):self.relink.read(ref)
        self.assertEqual(self.relink.read(self.ref)['binding_file'],str(self.file.resolve()))

    def test_same_session_does_not_report_clear_or_create_a_second_binding(self):
        # Spec L18,34: an already correct session refreshes its existing binding.
        self.relink.cancel(self.ref)
        self.new=self.old=replace(self.old,session=os.environ['CODEX_THREAD_ID'],history=self.new.history)
        self.store.save(self.old,self.store.load(self.old,self.repo))
        self.file=self.store.root/(self.old.key+'.json');self.session.file=self.file;self.session.binding=self.old
        self.advertised=self.old.session
        self.ref=self.relink.begin(self.session,self.old);self.history()
        result=self.relink.complete(self.ref)
        self.assertEqual(result['successor'],str(self.file))
        self.assertFalse(any(c[:2]==('pane','report-agent-session') for c in self.calls))

    def test_daemon_caller_cwd_and_inherited_pane_do_not_identify_target(self):
        # Spec L17,26,33,40: daemon caller is not a descendant of target, cwd unrelated.
        import subprocess
        # Boundary B: the real CLI launches a fake binary and runtime/OS fixtures.
        binary=self.repo/'fake herdr'
        binary.write_text('''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
a=sys.argv[1:]; root=Path(os.environ['FIXTURE_ROOT']); sid=root/'announced'
with (root/'calls').open('a') as f:f.write(json.dumps(a)+'\\n')
pane={'pane_id':'project:p4','terminal_id':'terminal','workspace_id':'project'}
if a[:2]==['pane','read']:
 print('LU-'+os.environ['FIXTURE_REF']);sys.exit()
if a[:2]==['agent','list']:result={'agents':[dict(pane,agent='codex')]}
elif a[:2]==['pane','get']:result={'pane':pane}
elif a[:2]==['pane','process-info']:result={'process_info':{'foreground_processes':[{'pid':123}]}}
elif a[:2]==['agent','get']:result={'agent':dict(pane,agent='codex',agent_session={'kind':'id','value':sid.read_text()})}
elif a[:2]==['pane','report-agent-session']:
 if not os.environ.get('FIXTURE_STUCK'):sid.write_text(a[a.index('--agent-session-id')+1])
 result={}
else:raise SystemExit(2)
print(json.dumps({'result':result}))
''');binary.chmod(0o755)
        fixture=self.repo/'fixture';fixture.mkdir()
        # Keep process proof real: psutil and runtime are isolated test doubles.
        (fixture/'psutil.py').write_text('''import os
from pathlib import Path
class Error(Exception):pass
class Process:
 def __init__(self,pid):
  assert pid==123 # The caller's daemon PID must never be queried.
 def environ(self):return {'CODEX_HOME':os.environ['FIXTURE_ACCOUNT'],'HERDR_PANE_ID':'project:p4'}
 def cmdline(self):return ['codex','--no-daemon']
 def name(self):return 'codex'
 def cwd(self):return os.environ['FIXTURE_ROOT']
''')
        (fixture/'left_undone').mkdir();(fixture/'left_undone/__init__.py').write_text('')
        (fixture/'left_undone/runtime.py').write_text('''import os
from pathlib import Path
from dataclasses import dataclass
import hashlib
@dataclass
class Binding:
 kind:str;session:str;account:str;pane:str;terminal:str;workspace:str;history:str;pid:int;started:str
 @property
 def key(self):return hashlib.sha256((self.kind+'\\0'+self.account+'\\0'+self.session).encode()).hexdigest()
def resolve_history(*a):return Path(os.environ['FIXTURE_ROOT'])/'B.jsonl'
def process_info(pid):return dict(pid=123,started='456',kind='codex',pane='project:p4',account=os.environ['FIXTURE_ACCOUNT'])
def verify(b):return {}
''')
        # Resolve via normal state dir while running from an unrelated cwd.
        env=dict(os.environ,HERDR_BIN_PATH=str(binary),FIXTURE_ROOT=str(self.repo),
                 FIXTURE_ACCOUNT=self.old.account,FIXTURE_REF=self.ref,WATCHDOG_LEFT_UNDONE_ROOT=str(fixture),
                 PYTHONPATH=os.pathsep.join([str(fixture),str(Path(__file__).resolve().parents[1])]),
                 HERDR_PANE_ID='wH:pG')
        from watchdog_app.store import atomic
        op=self.relink.read(self.ref);op['sources']={'HERDR_BIN_PATH':str(binary)};atomic(self.relink._path(self.ref),op)
        (self.repo/'announced').write_text(self.old.session)
        args=['python3','-m','watchdog_app.app','religar',self.ref]
        result=subprocess.run(args,cwd=self.repo.parent,env=env,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('Líder ligado',result.stdout)
        calls=(self.repo/'calls').read_text()
        self.assertNotIn('send-text',calls)
        self.assertIn('clear',calls)
        self.assertEqual(self.relink.read(self.ref)['state'],'confirmed')
        # A zero-exit report with the old announced ID must also fail through this CLI.
        self.relink.cancel(self.ref)
        # Start a new independent fixture owner so a confirmed transfer is not reused.
        old=replace(self.old,session='independent');self.store.save(old,self.store.load(old,self.repo))
        self.old=old;self.session.binding=old;self.session.file=self.store.root/(old.key+'.json')
        self.ref=self.relink.begin(self.session,old);self.history()
        op=self.relink.read(self.ref);op['sources']={'HERDR_BIN_PATH':str(binary)};atomic(self.relink._path(self.ref),op)
        env.update(FIXTURE_REF=self.ref,FIXTURE_STUCK='1');(self.repo/'announced').write_text(old.session)
        result=subprocess.run(args[:-1]+[self.ref],cwd=self.repo.parent,env=env,text=True,capture_output=True)
        self.assertEqual(result.returncode,1)
        self.assertIn('registro',result.stderr)
        self.assertEqual(self.relink.read(self.ref)['state'],'failed')

    def test_proven_transfer_retry_survives_marker_scrolling_offscreen(self):
        # Spec L19,36,40: persisted proof survives interruption; no new invocation.
        with patch.object(Store,'save',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):self.relink.complete(self.ref)
        self.api.output=lambda *a:'marker scrolled off screen'
        self.assertEqual(self.relink.complete(self.ref)['state'],'confirmed')

    def test_process_reuse_and_account_change_are_rejected_by_portable_proof(self):
        # Spec L17,35: portable OS identity is checked even if Herdr still reports old PID.
        process_proof=self.real_process_proof
        process=SimpleNamespace(environ=lambda:{'CODEX_HOME':self.old.account,'HERDR_PANE_ID':self.old.pane},
                                cmdline=lambda:['codex'],name=lambda:'codex',cwd=lambda:str(self.repo))
        info=dict(pid=self.old.pid,started='replacement',kind='codex',pane=self.old.pane,account=self.old.account)
        runtime=SimpleNamespace(process_info=lambda pid:info)
        with patch.dict('sys.modules',psutil=SimpleNamespace(Process=lambda pid:process,Error=OSError)):
            with self.assertRaisesRegex(RuntimeError,'substituído'):process_proof(self.old,self.repo,runtime)
            process.environ=lambda:{'CODEX_HOME':'/other','HERDR_PANE_ID':self.old.pane}
            with self.assertRaisesRegex(RuntimeError,'conta'):process_proof(self.old,self.repo,runtime)

    def test_begin_revalidates_destination_terminal_before_persisting(self):
        # Spec L16,35: chosen destination cannot silently turn into a replacement terminal.
        self.relink.cancel(self.ref)
        self.api.call=lambda *a: {'agent':dict(agent='codex',pane_id=self.old.pane,
            terminal_id='replacement',workspace_id=self.old.workspace)}
        with self.assertRaisesRegex(RuntimeError,'alvo'):self.relink.begin(self.session,self.old)

    def test_same_identity_refresh_receipt_survives_final_result_write_failure(self):
        # Spec L19,34,40: confirmation-write crash cannot duplicate an in-place refresh.
        self.relink.cancel(self.ref)
        self.new=self.old=replace(self.old,session=os.environ['CODEX_THREAD_ID'],history=self.new.history)
        self.store.save(self.old,self.store.load(self.old,self.repo))
        self.file=self.store.root/(self.old.key+'.json');self.session.file=self.file;self.session.binding=self.old
        self.advertised=self.old.session
        self.ref=self.relink.begin(self.session,self.old);self.history()
        save=self.relink._save
        def fail_confirm(op,state=None,notice=None):
            if state=='confirmed':raise OSError('result disk full')
            return save(op,state,notice)
        with patch.object(self.relink,'_save',side_effect=fail_confirm):
            with self.assertRaises(OSError):self.relink.complete(self.ref)
        self.assertEqual(self.relink.complete(self.ref)['state'],'confirmed')
        self.assertEqual(len(json.loads(self.file.read_text())['reopened']),1)

    def test_group_and_old_delivery_records_stay_byte_identical(self):
        # Spec L20,37: 15 members/14 done, base/modes/goal and old requests are retained.
        from watchdog_app import long_run
        from watchdog_app.store import atomic
        group=dict(members=['task:'+str(n) for n in range(15)],done=list(range(14)),base='abc',
                   modes={'task:0':'here'},goal={'session':'A'})
        atomic(long_run.path_for(self.repo),group)
        before=long_run.path_for(self.repo).read_bytes()
        old_request=self.store.root/'old-request.json';atomic(old_request,{'session':'A','text':'old request'})
        request=old_request.read_bytes()
        self.relink.complete(self.ref)
        self.assertEqual(long_run.path_for(self.repo).read_bytes(),before)
        self.assertEqual(old_request.read_bytes(),request)

    def test_transfer_validation_failure_before_relinquishment_is_terminal(self):
        # Spec L19,36: invalid destination fails without trapping an intact owner in retry.
        self.store.save(self.new,self.store.load(self.new,self.repo))
        with self.assertRaisesRegex(RuntimeError,'Destination'):self.relink.complete(self.ref)
        self.assertEqual(self.relink.read(self.ref)['state'],'failed')
        self.assertNotIn('ownership',json.loads(self.file.read_text()))
        self.assertNotEqual(self.relink.begin(self.session,self.old),self.ref)

    def test_marker_visible_in_two_panes_is_ambiguous(self):
        # Spec L17,19,33,36: a duplicated marker cannot choose a conversation.
        call=self.api.call
        def duplicated(*args):
            if args==('agent','list'):
                return {'agents':[{'pane_id':self.old.pane,'agent':'codex'},
                                  {'pane_id':'project:p9','agent':'codex'}]}
            return call(*args)
        self.api.call=duplicated
        with self.assertRaisesRegex(RuntimeError,'ambíguo'):self.relink.complete(self.ref)
        self.assertFalse(any(c[:2]==('pane','report-agent-session') for c in self.calls))

    def test_native_session_metadata_does_not_hide_the_confirmed_full_id(self):
        # Spec L18,32,40: Herdr AgentSessionInfo includes agent/source metadata.
        call=self.api.call
        def metadata(*args):
            result=call(*args)
            if args[:2]==('agent','get'):
                result['agent']['agent_session'].update(agent='codex',source='herdr:codex')
            return result
        self.api.call=metadata
        self.assertEqual(self.relink.complete(self.ref)['state'],'confirmed')
