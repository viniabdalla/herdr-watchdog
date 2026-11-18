"""Immutable selected TODO evidence: legacy blocks or versioned stable UUIDs.

Identity never approves revised instructions: both formats pin their exact block
and open state. Existing positional run ledgers are never rewritten or upgraded.
"""
from collections import defaultdict

from .todo import SECTIONS, TASK, Snapshot
from .todo_format import canonical_id


REVIEW = ('Restore its text to continue, or close the run in Progress (x) and Orchestrate again '
          'so the main reviews a new contract. Other tasks and new ideas can change freely.')
LEGACY = ('Task list changed and this older run pins the whole TODO.md. Close it in Progress (x) and '
          'Orchestrate again; new runs only pin the selected tasks.')


def explain(problem):
    """User-facing guidance for older stored monitor problems."""
    if problem.startswith('Task list changed; request a fresh contract'):  # Stored by older versions.
        return LEGACY
    if 'request a fresh contract' in problem:
        return problem.replace('request a fresh contract', REVIEW)
    return problem


def blocks(snapshot):
    lines = snapshot.raw.decode('utf-8').splitlines(keepends=True)
    return {t.id: ''.join(lines[t.start:t.end]) for t in snapshot.tasks}


def descriptors(run):
    """Absent scope means legacy. A present, invalid scope never falls back."""
    if 'scope' not in run:
        return None
    scope = run['scope']
    if not isinstance(scope, dict) or type(scope.get('version')) is not int or scope['version'] not in (1, 2):
        raise RuntimeError('Unsupported or malformed run scope version')
    tasks = scope.get('tasks')
    stable = scope['version'] == 2
    if stable and (type(scope.get('format')) is not int or scope['format'] != 1):
        raise RuntimeError('Malformed run scope: unsupported TODO format')
    if (set(scope) != ({'version', 'format', 'tasks'} if stable else {'version', 'tasks'}) or not isinstance(tasks, dict) or
            not tasks or set(tasks) != set(run['tasks'])):
        raise RuntimeError('Malformed run scope: expected exactly the selected task IDs')
    for key, value in tasks.items():
        if not isinstance(value, dict) or set(value) != {'block', 'section'}:
            raise RuntimeError('Malformed run scope task descriptor')
        block = value['block']
        if (not isinstance(block, str) or not block or
                not isinstance(value['section'], str) or value['section'] not in SECTIONS[:-1]):
            raise RuntimeError('Malformed run scope task content or section')
        match = TASK.match(block.splitlines(keepends=True)[0])
        if not match or match[2] != ' ':
            raise RuntimeError('Malformed run scope: selected task must be open')
        if stable:
            try:
                parsed = Snapshot.parse(run['repo'], ('---\nwatchdog_todo: 1\n---\n## ' + value['section'] + '\n' + block).encode())
            except RuntimeError as error:
                raise RuntimeError('Malformed run scope: invalid versioned task block') from error
            if not canonical_id(key) or len(parsed.tasks) != 1 or parsed.tasks[0].id != key:
                raise RuntimeError('Malformed run scope: ID differs from approved task block')
    return tasks


def capture(snapshot, tasks):
    content = blocks(snapshot)
    scope = {'version': 1, 'tasks': {t.id: {'block': content[t.id], 'section': t.section} for t in tasks}}
    if snapshot.format_version:
        scope.update(version=2, format=snapshot.format_version)
    # Reject ambiguous identity at confirmation, even when positional IDs differ.
    resolve({'repo': str(snapshot.repo), 'tasks': scope['tasks'], 'scope': scope}, snapshot)
    return scope


def resolve(run, snapshot=None):
    """Validate only selected descriptors, returning original ID -> current Task."""
    selected = descriptors(run)
    snapshot = snapshot or Snapshot.read(run['repo'])
    if selected is None:
        if snapshot.digest != run['source_digest']:
            raise RuntimeError(LEGACY)
        return None
    if run['scope']['version'] == 2:
        if snapshot.format_version != run['scope']['format']:
            raise RuntimeError('Run scope: formato do TODO mudou; revisar contrato explicitamente')
        by_id = {task.id: task for task in snapshot.tasks}
        content = blocks(snapshot)
        result = {}
        for key, expected in selected.items():
            task = by_id.get(key)
            if task is None:
                raise RuntimeError('Run scope: identidade removida ou substituída: ' + key + '. ' + REVIEW)
            if task.done or task.section != expected['section'] or content[key] != expected['block']:
                raise RuntimeError('Run scope: conteúdo ou estado mudou para ID ' + key +
                                   '; identidade preservada, revisar contrato. ' + REVIEW)
            result[key] = task
        return result
    if snapshot.format_version:
        raise RuntimeError('Run scope: TODO foi migrado; contrato antigo preservado, revisar migração explicitamente. ' + REVIEW)
    occurrences = defaultdict(list)
    content = blocks(snapshot)
    for task in snapshot.tasks:
        occurrences[content[task.id]].append(task)
    result = {}
    for key, expected in selected.items():
        matches = occurrences[expected['block']]
        title = TASK.match(expected['block'].splitlines()[0])[3].strip()
        if len(matches) > 1:
            raise RuntimeError('Run scope: selected task "' + title[:60] + '" is ambiguous: it now appears twice in TODO.md. '
                               'Remove the duplicate to continue this run.')
        if not matches:
            raise RuntimeError('Run scope: selected task "' + title[:60] + '" was edited or removed in TODO.md. '
                               + REVIEW)
        if matches[0].done:
            raise RuntimeError('Run scope: selected task "' + title[:60] + '" was marked done in TODO.md. '
                               'If you accepted it, close the run in Progress (x); otherwise reopen it.')
        if matches[0].section != expected['section']:
            raise RuntimeError('Run scope: selected task "' + title[:60] + '" moved from ' + expected['section'] +
                               ' to ' + matches[0].section + '. Move it back, or ' + REVIEW[0].lower() + REVIEW[1:])
        result[key] = matches[0]
    return result


def overlaps(previous, scope, tasks):
    """Detect an active selection across row shifts without rewriting older runs.

    Legacy ledgers lack raw blocks; their recorded display text is conservative
    duplicate evidence only, never authority to resolve or upgrade their scope.
    """
    selected = descriptors(previous)
    if previous.get('scope', {}).get('version') == 2 or scope.get('version') == 2:
        if previous.get('scope', {}).get('version') != scope.get('version'):
            return True  # An unfinished cross-format contract needs explicit operator review.
        return bool(set(previous['tasks']) & set(scope['tasks']))
    if selected is None:
        titles = {task['title'] for task in previous['tasks'].values()}
        return bool(set(previous['tasks']) & set(scope['tasks']) or any(t.text in titles for t in tasks))
    old = {value['block'] for value in selected.values()}
    return any(value['block'] in old for value in scope['tasks'].values())
