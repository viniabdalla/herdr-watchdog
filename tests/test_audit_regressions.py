"""QA regressions: lifecycle hooks and immutable leader identity, without live models."""
from contextlib import ExitStack
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from watchdog_app import audit
from watchdog_app.actions import Session
from watchdog_app.audit_ui import AuditUI


@dataclass
class Binding:
    kind: str = 'codex'
    session: str = 'same-leader'
    account: str = '/fixture/account'
    pane: str = 'old-pane'
    terminal: str = 'old-terminal'
    workspace: str = 'fixture'
    history: str = '/fixture/history'
    pid: int = 99999999
    started: str = 'fixture'

    @property
    def key(self): return 'fixture'


class IdentityRegressionTests(unittest.TestCase):
    def check_entrypoint(self, action):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            repo = Path(directory); file = repo/'binding.json'
            old = Binding(); resumed = Binding(pane='resumed-pane', terminal='resumed-terminal', pid=99999998)
            file.write_text(json.dumps({'repo': str(repo), 'binding': asdict(old)})); before = file.read_bytes()
            def verify(binding):
                if binding.pane == old.pane: raise RuntimeError('original process gone')
                return {'agent_status': 'idle'}
            runtime = SimpleNamespace(Binding=Binding, verify=verify)
            session = Session.__new__(Session)
            session.file = file; session.repo = repo; session.binding = old; session.runtime = runtime
            calls = []
            def native(*args):
                calls.append(args)
                return {'root_pane': {'pane_id': 'audit-pane', 'terminal_id': 'audit-terminal'}}
            for name, value in (
                ('watchdog_app.bindings.engine', runtime),
                ('watchdog_app.bindings.discover', ([resumed], [])),
                ('watchdog_app.bindings.project_for', repo),
                ('watchdog_app.audit.source', ('a'*40, 'b'*64)),
                ('watchdog_app.audit.accounts', [str(repo)])):
                stack.enter_context(patch(name, return_value=value))
            stack.enter_context(patch.dict('os.environ', {'WATCHDOG_STATE_DIR': str(repo/'state')}))
            store = audit.AuditStore(repo/'audits'); api = SimpleNamespace(call=native)
            refused = False
            try:
                action(session, store, api)
            except RuntimeError:
                refused = True
            self.assertEqual(file.read_bytes(), before, 'audit entrypoint rewrote leader binding')
            self.assertTrue(refused, 'unavailable original identity must be refused')
            self.assertFalse(calls, 'unavailable leader must not open a pane')

    def test_launch_refuses_original_resumed_elsewhere_without_rewriting_binding(self):
        self.check_entrypoint(lambda session, store, api: audit.launch(
            session, session.repo, 'fixture', '/usr/bin/python3', confirmed=True, store=store, api=api,
            inventory=lambda *a: [{'model': 'fixture'}]))

    def test_ui_open_refuses_original_resumed_elsewhere_without_rewriting_binding(self):
        self.check_entrypoint(lambda session, store, api: AuditUI(session, store))

    def test_ui_confirmation_refuses_resumed_identity_without_rewriting_binding(self):
        def action(session, store, api):
            ui = AuditUI.__new__(AuditUI); ui.recipient = asdict(session.binding)
            ui.stage = 'confirm'; ui.store = store; ui.account = str(session.repo); ui.model = 'fixture'
            ui.confirm(session)
        self.check_entrypoint(action)

    def test_cli_open_refuses_original_resumed_elsewhere_without_rewriting_binding(self):
        def action(session, store, api):
            # CLI catches failures, so convert its nonzero status to the shared refusal assertion.
            result = audit.main(['open', '--repo', str(session.repo), '--binding-file', str(session.file),
                                 '--account', str(session.repo), '--model', 'fixture', '--confirm',
                                 '--executable', '/usr/bin/python3', '--state-dir', str(store.root)])
            if result != 0: raise RuntimeError('CLI refused')
        self.check_entrypoint(action)


class HookRegressionTests(unittest.TestCase):
    def test_effective_thread_config_disables_account_hooks(self):
        config = audit.readonly_config({'features': {'hooks': True}, 'mcp_servers': {}})
        self.assertIs(config.get('features.hooks'), False)

    def test_hooks_disabled_before_initialize_and_thread_start_without_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); executable = root/'fixture-codex'; sentinel = root/'hook-executed'
            config = root/'config.toml'; hooks = root/'hooks.json'
            config.write_text('[features]\nhooks = true\n')
            hooks.write_text(json.dumps({'SessionStart': {'sentinel': str(sentinel), 'inject': 'PRIOR_HANDOFF'}}))
            before = (config.read_bytes(), hooks.read_bytes())
            executable.write_text('#!/usr/bin/python3\n' + '''import json,os,sys
from pathlib import Path
root=Path(os.environ['CODEX_HOME'])
enabled='hooks = true' in (root/'config.toml').read_text()
if 'features.hooks=false' in sys.argv: enabled=False
injected=''
# Account lifecycle initialization would happen before initialize/thread/start.
if enabled:
 hook=json.loads((root/'hooks.json').read_text())['SessionStart']
 Path(hook['sentinel']).write_text('ran')
 injected=hook['inject']
for line in sys.stdin:
 x=json.loads(line); method=x.get('method')
 if method=='initialized': continue
 if method not in ('initialize','thread/start'): raise SystemExit('generation forbidden')
 print(json.dumps({'id':x['id'],'result':{'injected':injected,'thread':{'id':'fixture-clean'}}}),flush=True)
''')
            executable.chmod(0o700)
            rpc = audit.RPC(str(executable), str(root), str(root), timeout=3)
            try:
                rpc.initialize()
                response = rpc.request('thread/start', {'sandbox': 'read-only', 'approvalPolicy': 'never'})
            finally: rpc.close()
            self.assertFalse(sentinel.exists(), 'account lifecycle hook ran before policy override')
            self.assertEqual(response['injected'], '', 'account lifecycle hook injected a handoff')
            self.assertEqual((config.read_bytes(), hooks.read_bytes()), before)

class ReadonlyEntryTests(unittest.TestCase):
    def test_live_open_load_and_ui_never_call_write_capable_session_methods(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            repo = Path(directory); file = repo/'binding.json'; binding = Binding()
            file.write_text(json.dumps({'repo': str(repo), 'binding': asdict(binding)})); before = file.read_bytes()
            runtime = SimpleNamespace(Binding=Binding, verify=lambda actor: {'agent_status': 'idle'})
            session = Session.__new__(Session)
            session.file = file; session.repo = repo; session.binding = binding; session.runtime = runtime
            for name, value in (('watchdog_app.bindings.engine', runtime),
                                ('watchdog_app.bindings.project_for', repo),
                                ('watchdog_app.audit.accounts', [str(repo)]),
                                ('watchdog_app.audit.source', ('a'*40, 'b'*64))):
                stack.enter_context(patch(name, return_value=value))
            stack.enter_context(patch.object(Session, 'verify', side_effect=AssertionError('must not reattach')))
            stack.enter_context(patch.object(Session, 'routing', side_effect=AssertionError('must not route via Session')))
            store = audit.AuditStore(repo/'audits')
            loaded = audit.load_leader(file, repo)
            self.assertEqual(asdict(loaded.binding), asdict(binding))
            ui = AuditUI(session, store); ui.account = str(repo); ui.model = 'fixture'; ui.stage = 'confirm'
            with patch.object(audit, 'launch', return_value={'audit_id': 'fixture-audit'}) as opened:
                self.assertIn('fixture-audit', ui.confirm(session)); opened.assert_called_once()
            calls = []
            api = SimpleNamespace(call=lambda *args: (calls.append(args) or
                                  {'root_pane': {'pane_id': 'new-pane', 'terminal_id': 'new-terminal'}}))
            audit.launch(session, repo, 'fixture', '/usr/bin/python3', confirmed=True, store=store, api=api,
                         inventory=lambda *a: [{'model': 'fixture'}])
            self.assertEqual(len(calls), 2)
            self.assertEqual(file.read_bytes(), before)

    def test_clean_sessions_lease_and_unsettled_operation_prevent_launch(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            repo = Path(directory); file = repo/'binding.json'; binding = Binding()
            file.write_text(json.dumps({'repo': str(repo), 'binding': asdict(binding)})); before = file.read_bytes()
            session = SimpleNamespace(file=file, repo=repo, binding=binding)
            calls = []; api = SimpleNamespace(call=lambda *args: calls.append(args))
            store = audit.AuditStore(repo/'audits')
            stack.enter_context(patch('watchdog_app.clean_sessions.operations', return_value=[{'state': 'active'}]))
            with self.assertRaisesRegex(RuntimeError, 'Clean sessions'):
                audit.launch(session, repo, 'fixture', '/usr/bin/python3', confirmed=True, store=store, api=api,
                             inventory=lambda *a: [{'model': 'fixture'}])
            self.assertFalse(calls); self.assertEqual(file.read_bytes(), before)
            # An already-held cleanup lease also refuses before effects, using the same lock.
            from watchdog_app.clean_sessions import lease
            from watchdog_app.store import Store
            with lease(Store(file.parent), repo):
                with self.assertRaisesRegex(RuntimeError, 'Cleanup is busy'):
                    audit.launch(session, repo, 'fixture', '/usr/bin/python3', confirmed=True, store=store, api=api,
                                 inventory=lambda *a: [{'model': 'fixture'}])
            self.assertFalse(calls); self.assertEqual(file.read_bytes(), before)
