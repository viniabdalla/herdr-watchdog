"""Spec #1 ponto B: real writers against an isolated Herdr executable."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PaneNoticeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name)
        self.git('init', '-q', '-b', 'integration')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        (self.repo/'TODO.md').write_text('## Next\n- [ ] Example\n')
        self.git('add', 'TODO.md')
        self.git('commit', '-qm', 'base')
        fake = self.repo/'herdr'
        fake.write_text('''#!/usr/bin/env python3
import json, os, sys, time
from pathlib import Path
args = sys.argv[1:]
root = Path(os.environ['FIXTURE_ROOT'])
if args[1] == 'send-keys':
 (root/'enter-started').touch()
 time.sleep(.3)
with (root/'commands').open('a') as f:
 f.write(json.dumps(args)+'\\n')
if args[1] == 'send-text':
 (root/'started').touch()
 time.sleep(.3)
if os.environ.get('FAIL_COMMAND') == args[1]:
 sys.exit(1)
print('{"result":{}}')
''')
        fake.chmod(0o755)
        self.env = dict(os.environ, PATH=str(self.repo)+os.pathsep+os.environ['PATH'],
                        HERDR_BIN_PATH=str(fake), FIXTURE_ROOT=str(self.repo),
                        XDG_STATE_HOME=str(self.repo/'xdg'), WATCHDOG_STATE_DIR=str(self.repo/'state'),
                        PYTHONPATH=str(ROOT)+os.pathsep+str(ROOT/'tests'))

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True).strip()

    def notice(self, *extra):
        return [sys.executable, str(ROOT/'watchdog'), 'aviso', '--lider', 'w11:p8',
                '--pane', 'w11:pE', '--ticket', 'T6', *extra]

    def start(self, argv, **env):
        p = subprocess.Popen(argv, cwd=self.repo, env=dict(self.env, **env),
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        def cleanup():
            if p.poll() is None:
                p.kill()
            p.communicate()
        self.addCleanup(cleanup)
        return p

    def finish(self, p):
        out, err = p.communicate(timeout=15)
        self.assertEqual(p.returncode, 0, out+err)

    def commands(self):
        path = self.repo/'commands'
        return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []

    def wait_text(self, p, marker='started'):
        deadline = time.monotonic()+5
        while not (self.repo/marker).exists() and p.poll() is None and time.monotonic()<deadline:
            time.sleep(.01)
        if not (self.repo/marker).exists():
            self.fail(str(p.communicate(timeout=5)))

    def test_ready_and_blocker_notices_are_whole_messages(self):
        # Spec #1 L60,80,137,172-174: removing the shared lock interleaves writers.
        a = self.start(self.notice('pronto', '--commit', 'abc1234', '--testes', '12 OK', '--resumo', 'Trava pronta'))
        self.wait_text(a)
        b = self.start(self.notice('BLOQUEIO', '--duvida', 'Qual aceite?'),
                       WATCHDOG_STATE_DIR=str(self.repo/'executor-state'))
        self.finish(a)
        self.finish(b)
        self.assertEqual(self.commands(), [
            ['pane','send-text','w11:p8','[T6 · painel w11:pE] T6 pronto: commit abc1234, testes 12 OK. Trava pronta'],
            ['pane','send-keys','w11:p8','Enter'],
            ['pane','send-text','w11:p8','[T6 · painel w11:pE] BLOQUEIO: Qual aceite?'],
            ['pane','send-keys','w11:p8','Enter']])

    def test_lock_is_held_until_enter_finishes(self):
        # Spec #1 L137,174: unlocking after text but before Enter completes is wrong.
        a = self.start(self.notice('BLOQUEIO', '--duvida', 'Primeiro'))
        self.wait_text(a, marker='enter-started')
        b = self.start(self.notice('BLOQUEIO', '--duvida', 'Segundo'))
        self.finish(a)
        self.finish(b)
        self.assertEqual([c[1] for c in self.commands()],
                         ['send-text','send-keys','send-text','send-keys'])

    def writer(self, kind):
        setup = '''from pathlib import Path
from types import SimpleNamespace as NS
import os
repo=Path(os.environ['FIXTURE_ROOT'])
'''
        if kind == 'dispatch':
            body = '''from watchdog_app.dispatch import preview, deliver
from watchdog_app.todo import Snapshot
from contextlib import nullcontext
binding=NS(pane='w11:p8',kind='codex')
session=NS(binding=binding,verify=lambda:None,routing=nullcontext)
snapshot=Snapshot.read(repo)
offer=preview(session,snapshot,{snapshot.tasks[0].id})
deliver(session,offer)
'''
        else:
            body = '''from watchdog_app.tasks_ui import TasksUI
ui=object.__new__(TasksUI)
ui.pending=dict(kind='verify',prompt='Verifique Example',ids={'1'})
ui.selected=set()
ui.refresh=lambda:None
ui.busy=lambda text:None
ui.clean=NS(operation=None)
ui.session=NS(verify=lambda:None,binding=NS(pane='w11:p8'))
ui.execute()
'''
        return [sys.executable, '-c', setup+body]

    def test_tasks_dispatch_and_verify_do_not_mix_with_notice(self):
        # Spec #1 L58-60,137,175: both real Tasks writers hold through Enter.
        for kind in ('dispatch', 'verify'):
            with self.subTest(kind=kind):
                (self.repo/'started').unlink(missing_ok=True)
                (self.repo/'commands').unlink(missing_ok=True)
                writer = self.start(self.writer(kind))
                self.wait_text(writer)
                notice = self.start(self.notice('BLOQUEIO', '--duvida', 'Aguarda decisão'))
                self.finish(writer)
                self.finish(notice)
                commands = self.commands()
                self.assertEqual([c[1] for c in commands], ['send-text','send-keys','send-text','send-keys'])
                self.assertIn('Concluir somente' if kind == 'dispatch' else 'Verifique Example', commands[0][3])
                self.assertIn('BLOQUEIO: Aguarda decisão', commands[2][3])
                self.assertEqual(commands[1], ['pane','send-keys','w11:p8',
                                               'enter' if kind == 'verify' else 'Enter'])

    def test_failed_text_does_not_submit_or_retry_and_releases_lock(self):
        # Spec #1 L137,151: keep text/Enter order, expose failure, no retry.
        p = self.start(self.notice('BLOQUEIO', '--duvida', 'Falha'), FAIL_COMMAND='send-text')
        _, err = p.communicate(timeout=10)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('não confirmado', err)
        self.assertEqual(len(self.commands()), 1)
        self.finish(self.start(self.notice('BLOQUEIO', '--duvida', 'Novo evento')))
        self.assertEqual([c[1] for c in self.commands()], ['send-text','send-text','send-keys'])

    def test_incomplete_ready_notice_is_rejected_without_sending(self):
        # Spec #1 L80: a ready event includes commit and tests.
        p = self.start(self.notice('pronto', '--resumo', 'Sem evidência'))
        p.communicate(timeout=10)
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(self.commands(), [])
