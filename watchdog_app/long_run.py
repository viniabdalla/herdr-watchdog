"""Project task group shared by Tasks, Progress and the curator."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re

from .store import atomic, state_root
from .todo import locked


def path_for(repo):
    key = hashlib.sha256(str(Path(repo).resolve()).encode()).hexdigest()
    return state_root() / 'long-runs' / (key + '.json')


def record(repo):
    try:
        value = json.loads(path_for(repo).read_text())
    except FileNotFoundError:
        return None
    group = value.get('members') if isinstance(value, dict) else value
    if not (isinstance(group, list) and group and all(isinstance(k, str) for k in group)
            and len(group) == len(set(group))):
        raise RuntimeError('Grupo do long run inválido')
    return value if isinstance(value, dict) else {'members': group}


def load(repo):
    value = record(repo)
    return value['members'] if value else None


def identity(snapshot, task):
    if snapshot.format_version and not task.historical:
        return 'id:' + task.id
    # Legacy TODOs change positional IDs on every move. Watchdog can prefix a
    # completion date or append a blocker; neither changes the original task.
    title = re.sub(r'^\d{4}-\d{2}-\d{2} ', '', task.title).split(' — Blocked: ', 1)[0]
    ticket = re.match(r'^(T\d+)(?=\s)', title)
    issues = re.findall(r'\(#(\d+)\)', title)
    if ticket and len(issues) == 1:
        return 'ticket:' + ticket[1] + '#' + issues[0]
    return 'title:' + title


def members(snapshot, group):
    """One slot per selected task; absent/ambiguous matches retain their slot."""
    by_key = defaultdict(list)
    for task in snapshot.tasks:
        by_key[identity(snapshot, task)].append(task)
    return [by_key[key][0] if len(by_key[key]) == 1 else None for key in group]


def save(snapshot, selected):
    with locked(snapshot.repo):
        snapshot.assert_current()
        group = [identity(snapshot, task) for task in snapshot.selected(selected)]
        if None in members(snapshot, group):
            raise RuntimeError('A seleção contém uma tarefa ambígua no TODO.md')
        atomic(path_for(snapshot.repo), group)
    return group
