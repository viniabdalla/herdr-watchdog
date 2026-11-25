"""Persisted, marker-proven Religar. A command's inherited pane is not evidence."""
from contextlib import contextmanager
from dataclasses import asdict, replace
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from types import SimpleNamespace
import uuid

from . import bindings
from .herdr import Herdr
from .portable_runtime import project_root
from .store import Store, atomic, state_root

TERMINAL = ('confirmed', 'failed', 'cancelled')


def _path(ref):
    if not re.fullmatch(r'[0-9a-f]{32}', ref or ''):
        raise RuntimeError('Referência de Religar inválida')
    return state_root()/'relink'/(ref+'.json')


def read(ref):
    return json.loads(_path(ref).read_text())


def _index(file):
    return state_root()/'relink'/('origin-'+hashlib.sha256(str(Path(file).resolve()).encode()).hexdigest()+'.json')


def pending_for(binding_file):
    try:
        return json.loads(_index(binding_file).read_text())['ref']
    except FileNotFoundError:
        return None


@contextmanager
def _lock(file):
    # A separate key: Store.transfer owns the actual binding locks.
    key = 'relink-'+hashlib.sha256(str(Path(file).resolve()).encode()).hexdigest()
    with Store().lock(SimpleNamespace(key=key)):
        yield


def _save(op, state=None, notice=None):
    value=dict(op)
    if state is not None:value['state']=state
    if notice is not None:value['notice']=notice
    value['updated']=time.time()
    atomic(_path(value['ref']),value)
    op.update(value)
    return op


def begin(session, candidate):
    if not session.binding or candidate.kind!='codex':
        raise RuntimeError('Religar pela skill exige um alvo Codex')
    file=str(session.file.resolve())
    with _lock(file):
        previous=pending_for(file)
        if previous:
            op=read(previous)
            if op['state']=='transferring':
                raise RuntimeError('Transferência interrompida; retome a tentativa existente')
            if op['state'] not in TERMINAL:_save(op,'cancelled','Tentativa substituída')
        source=json.loads(Path(file).read_text())
        if source.get('binding')!=asdict(session.binding) or source.get('ownership') in ('released','transferring'):
            raise RuntimeError('A origem mudou; reabra o Tasks')
        ref=uuid.uuid4().hex
        op=dict(ref=ref,state='pending',pane=candidate.pane,notice='Aguardando a skill no pane escolhido',
                binding_file=file,repo=str(session.repo.resolve()),origin=asdict(session.binding),
                candidate=asdict(candidate),created=time.time(),successor=None,
                sources={key:os.environ[key] for key in ('HERDR_BIN_PATH','HERDR_SOCKET_PATH','HERDR_SESSION') if key in os.environ})
        _target(op,candidate,session.runtime,_api(op),marker=False)
        _save(op)
        atomic(_index(file),{'ref':ref})
        return ref


def guard(binding_file):
    ref=pending_for(binding_file)
    if ref and read(ref)['state'] not in TERMINAL:
        raise RuntimeError('Religar em andamento; aguarde a prova ou cancele a tentativa')


def cancel(ref):
    op=read(ref)
    with _lock(op['binding_file']):
        op=read(ref)
        if op['state']=='transferring':
            raise RuntimeError('Transferência em curso; retome para concluir com segurança')
        if op['state'] not in TERMINAL:_save(op,'cancelled','Religar cancelado')
        return op


class _TargetHerdr(Herdr):
    """Use the server captured by the panel, not the daemon's inherited server."""
    def __init__(self, sources):
        super().__init__()
        self.environment={k:v for k,v in os.environ.items() if not k.startswith('HERDR_')}
        self.environment.update(sources)
        self.prefix=[sources.get('HERDR_BIN_PATH','herdr')]

    def output(self,*args):
        try:
            result=subprocess.run(self.prefix+list(args),env=self.environment,
                                  capture_output=True,text=True,timeout=20)
        except subprocess.TimeoutExpired as error:
            raise RuntimeError('Herdr demorou; confira o destino antes de retomar') from error
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or 'Herdr falhou')
        return result.stdout


def _api(op):
    return _TargetHerdr(op['sources'])


def process_proof(candidate, repo, runtime):
    """Check the real target via portable OS APIs; never require caller ancestry."""
    try:
        import psutil
    except ImportError as error:
        raise RuntimeError('Religar exige psutil; execute novamente o instalador do Watchdog') from error
    try:
        process=psutil.Process(candidate.pid)
        env=process.environ()
        argv=process.cmdline()
        name=Path(process.name()).stem.lower()
        if name!='codex' or 'app-server' in argv:
            raise RuntimeError('O alvo não é o Codex interativo')
        account=Path(env.get('CODEX_HOME',str(Path.home()/'.codex'))).resolve()
        if account!=Path(candidate.account).resolve() or env.get('HERDR_PANE_ID')!=candidate.pane:
            raise RuntimeError('Processo, pane ou conta do alvo mudou')
        current=runtime.process_info(candidate.pid)
        if not current or any(str(current[k])!=str(getattr(candidate,k)) for k in ('pid','started','kind','pane','account')):
            raise RuntimeError('O processo do alvo foi substituído')
        # A nested repository or another worktree is a distinct project.
        if project_root(process.cwd()) != project_root(repo):
            raise RuntimeError('O processo do alvo está em outro projeto')
    except psutil.Error as error:
        raise RuntimeError('Não foi possível conferir o processo do alvo: '+str(error)) from error


def _history_proof(path, session, repo, marker, created):
    metadata=False;fresh=False
    now=time.time()
    with Path(path).open('rb') as stream:
        # Session metadata is at the start, recent messages at the bounded tail.
        first=stream.readline(1024*1024)
        stream.seek(0,2);offset=max(0,stream.tell()-4*1024*1024);stream.seek(offset)
        if offset:stream.readline()
        lines=[first]+stream.read().splitlines()
    for line in lines:
        try:
            row=json.loads(line);p=row.get('payload',{})
            if row.get('type')=='session_meta':
                metadata |= p.get('id')==session and bool(p.get('cwd')) and project_root(p['cwd'])==project_root(repo)
            if (row.get('type')!='response_item' or p.get('type')!='message' or p.get('role')!='assistant'
                    or p.get('phase',p.get('channel'))!='commentary'):continue
            stamp=datetime.fromisoformat(row['timestamp'].replace('Z','+00:00')).timestamp()
            if not max(created,now-300)<=stamp<=now+1:continue
            for part in p.get('content',[]):
                if part.get('type')=='output_text' and re.search(r'(?<![A-Za-z0-9-])'+re.escape(marker)+r'(?![A-Za-z0-9-])',part.get('text','')):
                    fresh=True
        except (ValueError,KeyError,TypeError,AttributeError):continue
    if not metadata:raise RuntimeError('Histórico não comprova a sessão e o projeto do alvo')
    if not fresh:raise RuntimeError('Marcador ausente em comentário recente da sessão real')


def _target(op,new,runtime,api,*,marker=True):
    process_proof(new,op['repo'],runtime)
    api.checked({'pane_id':new.pane,'terminal_id':new.terminal})
    live=api.call('agent','get',new.pane)['agent']
    if (live.get('pane_id'),live.get('terminal_id'),live.get('workspace_id'),live.get('agent'))!=(new.pane,new.terminal,new.workspace,'codex'):
        raise RuntimeError('A identidade do alvo Herdr mudou')
    foreground=api.call('pane','process-info','--pane',new.pane)['process_info']['foreground_processes']
    if new.pid not in [p['pid'] for p in foreground]:
        raise RuntimeError('Codex escolhido não está em primeiro plano')
    if not marker:return live
    visible=api.output('pane','read',new.pane,'--source','visible','--format','text')
    visible=re.sub(r'\r?\n[ \t]*','',visible)
    pattern=r'(?<![A-Za-z0-9-])LU-'+op['ref']+r'(?![A-Za-z0-9-])'
    if not re.search(pattern,visible):
        raise RuntimeError('O marcador não está visível no pane escolhido')
    for other in api.call('agent','list')['agents']:
        if other.get('agent')!='codex' or other.get('pane_id')==new.pane:continue
        text=api.output('pane','read',other['pane_id'],'--source','visible','--format','text')
        if re.search(pattern,re.sub(r'\r?\n[ \t]*','',text)):
            raise RuntimeError('Marcador ambíguo: visível em mais de um pane Codex')
    return live


def complete(ref):
    op=read(ref)
    with _lock(op['binding_file']):
        op=read(ref)
        if op['state']=='confirmed':return op
        if op['state'] in ('cancelled','failed') or pending_for(op['binding_file'])!=ref:
            raise RuntimeError('Tentativa de Religar encerrada ou substituída')
        try:
            runtime=bindings.engine();candidate=runtime.Binding(**op['candidate'])
            session=os.environ.get('CODEX_THREAD_ID','')
            if not re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',session):
                raise RuntimeError('Execute watchdog religar no contexto real do Codex (CODEX_THREAD_ID)')
            if op['state']=='transferring':
                new=runtime.Binding(**op['proven'])
                if new.session!=session:raise RuntimeError('Retomada pertence a outra sessão Codex')
            else:
                history=runtime.resolve_history('codex',candidate.account,session)
                new=replace(candidate,session=session,history=str(history))
                _history_proof(history,session,op['repo'],'LU-'+ref,op['created'])
            api=_api(op)
            live=_target(op,new,runtime,api,marker=op['state']!='transferring')
            advertised=live.get('agent_session') or {}
            if advertised.get('kind')!='id' or advertised.get('value')!=session:
                if op['state']=='transferring':
                    raise RuntimeError('O registro nativo mudou durante a transferência')
                if advertised.get('kind')=='id' and advertised.get('value')!=candidate.session:
                    raise RuntimeError('A sessão anunciada do alvo mudou durante a tentativa')
                # A fresh marker proves the replacement within this exact process/terminal.
                report=['pane','report-agent-session',new.pane,'--source','herdr:codex',
                        '--agent','codex','--seq',str(time.time_ns()),'--agent-session-id',session]
                if advertised.get('kind')=='id':report+=['--session-start-source','clear']
                api.call(*report)
            live=_target(op,new,runtime,api,marker=op['state']!='transferring')
            recorded=live.get('agent_session') or {}
            if recorded.get('kind')!='id' or recorded.get('value')!=session:
                raise RuntimeError('O registro nativo ainda não anuncia a sessão comprovada')
            runtime.verify(new)
            op['proven']=asdict(new)
            _save(op,'transferring','Gravando e conferindo o vínculo')
            old=runtime.Binding(**op['origin'])
            target=Store(Path(op['binding_file']).parent).transfer(op['binding_file'],old,new,
                         Path(op['repo']),ref,api=api)
            saved=json.loads(Path(target).read_text())
            if saved.get('binding')!=asdict(new) or saved.get('ownership','active')!='active':
                raise RuntimeError('O vínculo reaberto diverge da sessão comprovada')
            runtime.verify(new)
            op['successor']=str(target)
            return _save(op,'confirmed','Líder ligado · '+new.pane+' · '+session[:8])
        except (RuntimeError,OSError,ValueError,KeyError,TypeError) as error:
            # Only a transfer that relinquished/refreshed ownership needs recovery.
            # A rejected destination must leave the intact origin free to try again.
            recoverable=op['state']=='transferring'
            if recoverable:
                try:
                    source=json.loads(Path(op['binding_file']).read_text())
                    recoverable=(source.get('outgoing_transfer_operation')==ref or
                                 source.get('last_refresh_operation')==ref)
                except (OSError,ValueError):
                    pass  # Unreadable storage cannot establish that relinquishment did not occur.
            _save(op, None if recoverable else 'failed',str(error))
            raise


def main(argv=None):
    import argparse
    parser=argparse.ArgumentParser(prog='watchdog religar')
    parser.add_argument('ref')
    args=parser.parse_args(argv)
    try:
        result=complete(args.ref)
        print(result['notice'])
        return 0
    except (RuntimeError,OSError,ValueError,KeyError,TypeError) as error:
        print('Religar: '+str(error),file=sys.stderr)
        return 1
