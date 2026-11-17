"""Real-terminal regression: Artifacts reveals a file in its linked Yazi."""
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import pty
import select
import signal
import shutil
import struct
import subprocess
import tempfile
import termios
import time
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'tools/watchdog-preview.py'


class Terminal:
    def __init__(self, argv, env):
        self.master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 30, 120, 0, 0))
        self.process = subprocess.Popen(argv, stdin=slave, stdout=slave,
                                        stderr=slave, env=env, start_new_session=True)
        os.close(slave)
        self.output = b''

    def wait_for(self, text, timeout=10):
        until = time.monotonic() + timeout
        while text.encode() not in self.output and time.monotonic() < until:
            if select.select([self.master], [], [], .1)[0]:
                try:
                    self.output += os.read(self.master, 65536)
                except OSError:
                    break
            if self.process.poll() is not None:
                break
        return text.encode() in self.output

    def close(self):
        if self.master is None:
            return
        if self.process.poll() is None:
            os.killpg(self.process.pid, signal.SIGTERM)
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait()
        os.close(self.master)
        self.master = None


@unittest.skipUnless(shutil.which('yazi') and shutil.which('ya'), 'requires Yazi and ya')
class ArtifactLinkTests(unittest.TestCase):
    def test_missing_and_broadcast_receivers_are_rejected(self):
        spec = importlib.util.spec_from_file_location('preview', SCRIPT)
        preview = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(preview)
        for receiver in (None, '', '0', '-1', 'not-an-id', str(2**64)):
            with self.subTest(receiver=receiver), self.assertRaises(ValueError):
                preview.browse(Path('/tmp/example'), receiver)

    def test_enter_reveals_in_linked_yazi_without_replacing_artifacts(self):
        self.check_link(b'jj\r')

    def test_click_reveals_in_linked_yazi_without_replacing_artifacts(self):
        # SGR mouse: press/release on the first artifact row (terminal row 6).
        self.check_link(b'\x1b[<0;1;6M\x1b[<0;1;6m')

    def check_link(self, activation):
        # A regression to opening a local Yazi loses the Artifacts display and
        # never emits a hover event from the linked Yazi instance.
        with tempfile.TemporaryDirectory(prefix='wd-artifact-link-') as folder:
            repo = Path(folder)
            (repo / 'docs').mkdir()
            target = repo / 'a file with spaces.txt'
            target.write_text('Linked artifact preview\n')
            (repo / 'docs/preview-artifacts.json').write_text(json.dumps([
                {'path': target.name, 'agent': 'Test', 'summary': 'Test artifact'}]))
            empty = repo / 'empty'
            empty.mkdir()
            client = str(time.time_ns())
            env = dict(os.environ, TERM='xterm-256color',
                       YAZI_CONFIG_HOME=str(repo / 'config'),
                       XDG_STATE_HOME=str(repo / 'state'),
                       XDG_CACHE_HOME=str(repo / 'cache'))
            browser = Terminal(['yazi', '--client-id', client,
                                '--local-events', 'hover', str(empty)], env)
            self.addCleanup(browser.close)
            self.assertTrue(browser.wait_for('empty'), browser.output.decode(errors='replace'))
            panel = Terminal(['python3', str(SCRIPT), 'artifacts', '--repo', str(repo),
                              '--yazi-client-id', client], env)
            self.addCleanup(panel.close)
            self.assertTrue(panel.wait_for('WATCHDOG MVP'), panel.output.decode(errors='replace'))
            os.write(panel.master, activation)
            self.assertTrue(browser.wait_for(str(target)), browser.output.decode(errors='replace'))
            self.assertIsNone(panel.process.poll())
            os.write(panel.master, b'q')
            self.assertEqual(panel.process.wait(timeout=3), 0,
                             'q should exit Artifacts directly, without a nested Yazi')


if __name__ == '__main__':
    unittest.main()
