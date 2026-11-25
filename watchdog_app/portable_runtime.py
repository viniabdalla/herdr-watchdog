"""Codex identity from native Herdr + exact account transcript, on all OSes.

No database or clipboard dependency. Missing process evidence fails closed.
"""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from sys import platform

try:
    import psutil
except ImportError:
    psutil = None

from .herdr import Herdr


@dataclass
class Binding:
    kind: str
    session: str
    account: str
    pane: str
    terminal: str
    workspace: str
    history: str
    pid: int
    started: str

    @property
    def key(self):
        return hashlib.sha256((self.kind+'\0'+self.account+'\0'+self.session).encode()).hexdigest()


def herdr(*args):
    return Herdr().call(*args)


def process_info(pid):
    if psutil is None:
        raise RuntimeError('Process dependency unavailable; run Watchdog install.py')
    try:
        process = psutil.Process(int(pid))
        kind = process.name().lower().removesuffix('.exe')
        if kind not in ('codex', 'claude'):
            return None
        env = process.environ()
        if env.get('LEFT_UNDONE_ANALYZER') or not env.get('HERDR_PANE_ID'):
            return None
        account = Path(env.get('CODEX_HOME' if kind == 'codex' else 'CLAUDE_CONFIG_DIR',
                               str(Path.home()/('.codex' if kind == 'codex' else '.claude')))).resolve()
        # Preserve existing bindings on Linux; birth timestamp elsewhere defeats PID reuse.
        if platform == 'linux':
            fields = (Path('/proc')/str(pid)/'stat').read_text().split(') ',1)[1].split()
            started = fields[19]
        else:
            started = str(process.create_time())
        return dict(pid=int(pid), started=started, kind=kind,
                    pane=env['HERDR_PANE_ID'], account=str(account))
    except (psutil.Error, OSError, ValueError, IndexError) as error:
        raise RuntimeError('Process/account identity unavailable: '+str(error)) from error


def processes():
    result = []
    # Herdr abstracts Unix foreground groups and Windows process descendants.
    for live in herdr('agent','list')['agents']:
        if live.get('agent') != 'codex':
            continue
        try:
            pane = live['pane_id']
            foreground = herdr('pane','process-info','--pane',pane)['process_info']['foreground_processes']
            for process in foreground:
                info = process_info(process['pid'])
                if info and info['kind'] == 'codex' and info['pane'] == pane:
                    result.append(info)
        except (RuntimeError, KeyError):
            continue
    return result


def resolve_history(kind, account, session):
    if kind not in ('codex','claude') or not re.fullmatch(r'[A-Za-z0-9_-]+', session or ''):
        raise RuntimeError('Invalid session ID')
    root = (Path(account)/('sessions' if kind == 'codex' else 'projects')).resolve()
    pattern = '**/rollout-*'+session+'.jsonl' if kind == 'codex' else '*/'+session+'.jsonl'
    found = set()
    for path in root.glob(pattern):
        path = path.resolve()
        if not path.is_relative_to(root):
            continue
        try:
            with path.open(encoding='utf-8') as stream:
                for _ in range(50):
                    line = stream.readline(4*1024*1024)
                    if not line:
                        break
                    row = json.loads(line)
                    sid = row.get('payload',{}).get('id') if row.get('type') == 'session_meta' else row.get('sessionId')
                    if sid == session:
                        found.add(path)
                        break
        except (OSError, ValueError, AttributeError):
            continue
    if len(found) != 1:
        raise RuntimeError('Session history is missing or ambiguous for this account')
    return found.pop()


def project_root(directory):
    path = Path(directory).resolve()
    try:
        result = subprocess.run(['git','-C',str(path),'rev-parse','--show-toplevel'],
                                env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')},
                                capture_output=True,text=True,timeout=5)
        if result.returncode == 0:
            return Path(result.stdout.strip()).resolve()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return path


def binding_project(binding):
    try:
        with Path(binding.history).open(encoding='utf-8') as stream:
            for _ in range(1000):
                line = stream.readline(4*1024*1024)
                if not line:
                    break
                row = json.loads(line)
                meta = row.get('payload',{}) if row.get('type') == 'session_meta' else row
                if meta.get('id',meta.get('sessionId')) == binding.session and meta.get('cwd'):
                    return project_root(meta['cwd'])
    except (OSError, ValueError, AttributeError):
        pass
    return None


def candidates(*, titles=None):
    result, errors = [], []
    for live in herdr('agent','list')['agents']:
        if live.get('agent') != 'codex':
            continue
        try:
            pane = live['pane_id']
            foreground = herdr('pane','process-info','--pane',pane)['process_info']['foreground_processes']
            procs = [process_info(p['pid']) for p in foreground]
            procs = [p for p in procs if p and p['kind']=='codex' and p['pane']==pane]
            if len(procs) != 1:
                raise RuntimeError('Foreground process/account is missing or ambiguous')
            native = live.get('agent_session') or {}
            if native.get('kind') != 'id':
                raise RuntimeError('Native session ID unavailable')
            sid = native['value']; process = procs[0]
            history = resolve_history('codex',process['account'],sid)
            result.append(Binding('codex',sid,process['account'],pane,live['terminal_id'],
                                  live['workspace_id'],str(history),process['pid'],process['started']))
            if titles is not None:
                titles[pane] = live.get('terminal_title_stripped','')
        except (RuntimeError, KeyError) as error:
            errors.append(live.get('pane_id','?')+': '+str(error))
    return result, errors


class AgentBusy(RuntimeError):
    pass


def verify(binding, ready=False):
    live = herdr('agent','get',binding.pane)['agent']
    native = live.get('agent_session') or {}
    if (live.get('pane_id'),live.get('terminal_id'),live.get('agent'),native.get('kind'),native.get('value')) != (
            binding.pane,binding.terminal,binding.kind,'id',binding.session):
        raise RuntimeError('Native conversation identity changed')
    foreground = herdr('pane','process-info','--pane',binding.pane)['process_info']['foreground_processes']
    if binding.pid not in [p['pid'] for p in foreground]:
        raise RuntimeError('Verified process no longer occupies the pane')
    proc = process_info(binding.pid)
    if not proc or any(proc[key] != getattr(binding,key) for key in ('started','kind','pane','account')):
        raise RuntimeError('Process or account changed')
    if resolve_history(binding.kind,binding.account,binding.session) != Path(binding.history):
        raise RuntimeError('Session history changed')
    if ready and live.get('agent_status') not in ('idle','done'):
        raise AgentBusy('Wait for the agent to finish')
    return live


def send(binding, message):
    verify(binding, ready=True)
    from .pane_delivery import send as deliver
    return deliver(binding.pane,message,api=Herdr())


def queue(binding, message):
    raise RuntimeError('Native queue unavailable in portable Codex runtime; use verified pane delivery')
