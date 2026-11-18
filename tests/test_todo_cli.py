from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from watchdog_app.app import main
from test_todo_migrate import LEGACY


class TodoCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.todo = self.repo / 'TODO.md'
        self.todo.write_text(LEGACY)
        self.proposal = self.repo / 'proposal.json'

    def cli(self, action, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(['todo', action, '--repo', str(self.repo),
                         '--state-dir', str(self.repo / 'state'), *args])
        return code, out.getvalue(), err.getvalue()

    def test_validate_and_preview_render_apply_end_to_end(self):
        code, out, err = self.cli('validate')
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)['format_version'], 0)
        code, out, err = self.cli('preview')
        self.assertEqual(code, 0, err)
        proposal = json.loads(out)
        self.proposal.write_text(json.dumps(proposal))
        before = self.todo.read_bytes()
        code, markdown, err = self.cli('render', '--proposal', str(self.proposal))
        self.assertEqual(code, 0, err)
        self.assertIn('watchdog_todo: 1', markdown)
        self.assertEqual(self.todo.read_bytes(), before)
        self.assertEqual(self.cli('apply', '--proposal', str(self.proposal))[0], 1)
        self.assertEqual(self.todo.read_bytes(), before)
        code, out, err = self.cli('apply', '--proposal', str(self.proposal), '--confirm')
        self.assertEqual(code, 0, err)
        result = json.loads(out)
        self.assertEqual(result['format_version'], 1)
        self.assertEqual(result['historical'], 1)
        self.assertEqual(self.todo.read_text(), markdown)
        self.assertEqual(self.cli('validate')[0], 0)

    def test_invalid_file_or_proposal_is_clear_error_with_no_traceback(self):
        for text in ('not json', '[]', '{"version": true}'):
            self.proposal.write_text(text)
            code, out, err = self.cli('apply', '--proposal', str(self.proposal), '--confirm')
            self.assertEqual(code, 1)
            self.assertIn('Watchdog:', err)
            self.assertNotIn('Traceback', err)
        self.todo.write_text('---\nwatchdog_todo: 99\n---\n')
        self.assertEqual(self.cli('validate')[0], 1)
