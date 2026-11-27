"""Explicit, hash-bound managed instruction preview/check/apply. Stdlib only."""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import stat
import re
import sys
import tempfile
from .todo import locked, exchange, preserve
import uuid

BEGIN='<!-- watchdog-todo:begin -->'
END='<!-- watchdog-todo:end -->'
NAMES=('AGENTS.md','CLAUDE.md')
LIMIT=256*1024
TEMPLATES=Path(__file__).resolve().parents[1]/'docs/templates'
TODO_RULE='docs/agents/todo.md'
TRACKER='docs/agents/issue-tracker.md'
PUBLISH='## When a skill says "publish to the issue tracker"'
BODY='''Watchdog TODO instructions v1
Use this project's TODO.md as the authoritative list (watchdog_todo: 1).
At a human request, record/update its task during the conversation, without waiting
for a commit, within the authorized project. The project leader maintains content.
Keep a plain title and Resumo understandable to the person. Put technical scope,
allowed files, dependencies and checks in Execução; put completion criteria in Aceite.
Retain the canonical UUID in ID across edits, moves, completion and reopening.
Origem distinguishes pedido-humano, sugestao-agente and legado-nao-confirmado.
Keep agent suggestions visibly labelled; a suggestion is not a human request.
Use Em andamento / Próximo / Bloqueado / Feito (or In progress / Next / Blocked / Done).
An open checkbox belongs in an open state; a checked task belongs in Feito/Done.
Record a concrete Motivo for blockers. Completion requires evidence against Aceite:
what changed, verification results and limitations, with source references.
Omission, dispatch, a worker result, or run approval alone never completes a task.
Preview task changes and obtain the required human confirmation through Watchdog;
apply only to the explicitly authorized project/action. Preserve existing rules.
Read the installed block in the actual agent conversation and acknowledge its
version and how a request/suggestion/completion will be handled. File installation
alone does not establish that an agent read or followed these instructions.
'''


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def project(repo):
    path=Path(repo).absolute()
    if any(p.is_symlink() for p in (path,*path.parents)):
        raise RuntimeError('Symlink project path refused')
    if not path.is_dir():raise RuntimeError('Select an existing project')
    return path.resolve()


def read_regular(path, limit=LIMIT, missing=False):
    try:
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    except FileNotFoundError:
        if missing:return None
        raise
    except OSError as error:raise RuntimeError('Unsafe file: '+str(path)) from error
    with os.fdopen(fd,'rb') as f:
        info=os.fstat(f.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise RuntimeError('Regular file with a single link required: '+str(path))
        raw=f.read(limit+1)
        if len(raw)>limit:raise RuntimeError('File exceeds byte limit')
        return raw



def validate_context(text):
    """Managed rules must be outside closed Markdown backtick/tilde fences."""
    fence=None
    for line in text.splitlines():
        if 'watchdog-todo:' in line and fence:
            raise RuntimeError('Managed markers inside a code fence are ambiguous')
        mark=re.match(r'^\s*(`{3,}|~{3,})(.*)$',line)
        if not mark:continue
        if fence is None:
            fence=mark[1]
        elif mark[1][0]==fence[0] and len(mark[1])>=len(fence) and not mark[2].strip():
            fence=None
    if fence is not None:
        raise RuntimeError('Unclosed Markdown fence; reconcile before instruction installation')


def proposed(raw):
    text=(raw or b'').decode('utf-8')
    validate_context(text)
    nl='\r\n' if b'\r\n' in (raw or b'') else '\n'
    block=BEGIN+nl+BODY.replace('\n',nl)+END
    markers=[line for line in text.splitlines() if 'watchdog-todo:' in line]
    if not markers:
        if 'Watchdog TODO instructions' in text:
            raise RuntimeError('Unmanaged conflicting instructions; reconcile manually')
        result=text+('' if not text or text.endswith('\n') else nl)+block+nl
        validate_context(result)
        return result.encode()
    if markers != [BEGIN,END] or text.count(BEGIN)!=1 or text.count(END)!=1:
        raise RuntimeError('Ambiguous managed markers; reconcile manually')
    start=text.index(BEGIN);end=text.index(END)+len(END)
    if end<=start:raise RuntimeError('Reversed managed markers')
    if 'Watchdog TODO instructions' in text[:start]+text[end:]:
        raise RuntimeError('Unmanaged conflicting instructions outside managed block')
    result=text[:start]+block+text[end:]
    validate_context(result)
    return result.encode()


def safe_path(repo, name):
    path=repo/name
    for parent in path.parents:
        if parent==repo:break
        if parent.is_symlink():raise RuntimeError('Symlink instruction directory refused: '+str(parent))
    return path


def headings(text):
    """Return real headings, ignoring fenced examples in copied templates."""
    result=[];fence=None;offset=0
    for line in text.splitlines(True):
        mark=re.match(r'^\s*(`{3,}|~{3,})(.*)$',line)
        if mark:
            if fence is None:fence=mark[1]
            elif mark[1][0]==fence[0] and len(mark[1])>=len(fence) and not mark[2].strip():fence=None
        elif fence is None:
            match=re.match(r'^(#{1,6}) (.+?)\s*$',line)
            if match:result.append((match[0].strip(),len(match[1]),offset))
        offset+=len(line)
    return result


def append_section(text, heading, body):
    """Fill an absent section; preserve every byte of an existing section."""
    if any(h==heading for h,_,_ in headings(text)):return text
    nl='\r\n' if '\r\n' in text else '\n'
    body=body.replace('\r\n','\n').replace('\n',nl)
    return text+('' if not text else nl+nl)+heading+nl+nl+body.rstrip()+nl


def in_section(text, heading, body, present):
    sections=headings(text)
    for i,(title,level,start) in enumerate(sections):
        if title!=heading:continue
        end=next((pos for _,depth,pos in sections[i+1:] if depth<=level),len(text))
        if present(text[start:end]):return text
        nl='\r\n' if '\r\n' in text else '\n'
        body=body.replace('\r\n','\n').replace('\n',nl)
        return text[:end]+nl+body.rstrip()+nl+nl+text[end:]
    return append_section(text,heading,body)


def todo_proposed(name, raw):
    text=(raw or b'').decode('utf-8')
    validate_context(text)
    if name=='AGENTS.md':
        pointer='### TODO\n\nTODO.md no formato do Watchdog (`watchdog_todo: 1`). See `docs/agents/todo.md`.'
        text=in_section(text,'## Agent skills',pointer,
                        lambda section:any(h=='### TODO' for h,_,_ in headings(section)))
    elif name==TODO_RULE:
        template=read_regular(TEMPLATES/'agents-todo.md').decode()
        template=re.sub(r'^<!--.*?-->\s*','',template,flags=re.S)
        template=template.replace('modelo `docs/templates/todo.md`\n  em `/home/tropico/Projects/herdr-watchdog`',
                                  'modelo na seção "Modelo local do TODO.md" deste arquivo')
        template=template.replace(' (`/home/tropico/Projects/herdr-watchdog`)','')
        if raw is None:text=template
        else:
            sections=headings(template)
            for i,(heading,_,start) in enumerate(sections):
                end=sections[i+1][2] if i+1<len(sections) else len(template)
                text=append_section(text,heading,template[start+len(heading):end].strip())
        skeleton=read_regular(TEMPLATES/'todo.md').decode()
        text=append_section(text,'## Modelo local do TODO.md','```markdown\n'+skeleton.rstrip()+'\n```')
    elif name==TRACKER:
        trigger=read_regular(TEMPLATES/'issue-tracker-todo.md').decode()
        trigger=re.sub(r'^<!--.*?-->\s*','',trigger,flags=re.S).strip()
        text=in_section(text,PUBLISH,trigger,lambda section:trigger in section.replace('\r\n','\n'))
    validate_context(text)
    return text.encode()


def preview(repo):
    repo=project(repo);files=[];warnings=[]
    tracker=read_regular(safe_path(repo,TRACKER),missing=True)
    names=(*NAMES,TODO_RULE,*((TRACKER,) if tracker is not None else ()))
    if tracker is None:
        warnings.append('Falta docs/agents/issue-tracker.md: rode /setup-matt-pocock-skills; o arquivo não será criado.')
    for name in names:
        before=read_regular(safe_path(repo,name),missing=True)
        after=proposed(before) if name in NAMES else before
        if name!='CLAUDE.md':after=todo_proposed(name,after)
        files.append({'path':name,'before_hash':digest(before) if before is not None else None,
            'after':after.decode(),'after_hash':digest(after),
            'status':'absent' if before is None else 'current' if before==after else 'outdated',
            'diff':''.join(difflib.unified_diff((before or b'').decode().splitlines(True),
                        after.decode().splitlines(True),fromfile=name,tofile=name))})
    return {'version':1,'project':str(repo),'files':files,'warnings':warnings,'agent_reading':'manual-unobserved'}


def check(repo):
    plan=preview(repo)
    plan['status']='current' if all(f['status']=='current' for f in plan['files']) else 'outdated'
    return plan


def apply(repo, plan, *, confirmed=False, root=None):
    if confirmed is not True:raise RuntimeError('Explicit confirmation of displayed preview required')
    repo=project(repo)
    with locked(repo,root) as root:
        if plan!=preview(repo):raise RuntimeError('Stale or modified preview; display a fresh preview')
        saved=[]
        try:
            for entry in plan['files']:
                if entry['status']=='current':continue
                path=safe_path(repo,entry['path']);before=read_regular(path,missing=True)
                if (digest(before) if before is not None else None)!=entry['before_hash']:
                    raise RuntimeError('Instructions changed during apply; display a fresh preview')
                after=entry['after'].encode()
                path.parent.mkdir(parents=True,exist_ok=True)
                safe_path(repo,entry['path'])
                fd,temp=tempfile.mkstemp(prefix='.watchdog-instructions-',dir=path.parent)
                try:
                    with os.fdopen(fd,'wb') as f:
                        f.write(after);f.flush();os.fsync(f.fileno())
                    if before is None:
                        os.link(temp,path) # exclusive creation, never replace a concurrent user file
                    else:
                        os.chmod(temp,stat.S_IMODE(path.stat().st_mode))
                        exchange(temp,path)
                        if Path(temp).read_bytes()!=before:
                            backup = root / 'instruction-conflicts'
                            backup.mkdir(parents=True,exist_ok=True)
                            expected=after
                            for _ in range(8):
                                candidate=Path(temp).read_bytes()
                                (backup/(uuid.uuid4().hex+'.md')).write_bytes(candidate)
                                exchange(temp,path)
                                if Path(temp).read_bytes()==expected:break
                                expected=candidate
                            preserve(temp,backup)
                            raise RuntimeError('Instructions changed during apply; competing versions preserved in '+str(backup))
                    saved.append((path,before,after))
                finally:Path(temp).unlink(missing_ok=True)
        except Exception as error:
            # Each completed file is installed atomically. Do not overwrite a
            # concurrent editor to roll back an earlier independent file.
            if saved:
                raise RuntimeError('Partial installation: '+', '.join(p.name for p,_,_ in saved)+
                                   '; display a fresh preview to continue. '+str(error)) from error
            raise
    return check(repo)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('preview','check','apply'))
    parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--preview-file',type=Path)
    parser.add_argument('--confirm',action='store_true')
    parser.add_argument('--human',action='store_true',help='Print exact unified changes instead of JSON')
    args=parser.parse_args(argv)
    try:
        if args.action=='apply':
            if not args.preview_file:raise RuntimeError('Supply the exact previously displayed --preview-file')
            plan=json.loads(read_regular(args.preview_file,2*1024*1024))
            if not isinstance(plan,dict) or not isinstance(plan.get('files'),list):
                raise RuntimeError('Invalid instruction preview')
            for entry in plan['files']:
                if not isinstance(entry,dict):raise RuntimeError('Invalid instruction preview entry')
                print(entry.get('diff',''),file=sys.stderr,end='')
            result=apply(args.repo,plan,confirmed=args.confirm)
        else:result=check(args.repo) if args.action=='check' else preview(args.repo)
        if args.human:
            print('Project: '+result['project'])
            for entry in result['files']:
                print(entry['path']+': '+entry['status'])
                print(entry['diff'],end='')
            for warning in result['warnings']:print('Warning: '+warning)
            print('Agent reading: '+result['agent_reading'])
        else:print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0
    except (RuntimeError,OSError,ValueError) as e:
        print('Watchdog: '+str(e),file=sys.stderr);return 1
