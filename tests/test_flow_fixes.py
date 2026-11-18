"""Regressions for the 2026-11-17 flow fixes: checkpoint, forgotten runs, live TODO edits."""
import subprocess
import time
import unittest

import test_actions
from watchdog_app import checkpoint, mission
from watchdog_app.tasks_ui import remap
from watchdog_app.todo import Snapshot


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True, text=True).stdout


class CheckpointTests(unittest.TestCase):
    setUp = test_actions.ActionTests.setUp

    def init(self):
        git(self.repo, 'init', '-q')
        git(self.repo, '-c', 'user.name=t', '-c', 'user.email=t@t', 'add', '-A')
        git(self.repo, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'base')
        git(self.repo, 'config', 'user.name', 't');git(self.repo, 'config', 'user.email', 't@t')

    def test_lists_exact_changes_and_commits_only_the_confirmed_list(self):
        self.init()
        (self.repo / 'TODO.md').write_text((self.repo / 'TODO.md').read_text() + '- [ ] New idea\n')
        (self.repo / 'pkg').mkdir();(self.repo / 'pkg' / 'new.py').write_text('x = 1\n')
        changes = checkpoint.pending(self.repo)
        self.assertEqual(checkpoint.describe(changes), ['Modified: TODO.md', 'New: pkg/new.py'])
        saved = checkpoint.commit(self.repo, changes, 'checkpoint')
        self.assertTrue(saved['created']);self.assertEqual(checkpoint.pending(self.repo), [])
        self.assertEqual(git(self.repo, 'rev-parse', 'HEAD').strip(), saved['sha'])

    def test_changes_after_confirmation_are_refused_without_commit(self):
        self.init()
        (self.repo / 'a.txt').write_text('a')
        changes = checkpoint.pending(self.repo)
        (self.repo / 'b.txt').write_text('b')
        head = git(self.repo, 'rev-parse', 'HEAD')
        with self.assertRaisesRegex(RuntimeError, 'review the checkpoint again'):
            checkpoint.commit(self.repo, changes, 'checkpoint')
        self.assertEqual(git(self.repo, 'rev-parse', 'HEAD'), head)

    def test_clean_repo_and_non_repo(self):
        self.assertIsNone(checkpoint.pending(self.repo))
        self.init()
        self.assertEqual(checkpoint.commit(self.repo, [], 'x')['created'], False)


class ForgottenRunTests(unittest.TestCase):
    setUp = test_actions.ActionTests.setUp

    def first(self):
        snapshot = Snapshot.read(self.repo)
        return snapshot, {snapshot.tasks[0].id}

    def test_stalled_overlapping_run_is_closed_and_new_run_starts(self):
        snapshot, ids = self.first()
        old = mission.request(self.session, snapshot, ids, confirmed=True)
        store = mission.RunStore();run = store.load(old['id'])
        run['created'] = time.time() - mission.STALL_SECONDS - 60
        for task in run['tasks'].values():task['updated'] = run['created']
        store.save(run)
        self.assertEqual(mission.run_status(run)['label'], 'Stalled')
        new = mission.request(self.session, snapshot, ids, confirmed=True)
        closed = store.load(old['id'])
        self.assertEqual(closed['phase'], 'closed');self.assertIn('stalled', closed['closed']['reason'])
        self.assertNotEqual(new['id'], old['id'])

    def test_live_run_still_blocks_with_a_path_forward(self):
        snapshot, ids = self.first()
        mission.request(self.session, snapshot, ids, confirmed=True)
        with self.assertRaisesRegex(RuntimeError, 'already have a running team .*Progress.*x'):
            mission.request(self.session, snapshot, ids, confirmed=True)

    def test_run_accepted_in_todo_never_blocks(self):
        snapshot, ids = self.first()
        old = mission.request(self.session, snapshot, ids, confirmed=True)
        title = snapshot.tasks[0].text
        text = (self.repo / 'TODO.md').read_text().replace('- [ ] ' + title, '- [x] ' + title)
        text = text.replace('## Next\n', '## Next\n- [ ] ' + title + '\n', 1)  # Same text reopened.
        (self.repo / 'TODO.md').write_text(text)
        snapshot = Snapshot.read(self.repo)
        self.assertTrue(mission.accepted_in_todo(old, snapshot))
        reopened = next(t.id for t in snapshot.tasks if not t.done)
        mission.request(self.session, snapshot, {reopened}, confirmed=True)
        self.assertEqual(mission.RunStore().load(old['id'])['phase'], 'closed')

    def test_status_labels_follow_real_state(self):
        now = time.time()
        run = {'phase': 'requested', 'request_delivery': 'sent', 'created': now,
               'tasks': {'t': {'state': 'ready', 'updated': now, 'title': 'T', 'summary': ''}}}
        self.assertEqual(mission.run_status(run)['label'], 'Preparing')
        run.update(phase='active', monitor_pid=None)
        run['tasks']['t']['state'] = 'working'
        self.assertEqual(mission.run_status(run)['label'], 'Running')
        run['tasks']['t']['state'] = 'review'
        self.assertEqual(mission.run_status(run)['label'], 'Verifying')
        run.update(qa={'verdict': 'pass'}, qa_finished=True, candidate='a' * 40)
        self.assertEqual(mission.run_status(run)['label'], 'Waiting for approval')
        run['tasks']['t']['state'] = 'blocked'
        self.assertEqual(mission.run_status(run)['label'], 'Needs your decision')
        run['phase'] = 'done'
        self.assertTrue(mission.run_status(run)['finished'])


class LiveTodoTests(unittest.TestCase):
    setUp = test_actions.ActionTests.setUp

    def test_selection_survives_unrelated_edits_but_not_selected_edits(self):
        old = Snapshot.read(self.repo);chosen = {old.tasks[0].id}
        text = (self.repo / 'TODO.md').read_text()
        (self.repo / 'TODO.md').write_text(text.replace('## Next\n', '## Next\n- [ ] Fresh idea\n', 1))
        new = Snapshot.read(self.repo)
        kept = remap(old, new, chosen)
        self.assertEqual([t.text for t in new.selected(kept)], [old.tasks[0].text])
        (self.repo / 'TODO.md').write_text(text.replace(old.tasks[0].text, old.tasks[0].text + ' (edited)'))
        self.assertIsNone(remap(old, Snapshot.read(self.repo), chosen))


if __name__ == '__main__':
    unittest.main()
