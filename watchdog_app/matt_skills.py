"""Leader-visible Matt skills and confirmed, editable command delivery."""
from pathlib import Path
import re

from .pane_delivery import send

# Keep numbering stable when one skill is missing. Other tickets extend this list.
SKILLS = ('grill-with-docs', 'to-spec', 'to-tickets', 'retro', 'code-review', 'merge-danger')


def installed(repo, binding):
    if binding is None or binding.kind not in ('claude', 'codex'):
        return []
    repo, home = Path(repo).resolve(), Path.home()
    account = Path(binding.account).expanduser()
    if binding.kind == 'codex':
        roots = [home/'.agents/skills', account/'skills']
        roots += [parent/'.agents/skills' for parent in (repo, *repo.parents)]
    else:
        roots = [account/'skills']
        roots += [parent/'.claude/skills' for parent in (repo, *repo.parents)]
    prefix = '/' if binding.kind == 'claude' else '$'
    return [(str(index), prefix + name) for index, name in enumerate(SKILLS, 1)
            if any((root/name/'SKILL.md').is_file() for root in roots)]


def preview(session, key):
    session.verify()
    command = dict(installed(session.repo, session.binding)).get(key)
    if command is None:
        raise RuntimeError('Skill indisponível para o harness do líder')
    warning = ''
    if command[1:] in ('to-spec', 'to-tickets'):
        tracker = Path(session.repo)/'docs/agents/issue-tracker.md'
        text = tracker.read_text() if tracker.is_file() else ''
        if not re.search(r'^##+\s+.*(?:cópia local|local cop(?:y|ies))', text, re.M | re.I):
            warning = 'O tracker do projeto não guarda cópia local das issues; revise antes de enviar.'
    if command[1:] == 'to-tickets':
        specs = sorted((Path(session.repo)/'docs/issues').glob('*.md'))
        specs = [path for path in specs if re.search(r'^title:\s*[\"\']?Spec:', path.read_text(), re.M | re.I)]
        if len(specs) == 1:
            command += ' ' + str(specs[0].relative_to(session.repo))
    return {'kind': 'skill', 'prompt': command, 'warning': warning,
            'binding': session.binding, 'pane': session.binding.pane, 'key': key}


def deliver(session, offer):
    with session.routing():
        session.verify()
        if session.binding != offer['binding'] or session.binding.pane != offer['pane']:
            raise RuntimeError('O líder mudou; confira uma nova prévia da skill')
        if offer['key'] not in dict(installed(session.repo, session.binding)):
            raise RuntimeError('Skill indisponível; confira uma nova prévia')
        text = offer['prompt'].strip()
        if not text or any(not character.isprintable() for character in text):
            raise RuntimeError('Digite um comando em uma única linha')
        send(offer['pane'], text)
