"""Account presentation and actual curses keyboard routing in a small terminal."""
import curses
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import struct
import subprocess
import sys
import termios
import time
from types import SimpleNamespace
import unittest

from watchdog_app.picker import choose_conversation


def binding(account, index=0):
    return SimpleNamespace(kind='codex', account=str(account), pane=f'w:p{index}',
                           session=f'long-session-identity-{index}', terminal=f't{index}')


class Screen:
    def __init__(self, keys):
        self.keys = iter(keys)
        self.rows = {}

    def getmaxyx(self):
        return 14, 100

    def keypad(self, enabled):
        pass

    def erase(self):
        self.rows = {}

    def refresh(self):
        pass

    def addnstr(self, row, col, value, length, attr):
        self.rows[row] = value[:length]

    def getch(self):
        return next(self.keys)


class PickerAccountTests(unittest.TestCase):
    def rows(self, accounts):
        choices = [binding(account, i) for i, account in enumerate(accounts)]
        screen = Screen([10])
        self.assertIs(choose_conversation(screen, choices), choices[0])
        return [screen.rows[2 + i] for i in range(len(choices))]

    def test_default_and_custom_labels_precede_session(self):
        rows = self.rows([Path.home() / '.codex', Path.home() / '.claude',
                          '/profiles/Office', '/elsewhere/.codex'])
        for row, label in zip(rows, ['Default account', 'Default account', 'Office', '.codex']):
            self.assertIn(f' · {label} · long-session-', row)

    def test_same_basename_uses_enough_parent_path_and_duplicate_accounts_share_label(self):
        rows = self.rows(['/alpha/team/work', '/beta/team/work', '/alpha/team/work'])
        self.assertIn('alpha/team/work', rows[0])
        self.assertIn('beta/team/work', rows[1])
        self.assertIn('alpha/team/work', rows[2])

    def test_account_controls_are_rendered_as_spaces(self):
        row, = self.rows(['/profiles/Office\n\x1b\t\x07Name'])
        self.assertIn('Office    Name', row)
        self.assertTrue(all(char.isprintable() for char in row))

    def test_keyboard_selection_preserves_original_object_and_identities(self):
        choices = [binding('/profiles/one'), binding('/profiles/two', 1)]
        original = [vars(choice).copy() for choice in choices]
        self.assertIs(choose_conversation(Screen([curses.KEY_DOWN, 10]), choices), choices[1])
        self.assertEqual([vars(choice) for choice in choices], original)
        self.assertIsNone(choose_conversation(Screen([27]), choices))


PTY_SCRIPT = r'''
import curses, json, sys
from types import SimpleNamespace
from watchdog_app.picker import choose_conversation
choices = [SimpleNamespace(kind='codex', pane='w:p'+str(i), account='/profiles/'+name,
           session='session-identity-too-long-for-narrow-pane-'+str(i))
           for i, name in enumerate(['Office', 'Personal'])]
result = curses.wrapper(choose_conversation, choices)
print('RESULT:' + json.dumps({'index': next((i for i, b in enumerate(choices) if b is result), None),
                             'session': result.session if result is not None else None}), flush=True)
'''


class PickerTerminalTests(unittest.TestCase):
    def run_picker(self, keys, expected):
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 14, 42, 0, 0))
        process = subprocess.Popen([sys.executable, '-B', '-c', PTY_SCRIPT],
                                   stdin=slave, stdout=slave, stderr=slave,
                                   env=dict(os.environ, TERM='xterm-256color', ESCDELAY='25'))
        os.close(slave)
        output = b''

        def read_until(token):
            nonlocal output
            deadline = time.monotonic() + 5
            while token not in output and time.monotonic() < deadline:
                if select.select([master], [], [], .1)[0]:
                    try:
                        data = os.read(master, 65536)
                    except OSError:
                        break
                    if not data:
                        break
                    output += data
            self.assertIn(token, output, output.decode(errors='replace'))

        try:
            read_until(b'Personal')
            self.assertIn(b'Office', output)
            os.write(master, keys)
            read_until(b'RESULT:')
            self.assertEqual(process.wait(timeout=5), 0)
            result = json.loads(output.split(b'RESULT:', 1)[1].splitlines()[0])
            self.assertEqual(result, expected)
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()
            os.close(master)

    def test_real_arrow_selection_in_narrow_terminal(self):
        self.run_picker(b'\x1bOB\r', {'index': 1, 'session': 'session-identity-too-long-for-narrow-pane-1'})

    def test_real_escape_cancels(self):
        self.run_picker(b'\x1b', {'index': None, 'session': None})
