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


def proposed(raw):
    text=(raw or b'').decode('utf-8')
    nl='\r\n' if b'\r\n' in (raw or b'') else '\n'
    block=BEGIN+nl+BODY.replace('\n',nl)+END
    markers=[line for line in text.splitlines() if 'watchdog-todo:' in line]
    if not markers:
        if 'Watchdog TODO instructions' in text:
            raise RuntimeError('Unmanaged conflicting instructions; reconcile manually')
        return (text+('' if not text or text.endswith('\n') else nl)+block+nl).encode()
    if markers != [BEGIN,END] or text.count(BEGIN)!=1 or text.count(END)!=1:
        raise RuntimeError('Ambiguous managed markers; reconcile manually')
    fence=None
    for line in text.splitlines():
        mark=re.match(r'^\s*(`{3,}|~{3,})(.*)$',line)
        if mark:
            if fence is None:fence=mark[1]
            elif mark[1][0]==fence[0] and len(mark[1])>=len(fence) and not mark[2].strip():fence=None
        if 'watchdog-todo:' in line and fence:
            raise RuntimeError('Managed markers inside a code fence are ambiguous')
    start=text.index(BEGIN);end=text.index(END)+len(END)
    if end<=start:raise RuntimeError('Reversed managed markers')
    if 'Watchdog TODO instructions' in text[:start]+text[end:]:
        raise RuntimeError('Unmanaged conflicting instructions outside managed block')
    return (text[:start]+block+text[end:]).encode()


def preview(repo):
    repo=project(repo);files=[]
    for name in NAMES:
        before=read_regular(repo/name,missing=True);after=proposed(before)
        files.append({'path':name,'before_hash':digest(before) if before is not None else None,
            'after':after.decode(),'after_hash':digest(after),
            'status':'absent' if before is None else 'current' if before==after else 'outdated',
            'diff':''.join(difflib.unified_diff((before or b'').decode().splitlines(True),
                        after.decode().splitlines(True),fromfile=name,tofile=name))})
    return {'version':1,'project':str(repo),'files':files,'agent_reading':'manual-unobserved'}


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
                path=repo/entry['path'];before=read_regular(path,missing=True)
                if (digest(before) if before is not None else None)!=entry['before_hash']:
                    raise RuntimeError('Instructions changed during apply; display a fresh preview')
                after=entry['after'].encode()
                fd,temp=tempfile.mkstemp(prefix='.watchdog-instructions-',dir=repo)
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
            print('Agent reading: '+result['agent_reading'])
        else:print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0
    except (RuntimeError,OSError,ValueError) as e:
        print('Watchdog: '+str(e),file=sys.stderr);return 1
