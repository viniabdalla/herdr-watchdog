"""AGENTES in Progress: who does what, and where (spec #21).

Order: blocked and queued work first, then the leader, then workers grouped
by Herdr tab. Reading never mutates panes; the explicit actions (go, close,
unblock) are separate methods the panel calls on a human click.
"""
from dataclasses import asdict, dataclass, field
from pathlib import Path
import re
import time

from . import bindings, leader_kit, long_run
from .actions import Session
from .agents_ui import describe
from .agent_usage import abbreviate
from .dispatch_preview import classify
from .herdr import Herdr
from .todo import Snapshot
from .session_progress import Progress

LABELS = {'blocked': 'Bloqueado', 'working': 'Trabalhando', 'done': 'Feito', 'idle': 'Ocioso'}
OTHERS = 'outros'
# A worker that kept working this long after BLOQUEIO has been answered.
BLOCK_GRACE = 60
RULE = ('Desbloqueie e responda a ele no pane {pane}. Se a decisão não muda o desenho, decida você '
        'e me conte depois o que fez. Só me pergunte se for imperativo (desenho, escopo, push, deploy, '
        'envio externo, perda de dados, merge na main); nesse caso, traga sua sugestão de desbloqueio '
        'e adiante o que puder.')


@dataclass
class Item:
    """Panel metadata for one AGENTES line; plain text stays in the row tuple."""
    kind: str                       # agent · detail · header · queue · title
    state: str = ''                 # blocked · working · queued · done · idle
    segments: list = field(default_factory=list)
    pane: str = None
    terminal: str = None
    ticket: str = None
    group: str = None
    leader: bool = False
    closable: bool = False
    unblock: str = None             # prompt for the leader
    unblock_key: tuple = None


def RULE_ROW(level=2):
    """Separator: 1 before AGENTES, 2 between sections, 3 between tab groups."""
    return ('', None, Item('rule', state=str(level)))


def context(usage):
    """'12k/100k ' plus a 10-cell bar coloured by context level (spec #21 L38)."""
    if not usage or usage.get('context') is None or not usage.get('window'):
        return [('Contexto · sem dados', None)]
    share = usage['context'] / usage['window']
    percent = 100 * share
    label = '<1' if 0 < percent < 1 else str(round(percent))
    filled = min(10, round(10 * min(1, share)))
    level = 'level_ok' if share < .8 else 'level_warn' if share < 1 else 'level_full'
    return [(abbreviate(usage['context']) + '/' + abbreviate(usage['window']) + ' ', None),
            ('▰' * filled + '▱' * (10 - filled) + ' ' + label + '%', level)]


def short_tab(tab):
    return (tab or '—').split(':')[-1]


def plural(count, one, many):
    return f'{count} {one if count == 1 else many}'


class Agents:
    def __init__(self, repo, binding_file=None):
        self.repo = Path(repo)
        self.binding_file = binding_file
        self.cache = {}
        self.activities = {}
        self.progress = Progress(repo, binding_file)
        self.toggled = {}
        self.collapsed = {}
        self.sent = set()
        self.leader_pane = None

    # -- reading -----------------------------------------------------------
    def poll(self):
        from .progress_notices import rows as notice_rows
        result = [RULE_ROW(1), ('AGENTES', 'ready', None)]
        group = long_run.record(self.repo) or {}
        result.extend(notice_rows(group, ended_banner=False))
        try:
            records = leader_kit.executors(self.repo)['executors']
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
        if not live and records:
            # Who and where stay visible; usage needs the verified leader (candidates).
            candidates = []
            for workspace in sorted({r['workspace'] for r in records if r.get('workspace')}):
                try:
                    live.update({p['pane_id']: p for p in Herdr().call('pane', 'list', '--workspace', workspace)['panes']})
                except (OSError, RuntimeError, ValueError, KeyError, TypeError):
                    pass
        self.leader_pane = leader['pane'] if leader else None

        blocked, groups, order = [], {}, []
        for record in records:
            built = self.worker(record, live, candidates, by_ticket)
            if not built:
                continue
            line, detail = built
            item = line[2]
            if item.state == 'blocked':
                blocked.append(line)
                continue
            mine = (not leader or record.get('leader') == leader['pane'] or
                    (group.get('base') and record.get('group') == group['base']))
            key = (record.get('tab') or '—') if mine else OTHERS
            item.group = key
            if key not in groups:
                groups[key] = dict(leva=record.get('leva') or '', lines=[])
                order.append(key)
            groups[key]['lines'].append((line, detail))

        queued = self.queued(snapshot, tasks, records)
        if blocked or queued:
            result.append(('BLOQUEADOS', 'blocked', Item('title', segments=[('BLOQUEADOS', None)])))
            result.extend(blocked + queued)
            result.append(RULE_ROW())

        if leader:
            state, usage = describe({'binding': leader}, live.get(leader['pane']), self.cache)
            view = self.progress.poll()
            kind = 'working' if state == 'Trabalhando' else 'blocked' if state == 'Bloqueado' else 'idle'
            segments = [(f"Líder · {leader['pane']} · {state} · ", None)] + context(usage)
            result.append((''.join(s for s, _ in segments), None,
                           Item('agent', kind, segments, leader['pane'], leader.get('terminal'), leader=True)))
            if kind == 'working' and live and view.current:
                result.append(('  ' + view.current, None, Item('detail')))
        else:
            segments = [('Líder · — · identidade indisponível', None)]
            result.append((segments[0][0], 'unavailable', Item('agent', 'idle', segments, leader=True)))

        for number, key in enumerate(sorted(order, key=lambda k: k == OTHERS)):
            result.append(RULE_ROW(2 if number == 0 else 3))  # spec #21 L32: sections and groups
            lines = groups[key]['lines']
            states = [line[2].state for line, _ in lines]
            default = key == OTHERS or 'working' not in states
            collapsed = self.toggled.get(key, default)
            self.collapsed[key] = collapsed
            label = ('Outros · ' + plural(len(lines), 'executor', 'executores') if key == OTHERS else
                     short_tab(key) + (' · ' + groups[key]['leva'] if groups[key]['leva'] else ''))
            if collapsed:
                counts = [plural(states.count('working'), 'trabalhando', 'trabalhando') if 'working' in states else '',
                          plural(states.count('idle'), 'ocioso', 'ociosos') if 'idle' in states else '',
                          plural(states.count('done'), 'feito', 'feitos') if 'done' in states else '']
                label += ' · ' + ' · '.join(c for c in counts if c) if key != OTHERS else ''
            text = ('▶ ' if collapsed else '▼ ') + label
            tone = ('dot_working' if 'working' in states else 'dot_done' if 'done' in states else 'dot_idle')
            result.append((text, None, Item('header', segments=[(text, tone)], group=key)))
            if not collapsed:
                for line, detail in lines:
                    result.append(line)
                    if detail:
                        result.append(detail)

        ended = (group.get('notices') or {}).get('ended')
        if ended:
            # Spec #21 L32: the leader's final summary is history, one collapsible line.
            collapsed = self.toggled.get('meta', True)
            self.collapsed['meta'] = collapsed
            text = ('▶ ' if collapsed else '▼ ') + ended['title']
            result.extend([RULE_ROW(), (text, None, Item('header', segments=[(text, 'dot_done')], group='meta'))])
            if not collapsed:
                result.extend(('  ' + line, None, None) for line in ended['body'].splitlines())
        return result + [('', None, None)]

    def worker(self, record, live, candidates, by_ticket):
        pane = live.get(record.get('pane'))
        matching = by_ticket.get(record['ticket'], [])
        task = matching[0] if len(matching) == 1 else None
        if not pane or pane.get('terminal_id') != record.get('terminal'):
            if record.get('state') != 'failed':
                return None  # Closed or replaced panes are history (spec #21 L36).
            reason = record.get('error') or record.get('operation') or 'abertura falhou'
            segments = [(f"{record['ticket']} · {record.get('pane') or '—'} · Bloqueado · {reason}", None)]
            item = Item('agent', 'blocked', segments, record.get('pane'), record.get('terminal'),
                        record['ticket'], unblock=self.prompt(record, reason), unblock_key=(record['ticket'], reason))
            return (segments[0][0], 'blocked', item), None
        actor = None
        if any(cwd and Path(cwd).resolve().is_relative_to(Path(record['worktree']).resolve())
               for cwd in (pane.get('foreground_cwd') or pane.get('cwd'),)):
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
        usage = None
        if actor:
            _, usage = describe({'binding': actor}, pane, self.cache, on_verified=read_activity)
        self.activities = {k: v for k, v in self.activities.items()
                           if k[0] != record.get('pane') or (verified and k == key)}

        status = pane.get('agent_status')
        block = record.get('blocked') or {}
        answered = status == 'working' and time.time() - block.get('at', 0) > BLOCK_GRACE
        if status == 'blocked' or record.get('state') == 'failed' or (block and not answered):
            state = 'blocked'
        elif status == 'working':
            state = 'working'
        elif (task and task.done) or (record.get('ready') and record['ready'].get('at', 0) >= block.get('at', 0)):
            state = 'done'
        else:
            state = 'idle'
        segments = [(f"{record['ticket']} · {record['pane']} · {LABELS[state]} · ", None)] + context(usage)
        reason = None
        if state == 'blocked':
            reason = block.get('reason') or record.get('error') or 'bloqueado no Herdr'
            segments.append((' · ' + reason, None))
        item = Item('agent', state, segments, record['pane'], record['terminal'], record['ticket'],
                    closable=state in ('idle', 'done'),
                    unblock=self.prompt(record, reason) if reason else None,
                    unblock_key=(record['ticket'], reason) if reason else None)
        detail = None
        if state == 'working':
            parts = [activity or (task.title if task else record.get('operation') or '')]
            checks = record.get('checks', [])
            if checks and not (task and task.done):
                parts.append(f"checagem inicial {len(checks)}/3 · {checks[-1]['summary']}")
            if len(checks) < 3 and record.get('state') == 'ready' and not (task and task.done):
                parts.append(f'próxima checagem prevista {len(checks) + 1}/3 aos {len(checks) + 2} min')
            text = ' · '.join(p for p in parts if p)
            if text:
                detail = ('  ' + text, None, Item('detail'))
        return (''.join(s for s, _ in segments), 'blocked' if state == 'blocked' else None, item), detail

    def queued(self, snapshot, tasks, records):
        if snapshot is None:
            return []
        result = []
        try:
            registered = {r['ticket'] for r in records}
            for entry in classify(snapshot, [t.id for t in tasks if not t.done]):
                ticket = re.match(r'^(T\d+)\b', entry['title'])
                if ticket and ticket[1] in registered:
                    continue
                note = entry['label'] if entry['label'] != 'livre' else 'aguardando executor'
                detail = ' · ' + '; '.join(entry['details']) if entry['details'] else ''
                text = entry['title'] + ' · na fila · ' + note + detail
                prompt = (f"[Unblock · {entry['title']}] A tarefa está na fila: \"{note}{detail}\". "
                          f"TODO: {self.repo / 'TODO.md'}. Veja se ela pode começar agora ou o que falta. "
                          + RULE.format(pane='do executor, quando houver'))
                item = Item('queue', 'queued', [(text, None)], ticket=entry['title'],
                            unblock=prompt, unblock_key=(entry['title'], note + detail))
                result.append((text, 'blocked', item))
        except (OSError, RuntimeError, ValueError, KeyError, TypeError):
            pass
        return result

    def prompt(self, record, reason):
        command = (f"{leader_kit.ROOT / 'watchdog'} kit desbloquear --repo {self.repo} "
                   f"--grupo {record.get('group')} --ticket {record['ticket']}")
        return (f"[Unblock · {record['ticket']}] O executor em {record.get('pane') or '—'} "
                f"(aba {short_tab(record.get('tab'))}) está bloqueado: \"{reason}\". "
                f"Contrato: {record.get('contract') or 'indisponível'}. "
                + RULE.format(pane=record.get('pane') or 'do executor')
                + f" Depois de responder, limpe o bloqueio: {command}")

    # -- explicit actions --------------------------------------------------
    def toggle(self, group):
        self.toggled[group] = not self.collapsed.get(group, False)

    def go(self, item, api=None):
        if not item or not item.pane:
            raise RuntimeError('Este item não tem pane')
        (api or Herdr()).call('agent', 'focus', item.pane)
        return 'Indo para ' + item.pane

    def close(self, item, api=None):
        if not item or not item.closable or item.leader:
            raise RuntimeError('Só um executor ocioso e não bloqueado pode ser fechado')
        api = api or Herdr()
        pane = api.call('pane', 'get', item.pane)['pane']
        if pane.get('terminal_id') != item.terminal:
            raise RuntimeError('O pane ' + item.pane + ' mudou; nada foi fechado')
        if pane.get('agent_status') not in ('idle', 'done'):
            raise RuntimeError(item.ticket + ' voltou a trabalhar; nada foi fechado')
        api.call('pane', 'close', item.pane)
        return item.ticket + ' fechado (' + item.pane + ')'

    def unblock(self, item, send=None):
        if not item or not item.unblock:
            raise RuntimeError('Selecione um item bloqueado ou na fila')
        if item.unblock_key in self.sent:
            return 'Unblock de ' + item.ticket + ' já enviado ao líder'
        if not self.leader_pane:
            raise RuntimeError('Líder indisponível; religue o painel')
        message = 'Unblock de ' + item.ticket + ' enviado ao líder'
        if send is None:
            from .pane_delivery import DeliveryPending, send as deliver
            try:
                deliver(self.leader_pane, item.unblock, api=Herdr())
            except DeliveryPending:
                message = 'Unblock de ' + item.ticket + ' na fila de entrega do líder'
        else:
            send(self.leader_pane, item.unblock)
        self.sent.add(item.unblock_key)
        return message
