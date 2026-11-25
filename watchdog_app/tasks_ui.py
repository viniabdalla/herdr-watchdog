"""Interactive project tasks, explicit routing and confirmed Codex suggestions."""
import curses
import os
import subprocess
from pathlib import Path
from dataclasses import asdict
import signal
import textwrap
import time

from .actions import Session, Busy
from .curate import ReviewJob, latest_reply, apply_review
from .todo import Snapshot, SECTIONS, change
from .clean_sessions import SETTLED, defaults as clean_defaults
from .clean_sessions_ui import Controller, Setup, confirmation_rows
from .checkpoint import pending, describe, conflicted, commit


def safe(text):
    return ''.join(c if c.isprintable() else ' ' for c in str(text))


def put(screen, y, text, attr=0, x=0):
    h, w = screen.getmaxyx()
    if 0 <= y < h and 0 <= x < w - 1:
        try:
            screen.addnstr(y, x, safe(text), w - x - 1, attr)
        except curses.error:
            pass


def colors():
    palette = {section: curses.A_BOLD for section in SECTIONS}
    try:
        if curses.has_colors():
            curses.start_color()
            try:
                curses.use_default_colors();background = -1
            except curses.error:
                background = curses.COLOR_BLACK
            bright = curses.COLORS >= 16
            for pair, (section, foreground) in enumerate((('Next', 12 if bright else curses.COLOR_BLUE),
                    ('In progress', 11 if bright else curses.COLOR_YELLOW),
                    ('Blocked', 9 if bright else curses.COLOR_RED),
                    ('Done', 10 if bright else curses.COLOR_GREEN)), 1):
                curses.init_pair(pair, foreground, background)
                palette[section] = curses.color_pair(pair)
    except curses.error:
        pass
    return palette


def remap(old, new, ids):
    """Selected task IDs in the new snapshot, or None if a selected block changed."""
    if old.format_version != new.format_version:
        return None
    lines_old = old.raw.decode('utf-8').splitlines(keepends=True)
    lines_new = new.raw.decode('utf-8').splitlines(keepends=True)
    blocks = {}
    for task in new.tasks:
        blocks.setdefault(''.join(lines_new[task.start:task.end]), []).append(task)
    result = set()
    for task in old.tasks:
        if task.id in ids:
            matches = blocks.get(''.join(lines_old[task.start:task.end]), [])
            if old.format_version:
                matches = [match for match in matches if match.id == task.id]
            if len(matches) != 1 or matches[0].section != task.section:
                return None
            result.add(matches[0].id)
    return result


def task_summary(snapshot, task):
    """Show only declared human summary; never fall back to technical task.text."""
    if task.summary:
        return task.summary
    lines = snapshot.raw.decode('utf-8').splitlines()
    for line in lines[task.start + 1:task.end]:
        text = line.strip()
        if text.startswith('Resumo:'):
            return text[len('Resumo:'):].strip() or 'Resumo ainda não informado.'
    return 'Conclusão registrada no histórico.' if task.done else 'Resumo ainda não informado.'


# Seleção, despacho ao líder, curador e verificação ficam disponíveis no painel.
# WATCHDOG_FULL_CONTROLS=1 restaura os fluxos anteriores de execução e edição manual.
def full_controls():
    return os.environ.get('WATCHDOG_FULL_CONTROLS') == '1'


DISABLED_KEYS = {'A', 'm', 'M', 'c', 'C', 'D', 'P', '0', 'o', 's', 'd', 'i', 'n'}


def verification_prompt(tasks):
    titles = '; '.join(task.title.strip() for task in tasks)
    return ('Verifique se estas tarefas do TODO.md estão realmente prontas: ' + titles + '. '
            'Para cada uma, confira o Resumo/Aceite contra as evidências (commits, testes, issue no GitHub) '
            'e responda: pronta (com evidência) ou não pronta (o que falta). '
            'Se confirmar, atualize o TODO.md e a issue.')


class TasksUI:
    def __init__(self, screen, repo, binding_file):
        self.screen, self.repo = screen, Path(repo).resolve()
        self.snapshot = None
        self.selected, self.proposal_selected = set(), set()
        self.expanded = set()
        self.cursor, self.scroll = 0, 0
        self.mode, self.pending = 'tasks', None
        self.notice, self.review_status = '', 'Codex: waiting for a completed reply'
        self.result = None
        self.job = ReviewJob()
        self.last_auto_key = None
        self.next_check = 0
        self.open_when_ready = False
        self.targets, self.mouse_armed = [], None
        self.palette = colors()
        self.clean = Controller(self.repo)
        self.binding_file = binding_file
        self.next_reconnect = 0
        self.can_confirm = False
        try:
            self.session = Session.for_panel(binding_file, self.repo) if binding_file else Session(None, self.repo)
        except (RuntimeError, OSError, ValueError, KeyError, TypeError) as error:
            self.session = Session(None, self.repo)
            self.notice = str(error)
        if not self.session.binding:
            self.review_status = 'Codex: unbound · open with watchdog to review or send'

    def refresh(self):
        if self.mode == 'audit' and time.monotonic() >= getattr(self, 'audit_refresh', 0):
            self.audit_refresh = time.monotonic() + 2
            try:
                self.audit.refresh(self.session)
            except (OSError, RuntimeError, ValueError, KeyError) as error:
                self.notice = str(error)
        try:
            if self.binding_file and not self.session.binding and time.monotonic()>=self.next_reconnect:
                self.next_reconnect=time.monotonic()+2
                self.clean.poll_file(self.binding_file)
                self.session=Session.for_panel(self.binding_file,self.repo)
            target = self.session.successor_file()
            if target:
                self.job.close()
                self.session = Session(target, self.repo)
                self.last_auto_key = None
                self.mode, self.pending = 'tasks', None
                self.notice = 'Panel ownership transferred · Tasks and Orchestrate now target ' + self.session.binding.session
            if self.session.binding:
                self.clean.poll(self.session.binding)
        except (RuntimeError, OSError, ValueError, KeyError, TypeError) as error:
            self.notice = str(error)
        try:
            snapshot = Snapshot.read(self.repo)
            if self.snapshot and snapshot.digest != self.snapshot.digest:
                if self.snapshot.format_version == snapshot.format_version == 1:
                    self.expanded.intersection_update(t.id for t in snapshot.tasks)
                else:
                    self.expanded = remap(self.snapshot, snapshot, self.expanded) or set()
                # Keep the selection when only other tasks changed (ideas added, rows moved).
                kept = remap(self.snapshot, snapshot, self.selected)
                changed = kept is None
                self.selected = kept or set()
                self.result = None;self.proposal_selected.clear()
                self.job.close()
                if self.session.binding:
                    self.review_status = 'Codex: tasks changed · press r to review'
                if self.mode == 'confirm' and self.pending and self.pending.get('ids') is not None and not changed:
                    self.pending.update(snapshot=snapshot, ids=set(self.selected))
                    if self.pending['kind'] in ('orchestrate', 'fresh'):
                        self.pending['changes'] = pending(self.repo)
                    self.notice = 'TODO changed elsewhere; selected tasks unchanged, confirmation updated'
                elif self.mode not in ('tasks', 'clean_setup', 'audit'):
                    self.notice = 'A selected task changed; confirmation cancelled. Select again.'
                    self.mode, self.pending = 'tasks', None
            self.snapshot = snapshot
        except (OSError, RuntimeError, UnicodeError) as error:
            self.snapshot = None
            self.notice = 'Cannot read TODO.md: ' + str(error)
        received = self.job.poll()
        if received:
            kind, result = received
            if kind == 'error':
                self.review_status = 'Codex review failed: ' + result
            elif self.snapshot and result['digest'] == self.snapshot.digest:
                self.result = result
                self.proposal_selected = set(range(len(result['actions'])))
                self.review_status = (f"Codex: {len(result['actions'])} suggestions · "
                                      f"{len(result['rejected'])} rejected · press r")
                if self.open_when_ready and self.mode == 'tasks':
                    self.mode, self.cursor, self.scroll = 'proposals', 0, 0
                self.open_when_ready = False
            else:
                self.review_status = 'Codex result is stale; press r to review again'
        if self.job.running:
            self.review_status = 'Codex: reviewing the last completed reply…'
        if (self.session.binding and self.snapshot and time.monotonic() >= self.next_check and
                not (self.clean.operation and self.clean.operation['state'] not in SETTLED)):
            self.next_check = time.monotonic() + 5
            try:
                source = latest_reply(self.session.binding)
                if source and source['key'] != self.last_auto_key and not self.job.running:
                    self.last_auto_key = source['key']
                    self.job.start(self.session, self.snapshot)
            except (OSError, RuntimeError, ValueError) as error:
                self.review_status = 'Codex review unavailable: ' + str(error)

    def body(self):
        rows = []
        if self.mode == 'audit':
            return self.audit.rows()
        if self.mode == 'dispatch':
            return [('Despachar', 'In progress', None),
                    ('Para um agente · revisão pelo líder', None, 'single'),
                    ('Orquestrar equipe · executor + QA', None, 'team'),
                    ('Novo agente · abrir executor e revisar pelo líder', None, 'fresh'),
                    ('Planejar · proposta antes de implementar', None, 'plan')]
        if self.mode == 'grouping':
            return [('Organizar as tarefas selecionadas', 'In progress', None),
                    ('Juntas · um agente para o conjunto', None, 'together'),
                    ('Separadas · um novo agente por tarefa', None, 'separate')]
        if self.mode == 'executors':
            rows = [('Escolher executor · uma tarefa por execução', 'In progress', None),
                    ('Somente sessões Codex ociosas em worktree limpa deste repositório.', None, None)]
            if not self.executor_choices:
                rows.append(('Nenhum executor elegível. Abra uma sessão dedicada em uma worktree limpa e isolada do projeto.', 'Blocked', None))
            for index, executor in enumerate(self.executor_choices):
                actor = executor['binding']
                rows.extend([(actor['pane'] + ' · ' + actor['session'], None, index),
                    ('Conta: ' + actor['account'], None, index),
                    ('Worktree: ' + executor['worktree'], None, index)])
            return rows
        if self.mode == 'clean_setup':
            return self.clean_setup.rows(self.session)
        if self.mode == 'confirm':
            offer = self.pending
            if offer['kind'] == 'clean':
                return confirmation_rows(self.session, offer['policy'])
            if offer['kind'] == 'clean_stuck':
                return self.clean.stuck_rows() if self.clean.stuck else [('Clean sessions is no longer stopped.', 'Done', None)]
            title = {'group_dispatch': 'Confirmar despacho', 'done': 'Confirm completion', 'send': 'Confirm send',
                     'queue': 'Conversation is working — confirm queue',
                     'fresh': 'Novo executor · confirmar',
                     'orchestrate': 'Confirm orchestration', 'single': 'Confirmar envio para um agente',
                     'apply': 'Review Curator · confirmar alterações',
                     'verify': 'Verify Leader · pedir verificação ao líder'}[offer['kind']]
            rows.append((title, 'In progress', None))
            rows.append((self.session.label, None, None))
            if offer['kind'] in ('send', 'queue', 'orchestrate') and self.session.binding:
                rows.append(('Account: ' + self.session.binding.account, None, None))
            if offer['kind'] in ('verify', 'group_dispatch'):
                rows.append(('Enviar para o painel ' + offer.get('pane', self.session.binding.pane) + ' · sessão ' + self.session.binding.session, None, None))
                rows.append(('', None, None))
                rows.extend((line, None, None) for line in textwrap.wrap(offer['prompt'], 70))
                rows.append(('', None, None))
                rows.append((('y digita a meta no pane do líder e aperta Enter.' if offer['kind'] == 'group_dispatch'
                              else 'y digita o pedido no prompt da sessão principal e aperta Enter.'), 'In progress', None))
            if offer['kind'] == 'single':
                actor = offer['executor']['binding']
                rows.extend([('Executor: ' + actor['pane'] + ' · ' + actor['session'], None, None),
                    ('Conta do executor: ' + actor['account'], None, None),
                    ('Worktree: ' + offer['executor']['worktree'], None, None),
                    ('Revisão pelo líder · evidências e commit exato antes de aprovar.', None, None),
                    ('A sessão escolhida será usada sem abrir outro agente. TODO continua aberto.', None, None),
                    ('', None, None)])
            if offer['kind'] in ('orchestrate', 'fresh'):
                rows.extend([(str(self.repo), None, None),
                    ('Main conversation: ' + self.session.binding.session, None, None),
                    ((('Novo executor · somente planejamento, sem implementação' if offer.get('purpose') == 'plan' else
                       'Novo executor · revisão pelo líder, sem QA') if offer['kind'] == 'fresh' else
                      'Team: one Codex worker + one Codex QA'), None, None),
                    ('One new execution tab; each agent gets an isolated worktree.', None, None),
                    ('Main prepares the brief and coordinates. TODO stays open.', None, None),
                    ('', None, None)])
                if offer['kind'] == 'fresh':
                    rows.append(('Tarefas: ' + ('separadas, um agente por tarefa' if offer.get('grouping') == 'separate' else 'juntas em um contrato'), None, None))
                elif len(offer['ids']) > 1:
                    rows.append((f"Uma entrega conjunta · {len(offer['ids'])} tarefas · um executor e um QA", None, None))
                changes = offer.get('changes')
                if changes is None:
                    rows.append(('Checkpoint: not a Git repository; nothing will be committed.', None, None))
                elif not changes:
                    rows.append(('Checkpoint: project is clean; the run starts from HEAD.', 'Done', None))
                else:
                    rows.append((f'Checkpoint: y saves these {len(changes)} change(s) in one local commit '
                                 '(no push), then starts the run:', 'In progress', None))
                    rows.extend(('  ' + line, None, None) for line in describe(changes))
                for previous, reason in offer.get('settle', []):
                    rows.append(('Closes earlier run ' + previous['id'][:8] + ': ' + reason, 'Blocked', None))
                rows.append(('', None, None))
            if offer['kind'] == 'apply':
                for index in sorted(offer['indices']):
                    action = offer['result']['actions'][index]
                    rows.append((action['kind'].upper() + ': ' + action['text'],
                                 'Blocked' if action['kind'] == 'blocked' else 'Done', None))
            else:
                rows.append((f"{len(offer['ids'])} selected task(s)", None, None))
                for task in offer['snapshot'].selected(offer['ids']):
                    rows.append(('- ' + task.text, None, None))
            rows.append(('', None, None))
            rows.append(('Sending keeps the task open.' if offer['kind'] in ('send', 'queue')
                         else 'Only confirm after checking the selected changes.', None, None))
            return rows
        if self.mode == 'proposals':
            rows.append(('Review Curator · propostas', 'In progress', None))
            if not self.result:
                return [('No review is available yet.', None, None)]
            source = self.result['source']
            rows.append(('Last completed reply: ' + source['timestamp'], None, None))
            rows.append(('Proposals only — TODO.md has not changed.', None, None))
            rows.append(('', None, None))
            for index, action in enumerate(self.result['actions']):
                section = {'done': 'Done', 'blocked': 'Blocked', 'add': 'Next'}[action['kind']]
                marker = '[+]' if index in self.proposal_selected else '[ ]'
                rows.append((marker + ' ' + action['kind'].upper() + ': ' + action['text'], section, index))
                if action['kind'] == 'blocked':
                    rows.append(('Reason: ' + action['reason'], section, index))
                rows.append(('Quote: ' + action['evidence'], None, index))
                rows.append(('', None, None))
            if not self.result['actions']:
                rows.append(('No task changes are supported by this reply.', None, None))
            for error in self.result['rejected']:
                rows.append(('Withheld: ' + error, 'Blocked', None))
            return rows
        rows.extend(self.clean.rows())
        rows.extend(self.run_rows())
        if not self.snapshot:
            return rows + [('TODO.md is unavailable. Create or fix it in the project folder.', None, None)]
        suggestions = {a['id']: a for a in (self.result or {}).get('actions', []) if 'id' in a}
        for section in SECTIONS:
            tasks = [t for t in self.snapshot.tasks if t.section == section]
            rows.append((section.upper() + f' ({len(tasks)})', section, None))
            for task in tasks:
                marker = '[x]' if task.done else '[+]' if task.id in self.selected else '[ ]'
                opened = task.id in self.expanded
                arrow = '▾' if opened else '▸'
                title = task.title.split(' — Blocked: ', 1)[0]
                rows.append((marker + ' ' + arrow + ' ' + title, 'Done' if task.done else section, task.id))
                if opened:
                    rows.append(('', None, None))
                    rows.append(('    Resumo:', None, None))
                    for line in task_summary(self.snapshot, task).splitlines():
                        rows.append(('      ' + line if line else '', None, None))
                    rows.append(('', None, None))
                    status = {'Next': 'Pendente', 'In progress': 'Em andamento',
                              'Blocked': 'Bloqueada', 'Done': 'Concluída'}[section]
                    rows.append(('    Situação: ' + status, section, None))
                    reason = task.reason or (task.title.split(' — Blocked: ', 1)[1]
                                            if ' — Blocked: ' in task.title else '')
                    if reason:
                        rows.append(('      Motivo: ' + reason, section, None))
                    rows.append(('', None, None))
                suggestion = suggestions.get(task.id)
                if suggestion and opened:
                    status = 'Done' if suggestion['kind'] == 'done' else 'Blocked'
                    detail = ': ' + suggestion['reason'] if status == 'Blocked' else ''
                    rows.append(('  ? Suggested ' + status + detail, status, task.id))
            if not tasks:
                rows.append(('  None', None, None))
            rows.append(('', None, None))
        return rows

    def draw(self):
        screen = self.screen
        screen.erase()
        h, w = screen.getmaxyx()
        self.targets, self.can_confirm = [], False
        put(screen, 0, 'WATCHDOG / TASKS', curses.A_BOLD)
        put(screen, 1, self.repo.name + ' · ' + self.session.label)
        if h < 10 or w < 24:
            put(screen, h - 2, 'Enlarge this pane · q exits')
            screen.refresh()
            return
        put(screen, 2, self.review_status)
        put(screen, 3, self.notice, curses.A_BOLD)
        if self.mode == 'audit':
            buttons = [('Confirmar y', 'y'), ('Escolher Enter', 'enter'), ('Cancelar Esc', 'escape')]
            hint = 'Setas/j/k: escolher · Enter/clique: continuar · y: confirmar · Esc: cancelar'
        elif self.mode == 'confirm':
            buttons = [('Confirm y', 'y'), ('Cancel Esc', 'escape')]
            hint = 'y: confirm · Esc: cancel · j/k: scroll'
        elif self.mode in ('dispatch', 'executors', 'grouping'):
            buttons = [('Escolher Enter', 'enter'), ('Cancelar Esc', 'escape')]
            hint = 'Setas/j/k: escolher · Enter/clique: continuar · Esc: cancelar'
        elif self.mode == 'clean_setup':
            buttons = [('Review Enter', 'enter'), ('Cancel Esc', 'escape')]
            hint = 'Tab/Up/Down: field · type to edit · Ctrl+U: clear · Enter: review'
        elif self.mode == 'proposals':
            buttons = [('Apply a', 'a'), ('Recheck R', 'R'), ('Back Esc', 'escape')]
            hint = 'Space: select · j/k: move · a: apply selected'
        elif not full_controls():
            buttons = [('Review Curator r', 'r'), ('Verify Leader v', 'v'), ('Despachar p', 'p'), ('Quit q', 'q')]
            hint = 'Space: selecionar · Enter/▸: resumo · r: Review Curator · v: Verify Leader'
        else:
            buttons = [('Auditoria A', 'A'), ('Agents m', 'm'), ('Clean sessions c', 'c'), ('Despachar p', 'p'), ('Orchestrate o', 'o'), ('Send s', 's'), ('Done d', 'd'), ('Review Curator r', 'r'), ('Verify Leader v', 'v'),
                       ('Start i', 'i'), ('Next n', 'n'), ('Envio avançado D', 'D'), ('Quit q', 'q')]
            hint = 'Space: select · Enter/▸: resumo · r: Review Curator · v: Verify Leader · 0: novo agente · P: planejar · C: opções'
        packed, x, line = [], 0, 0
        for label, action in buttons:
            label = '[' + label + ']'
            if x and x + len(label) >= w:
                line += 1;x = 0
            packed.append((line, x, label, action));x += len(label) + 1
        footer = h - line - 2
        room = max(1, footer - 4)
        rows = []
        for text, section, identity in self.body():
            indent = max(2, len(text) - len(text.lstrip()))
            if self.mode == 'tasks' and identity is not None:
                indent = 6
            for part in textwrap.wrap(safe(text), max(4, w - 2), subsequent_indent=' ' * indent) or ['']:
                rows.append((part, section, identity))
        identifiers = list(dict.fromkeys(identity for _, _, identity in rows if identity is not None))
        self.cursor = min(self.cursor, max(0, len(identifiers) - 1))
        focus = identifiers[self.cursor] if identifiers else None
        if getattr(self, 'follow_cursor', True) and focus is not None:
            position = next(i for i, row in enumerate(rows) if row[2] == focus)
            if position < self.scroll:
                self.scroll = position
            elif position >= self.scroll + room:
                self.scroll = position - room + 1
        self.follow_cursor = False
        self.scroll = max(0, min(self.scroll, max(0, len(rows) - room)))
        for index, (text, section, identity) in enumerate(rows[self.scroll:self.scroll + room]):
            attr = self.palette.get(section, 0)
            if identity is not None and identity == focus:
                attr |= curses.A_REVERSE
            if text.strip() == 'Resumo:' or text.strip().startswith('Situação:'):
                attr |= curses.A_BOLD
            y = index + 4
            put(screen, y, text, attr)
            if identity is not None:
                if self.mode == 'tasks':
                    self.targets.append((4, y, w - 5, ('toggle', identity)))
                    self.targets.append((0, y, 4, ('item', identity)))
                else:
                    self.targets.append((0, y, w - 1, ('item', identity)))
        for offset, x, label, action in packed:
            y = footer + offset
            put(screen, y, label, curses.A_REVERSE, x)
            self.targets.append((x, y, len(label), ('key', action)))
        self.can_confirm = self.mode == 'confirm'
        put(screen, h - 1, hint, curses.A_DIM)
        screen.refresh()
        self.visible_identifiers = identifiers

    def require_selection(self):
        if not self.snapshot:
            raise RuntimeError('TODO.md is unavailable')
        self.snapshot.selected(self.selected)

    def fresh_dispatch(self, purpose='implementation'):
        self.require_selection(); self.session.verify()
        self.dispatch_purpose = purpose
        self.dispatch_grouping = 'together'
        if len(self.selected) > 1:
            self.mode, self.cursor, self.scroll = 'grouping', 0, 0
        else:
            self.confirm('fresh')

    def confirm(self, kind, executor=None):
        self.require_selection()
        if kind in ('send', 'orchestrate', 'single', 'fresh'):
            self.session.verify()
        self.pending = {'kind': kind, 'snapshot': self.snapshot, 'ids': set(self.selected)}
        if kind == 'fresh':
            self.pending.update(purpose=getattr(self, 'dispatch_purpose', 'implementation'),
                                grouping=getattr(self, 'dispatch_grouping', 'together'))
        if kind == 'single':
            from .mission_single import validate_executor, available
            from .mission_launch import git
            from .mission import RunStore
            if len(self.selected) != 1:
                raise RuntimeError('Para um agente: selecione uma tarefa por execução')
            validate_executor(self.repo, asdict(self.session.binding), executor, base=git(self.repo, 'rev-parse', 'HEAD'))
            available(RunStore(), self.repo, executor)
            changes = pending(self.repo) or []
            if any(path != 'TODO.md' for _, path in changes):
                raise RuntimeError('Salve as alterações do projeto antes de despachar para a worktree existente')
            self.pending['executor'] = executor
        if kind in ('orchestrate', 'fresh'):
            from .mission import RunStore, blocking
            from .mission_scope import capture
            tasks = self.snapshot.selected(self.selected)
            settle, live = blocking(RunStore(), self.repo, capture(self.snapshot, tasks), tasks, self.snapshot)
            if live:
                raise RuntimeError('These tasks already have a running team ' + live[0]['id'][:8] +
                                   '. Follow it in Progress, or close it there with x to start over.')
            changes = pending(self.repo)
            if changes and conflicted(changes):
                raise RuntimeError('Resolve merge conflicts before Orchestrate: ' + ', '.join(conflicted(changes)))
            self.pending.update(changes=changes, settle=settle)
        self.mode, self.scroll = 'confirm', 0

    def busy(self, text):
        """Immediate visible feedback before a slow confirmed action."""
        self.notice = text
        try:
            self.draw()
        except Exception:
            pass  # Feedback is best effort; the action itself still runs.

    def run_rows(self):
        """Live state of this project's unfinished runs, so every click has visible effect."""
        from .mission import RunStore, run_status
        rows = []
        try:
            for run in RunStore().list(self.repo):
                status = run_status(run)
                if status['finished']:
                    continue
                rows.append(('RUN ' + run['id'][:8] + ' · ' + status['label'] + ' · ' + status['detail'],
                             status['section'], None))
        except (OSError, ValueError, KeyError, RuntimeError) as error:
            rows.append(('Runs unavailable: ' + str(error), 'Blocked', None))
        return rows + ([('', None, None)] if rows else [])

    def in_live_run(self, ids):
        from .mission import RunStore, FINISHED
        texts = {t.text for t in self.snapshot.selected(ids)}
        for run in RunStore().list(self.repo):
            stable_overlap = (self.snapshot.format_version == 1 and run.get('scope', {}).get('version') == 2
                              and set(ids) & set(run['tasks']))
            if run['phase'] not in FINISHED and (stable_overlap or texts & {t['title'] for t in run['tasks'].values()}):
                return run
        return None

    def execute(self):
        offer = self.pending
        self.busy('Working…')
        if offer['kind'] == 'clean_stuck':
            operation = self.clean.retry()
            self.notice = 'Clean sessions retrying · ' + operation['operation_id'][:8] + ' · see the status above'
        elif (offer['kind'] != 'clean' and self.clean.operation and
                self.clean.operation['state'] not in SETTLED):
            raise RuntimeError('Clean sessions '+self.clean.operation['state']+'; press c to retry or close it')
        elif offer['kind'] == 'clean':
            self.job.close()
            operation = self.clean.start(self.session, offer['policy'])
            self.notice = 'Clean sessions ' + operation['state'] + ' · ' + operation['operation_id']
        elif offer['kind'] == 'group_dispatch':
            from .dispatch import deliver
            deliver(self.session, offer)
            self.notice = 'Despacho enviado · grupo com ' + str(len(offer['group']['members'])) + ' tarefa(s)'
        elif offer['kind'] == 'verify':
            self.session.verify()
            pane = self.session.binding.pane
            for command in (['herdr', 'pane', 'send-text', pane, offer['prompt']], ['herdr', 'pane', 'send-keys', pane, 'enter']):
                result = subprocess.run(command, capture_output=True, text=True, timeout=10)
                if result.returncode:
                    raise RuntimeError('Envio ao painel ' + pane + ' falhou: ' + (result.stderr.strip() or 'erro do herdr'))
            self.notice = f"Pedido de verificação enviado à sessão principal ({len(offer['ids'])} tarefa(s))"
        elif offer['kind'] in ('send', 'queue'):
            try:
                self.session.dispatch(offer['snapshot'], offer['ids'], offer['kind'] == 'queue')
            except Busy as error:
                if error.can_queue:
                    offer['kind'] = 'queue'
                    self.notice = 'Nothing sent yet. Confirm queue or cancel.'
                    return
                raise RuntimeError('The conversation is working; wait until idle. Selection kept.') from error
            self.notice = 'Queued selected tasks to this Codex thread; they remain open.'
        elif offer['kind'] == 'single':
            from .mission import request
            run = request(self.session, offer['snapshot'], offer['ids'], confirmed=True,
                          mode='single', executor=offer['executor'])
            self.notice = 'Execução ' + run['id'][:8] + ' · preparando contrato · acompanhe em Progresso'
        elif offer['kind'] in ('orchestrate', 'fresh'):
            from .mission import request
            self.busy('Saving checkpoint and starting the run…')
            saved = None
            if offer.get('changes') is not None:
                saved = commit(self.repo, offer['changes'], 'chore: Watchdog checkpoint before Orchestrate\n\n' +
                               '\n'.join('- ' + t.text for t in offer['snapshot'].selected(offer['ids'])))
            if offer['kind'] == 'fresh':
                from .mission import request_batch
                runs = request_batch(self.session, offer['snapshot'], offer['ids'], confirmed=True, checkpoint=saved,
                                     grouping=offer['grouping'], purpose=offer['purpose'])
                run = runs[0]
            else:
                run = request(self.session, offer['snapshot'], offer['ids'], confirmed=True, checkpoint=saved,
                              grouping='together' if len(offer['ids']) > 1 else 'single')
            self.notice = ('Checkpoint ' + saved['sha'][:8] + ' saved · ' if saved and saved['created'] else '') + \
                'Run ' + run['id'][:8] + ' · preparing the brief · see Progress'
        elif offer['kind'] == 'done':
            change(offer['snapshot'], [{'kind': 'done', 'id': key} for key in sorted(offer['ids'])])
            self.notice = f"Marked {len(offer['ids'])} task done" if len(offer['ids']) == 1 else f"Marked {len(offer['ids'])} tasks done"
        else:
            apply_review(self.session, offer['snapshot'], offer['result'], offer['indices'])
            self.notice = f"Applied {len(offer['indices'])} reviewed changes"
            self.result = None
        self.mode, self.pending = 'tasks', None
        self.selected.clear();self.scroll = 0;self.cursor = 0;self.follow_cursor = True

    def handle(self, key):
        if key == 'escape':
            if self.mode != 'tasks':
                self.mode, self.pending = 'tasks', None
                self.notice = 'Cancelled';self.scroll = 0;self.cursor = 0;self.follow_cursor = True
            else:
                return False
            return True
        h, w = self.screen.getmaxyx()
        if h < 10 or w < 24:
            return key != 'q'
        if self.mode == 'audit':
            if key in ('up', 'k', 'down', 'j'):
                self.cursor = max(0, self.cursor + (1 if key in ('down', 'j') else -1))
                self.follow_cursor = True
            elif key in ('enter', ' ', 'y'):
                if self.audit.stage in ('confirm', 'deliver'):
                    self.busy('Abrindo auditoria…' if self.audit.stage == 'confirm' else 'Entregando relatório…')
                    self.notice = self.audit.confirm(self.session)
                    self.mode = 'tasks'
                elif key != 'y':
                    ids = getattr(self, 'visible_identifiers', [])
                    if ids:
                        self.cursor = self.audit.choose(ids[min(self.cursor, len(ids)-1)])
                        self.scroll = 0; self.follow_cursor = True
            elif key in ('pageup', 'pagedown'):
                self.scroll = max(0, self.scroll + (max(1, h-8) if key == 'pagedown' else -max(1, h-8)))
                self.follow_cursor = False
            return True
        if self.mode == 'clean_setup':
            if key == 'enter':
                self.session.verify()
                self.pending = {'kind': 'clean', 'policy': self.clean_setup.policy.copy()}
                self.mode, self.scroll = 'confirm', 0
            else:
                self.clean_setup.handle(key)
            return True
        if key in ('up', 'k', 'down', 'j'):
            if self.mode == 'confirm':
                self.scroll = max(0, self.scroll + (1 if key in ('down', 'j') else -1))
            else:
                self.cursor = max(0, self.cursor + (1 if key in ('down', 'j') else -1))
                self.follow_cursor = True
            return True
        if key in ('pageup', 'pagedown'):
            self.scroll = max(0, self.scroll + (max(1, h - 8) if key == 'pagedown' else -max(1, h - 8)))
            self.follow_cursor = False
            return True
        if key == 'home':
            self.cursor, self.scroll, self.follow_cursor = 0, 0, True
            return True
        if self.mode == 'confirm' and self.pending and self.pending['kind'] == 'clean_stuck':
            if key == 'x' and self.clean.stuck:
                self.busy('Closing…')
                operation = self.clean.close()
                self.notice = 'Clean sessions ' + operation['operation_id'][:8] + ' closed · press c to start again'
                self.mode, self.pending = 'tasks', None
            elif key in ('y', 'enter') and self.clean.stuck and self.clean.stuck['state'] == 'partial':
                self.execute()
            return True
        if self.mode == 'confirm':
            if key in ('y', 'enter') and self.can_confirm:
                self.execute()
            return True
        if self.mode in ('dispatch', 'executors', 'grouping'):
            if key in ('enter', ' '):
                identities = getattr(self, 'visible_identifiers', [])
                if not identities:
                    return True
                identity = identities[min(self.cursor, len(identities) - 1)]
                if self.mode == 'grouping':
                    self.dispatch_grouping = identity
                    self.confirm('fresh')
                elif self.mode == 'dispatch':
                    if identity in ('fresh', 'plan'):
                        self.fresh_dispatch('plan' if identity == 'plan' else 'implementation')
                    elif identity == 'team':
                        self.confirm('orchestrate')
                    else:
                        self.require_selection()
                        if len(self.selected) != 1:
                            raise RuntimeError('Para um agente: selecione uma tarefa por execução')
                        from .mission_single import choices
                        self.executor_choices, _ = choices(self.repo, asdict(self.session.binding))
                        self.mode, self.cursor, self.scroll = 'executors', 0, 0
                else:
                    self.confirm('single', self.executor_choices[identity])
            return True
        if self.mode == 'tasks' and key in ('enter', 'toggle', 'left', 'right'):
            identities = getattr(self, 'visible_identifiers', [])
            if identities:
                identity = identities[min(self.cursor, len(identities) - 1)]
                if key == 'right':
                    self.expanded.add(identity)
                elif key == 'left':
                    self.expanded.discard(identity)
                else:
                    self.expanded.symmetric_difference_update({identity})
            return True
        if key in (' ', 'enter'):
            identities = getattr(self, 'visible_identifiers', [])
            if not identities:
                return True
            identity = identities[min(self.cursor, len(identities) - 1)]
            if self.mode == 'proposals':
                selected = self.proposal_selected
            else:
                self.snapshot.selected({identity})
                selected = self.selected
            selected.symmetric_difference_update({identity})
            self.notice = (f'{len(selected)} proposal(s) selected' if self.mode == 'proposals'
                           else f'{len(selected)} task(s) selected')
        elif self.mode == 'proposals':
            if key == 'a':
                if not self.proposal_selected:
                    raise RuntimeError('Select at least one verified proposal')
                self.pending = {'kind': 'apply', 'snapshot': self.snapshot, 'result': self.result,
                                'indices': set(self.proposal_selected)}
                self.mode, self.scroll = 'confirm', 0
            elif key == 'R':
                self.job.start(self.session, self.snapshot, force=True)
                self.mode = 'tasks';self.open_when_ready = True
        elif key == 'q':
            return False
        elif not full_controls() and key in DISABLED_KEYS:
            return True
        elif key == 'p':
            self.require_selection()
            from .dispatch import preview
            self.pending = preview(self.session, self.snapshot, self.selected)
            self.mode, self.scroll = 'confirm', 0
        elif key == 'v':
            self.require_selection()
            if not self.selected:
                raise RuntimeError('Selecione as tarefas com Space antes de pedir verificação')
            self.session.verify()
            self.pending = {'kind': 'verify', 'snapshot': self.snapshot, 'ids': set(self.selected),
                            'prompt': verification_prompt(self.snapshot.selected(self.selected))}
            self.mode, self.scroll = 'confirm', 0
        elif key == 'A':
            from .audit_ui import AuditUI
            self.audit = AuditUI(self.session)
            self.mode, self.cursor, self.scroll = 'audit', 0, 0
            self.follow_cursor = True
        elif key in ('m', 'M'):
            self.session.verify()
            from .panes import open_pane
            pane = open_pane(self.session.file, self.repo, 'agents')
            self.notice = 'Agents aberto · ' + pane['pane_id']
        elif key == 'c' and self.clean.stuck and self.clean.stuck.get('problem') == 'Preparation base changed before Git authorization':
            self.pending = {'kind': 'clean_stuck'}
            self.execute()
        elif key == 'c' and self.clean.stuck:
            self.pending = {'kind': 'clean_stuck'}
            self.mode, self.scroll = 'confirm', 0
        elif key == 'c':
            self.session.verify()
            if self.clean.operation and self.clean.operation['state'] not in SETTLED:
                self.notice = 'Clean sessions · ' + self.clean.operation['stage']
            else:
                self.job.close()
                policy = clean_defaults(self.session)
                if not policy['remote'] or not policy['branch']:
                    self.clean_setup = Setup(self.session)
                    self.mode, self.scroll = 'clean_setup', 0
                    self.notice = 'Escolha o destino do push para esta worktree'
                    return True
                operation = self.clean.start(self.session, policy, automatic=True)
                self.notice = 'Clean sessions ' + operation['state'] + ' · ' + operation['operation_id']
        elif key == 'C':
            self.session.verify()
            self.clean_setup = Setup(self.session)
            self.mode, self.scroll = 'clean_setup', 0
        elif key == 'P':
            self.fresh_dispatch('plan')
        elif key == '0':
            self.fresh_dispatch()
        elif key == 'D':
            self.require_selection(); self.session.verify()
            self.mode, self.cursor, self.scroll = 'dispatch', 0, 0
        elif key == 'o':
            self.confirm('orchestrate')
        elif key == 's':
            self.confirm('send')
        elif key == 'd':
            self.confirm('done')
        elif key in ('i', 'n'):
            self.require_selection()
            run = self.in_live_run(self.selected)
            if run:
                raise RuntimeError('Task is part of run ' + run['id'][:8] + '; moving it would change its '
                                   'contract. Finish it, or close the run in Progress (x) and Orchestrate again.')
            change(self.snapshot, [{'kind': 'start' if key == 'i' else 'next', 'id': k} for k in self.selected])
            self.notice = 'Moved selected tasks to ' + ('In progress' if key == 'i' else 'Next')
            self.selected.clear()
        elif key in ('r', 'R'):
            self.session.verify()
            if self.result and key == 'r':
                self.mode, self.cursor, self.scroll = 'proposals', 0, 0
            elif self.snapshot:
                self.job.start(self.session, self.snapshot, force=key == 'R')
                self.open_when_ready = True
        return True

    def mouse(self):
        try:
            _, x, y, _, mask = curses.getmouse()
        except curses.error:
            return None
        if mask & curses.BUTTON4_PRESSED:
            return 'pageup'
        if mask & getattr(curses, 'BUTTON5_PRESSED', 0):
            return 'pagedown'
        target = next((action for left, row, width, action in self.targets if row == y and left <= x < left + width), None)
        if mask & curses.BUTTON1_PRESSED:
            self.mouse_armed = target
            return None
        clicked = mask & (curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED)
        released = mask & curses.BUTTON1_RELEASED and self.mouse_armed == target
        self.mouse_armed = None
        if target and (clicked or released):
            kind, value = target
            if kind == 'key':
                return value
            identities = getattr(self, 'visible_identifiers', [])
            if value in identities:
                self.cursor = identities.index(value)
                return 'toggle' if kind == 'toggle' else ' '
        return None

    def loop(self):
        screen = self.screen
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        screen.keypad(True);screen.timeout(300)
        curses.mouseinterval(150)
        curses.mousemask(curses.ALL_MOUSE_EVENTS)
        keys = {curses.KEY_UP: 'up', curses.KEY_DOWN: 'down', curses.KEY_NPAGE: 'pagedown',
                curses.KEY_LEFT: 'left', curses.KEY_RIGHT: 'right',
                curses.KEY_PPAGE: 'pageup', curses.KEY_HOME: 'home', curses.KEY_ENTER: 'enter',
                curses.KEY_BACKSPACE: 'backspace', curses.KEY_BTAB: 'backtab',
                '\n': 'enter', '\r': 'enter', '\x1b': 'escape'}
        try:
            while True:
                self.refresh();self.draw()
                try:
                    raw = screen.get_wch()
                except curses.error:
                    continue
                key = self.mouse() if raw == curses.KEY_MOUSE else keys.get(raw, raw)
                if key is None:
                    continue
                try:
                    if not self.handle(key):
                        return
                except (RuntimeError, OSError, ValueError, KeyError, TypeError) as error:
                    self.notice = str(error)
                    if self.mode in ('confirm', 'audit'):
                        self.mode, self.pending = 'tasks', None
        finally:
            self.job.close()


def run(repo, binding_file=None):
    def stop(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGHUP, stop)
    try:
        curses.wrapper(lambda screen: TasksUI(screen, repo, binding_file).loop())
    except KeyboardInterrupt:
        pass
