"""Native Herdr commands. Mutations are never retried after an uncertain result."""
import json
import os
from pathlib import Path
import socket
import subprocess
import uuid


class Herdr:
    def __init__(self, session=None):
        self.prefix = [os.environ.get('HERDR_BIN_PATH', 'herdr')]
        self.session = session
        if session:
            self.prefix += ['--session', session]

    def output(self, *args):
        """Raw output, including ANSI snapshots used to inspect the composer."""
        try:
            result = subprocess.run(self.prefix + list(args), capture_output=True,
                                    text=True, timeout=20)
        except subprocess.TimeoutExpired as error:
            raise RuntimeError('Herdr request timed out; inspect the panes before retrying') from error
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or 'Herdr command failed')
        return result.stdout

    def call(self, *args):
        output = self.output(*args)
        if not output.strip():
            return {}
        value = json.loads(output)
        if 'error' in value:
            raise RuntimeError(str(value['error']))
        return value['result']

    def checked(self, pane):
        live = self.call('pane', 'get', pane['pane_id'])['pane']
        if live['terminal_id'] != pane['terminal_id']:
            raise RuntimeError('Pane terminal changed; refusing to rearrange it')
        return live

    def panel(self, pane, repo):
        """A Watchdog panel record, refreshed when Herdr restored it after a restart.

        A restart keeps pane ids but issues new terminal ids. The same pane id in
        the same tab, still inside this project folder, is the restored panel;
        anything else is treated as replaced and refused.
        """
        live = self.call('pane', 'get', pane['pane_id'])['pane']
        if live['terminal_id'] == pane['terminal_id']:
            return pane
        root = Path(repo).resolve()
        inside = any(value and Path(value).resolve().is_relative_to(root)
                     for value in (live.get('cwd'), live.get('foreground_cwd')))
        if live.get('tab_id') != pane.get('tab_id') or not inside:
            raise RuntimeError('Panel ' + pane['pane_id'] + ' was replaced by another terminal; reopen Watchdog panels')
        return dict(pane, terminal_id=live['terminal_id'], restored_from=pane['terminal_id'])

    def request(self, method, params):
        """Typed native methods without a direct CLI equivalent (e.g. pane.focus)."""
        if self.session:
            path = Path.home() / '.config/herdr/sessions' / self.session / 'herdr.sock'
        else:
            path = Path(os.environ.get('HERDR_SOCKET_PATH', str(Path.home() / '.config/herdr/herdr.sock')))
        with socket.socket(socket.AF_UNIX) as connection:
            connection.settimeout(10)
            connection.connect(str(path))
            connection.sendall((json.dumps({'id': str(uuid.uuid4()), 'method': method,
                                           'params': params}) + '\n').encode())
            with connection.makefile() as stream:
                value = json.loads(stream.readline())
        if 'error' in value:
            raise RuntimeError(str(value['error']))
        return value['result']

    def export(self, tab):
        return self.request('layout.export', {'tab_id': tab})['layout']
