"""Confirmed selection delivery; coordination remains the leader's job."""
from pathlib import Path
import re
import subprocess

from . import long_run
from .dispatch_preview import classify, warnings, blocked
from .pane_delivery import send
from .store import atomic
from .todo import locked


STANDARD = Path(__file__).resolve().parents[1] / 'docs/dispatch.md'


def git(repo, *args):
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('Não foi possível ler a branch de integração: ' + result.stderr.strip())
    return result.stdout.strip()


def integration(repo):
    instructions = Path(repo) / 'AGENTS.md'
    text = instructions.read_text() if instructions.exists() else ''
    section = re.search(r'^## Dispatch\s*\n(.*?)(?=^## |\Z)', text, re.M | re.S)
    configured = re.search(r'^Branch de integração:\s*`([^`]+)`', section[1], re.M) if section else None
    branch = configured[1] if configured else git(repo, 'symbolic-ref', '--short', 'HEAD')
    return branch, git(repo, 'rev-parse', '--verify', 'refs/heads/' + branch + '^{commit}')


def goal_identity(binding):
    return {key: getattr(binding, key) for key in ('kind', 'account', 'session')}


def preview(session, snapshot, ids, mode='dispatch'):
    if mode not in ('dispatch', 'here'):
        raise ValueError('Modo de despacho inválido')
    snapshot.assert_current()
    session.verify()
    tasks = snapshot.selected(ids)
    previous = long_run.record(snapshot.repo)
    old_members = long_run.members(snapshot, previous['members']) if previous else []
    restart = bool(old_members) and all(task and task.done for task in old_members)
    group = list(previous['members']) if previous and not restart else []
    keys = [long_run.identity(snapshot, task) for task in tasks]
    if None in long_run.members(snapshot, keys):
        raise RuntimeError('A seleção contém uma tarefa ambígua no TODO.md')
    added = []
    for task, key in zip(tasks, keys):
        if key not in group:
            group.append(key)
            added.append(task)
    state = dict(previous or {}, members=group)
    if restart:
        for field in ('base', 'integration_branch', 'goal', 'modes'):
            state.pop(field, None)
    modes = dict(state.get('modes', {}))
    for task in added:
        modes[long_run.identity(snapshot, task)] = mode
    state['modes'] = modes
    new_base = 'base' not in state
    if new_base:
        branch, base = integration(snapshot.repo)
        state.update(integration_branch=branch, base=base)
    action = 'Implementar nesta sessão' if mode == 'here' else 'Concluir'
    execution = ('Implemente em worktree própria a partir da integração; integre com as mesmas '
                 'checagens e avise "Tn concluído".' if mode == 'here' else 'Despache um executor por tarefa;')
    phrase = (action + ' somente as tarefas do grupo do Watchdog em ' + str(long_run.path_for(snapshot.repo)) +
              ', acompanhadas no TODO.md de ' + str(snapshot.repo) + '. Leia o padrão do dispatch ' + str(STANDARD) +
              ' e a seção ## Dispatch do AGENTS.md do projeto. ' + execution + ' '
              'Leia o modo por identidade no campo modes do grupo a cada atualização; '
              'siga os ponteiros de aceite e avise ao concluir ou bloquear o grupo.')
    prompt = ('/goal ' if session.binding.kind in ('codex', 'claude') else '') + phrase
    if group and not restart and previous and previous.get('goal') == goal_identity(session.binding):
        prompt = 'Grupo atualizado: ' + (', '.join('+' + task.title for task in added)
                                           or 'nenhuma tarefa nova.')
    return {'kind': 'group_dispatch', 'mode': mode, 'snapshot': snapshot, 'ids': set(ids),
            'prompt': prompt, 'pane': session.binding.pane, 'binding': session.binding,
            'previous': previous, 'group': state, 'new_base': new_base,
            'classification': classify(snapshot, set(ids)), 'warnings': warnings(snapshot.repo)}


def deliver(session, offer):
    snapshot = offer['snapshot']
    with session.routing(), locked(snapshot.repo):
        snapshot.assert_current()
        snapshot.selected(offer['ids'])
        if blocked(offer) and not offer.get('allow_blocked'):
            raise RuntimeError('Nenhuma tarefa livre; escolha incluir, cancelar ou mandar assim mesmo')
        session.verify()
        if session.binding != offer['binding'] or session.binding.pane != offer['pane']:
            raise RuntimeError('O líder mudou; confira uma nova prévia antes de despachar')
        if long_run.record(snapshot.repo) != offer['previous']:
            raise RuntimeError('O grupo mudou; confira uma nova prévia antes de despachar')
        if offer['new_base']:
            branch, base = integration(snapshot.repo)
            if (branch, base) != (offer['group']['integration_branch'], offer['group']['base']):
                raise RuntimeError('A integração mudou; confira uma nova prévia antes de despachar')
        # The leader can read the group as soon as Enter reaches its pane.
        atomic(long_run.path_for(snapshot.repo), offer['group'])
        try:
            send(offer['pane'], offer['prompt'])
        except (RuntimeError, OSError) as error:
            raise RuntimeError('Despacho não confirmado; grupo preservado. Confira o pane do líder '
                               'antes de tentar novamente; nada foi reenviado automaticamente.') from error

        state = dict(offer['group'], goal=goal_identity(session.binding))
        atomic(long_run.path_for(snapshot.repo), state)
