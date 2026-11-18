"""Approval integrates the QA-passed candidate into the project branch and pushes it."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from watchdog_app.mission_merge import integrate, summary


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), '-c', 'user.name=t', '-c', 'user.email=t@t', *args],
                          check=True, capture_output=True, text=True).stdout.strip()


class MergeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        root = Path(tmp.name);self.remote = root / 'remote.git';self.repo = root / 'repo'
        subprocess.run(['git', 'init', '-q', '--bare', '-b', 'main', str(self.remote)], check=True)
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(self.repo)], check=True)
        git(self.repo, 'config', 'user.name', 't');git(self.repo, 'config', 'user.email', 't@t')
        (self.repo / 'a.txt').write_text('a\n');git(self.repo, 'add', '.');git(self.repo, 'commit', '-qm', 'base')
        git(self.repo, 'remote', 'add', 'origin', str(self.remote));git(self.repo, 'push', '-qu', 'origin', 'main')
        self.base = git(self.repo, 'rev-parse', 'HEAD')
        self.run_ = {'id': 'abcdef12-run', 'repo': str(self.repo), 'tasks': {'t': {'title': 'Do the thing'}}}

    def worker(self, name='w.txt', text='work\n'):
        git(self.repo, 'checkout', '-qb', 'worker-' + name, self.base)
        (self.repo / name).write_text(text);git(self.repo, 'add', '.');git(self.repo, 'commit', '-qm', 'work')
        sha = git(self.repo, 'rev-parse', 'HEAD');git(self.repo, 'checkout', '-q', 'main')
        return sha

    def test_fast_forward_and_push_keep_user_uncommitted_files(self):
        sha = self.worker();(self.repo / 'mine.txt').write_text('user draft\n')
        result = integrate(self.run_, sha)
        self.assertEqual(result['how'], 'fast-forward');self.assertTrue(result['pushed'])
        self.assertEqual(git(self.remote, 'rev-parse', 'main'), sha);self.assertEqual((self.repo / 'mine.txt').read_text(), 'user draft\n')
        self.assertIn('pushed to origin/main', summary(result))
        self.assertEqual(integrate(self.run_, sha)['how'], 'already')

    def test_main_moved_on_gets_a_merge_commit_naming_the_run(self):
        sha = self.worker();(self.repo / 'b.txt').write_text('b\n');git(self.repo, 'add', '.');git(self.repo, 'commit', '-qm', 'other')
        result = integrate(self.run_, sha)
        self.assertEqual(result['how'], 'merge');self.assertTrue(result['pushed'])
        self.assertIn('Do the thing', git(self.repo, 'log', '-1', '--format=%B'))
        self.assertEqual(git(self.repo, 'merge-base', '--is-ancestor', sha, 'HEAD'), '')

    def test_conflict_aborts_cleanly_and_says_what_to_do(self):
        sha = self.worker('a.txt', 'worker\n')
        (self.repo / 'a.txt').write_text('main\n');git(self.repo, 'commit', '-qam', 'main edit');head = git(self.repo, 'rev-parse', 'HEAD')
        with self.assertRaisesRegex(RuntimeError, 'conflicts with main in: a.txt.*rebase'):
            integrate(self.run_, sha)
        self.assertEqual(git(self.repo, 'rev-parse', 'HEAD'), head);self.assertEqual(git(self.repo, 'status', '--porcelain'), '')

    def test_no_upstream_merges_locally_and_says_so(self):
        git(self.repo, 'branch', '--unset-upstream');sha = self.worker()
        result = integrate(self.run_, sha)
        self.assertFalse(result['pushed']);self.assertIn('no upstream', summary(result))


if __name__ == '__main__':
    unittest.main()
