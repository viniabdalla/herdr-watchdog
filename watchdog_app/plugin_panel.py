"""Native plugin pane entry: select and persist a binding before opening its UI."""
import argparse
import os
from pathlib import Path

from . import bindings
from .herdr import Herdr
from .store import Store


def launch(role, repo, file):
    if role == 'tasks':
        from .tasks_ui import run
    elif role == 'progress':
        from .progress_ui import run
    else:
        from .app import main
        return main(['panel',role,'--repo',str(repo),'--binding-file',str(file)])
    run(repo,file)


def main(argv=None):
    from .app import context
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('role',choices=('tasks','progress','artifacts'))
    parser.add_argument('--repo',type=Path,default=Path(os.environ.get('WATCHDOG_REPO') or context().get('focused_pane_cwd') or Path.cwd()))
    args=parser.parse_args(argv)
    repo=args.repo.expanduser().resolve()
    candidates,errors=bindings.discover(repo)
    try:
        binding=bindings.select(candidates,pane=os.environ.get('WATCHDOG_PANE'),session=os.environ.get('WATCHDOG_SESSION'))
    except bindings.ChoiceRequired as choice:
        import curses
        from .picker import choose_conversation
        binding=curses.wrapper(choose_conversation,choice.choices)
        if binding is None:return 0
    bindings.verify(binding)
    store=Store()
    file=store.root/(binding.key+'.json')
    with store.lock(binding):
        state=store.load(binding,repo)
        state['binding_file']=str(file)
        # Native context names this newly created plugin panel, not its leader.
        pane_id=os.environ.get('HERDR_PANE_ID')
        if pane_id:
            panel=Herdr().call('pane','get',pane_id)['pane']
            existing=state['panes'].get(args.role)
            if existing and existing['pane_id'] != pane_id:
                raise RuntimeError('A bound panel already exists; reopen it instead of replacing ownership')
            state['panes'][args.role]=panel
        store.save(binding,state)
    launch(args.role,repo,file)
    return 0
