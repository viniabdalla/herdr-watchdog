"""Durable observed project transitions. TODO remains the authority.

The TODO lock serializes observation and writes. A write-ahead intent survives a
crash between file exchange and history finalization. Recovery never writes TODO.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import uuid
from .store import atomic
from .todo import locked, Snapshot
from .todo_format import canonical_id


def stamp():return datetime.now(timezone.utc).isoformat()


def path(repo,root):
    return Path(root)/'project-history'/(hashlib.sha256(str(Path(repo).resolve()).encode()).hexdigest()+'.json')


def load(repo,root):
    file=path(repo,root)
    if file.exists():
        data=json.loads(file.read_text())
        if data.get('version')!=1 or data.get('project')!=str(repo):raise RuntimeError('Invalid project history')
        return data
    return dict(version=1,project=str(repo),digest=None,states={},events=[],pending=None)


def states(snapshot):
    return {t.id:dict(state=t.section,content_digest=hashlib.sha256(t.text.encode()).hexdigest())
            for t in snapshot.tasks if canonical_id(t.id)}


def record(data, digest, current, evidence, *, observed_at=None):
    if data['digest']==digest and data['states']==current:return
    old=data['states'];when=observed_at or stamp()
    for key in sorted(set(old)|set(current)):
        before=old.get(key,dict(state='absent',content_digest=None))
        after=current.get(key,dict(state='absent',content_digest=None))
        if before==after:continue
        data['events'].append(dict(event_id=str(uuid.uuid4()),id=key,observed_at=when,
            **{'from':before['state'],'to':after['state']},
            source_digest=data['digest'],digest=digest,before_content_digest=before['content_digest'],
            content_digest=after['content_digest'],evidence=evidence.get(key,'external observation; verification not established')))
    data.update(digest=digest,states=current)


def recover(data,snapshot):
    pending=data['pending']
    if not pending:return
    if snapshot.digest==pending['after_digest']:
        record(data,snapshot.digest,states(snapshot),pending['evidence'],observed_at=stamp())
    elif snapshot.digest!=pending['before_digest']:
        # Retain the unresolved intent and report it. A competing editor's bytes
        # are neither attributed to the operation nor silently called complete.
        raise RuntimeError('Project history recovery conflict; TODO differs from both saved intent digests')
    data['pending']=None


def prepare(snapshot,raw,root,actions=()):
    """Called with TODO lock held, before any source replacement."""
    data=load(snapshot.repo,root);recover(data,snapshot)
    record(data,snapshot.digest,states(snapshot),{})
    target=Snapshot.parse(snapshot.repo,raw)
    data['pending']=dict(operation_id=str(uuid.uuid4()),prepared_at=stamp(),
        before_digest=snapshot.digest,after_digest=target.digest,
        evidence={a['id']:str(a.get('evidence','confirmed edit; verification not supplied'))[:2000]
                  for a in actions if 'id' in a})
    atomic(path(snapshot.repo,root),data)


def finish(snapshot,root):
    """Called with TODO lock held, after successful exchange or on recovery."""
    data=load(snapshot.repo,root);recover(data,snapshot)
    record(data,snapshot.digest,states(snapshot),{})
    atomic(path(snapshot.repo,root),data)
    return data


def observe(snapshot,root=None):
    with locked(snapshot.repo,root) as root:
        current=snapshot.assert_current()
        return finish(current,root)


def read(repo,root=None):
    repo=Path(repo).resolve()
    with locked(repo,root) as root:return load(repo,root)
