"""Small OS boundaries used by the Codex/Tasks path."""
import errno
import os
import shlex
import time

_windows = os.name == 'nt'
if _windows:
    import msvcrt as _msvcrt
    LOCK_SH, LOCK_EX, LOCK_NB, LOCK_UN = 1, 2, 4, 8
else:
    import fcntl as _unix
    LOCK_SH, LOCK_EX, LOCK_NB, LOCK_UN = (_unix.LOCK_SH, _unix.LOCK_EX, _unix.LOCK_NB, _unix.LOCK_UN)
    _msvcrt = None


def flock(file, operation):
    if not _windows:
        return _unix.flock(file, operation)
    fd = file if isinstance(file,int) else file.fileno()
    # Lock byte zero even for append streams; all clients share the same range.
    os.lseek(fd,0,os.SEEK_SET)
    mode = _msvcrt.LK_UNLCK if operation & LOCK_UN else (
        _msvcrt.LK_NBLCK if operation & LOCK_EX else _msvcrt.LK_NBRLCK)
    while True:
        try:
            return _msvcrt.locking(fd,mode,1)
        except OSError as error:
            if error.errno not in (errno.EACCES,errno.EAGAIN,errno.EDEADLK):
                raise
            if operation & LOCK_NB:
                raise BlockingIOError(error.errno,str(error)) from error
            time.sleep(.05)


# Import-compatible with existing callers; Unix keeps native flock semantics.
import sys
fcntl = sys.modules[__name__]


def fsync_directory(directory):
    if _windows:
        return
    fd = os.open(directory,os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def shell_command(argv, *, windows=None):
    if windows if windows is not None else _windows:
        # PowerShell call operator; single quotes avoid interpolation.
        return '& ' + ' '.join('"'+str(arg).replace('`','``').replace('$','`$').replace('"','`"')+'"' for arg in argv)
    return shlex.join([str(arg) for arg in argv])
