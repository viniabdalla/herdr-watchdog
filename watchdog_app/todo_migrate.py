"""Explicit, reviewable TODO migrations. Never rewrites a run ledger."""
import json
import uuid

from . import todo_format as schema
from .todo import Snapshot, locked, _replace_locked


PROPOSAL_KEYS = {'version', 'kind', 'repo', 'source_digest', 'original', 'tasks', 'blocked_runs'}
TASK_KEYS = {'old_id', 'id', 'title', 'summary', 'execution', 'acceptance', 'origin', 'reference', 'reason'}


def details(snapshot, task):
    lines = snapshot.raw.decode('utf-8').splitlines()
    return '\n'.join(line[2:] if line.startswith('  ') else line
                     for line in lines[task.start + 1:task.end]).strip()


def declared(snapshot, task, label):
    for line in details(snapshot, task).splitlines():
        if line.startswith(label + ':'):
            return line[len(label) + 1:].strip()
    return ''


def blockers(snapshot, store, kind, ids):
    # Import lazily: mission uses TODO, but TODO never imports this module.
    if store is None:
        from .mission import RunStore
        store = RunStore()
    return [run['id'] for run in store.list(snapshot.repo)
            if run['phase'] not in ('done', 'closed') and
            (kind == 'legacy' or run.get('scope', {}).get('version') != 2
             or set(run['tasks']) & set(ids))]


def preview(snapshot, *, store=None, task_id=None, new_id=None):
    tasks = []
    if snapshot.format_version:
        if task_id is None:
            raise RuntimeError('TODO já migrado; mudança de identidade exige ID explícito')
        selected = [t for t in snapshot.tasks if t.id == task_id and not t.historical]
        if len(selected) != 1:
            raise RuntimeError('ID não encontrado para mudança de identidade')
        task = selected[0]
        new_id = new_id or str(uuid.uuid4())
        retired = {old for record in snapshot.migrations if record['kind'] == 'identity' for old in record['ids']}
        if not schema.canonical_id(new_id) or new_id in retired or any(t.id == new_id for t in snapshot.tasks):
            raise RuntimeError('ID inválido, existente ou aposentado; revisar identidade')
        tasks.append(dict(old_id=task.id, id=new_id, title=task.title,
                          **{name: getattr(task, name) for name in schema.FIELDS.values() if name != 'id'}))
        kind = 'identity'
    else:
        if task_id is not None or new_id is not None:
            raise RuntimeError('Mudança de identidade requer primeiro migração explícita do formato antigo')
        kind = 'legacy'
        for task in snapshot.tasks:
            if task.done:
                continue
            tasks.append(dict(old_id=task.id, id=str(uuid.uuid4()), title=task.title,
                              summary=declared(snapshot, task, 'Resumo'),
                              execution=details(snapshot, task), acceptance=declared(snapshot, task, 'Aceite'),
                              origin='legado-nao-confirmado', reference='', reason=''))
    return {'version': 1, 'kind': kind, 'repo': str(snapshot.repo), 'source_digest': snapshot.digest,
            'original': snapshot.raw.decode('utf-8'), 'tasks': tasks,
            'blocked_runs': blockers(snapshot, store, kind, [t['old_id'] for t in tasks])}


def render(snapshot, proposal):
    """Validate proposal against its exact source and return the candidate bytes."""
    if (not isinstance(proposal, dict) or set(proposal) != PROPOSAL_KEYS
            or type(proposal['version']) is not int or proposal['version'] != 1
            or proposal['repo'] != str(snapshot.repo)
            or proposal['source_digest'] != snapshot.digest
            or proposal['original'] != snapshot.raw.decode('utf-8')):
        raise RuntimeError('TODO proposta inválida ou origem alterada (changed); gere nova prévia')
    kind = proposal['kind']
    if kind != ('identity' if snapshot.format_version else 'legacy'):
        raise RuntimeError('TODO tipo de migração incompatível com o formato de origem')
    entries = proposal['tasks']
    if not isinstance(entries, list) or not isinstance(proposal['blocked_runs'], list):
        raise RuntimeError('TODO esquema de proposta inválido')
    by_id, new_ids = {}, set()
    for entry in entries:
        if (not isinstance(entry, dict) or set(entry) != TASK_KEYS
                or any(not isinstance(value, str) for value in entry.values())
                or not schema.canonical_id(entry['id'])
                or entry['old_id'] in by_id or entry['id'] in new_ids):
            raise RuntimeError('TODO campos ou IDs da proposta inválidos/duplicados')
        by_id[entry['old_id']] = entry
        new_ids.add(entry['id'])
    source = {t.id: t for t in snapshot.tasks if not t.historical and (kind == 'identity' or not t.done)}
    if kind == 'legacy' and set(source) != set(by_id):
        raise RuntimeError('TODO migração deve preservar todas as tarefas abertas')
    if kind == 'identity' and (not by_id or not set(by_id) <= set(source)):
        raise RuntimeError('TODO mudança de identidade exige tarefas existentes explícitas')
    retired = {old for record in snapshot.migrations if record['kind'] == 'identity' for old in record['ids']}
    if kind == 'identity' and (new_ids & (set(source) | retired)):
        raise RuntimeError('TODO ID existente ou aposentado; mudança de identidade inválida')
    for old_id, entry in by_id.items():
        task = source[old_id]
        if entry['title'] != task.title:
            raise RuntimeError('TODO migração preserva títulos; revise a redação depois de migrar')
        if kind == 'legacy':
            original = details(snapshot, task)
            if original and original not in entry['execution']:
                raise RuntimeError('TODO instruções originais devem ser preservadas integralmente na Execução')
        elif any(entry[name] != getattr(task, name) for name in schema.FIELDS.values() if name != 'id'):
            raise RuntimeError('TODO mudança de identidade não pode alterar o conteúdo da tarefa')
    lines = snapshot.raw.decode('utf-8').splitlines(keepends=True)
    newline = '\r\n' if b'\r\n' in snapshot.raw else '\n'
    for task in reversed(snapshot.tasks):
        entry = by_id.get(task.id)
        if entry:
            content = schema.render(task.title, entry, done=task.done, newline=newline)
        elif kind == 'legacy' and task.done:
            if task.section != 'Done':
                raise RuntimeError('TODO legado com conclusão fora de Feito; revisar estado antes da migração')
            original = ''.join(lines[task.start:task.end])
            content = schema.HISTORY_BEGIN + newline + original
            if not content.endswith(('\r', '\n')):
                content += newline
            content += schema.HISTORY_END + newline
        else:
            continue
        lines[task.start:task.end] = [content]
    if kind == 'legacy':
        if lines and lines[0].strip() == '---':
            if not any(line.strip() == '---' for line in lines[1:]):
                raise RuntimeError('TODO frontmatter sem fechamento; revisar antes da migração')
            lines.insert(1, 'watchdog_todo: 1' + newline)
        else:
            lines.insert(0, '---' + newline + 'watchdog_todo: 1' + newline + '---' + newline)
    record = dict(version=1, kind=kind, source_digest=snapshot.digest,
                  ids={old: entry['id'] for old, entry in by_id.items()})
    result = ''.join(lines)
    if result and not result.endswith(('\r', '\n')):
        result += newline
    result += schema.MIGRATION_PREFIX + json.dumps(record, ensure_ascii=False, sort_keys=True) + ' -->' + newline
    raw = result.encode('utf-8')
    candidate = Snapshot.parse(snapshot.repo, raw)
    # Check historical imports too: malformed legacy states must be reviewed, not repaired invisibly.
    if len(candidate.tasks) != len(snapshot.tasks):
        raise RuntimeError('TODO migração alteraria a quantidade de tarefas; revisar arquivo original')
    return raw


def apply(snapshot, proposal, *, confirmed=False, store=None, root=None):
    if not confirmed:
        raise RuntimeError('TODO migração exige confirmação explícita (--confirm)')
    with locked(snapshot.repo, root) as locked_root:
        snapshot.assert_current()
        raw = render(snapshot, proposal)
        active = blockers(snapshot, store, proposal['kind'], [t['old_id'] for t in proposal['tasks']])
        if active:
            raise RuntimeError('TODO migração bloqueada por execuções inacabadas: ' + ', '.join(active) +
                               '. Termine ou encerre explicitamente pelo fluxo existente; registros preservados.')
        return _replace_locked(snapshot, raw, locked_root)
