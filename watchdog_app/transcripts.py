"""Bounded read-only JSONL tailing. No transcript content is ever executed."""
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import stat


@dataclass
class Batch:
    records: list = field(default_factory=list)
    reset: bool = False
    catching_up: bool = False
    unavailable: str = ''
    incomplete: bool = False
    discarded: bool = False


class Reader:
    def __init__(self, path, *, budget=256*1024, max_line=1024*1024):
        self.path = Path(path)
        self.budget, self.max_line = budget, max_line
        self.identity = None
        self.cursor = self.offset = 0
        self.pending = b''
        self.dropping = False
        self.anchor = self.prefix = b''

    def _reset(self):
        self.cursor = self.offset = 0
        self.pending = self.anchor = self.prefix = b''
        self.dropping = False

    def read(self):
        batch = Batch()
        try:
            with os.fdopen(os.open(self.path, os.O_RDONLY | os.O_NONBLOCK), 'rb') as file:
                info = os.fstat(file.fileno())
                if not stat.S_ISREG(info.st_mode):
                    raise OSError('Transcript is not a regular file')
                identity = (info.st_dev, info.st_ino)
                changed = self.identity != identity or info.st_size < self.offset
                if not changed and self.anchor:
                    file.seek(self.offset-len(self.anchor))
                    changed = file.read(len(self.anchor)) != self.anchor
                file.seek(0)
                prefix = file.read(min(256, info.st_size))
                if self.prefix and prefix[:len(self.prefix)] != self.prefix:
                    changed = True
                if changed:
                    self._reset(); batch.reset = True
                self.prefix = prefix
                self.identity = identity
                file.seek(self.offset)
                data = file.read(self.budget)
                self.offset += len(data)
                # The anchor includes partial bytes so truncate/regrow is detected too.
                file.seek(max(0, self.offset-64))
                self.anchor = file.read(min(64, self.offset))
                batch.catching_up = self.offset < info.st_size
        except OSError as error:
            batch.reset = True
            batch.unavailable = str(error)
            self.identity = None; self._reset()
            return batch
        chunks = data.split(b'\n')
        for chunk in chunks[:-1]:
            if not self.dropping and len(self.pending)+len(chunk) <= self.max_line:
                try:
                    row = json.loads(self.pending+chunk)
                    if isinstance(row, dict):
                        batch.records.append(row)
                    else:
                        batch.discarded = True; batch.records.clear()
                except (ValueError, UnicodeError, RecursionError):
                    batch.discarded = True; batch.records.clear()
            else:
                batch.discarded = True; batch.records.clear()
            self.pending = b''; self.dropping = False
        tail = chunks[-1]
        if self.dropping or len(self.pending)+len(tail) > self.max_line:
            self.pending = b''; self.dropping = True
            batch.discarded = True; batch.records.clear()
        else:
            self.pending += tail
        # Cursor is the last complete line, distinct from the physical read offset.
        if len(chunks) > 1: self.cursor = self.offset-len(tail)
        batch.incomplete = bool(self.pending) or self.dropping
        return batch


def evidence_tail(path, *, limit=4*1024*1024):
    """Bounded complete records with byte references; partial/malformed data labelled."""
    import hashlib
    records=[];issues=[]
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):raise RuntimeError('Transcript must be regular')
        start=max(0,info.st_size-limit);stream.seek(start)
        if start:stream.readline();issues.append('bounded tail; older evidence omitted')
        offset=stream.tell();raw=stream.read(limit)
    incomplete=bool(raw and not raw.endswith(b'\n'))
    for line in raw.splitlines(keepends=True):
        ref='byte:'+str(offset)+':sha256:'+hashlib.sha256(line).hexdigest();offset+=len(line)
        if not line.endswith(b'\n'):continue
        try:
            row=json.loads(line)
            if not isinstance(row,dict):raise ValueError('non-object')
            records.append((row,ref))
        except (ValueError,UnicodeError,RecursionError):issues.append('malformed record at '+ref)
    return dict(records=records,incomplete=incomplete,issues=issues,digest=hashlib.sha256(raw).hexdigest(),
                start=start,identity=(info.st_dev,info.st_ino),size=info.st_size)
