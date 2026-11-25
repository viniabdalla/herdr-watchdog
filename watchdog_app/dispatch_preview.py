"""Read explicit TODO blockers against current identities; never infer from acceptance prose."""
import re

from .todo import plain


def title(task):
    return re.sub(r'^\d{4}-\d{2}-\d{2} ', '', task.title).split(' — Blocked: ', 1)[0]


def aliases(task):
    names = {plain(title(task)), task.id, 'id:' + task.id}
    ticket = re.match(r'^(T\d+)\b(?:\s+\(#(\d+)\))?', title(task), re.I)
    if ticket:
        names.add(plain(ticket[1]))
        if ticket[2]:
            names.update(('#' + ticket[2], plain(ticket[0])))
    return names


def classify(snapshot, ids):
    selected = snapshot.selected(ids)
    result = []
    for task in selected:
        source = '\n'.join((task.execution, task.reason)) if snapshot.format_version else task.text
        blockers = re.findall(r'(?:bloquead[oa] por|blocked:|depende de|depende do)\s*:?\s*([^\n]+)', source, re.I)
        if task.reason and not blockers:
            blockers = [task.reason]
        dependencies, unresolved = [], []
        for blocker in blockers:
            # The project's explicit convention is "Bloqueado por: T1 (#2), T2 (#3)."
            for reference in re.split(r'\s*[,;]\s*|\s+e\s+', blocker.rstrip(' .')):
                reference = reference.strip(' `')
                matches = [candidate for candidate in snapshot.tasks if plain(reference) in aliases(candidate)]
                if len(matches) != 1:
                    unresolved.append(reference)
                elif not matches[0].done and matches[0] not in dependencies:
                    dependencies.append(matches[0])
        outside = [dep for dep in dependencies if dep.id not in ids]
        human = bool(unresolved) or (task.section == 'Blocked' and not blockers)
        label = ('depende do Vini' if human else 'espera fora da seleção' if outside else
                 'espera outra da seleção' if dependencies else 'livre')
        result.append({'id': task.id, 'title': title(task), 'label': label,
                       'outside': [dep.id for dep in outside],
                       'details': [title(dep) for dep in dependencies] + unresolved})
    return result


def warnings(repo):
    agents = repo / 'AGENTS.md'
    claude = repo / 'CLAUDE.md'
    agent_text = agents.read_text() if agents.exists() else ''
    claude_text = claude.read_text() if claude.exists() else ''
    result = []
    if not re.search(r'^## Dispatch\s*$', agent_text, re.M):
        result.append('Aviso: projeto sem seção Dispatch no AGENTS.md')
    if not re.search(r'(?m)^\s*@(?:\./)?AGENTS\.md\s*$', claude_text):
        result.append('Aviso: CLAUDE.md sem import do AGENTS.md')
    return result


def blocked(offer):
    return not any(task['label'] == 'livre' for task in offer['classification'])


def rows(offer):
    result = [(warning, 'Blocked', None) for warning in offer['warnings']]
    for task in offer['classification']:
        result.append((task['title'] + ': ' + task['label'],
                       'Next' if task['label'] == 'livre' else 'Blocked', None))
        if task['details']:
            result.append(('  ' + '; '.join(task['details']), None, None))
    if blocked(offer):
        result.append(('Nenhuma tarefa livre. Escolha antes de enviar.', 'Blocked', None))
    return result
