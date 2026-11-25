"""Open one Watchdog panel without rebuilding the conversation's layout."""
import argparse
import curses
import os
import shutil
from pathlib import Path
import sys

from . import bindings
from .actions import Session
from .herdr import Herdr
from .picker import setup, text, choose_conversation
from .store import Store

ROLES = ('agents', 'tasks', 'progress', 'artifacts', 'files')


def choose_panel(screen):
    setup(screen)
    selected = 0
    while True:
        screen.erase()
        text(screen, 0, 0, 'Watchdog / Escolher painel', curses.A_BOLD)
        for i, role in enumerate(ROLES):
            text(screen, i + 2, 0, role.title(), curses.A_REVERSE if i == selected else 0)
        text(screen, screen.getmaxyx()[0] - 2, 0, '↑ ↓ / j k: escolher · Enter: abrir · Esc: cancelar')
        screen.refresh()
        key = screen.getch()
        if key in (27, ord('q')):
            return None
        if key in (10, 13, curses.KEY_ENTER):
            return ROLES[selected]
        if key in (ord('j'), curses.KEY_DOWN):
            selected = (selected + 1) % len(ROLES)
        elif key in (ord('k'), curses.KEY_UP):
            selected = (selected - 1) % len(ROLES)


def open_pane(binding_file, repo, role, *, api=None):
    if role not in ROLES:
        raise ValueError('Painel desconhecido: ' + role)
    if role == 'files' and not shutil.which('yazi'):
        raise RuntimeError('O painel Files precisa do Yazi. Execute install.py para instalá-lo.')
    session = Session.for_panel(binding_file, Path(repo).resolve())
    binding, repo = session.binding, session.repo
    api, store = api or Herdr(), Store(session.file.parent)
    from .app import ensure_panels
    with store.lock(binding):
        session.verify()
        state = store.load(binding, repo)
        if state.get('operation') not in (None, 'ready'):
            raise RuntimeError('O layout ainda está sendo alterado; aguarde antes de abrir o painel')
        state['binding_file'] = str(session.file)
        # A confirmed absence can be recreated. A recycled terminal is refused.
        live = {p['pane_id']: p for p in api.call('pane', 'list', '--workspace', binding.workspace)['panes']}
        existing = state['panes'].get(role)
        if existing:
            current = live.get(existing['pane_id'])
            if current is None:
                del state['panes'][role]
            elif current['terminal_id'] != existing['terminal_id']:
                raise RuntimeError('Pane terminal substituído; não será reutilizado')
        target = state['panes'].get('progress') or state['panes'].get('tasks')
        if not target or target['pane_id'] not in live:
            target = {'pane_id': binding.pane, 'terminal_id': binding.terminal}
        save = lambda: store.save(binding, state)
        ensure_panels(api, state, save, roles=(role,), split_target=target)
        pane = state['panes'][role]
        api.checked(pane)
        api.request('pane.focus', {'pane_id': pane['pane_id']})
        return pane


def main(argv=None):
    from .app import context
    parser = argparse.ArgumentParser(description='Abrir um painel do Watchdog')
    parser.add_argument('role', nargs='?', choices=ROLES)
    parser.add_argument('--repo', type=Path, default=Path(os.environ.get('WATCHDOG_REPO') or
                        context().get('focused_pane_cwd') or Path.cwd()))
    parser.add_argument('--pane', default=os.environ.get('WATCHDOG_PANE'))
    parser.add_argument('--session', default=os.environ.get('WATCHDOG_SESSION'))
    parser.add_argument('--binding-file', type=Path, default=os.environ.get('WATCHDOG_BINDING_FILE'))
    args = parser.parse_args(argv)
    try:
        repo = args.repo.expanduser().resolve()
        tty = sys.stdin.isatty() and sys.stdout.isatty()
        role = args.role
        if role is None:
            if not tty:
                raise RuntimeError('Execute watchdog pane em um terminal para escolher, ou use watchdog pane agents')
            role = curses.wrapper(choose_panel)
            if role is None:
                return 0
        file = args.binding_file
        if file is None:
            candidates, _ = bindings.discover(repo)
            try:
                binding = bindings.select(candidates, pane=args.pane, session=args.session,
                                          thread=os.environ.get('CODEX_THREAD_ID'))
            except bindings.ChoiceRequired as choice:
                if not tty:
                    raise RuntimeError('Informe --pane e --session para escolher a conversa')
                binding = curses.wrapper(choose_conversation, choice.choices)
                if binding is None:
                    return 0
            bindings.verify(binding)
            store = Store()
            file = store.root / (binding.key + '.json')
            if not file.exists():
                with store.lock(binding):
                    state = store.load(binding, repo)
                    state['binding_file'] = str(file)
                    store.save(binding, state)
        pane = open_pane(file, repo, role)
        print('Watchdog / ' + role.title() + ' / ' + pane['pane_id'])
        return 0
    except (RuntimeError, OSError, ValueError, KeyError, TypeError) as error:
        print('Watchdog: ' + str(error), file=sys.stderr)
        return 1
