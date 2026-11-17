from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from watchdog_app.actions import Session, Busy
from watchdog_app.todo import Snapshot


@dataclass
class FakeBinding:
    kind: str = 'codex'
    session: str = 'current-session'
    account: str = '/test/account'
    pane: str = 'project:p4'
    terminal: str = 'terminal'
    workspace: str = 'project'
    history: str = '/test/transcript'
    pid: int = 123
    started: str = '456'


class NativeBusy(RuntimeError):
    pass


class ActionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.env = patch.dict(os.environ, {'WATCHDOG_STATE_DIR': str(self.repo / 'state')})
        self.env.start();self.addCleanup(self.env.stop)
        (self.repo / 'TODO.md').write_text('## Next\n- [ ] Add task controls\n## Done\n- [x] Old work\n')
        self.file = self.repo / 'binding.json'
        self.file.write_text(json.dumps({'repo': str(self.repo), 'binding': asdict(FakeBinding())}))
        self.delivered = []
        self.busy = False
        self.identity_changed = False
        def verify(binding, **kwargs):
            if self.identity_changed:raise RuntimeError('identity changed')
            return {'agent_status': 'working' if self.busy else 'idle'}
        def send(binding, text):
            verify(binding)
            if self.busy:raise NativeBusy('working')
            self.delivered.append(('send', binding.session, text))
        def queue(binding, text):
            verify(binding);self.delivered.append(('queue', binding.session, text))
        engine = SimpleNamespace(Binding=FakeBinding, verify=verify, send=send, queue=queue,
                                 AgentBusy=NativeBusy)
        self.addCleanup(patch.stopall)
        patch('watchdog_app.actions.bindings.engine', return_value=engine).start()
        patch('watchdog_app.actions.bindings.project_for', return_value=self.repo).start()
        self.session = Session(self.file, self.repo)

    def test_send_uses_verified_recipient_and_does_not_complete_tasks(self):
        snapshot = Snapshot.read(self.repo)
        self.session.dispatch(snapshot, {snapshot.tasks[0].id})
        self.assertEqual(self.delivered[0][:2], ('queue', 'current-session'))
        self.assertIn('Add task controls', self.delivered[0][2])
        self.assertEqual((self.repo / 'TODO.md').read_bytes(), snapshot.raw)

    def test_identity_or_document_change_blocks_delivery(self):
        snapshot = Snapshot.read(self.repo)
        self.identity_changed = True
        with self.assertRaises(RuntimeError):self.session.dispatch(snapshot, {snapshot.tasks[0].id})
        self.identity_changed = False
        (self.repo / 'TODO.md').write_text('## Next\n- [ ] Replacement\n')
        with self.assertRaises(RuntimeError):self.session.dispatch(snapshot, {snapshot.tasks[0].id})
        self.assertEqual(self.delivered, [])

    def test_busy_requires_separate_explicit_queue_action(self):
        snapshot = Snapshot.read(self.repo);self.busy = True
        with self.assertRaises(Busy):self.session.dispatch(snapshot, {snapshot.tasks[0].id})
        self.assertEqual(self.delivered, [])
        self.session.dispatch(snapshot, {snapshot.tasks[0].id}, queued=True)
        self.assertEqual(self.delivered[0][:2], ('queue', 'current-session'))

    def test_completed_task_cannot_be_sent(self):
        snapshot = Snapshot.read(self.repo)
        with self.assertRaises(RuntimeError):self.session.dispatch(snapshot, {snapshot.tasks[1].id})
        self.assertEqual(self.delivered, [])

    def test_project_association_change_blocks_delivery(self):
        snapshot = Snapshot.read(self.repo)
        with patch('watchdog_app.actions.bindings.project_for', return_value=Path('/other/project')):
            with self.assertRaisesRegex(RuntimeError, 'project'):
                self.session.dispatch(snapshot, {snapshot.tasks[0].id})
        self.assertEqual(self.delivered, [])

    def test_recipient_switch_cannot_redirect_a_send_to_the_new_session(self):
        snapshot = Snapshot.read(self.repo)
        def pane_race(binding, text):
            self.delivered.append(('wrong-pane-recipient', 'replacement-session', text))
        self.session.runtime.send = pane_race
        self.session.dispatch(snapshot, {snapshot.tasks[0].id})
        self.assertEqual(self.delivered[0][:2], ('queue', 'current-session'))

    def test_transport_without_thread_identity_fails_closed(self):
        data=json.loads(self.file.read_text());data['binding']['kind']='claude'
        self.file.write_text(json.dumps(data))
        session=Session(self.file,self.repo);snapshot=Snapshot.read(self.repo)
        with self.assertRaisesRegex(RuntimeError, 'Claude'):
            session.dispatch(snapshot,{snapshot.tasks[0].id})
        self.assertEqual(self.delivered,[])
