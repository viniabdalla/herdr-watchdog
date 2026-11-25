"""Successful native checklist calls, scoped to a verified conversation and turn.

Direct Codex update_plan and Claude TodoWrite protocols are recognized. TaskCreate
and TaskUpdate remain unsupported until actual native result records are available.
Code in shell/stdin/orchestration wrappers and assistant prose are never parsed.
"""
from collections import OrderedDict
from dataclasses import dataclass
import hashlib
import json

from .actions import Session
from .transcripts import Reader


@dataclass(frozen=True)
class View:
    state: str
    detail: str = ''
    done: int | None = None
    total: int | None = None
    current: str = ''


class Checklist:
    def __init__(self, kind, session):
        self.kind, self.session = kind, session
        self.pending = OrderedDict()
        self.seen = OrderedDict()
        self.applied = OrderedDict()
        self.steps = []
        self.turn = self.native_turn = None
        self.problem = ''
        self.wrong_source = False

    @staticmethod
    def _remember(cache, key, limit):
        cache[key] = True
        cache.move_to_end(key)
        while len(cache) > limit: cache.popitem(last=False)

    def _turn(self, identity, *, native=False):
        if identity != self.turn:
            self.turn = identity
            self.native_turn = identity if native else None
            self.steps = []; self.pending.clear(); self.problem = ''

    @staticmethod
    def _steps(name, data):
        if not isinstance(data, dict): return None
        steps = data.get('plan' if name == 'update_plan' else 'todos')
        if not isinstance(steps, list) or len(steps) > 256: return None
        parsed = []
        size = 0
        for step in steps:
            if not isinstance(step, dict): return None
            text = step.get('step' if name == 'update_plan' else 'content')
            status = step.get('status')
            if not isinstance(text, str) or not text.strip() or len(text) > 2000: return None
            if status not in ('pending', 'in_progress', 'completed'): return None
            size += len(text)
            if size > 32768: return None
            parsed.append((text, status))
        return parsed

    def _call(self, identity, name, data):
        if not isinstance(identity, str) or not 0 < len(identity) <= 256 or identity in self.applied:
            return
        allowed = ('update_plan',) if self.kind == 'codex' else ('TodoWrite', 'TaskCreate', 'TaskUpdate')
        if name not in allowed: return
        self.pending[identity] = (name, self._steps(name, data))
        self.pending.move_to_end(identity)
        while len(self.pending) > 128: self.pending.popitem(last=False)

    def _result(self, identity, output, error=False):
        if not isinstance(identity, str): return
        pending = self.pending.pop(identity, None)
        if pending is None or identity in self.applied: return
        name, steps = pending
        if error: return
        if name in ('TaskCreate', 'TaskUpdate'):
            self.steps = []; self.problem = 'Task checklist format is unsupported'
            self._remember(self.applied, identity, 4096)
            return
        # Require native success text, not a tool call alone or an arbitrary echo.
        success = isinstance(output, str) and (
            output.strip() == 'Plan updated' if name == 'update_plan' else
            output.startswith('Todos have been modified successfully.'))
        if error or not success: return
        self._remember(self.applied, identity, 4096)
        if steps is None:
            self.steps = []; self.problem = 'Native checklist schema is unsupported'
        else:
            self.steps = steps; self.problem = ''

    def feed(self, row):
        if not isinstance(row, dict) or row.get('isSidechain') or row.get('agentId'): return
        source = row.get('sessionId') or row.get('session_id')
        if source and source != self.session: return
        fingerprint = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
        if fingerprint in self.seen: return
        self._remember(self.seen, fingerprint, 4096)
        if self.kind == 'codex':
            payload = row.get('payload')
            if not isinstance(payload, dict): return
            kind = payload.get('type')
            if row.get('type') == 'session_meta':
                if payload.get('id') != self.session:
                    self.wrong_source = True; self.steps = []; self.pending.clear()
                return
            if self.wrong_source: return
            if row.get('type') == 'turn_context':
                if payload.get('turn_id'): self._turn(payload['turn_id'], native=True)
                return
            if row.get('type') == 'event_msg':
                if kind == 'task_started' and payload.get('turn_id'):
                    self._turn(payload['turn_id'], native=True)
                elif kind == 'user_message':
                    if payload.get('turn_id'): self._turn(payload['turn_id'], native=True)
                    else: self._turn(fingerprint)
                return
            if row.get('type') != 'response_item': return
            attribution = payload.get('internal_chat_message_metadata_passthrough', {})
            if isinstance(attribution, dict) and self.native_turn and attribution.get('turn_id'):
                if attribution['turn_id'] != self.native_turn: return
            if kind == 'function_call' and payload.get('name') in ('update_plan', 'functions.update_plan'):
                if payload.get('namespace') not in (None, 'functions'): return
                try: data = json.loads(payload.get('arguments', ''))
                except (ValueError, TypeError, RecursionError): data = None
                self._call(payload.get('call_id'), 'update_plan', data)
            elif kind == 'function_call_output':
                self._result(payload.get('call_id'), payload.get('output'), payload.get('is_error', False))
        elif self.kind == 'claude':
            message = row.get('message')
            if not isinstance(message, dict): return
            content = message.get('content')
            if row.get('type') == 'user':
                parts = content if isinstance(content, list) else []
                results = [p for p in parts if isinstance(p, dict) and p.get('type') == 'tool_result']
                if results:
                    for part in results:
                        self._result(part.get('tool_use_id'), part.get('content'), part.get('is_error', False))
                elif not row.get('sourceToolAssistantUUID') and not row.get('isMeta'):
                    if isinstance(content, str) or any(isinstance(p, dict) and p.get('type') == 'text' for p in parts):
                        self._turn(row.get('uuid') or fingerprint)
            elif row.get('type') == 'assistant' and isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get('type') == 'tool_use':
                        self._call(part.get('id'), part.get('name'), part.get('input'))

    def gap(self):
        # Missing rows may hide a new turn, but do not authorize replay of old calls.
        self.steps = []; self.pending.clear()
        self.turn = self.native_turn = None
        self.problem = 'Transcript rows were skipped; waiting for a fresh checklist'

    def view(self):
        if self.wrong_source: return View('unavailable', 'Transcript identity does not match the watched conversation')
        if self.kind not in ('codex', 'claude'): return View('unsupported', 'Conversation format is unsupported')
        if self.problem: return View('unsupported', self.problem)
        if not self.steps: return View('no_checklist', 'No successful checklist in the current turn')
        done = sum(status == 'completed' for _, status in self.steps)
        current = next((text for text, status in self.steps if status == 'in_progress'), '')
        if not current: current = next((text for text, status in self.steps if status == 'pending'), '')
        state = 'done' if done == len(self.steps) else 'working' if any(s == 'in_progress' for _, s in self.steps) else 'ready'
        return View(state, '', done, len(self.steps), current)


class Progress:
    """One instance per panel. Re-verify native identity/project before every read."""
    def __init__(self, repo, binding_file=None):
        self.repo, self.binding_file = repo, binding_file
        self.session = self.reader = self.checklist = None
        self.source = None

    def poll(self):
        if not self.binding_file: return View('unavailable', 'No conversation binding; open Progress with Watchdog')
        try:
            if self.session is None: self.session = Session(self.binding_file, self.repo)
            target = self.session.successor_file()
            if target:
                self.session = Session.for_panel(target, self.repo)
                self.binding_file = self.session.file
            self.session.verify()
            binding = self.session.binding
            source = (binding.kind, binding.session, binding.history)
            if source != self.source:
                self.reader = Reader(binding.history)
                self.checklist = Checklist(binding.kind, binding.session)
                self.source = source
            batch = self.reader.read()
            if batch.reset: self.checklist = Checklist(binding.kind, binding.session)
            if batch.unavailable: return View('unavailable', 'Transcript unavailable')
            if batch.discarded:
                self.checklist.gap()
            for row in batch.records: self.checklist.feed(row)
            if batch.catching_up: return View('catching_up', 'Reading conversation checklist records')
            if batch.incomplete: return View('catching_up', 'Waiting for a complete transcript row')
            return self.checklist.view()
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
            # Do not resume a stale plan after a period of unverifiable identity.
            self.session = self.reader = self.checklist = self.source = None
            return View('unavailable', str(error))
