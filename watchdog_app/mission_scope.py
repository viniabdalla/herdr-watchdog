"""Immutable selected TODO evidence for new runs; positional ledger IDs stay pinned.

No markers, fuzzy matching or title normalization: an exact block must have one
occurrence in the current parsed TODO and retain its section and open state.
"""
from collections import defaultdict

from .todo import SECTIONS, TASK, Snapshot


def blocks(snapshot):
    lines = snapshot.raw.decode('utf-8').splitlines(keepends=True)
    return {t.id: ''.join(lines[t.start:t.end]) for t in snapshot.tasks}


def descriptors(run):
    """Absent scope means legacy. A present, invalid scope never falls back."""
    if 'scope' not in run:
        return None
    scope = run['scope']
    if not isinstance(scope, dict) or type(scope.get('version')) is not int or scope['version'] != 1:
        raise RuntimeError('Unsupported or malformed run scope version')
    tasks = scope.get('tasks')
    if (set(scope) != {'version', 'tasks'} or not isinstance(tasks, dict) or
            not tasks or set(tasks) != set(run['tasks'])):
        raise RuntimeError('Malformed run scope: expected exactly the selected task IDs')
    for value in tasks.values():
        if not isinstance(value, dict) or set(value) != {'block', 'section'}:
            raise RuntimeError('Malformed run scope task descriptor')
        block = value['block']
        if (not isinstance(block, str) or not block or
                not isinstance(value['section'], str) or value['section'] not in SECTIONS[:-1]):
            raise RuntimeError('Malformed run scope task content or section')
        match = TASK.match(block.splitlines(keepends=True)[0])
        if not match or match[2] != ' ':
            raise RuntimeError('Malformed run scope: selected task must be open')
    return tasks


def capture(snapshot, tasks):
    content = blocks(snapshot)
    scope = {'version': 1, 'tasks': {t.id: {'block': content[t.id], 'section': t.section} for t in tasks}}
    # Reject ambiguous identity at confirmation, even when positional IDs differ.
    resolve({'repo': str(snapshot.repo), 'tasks': scope['tasks'], 'scope': scope}, snapshot)
    return scope


def resolve(run, snapshot=None):
    """Validate only selected descriptors, returning original ID -> current Task."""
    selected = descriptors(run)
    snapshot = snapshot or Snapshot.read(run['repo'])
    if selected is None:
        if snapshot.digest != run['source_digest']:
            raise RuntimeError('Task list changed; request a fresh contract')
        return None
    occurrences = defaultdict(list)
    content = blocks(snapshot)
    for task in snapshot.tasks:
        occurrences[content[task.id]].append(task)
    result = {}
    for key, expected in selected.items():
        matches = occurrences[expected['block']]
        if len(matches) > 1:
            raise RuntimeError('Run scope is ambiguous for selected task ' + key + '; request a fresh contract')
        if not matches or matches[0].done or matches[0].section != expected['section']:
            raise RuntimeError('Selected run scope changed for task ' + key + '; request a fresh contract')
        result[key] = matches[0]
    return result


def overlaps(previous, scope, tasks):
    """Detect an active selection across row shifts without rewriting older runs.

    Legacy ledgers lack raw blocks; their recorded display text is conservative
    duplicate evidence only, never authority to resolve or upgrade their scope.
    """
    selected = descriptors(previous)
    if selected is None:
        titles = {task['title'] for task in previous['tasks'].values()}
        return bool(set(previous['tasks']) & set(scope['tasks']) or any(t.text in titles for t in tasks))
    old = {value['block'] for value in selected.values()}
    return any(value['block'] in old for value in scope['tasks'].values())
