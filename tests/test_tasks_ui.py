import os
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest

from test_artifacts_yazi import Terminal, SCRIPT
from watchdog_app.todo import Snapshot
from test_actions import FakeBinding

ROOT = SCRIPT.parents[1]

BOUND_SCRIPT = '''import sys,json
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,sys.argv[3])
from test_actions import FakeBinding,NativeBusy
from watchdog_app import bindings,curate
repo=Path(sys.argv[1])
def deliver(binding,text):
 (repo/'delivery.json').write_text(json.dumps({'session':binding.session,'pane':binding.pane,'text':text}))
runtime=SimpleNamespace(Binding=FakeBinding,verify=lambda b,**kw:{'agent_status':'idle'},
 send=deliver,queue=deliver,AgentBusy=NativeBusy)
bindings.engine=lambda:runtime
bindings.project_for=lambda b:repo
def infer(payload,cancel):
 task=next(t for t in payload['tasks'] if 'Add task colors' in t['text'])
 return {'done':[{'id':task['id'],'evidence':'Add task colors is complete.'}],'blocked':[],'add':[]}
curate.ask_codex=infer
from watchdog_app.tasks_ui import run
run(repo,Path(sys.argv[2]))
'''


class TasksUITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.original = ('## In progress\n\n## Next\n- [ ] Add task colors\n'
                         '## Blocked\n- [ ] Check login — Blocked: login expired\n'
                         '## Done\n- [x] Old completion\n')
        (self.repo / 'TODO.md').write_text(self.original)
        self.terminal = Terminal(['python3', str(SCRIPT), 'tasks', '--repo', str(self.repo)],
                                 dict(os.environ, WATCHDOG_FULL_CONTROLS='1', TERM='xterm-256color',
                                      WATCHDOG_STATE_DIR=str(self.repo / 'state')))
        self.addCleanup(self.terminal.close)

    def test_agents_button_and_shortcut_do_not_require_task_selection(self):
        terminal = self.bound_terminal(with_agents=True)
        self.assertTrue(terminal.wait_for('Mostrar ações'))
        os.write(terminal.master, b'?')
        self.assertTrue(terminal.wait_for('Agents m'), terminal.output.decode(errors='replace'))
        os.write(terminal.master, b'm')
        self.assertTrue(terminal.wait_for('Agents aberto'), terminal.output.decode(errors='replace'))
        delivered = json.loads((self.repo/'agents-open.json').read_text())
        self.assertEqual(delivered['role'], 'agents')
        self.assertEqual(delivered['file'], str(self.repo/'binding.json'))
        self.assertEqual((self.repo/'TODO.md').read_text(), self.original)

    def test_unbound_agents_shortcut_refuses_a_guessed_session(self):
        terminal = self.terminal
        self.assertTrue(terminal.wait_for('Mostrar ações'), terminal.output.decode(errors='replace'))
        os.write(terminal.master, b'm')
        self.assertTrue(terminal.wait_for('No conversation binding'), terminal.output.decode(errors='replace'))
        self.assertEqual((self.repo / 'TODO.md').read_text(), self.original)

    def test_keyboard_completion_requires_confirmation_and_cancel_preserves_file(self):
        terminal = self.terminal
        self.assertTrue(terminal.wait_for('Space: select'), terminal.output.decode(errors='replace'))
        os.write(terminal.master, b' d')
        self.assertTrue(terminal.wait_for('Confirm completion'), terminal.output.decode(errors='replace'))
        os.write(terminal.master, b'\x1b')
        self.assertTrue(terminal.wait_for('Cancelled'), terminal.output.decode(errors='replace'))
        self.assertEqual((self.repo / 'TODO.md').read_text(), self.original)
        os.write(terminal.master, b'dy')
        self.assertTrue(terminal.wait_for('Marked 1 task done'), terminal.output.decode(errors='replace'))
        task = next(t for t in Snapshot.read(self.repo).tasks if 'Add task colors' in t.text)
        self.assertTrue(task.done)

    def test_click_selects_task_and_section_colors_are_emitted(self):
        terminal = self.terminal
        self.assertTrue(terminal.wait_for('Space: select'), terminal.output.decode(errors='replace'))
        # Empty In progress takes three body rows; Next header then its task.
        # Body starts at zero-based row 4, so the first task is terminal row 9.
        os.write(terminal.master, b'\x1b[<0;2;9M\x1b[<0;2;9m')
        self.assertTrue(terminal.wait_for('1 task(s) selected'), terminal.output.decode(errors='replace'))
        os.write(terminal.master, b'd')
        self.assertTrue(terminal.wait_for('Confirm completion'), terminal.output.decode(errors='replace'))
        os.write(terminal.master, b'\x1b')
        self.assertTrue(terminal.wait_for('Cancelled'))
        data = terminal.output
        for color in (b'94m', b'93m', b'91m', b'92m'):
            self.assertIn(color, data, 'colored section was not rendered')

    def test_unbound_panel_cannot_send_to_a_guessed_conversation(self):
        terminal = self.terminal
        self.assertTrue(terminal.wait_for('Space: select'))
        os.write(terminal.master, b' s')
        self.assertTrue(terminal.wait_for('No conversation binding'), terminal.output.decode(errors='replace'))
        self.assertEqual((self.repo / 'TODO.md').read_text(), self.original)

    def test_audit_action_selects_account_model_then_requires_explicit_confirmation(self):
        terminal = self.bound_terminal(with_audit=True)
        self.assertTrue(terminal.wait_for('Mostrar ações'), terminal.output.decode(errors='replace'))
        os.write(terminal.master, b'A')
        self.assertTrue(terminal.wait_for('Escolha a conta Codex'), terminal.output.decode(errors='replace'))
        os.write(terminal.master, b'\r')
        self.assertTrue(terminal.wait_for('Modelo de teste'), terminal.output.decode(errors='replace'))
        self.assertTrue(terminal.wait_for('não listado'), terminal.output.decode(errors='replace'))
        os.write(terminal.master, b'\r')
        self.assertTrue(terminal.wait_for('nova auditoria'), terminal.output.decode(errors='replace'))
        self.assertFalse((self.repo/'audit-open.json').exists())
        os.write(terminal.master, b'y')
        self.assertTrue(terminal.wait_for('test-audit'), terminal.output.decode(errors='replace'))
        value = json.loads((self.repo/'audit-open.json').read_text())
        self.assertTrue(value['confirmed']); self.assertEqual(value['model'], 'fixture-model')
        self.assertEqual(value['repo'], str(self.repo))
        self.assertEqual((self.repo/'TODO.md').read_text(), self.original)

    def test_cancel_audit_does_not_launch_or_change_tasks(self):
        terminal = self.bound_terminal(with_audit=True)
        self.assertTrue(terminal.wait_for('Mostrar ações'))
        os.write(terminal.master, b'A')
        self.assertTrue(terminal.wait_for('Escolha a conta Codex'))
        os.write(terminal.master, b'\x1b')
        self.assertTrue(terminal.wait_for('Cancelled'))
        self.assertFalse((self.repo/'audit-open.json').exists())
        self.assertEqual((self.repo/'TODO.md').read_text(), self.original)

    def bound_terminal(self, with_reply=False, with_agents=False, with_audit=False):
        self.terminal.close()
        history = self.repo / 'record.jsonl'
        history.write_text(json.dumps({'type': 'event_msg', 'timestamp': '2026-11-16T10:00:00Z',
            'payload': {'type': 'task_complete', 'turn_id': 'turn', 'last_agent_message': 'Add task colors is complete.'}})+'\n' if with_reply else '')
        binding = self.repo / 'binding.json'
        binding.write_text(json.dumps({'repo':str(self.repo),'binding':asdict(FakeBinding(history=str(history)))}))
        script = BOUND_SCRIPT
        if with_audit:
            script = script.replace('from watchdog_app.tasks_ui import run', """from watchdog_app import audit
from dataclasses import asdict
audit.accounts=lambda session:[session.binding.account]
audit.models=lambda *a:[{'model':'fixture-model','label':'Modelo de teste'}]
def launched(session,account,model,**kw):
 (repo/'audit-open.json').write_text(json.dumps({'account':account,'model':model,'confirmed':kw['confirmed'],'recipient':asdict(session.binding),'repo':str(session.repo)}))
 return {'audit_id':'test-audit'}
audit.launch=launched
from watchdog_app.tasks_ui import run""")
        if with_agents:
            script = script.replace('from watchdog_app.tasks_ui import run', "from watchdog_app import panes\ndef opened(file, project, role):\n (repo/'agents-open.json').write_text(json.dumps({'file':str(file),'role':role}))\n return {'pane_id':'test-agents'}\npanes.open_pane=opened\nfrom watchdog_app.tasks_ui import run")
        terminal = Terminal(['python3','-c',script,str(self.repo),str(binding),str(ROOT/'tests')],
                            dict(os.environ,WATCHDOG_FULL_CONTROLS='1',TERM='xterm-256color',WATCHDOG_STATE_DIR=str(self.repo/'state')))
        self.addCleanup(terminal.close)
        return terminal

    def test_bound_send_confirmation_cancel_and_delivery_keep_task_open(self):
        terminal = self.bound_terminal()
        self.assertTrue(terminal.wait_for('Space: select'))
        os.write(terminal.master,b' s')
        self.assertTrue(terminal.wait_for('Confirm send'),terminal.output.decode(errors='replace'))
        self.assertFalse((self.repo/'delivery.json').exists())
        os.write(terminal.master,b'\x1b')
        self.assertTrue(terminal.wait_for('Cancelled'))
        self.assertFalse((self.repo/'delivery.json').exists())
        os.write(terminal.master,b'sy')
        self.assertTrue(terminal.wait_for('Queued selected tasks to this Codex thread'),terminal.output.decode(errors='replace'))
        delivered=json.loads((self.repo/'delivery.json').read_text())
        self.assertEqual(delivered['session'],'current-session')
        self.assertEqual(delivered['pane'],'project:p4')
        self.assertIn('Add task colors',delivered['text'])
        self.assertEqual((self.repo/'TODO.md').read_text(),self.original)

    def test_review_proposal_does_not_change_file_until_confirmed(self):
        # Spec #1, lines 127 and 168: Review Curator labels its proposal/confirmation.
        terminal = self.bound_terminal(with_reply=True)
        self.assertTrue(terminal.wait_for('1 suggestions'),terminal.output.decode(errors='replace'))
        self.assertEqual((self.repo/'TODO.md').read_text(),self.original)
        os.write(terminal.master,b'r')
        self.assertTrue(terminal.wait_for('Review Curator · propostas'),terminal.output.decode(errors='replace'))
        self.assertTrue(terminal.wait_for('Proposals only'),terminal.output.decode(errors='replace'))
        os.write(terminal.master,b'a')
        self.assertTrue(terminal.wait_for('confirmar alterações'),terminal.output.decode(errors='replace'))
        os.write(terminal.master,b'\x1b')
        self.assertTrue(terminal.wait_for('Cancelled'))
        self.assertEqual((self.repo/'TODO.md').read_text(),self.original)
        os.write(terminal.master,b'ray')
        self.assertTrue(terminal.wait_for('Applied 1 reviewed changes'),terminal.output.decode(errors='replace'))
        task=next(t for t in Snapshot.read(self.repo).tasks if 'Add task colors' in t.text)
        self.assertTrue(task.done)
