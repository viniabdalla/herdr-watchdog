"""Religar spec L9,16-18,26,33,40: canonical project at every proof boundary."""
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_leader_link import Binding
from watchdog_app import relink, relink_delivery


class RelinkProjectTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix='wd project spaces ');self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name);self.repo=self.root/'project space';self.repo.mkdir()
        env=patch.dict(os.environ,WATCHDOG_STATE_DIR=str(self.root/'state'),XDG_STATE_HOME=str(self.root/'xdg'))
        env.start();self.addCleanup(env.stop)
        self.git('init','-q',str(self.repo))
        self.src=self.repo/'src space';self.src.mkdir()
        self.nested=self.src/'nested repo';self.nested.mkdir();self.git('init','-q',str(self.nested))
        self.git('-C',str(self.repo),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture','--allow-empty')
        self.worktree=self.repo/'other worktree';self.git('-C',str(self.repo),'worktree','add','-q','--detach',str(self.worktree))
        self.other=self.root/'other project';self.other.mkdir();self.git('init','-q',str(self.other))
        self.plain=self.root/'without git';self.plain.mkdir()
        self.b=Binding(account=str(self.root/'account'),history='')
        self.runtime=SimpleNamespace(Binding=Binding,process_info=lambda pid:asdict(self.b),processes=lambda:[asdict(self.b)])
        agent=dict(pane_id=self.b.pane,terminal_id=self.b.terminal,workspace_id=self.b.workspace,
                   agent='codex',agent_session=dict(kind='id',value=self.b.session))
        def call(*args):
            if args[:2]==('agent','get'):return {'agent':agent}
            if args[:2]==('agent','list'):return {'agents':[agent]}
            if args[:2]==('pane','process-info'):return {'process_info':{'foreground_processes':[{'pid':self.b.pid}]}}
            raise AssertionError(args)
        self.api=SimpleNamespace(call=call,checked=lambda pane:dict(pane,foreground_cwd=str(self.cwd)))
        self.cwd=self.src
        self.process=SimpleNamespace(environ=lambda:{'CODEX_HOME':self.b.account,'HERDR_PANE_ID':self.b.pane},
                                    cmdline=lambda:['codex'],name=lambda:'codex',cwd=lambda:str(self.cwd))
        for mock in (patch('watchdog_app.bindings.engine',return_value=self.runtime),
                     patch.dict('sys.modules',psutil=SimpleNamespace(Process=lambda pid:self.process,Error=OSError))):
            mock.start();self.addCleanup(mock.stop)

    def git(self,*args):
        subprocess.run(['git',*args],check=True,capture_output=True)

    def history(self):
        file=self.root/'history.jsonl'
        file.write_text(json.dumps({'type':'session_meta','payload':{'id':self.b.session,'cwd':str(self.cwd)}})+'\n'+
            json.dumps({'type':'response_item','timestamp':datetime.now(timezone.utc).isoformat(),
                'payload':{'type':'message','role':'assistant','phase':'commentary',
                           'content':[{'type':'output_text','text':'LU-proof'}]}})+'\n')
        return file

    def test_project_accepts_subdirectory_at_selection_process_and_history(self):
        # Spec L9,16-17,26: no literal cwd equality; pane/process/history all mean R.
        for repo,cwd in ((self.repo,self.src),(self.src,self.repo),(self.plain,self.plain)):
            with self.subTest(repo=repo,cwd=cwd):
                self.cwd=cwd
                relink_delivery.validate(self.b,repo,self.api)
                relink.process_proof(self.b,repo,self.runtime)
                relink._history_proof(self.history(),self.b.session,repo,'LU-proof',0)
                session=SimpleNamespace(repo=repo,binding=self.b)
                with patch('watchdog_app.leader_link.choices',return_value=[]),patch.object(relink_delivery,'Herdr',return_value=self.api):
                    self.assertEqual(relink_delivery.choices(session),[self.b])

    def test_other_projects_nested_repositories_and_worktrees_are_rejected(self):
        # Spec L16-17,33,36: descendants must not weaken project/worktree isolation.
        for cwd in (self.nested,self.worktree,self.other):
            with self.subTest(cwd=cwd):
                self.cwd=cwd
                with self.assertRaises(RuntimeError):relink_delivery.validate(self.b,self.repo,self.api)
                with self.assertRaises(RuntimeError):relink.process_proof(self.b,self.repo,self.runtime)
                with self.assertRaises(RuntimeError):relink._history_proof(self.history(),self.b.session,self.repo,'LU-proof',0)

    def test_missing_live_cwd_uses_canonical_binding_project_or_rejects_unknown(self):
        # Spec L9,16-17: preserve existing metadata fallback, fail closed if absent.
        self.api.checked=lambda pane:pane
        with patch('watchdog_app.bindings.project_for',return_value=self.src):
            relink_delivery.validate(self.b,self.repo,self.api)
        with patch('watchdog_app.bindings.project_for',return_value=None):
            with self.assertRaises(RuntimeError):relink_delivery.validate(self.b,self.repo,self.api)
