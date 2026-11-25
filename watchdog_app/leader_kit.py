"""Leader tools: isolated executors, retained contracts, explicit issue closure.

The versioned project registry is public input for Progress and review tools.
No scheduler, polling, integration, push or implicit retry lives here.
"""
import argparse
from datetime import date
import json
from pathlib import Path
import re
import shlex
import sys
import time
import uuid

from .herdr import Herdr
from .mission_launch import command, git
from .pane_delivery import pane_lock
from .store import atomic

ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT/'docs/dispatch.md'


def configuration(repo):
    text = (repo/'AGENTS.md').read_text()
    match = re.search(r'^## Dispatch\s*\n(.*?)(?=^## |\Z)', text, re.M | re.S)
    if not match:
        raise RuntimeError('AGENTS.md precisa da seção Dispatch')
    section = match[1]
    values = {}
    for key, label in (('integration', 'Branch de integração'),
                       ('model', 'Modelo dos executores'),
                       ('effort', 'Esforço dos executores'),
                       ('permissions', 'Permissões dos executores')):
        found = re.search(r'^'+label+r':\s*([^\n]+)', section, re.M)
        if not found or not found[1].strip(' `<>'):
            raise RuntimeError('Dispatch precisa de '+label)
        values[key] = found[1].strip().strip('`')
    efforts = {'médio':'medium', 'medio':'medium', 'baixo':'low', 'alto':'high'}
    values['effort'] = efforts.get(values['effort'].lower(), values['effort'])
    if values['effort'] not in ('minimal','low','medium','high','xhigh','max'):
        raise RuntimeError('Esforço dos executores inválido')
    if values['permissions'].lower() not in ('full access','danger-full-access','workspace-write','read-only'):
        raise RuntimeError('Permissões dos executores não reconhecidas')
    values['dispatch'] = section.strip()
    return values


def ignored_directories(repo):
    """Local Git exclusions work in arbitrary projects without editing tracked files."""
    directory = Path(git(repo, 'rev-parse', '--path-format=absolute', '--git-common-dir'))
    exclude = directory/'info/exclude'
    exclude.parent.mkdir(parents=True, exist_ok=True)
    existing = exclude.read_text() if exclude.exists() else ''
    missing = [p for p in ('/.worktrees/', '/.watchdog/') if p not in existing.splitlines()]
    if missing:
        with exclude.open('a') as stream:
            stream.write(('\n' if existing and not existing.endswith('\n') else '')+'\n'.join(missing)+'\n')


def registry(repo):
    path = repo/'.watchdog/executors.json'
    if not path.exists():
        return {'version':1, 'project':str(repo), 'executors':[]}
    value = json.loads(path.read_text())
    if value.get('version') != 1 or value.get('project') != str(repo):
        raise RuntimeError('Registro de executores pertence a outro projeto ou versão')
    return value


def executors(repo, group=None):
    """Return persisted observations, including uncertain/failed launches; never infer success."""
    repo = Path(repo).resolve()
    value = registry(repo)
    return dict(value, executors=[r for r in value['executors'] if group is None or r['group'] == group])


def record_check(repo, *, group, ticket, step, summary):
    """Persist a leader-confirmed inspection, without contacting any agent."""
    repo = Path(repo).resolve()
    if step not in (1, 2, 3) or not summary.strip():
        raise RuntimeError('Checagem exige etapa 1–3 e resumo')
    with pane_lock('kit:'+str(repo)):
        data = registry(repo)
        matches = [r for r in data['executors'] if r['group'] == group and r['ticket'] == ticket]
        if len(matches) != 1:
            raise RuntimeError('Executor sem correspondência única no grupo')
        record = matches[0]
        checks = record.setdefault('checks', [])
        if step != len(checks) + 1:
            raise RuntimeError('Registre cada checagem em ordem, sem repetir etapas')
        checks.append(dict(step=step, checked_at=time.time(), summary=summary.strip()))
        atomic(repo/'.watchdog/executors.json', data)
        return record


def contract(record, config):
    notice = shlex.join([str(ROOT/'watchdog'), 'aviso', '--lider', record['leader'],
                         '--pane', record['pane'], '--ticket', record['ticket']] +
                        (['--session',record['herdr_session']] if record['herdr_session'] else []))
    footer = DISPATCH.read_text().split('## Rodapé comum do contrato\n',1)[1].split('### CLI de aviso',1)[0]
    return (f"Executor {record['ticket']} · grupo {record['group']}\n"
            f"Projeto: {record['project']}\nWorktree: {record['worktree']}\nBranch: {record['branch']}\n"
            f"Pane próprio: {record['pane']}\nPane líder: {record['leader']}\n"
            f"Aceite: {record['acceptance']}\nSpec/plano: {record['spec']}\n"
            f"Leia GLOSSARY.md, AGENTS.md (## Dispatch) e {DISPATCH}.\n"
            f"Configuração do projeto:\n{config['dispatch']}\n\n"
            f"{footer}\nAntes do último commit: git merge {shlex.quote(config['integration'])}; "
            "execute os testes obrigatórios do Dispatch. Não abra outros executores.\n"
            f"Pronto: {notice} pronto --commit SHA --testes RESULTADO --resumo RESUMO\n"
            f"Dúvida não decidida: {notice} BLOQUEIO --duvida TEXTO\n")


def open_executor(repo, *, ticket, group, leader, workspace, leva, acceptance, spec,
                  dependencies=(), capacity=4, session=None):
    repo = Path(repo).resolve()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,39}', ticket):
        raise RuntimeError('Ticket deve ser um identificador simples')
    if capacity < 1:
        raise RuntimeError('Capacidade deve ser positiva')
    config = configuration(repo)
    base = git(repo, 'rev-parse', '--verify', 'refs/heads/'+config['integration'])
    api = Herdr(session)
    # Same mechanism as T6, different key: serialize project registry mutations,
    # while send() independently holds the actual target pane through Enter.
    with pane_lock('kit:'+str(repo)):
        data = registry(repo)
        if any(r['ticket'] == ticket and r['group'] == group for r in data['executors']):
            raise RuntimeError('Executor já registrado; confira antes de repetir')
        ignored_directories(repo)
        run_dir = repo/'.watchdog/run'/date.today().isoformat()
        run_dir.mkdir(parents=True, exist_ok=True)
        identity = uuid.uuid4().hex
        branch = 'watchdog/'+identity[:8]+'/'+ticket
        tree = repo/'.worktrees'/ticket
        if tree.exists():
            raise RuntimeError('Worktree já existe; preserve e confira antes de repetir')
        record = dict(id=identity, project=str(repo), group=group, ticket=ticket, leader=leader,
                      workspace=workspace, leva=leva, dependencies=list(dependencies),
                      branch=branch, integration=config['integration'], base=base, worktree=str(tree),
                      acceptance=acceptance, spec=spec, model=config['model'], effort=config['effort'],
                      herdr_session=session, pane=None, terminal=None, session=None, tab=None,
                      contract=str(run_dir/(ticket+'-'+identity[:8]+'-contrato.md')),
                      state='preparing', operation='worktree', created=date.today().isoformat(),
                      created_at=time.time())
        data['executors'].append(record)
        save = lambda: atomic(repo/'.watchdog/executors.json', data)
        save()
        try:
            git(repo, 'worktree', 'add', '-b', branch, str(tree), base)
            record['operation'] = 'pane'; save()
            # Later dependent tasks follow the dependency's leva. Inspect live
            # occupancy, including panes not created by the kit; never overfill.
            eligible = [r for r in data['executors'] if r is not record and r['group'] == group
                        and r['workspace'] == workspace and r.get('herdr_session') == session
                        and r['state'] == 'ready']
            candidates = [r for r in reversed(eligible) if r['ticket'] in dependencies]
            candidates += [r for r in reversed(eligible) if r['leva'] == leva and r not in candidates]
            target = None
            if candidates:
                live = api.call('pane','list','--workspace',workspace)['panes']
                for candidate in candidates:
                    members = [p for p in live if p['tab_id'] == candidate['tab']]
                    anchor = next((p for p in members if p['pane_id'] == candidate['pane']
                                   and p['terminal_id'] == candidate['terminal']), None)
                    if anchor and len(members) < capacity:
                        target = anchor; record['leva'] = candidate['leva']; break
            if target:
                pane = api.call('pane','split',target['pane_id'],'--direction','down',
                                '--cwd',str(tree),'--no-focus')['pane']
            else:
                pane = api.call('tab','create','--workspace',workspace,'--cwd',str(tree),
                                '--label',leva,'--no-focus')['root_pane']
            record.update(pane=pane['pane_id'], terminal=pane['terminal_id'], tab=pane['tab_id'], operation='start')
            save()
            Path(record['contract']).write_text(contract(record,config))
            permissions = config['permissions'].lower()
            sandbox = {'full access':'danger-full-access'}.get(permissions, permissions)
            api.call('agent','start','wd-'+identity[:12], '--kind','codex','--pane',record['pane'],
                     '--timeout','15000','--','--no-daemon','--model',config['model'],'--sandbox',sandbox,'--ask-for-approval','never',
                     '-c','model_reasoning_effort='+json.dumps(config['effort']))
            live = api.checked(pane)
            if live.get('agent') != 'codex':
                raise RuntimeError('Harness do executor não confirmado')
            native = live.get('agent_session') or {}
            record['session'] = native.get('value') if native.get('kind') == 'id' else None
            record['operation'] = 'contract'; save()
            with pane_lock(record['pane'], session):
                api.call('agent','prompt',record['pane'],Path(record['contract']).read_text(),
                         '--wait','--until','working','--timeout','15000')
            live = api.checked(pane)
            if live.get('agent') != 'codex':
                raise RuntimeError('Harness mudou após submissão do contrato')
            native = live.get('agent_session') or {}
            record['session'] = native.get('value') if native.get('kind') == 'id' else None
            record.update(state='ready', operation=None); save()
            return record
        except Exception as error:
            record.update(state='failed', error=str(error)); save()
            raise RuntimeError('Abertura não confirmada; recursos preservados, sem repetição automática: '+str(error)) from error


def close_issue(repo, *, issue, copy, comment):
    repo = Path(repo).resolve()
    path = (repo/copy).resolve()
    if not path.is_relative_to(repo) or not path.is_file():
        raise RuntimeError('Cópia local deve existir dentro do projeto')
    text = path.read_text()
    frontmatter = re.match(r'\A---\n(.*?)\n---(?:\n|$)', text, re.S)
    if not frontmatter:
        raise RuntimeError('Cópia local precisa de cabeçalho YAML válido')
    if not re.search(r'^number:\s*'+str(issue)+r'\s*$',frontmatter[1],re.M):
        raise RuntimeError('Número da cópia não corresponde à issue')
    if not comment.strip():
        raise RuntimeError('Comentário de evidências obrigatório')
    gh = lambda *args: command(['gh','issue',*args],cwd=repo)
    # Check status before mutation; closing an already closed issue must still
    # publish its evidence comment (gh close --comment silently drops it).
    existing = json.loads(gh('view',str(issue),'--json','number,state,comments'))
    if existing['number'] != issue:
        raise RuntimeError('Issue consultada não corresponde ao número solicitado')
    ignored_directories(repo)
    folder = repo/'.watchdog/run'/date.today().isoformat()
    folder.mkdir(parents=True,exist_ok=True)
    evidence = folder/(str(issue)+'-'+uuid.uuid4().hex[:8]+'-comentario.md')
    evidence.write_text(comment)
    if not any(entry.get('body') == comment for entry in existing['comments']):
        gh('comment',str(issue),'--body-file',str(evidence))
    if existing['state'].upper() != 'CLOSED':
        gh('close',str(issue))
    current = json.loads(gh('view',str(issue),'--json','number,title,body,labels,state,comments,url'))
    if current['number'] != issue or current['state'].upper() != 'CLOSED':
        raise RuntimeError('Fechamento não confirmado; confira issue antes de repetir')
    # Keep project-specific frontmatter such as parent/blocked_by, while taking
    # body, state and complete comments from the authoritative tracker.
    header = '\n'+frontmatter[1]+'\n'
    fields = {'number':str(issue), 'title':json.dumps(current['title'],ensure_ascii=False),
              'state':'closed', 'labels':json.dumps([v['name'] for v in current['labels']]),
              'url':current['url'], 'updated':date.today().isoformat()}
    for key,value in fields.items():
        if re.search(r'^'+key+':.*$',header,re.M):
            header = re.sub(r'^'+key+':.*$',lambda m:key+': '+value,header,flags=re.M)
        else:header += key+': '+value+'\n'
    result = '---'+header+'---\n\n'+current['body']+'\n'
    if current['comments']:
        result += '\n## Comentários\n'
        for entry in current['comments']:
            result += '\n### '+entry['createdAt']+' · '+entry['author']['login']+'\n\n'+entry['body']+'\n'
    # Only replace the copy after verified remote success. The evidence file
    # remains available if gh fails at any stage, without an automatic resend.
    temporary = path.with_name('.'+path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        temporary.write_text(result)
        temporary.replace(path)
    finally:temporary.unlink(missing_ok=True)
    return {'issue':issue,'state':'closed','copy':str(path),'comment':str(evidence)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest='action',required=True)
    opening = actions.add_parser('abrir')
    for flag in ('ticket','grupo','lider','workspace','leva','aceite','spec'):
        opening.add_argument('--'+flag,required=True)
    opening.add_argument('--depende',action='append',default=[])
    opening.add_argument('--capacidade',type=int,default=4)
    opening.add_argument('--session')
    listing = actions.add_parser('listar')
    listing.add_argument('--grupo')
    closing = actions.add_parser('fechar')
    closing.add_argument('--issue',type=int,required=True)
    closing.add_argument('--copia',required=True)
    closing.add_argument('--comentario',required=True)
    checking = actions.add_parser('checar')
    for flag in ('grupo','ticket','resumo'):checking.add_argument('--'+flag,required=True)
    checking.add_argument('--etapa',type=int,choices=(1,2,3),required=True)
    for sub in (opening,listing,closing,checking):sub.add_argument('--repo',type=Path,required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == 'abrir':
            result = open_executor(args.repo,ticket=args.ticket,group=args.grupo,leader=args.lider,
                                   workspace=args.workspace,leva=args.leva,acceptance=args.aceite,spec=args.spec,
                                   dependencies=args.depende,capacity=args.capacidade,session=args.session)
        elif args.action == 'checar':
            result = record_check(args.repo,group=args.grupo,ticket=args.ticket,step=args.etapa,summary=args.resumo)
        elif args.action == 'listar':result = executors(args.repo,args.grupo)
        else:result = close_issue(args.repo,issue=args.issue,copy=args.copia,comment=args.comentario)
        print(json.dumps(result,ensure_ascii=False,indent=2)); return 0
    except (RuntimeError,OSError,ValueError,KeyError) as error:
        print('Watchdog kit: '+str(error),file=sys.stderr); return 1
