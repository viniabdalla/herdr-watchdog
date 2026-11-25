"""Exercise actual terminal controls rather than comparing source text."""
import json
import os
from pathlib import Path
import subprocess
import unittest

import test_tasks_ui
from test_artifacts_yazi import Terminal,SCRIPT
from watchdog_app.mission import RunStore


class OrchestrateUITests(unittest.TestCase):
    setUp=test_tasks_ui.TasksUITests.setUp
    bound_terminal=test_tasks_ui.TasksUITests.bound_terminal

    def test_orchestrate_shows_team_and_main_then_requires_confirmation(self):
        terminal=self.bound_terminal()
        self.assertTrue(terminal.wait_for('Mostrar ações'),terminal.output.decode(errors='replace'))
        os.write(terminal.master,b' o')
        self.assertTrue(terminal.wait_for('Confirm orchestration'),terminal.output.decode(errors='replace'))
        self.assertTrue(terminal.wait_for('one Codex worker'),terminal.output.decode(errors='replace'))
        self.assertFalse((self.repo/'delivery.json').exists())
        os.write(terminal.master,b'\x1b')
        self.assertTrue(terminal.wait_for('Cancelled'))
        os.write(terminal.master,b'oy')
        self.assertTrue(terminal.wait_for('see Progress'),terminal.output.decode(errors='replace'))
        delivered=json.loads((self.repo/'delivery.json').read_text())
        self.assertEqual(delivered['session'],'current-session')
        self.assertIn('explicit brief',delivered['text'])
        self.assertEqual((self.repo/'TODO.md').read_text(),self.original)
        runs=RunStore(self.repo/'state'/'runs').list(self.repo)
        self.assertEqual(len(runs),1)
        self.assertTrue(all(t['state']=='ready' for t in runs[0]['tasks'].values()))

    def test_progress_uses_real_run_and_project_counts_without_preview_file(self):
        self.terminal.close()
        run={'id':'d6b97491-3dc1-4018-afb7-ce263032e5e2','repo':str(self.repo),'created':1,
             'phase':'active','participants':{'worker':{'model':'gpt-6.1-sol','effort':'medium'}},'tasks':{'x':{'title':'Actual selected task',
                'state':'blocked','agent':'main','summary':'Missing approved fixture','updated':1}}}
        RunStore(self.repo/'state'/'runs').save(run)
        terminal=Terminal(['python3',str(SCRIPT),'progress','--repo',str(self.repo)],
                          dict(os.environ,TERM='xterm-256color',WATCHDOG_STATE_DIR=str(self.repo/'state')))
        self.addCleanup(terminal.close)
        self.assertTrue(terminal.wait_for('Needs help'),terminal.output.decode(errors='replace'))
        self.assertTrue(terminal.wait_for('Missing approved fixture'),terminal.output.decode(errors='replace'))
        self.assertTrue(terminal.wait_for('gpt-6.1-sol'),terminal.output.decode(errors='replace'))
        self.assertTrue(terminal.wait_for('medium'),terminal.output.decode(errors='replace'))
        self.assertTrue(terminal.wait_for('Projeto ·'),terminal.output.decode(errors='replace'))
        self.assertIn(b'91m',terminal.output)

    def test_cli_inspect_is_available_without_native_binding(self):
        store=RunStore(self.repo/'runs');identity='d6b97491-3dc1-4018-afb7-ce263032e5e2'
        store.save({'id':identity,'repo':str(self.repo),'created':1,'tasks':{},'phase':'requested'})
        result=subprocess.run(['python3',str(SCRIPT.parents[1]/'watchdog'),'mission','inspect',
                               '--run',identity,'--state-dir',str(store.root)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['id'],identity)


class CheckpointUITests(unittest.TestCase):
    """Real curses + real git: o, y commits exactly the listed changes, then requests the run."""
    setUp=test_tasks_ui.TasksUITests.setUp
    bound_terminal=test_tasks_ui.TasksUITests.bound_terminal

    def git(self,*args):
        return subprocess.run(['git','-C',str(self.repo),*args],check=True,capture_output=True,text=True).stdout

    def test_dirty_repo_is_checkpointed_inside_orchestrate(self):
        (self.repo/'.gitignore').write_text('state/\nclean-sessions/\nbinding.json\nrecord.jsonl\ndelivery.json\n')
        self.git('init','-q');self.git('config','user.name','t');self.git('config','user.email','t@t')
        self.git('add','-A');self.git('commit','-qm','base')
        (self.repo/'feature.py').write_text('ready = True\n')
        terminal=self.bound_terminal()
        self.assertTrue(terminal.wait_for('Mostrar ações'),terminal.output.decode(errors='replace'))
        os.write(terminal.master,b' o')
        self.assertTrue(terminal.wait_for('New: feature.py'),terminal.output.decode(errors='replace'))
        self.assertEqual(self.git('log','--oneline').count('\n'),1)
        os.write(terminal.master,b'y')
        self.assertTrue(terminal.wait_for('saved'),terminal.output.decode(errors='replace'))
        self.assertTrue(terminal.wait_for('see Progress'),terminal.output.decode(errors='replace'))
        self.assertIn('Watchdog checkpoint before Orchestrate',self.git('log','-1','--format=%s'))
        self.assertEqual(self.git('status','--porcelain'),'')
        run=RunStore(self.repo/'state'/'runs').list(self.repo)[0]
        self.assertEqual(run['checkpoint']['sha'],self.git('rev-parse','HEAD').strip())
        self.assertIn(run['checkpoint']['sha'],json.loads((self.repo/'delivery.json').read_text())['text'])
