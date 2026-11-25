"""Read-only Progress view of the leader, current kit group and TODO blockers."""
from dataclasses import asdict
from pathlib import Path
import re

from . import bindings, leader_kit, long_run
from .actions import Session
from .agents_ui import describe
from .agent_usage import usage_meter
from .dispatch_preview import classify
from .herdr import Herdr
from .todo import Snapshot
from .session_progress import Progress


class Agents:
    def __init__(self, repo, binding_file=None):
        self.repo = Path(repo)
        self.binding_file = binding_file
        self.cache = {}
        self.activities = {}
        self.progress = Progress(repo, binding_file)

    def poll(self):
        result = [('AGENTES', 'ready', None)]
        group = long_run.record(self.repo) or {}
        from .progress_notices import rows as notice_rows
        result.extend(notice_rows(group))
        try:
            records = leader_kit.executors(self.repo, group=group['base'])['executors'] if group.get('base') else []
        except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
            records = []
            result.append(('Registro de agentes · ' + str(error), 'unavailable', None))
        try:
            snapshot = Snapshot.read(self.repo)
            tasks = [t for t in long_run.members(snapshot, group.get('members', [])) if t]
        except (OSError, RuntimeError, ValueError, KeyError, TypeError):
            snapshot, tasks = None, []
        by_ticket = {}
        for task in tasks:
            match = re.match(r'^(?:\d{4}-\d{2}-\d{2} )?(T\d+)\b', task.title)
            if match:
                by_ticket.setdefault(match[1], []).append(task)
        live, candidates, leader = {}, [], None
        try:
            if self.binding_file:
                session = Session.for_panel(self.binding_file, self.repo)
                if self.binding_file != session.file:
                    self.progress = Progress(self.repo, session.file)
                self.binding_file = session.file
                leader = asdict(session.binding)
                live = {p['pane_id']: p for p in Herdr().call('pane', 'list', '--workspace', leader['workspace'])['panes']}
                if records:
                    candidates, _ = bindings.engine().candidates()
        except (OSError, RuntimeError, ValueError, KeyError, TypeError):
            live = {}  # Hide stale usage when the leader's identity cannot be verified.
        if leader:
            state, usage = describe({'binding':leader}, live.get(leader['pane']), self.cache)
            view = self.progress.poll()
            activity = ' · ' + view.current if live and view.current else ''
            result.append((f"Líder · {leader['pane']} · {state} · {usage_meter(usage)}{activity}", 'working', None))
        else:
            result.append(('Líder · — · identidade indisponível · Contexto · Sem dados', 'unavailable', None))
        for record in records:
            pane = live.get(record.get('pane'))
            actor = None
            if (pane and pane.get('terminal_id') == record.get('terminal') and
                    any(cwd and Path(cwd).resolve().is_relative_to(Path(record['worktree']).resolve())
                        for cwd in (pane.get('foreground_cwd') or pane.get('cwd'),))):
                native = pane.get('agent_session') or {}
                sid = native.get('value') if native.get('kind') == 'id' else None
                if sid and (record.get('session') is None or record['session'] == sid):
                    matches = [b for b in candidates if b.pane == record['pane'] and
                               b.terminal == record['terminal'] and b.session == sid and b.kind == pane.get('agent')]
                    if len(matches) == 1:
                        actor = asdict(matches[0])
            activity = ''
            verified = False
            key = (actor['pane'], actor['terminal'], actor['kind'], actor['session'], actor['history']) if actor else None
            def read_activity(binding):
                nonlocal activity, verified
                verified = True
                try:
                    monitor = self.activities.setdefault(key, Progress(self.repo))
                    activity = monitor.poll_verified(binding).current
                except (OSError, ValueError, RuntimeError, KeyError, TypeError):
                    self.activities.pop(key, None)
            state, usage = describe({'binding':actor}, pane, self.cache, on_verified=read_activity) if actor else ('Identidade indisponível', None)
            self.activities = {k:v for k,v in self.activities.items()
                               if k[0] != record.get('pane') or (verified and k == key)}
            matching = by_ticket.get(record['ticket'], [])
            task = matching[0] if len(matching) == 1 else None
            note = ('concluída · ' + task.title if task and task.done else
                    record.get('error') or record.get('operation') or (task.title if task else 'atividade indisponível'))
            if not (task and task.done):
                checks = record.get('checks', [])
                if checks:
                    note += f" · checagem inicial {len(checks)}/3 · {checks[-1]['summary']}"
                if len(checks) < 3 and record.get('state') == 'ready':
                    next_check = len(checks) + 1
                    note += f' · próxima checagem prevista {next_check}/3 aos {next_check + 1} min'
            if activity: note += ' · ' + activity
            result.append((f"{record['ticket']} · {record.get('pane') or '—'} · {state} · {usage_meter(usage)} · {note}",
                           'done' if task and task.done else 'blocked' if record.get('state') == 'failed' else 'working', None))
        try:
            if snapshot is None:
                return result + notice_rows(group, details=True) + [('', None, None)]
            tasks = [t for t in tasks if not t.done]
            registered = {r['ticket'] for r in records}
            for item in classify(snapshot, [t.id for t in tasks]):
                ticket = re.match(r'^(T\d+)\b', item['title'])
                if ticket and ticket[1] in registered:
                    continue
                note = item['label'] if item['label'] != 'livre' else 'aguardando executor'
                detail = ' · ' + '; '.join(item['details']) if item['details'] else ''
                result.append((item['title'] + ' · — · ' + note + detail, 'blocked' if item['label'] != 'livre' else 'ready', None))
        except (OSError, RuntimeError, ValueError, KeyError, TypeError):
            pass
        return result + notice_rows(group, details=True) + [('', None, None)]
