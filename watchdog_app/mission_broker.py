"""Typed, frontend-scoped host bridge for a Codex sandbox's own Gossip peer.

This trusts the local user/runtime, not hostile code with unrestricted same-UID
host access. A shared app-server ancestor alone is NEVER sufficient identity.
"""
import json
import fcntl
from contextlib import contextmanager
import stat
import os
from pathlib import Path
import socket
import socketserver
import struct
import threading
import time

from . import bindings
from .mission_identity import check_context
from .mission_launch import command

LIMIT=131072


def process(pid):
    root=Path('/proc')/str(pid)
    tail=(root/'stat').read_text().rsplit(')',1)[1].split()
    if tail[0]=='Z' or root.stat().st_uid!=os.getuid():
        raise RuntimeError('Broker client is not a live process owned by this user')
    return int(tail[1]),tail[19]


def authorize(pid,uid,native,session):
    if uid!=os.getuid() or session!=native['session']:
        raise RuntimeError('Broker caller user or thread differs')
    current=pid
    client_started=None
    for _ in range(64):
        parent,started=process(current)
        if client_started is None:client_started=started
        if current==native['pid']:
            if str(started)!=str(native['started']):
                raise RuntimeError('Broker frontend PID was recycled')
            return client_started
        if parent<=1:break
        current=parent
    raise RuntimeError('Broker caller is not a descendant of this verified frontend')



@contextmanager
def context_lease(proof):
    # Rust File::lock uses the same flock lease on Linux. Never use a copied
    # registry path: Gossip explicitly requires its canonical context file.
    context=proof['context']
    path=Path(context['context_file']).with_suffix('.lock')
    fd=os.open(path,os.O_RDWR|os.O_NOFOLLOW)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode & 0o077 or info.st_nlink!=1 or path.stat().st_ino!=info.st_ino:
            raise RuntimeError('Context lock is not a private regular file')
        deadline=time.monotonic()+2
        while True:
            try:fcntl.flock(fd,fcntl.LOCK_SH|fcntl.LOCK_NB);break
            except BlockingIOError:
                if time.monotonic()>=deadline:raise RuntimeError('Context lease is busy')
                time.sleep(.02)
        yield
    finally:os.close(fd)


def request(store,identity,role,method,**data):
    store.path(identity)
    if role not in ('worker','qa'):raise RuntimeError('Broker role must be worker or qa')
    proof=json.loads((store.root/identity/(role+'-identity.json')).read_text())
    session=os.environ.get('CODEX_THREAD_ID')
    if session!=proof['native']['session']:
        raise RuntimeError('Broker request must originate in its assigned native conversation')
    payload=json.dumps({'run':identity,'role':role,'session':session,'method':method,'data':data}).encode()+b'\n'
    if len(payload)>LIMIT:raise RuntimeError('Broker request is too large')
    with socket.socket(socket.AF_UNIX) as sock:
        sock.settimeout(60)
        sock.connect(proof['broker'])
        sock.sendall(payload)
        with sock.makefile('rb') as stream:raw=stream.readline(LIMIT+1)
    if len(raw)>LIMIT or not raw.endswith(b'\n'):raise RuntimeError('Broker response is malformed or too large')
    value=json.loads(raw)
    if not value.get('ok'):raise RuntimeError(value.get('error','Broker refused request'))
    return value['result']


class Broker:
    def __init__(self,store,identity,role,proof,child):
        self.store=store;self.identity=identity;self.role=role
        self.proof=json.loads(json.dumps(proof));self.child=child
        self.slots=threading.BoundedSemaphore(2)
        self.path=Path(proof['broker'])
        if self.path.exists():raise RuntimeError('Broker socket already exists; inspect its owner')
        broker=self
        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                self.connection.settimeout(5)
                if not broker.slots.acquire(blocking=False):return
                try:
                    raw=self.rfile.readline(LIMIT+1)
                    if len(raw)>LIMIT or not raw.endswith(b'\n'):raise RuntimeError('Invalid broker payload size')
                    pid,uid,_=struct.unpack('3i',self.connection.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
                    result=broker.execute(pid,uid,json.loads(raw))
                    response={'ok':True,'result':result}
                except Exception as error:
                    response={'ok':False,'error':str(error)}
                finally:broker.slots.release()
                raw=json.dumps(response).encode()+b'\n'
                if len(raw)>LIMIT:raw=b'{"ok":false,"error":"Broker response too large"}\n'
                self.wfile.write(raw)
        class Server(socketserver.ThreadingMixIn,socketserver.UnixStreamServer):
            daemon_threads=True
        self.server=Server(str(self.path),Handler)
        os.chmod(self.path,0o600)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()

    def execute(self,pid,uid,message):
        from .mission_transport import Gossip,publish_identity,verify_graph,report
        if not isinstance(message,dict) or set(message)!={'run','role','session','method','data'}:
            raise RuntimeError('Malformed broker request')
        if message['run']!=self.identity or message['role']!=self.role:
            raise RuntimeError('Broker run or role differs')
        if self.child.poll() is not None:raise RuntimeError('Participant exited; broker access revoked')
        native=self.proof['native']
        client_started=authorize(pid,uid,native,message['session'])
        bindings.verify(bindings.engine().Binding(**native))
        with context_lease(self.proof):
            # Revalidate the pinned generation after acquiring the very same
            # lock used by Gossip bind, and hold it through the finite command.
            return self.execute_locked(message,caller=(pid,uid,client_started))

    def execute_locked(self,message,*,caller=None):
        from .mission_transport import Gossip,publish_identity,verify_graph,report
        native=self.proof['native']
        context=json.loads(command(['agent-gossip','context','show','--context',self.proof['context']['context_file']],timeout=5))
        check_context(context,native)
        if context!=self.proof['context']:raise RuntimeError('Broker context generation changed')
        run=self.store.load(self.identity);part=run['participants'][self.role]
        pane=run['resources'][self.role]
        if (part['account']!=native['account'] or pane['pane_id']!=native['pane'] or
                pane['terminal_id']!=native['terminal']):raise RuntimeError('Broker native assignment changed')
        state=json.loads(Path(context['state_file']).read_text())
        if (state.get('pubkey')!=self.proof['pubkey'] or state.get('nickname')!=part['nickname'] or
                state.get('gossip')!=run['transport']['gossip']):raise RuntimeError('Broker local signer changed')
        part.update(native=native,pubkey=self.proof['pubkey'],gossip_context=self.proof['context']['context_file'])
        gossip=Gossip(run['transport'],part['nickname'],session_context=self.proof['context']['context_file'])
        if caller is not None:
            pid,uid,started=caller
            if authorize(pid,uid,native,message['session'])!=started:
                raise RuntimeError('Broker caller exited or its PID was recycled')
        method=message['method'];data=message['data']
        if not isinstance(data,dict):raise RuntimeError('Broker data must be an object')
        if method=='enroll' and not data:
            publish_identity(run,self.role);verify_graph(run,self.role,gossip=gossip)
            return {'published':True,'role':self.role,'session':native['session']}
        if method=='poll' and set(data)=={'after'} and type(data['after']) is int and data['after']>=0:
            return gossip.poll(data['after'])
        if method=='report' and set(data)=={'report'}:
            return report(self.store,self.identity,self.role,data['report'],via_broker=False)
        raise RuntimeError('Unsupported broker operation or data')

    def close(self):
        self.server.shutdown();self.server.server_close();self.path.unlink(missing_ok=True)
