"""Watchdog's local adaptation of the Left Undone agents monitor.

Only native actors recorded for this exact leader are shown; old runs stay history.
No dispatches, reviews, task updates or Left Undone database writes occur here.
"""
import curses
from dataclasses import asdict
import json
from pathlib import Path
import textwrap
import time

from . import bindings
from .actions import Session
from .agent_usage import read_usage, claude_usage, claude_window, usage_meter, abbreviate
from .herdr import Herdr
from .mission import RunStore
from .store import atomic
from .tasks_ui import put, safe


def agent_rows(session, runs):
    main = asdict(session.binding)
    rows = [{'main': True, 'binding': main, 'label': 'SESSÃO PRINCIPAL', 'delivery': '', 'task': ''}]
    seen = {(main['kind'], main['account'], main['session'])}
    for run in runs:
        leader = run.get('main', {})
        if any(leader.get(k) != main[k] for k in ('kind', 'account', 'session')):
            continue
        for role, part in run.get('participants', {}).items():
            actor = part.get('native')
            if not actor:
                continue  # Legacy/export-only actors have no verified native binding.
            identity = (actor['kind'], actor['account'], actor['session'])
            if identity in seen:
                continue
            seen.add(identity)
            tasks = list(run.get('tasks', {}).values())
            state = ('Encerrada' if run.get('phase') == 'closed' else
                     'Aceita' if run.get('phase') == 'done' else
                     'Bloqueada' if any(t.get('state') == 'blocked' for t in tasks) else
                     'Aguardando revisão' if tasks and all(t.get('state') in ('review', 'done') for t in tasks) else
                     'Em andamento')
            rows.append({'main': False, 'binding': actor,
                'label': role.upper() + ' · ' + run['id'][:8], 'delivery': state,
                'task': ' · '.join(t.get('title', '') for t in tasks),
                'model': part.get('model', ''), 'effort': part.get('effort', '')})
    return rows


def describe(row, pane, cache, window=None, *, on_verified=None, trusted=None, ttl=30):
    """trusted: {identity: last verification}; Progress reuses a check for ttl seconds."""
    actor = row['binding']
    if not pane or pane.get('terminal_id') != actor['terminal']:
        return 'Fechado', None
    native = pane.get('agent_session') or {}
    if (pane.get('agent') != actor['kind'] or native.get('kind') != 'id' or
            native.get('value') != actor['session']):
        return 'Sessão alterada', None
    state = {'working': 'Trabalhando', 'idle': 'Ocioso', 'done': 'Ocioso',
             'blocked': 'Bloqueado'}.get(pane.get('agent_status'), 'Desconhecido')
    try:
        runtime = bindings.engine()
        binding = runtime.Binding(**actor)
        key = (actor['pane'], actor['terminal'], actor['kind'], actor['session'], actor.get('history'))
        now = time.monotonic()
        if trusted is None or now - trusted.get(key, float('-inf')) >= ttl:
            runtime.verify(binding)
            if trusted is not None:
                trusted[key] = now
        if on_verified: on_verified(binding)
        path = Path(actor['history'])
        if actor['kind'] == 'codex':
            context, size, total = read_usage(path, cache)
        elif actor['kind'] == 'claude':
            context, total, model = claude_usage(path, cache, actor['session'])
            size = claude_window(context, model, window) if context is not None else None
        else:
            return state, None
        return state, {'context': context, 'window': size, 'total': total}
    except (OSError, ValueError, RuntimeError, KeyError, TypeError):
        return state, None


def monitor_lines(rows, width):
    """Wrap before scrolling; narrow panes retain all addresses and usage."""
    lines = []
    for row, state, usage, pane in rows:
        def add(text, style='normal'):
            lines.extend((line, style) for line in textwrap.wrap(safe(text), max(4, width)) or [''])
        add(row['label'], 'heading')
        actor = row['binding']
        address = (pane or {}).get('tab_id', '—') + ' / ' + actor['pane']
        add(('○ ' if state == 'Ocioso' else '● ') + state + ' · ' + address,
            'blocked' if state in ('Bloqueado', 'Sessão alterada', 'Fechado') else 'active' if state == 'Trabalhando' else 'normal')
        add(actor['kind'] + ' · ' + actor['session'][:8] + ' · ' + actor['account'], 'dim')
        add(usage_meter(usage), 'context')
        if row['delivery']:
            add('Entrega: ' + row['delivery'])
        if row.get('model'):
            add(row['model'] + ' · ' + row.get('effort', ''), 'dim')
        if row['task']:
            add(row['task'], 'dim')
        lines.append(('', 'normal'))
    if len(rows) == 1:
        lines.append(('Nenhum subagente associado a esta sessão.', 'dim'))
    totals = [usage['total'] for row, _, usage, _ in rows if not row['main'] and usage and usage.get('total') is not None]
    if totals:
        lines.append(('Tokens conhecidos dos subagentes: ' + abbreviate(sum(totals)), 'dim'))
    return lines


def edit_window(screen, root, current):
    from .picker import text
    digits = str(current or '')
    replace = True
    while True:
        screen.erase()
        text(screen, 0, 0, 'Janela de contexto Claude (vazio = automático)')
        text(screen, 2, 0, digits)
        text(screen, 4, 0, 'Enter: salvar · Esc: cancelar')
        screen.refresh()
        key = screen.getch()
        if key == 27:
            return current
        if key in (10, 13, curses.KEY_ENTER):
            value = int(digits) if digits else None
            if value is None or value > 0:
                atomic(root / 'agents-preferences.json', {'claude_window': value})
                return value
        elif key in (127, 8, curses.KEY_BACKSPACE):
            digits = digits[:-1]; replace = False
        elif 48 <= key <= 57 and (replace or len(digits) < 12):
            digits = chr(key) if replace else digits + chr(key); replace = False


def panel(screen, repo, binding_file):
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    screen.keypad(True); screen.timeout(500)
    curses.mousemask(curses.ALL_MOUSE_EVENTS)
    styles = {'heading': curses.A_BOLD, 'dim': curses.A_DIM, 'normal': 0}
    try:
        if curses.has_colors():
            curses.start_color(); curses.use_default_colors()
            for i, (name, color) in enumerate((('active', curses.COLOR_BLUE), ('blocked', curses.COLOR_RED),
                                             ('context', curses.COLOR_CYAN)), 1):
                curses.init_pair(i, color, -1); styles[name] = curses.color_pair(i)
    except curses.error:
        pass
    cache = {}; first = 0; refresh = 0; rows = []; error = ''; kind = None
    root = Path(binding_file).parent
    try:
        window = json.loads((root / 'agents-preferences.json').read_text()).get('claude_window')
        if type(window) is not int or not 0 < window <= 999_999_999_999: window = None
    except (OSError, ValueError, TypeError):
        window = None
    while True:
        if time.monotonic() >= refresh:
            try:
                session = Session.for_panel(binding_file, repo)
                binding_file = session.file
                kind = session.binding.kind
                live = {p['pane_id']: p for p in Herdr().call('pane', 'list', '--workspace', session.binding.workspace)['panes']}
                source = agent_rows(session, RunStore().list(repo))
                rows = [(row, *describe(row, live.get(row['binding']['pane']), cache, window),
                         live.get(row['binding']['pane'])) for row in source]
                error = ''
            except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
                rows = []; error = str(exc)  # Never keep telemetry for an unverified old owner.
            refresh = time.monotonic() + 3
        screen.erase(); h, w = screen.getmaxyx()
        put(screen, 0, 'WATCHDOG / AGENTS', curses.A_BOLD)
        lines = monitor_lines(rows, w - 2)
        if error:
            lines.extend((line, 'blocked') for line in textwrap.wrap(safe(error), max(4, w - 2)))
        room = max(1, h - 3)
        first = max(0, min(first, len(lines) - room))
        for y, (line, style) in enumerate(lines[first:first + room], 2):
            put(screen, y, line, styles.get(style, 0))
        hint = '↑ ↓: rolar · q/Esc: sair'
        if kind == 'claude': hint = 'B: janela Claude · ' + hint
        put(screen, h - 1, hint, curses.A_DIM)
        screen.refresh(); key = screen.getch()
        if key in (27, ord('q')): return
        if key in (ord('j'), curses.KEY_DOWN): first += 1
        elif key in (ord('k'), curses.KEY_UP): first -= 1
        elif key == curses.KEY_NPAGE: first += room
        elif key == curses.KEY_PPAGE: first -= room
        elif key in (ord('B'), ord('b')) and kind == 'claude':
            try: window = edit_window(screen, root, window)
            except OSError as exc: error = str(exc)
            refresh = 0
        elif key == curses.KEY_MOUSE:
            try:
                mask = curses.getmouse()[4]
                if mask & curses.BUTTON4_PRESSED: first -= 3
                elif mask & getattr(curses, 'BUTTON5_PRESSED', 0): first += 3
            except curses.error:
                pass


def run(repo, binding_file):
    curses.wrapper(panel, Path(repo).resolve(), Path(binding_file))
