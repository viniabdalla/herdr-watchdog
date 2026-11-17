"""Run contracts: durable intent, exact recipients and evidence-gated progress."""
import copy
from dataclasses import asdict
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import test_actions
from watchdog_app import mission
from watchdog_app.todo import Snapshot


class RequestTests(unittest.TestCase):
    setUp = test_actions.ActionTests.setUp
    def test_confirmation_and_duplicate_request_keep_todo_open(self):
        snapshot = Snapshot.read(self.repo)
        ids = {snapshot.tasks[0].id}
        with self.assertRaisesRegex(RuntimeError, 'confirm'):
            mission.request(self.session, snapshot, ids, confirmed=False)
        self.assertFalse(self.delivered)
        run = mission.request(self.session, snapshot, ids, confirmed=True)
        self.assertEqual(run['main'], asdict(self.session.binding))
        self.assertEqual(len(self.delivered), 1)
        self.assertIn(run['id'], self.delivered[0][2])
        self.assertIn('explicit brief', self.delivered[0][2])
        self.assertEqual((self.repo / 'TODO.md').read_bytes(), snapshot.raw)
        with self.assertRaisesRegex(RuntimeError, 'already'):
            mission.request(self.session, snapshot, ids, confirmed=True)
        self.assertEqual(len(self.delivered), 1)

    def test_uncertain_queue_is_retained_and_never_retried(self):
        snapshot = Snapshot.read(self.repo)
        self.session.runtime.queue = lambda *args: (_ for _ in ()).throw(RuntimeError('timeout'))
        with self.assertRaisesRegex(RuntimeError, 'not confirmed'):
            mission.request(self.session, snapshot, {snapshot.tasks[0].id}, confirmed=True)
        run = mission.RunStore().list(self.repo)[0]
        self.assertEqual(run['request_delivery'], 'uncertain')
        with self.assertRaisesRegex(RuntimeError, 'already'):
            mission.request(self.session, snapshot, {snapshot.tasks[0].id}, confirmed=True)

    def test_changed_identity_and_stale_tasks_never_queue(self):
        snapshot = Snapshot.read(self.repo)
        self.identity_changed = True
        with self.assertRaises(RuntimeError):
            mission.request(self.session, snapshot, {snapshot.tasks[0].id}, confirmed=True)
        self.identity_changed = False
        (self.repo / 'TODO.md').write_text('## Next\n- [ ] Changed\n')
        with self.assertRaises(RuntimeError):
            mission.request(self.session, snapshot, {snapshot.tasks[0].id}, confirmed=True)
        self.assertFalse(self.delivered)


class StateTests(unittest.TestCase):
    def setUp(self):
        self.run = {'id': 'run', 'phase': 'active', 'tasks': {
            'task': {'title': 'Add controls', 'state': 'working', 'agent': 'worker',
                     'gossip_task': 'native-task', 'updated': 100, 'summary': ''}},
            'participants': {'worker': {'nickname': 'worker', 'pubkey': 'key'},
                             'qa': {'nickname': 'qa', 'pubkey': 'qa-key'}},
            'events': {}, 'candidate': None, 'qa': None}

    def event(self, status, **kw):
        report = {'run_id': 'run', 'task_id': 'task', 'status': status, 'summary': 'Concrete report', **kw}
        return {'id': 'event-'+status, 'event': 'task', 'kind': 'artifact' if status == 'result' else 'status-update',
                'task_id': 'native-task', 'author': 'worker', 'pubkey': 'key', 'body': json.dumps(report)}

    def test_blocker_requires_reason_and_followup_keeps_identity(self):
        event = self.event('blocked', summary='')
        with self.assertRaisesRegex(RuntimeError, 'summary'):
            mission.accept_event(self.run, event, now=110)
        event = self.event('blocked', summary='Need approval for new dependency')
        self.assertTrue(mission.accept_event(self.run, event, now=110))
        self.assertEqual(self.run['tasks']['task']['state'], 'blocked')
        self.assertFalse(mission.accept_event(self.run, event, now=120))
        self.assertEqual(self.run['tasks']['task']['gossip_task'], 'native-task')

    def test_result_waits_for_exact_qa_and_explicit_approval(self):
        mission.accept_event(self.run, self.event('result', commits=['a'*40], tests=['unittest: passed']), now=110)
        self.assertEqual(self.run['tasks']['task']['state'], 'review')
        with self.assertRaises(RuntimeError):
            mission.finish(self.run, 'a'*40, confirmed=True)
        self.run['candidate'] = 'a'*40
        self.run['qa'] = {'candidate': 'b'*40, 'verdict': 'pass', 'tests': ['suite passed']}
        with self.assertRaises(RuntimeError):mission.finish(self.run, 'a'*40, confirmed=True)
        self.run['qa']['candidate'] = 'a'*40
        with self.assertRaises(RuntimeError):mission.finish(self.run, 'a'*40, confirmed=False)
        mission.finish(self.run, 'a'*40, confirmed=True)
        self.assertEqual(self.run['tasks']['task']['state'], 'done')

    def test_foreign_task_or_peer_cannot_change_progress(self):
        for field, value in [('pubkey', 'foreign'), ('author', 'stranger'), ('task_id', 'other-task')]:
            event = self.event('working');event[field] = value
            before = copy.deepcopy(self.run)
            self.assertFalse(mission.accept_event(self.run, event, now=110))
            self.assertEqual(self.run, before)

    def test_lost_contact_is_unavailable_never_done(self):
        mission.contact(self.run, set(), now=500)
        self.assertEqual(mission.task_view(self.run, 'task', now=500)['label'], 'Unavailable')
        self.assertNotEqual(self.run['tasks']['task']['state'], 'done')
        mission.contact(self.run, {'key'}, now=510)
        self.assertEqual(mission.task_view(self.run, 'task', now=510)['label'], 'Working')

    def test_unstructured_completed_is_not_evidence_of_done(self):
        event = self.event('working');event.update(body='Done!', state='completed')
        with self.assertRaisesRegex(RuntimeError, 'structured'):
            mission.accept_event(self.run, event, now=110)
        self.assertEqual(self.run['tasks']['task']['state'], 'working')

    def test_new_work_invalidates_previous_acceptance_and_qa(self):
        self.run['tasks']['task']['accepted_result']=True
        self.run['qa']={'candidate':'a'*40,'verdict':'pass','tests':['passed']}
        mission.accept_event(self.run,self.event('working'),now=110)
        self.assertFalse(self.run['tasks']['task'].get('accepted_result'))
        self.assertIsNone(self.run['qa'])
