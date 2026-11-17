"""Explicit task routing through the same verified native binding engine."""
from dataclasses import asdict
import json
from pathlib import Path

from . import bindings
from .todo import locked


class Busy(RuntimeError):
    def __init__(self, can_queue):
        super().__init__('The conversation is working. Queue explicitly or wait until it is idle.')
        self.can_queue = can_queue


class Session:
    def __init__(self, file, repo):
        self.file = Path(file) if file else None
        self.repo = Path(repo).resolve()
        self.binding = None
        self.runtime = None
        if self.file:
            data = json.loads(self.file.read_text())
            if Path(data['repo']).resolve() != self.repo:
                raise RuntimeError('Binding belongs to another project')
            self.runtime = bindings.engine()
            self.binding = self.runtime.Binding(**data['binding'])
            self.verify()

    @property
    def label(self):
        if not self.binding:
            return 'Unbound · open this panel with watchdog'
        return f'{self.binding.kind} · {self.binding.pane} · {self.binding.session[:8]}'

    def verify(self):
        if self.binding is None:
            raise RuntimeError('No conversation binding. Open this panel with watchdog first.')
        data = json.loads(self.file.read_text())
        if data.get('binding') != asdict(self.binding) or Path(data['repo']).resolve() != self.repo:
            raise RuntimeError('Conversation binding changed; reopen Tasks before sending or reviewing')
        try:
            live = self.runtime.verify(self.binding)
        except RuntimeError as error:
            raise RuntimeError('Conversation identity changed or is unavailable; reopen Watchdog.') from error
        project = bindings.project_for(self.binding)
        if project is None or Path(project).resolve() != self.repo:
            raise RuntimeError('Conversation project association changed; reopen Watchdog')
        return live

    def dispatch(self, snapshot, ids, queued=False):
        with locked(snapshot.repo):
            snapshot.assert_current()
            tasks = snapshot.selected(ids)
            live = self.verify()
            if self.binding.kind != 'codex':
                raise RuntimeError('Claude task delivery needs a thread-addressed transport; sending is unavailable')
            if not queued and live.get('agent_status') == 'working':
                raise Busy(True)
            if live.get('agent_status') not in ('working', 'idle', 'done'):
                raise RuntimeError('Conversation is not ready to receive tasks')
            message = (f'Please work on these project tasks for {self.repo.name} ({self.repo}):\n\n' +
                       '\n'.join('- ' + task.text for task in tasks) +
                       '\n\nReport what is completed and any concrete blockers. '
                       'Sending this request does not mark the tasks complete.')
            try:
                # Native queue targets the full thread UUID in its own account.
                # A pane prompt could switch sessions after verification.
                return self.runtime.queue(self.binding, message)
            except RuntimeError as error:
                raise RuntimeError('Delivery was not confirmed. Check the Codex queue before retrying; '
                                   'nothing was resent automatically.') from error
