"""Leader-confirmed questions and final summaries; Progress only reads them."""
from pathlib import Path
import re
import subprocess

from . import long_run
from .store import atomic
from .todo import Snapshot, locked


def entries(values, fields):
    result = []
    for value in values:
        parts = [part.strip() for part in value.split('|', len(fields)-1)]
        if len(parts) != len(fields) or not all(parts):
            raise RuntimeError('Use ' + '|'.join(fields) + ', sem campos vazios')
        result.append(dict(zip(fields, parts)))
    return result


def update(repo, group, action, *, ticket=None, question=None, completed=(), blocked=()):
    repo = Path(repo).resolve()
    with locked(repo):
        state = long_run.record(repo)
        if not state or not state['members'] or state.get('base') != group:
            raise RuntimeError('Grupo ausente ou alterado; confira o grupo atual')
        tasks = long_run.members(Snapshot.read(repo), state['members'])
        def resolve(selector):
            matches = []
            for key, task in zip(state['members'], tasks):
                if task is None:
                    continue
                match = re.match(r'^(?:\d{4}-\d{2}-\d{2} )?(T\d+)\b', task.title)
                alias = match[1] if match else task.title
                if selector in (key, task.id, task.title, alias, key.removeprefix('id:')):
                    matches.append((key, alias, task))
            if len(matches) != 1:
                raise RuntimeError('Tarefa fora do grupo ou sem correspondência única: '+str(selector))
            return matches[0]

        notices = dict(state.get('notices', {}))
        questions = dict(notices.get('questions', {}))
        event = None
        if action in ('perguntar', 'responder'):
            key, label, _ = resolve(ticket)
            if action == 'perguntar':
                if not question or not question.strip():
                    raise RuntimeError('Informe a dúvida encaminhada ao Vini')
                event = dict(title=f'pergunta de {label} aguarda você', body=question.strip())
                if questions.get(key, {}).get('body') == event['body']:
                    return notices
                questions[key] = event
            else:
                questions.pop(key, None)
            notices['questions'] = questions
        else:
            done = entries(completed, ('ticket','evidence'))
            waiting = entries(blocked, ('ticket','reason','next_step'))
            for item in done + waiting:
                key, label, task = resolve(item['ticket'])
                item.update(identity=key, ticket=label)
                if item in done and not task.done:
                    raise RuntimeError('Tarefa concluída precisa estar concluída no TODO')
            reported = [item['identity'] for item in done + waiting]
            if sorted(reported) != sorted(state['members']):
                raise RuntimeError('Resumo deve listar cada tarefa do grupo uma única vez')
            blockers = [f"Bloqueada {i['ticket']} · motivo: {i['reason']} · próximo passo: {i['next_step']}" for i in waiting]
            body = '\n'.join(blockers + [f"Concluída {i['ticket']} · evidência: {i['evidence']}" for i in done])
            title = f'Meta encerrada · {len(done)} de {len(tasks)}'
            if waiting:
                title += ' · ' + '; '.join(f"{i['ticket']} · {i['reason']} · próximo passo: {i['next_step']}" for i in waiting)
            event = dict(title=title, body=body, completed=done, blocked=waiting)
            if notices.get('ended', {}).get('body') == body:
                return notices
            notices['ended'] = event
        state['notices'] = notices
        atomic(long_run.path_for(repo), state)
        # Persist before the desktop call: failure must not hide the banner.
        # Replaying the same event never sends a second desktop notification.
        if event:
            try:
                subprocess.run(['notify-send', '--app-name=Herdr Watchdog', '--', event['title'], event['body']],
                               check=True, capture_output=True, text=True, timeout=5)
            except (OSError, subprocess.SubprocessError) as error:
                event['notification_error'] = str(error)
                atomic(long_run.path_for(repo), state)
        return notices


def rows(group, *, details=False, ended_banner=True):
    """Spec #21 L32: AGENTES leaves the ended banner out of its top (ended_banner=False)."""
    notices = group.get('notices', {})
    result = []
    ended = notices.get('ended')
    if details:
        if ended:
            if not ended_banner:
                result.append((ended['title'], 'done', None))
            result.extend((line, 'ready', None) for line in ended['body'].splitlines())
        return result
    if not ended_banner:
        ended = None
    events = ([ended] if ended else []) + list(notices.get('questions', {}).values())
    for event in events:
        result.append((event['title'], 'blocked' if 'completed' not in event else 'done', None))
        if event is not ended:
            result.extend((line, 'ready', None) for line in event['body'].splitlines())
        if event.get('notification_error'):
            result.append(('Desktop · notificação indisponível: '+event['notification_error'], 'blocked', None))
    return result
