"""Serialize a complete prompt through Enter across panels and executors."""
from contextlib import contextmanager
import fcntl
import hashlib
import os
from pathlib import Path

from .herdr import Herdr


@contextmanager
def pane_lock(pane, session=None):
    # Deliberately independent of project/worktree/WATCHDOG_STATE_DIR: all
    # Watchdog writers targeting this Herdr pane must share the same lease.
    root = Path(os.environ.get('XDG_STATE_HOME', str(Path.home()/'.local/state')))/'herdr-watchdog/pane-locks'
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    endpoint = (str(Path.home()/'.config/herdr/sessions'/session/'herdr.sock') if session else
                os.environ.get('HERDR_SOCKET_PATH', str(Path.home()/'.config/herdr/herdr.sock')))
    key = hashlib.sha256((endpoint+'\0'+pane).encode()).hexdigest()
    with (root/(key+'.lock')).open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def send(pane, text, *, api=None, enter='Enter'):
    api = api or Herdr()
    with pane_lock(pane, api.session):
        try:
            api.call('pane', 'send-text', pane, text)
            api.call('pane', 'send-keys', pane, enter)
        except (RuntimeError, OSError, ValueError) as error:
            raise RuntimeError('Envio não confirmado ao pane ' + pane +
                               '; confira antes de repetir; nada foi reenviado automaticamente: ' + str(error)) from error
