"""Boundary tests: no real LLM, no production pane or leader changes."""
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid
from contextlib import nullcontext

from watchdog_app import audit
from test_actions import FakeBinding


class FakeSession:
    def __init__(self, repo, file):
        self.repo = repo; self.file = file
        self.binding = FakeBinding()
        self.calls = []; self.status = 'idle'; self.error = None
        self.runtime = SimpleNamespace(queue=self.queue)

    def verify(self): return {'agent_status': self.status}
    def routing(self): return nullcontext()
    def queue(self, binding, text):
        self.calls.append((binding, text))
        if self.error: raise self.error
        return str(uuid.uuid4())


class FakeHerdr:
    def __init__(self): self.calls = []; self.error = None
    def call(self, *args):
        self.calls.append(args)
        if self.error: raise self.error
        return {'root_pane': {'pane_id': 'new-pane', 'terminal_id': 'new-terminal', 'tab_id': 'new-tab'}}
    def checked(self, pane): return pane


class FakeRPC:
    created = []
    response_changes = {}
    extra_events = []
    fail_turn = False
    def __init__(self, executable, account, cwd, **kw):
        self.calls = []; self.events = []; self.closed = False; self.cwd = cwd
        self.created.append(self)
    def initialize(self): self.calls.append(('initialize', {}))
    def request(self, method, params):
        self.calls.append((method, params))
        if method == 'model/list':
            return {'data': [{'model': 'model-a', 'displayName': 'Model A', 'hidden': False},
                             {'model': 'secret', 'hidden': True}]}
        if method == 'config/read': return {'config': {'mcp_servers': {'remote': {'url': 'https://example.invalid'}}}}
        if method == 'thread/start':
            return {'model': 'model-a', 'cwd': self.cwd, 'approvalPolicy': 'never',
                    'sandbox': {'type': 'readOnly'}, 'thread': {'id': str(uuid.uuid4()), 'turns': []},
                    **self.response_changes}
        if method == 'turn/start':
            self.events = list(self.extra_events) + [
                {'method': 'item/completed', 'params': {'turnId': 'turn', 'item': {'type': 'agentMessage', 'text': 'Evidência: app.py:1. Lacunas. Próximos passos.'}}},
                {'method': 'turn/completed', 'params': {'turn': {'id': 'turn', 'status': 'failed' if self.fail_turn else 'completed'}}}]
            return {'turn': {'id': 'turn'}}
        raise AssertionError(method)
    def receive(self): raise AssertionError('Unexpected receive')
    def close(self): self.closed = True


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / 'project'; self.repo.mkdir()
        self.account = Path(self.tmp.name) / 'codex'; self.account.mkdir()
        self.executable = Path('/usr/bin/python3')
        self.session = FakeSession(self.repo, self.repo / 'binding.json')
        self.api = FakeHerdr(); self.store = audit.AuditStore(Path(self.tmp.name) / 'audits')
        self.identity = str(uuid.uuid4())
        self.inventory = lambda *a: [{'model': 'model-a', 'label': 'Model A'}]
        self.patches = [patch.object(audit, 'source', return_value=('a'*40, 'b'*64)),
                        patch.object(audit, 'original', side_effect=lambda value: (self.session, self.session.verify()))]
        for p in self.patches: p.start(); self.addCleanup(p.stop)
        FakeRPC.created = []; FakeRPC.response_changes = {}; FakeRPC.extra_events = []; FakeRPC.fail_turn = False

    def launch(self, **kw):
        args = dict(confirmed=True, audit_id=self.identity, store=self.store, api=self.api, inventory=self.inventory)
        args.update(kw)
        return audit.launch(self.session, self.account, 'model-a', self.executable, **args)

    def complete(self):
        value = self.launch(); value.update(state='completed', effective_model='model-a', thread_id=str(uuid.uuid4()))
        path = Path(value['report_file']); path.write_text('Report evidence: file.py:5')
        value['report_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.store.save(value); return value

    def test_confirmed_launch_creates_new_tab_in_project_without_leader_changes(self):
        before = asdict(self.session.binding)
        value = self.launch()
        create, run = self.api.calls
        self.assertEqual(create[:2], ('tab', 'create'))
        self.assertEqual(create[create.index('--cwd')+1], str(self.repo))
        self.assertEqual(create[create.index('--workspace')+1], before['workspace'])
        self.assertEqual(run[:3], ('pane', 'run', 'new-pane'))
        self.assertIn('audit runner', run[3]); self.assertIn(self.identity, run[3])
        self.assertEqual(asdict(self.session.binding), before)
        self.assertEqual(value['recipient'], before)
        self.assertIsNone(value['effective_model'])
        self.assertEqual(self.store.load(self.identity)['launch'], 'starting')
        self.assertFalse(self.session.calls)

    def test_unconfirmed_unavailable_and_duplicate_launches_have_no_second_effect(self):
        with self.assertRaisesRegex(RuntimeError, 'Confirme'): self.launch(confirmed=False)
        with self.assertRaisesRegex(RuntimeError, 'não listado'): self.launch(inventory=lambda *a: [])
        self.assertFalse(self.api.calls)
        self.launch()
        with self.assertRaisesRegex(RuntimeError, 'já registrada'): self.launch()
        self.assertEqual(len(self.api.calls), 2)

    def test_uncertain_native_launch_is_durable_and_not_retried(self):
        self.api.error = RuntimeError('timeout')
        with self.assertRaisesRegex(RuntimeError, 'incerto'): self.launch()
        self.assertEqual(self.store.load(self.identity)['state'], 'uncertain')
        with self.assertRaisesRegex(RuntimeError, 'já registrada'): self.launch()
        self.assertEqual(len(self.api.calls), 1)

    def test_thread_start_proof_new_session_readonly_never_and_bounded_brief(self):
        value = self.launch(); value['private_transcript'] = 'DO NOT COPY THIS SECRET'
        output = audit.execute(value, self.store.save, rpc_factory=FakeRPC)
        calls = FakeRPC.created[0].calls
        start = next(params for method, params in calls if method == 'thread/start')
        turn = next(params for method, params in calls if method == 'turn/start')
        self.assertEqual(start['sandbox'], 'read-only'); self.assertEqual(start['approvalPolicy'], 'never')
        self.assertEqual(start['cwd'], str(self.repo)); self.assertNotIn('threadId', start)
        self.assertEqual(start['model'], 'model-a')
        self.assertFalse(start['config']['features.apps']); self.assertFalse(start['config']['features.multi_agent'])
        self.assertNotIn('DO NOT COPY', turn['input'][0]['text'])
        self.assertNotIn(self.session.binding.session, turn['input'][0]['text'])
        self.assertLess(len(turn['input'][0]['text'].encode()), 8192)
        self.assertIn(self.identity, turn['input'][0]['text'])
        self.assertNotEqual(value['thread_id'], self.session.binding.session)
        self.assertEqual(value['effective_model'], 'model-a'); self.assertIn('Evidência', output)
        self.assertTrue(FakeRPC.created[0].closed)

    def test_policy_cwd_model_or_prior_turn_mismatch_refuses_generation(self):
        for changed in ({'model': 'fallback'}, {'approvalPolicy': 'on-request'},
                        {'cwd': '/wrong'}, {'sandbox': {'type': 'workspaceWrite'}},
                        {'thread': {'id': self.session.binding.session, 'turns': []}},
                        {'thread': {'id': 'new', 'turns': [{'id': 'prior'}]}}):
            with self.subTest(changed=changed):
                value = dict(audit_id=self.identity, repo=str(self.repo), account=str(self.account),
                             executable=str(self.executable), requested_model='model-a', recipient=asdict(self.session.binding))
                FakeRPC.response_changes = changed
                with self.assertRaisesRegex(RuntimeError, 'diverge'):
                    audit.execute(value, lambda v: None, rpc_factory=FakeRPC)
                self.assertNotIn('turn/start', [m for m, p in FakeRPC.created[-1].calls])

    def test_reroute_or_failed_turn_never_returns_accepted_report(self):
        value = self.launch()
        for events, failure in (([{'method': 'model/rerouted', 'params': {}}], False), ([], True)):
            FakeRPC.extra_events = events; FakeRPC.fail_turn = failure
            with self.assertRaises(RuntimeError): audit.execute(value, self.store.save, rpc_factory=FakeRPC)

    def test_inventory_filters_hidden_and_never_guesses_astra(self):
        values = audit.models(self.account, self.executable, rpc_factory=FakeRPC)
        self.assertEqual([v['model'] for v in values], ['model-a'])
        self.assertIsNone(audit.preferred(values))
        self.assertEqual(audit.preferred(values + [{'model': 'gpt-6.1-astra'}]), 'gpt-6.1-astra')
        self.assertNotIn('thread/start', [m for m, p in FakeRPC.created[-1].calls])

    def test_busy_preserves_report_then_explicit_delivery_queues_exact_original_once(self):
        value = self.complete(); self.session.status = 'working'
        self.assertEqual(audit.deliver(self.store, self.identity)['delivery'], 'busy')
        self.assertFalse(self.session.calls)
        self.session.status = 'idle'
        result = audit.deliver(self.store, self.identity)
        self.assertEqual(result['delivery'], 'sent')
        binding, message = self.session.calls[0]
        self.assertEqual(asdict(binding), value['recipient'])
        self.assertIn(self.identity, message); self.assertIn(value['report_sha256'], message)
        self.assertIn(value['report_file'], message)
        with self.assertRaisesRegex(RuntimeError, 'sem reenvio'): audit.deliver(self.store, self.identity)
        self.assertEqual(len(self.session.calls), 1)

    def test_failed_queue_and_invalid_receipt_are_uncertain_without_retry(self):
        for error in (RuntimeError('timeout'), None):
            with self.subTest(error=error):
                self.identity = str(uuid.uuid4()); self.complete()
                self.session.error = error
                if error is None: self.session.runtime.queue = lambda *a: None
                result = audit.deliver(self.store, self.identity)
                self.assertEqual(result['delivery'], 'uncertain')
                with self.assertRaisesRegex(RuntimeError, 'sem reenvio'): audit.deliver(self.store, self.identity)

    def test_wrong_or_stale_recipient_is_not_redirected(self):
        self.complete()
        with patch.object(audit, 'original', side_effect=RuntimeError('leader changed')):
            self.assertEqual(audit.deliver(self.store, self.identity)['delivery'], 'stale')
        self.assertFalse(self.session.calls)

    def test_tampered_report_and_incomplete_audit_refuse_delivery(self):
        value = self.complete(); Path(value['report_file']).write_text('changed')
        with self.assertRaisesRegex(RuntimeError, 'alterado'): audit.deliver(self.store, self.identity)
        value.update(state='failed'); self.store.save(value)
        with self.assertRaisesRegex(RuntimeError, 'não concluída'): audit.deliver(self.store, self.identity)
        self.assertFalse(self.session.calls)

    def test_duplicate_runner_refuses_before_provider_and_artifacts_are_host_owned(self):
        self.launch()
        self.assertEqual(audit.runner(self.store, self.identity, api=self.api, rpc_factory=FakeRPC), 0)
        self.assertEqual(self.store.load(self.identity)['state'], 'completed')
        self.assertTrue(Path(self.store.load(self.identity)['report_file']).is_file())
        with self.assertRaisesRegex(RuntimeError, 'já tentado'):
            audit.runner(self.store, self.identity, api=self.api, rpc_factory=FakeRPC)
        self.assertEqual(len(FakeRPC.created), 1)

    def test_dead_wrapper_marks_uncertain_without_launch_or_send(self):
        value = self.launch(); value['created'] = 0; self.store.save(value)
        self.assertEqual(audit.inspect(self.store, self.identity)['state'], 'uncertain')
        self.assertEqual(len(self.api.calls), 2); self.assertFalse(self.session.calls)

    def test_readonly_disables_configured_mcp_servers(self):
        config = audit.readonly_config({'mcp_servers': {'remote': {'url': 'https://example.invalid'}}})
        self.assertEqual(config['mcp_servers']['remote'], {'enabled': False})
        self.assertFalse(config['features.apps'])

    def test_original_refuses_changed_binding_file_without_following_redirect(self):
        value = self.launch()
        self.patches[1].stop()
        data = {'repo':str(self.repo), 'binding':asdict(FakeBinding(session='other'))}
        self.session.file.write_text(json.dumps(data))
        with self.assertRaisesRegex(RuntimeError, 'Destinatário original mudou'):
            audit.original(value)
        self.assertEqual(json.loads(self.session.file.read_text()), data)

    def test_changed_source_preserves_historical_result_without_delivery(self):
        self.complete()
        with patch.object(audit, 'source', return_value=('c'*40, 'd'*64)):
            result = audit.deliver(self.store, self.identity)
        self.assertEqual(result['delivery'], 'stale_source')
        self.assertFalse(self.session.calls)
        self.assertTrue(Path(result['report_file']).is_file())
        with self.assertRaisesRegex(RuntimeError, 'sem reenvio'):
            audit.deliver(self.store, self.identity)

    def test_new_id_cannot_duplicate_an_active_or_uncertain_audit(self):
        self.launch(); self.identity = str(uuid.uuid4())
        with self.assertRaisesRegex(RuntimeError, 'ativa/incerta'): self.launch()
        self.assertEqual(len(self.api.calls), 2)

    def test_environment_drops_inherited_thread_and_provider_credentials(self):
        with patch.dict(os.environ, {'CODEX_THREAD_ID': 'old', 'OPENAI_API_KEY': 'secret', 'GIT_DIR': 'wrong'}):
            env = audit.environment(self.account)
        self.assertNotIn('CODEX_THREAD_ID', env); self.assertNotIn('OPENAI_API_KEY', env)
        self.assertNotIn('GIT_DIR', env); self.assertEqual(env['CODEX_HOME'], str(self.account))


if __name__ == '__main__': unittest.main()

class RPCProcessTests(unittest.TestCase):
    """Exercise the real pipe/framing layer with a bounded non-LLM provider fixture."""
    def test_jsonl_subprocess_gets_only_new_thread_and_readonly_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); log = root/'calls.jsonl'; executable = root/'fixture-codex'
            executable.write_text('#!/usr/bin/python3\n' + '''import json,sys
from pathlib import Path
log=Path(__file__).with_name('calls.jsonl')
def emit(x): print(json.dumps(x),flush=True)
for line in sys.stdin:
 x=json.loads(line)
 with log.open('a') as out: out.write(json.dumps(x)+'\\n')
 method=x.get('method'); p=x.get('params',{})
 if method=='initialized': continue
 if method=='initialize': result={}
 elif method=='config/read': result={'config':{'mcp_servers':{}}}
 elif method=='thread/start':
  result={'model':p['model'],'cwd':p['cwd'],'approvalPolicy':p['approvalPolicy'],
   'sandbox':{'type':'readOnly','networkAccess':False},
   'thread':{'id':'11111111-1111-4111-8111-111111111111','turns':[]}}
 elif method=='turn/start':
  result={'turn':{'id':'fixture-turn'}}
  # Notifications may precede their request acknowledgement.
  emit({'method':'item/completed','params':{'threadId':p['threadId'],'turnId':'fixture-turn',
   'item':{'type':'agentMessage','text':'fixture.py:1; lacunas; próximos passos'}}})
  emit({'method':'turn/completed','params':{'threadId':p['threadId'],
   'turn':{'id':'fixture-turn','status':'completed'}}})
 else: raise SystemExit('unexpected method '+str(method))
 emit({'id':x['id'],'result':result})
''')
            executable.chmod(0o700)
            value = {'executable': str(executable), 'account': str(root), 'repo': str(root),
                     'requested_model':'fixture-model', 'recipient': {'session':'original-leader'},
                     'audit_id':str(uuid.uuid4()), 'revision':'a'*40, 'source_digest':'b'*64}
            result = audit.execute(value, lambda v: None)
            self.assertIn('fixture.py:1', result)
            calls = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertEqual([c['method'] for c in calls], ['initialize','initialized','config/read','thread/start','turn/start'])
            start = calls[3]['params']
            self.assertEqual(start['sandbox'], 'read-only'); self.assertEqual(start['approvalPolicy'], 'never')
            self.assertNotIn('original-leader', json.dumps(calls))
            self.assertEqual(start['cwd'], str(root))
            self.assertEqual(value['startup_proof']['sandbox']['type'], 'readOnly')

    def test_server_approval_is_refused_before_failing_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); executable = root/'fixture-codex'
            executable.write_text('#!/usr/bin/python3\n' + '''import json,sys,time
x=json.loads(sys.stdin.readline())
print(json.dumps({'id':10,'method':'item/commandExecution/requestApproval','params':{}}),flush=True)
reply=sys.stdin.readline()
open(__file__+'.reply','w').write(reply)
time.sleep(5)
''')
            executable.chmod(0o700)
            rpc = audit.RPC(str(executable), str(root), str(root), timeout=2)
            try:
                with self.assertRaisesRegex(RuntimeError, 'solicitou'): rpc.initialize()
            finally: rpc.close()
            # The host never sends an approval result; only a refusal error is written.
            self.assertEqual(rpc.number, 1)

class OriginalRecipientTests(unittest.TestCase):
    def test_exact_recipient_verification_never_reattaches_or_writes_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory); file = repo/'binding.json'; binding = FakeBinding()
            data = {'repo': str(repo), 'binding': asdict(binding)}
            file.write_text(json.dumps(data)); before = file.read_bytes()
            runtime = SimpleNamespace(Binding=FakeBinding, verify=lambda b: {'agent_status': 'idle'})
            value = {'repo': str(repo), 'binding_file': str(file), 'recipient': asdict(binding)}
            with patch('watchdog_app.bindings.engine', return_value=runtime), \
                 patch('watchdog_app.bindings.project_for', return_value=repo), \
                 patch.object(audit, 'Session', side_effect=AssertionError('must not reattach')):
                session, live = audit.original(value)
            self.assertEqual(asdict(session.binding), asdict(binding))
            self.assertEqual(live['agent_status'], 'idle')
            self.assertEqual(file.read_bytes(), before)
