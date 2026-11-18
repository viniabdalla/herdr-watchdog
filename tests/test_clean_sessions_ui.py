"""Tasks UI drives the real cleanup backend; model/native boundaries simulated."""
import json
import unittest
from unittest.mock import patch
import test_clean_sessions as fixture
from watchdog_app import tasks_ui


class Screen:
    def getmaxyx(self):return 42,120


class CleanSessionsUITests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.CleanSessionsTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        with patch.object(tasks_ui,'colors',return_value={}):
            self.ui=tasks_ui.TasksUI(Screen(),self.f.repo,self.f.file)
        self.addCleanup(self.ui.job.close)

    def test_action_needs_no_task_selection_shows_exact_scope_and_can_cancel(self):
        self.ui.handle('C');self.assertEqual(self.ui.mode,'clean_setup')
        body='\n'.join(row[0] for row in self.ui.body())
        self.assertIn(self.f.old.session,body);self.assertIn(str(self.f.repo),body)
        self.assertIn('owned',body.lower());self.assertIn('push',body.lower())
        self.ui.handle('escape');self.assertFalse(self.f.runtime.deliveries)

    def test_confirmation_requests_exact_leader_without_marking_todo_done(self):
        before=(self.f.repo/'TODO.md').read_bytes()
        self.ui.handle('C');self.ui.clean_setup.policy=self.f.policy
        self.ui.handle('enter');self.assertEqual(self.ui.mode,'confirm')
        body='\n'.join(row[0] for row in self.ui.body())
        self.assertIn('Confirm Clean sessions',body);self.assertIn(self.f.old.session,body);self.assertIn('origin',body)
        self.ui.can_confirm=True;self.ui.handle('y')
        self.assertEqual(self.f.runtime.deliveries[0][0],self.f.old.session)
        self.assertIn('pending',self.ui.notice.lower());self.assertEqual((self.f.repo/'TODO.md').read_bytes(),before)

    def test_released_panels_follow_successor_and_new_orchestrate_session(self):
        self.f.to_receipt();self.f.receive();op=fixture.clean.load(self.f.store,self.f.op['operation_id'])
        self.f.reply(self.f.old,'released',checkpoint=op['checkpoint'],successor=self.f.new.session);self.f.tick()
        with patch.object(tasks_ui,'latest_reply',return_value=None):self.ui.refresh()
        self.assertEqual(self.ui.session.binding.session,self.f.new.session)
        self.assertEqual(json.loads(self.f.file.read_text())['panes'],{})

    def test_pending_and_partial_outcomes_render_without_false_completion(self):
        self.ui.handle('C');self.ui.clean_setup.policy=self.f.policy;self.ui.handle('enter');self.ui.can_confirm=True;self.ui.handle('y')
        self.assertIn('pending',' '.join(x[0] for x in self.ui.body()).lower())
        op=self.ui.clean.operation;op.update(state='partial',problem='ai-memory unavailable');fixture.clean.save(self.f.store,op)
        self.ui.clean.operation=op
        body='\n'.join(x[0] for x in self.ui.body())
        self.assertIn('partial',body);self.assertIn('ai-memory unavailable',body)

    def test_stopped_operation_offers_retry_and_close_then_c_starts_again(self):
        self.ui.handle('C');self.ui.clean_setup.policy=self.f.policy;self.ui.handle('enter');self.ui.can_confirm=True;self.ui.handle('y')
        op=self.ui.clean.operation;op.update(state='partial',problem='Owned files changed while staging');fixture.clean.save(self.f.store,op)
        self.ui.handle('c');self.assertEqual(self.ui.mode,'confirm')
        body='\n'.join(x[0] for x in self.ui.body())
        self.assertIn('Owned files changed while staging',body);self.assertIn('y: retry',body);self.assertIn('x: close',body)
        self.ui.handle('y');self.assertEqual(fixture.clean.load(self.f.store,op['operation_id'])['state'],'pending')
        op=fixture.clean.load(self.f.store,op['operation_id']);op.update(state='blocked',problem='Leader reports blocked');fixture.clean.save(self.f.store,op)
        self.ui.clean.operation=op;self.ui.handle('c')
        self.assertNotIn('y: retry','\n'.join(x[0] for x in self.ui.body()))
        self.ui.handle('x');self.assertEqual(fixture.clean.load(self.f.store,op['operation_id'])['state'],'closed')
        self.assertIn('closed',self.ui.notice);self.assertEqual(self.ui.mode,'tasks')
        self.ui.handle('C');self.assertEqual(self.ui.mode,'clean_setup')

    def test_setup_lists_pending_project_files_for_commit(self):
        (self.f.repo/'note.md').write_text('dropped by another conversation\n')
        self.ui.handle('C');self.assertIn('note.md',self.ui.clean_setup.policy['owned_paths'])
        self.assertEqual(self.ui.clean_setup.policy['owned_paths'][0],'TODO.md')

    def test_finished_operation_is_one_line_then_disappears(self):
        self.ui.clean.operation={'state':'released','stage':'released','operation_id':'x','updated':__import__('time').time(),
                                 'target':{'pane':'wD:p1P'},'left_uncommitted':['old.py']}
        body='\n'.join(x[0] for x in self.ui.clean.rows())
        self.assertIn('done',body);self.assertIn('wD:p1P',body);self.assertNotIn('old.py',body)
        self.ui.clean.operation['updated']-=601;self.assertEqual(self.ui.clean.rows(),[])

    def test_editing_owned_files_keeps_comma_separators_and_spaces(self):
        self.ui.handle('C');self.ui.clean_setup.index=2
        self.ui.handle('\x15')
        for character in 'TODO.md, owned.py':self.ui.handle(character)
        self.assertEqual(self.ui.clean_setup.policy['owned_paths'],['TODO.md','owned.py'])

    def test_real_curses_action_confirmation_and_queue_remain_pending(self):
        import os
        from test_artifacts_yazi import Terminal
        from test_tasks_ui import BOUND_SCRIPT,ROOT
        script=BOUND_SCRIPT.replace('from test_actions import FakeBinding,NativeBusy', 'from test_actions import NativeBusy\nfrom test_clean_sessions import Binding as FakeBinding').replace('from watchdog_app.tasks_ui import run',
            'bindings.discover=lambda r:([FakeBinding(**json.loads(Path(sys.argv[2]).read_text())["binding"])],[])\nfrom watchdog_app import clean_sessions\nclean_sessions.defaults=lambda s:json.loads(sys.argv[4])\nfrom watchdog_app.tasks_ui import run')
        terminal=Terminal(['python3','-c',script,str(self.f.repo),str(self.f.file),str(ROOT/'tests'),json.dumps(self.f.policy)],
            dict(os.environ,TERM='xterm-256color',WATCHDOG_STATE_DIR=str(self.f.store.root)))
        self.addCleanup(terminal.close)
        self.terminal=terminal
        self.assertTrue(terminal.wait_for('Clean sessions c'))
        os.write(terminal.master,b'c');self.assertTrue(terminal.wait_for('Clean sessions pending'),terminal.output.decode(errors='replace'))
        delivery=json.loads((self.f.repo/'delivery.json').read_text())
        self.assertEqual(delivery['session'],self.f.old.session);self.assertIn('memory_handoff_begin',delivery['text'])

    def test_one_click_transfers_leadership_and_orchestrate_after_concurrent_commit(self):
        with patch.object(tasks_ui,'clean_defaults',return_value=self.f.policy):
            self.ui.handle('c')
        self.f.op=self.ui.clean.operation
        (self.f.repo/'TODO.md').write_text('## Next\n- [ ] Still pending\n')
        fixture.git(self.f.repo,'commit','-am','Concurrent TODO update')
        self.f.prepared(owned_paths=['TODO.md'])
        op=self.f.tick()
        self.assertEqual(op['checkpoint'],fixture.git(self.f.repo,'rev-parse','HEAD'))
        self.f.tick()
        self.f.runtime.actors[self.f.new.session]=fixture.asdict(self.f.new)
        fixture.clean.atomic(fixture.clean.folder(self.f.store,self.f.op['operation_id'])/'leader-proof.json',{'native':fixture.asdict(self.f.new)})
        self.f.tick();self.f.receive();op=fixture.clean.load(self.f.store,self.f.op['operation_id'])
        self.f.reply(self.f.old,'released',checkpoint=op['checkpoint'],successor=self.f.new.session);self.f.tick()
        with patch.object(tasks_ui,'latest_reply',return_value=None):self.ui.refresh()
        self.ui.selected={self.ui.snapshot.tasks[0].id};self.ui.handle('o');self.ui.can_confirm=True;self.ui.handle('y')
        from watchdog_app.mission import RunStore
        run=RunStore(self.f.store.root/'runs').list(self.f.repo)[0]
        self.assertEqual(run['main'],fixture.asdict(self.f.new));self.assertEqual(self.f.runtime.deliveries[-1][0],self.f.new.session)
        self.assertFalse(self.ui.snapshot.tasks[0].done)
        from watchdog_app.actions import Session
        self.assertEqual(Session.for_panel(self.f.file,self.f.repo).binding.session,self.f.new.session,'Progress follows the same sealed Store redirect')

    def test_reopened_tasks_follows_old_binding_file_after_transfer(self):
        self.f.to_receipt();self.f.receive();op=fixture.clean.load(self.f.store,self.f.op['operation_id'])
        self.f.reply(self.f.old,'released',checkpoint=op['checkpoint'],successor=self.f.new.session);self.f.tick()
        with patch.object(tasks_ui,'colors',return_value={}):
            reopened=tasks_ui.TasksUI(Screen(),self.f.repo,self.f.file)
        self.addCleanup(reopened.job.close)
        self.assertIsNotNone(reopened.session.binding)
        self.assertEqual(reopened.session.binding.session,self.f.new.session)

    def test_reopened_and_lagging_tasks_follow_original_arguments_after_two_transfers(self):
        self.f.to_receipt();self.f.receive();op=fixture.clean.load(self.f.store,self.f.op['operation_id'])
        self.f.reply(self.f.old,'released',checkpoint=op['checkpoint'],successor=self.f.new.session);op=self.f.tick()
        third=fixture.Binding(session=str(fixture.uuid.uuid4()),account=self.f.new.account,
            history=str(self.f.root/'third.jsonl'),pane='project:third',terminal='third-terminal',pid=999,started='999')
        fixture.Path(third.history).touch();self.f.runtime.actors[third.session]=fixture.asdict(third)
        self.f.store.transfer(op['new_binding_file'],self.f.new,third,self.f.repo,str(fixture.uuid.uuid4()),api=self.f.api)
        with patch.object(tasks_ui,'colors',return_value={}):reopened=tasks_ui.TasksUI(Screen(),self.f.repo,self.f.file)
        self.addCleanup(reopened.job.close)
        self.assertEqual(reopened.session.binding.session,third.session)
        with patch.object(tasks_ui,'latest_reply',return_value=None):self.ui.refresh()
        self.assertEqual(self.ui.session.binding.session,third.session)
