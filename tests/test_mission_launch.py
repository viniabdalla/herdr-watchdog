"""Use real temporary Git repositories; substitute only native Herdr/Gossip boundaries."""
import copy
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from test_actions import FakeBinding
from watchdog_app.mission import RunStore
from watchdog_app import mission_launch as launch
from watchdog_app.todo import Snapshot


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True, text=True, capture_output=True).stdout.strip()


class NativeHerdr:
    def __init__(self):
        self.calls = [];self.panes = {};self.fail = None
    def call(self, *args):
        self.calls.append(args)
        if self.fail == args[:2]:raise RuntimeError('Native response lost')
        if args[:2] == ('tab', 'create'):
            pane = {'pane_id':'wd-test:p1','terminal_id':'terminal1','tab_id':'tab','workspace_id':'wd-test'}
            self.panes[pane['pane_id']] = pane
            return {'root_pane':pane.copy()}
        if args[:2] == ('pane', 'split'):
            pane = {'pane_id':'wd-test:p2','terminal_id':'terminal2','tab_id':'tab','workspace_id':'wd-test'}
            self.panes[pane['pane_id']] = pane
            return {'pane':pane.copy()}
        if args[:2] == ('pane', 'get'):return {'pane':self.panes[args[2]].copy()}
        if args[:2] == ('pane', 'process-info'):
            return {'process_info':{'shell_pid':99, 'foreground_processes':[]}}
        if args[:2] not in (('pane','run'),('pane','rename'),('tab','focus')):raise AssertionError(args)
        return {}
    def checked(self, pane):
        live = self.call('pane','get',pane['pane_id'])['pane']
        if live['terminal_id'] != pane['terminal_id']:raise RuntimeError('terminal changed')
        return live


class LaunchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='wd-test-launch-');self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name);self.repo = self.root/'repo';self.repo.mkdir()
        git(self.repo,'init','-q');git(self.repo,'config','user.email','test@example.invalid');git(self.repo,'config','user.name','Test')
        (self.repo/'TODO.md').write_text('## Next\n- [ ] First\n- [ ] Second\n')
        (self.repo/'a.py').write_text('print(1)\n')
        git(self.repo,'add','TODO.md','a.py');git(self.repo,'commit','-qm','base')
        self.base = git(self.repo,'rev-parse','HEAD');snapshot = Snapshot.read(self.repo)
        self.store = RunStore(self.root/'runs');self.run_id = 'e6b69dbf-b3ef-4481-a0d0-8c9698cc1eb6'
        binding = FakeBinding()
        self.run = {'version':1,'id':self.run_id,'repo':str(self.repo),'main':asdict(binding),
            'binding_file':str(self.root/'binding.json'),'source_digest':snapshot.digest,'created':0,
            'phase':'requested','request_delivery':'sent','tasks':{t.id:{'title':t.text,'state':'ready','agent':'main','updated':0,'summary':''} for t in snapshot.tasks},
            'participants':{},'resources':{},'events':{},'cursor':0,'candidate':None,'qa':None}
        self.store.save(self.run)
        self.session = SimpleNamespace(binding=binding,verify=lambda:{'agent_status':'idle'})
        self.api = NativeHerdr()
        self.brief = {'run_id':self.run_id,'repo':str(self.repo),'base_sha':self.base,
            'participants':{role:{'account':str(self.root),'executable':'/usr/bin/true','model':'gpt-6.1-sol','effort':'medium'} for role in ('worker','qa')},
            'tasks':[{ 'id':t.id,'allowed_files':['a.py'],'acceptance':['Output is correct'],
                      'tests':['python a.py'],'dependencies':[]} for t in snapshot.tasks]}
        self.patches = [patch.object(launch,'Session',return_value=self.session),
                        patch.object(launch,'role_context',return_value='Worker/QA role. No main merges.'),
                        patch.object(launch,'create_gossip',return_value={'gossip':'owned-gossip','nickname':'main','pubkey':'main-key'}),
                        patch.object(launch,'start_monitor',return_value=55)]
        for p in self.patches:p.start();self.addCleanup(p.stop)

    def start(self):
        return launch.launch(self.store,self.run_id,self.brief,confirmed=True,api=self.api)

    def test_explicit_brief_creates_two_worktrees_and_one_tab_once(self):
        run = self.start()
        self.assertEqual(sum(a[:2] == ('tab','create') for a in self.api.calls),1)
        self.assertEqual(sum(a[:2] == ('pane','split') for a in self.api.calls),1)
        for role in ('worker','qa'):
            participant = run['participants'][role]
            self.assertEqual(git(participant['worktree'],'rev-parse','HEAD'),self.base)
        self.assertNotEqual(run['participants']['worker']['worktree'],run['participants']['qa']['worktree'])
        self.assertEqual(git(self.repo,'rev-parse','HEAD'),self.base)
        with self.assertRaisesRegex(RuntimeError,'already|inspect'):self.start()
        self.assertEqual(sum(a[:2] == ('tab','create') for a in self.api.calls),1)

    def test_interrupted_creation_preserves_intent_and_refuses_second_tab(self):
        self.api.fail = ('tab','create')
        with self.assertRaises(RuntimeError):self.start()
        retained = self.store.load(self.run_id)
        self.assertEqual(retained['phase'],'blocked')
        self.assertIn('tab',retained['operation'])
        self.api.fail = None
        with self.assertRaises(RuntimeError):self.start()
        self.assertEqual(sum(a[:2] == ('tab','create') for a in self.api.calls),1)

    def test_dirty_base_stale_selection_and_wrong_main_fail_before_resources(self):
        original = copy.deepcopy(self.run)
        (self.repo/'new.py').write_text('not committed')
        with self.assertRaisesRegex(RuntimeError,'clean'):self.start()
        (self.repo/'new.py').unlink()
        (self.repo/'TODO.md').write_text('## Next\n- [ ] Changed\n')
        with self.assertRaises(RuntimeError):self.start()
        git(self.repo,'restore','TODO.md')
        changed = copy.deepcopy(original);changed['main']['session']='other'
        self.store.save(changed)
        with self.assertRaisesRegex(RuntimeError,'identity'):self.start()
        self.assertFalse(self.api.calls)

    def test_invalid_dependencies_and_files_never_launch(self):
        for key,value in [('allowed_files',['../secret']),('allowed_files',['*']),('dependencies',['missing'])]:
            brief = copy.deepcopy(self.brief);brief['tasks'][0][key] = value
            with self.assertRaises(RuntimeError):launch.validate_brief(self.run,brief)
        self.brief['tasks'][0]['dependencies'] = [self.brief['tasks'][1]['id']]
        self.brief['tasks'][1]['dependencies'] = [self.brief['tasks'][0]['id']]
        with self.assertRaisesRegex(RuntimeError,'cycle'):launch.validate_brief(self.run,self.brief)

    def test_open_refuses_reused_terminal_or_moved_tab(self):
        run=self.start()
        self.api.panes['wd-test:p1']['terminal_id']='foreign'
        with self.assertRaises(RuntimeError):launch.open_run(run,self.api)
        self.assertNotIn(('tab','focus','tab'),self.api.calls)

    def test_confirmation_cannot_be_inferred(self):
        with self.assertRaisesRegex(RuntimeError,'confirmation'):
            launch.launch(self.store,self.run_id,self.brief,api=self.api)
        self.assertFalse(self.api.calls)

    def test_participant_launch_intent_prevents_duplicate_child_process(self):
        run=self.start()
        env={'HERDR_PANE_ID':run['resources']['worker']['pane_id']}
        with patch.dict(os.environ,env),patch.object(launch,'Herdr',return_value=self.api),patch.object(launch,'command',return_value=''),patch.object(launch.subprocess,'Popen') as popen:
            popen.return_value.wait.return_value=0
            popen.return_value.returncode=0
            launch.participant(self.store,self.run_id,'worker')
            with self.assertRaisesRegex(RuntimeError,'already|inspect'):
                launch.participant(self.store,self.run_id,'worker')
            self.assertEqual(popen.call_count,1)

    def test_replaced_worktree_cannot_be_checked_out_or_dispatched(self):
        run=self.start()
        path=Path(run['participants']['qa']['worktree'])
        (path/'.git').unlink()
        git(path,'init','-q')
        with self.assertRaisesRegex(RuntimeError,'repository'):
            launch.owned_worktree(run,'qa')

    def test_inherited_git_overrides_cannot_redirect_owned_repository_checks(self):
        foreign=self.root/'foreign';foreign.mkdir();git(foreign,'init','-q')
        with patch.dict(os.environ,{'GIT_DIR':str(foreign/'.git'),'GIT_WORK_TREE':str(foreign)}):
            self.assertEqual(launch.git(self.repo,'rev-parse','HEAD'),self.base)

    def test_launch_contract_requires_explicit_effort(self):
        del self.brief['participants']['worker']['effort']
        with self.assertRaisesRegex(RuntimeError,'effort'):
            self.start()
        self.assertFalse(self.api.calls)

    def test_participant_cli_overrides_model_effort_and_inherited_thread(self):
        self.brief['participants']['worker'].update(model='gpt-6.1-sol',effort='medium')
        run=self.start()
        self.assertEqual(run['participants']['worker']['effort'],'medium')
        env={'HERDR_PANE_ID':run['resources']['worker']['pane_id'],'CODEX_THREAD_ID':'foreign-thread',
             'CODEX_MODEL':'gpt-6-astra','CODEX_MODEL_REASONING_EFFORT':'xhigh'}
        with patch.dict(os.environ,env),patch.object(launch,'Herdr',return_value=self.api),patch.object(launch,'command',return_value=''),patch.object(launch.subprocess,'Popen') as popen:
            popen.return_value.wait.return_value=0;popen.return_value.returncode=0
            launch.participant(self.store,self.run_id,'worker')
            argv=popen.call_args.args[0]
            self.assertEqual(argv[argv.index('--model')+1],'gpt-6.1-sol')
            overrides=[argv[i+1] for i,item in enumerate(argv) if item=='-c']
            self.assertIn('model_reasoning_effort="medium"',overrides)
            self.assertNotIn('CODEX_THREAD_ID',popen.call_args.kwargs['env'])
            self.assertNotIn('CODEX_MODEL_REASONING_EFFORT',popen.call_args.kwargs['env'])
