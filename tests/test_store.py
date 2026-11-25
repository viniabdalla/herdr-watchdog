from dataclasses import dataclass
import json
from pathlib import Path
import tempfile
import unittest

from watchdog_app.store import Store


@dataclass
class Binding:
    pane: str = 'project:p4'
    terminal: str = 'conversation-terminal'
    session: str = 'verified-session'
    kind: str = 'codex'
    account: str = '/example/account'
    key: str = 'test-key'


class StoreTests(unittest.TestCase):
    def test_only_matching_preview_is_adopted(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            preview = {'repo': str(root), 'panes': {'tasks': {'pane_id': 'tasks'}},
                       'conversation': {'pane_id': 'wrong-pane', 'terminal_id': 'conversation-terminal'},
                       'yazi_client_id': '1234'}
            (root / 'preview.json').write_text(json.dumps(preview))
            store = Store(root)
            self.assertEqual(store.load(Binding(), root)['panes'], {})
            preview['conversation']['pane_id'] = 'project:p4'
            (root / 'preview.json').write_text(json.dumps(preview))
            state = store.load(Binding(), root)
            self.assertEqual(state['panes']['tasks']['pane_id'], 'tasks')
            self.assertEqual(state['yazi_client_id'], '1234')

    def test_successful_layout_preference_survives_new_session(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder))
            self.assertEqual(store.preference(), 2)
            store.remember(4)
            self.assertEqual(Store(Path(folder)).preference(), 4)

    def test_state_from_another_project_is_not_reused(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder))
            binding = Binding()
            state = store.load(binding, Path(folder))
            store.save(binding, state)
            with self.assertRaisesRegex(RuntimeError, 'project'):
                store.load(binding, Path('/another/project'))


class PanelTransferTests(unittest.TestCase):
    """Real Store redirects; native/Herdr boundaries explicitly simulated."""
    def setUp(self):
        import test_clean_sessions as fixtures
        from dataclasses import asdict
        import uuid
        self.fixtures=fixtures
        self.f=fixtures.CleanSessionsTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        f=self.f
        f.runtime.actors[f.new.session]=asdict(f.new)
        self.first=str(uuid.uuid4());self.second=str(uuid.uuid4())
        self.middle=Path(f.store.transfer(f.file,f.old,f.new,f.repo,self.first,api=f.api))
        from watchdog_app.actions import Session
        self.lagging_middle=Session(self.middle,f.repo)
        self.third=fixtures.Binding(session=str(uuid.uuid4()),account=f.new.account,
            history=str(f.root/'third.jsonl'),pane='project:third',terminal='third-terminal',pid=999,started='999')
        Path(self.third.history).touch();f.runtime.actors[self.third.session]=asdict(self.third)
        self.final=Path(f.store.transfer(self.middle,f.new,self.third,f.repo,self.second,api=f.api))

    def test_original_and_lagging_panels_reopen_after_two_transfers(self):
        from watchdog_app.actions import Session
        f=self.f
        self.assertEqual(Session.for_panel(f.file,f.repo).binding.session,self.third.session)
        self.assertEqual(f.session.successor_file(),self.final)
        self.assertEqual(self.lagging_middle.successor_file(),self.final)
        middle=json.loads(self.middle.read_text());last=json.loads(self.final.read_text())
        self.assertEqual(middle['transfer_operation'],self.first,'Incoming hop must remain immutable')
        self.assertEqual(middle['outgoing_transfer_operation'],self.second)
        self.assertEqual(last['transfer_operation'],self.second)
        self.assertNotIn('outgoing_transfer_operation',last)
        self.assertEqual(last['panes'],f.panes);self.assertEqual(last['layout'],2);self.assertEqual(last['yazi_client_id'],'keep-client')
        self.assertEqual(json.loads(f.file.read_text())['panes'],{});self.assertEqual(middle['panes'],{})

    def test_each_hop_rejects_tampered_operation_or_predecessor(self):
        from watchdog_app.actions import Session
        import uuid
        f=self.f;files=(f.file,self.middle,self.final);originals={p:p.read_bytes() for p in files}
        cases=((f.file,'outgoing_transfer_operation',str(uuid.uuid4())),
               (self.middle,'transfer_operation',str(uuid.uuid4())),
               (self.middle,'predecessor_binding',{}),
               (self.middle,'outgoing_transfer_operation',str(uuid.uuid4())),
               (self.final,'transfer_operation',str(uuid.uuid4())),
               (self.final,'predecessor_binding',{}))
        for file,key,value in cases:
            with self.subTest(file=file.name,key=key):
                for p,raw in originals.items():p.write_bytes(raw)
                data=json.loads(file.read_text());data[key]=value;file.write_text(json.dumps(data))
                with self.assertRaisesRegex(RuntimeError,'correlation'):Session.for_panel(f.file,f.repo)
                with self.assertRaisesRegex(RuntimeError,'correlation'):f.session.successor_file()

    def test_cross_project_and_symlink_targets_are_rejected(self):
        from watchdog_app.actions import Session
        f=self.f;data=json.loads(self.final.read_text());data['repo']=str(f.root/'foreign-project');self.final.write_text(json.dumps(data))
        with self.assertRaisesRegex(RuntimeError,'project'):Session.for_panel(f.file,f.repo)
        # The first pointer must reject symlinks even when they contain a valid hop.
        moved=self.middle.with_suffix('.saved');self.middle.rename(moved);self.middle.symlink_to(moved)
        with self.assertRaisesRegex(RuntimeError,'Watchdog state'):Session.for_panel(f.file,f.repo)
        with self.assertRaisesRegex(RuntimeError,'Watchdog state'):f.session.successor_file()

    def test_cycle_and_final_native_or_project_changes_are_rejected(self):
        from dataclasses import asdict
        from watchdog_app.actions import Session
        from watchdog_app import bindings
        from unittest.mock import patch
        f=self.f
        with patch.object(bindings,'project_for',side_effect=lambda b:f.root/'foreign' if b.session==self.third.session else f.repo):
            with self.assertRaisesRegex(RuntimeError,'project'):Session.for_panel(f.file,f.repo)
        f.runtime.actors[self.third.session]['started']='recycled'
        with self.assertRaisesRegex(RuntimeError,'identity'):Session.for_panel(f.file,f.repo)
        f.runtime.actors[self.third.session]=asdict(self.third)
        data=json.loads(self.final.read_text());data.update(ownership='released',successor_binding_file=str(self.final),
            outgoing_transfer_operation=data['transfer_operation'],predecessor_binding=asdict(self.third))
        self.final.write_text(json.dumps(data))
        with self.assertRaisesRegex(RuntimeError,'cyclic|too long'):Session.for_panel(self.final,f.repo)

    def test_retry_preserves_progressed_successor_and_refuses_new_owner(self):
        # #17 L34-35,48: partial persistence cannot overwrite a newer destination.
        from dataclasses import asdict
        from unittest.mock import patch
        from watchdog_app.store import atomic
        f=self.f
        # Start another transfer, then fail the source's final release write.
        next_binding=self.fixtures.Binding(session='retry-target',account=f.new.account,
            history=str(f.root/'retry.jsonl'),pane='project:retry',terminal='retry',pid=998,started='998')
        f.runtime.actors[next_binding.session]=asdict(next_binding)
        target=f.store.root/(next_binding.key+'.json')
        def fail_release(path,value):
            if Path(path)==self.final and value.get('ownership')=='released':raise OSError('disk failure')
            atomic(path,value)
        with patch('watchdog_app.store.atomic',side_effect=fail_release):
            with self.assertRaises(OSError):
                f.store.transfer(self.final,self.third,next_binding,f.repo,'retry-op',api=f.api)
        pending=self.final.read_bytes()
        successor=json.loads(target.read_text());successor['new_progress']='preserve me';atomic(target,successor)
        expected=target.read_bytes()
        f.store.transfer(self.final,self.third,next_binding,f.repo,'retry-op',api=f.api)
        self.assertEqual(target.read_bytes(),expected)
        # Simulate a competing owner appearing while the original transfer is suspended.
        self.final.write_bytes(pending)
        successor['binding']['session']='another-owner';atomic(target,successor)
        expected=target.read_bytes()
        with self.assertRaises(RuntimeError):
            f.store.transfer(self.final,self.third,next_binding,f.repo,'retry-op',api=f.api)
        self.assertEqual(target.read_bytes(),expected)
        self.assertEqual(self.final.read_bytes(),pending)
