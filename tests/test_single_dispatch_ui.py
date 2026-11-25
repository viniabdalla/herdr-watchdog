import copy
import curses
from dataclasses import asdict
import os
import unittest
from unittest.mock import patch

from test_task_disclosure import Screen
import test_mission_single
from watchdog_app.tasks_ui import TasksUI
from watchdog_app.todo import Snapshot
from watchdog_app import mission_single as single, mission, progress_ui


class DispatchUITests(unittest.TestCase):
    def setUp(self):
        f=test_mission_single.SingleTests(); f.setUp(); self.addCleanup(f.doCleanups); self.f=f
        self.env=patch.dict(os.environ,WATCHDOG_FULL_CONTROLS='1',WATCHDOG_STATE_DIR=str(f.f.root/'ui-state'))
        self.env.start(); self.addCleanup(self.env.stop)
        self.ui=TasksUI(Screen(54),f.repo,None); self.addCleanup(self.ui.job.close)
        self.ui.snapshot=Snapshot.read(f.repo); self.ui.selected={self.ui.snapshot.tasks[0].id}
        # Same native leader boundary as launch fixture; real request persists a ledger.
        from contextlib import nullcontext
        self.ui.session=f.f.session
        self.ui.session.file=f.f.root/'binding.json'
        self.ui.session.routing=lambda:nullcontext()
        self.ui.session.runtime=f.engine
        self.ui.session.label='Leader · wd-test:p1'

    def body(self):return '\n'.join(row[0] for row in self.ui.body())

    def select_executor(self):
        self.ui.handle('D'); self.ui.draw(); self.ui.handle('enter')
        self.assertEqual(self.ui.mode,'executors')
        self.ui.draw(); self.ui.handle('enter')

    def test_dispatch_menu_and_executor_panel_require_separate_confirmation(self):
        self.ui.handle('D')
        self.assertIn('Para um agente',self.body()); self.assertIn('Orquestrar equipe',self.body())
        self.ui.draw(); self.ui.handle('enter')
        self.assertIn(self.f.worker.pane,self.body())
        self.assertIn(self.f.worker.session,self.body())
        self.assertFalse(self.f.messages)
        self.ui.draw(); self.ui.handle('enter')
        self.assertEqual(self.ui.mode,'confirm')
        body=self.body(); self.assertIn('Confirmar envio para um agente',body)
        self.assertIn(self.f.worker.pane,body); self.assertIn('Revisão pelo líder',body)
        self.assertFalse(self.f.messages)
        self.ui.draw(); self.ui.handle('y')
        runs=mission.RunStore().list(self.f.repo)
        self.assertEqual(len(runs),1); self.assertEqual(runs[0]['execution_mode'],'single')
        self.assertEqual(runs[0]['executor'],self.f.executor)
        self.assertEqual(self.f.messages[0][0],asdict(self.ui.session.binding))
        self.assertIn('leader-review',self.f.messages[0][1])
        self.assertFalse(Snapshot.read(self.f.repo).tasks[0].done)

    def test_mouse_selects_mode_then_executor_and_escape_sends_nothing(self):
        self.ui.handle('D'); self.ui.draw()
        for identity in ('single',0):
            target=next(t for t in self.ui.targets if t[3]==('item',identity))
            x,y,_,_=target
            with patch('curses.getmouse',return_value=(0,x,y,0,curses.BUTTON1_CLICKED)):
                self.ui.handle(self.ui.mouse())
            self.ui.draw()
        self.assertEqual(self.ui.mode,'confirm')
        self.ui.handle('escape')
        self.assertEqual(self.ui.mode,'tasks'); self.assertFalse(self.f.messages)
        self.assertFalse(mission.RunStore().list(self.f.repo))

    def test_no_eligible_executor_explains_requirement_without_side_effect(self):
        self.f.live['agent_status']='working'
        self.ui.handle('D'); self.ui.draw(); self.ui.handle('enter')
        self.assertIn('Nenhum executor',self.body())
        self.ui.draw(); self.ui.handle('enter'); self.ui.handle('y')
        self.assertFalse(self.f.messages)

    def test_recipient_became_busy_or_task_changed_blocks_confirmed_send(self):
        self.select_executor(); self.ui.draw(); self.f.live['agent_status']='working'
        with self.assertRaisesRegex(RuntimeError,'idle'):self.ui.handle('y')
        self.assertFalse(self.f.messages)
        self.f.live['agent_status']='idle'
        (self.f.repo/'TODO.md').write_text('## Next\n- [ ] Changed\n')
        with self.assertRaises(RuntimeError):self.ui.handle('y')
        self.assertFalse(self.f.messages)

    def test_team_choice_and_old_shortcut_preserve_two_actor_flow(self):
        self.ui.handle('D'); self.ui.draw(); self.ui.handle('down'); self.ui.draw(); self.ui.handle('enter')
        self.assertEqual(self.ui.pending['kind'],'orchestrate')
        self.assertIn('one Codex worker + one Codex QA',self.body())
        self.ui.handle('escape'); self.ui.handle('o')
        self.assertEqual(self.ui.pending['kind'],'orchestrate')
        self.ui.handle('escape'); self.ui.handle('s')
        self.assertEqual(self.ui.pending['kind'],'send')

    def test_single_mode_rejects_multiple_tasks_before_selecting_executor(self):
        self.ui.selected={t.id for t in self.ui.snapshot.tasks}
        self.ui.handle('D'); self.ui.draw()
        with self.assertRaisesRegex(RuntimeError,'uma tarefa'):self.ui.handle('enter')
        self.assertFalse(self.f.messages)

    def test_progress_identifies_existing_executor_and_leader_review(self):
        self.f.active_result(); self.f.review()
        body='\n'.join(text for text,_,_ in progress_ui.rows(self.f.repo,self.f.store))
        self.assertIn('Revisão do líder',body)
        self.assertIn(self.f.worker.pane,body)
        self.assertNotIn('QA is checking',body)

    def test_real_terminal_dispatch_menu_recipient_confirmation_and_cancel(self):
        import json
        from pathlib import Path
        from test_artifacts_yazi import Terminal
        binding=self.f.f.root/'pty-binding.json'
        binding.write_text(json.dumps({'repo':str(self.f.repo),'binding':asdict(self.f.f.session.binding)}))
        receipt=self.f.f.root/'pty-receipt.json'
        code='''import sys,json,uuid
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,sys.argv[3])
from test_actions import FakeBinding
from watchdog_app import bindings,curate
repo=Path(sys.argv[1]);worktree=Path(sys.argv[4]);worker=FakeBinding(**json.loads(sys.argv[5]))
def live(b,**kwargs):return {'agent_status':'idle','cwd':str(worktree if b.session==worker.session else repo)}
def queue(b,text):
 Path(sys.argv[6]).write_text(json.dumps({'session':b.session,'text':text}))
 return str(uuid.uuid4())
runtime=SimpleNamespace(Binding=FakeBinding,verify=live,candidates=lambda:([worker],[]),queue=queue)
bindings.engine=lambda:runtime
bindings.project_for=lambda b:worktree if b.session==worker.session else repo
curate.latest_reply=lambda b:None
from watchdog_app.tasks_ui import run
run(repo,Path(sys.argv[2]))
'''
        terminal=Terminal(['python3','-B','-c',code,str(self.f.repo),str(binding),str(Path(__file__).parent),
                          str(self.f.worktree),json.dumps(asdict(self.f.worker)),str(receipt)],dict(os.environ,TERM='xterm-256color'))
        self.addCleanup(terminal.close)
        self.assertTrue(terminal.wait_for('Despachar p'),terminal.output.decode(errors='replace'))
        os.write(terminal.master,b' D')
        self.assertTrue(terminal.wait_for('Para um agente'),terminal.output.decode(errors='replace'))
        self.assertTrue(terminal.wait_for('Orquestrar equipe'),terminal.output.decode(errors='replace'))
        terminal.output=b'';os.write(terminal.master,b'\r')
        self.assertTrue(terminal.wait_for(self.f.worker.pane),terminal.output.decode(errors='replace'))
        terminal.output=b'';os.write(terminal.master,b'\r')
        self.assertTrue(terminal.wait_for('Confirmar envio'),terminal.output.decode(errors='replace'))
        self.assertTrue(terminal.wait_for('Revisão pelo líder'),terminal.output.decode(errors='replace'))
        self.assertFalse(receipt.exists())
        os.write(terminal.master,b'\x1b')
        self.assertTrue(terminal.wait_for('Cancelled'),terminal.output.decode(errors='replace'))
        self.assertFalse(receipt.exists())
        self.assertFalse(Snapshot.read(self.f.repo).tasks[0].done)
