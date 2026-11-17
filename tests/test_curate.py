import json
from dataclasses import asdict
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import threading
import time
import sys

from watchdog_app.curate import latest_reply, normalize_reply, validate_proposals, review, apply_review, ask_codex, Cancelled
from watchdog_app.todo import Snapshot
from test_actions import FakeBinding


class CuratorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        patcher = patch.dict(os.environ, {'WATCHDOG_STATE_DIR': str(self.repo / 'state')})
        patcher.start();self.addCleanup(patcher.stop)
        (self.repo / 'TODO.md').write_text('## Next\n- [ ] Add colors\n- [ ] Connect verifier\n## Done\n- [x] Previous work\n')
        self.snapshot = Snapshot.read(self.repo)

    def session(self):
        path = self.repo / 'source.jsonl'
        path.write_text(json.dumps({'type': 'event_msg', 'timestamp': '2026-11-16T10:00:00Z',
                                   'payload': {'type': 'task_complete', 'turn_id': 'turn',
                                               'last_agent_message': 'Colors are implemented.'}}) + '\n')
        return SimpleNamespace(binding=FakeBinding(history=str(path)), verify=lambda: None)

    def test_review_is_cached_and_never_changes_todo_without_apply(self):
        session = self.session();calls = []
        def infer(payload, cancel):
            calls.append(payload)
            return {'done': [{'id': self.snapshot.tasks[0].id, 'evidence': 'Colors are implemented.'}],
                    'blocked': [], 'add': []}
        with patch('watchdog_app.curate.ask_codex', side_effect=infer):
            first = review(session, self.snapshot, threading.Event())
            second = review(session, self.snapshot, threading.Event())
        self.assertEqual(len(calls), 1)
        self.assertEqual(first['actions'], second['actions'])
        self.assertEqual((self.repo / 'TODO.md').read_bytes(), self.snapshot.raw)
        after = apply_review(session, self.snapshot, first, {0})
        self.assertTrue(next(t for t in after.tasks if 'Add colors' in t.text).done)

    def test_new_completed_reply_invalidates_an_old_review(self):
        session = self.session()
        raw = {'done': [{'id': self.snapshot.tasks[0].id, 'evidence': 'Colors are implemented.'}],
               'blocked': [], 'add': []}
        with patch('watchdog_app.curate.ask_codex', return_value=raw):
            result = review(session, self.snapshot, threading.Event())
        with Path(session.binding.history).open('a') as file:
            file.write(json.dumps({'type': 'event_msg', 'payload': {'type': 'task_complete',
                'turn_id': 'new', 'last_agent_message': 'A later correction changes the work.'}}) + '\n')
        with self.assertRaisesRegex(RuntimeError, 'changed'):
            apply_review(session, self.snapshot, result, {0})
        self.assertEqual((self.repo / 'TODO.md').read_bytes(), self.snapshot.raw)

    def test_cancelling_review_terminates_its_own_cli_child(self):
        pid_file = self.repo / 'child.pid'
        code = 'import os,time;from pathlib import Path;Path('+repr(str(pid_file))+').write_text(str(os.getpid()));time.sleep(30)'
        analyzer = SimpleNamespace(command=lambda *args: ([sys.executable, '-c', code], dict(os.environ)))
        runtime = SimpleNamespace(Analyzer=lambda *args, **kwargs: analyzer)
        cancel = threading.Event();errors = []
        def work():
            try:ask_codex({'reply': 'test'}, cancel)
            except Exception as error:errors.append(error)
        with patch('watchdog_app.curate.bindings.engine', return_value=runtime):
            thread = threading.Thread(target=work);thread.start()
            deadline = time.monotonic() + 5
            while not pid_file.exists() and time.monotonic() < deadline:time.sleep(.02)
            self.assertTrue(pid_file.exists())
            child = int(pid_file.read_text());cancel.set();thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        self.assertTrue(any(isinstance(error, Cancelled) for error in errors))
        with self.assertRaises(ProcessLookupError):os.kill(child, 0)

    def test_done_and_blocked_require_literal_support_and_open_ids(self):
        a, b, closed = self.snapshot.tasks
        reply = normalize_reply('**Task colors are implemented.**\nVerifier cannot run because login expired.')
        output = {'done': [{'id': a.id, 'evidence': 'Task colors are implemented.'}],
                  'blocked': [{'id': b.id, 'reason': 'Login expired',
                               'evidence': 'Verifier cannot run because login expired.'}], 'add': []}
        result = validate_proposals(output, self.snapshot, reply)
        self.assertEqual([a['kind'] for a in result['actions']], ['done', 'blocked'])
        self.assertEqual(result['rejected'], [])
        self.assertFalse(any(a['id'] == closed.id for a in result['actions']))

    def test_bad_quote_does_not_hide_a_separate_valid_proposal(self):
        a, b, _ = self.snapshot.tasks
        output = {'done': [{'id': a.id, 'evidence': 'Colors work.'},
                           {'id': b.id, 'evidence': 'Made-up evidence'}], 'blocked': [], 'add': []}
        result = validate_proposals(output, self.snapshot, 'Colors work.')
        self.assertEqual([a['id'] for a in result['actions']], [a.id])
        self.assertTrue(result['rejected'])

    def test_conflicting_statuses_are_both_withheld(self):
        task = self.snapshot.tasks[0]
        output = {'done': [{'id': task.id, 'evidence': 'Colors work.'}],
                  'blocked': [{'id': task.id, 'reason': 'waiting', 'evidence': 'Colors work.'}], 'add': []}
        result = validate_proposals(output, self.snapshot, 'Colors work.')
        self.assertEqual(result['actions'], [])
        self.assertTrue(result['rejected'])

    def test_unknown_or_closed_ids_and_multiline_additions_are_rejected(self):
        closed = self.snapshot.tasks[-1]
        output = {'done': [{'id': closed.id, 'evidence': 'Done'}, {'id': 'unknown', 'evidence': 'Done'}],
                  'blocked': [], 'add': [{'text': 'New\n## Done', 'evidence': 'Done'}]}
        result = validate_proposals(output, self.snapshot, 'Done')
        self.assertEqual(result['actions'], [])
        self.assertEqual(len(result['rejected']), 3)

    def test_completed_reply_reader_ignores_tools_and_partial_lines(self):
        path = self.repo / 'record.jsonl'
        rows = [{'type': 'event_msg', 'timestamp': '2026-11-16T10:00:00Z',
                 'payload': {'type': 'task_complete', 'turn_id': 'real-turn', 'last_agent_message': 'Actual completion'}},
                {'type': 'response_item', 'payload': {'type': 'function_call_output', 'output': 'Everything done'}}]
        path.write_text('\n'.join(json.dumps(r) for r in rows) + '\n{"type":')
        reply = latest_reply(SimpleNamespace(kind='codex', history=str(path)))
        self.assertEqual(reply['id'], 'real-turn')
        self.assertEqual(reply['text'], 'Actual completion')

    def test_normalization_removes_formatting_but_preserves_negation(self):
        text = '**Colors work.**\nThe verifier is **not done**.\n```\nAll tasks done.\n```'
        result = normalize_reply(text)
        self.assertIn('verifier is not done', result)
        self.assertNotIn('All tasks done.', result)

    def test_claude_sidechain_is_not_current_conversation_evidence(self):
        path = self.repo / 'claude.jsonl'
        rows = [{'type': 'assistant', 'timestamp': '2026-11-16T10:00:00Z',
                 'message': {'id': 'main', 'stop_reason': 'end_turn', 'content': [{'type': 'text', 'text': 'Main reply'}]}},
                {'type': 'assistant', 'isSidechain': True,
                 'message': {'id': 'side', 'stop_reason': 'end_turn', 'content': [{'type': 'text', 'text': 'Wrong reply'}]}}]
        path.write_text('\n'.join(json.dumps(r) for r in rows) + '\n')
        self.assertEqual(latest_reply(SimpleNamespace(kind='claude', history=str(path)))['text'], 'Main reply')
