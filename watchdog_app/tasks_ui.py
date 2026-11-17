"""Interactive project tasks, explicit routing and confirmed Codex suggestions."""
import curses
from pathlib import Path
import signal
import textwrap
import time

from .actions import Session, Busy
from .curate import ReviewJob, latest_reply, apply_review
from .todo import Snapshot, SECTIONS, change


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


class TasksUI:
    def __init__(self, screen, repo, binding_file):
        self.screen, self.repo = screen, Path(repo).resolve()
        self.snapshot = None
        self.selected, self.proposal_selected = set(), set()
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
        self.can_confirm = False
        try:
            self.session = Session(binding_file, self.repo)
        except (RuntimeError, OSError, ValueError, KeyError, TypeError) as error:
            self.session = Session(None, self.repo)
            self.notice = str(error)
        if not self.session.binding:
            self.review_status = 'Codex: unbound · open with watchdog to review or send'

    def refresh(self):
        try:
            snapshot = Snapshot.read(self.repo)
            if self.snapshot and snapshot.digest != self.snapshot.digest:
                self.selected.clear();self.result = None;self.proposal_selected.clear()
                self.job.close()
                if self.session.binding:
                    self.review_status = 'Codex: tasks changed · press r to review'
                if self.mode != 'tasks':
                    self.notice = 'Task list changed; confirmation cancelled'
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
        if self.session.binding and self.snapshot and time.monotonic() >= self.next_check:
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
        if self.mode == 'confirm':
            offer = self.pending
            title = {'done': 'Confirm completion', 'send': 'Confirm send',
                     'queue': 'Conversation is working — confirm queue',
                     'apply': 'Confirm reviewed changes'}[offer['kind']]
            rows.append((title, 'In progress', None))
            rows.append((self.session.label, None, None))
            if offer['kind'] in ('send', 'queue') and self.session.binding:
                rows.append(('Account: ' + self.session.binding.account, None, None))
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
        if not self.snapshot:
            return [('TODO.md is unavailable. Create or fix it in the project folder.', None, None)]
        suggestions = {a['id']: a for a in (self.result or {}).get('actions', []) if 'id' in a}
        for section in SECTIONS:
            tasks = [t for t in self.snapshot.tasks if t.section == section]
            rows.append((section.upper() + f' ({len(tasks)})', section, None))
            for task in tasks:
                marker = '[x]' if task.done else '[+]' if task.id in self.selected else '[ ]'
                rows.append((marker + ' ' + task.text, 'Done' if task.done else section, task.id))
                suggestion = suggestions.get(task.id)
                if suggestion:
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
        if self.mode == 'confirm':
            buttons = [('Confirm y', 'y'), ('Cancel Esc', 'escape')]
            hint = 'y: confirm · Esc: cancel · j/k: scroll'
        elif self.mode == 'proposals':
            buttons = [('Apply a', 'a'), ('Recheck R', 'R'), ('Back Esc', 'escape')]
            hint = 'Space: select · j/k: move · a: apply selected'
        else:
            buttons = [('Send s', 's'), ('Done d', 'd'), ('Review r', 'r'),
                       ('Start i', 'i'), ('Next n', 'n'), ('Quit q', 'q')]
            hint = 'Space: select · j/k: move · PgUp/PgDn'
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
            for part in textwrap.wrap(safe(text), max(4, w - 2), subsequent_indent='  ') or ['']:
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
            y = index + 4
            put(screen, y, text, attr)
            if identity is not None:
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

    def confirm(self, kind):
        self.require_selection()
        if kind == 'send':
            self.session.verify()
        self.pending = {'kind': kind, 'snapshot': self.snapshot, 'ids': set(self.selected)}
        self.mode, self.scroll = 'confirm', 0

    def execute(self):
        offer = self.pending
        if offer['kind'] in ('send', 'queue'):
            try:
                self.session.dispatch(offer['snapshot'], offer['ids'], offer['kind'] == 'queue')
            except Busy as error:
                if error.can_queue:
                    offer['kind'] = 'queue'
                    self.notice = 'Nothing sent yet. Confirm queue or cancel.'
                    return
                raise RuntimeError('The conversation is working; wait until idle. Selection kept.') from error
            self.notice = 'Queued selected tasks to this Codex thread; they remain open.'
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
        if self.mode == 'confirm':
            if key in ('y', 'enter') and self.can_confirm:
                self.execute()
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
        elif key == 's':
            self.confirm('send')
        elif key == 'd':
            self.confirm('done')
        elif key in ('i', 'n'):
            self.require_selection()
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
                return ' '
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
                curses.KEY_PPAGE: 'pageup', curses.KEY_HOME: 'home', curses.KEY_ENTER: 'enter',
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
                    if self.mode == 'confirm':
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
