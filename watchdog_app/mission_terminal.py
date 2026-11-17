"""Restore the owned terminal even when a Codex child exits without TUI cleanup."""
import os
import termios


RESET=b'\x1b[?9l\x1b[?1000l\x1b[?1002l\x1b[?1003l\x1b[?1006l' \
      b'\x1b[?1015l\x1b[?1016l\x1b[?1004l\x1b[?2004l' \
      b'\x1b[<u\x1b[=0u\x1b[>4;0m\x1b[?1049l\x1b[?25h\x1b[0m'


class TerminalLease:
    def __init__(self, fd):
        self.fd=fd
        self.attributes=termios.tcgetattr(fd) if os.isatty(fd) else None

    def restore(self):
        if self.attributes is None:
            return
        termios.tcsetattr(self.fd,termios.TCSANOW,self.attributes)
        os.write(self.fd,RESET)


def reset_owned_shell(api,pane):
    """Output mode resets through the verified slave, never as shell input."""
    from pathlib import Path
    import subprocess
    api.checked(pane)
    info=api.call('pane','process-info','--pane',pane['pane_id'])['process_info']
    if any(p['pid']!=info['shell_pid'] for p in info['foreground_processes']):
        raise RuntimeError('Owned shell is busy; terminal was not modified')
    fdpath=Path('/proc')/str(info['shell_pid'])/'fd/1'
    tty_path=fdpath.resolve()
    if not str(tty_path).startswith('/dev/pts/'):
        raise RuntimeError('Owned shell terminal is unavailable')
    fd=os.open(fdpath,os.O_WRONLY|os.O_NOCTTY)
    try:
        os.write(fd,b'\x1bc'+RESET)
        subprocess.run(['stty','-F',str(tty_path),'sane'],check=True,timeout=3,
                       capture_output=True)
        termios.tcflush(fd,termios.TCIFLUSH)
    finally:os.close(fd)
    api.call('pane','send-keys',pane['pane_id'],'ctrl+c')
    __import__('time').sleep(.15)
