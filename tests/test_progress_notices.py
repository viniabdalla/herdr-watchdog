"""Spec #1 L85,96-98,153,166: explicit leader events, desktop and Progress."""
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from watchdog_app import leader_kit, long_run
from watchdog_app.progress_agents import Agents
from watchdog_app.store import atomic
from watchdog_app.todo import Snapshot


class ProgressNoticeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.env = patch.dict(os.environ, WATCHDOG_STATE_DIR=str(self.repo/'state'))
        self.env.start(); self.addCleanup(self.env.stop)
        (self.repo/'TODO.md').write_text('## Next\n- [x] T1 (#2) — Work\n- [ ] T2 (#3) — Human — Blocked: Vini\n')
        snapshot = Snapshot.read(self.repo)
        members = [long_run.identity(snapshot,t) for t in snapshot.tasks]
        atomic(long_run.path_for(self.repo), dict(members=members,base='a'*40))
        self.notifications = patch('subprocess.run').start()
        self.addCleanup(patch.stopall)

    def command(self, *args):
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            try:
                return leader_kit.main([args[0],'--repo',str(self.repo),'--grupo','a'*40,*args[1:]])
            except SystemExit as error:
                return error.code

    def text(self):
        return '\n'.join(t for t,_,_ in Agents(self.repo).poll())

    def test_question_persists_notifies_once_and_explicit_answer_clears_it(self):
        # Spec #1 L85,96,166: only an explicit escalation asks the user.
        self.assertNotIn('aguarda você', self.text())
        self.assertEqual(self.command('perguntar','--ticket','T2','--duvida','Qual destino?'),0)
        self.assertIn('pergunta de T2 aguarda você',self.text())
        self.assertIn('Qual destino?',self.text())
        self.assertEqual(self.notifications.call_args.args[0][0], 'notify-send')
        self.assertEqual(self.command('perguntar','--ticket','T2','--duvida','Qual destino?'),0)
        self.assertEqual(self.notifications.call_count,1)
        self.assertEqual(self.command('responder','--ticket','T2'),0)
        self.assertNotIn('aguarda você', self.text())

    def test_end_requires_evidence_reason_next_step_and_retains_summary(self):
        # Spec #1 L97-98: terminal summary is explicit, retained across monitors.
        self.assertEqual(self.command('encerrar','--concluida','T1|abc123, 8 testes OK',
                                     '--bloqueada','T2|Falta decisão|Vini escolhe destino'),0)
        for text in (self.text(),self.text()):
            for part in ('Meta encerrada · 1 de 2','T1','abc123','T2','Falta decisão','Vini escolhe destino'):
                self.assertIn(part,text)
        self.assertEqual(self.notifications.call_count,1)
        self.assertEqual(self.command('encerrar','--concluida','T1|abc123, 8 testes OK',
                                     '--bloqueada','T2|Falta decisão|Vini escolhe destino'),0)
        self.assertEqual(self.notifications.call_count,1)
        long_run.reset(self.repo)
        self.assertNotIn('Meta encerrada',self.text())

    def test_invalid_summary_and_stale_group_leave_state_unchanged(self):
        # Spec #1 L98: no final notice without complete evidence and next steps.
        original=long_run.record(self.repo)
        for args in (('encerrar','--concluida','T1|'),
                     ('encerrar','--bloqueada','T2|motivo'),
                     ('encerrar','--concluida','T1|abc123'),
                     ('perguntar','--ticket','T99','--duvida','Qual?'),
                     ('perguntar','--grupo','b'*40,'--ticket','T2','--duvida','Qual?')):
            self.assertEqual(self.command(*args),1)
            self.assertEqual(long_run.record(self.repo),original)
        self.notifications.assert_not_called()

    def test_notification_unavailable_keeps_visible_event(self):
        # Spec #1 L96-97: desktop failure cannot erase the user-facing banner.
        self.notifications.side_effect=FileNotFoundError('notify-send')
        self.assertEqual(self.command('perguntar','--ticket','T2','--duvida','Qual destino?'),0)
        self.assertIn('pergunta de T2 aguarda você',self.text())
        self.assertIn('notificação indisponível',self.text())

    def test_next_dispatch_clears_end_only_on_confirmed_delivery(self):
        # Spec #1 L97,166: retain final banner until the next dispatch.
        from types import SimpleNamespace as NS
        from watchdog_app import dispatch
        from contextlib import nullcontext
        from test_actions import FakeBinding
        from watchdog_app.dispatch import goal_identity
        self.assertEqual(self.command('encerrar','--concluida','T1|commit e testes',
                                     '--bloqueada','T2|decisão|Vini responde'),0)
        binding=FakeBinding()
        state=long_run.record(self.repo)
        state['goal']=goal_identity(binding)
        atomic(long_run.path_for(self.repo),state)
        session=NS(binding=binding,verify=lambda:None,routing=nullcontext)
        snapshot=Snapshot.read(self.repo)
        offer=dispatch.preview(session,snapshot,{snapshot.tasks[1].id})
        self.assertIn('Meta encerrada',self.text())  # cancelled preview keeps it
        self.assertNotIn('Grupo atualizado',offer['prompt'])
        offer['allow_blocked']=True
        with patch('watchdog_app.dispatch.send'):
            dispatch.deliver(session,offer)
        self.assertNotIn('Meta encerrada',self.text())

    def test_group_accepts_stable_keys_and_unprefixed_titles(self):
        # Spec #1 L96-98: A/B/C are tasks, not necessarily executor ticket names.
        (self.repo/'TODO.md').write_text('## Next\n- [x] A\n- [x] B\n- [ ] C\n')
        snapshot=Snapshot.read(self.repo)
        atomic(long_run.path_for(self.repo),dict(members=[long_run.identity(snapshot,t) for t in snapshot.tasks],base='a'*40))
        self.assertEqual(self.command('perguntar','--tarefa','title:C','--duvida','Qual destino?'),0)
        self.assertIn('pergunta de C aguarda você',self.text())
        self.assertEqual(self.command('encerrar','--concluida','title:A|commit A e testes',
                                     '--concluida','B|commit B e testes','--bloqueada','C|Falta decisão|Vini escolhe destino'),0)
        self.assertIn('Meta encerrada · 2 de 3 · C',self.text())
        self.assertIn('Vini escolhe destino',self.notifications.call_args.args[0][-2])

    def test_failed_dispatch_retains_end_banner(self):
        # Spec #1 L97,151,166: a failed/unconfirmed send cannot clear the end.
        from contextlib import nullcontext
        from types import SimpleNamespace as NS
        from test_actions import FakeBinding
        from watchdog_app import dispatch
        self.assertEqual(self.command('encerrar','--concluida','T1|commit e testes',
                                     '--bloqueada','T2|decisão|Vini responde'),0)
        session=NS(binding=FakeBinding(),verify=lambda:None,routing=nullcontext)
        snapshot=Snapshot.read(self.repo)
        offer=dispatch.preview(session,snapshot,{snapshot.tasks[1].id})
        offer['allow_blocked']=True
        with patch('watchdog_app.dispatch.send',side_effect=RuntimeError('not consumed')):
            with self.assertRaises(RuntimeError):dispatch.deliver(session,offer)
        self.assertIn('Meta encerrada',self.text())

    def test_blocker_and_next_step_precede_thirteen_evidences(self):
        # Spec #1 L97-98,166; spec #21 L32-34: blockers lead AGENTES; the ended banner
        # moved to the end, still before completed evidence.
        (self.repo/'TODO.md').write_text('## Next\n'+''.join(f'- [x] T{n} (#1{n}) — Work\n' for n in range(1,14))+'- [ ] T14 (#114) — Human\n')
        snapshot=Snapshot.read(self.repo)
        atomic(long_run.path_for(self.repo),dict(members=[long_run.identity(snapshot,t) for t in snapshot.tasks],base='a'*40))
        args=['encerrar']
        for n in range(1,14):args.extend(['--concluida',f'T{n}|commit e testes {n}'])
        args.extend(['--bloqueada','T14|Falta decisão|Vini escolhe destino'])
        self.assertEqual(self.command(*args),0)
        lines=self.text().splitlines()
        self.assertEqual(lines[1],'BLOQUEADOS')
        self.assertIn('T14',lines[2])
        self.assertLess(self.text().index('Vini escolhe destino'),self.text().index('Concluída'))
        self.assertLess(self.text().index('Bloqueada'),self.text().index('Concluída'))
        notification=self.notifications.call_args.args[0]
        self.assertIn('Vini escolhe destino',notification[-2])
        self.assertLess(notification[-1].index('Bloqueada'),notification[-1].index('Concluída'))

    def test_uuid_survives_title_change_and_ambiguous_title_is_rejected(self):
        # Spec #1 L96-98,151: stable identities, no guessing among equal titles.
        from test_todo_format import TEXT, KEY
        (self.repo/'TODO.md').write_text(TEXT)
        atomic(long_run.path_for(self.repo),dict(members=['id:'+KEY],base='a'*40))
        self.assertEqual(self.command('perguntar','--ticket',KEY,'--duvida','Qual destino?'),0)
        (self.repo/'TODO.md').write_text(TEXT.replace('Resolver o áudio','Ajustar áudio'))
        self.assertEqual(self.command('responder','--ticket','id:'+KEY),0)
        self.assertNotIn('aguarda você',self.text())
        (self.repo/'TODO.md').write_text('## Next\n- [ ] T1 (#1) — Same\n- [ ] T1 (#2) — Other\n')
        snapshot=Snapshot.read(self.repo)
        atomic(long_run.path_for(self.repo),dict(members=[long_run.identity(snapshot,t) for t in snapshot.tasks],base='a'*40))
        self.assertEqual(self.command('perguntar','--ticket','T1','--duvida','Qual?'),1)
        self.assertEqual(self.command('perguntar','--ticket','ticket:T1#1','--duvida','Qual?'),0)

    def test_pty_low_panel_prioritizes_blocker_and_records_desktop_calls(self):
        # Spec #1 L96-98,153,166: real terminal, fake desktop, isolated state.
        import fcntl
        import struct
        import termios
        from test_artifacts_yazi import Terminal
        boot = r'''
import curses, json, os, sys
from pathlib import Path
from watchdog_app import leader_kit,long_run
from watchdog_app.store import atomic
from watchdog_app.todo import Snapshot
from watchdog_app.progress_ui import panel
repo=Path(sys.argv[1])
(repo/'TODO.md').write_text('## Next\n'+''.join(f'- [x] A{n}\n' for n in range(1,14))+'- [ ] C\n')
snapshot=Snapshot.read(repo)
atomic(long_run.path_for(repo),dict(members=[long_run.identity(snapshot,t) for t in snapshot.tasks],base='a'*40))
common=['--repo',str(repo),'--grupo','a'*40]
for n in range(1,14):
    assert leader_kit.main(['perguntar',*common,'--tarefa',f'A{n}','--duvida','Pergunta antiga'])==0
assert leader_kit.main(['perguntar',*common,'--tarefa','C','--duvida','Qual destino?'])==0
args=['encerrar',*common,'--bloqueada','C|Falta decisão|Escolha destino']
for n in range(1,14):args.extend(['--concluida',f'A{n}|commit e testes {n}'])
assert leader_kit.main(args)==0
curses.wrapper(panel,repo)
'''
        binary=self.repo/'bin';binary.mkdir()
        log=self.repo/'notifications.jsonl'
        notify=binary/'notify-send'
        notify.write_text('#!/usr/bin/env python3\nimport json,sys\nfrom pathlib import Path\nwith Path('+repr(str(log))+').open("a") as f:f.write(json.dumps(sys.argv[1:])+"\\n")\n')
        notify.chmod(0o700)
        terminal=Terminal(['python3','-c',boot,str(self.repo)],dict(os.environ,TERM='xterm-256color',PATH=str(binary)+':'+os.environ['PATH']))
        self.addCleanup(terminal.close)
        fcntl.ioctl(terminal.master,termios.TIOCSWINSZ,struct.pack('HHHH',20,120,0,0))
        self.assertTrue(terminal.wait_for('WATCHDOG / PROGRESS'),terminal.output.decode(errors='replace'))
        self.assertTrue(terminal.wait_for('Meta encerrada'),terminal.output.decode(errors='replace'))
        self.assertTrue(terminal.wait_for('Escolha destino'),terminal.output.decode(errors='replace'))
        import json
        notifications=[json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual(len(notifications),15)
        self.assertIn('pergunta de C',notifications[-2][-2])
        self.assertIn('Escolha destino',notifications[-1][-2])
        os.write(terminal.master,b'q')
        self.assertEqual(terminal.process.wait(timeout=3),0)

    def test_final_banner_precedes_all_old_questions_and_evidence_follows_agents(self):
        # Spec #1 L85,97-98,166; spec #21 L32: questions stay on top, the final notice
        # follows the agents and precedes its evidence.
        self.assertEqual(self.command('perguntar','--ticket','T1','--duvida','Pergunta antiga A'),0)
        self.assertEqual(self.command('perguntar','--ticket','T2','--duvida','Pergunta antiga B'),0)
        self.assertEqual(self.command('encerrar','--concluida','T1|commit e testes',
                                     '--bloqueada','T2|Sem resposta|Vini responde'),0)
        lines=self.text().splitlines()
        self.assertTrue(lines[1].startswith('pergunta de T1'),lines)
        self.assertLess(self.text().index('Líder'),self.text().index('Meta encerrada'))
        self.assertLess(self.text().index('Meta encerrada'),self.text().index('Concluída T1'))
