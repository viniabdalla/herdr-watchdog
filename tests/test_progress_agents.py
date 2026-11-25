"""Spec #1 L94-97,141,167: live, read-only AGENTES in Progress."""
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from dataclasses import asdict
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from test_actions import FakeBinding
from watchdog_app import long_run
from watchdog_app.progress_ui import rows


class ProgressAgentsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        (self.repo/'TODO.md').write_text('## Next\n- [ ] T1 (#2) — Work\n- [ ] T2 (#3) — Wait — Blocked: T1\n- [ ] T3 (#4) — Human — Blocked: Vini\n')
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, WATCHDOG_STATE_DIR=str(self.repo/'state')).start()
        from watchdog_app.todo import Snapshot
        snap = Snapshot.read(self.repo)
        group = long_run.save(snap, [t.id for t in snap.tasks])
        from watchdog_app.store import atomic
        atomic(long_run.path_for(self.repo), {'members':group, 'base':'a'*40})
        self.tree = self.repo/'.worktrees/T1'; self.tree.mkdir(parents=True)
        self.history = self.tree/'history.jsonl'
        self.history.write_text(json.dumps({'payload':{'type':'token_count','info':{
            'last_token_usage':{'total_tokens':12000},'model_context_window':100000,
            'total_token_usage':{'total_tokens':15000}}}})+'\n')
        self.worker = FakeBinding(session='worker',pane='w:p2',terminal='t2',history=str(self.history))
        self.leader = FakeBinding(history=str(self.history))
        self.file = self.repo/'binding.json'
        self.file.write_text(json.dumps({'repo':str(self.repo),'binding':asdict(self.leader)}))
        self.record = dict(group='a'*40,ticket='T1',leader=self.leader.pane,pane='w:p2',terminal='t2',
                           session=None,worktree=str(self.tree),state='ready',created_at=100)
        self.live = [dict(pane_id=b.pane,terminal_id=b.terminal,agent=b.kind,
                          agent_session={'kind':'id','value':b.session},agent_status='working',
                          cwd=str(self.tree if b is self.worker else self.repo)) for b in (self.leader,self.worker)]
        patch('watchdog_app.leader_kit.executors', side_effect=lambda repo,group=None:{'executors':[self.record] if group in (None,self.record['group']) else []}).start()
        patch('watchdog_app.bindings.engine',return_value=NS(Binding=FakeBinding,verify=lambda b:None,
              candidates=lambda:([self.leader,self.worker],[]))).start()
        patch('watchdog_app.bindings.project_for',return_value=self.repo).start()
        def read_panes(*args):
            self.assertEqual(args[:2], ('pane','list'), 'AGENTES must never send or mutate panes')
            return {'panes':self.live}
        patch('watchdog_app.herdr.Herdr.call',side_effect=read_panes).start()

    @staticmethod
    def agent(lines, prefix):
        """Spec #21 L39: an agent line plus its indented activity line."""
        lines=[t if isinstance(t,str) else t[0] for t in lines]
        index=next(i for i,t in enumerate(lines) if t.startswith(prefix))
        following=lines[index+1] if index+1<len(lines) and lines[index+1].startswith('  ') else ''
        return lines[index]+' · '+following.strip()

    def monitor(self):
        from watchdog_app.progress_agents import Agents
        return Agents(self.repo,self.file)

    def test_registered_late_session_and_waiting_tasks_are_read_only(self):
        # Spec #1 L94-97,167: real transcript usage, kit registry and explicit blockers.
        monitor=self.monitor()
        text='\n'.join(t for t,_,run in monitor.poll())
        for expected in ('AGENTES','Líder','w:p2','Trabalhando','12k','12%',
                         'próxima checagem prevista 1/3','T2','espera outra','T3','depende do Vini'):
            self.assertIn(expected,text)
        self.assertFalse(any(isinstance(run,dict) for _,_,run in monitor.poll()))  # no runs, only AGENTES items
        self.assertIsNone(self.record['session'])
        with self.history.open('a') as stream:
            stream.write(self.history.read_text().replace('12000','24000'))
        self.assertIn('24%', '\n'.join(t for t,_,_ in monitor.poll()))

    def test_executor_activity_uses_own_verified_history_and_keeps_task_and_checks(self):
        # Spec #1 L92-94,153,167: normal Progress presentation, separate native sources.
        from test_session_progress import codex_call, codex_result
        from dataclasses import replace
        history=self.tree/'worker.jsonl'
        history.write_text('\n'.join(json.dumps(e) for e in (codex_call(),codex_result()))+'\n')
        self.worker=replace(self.worker,history=str(history))
        self.record['checks']=[{'summary':'rumo conferido'}]
        monitor=self.monitor()
        lines=[t for t,_,_ in monitor.poll()]
        worker=self.agent(lines,'T1 ·')
        self.assertIn('Inspect fixtures',worker)
        self.assertNotIn('T1 (#2) — Work',worker)  # spec #21 L39: activity, or the title when none
        self.assertIn('checagem inicial 1/3',worker)
        self.assertNotIn('Inspect fixtures',self.agent(lines,'Líder ·'))
        self.live[1]['agent_session']={'kind':'id','value':'replacement'}
        self.assertNotIn('Inspect fixtures',self.agent(monitor.poll(),'T1 ·'))

    def test_executor_binding_is_verified_once_per_refresh(self):
        # Spec #1 L92-94,141: reuse the monitor verification for activity and context.
        from watchdog_app import bindings
        calls=[]
        bindings.engine().verify=lambda binding:calls.append(binding.session)
        self.monitor().poll()
        self.assertEqual(calls.count('worker'),1)

    def test_replaced_terminal_worktree_or_session_hides_usage(self):
        # Spec #1 L95: never associate telemetry with a different native actor.
        # Spec #21 L36: a replaced terminal means the worker's pane was closed.
        self.live[1]['terminal_id']='other'
        self.assertFalse(any(t.startswith('T1 ·') for t,_,_ in self.monitor().poll()))
        self.live[1]['terminal_id']='t2'
        for field,value in (('cwd',str(self.repo)),
                            ('agent_session',{'kind':'id','value':'replacement'})):
            with self.subTest(field=field):
                previous=self.live[1][field];self.live[1][field]=value
                line=next(t for t,_,_ in self.monitor().poll() if t.startswith('T1 ·'))
                self.assertNotIn('12%',line)
                self.live[1][field]=previous

    def test_agents_precede_session_and_runs_even_without_binding(self):
        # Spec #1 L94,141: always present under group and project bars, no button.
        # Spec #21 L43: SESSION only appears with a checklist.
        source=rows(self.repo,NS(list=lambda repo:[]),progress=NS(poll=lambda:NS(state='working',total=2,done=0,current='Passo',detail=None)))
        text=[t for t,_,_ in source]
        self.assertIn('AGENTES',text)
        self.assertLess(text.index('AGENTES'),next(i for i,t in enumerate(text) if t.startswith('SESSION')))
        source=rows(self.repo,NS(list=lambda repo:[]),progress=NS(poll=lambda:NS(state='unavailable',total=None,detail='offline')))
        self.assertFalse(any(t.startswith('SESSION') or t.startswith('No active runs') for t,_,_ in source))

    def test_group_base_and_initial_check_schedule(self):
        # Spec #1 L95-97,139: checks at 2, 3 and 4 minutes. Spec #21 L35 replaces
        # "current group only": other rounds of the same leader stay visible.
        monitor=self.monitor()
        for _ in range(3):
            self.assertIn('próxima checagem prevista 1/3', '\n'.join(t for t,_,_ in monitor.poll()))
        self.record['group']='previous-group'
        self.assertTrue(any(t.startswith('T1 ·') for t,_,_ in monitor.poll()))
        self.record['leader']='w:other'
        self.assertFalse(any(t.startswith('T1 ·') for t,_,_ in monitor.poll()))
        self.assertTrue(any('Outros' in t for t,_,_ in monitor.poll()))

    def test_pty_twenty_lines_keeps_agents_visible_and_refreshes(self):
        # Spec #1 L94-97,153,167: actual terminal, isolated runtime, no sends.
        import fcntl
        import struct
        import termios
        from test_artifacts_yazi import Terminal
        boot = """
import sys, curses
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,sys.argv[1])
from test_progress_agents import ProgressAgentsTests
from watchdog_app import leader_kit
read_registry=leader_kit.executors
f=ProgressAgentsTests();f.setUp()
from watchdog_app.progress_ui import panel
from watchdog_app import leader_kit
from dataclasses import replace
records=[]
for n in range(1,13):
    actor=replace(f.worker,pane='w:p'+str(n+10),terminal='t'+str(n+10),session='s'+str(n))
    records.append(dict(f.record,ticket='T'+str(n),pane=actor.pane,terminal=actor.terminal))
    f.live.append(dict(f.live[1],pane_id=actor.pane,terminal_id=actor.terminal,
                       agent_session={'kind':'id','value':actor.session}))
f.live[2]['agent_status']='idle'
actors=[replace(f.worker,pane=r['pane'],terminal=r['terminal'],session='s'+str(i+1)) for i,r in enumerate(records)]
from watchdog_app import bindings
bindings.engine().candidates=lambda:([f.leader]+actors,[])

from watchdog_app.store import atomic
atomic(f.repo/'.watchdog/executors.json',{'version':1,'project':str(f.repo),'executors':records})
leader_kit.executors=read_registry
for step in (1,2,3):leader_kit.record_check(f.repo,group='a'*40,ticket='T2',step=step,summary='rumo conferido')
from test_session_progress import codex_call, codex_result
with f.history.open('a') as stream:
    for event in (codex_call(),codex_result()):stream.write(__import__('json').dumps(event)+'\\n')
(f.repo/'TODO.md').write_text((f.repo/'TODO.md').read_text().replace('- [ ] T1','- [x] T1'))
original=(f.repo/'TODO.md').read_bytes()
registry=(f.repo/'.watchdog/executors.json').read_bytes()
f.live[1]['agent_status']='idle'
try:
    curses.wrapper(panel,f.repo,f.file)
    assert (f.repo/'TODO.md').read_bytes()==original
    assert (f.repo/'.watchdog/executors.json').read_bytes()==registry
finally:f.doCleanups()
"""
        terminal=Terminal(['python3','-c',boot,str(Path(__file__).parent)],dict(os.environ,TERM='xterm-256color'))
        self.addCleanup(terminal.close)
        fcntl.ioctl(terminal.master,termios.TIOCSWINSZ,struct.pack('HHHH',20,120,0,0))
        self.assertTrue(terminal.wait_for('AGENTES'),terminal.output.decode(errors='replace'))
        self.assertTrue(terminal.wait_for('Líder'),terminal.output.decode(errors='replace'))
        self.assertTrue(terminal.wait_for('concluída'),terminal.output.decode(errors='replace'))
        self.assertTrue(terminal.wait_for('Inspect fixtures'),terminal.output.decode(errors='replace'))
        os.write(terminal.master,b'jjjjjjjjjjjjjjjj')  # spec #21 L32: separator lines take rows
        self.assertTrue(terminal.wait_for('checagem inicial 3/3'),terminal.output.decode(errors='replace'))
        os.write(terminal.master,b'jjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjj')
        self.assertTrue(terminal.wait_for('T12'),terminal.output.decode(errors='replace'))
        os.write(terminal.master,b'q')
        self.assertEqual(terminal.process.wait(timeout=3),0)

    def test_done_todo_and_observed_leader_activity_replace_waiting(self):
        # Spec #1 L94-97: completion and current work are visible per agent.
        # Spec #21 L36-37: a stopped worker with a done task is Feito, in a collapsed group.
        from test_session_progress import codex_call, codex_result
        with self.history.open('a') as stream:
            for event in (codex_call(),codex_result()):stream.write(json.dumps(event)+'\n')
        text=(self.repo/'TODO.md').read_text().replace('- [ ] T1','- [x] T1')
        (self.repo/'TODO.md').write_text(text)
        self.live[1]['agent_status']='idle'
        monitor=self.monitor()
        self.assertIn('1 feito',next(t for t,_,_ in monitor.poll() if t.startswith('▶')))
        monitor.toggle('w:t2' if self.record.get('tab') else '—')
        source=monitor.poll()
        worker=self.agent(source,'T1 ·')
        leader=self.agent(source,'Líder ·')
        self.assertIn('Feito',worker)
        self.assertNotIn('aguardando aviso',worker)
        self.assertIn('Inspect fixtures',leader)

    def test_kit_check_is_persisted_and_progress_does_not_infer_confirmation(self):
        # Spec #1 L80,96,135: leader records each actual initial check through the kit.
        from watchdog_app import leader_kit
        from watchdog_app.store import atomic
        target=self.repo/'.watchdog/executors.json'
        self.record['id']='executor-one'
        atomic(target,{'version':1,'project':str(self.repo),'executors':[self.record]})
        monitor=self.monitor()
        self.assertNotIn('checagem inicial 3/3', '\n'.join(t for t,_,_ in monitor.poll()))
        for step in (1,2,3):
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                result = leader_kit.main(['checar','--repo',str(self.repo),'--grupo','a'*40,
                '--ticket','T1','--etapa',str(step),'--resumo','rumo conferido'])
            self.assertEqual(result,0)
        self.record.update(json.loads(target.read_text())['executors'][0])
        text='\n'.join(t for t,_,_ in monitor.poll())
        self.assertIn('checagem inicial 3/3',text)
        self.assertIn('rumo conferido',text)
        before=target.read_bytes()
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            result = leader_kit.main(['checar','--repo',str(self.repo),'--grupo','a'*40,
            '--ticket','T1','--etapa','2','--resumo','duplicate'])
        self.assertEqual(result,1)
        self.assertEqual(target.read_bytes(),before)
