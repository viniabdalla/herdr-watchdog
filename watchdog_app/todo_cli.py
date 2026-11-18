"""Read/validate TODOs and explicitly preview, render or apply one migration."""
import argparse
import json
from pathlib import Path
import sys

from .mission import RunStore
from .todo import Snapshot
from . import todo_migrate


def describe(snapshot):
    return {'repo': str(snapshot.repo), 'format_version': snapshot.format_version,
            'digest': snapshot.digest, 'tasks': len(snapshot.tasks),
            'open': sum(not t.done for t in snapshot.tasks),
            'done': sum(t.done for t in snapshot.tasks),
            'historical': sum(t.historical for t in snapshot.tasks)}


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('validate', 'preview', 'render', 'apply'))
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--state-dir', type=Path, help='Run ledger directory, as in watchdog mission')
    parser.add_argument('--proposal', type=Path, help='JSON preview saved for review')
    parser.add_argument('--task', help='Existing UUID for an explicit identity change')
    parser.add_argument('--new-id', help='Replacement UUID; preview otherwise allocates one')
    parser.add_argument('--confirm', action='store_true')
    args = parser.parse_args(argv)
    try:
        snapshot = Snapshot.read(args.repo)
        store = RunStore(args.state_dir)
        if args.action == 'validate':
            result = describe(snapshot)
        elif args.action == 'preview':
            result = todo_migrate.preview(snapshot, store=store, task_id=args.task, new_id=args.new_id)
        else:
            if not args.proposal:
                raise RuntimeError('--proposal é obrigatório para render/apply')
            proposal = json.loads(args.proposal.read_text(encoding='utf-8'))
            if args.action == 'render':
                sys.stdout.write(todo_migrate.render(snapshot, proposal).decode('utf-8'))
                return 0
            result = describe(todo_migrate.apply(snapshot, proposal, store=store, confirmed=args.confirm))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (RuntimeError, OSError, ValueError, TypeError, KeyError) as error:
        print('Watchdog: ' + str(error), file=sys.stderr)
        return 1
