"""Real PTY kernel modes must survive a child leaving raw mode on exit."""
import os
import pty
import termios
import tty
import unittest
from watchdog_app.mission_terminal import TerminalLease


class TerminalTests(unittest.TestCase):
    def test_restores_kernel_modes_and_disables_mouse_after_failure(self):
        master,slave=pty.openpty()
        self.addCleanup(os.close,master);self.addCleanup(os.close,slave)
        before=termios.tcgetattr(slave)
        lease=TerminalLease(slave)
        tty.setraw(slave)
        self.assertNotEqual(termios.tcgetattr(slave),before)
        lease.restore()
        self.assertEqual(termios.tcgetattr(slave),before)
        emitted=os.read(master,4096)
        for mode in (1000,1002,1003,1006,1015,1004):
            self.assertIn(('\x1b[?%dl'%mode).encode(),emitted)

    def test_non_terminal_output_is_not_modified(self):
        read,write=os.pipe()
        self.addCleanup(os.close,read);self.addCleanup(os.close,write)
        lease=TerminalLease(write);lease.restore()
        os.set_blocking(read,False)
        with self.assertRaises(BlockingIOError):os.read(read,1)
