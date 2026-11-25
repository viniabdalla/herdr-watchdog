"""Launcher, verified layouts and interactive project-task panel entrypoints."""
import argparse
import curses
from dataclasses import asdict
import json
import os
from pathlib import Path
import shlex
import sys
import time

from . import bindings
from .herdr import Herdr
from .layouts import PRESETS, arrange
from .picker import choose_conversation, choose_layout
from .store import Store

ROOT = Path(__file__).resolve().parents[1]
ALIASES = {'right-column': 1, 'column-bottom': 2, 'separate-tab': 3, 'slim-column': 4}


def context():
    try:
        value = json.loads(os.environ.get('HERDR_PLUGIN_CONTEXT_JSON', '{}'))
        return value if isinstance(value, dict) else {}
    except ValueError:
        return {}


def preset_number(value):
    if value in ALIASES:
        return ALIASES[value]
    if value in ('1', '2', '3', '4'):
        return int(value)
    raise ValueError('Unknown layout. Use 1–4, right-column, column-bottom, separate-tab or slim-column.')


def panel_process(api, pane, role, state):
    info = api.call('pane', 'process-info', '--pane', pane['pane_id'])['process_info']
    foreground = [p for p in info['foreground_processes'] if p['pid'] != info['shell_pid']]
    for process in foreground:
        argv = process.get('argv', [])
        if role == 'files':
            if (process['name'] == 'yazi' and '--client-id' in argv and
                    argv[argv.index('--client-id') + 1:][:1] == [state['yazi_client_id']]):
                return True, foreground
        elif (argv[1:3] == [str(ROOT / 'tools/watchdog-preview.py'), role] or
              argv[1:4] == [str(ROOT / 'watchdog'), 'panel', role]):
            if role == 'agents':
                try:
                    repo = Path(argv[argv.index('--repo') + 1]).resolve()
                    file = Path(argv[argv.index('--binding-file') + 1])
                    if repo != Path(state['repo']).resolve() or not file.is_file():
                        continue
                    if file.resolve() != Path(state['binding_file']).resolve():
                        # Older launch arguments are valid only through a sealed
                        # Clean sessions redirect to this exact current owner.
                        from .actions import Session
                        owner = Session.for_panel(file, repo).binding
                        if asdict(owner) != state['binding']:
                            continue
                except (OSError, ValueError, IndexError, KeyError, RuntimeError, TypeError):
                    continue
            return True, foreground
    return False, foreground


def ensure_panels(api, state, save, *, roles=('tasks', 'progress', 'artifacts', 'files'), split_target=None):
    staging = anchor = None
    workspace = state['binding']['workspace']
    for role in roles:
        if role in state['panes']:
            # A Herdr restart keeps pane ids but issues new terminal ids.
            pane = state['panes'][role] = api.panel(state['panes'][role], state['repo'])
            running, foreground = panel_process(api, pane, role, state)
            # Shell prompt hooks can briefly be foreground during startup.
            # Wait for them to finish, but never interrupt or overwrite a busy pane.
            deadline = time.monotonic() + 1
            while foreground and not running and time.monotonic() < deadline:
                time.sleep(.05)
                running, foreground = panel_process(api, pane, role, state)
            if running:
                pane['launch_state'] = 'running'
                save()
                continue
            if foreground:
                raise RuntimeError(role + ' pane is running another command; leaving it untouched')
            if pane.get('launch_state') == 'starting':
                raise RuntimeError('Unconfirmed ' + role + ' launch; inspect that pane before retrying')
        else:
            if split_target is not None:
                target = api.checked(split_target)
                pane = api.call('pane', 'split', target['pane_id'], '--direction', 'down',
                                '--cwd', state['repo'], '--no-focus')['pane']
            elif staging is None:
                created = api.call('tab', 'create', '--workspace', workspace, '--cwd',
                                   state['repo'], '--label', 'Watchdog starting', '--no-focus')
                pane = created['root_pane']
                staging, anchor = pane['tab_id'], pane['pane_id']
            else:
                pane = api.call('pane', 'split', anchor, '--direction', 'down',
                                '--cwd', state['repo'], '--no-focus')['pane']
            pane['launch_state'] = 'owned'
            state['panes'][role] = pane
            save()
        api.call('pane', 'rename', pane['pane_id'], 'Watchdog ' + role.title())
        if role == 'files':
            argv = ['yazi', '--client-id', state['yazi_client_id'], state['repo']]
        else:
            argv = [sys.executable, str(ROOT / 'watchdog'), 'panel', role, '--repo',
                    state['repo'], '--yazi-client-id', state['yazi_client_id']]
            if role in ('tasks', 'progress', 'agents', 'artifacts') and state.get('binding_file'):
                argv += ['--binding-file', state['binding_file']]
        pane['launch_state'] = 'starting'
        save()
        api.call('pane', 'run', pane['pane_id'], shlex.join(argv))
        deadline = time.monotonic() + 6
        while True:
            running, _ = panel_process(api, pane, role, state)
            if running:
                pane['launch_state'] = 'running'
                save()
                break
            if time.monotonic() >= deadline:
                raise RuntimeError(role + ' launch was not confirmed; no command was retried')
            time.sleep(.1)


def reconcile_companion(binding, api, state):
    state['panes'].pop('left_undone', None)
    companion = bindings.companion(binding, api)
    if companion:
        state['panes']['left_undone'] = companion


def apply(binding, repo, preset):
    bindings.verify(binding)
    api, store = Herdr(), Store()
    with store.lock(binding):
        state = store.load(binding, repo)
        state['binding'] = asdict(binding)
        state['binding_file'] = str(store.root / (binding.key + '.json'))
        save = lambda: store.save(binding, state)
        # Native LU can have replaced or closed its old panel since last time.
        reconcile_companion(binding, api, state)
        # Ownership checks happen before creating or moving any terminal.
        for role, pane in state['panes'].items():
            if role == 'left_undone':
                api.checked(pane)
            else:
                state['panes'][role] = api.panel(pane, repo)
        conversation = api.call('pane', 'get', binding.pane)['pane']
        state['conversation'] = conversation
        save()
        ensure_panels(api, state, save)
        bindings.verify(binding)
        state['operation'] = 'arranging'
        save()
        tab = arrange(api, conversation, state['panes'], preset, save)
        bindings.verify(binding)
        state['layout'] = preset
        state['operation'] = 'ready'
        state['focus_tab'] = tab
        save()
        store.remember(preset)
    return state


def open_selector(api, repo, binding=None, *, pane=None, session=None, preset=None):
    target = binding.pane if binding else pane or context().get('focused_pane_id')
    if not target:
        raise RuntimeError('Run watchdog in a terminal to choose a conversation, or pass --pane and --session')
    argv = ['plugin', 'pane', 'open', '--plugin', 'watchdog', '--entrypoint', 'picker',
            '--placement', 'split', '--target-pane', target, '--direction', 'right',
            '--cwd', str(repo), '--focus', '--env', 'WATCHDOG_REPO=' + str(repo)]
    pane = binding.pane if binding else pane
    session = binding.session if binding else session
    if pane:
        argv += ['--env', 'WATCHDOG_PANE=' + pane]
    if session:
        argv += ['--env', 'WATCHDOG_SESSION=' + session]
    if preset is not None:
        argv += ['--env', 'WATCHDOG_LAYOUT=' + str(preset)]
    return api.call(*argv)


def main(argv=None):
    os.umask(0o077)
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ['aviso']:
        from .notice import main as notice_main
        return notice_main(argv[1:])
    if argv[:1] == ['project-instructions']:
        from .project_instructions import main as instructions_main
        return instructions_main(argv[1:])
    if argv[:1] == ['project-plan']:
        from .project_plans import main as plan_main
        return plan_main(argv[1:])
    if argv[:1] == ['artifacts']:
        from .artifacts import main as artifacts_main
        return artifacts_main(argv[1:])
    if argv[:1] == ['audit']:
        from .audit import main as audit_main
        return audit_main(argv[1:])
    if argv[:1] == ['todo']:
        from .todo_cli import main as todo_main
        return todo_main(argv[1:])
    if argv[:1] == ['clean-sessions']:
        from .clean_sessions import main as clean_main
        return clean_main(argv[1:])
    if argv[:1] == ['mission']:
        from .mission_cli import main as mission_main
        return mission_main(argv[1:])
    if argv[:1] == ['pane']:
        from .panes import main as pane_main
        return pane_main(argv[1:])
    parser = argparse.ArgumentParser(description='Watchdog: verified conversation layouts and project panels')
    parser.add_argument('command', nargs='?', default='open',
                        choices=('open', 'layout', 'list', 'status', 'panel', 'pick'))
    parser.add_argument('preset', nargs='?')
    parser.add_argument('--layout', dest='layout_name', default=os.environ.get('WATCHDOG_LAYOUT'))
    parser.add_argument('--list', action='store_true', help='List layout presets')
    parser.add_argument('--repo', type=Path, default=Path(os.environ.get('WATCHDOG_REPO') or
                        context().get('focused_pane_cwd') or Path.cwd()))
    parser.add_argument('--pane', default=os.environ.get('WATCHDOG_PANE'))
    parser.add_argument('--session', default=os.environ.get('WATCHDOG_SESSION'))
    parser.add_argument('--yazi-client-id')
    parser.add_argument('--binding-file', type=Path, default=os.environ.get('WATCHDOG_BINDING_FILE'))
    args = parser.parse_args(argv)
    if args.command == 'panel':
        if args.preset == 'agents':
            if not args.binding_file:
                parser.error('panel agents requires --binding-file')
            from .agents_ui import run
            run(args.repo.resolve(), args.binding_file)
            return 0
        if args.preset not in ('tasks', 'progress', 'artifacts'):
            parser.error('panel requires tasks, progress, artifacts or agents')
        command = [sys.executable, str(ROOT / 'tools/watchdog-preview.py'), args.preset,
                   '--repo', str(args.repo.resolve())]
        if args.yazi_client_id:
            command += ['--yazi-client-id', args.yazi_client_id]
        if args.binding_file:
            command += ['--binding-file', str(args.binding_file)]
        os.execv(sys.executable, command)
    if args.list:
        for number, (name, drawing) in PRESETS.items():
            print(f'{number}. {name}\n{drawing}\n')
        return 0
    requested = args.layout_name or args.preset
    try:
        preset = preset_number(requested) if requested else None
    except ValueError as error:
        parser.error(str(error))
    repo = args.repo.expanduser().resolve()
    try:
        if not repo.is_dir():
            raise RuntimeError('Project folder does not exist: ' + str(repo))
        candidates, errors = bindings.discover(repo)
        if args.command == 'list':
            print(json.dumps({'sessions': [asdict(b) for b in candidates], 'unavailable': errors}, indent=2))
            return 0
        tty = sys.stdin.isatty() and sys.stdout.isatty()
        try:
            binding = bindings.select(candidates, pane=args.pane, session=args.session,
                                      thread=os.environ.get('CODEX_THREAD_ID'))
        except bindings.ChoiceRequired as choice:
            if not tty:
                print(json.dumps(open_selector(Herdr(), repo, pane=args.pane,
                                               session=args.session, preset=preset)))
                return 0
            binding = curses.wrapper(choose_conversation, choice.choices)
            if binding is None:
                return 0
        bindings.verify(binding)
        if args.command == 'status':
            print(json.dumps({'project': str(repo), 'binding': asdict(binding)}, indent=2))
            return 0
        if preset is None:
            if not tty:
                print(json.dumps(open_selector(Herdr(), repo, binding)))
                return 0
            preset = curses.wrapper(choose_layout, Store().preference())
            if preset is None:
                return 0
        state = apply(binding, repo, preset)
        print(f'Watchdog / {repo.name} / {binding.kind} {binding.pane} / '
              f'layout {preset}: {PRESETS[preset][0]}')
        print('Layout is ready. Tasks and Progress are interactive; Artifacts retains its preview data source.')
        return 0
    except (RuntimeError, OSError, ValueError, KeyError) as error:
        print('Watchdog: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
