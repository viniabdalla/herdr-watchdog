import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from watchdog_app import project_history as ph
from watchdog_app.todo import Snapshot, change, replace
from watchdog_app.todo_format import render
ID='9f4cdfb9-3b30-4d69-a178-aa3ff61301a6'
class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.repo=Path(self.tmp.name)
        self.root=self.repo/'state';env=patch.dict(os.environ,{'WATCHDOG_STATE_DIR':str(self.root)});env.start();self.addCleanup(env.stop)
        self.raw=('---\nwatchdog_todo: 1\n---\n## Next\n'+render('Work',dict(id=ID,summary='Simple',origin='pedido-humano',execution='Details',acceptance='Checks'))).encode()
        (self.repo/'TODO.md').write_bytes(self.raw)
    def test_complete_reopen_correct_remove_and_readd_preserve_history(self):
        snap=Snapshot.read(self.repo);ph.observe(snap)
        done=change(snap,[dict(kind='done',id=ID,evidence='tests passed')])
        events=ph.read(self.repo)['events'];self.assertEqual(events[-1]['to'],'Done')
        self.assertEqual(events[-1]['evidence'],'tests passed');self.assertIn('observed_at',events[-1])
        reopened=change(done,[dict(kind='reopen',id=ID,evidence='regression')])
        self.assertEqual(reopened.tasks[0].section,'Next')
        removed=replace(reopened,b'---\nwatchdog_todo: 1\n---\n## Next\n')
        self.assertEqual(ph.read(self.repo)['events'][-1]['to'],'absent')
        replace(removed,self.raw)
        events=ph.read(self.repo)['events'];self.assertEqual(events[-1]['from'],'absent')
        self.assertEqual(sum(e['to']=='Done' for e in events),1)
        self.assertEqual(events[-1]['id'],ID)
    def test_external_edits_are_observed_without_backdating(self):
        ph.observe(Snapshot.read(self.repo));(self.repo/'TODO.md').write_bytes(self.raw.replace(b'## Next',b'## Done').replace(b'[ ]',b'[x]'))
        ph.observe(Snapshot.read(self.repo));events=ph.read(self.repo)['events']
        self.assertEqual(events[-1]['to'],'Done');self.assertEqual(events[-1]['evidence'],'external observation; verification not established')
    def test_concurrent_observations_are_idempotent(self):
        snap=Snapshot.read(self.repo)
        with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(lambda _:ph.observe(snap),range(12)))
        self.assertEqual(len(ph.read(self.repo)['events']),1)
    def test_history_failure_before_save_preserves_todo(self):
        snap=Snapshot.read(self.repo)
        with patch('watchdog_app.project_history.prepare',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):change(snap,[dict(kind='done',id=ID)])
        self.assertEqual((self.repo/'TODO.md').read_bytes(),self.raw)
    def test_failure_after_save_recovers_once_on_restart(self):
        snap=Snapshot.read(self.repo)
        with patch('watchdog_app.project_history.finish',side_effect=OSError('disk full')):
            with self.assertRaisesRegex(RuntimeError,'history'):change(snap,[dict(kind='done',id=ID,evidence='verified')])
        self.assertTrue(Snapshot.read(self.repo).tasks[0].done)
        ph.observe(Snapshot.read(self.repo));ph.observe(Snapshot.read(self.repo))
        self.assertEqual(sum(e['to']=='Done' for e in ph.read(self.repo)['events']),1)
        self.assertIsNone(ph.read(self.repo)['pending'])

    def test_pending_intent_and_unrelated_editor_version_is_visible_conflict(self):
        snap=Snapshot.read(self.repo)
        with patch('watchdog_app.project_history.finish',side_effect=OSError('unavailable')):
            with self.assertRaises(RuntimeError):change(snap,[dict(kind='done',id=ID)])
        # Use a valid external save, outside task indentation, for a third digest.
        (self.repo/'TODO.md').write_bytes(b'---\nwatchdog_todo: 1\n---\n## Next\n')
        with self.assertRaisesRegex(RuntimeError,'recovery conflict'):ph.observe(Snapshot.read(self.repo))
        self.assertIsNotNone(ph.read(self.repo)['pending'])
