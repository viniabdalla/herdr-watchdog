"""Spec #1 L119-123,164-165: observable leader lifecycle in an isolated PTY."""
from dataclasses import asdict, dataclass, replace
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_actions import FakeBinding
from test_artifacts_yazi import Terminal
from watchdog_app.store import Store


@dataclass
class Binding(FakeBinding):
    @property
    def key(self):
        return hashlib.sha256((self.kind+'\0'+self.account+'\0'+self.session).encode()).hexdigest()


SCRIPT = '''import sys,json
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,sys.argv[3])
from test_leader_link import Binding
from watchdog_app import bindings,curate
repo=Path(sys.argv[1])
def candidates():return [Binding(**b) for b in json.loads((repo/'live.json').read_text())],[]
def verify(b,**kw):
 if b not in candidates()[0]:raise RuntimeError('identity changed')
 return {'agent_status':'idle'}
bindings.engine=lambda:SimpleNamespace(Binding=Binding,verify=verify)
bindings.discover=lambda repo:candidates()
bindings.project_for=lambda b:repo
curate.latest_reply=lambda b:None
from watchdog_app.tasks_ui import run
run(repo,Path(sys.argv[2]))
'''


class LeaderLinkTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name)
        (self.repo/'TODO.md').write_text('## Next\n- [ ] A\n- [ ] B\n')
        self.old = Binding(pid=os.getpid())
        self.store = Store(self.repo/'state')
        self.store.save(self.old, self.store.load(self.old, self.repo))
        self.file = self.store.root/(self.old.key+'.json')
        self.live(self.old)
        herdr = self.repo/'herdr'
        herdr.write_text('''#!/usr/bin/env python3
import sys,json
from pathlib import Path
root=Path(__file__).parent
args=sys.argv[1:]
with (root/'commands.jsonl').open('a') as f:f.write(json.dumps(args)+'\\n')
live=json.loads((root/'live.json').read_text())
b=next((b for b in live if len(args)>2 and b['pane']==args[2]),live[0])
print(json.dumps({'result':{'pane':{'pane_id':b['pane'],'terminal_id':b['terminal']}}}))
''')
        herdr.chmod(0o755)
        self.env = dict(os.environ, TERM='xterm-256color', WATCHDOG_STATE_DIR=str(self.store.root),
                        XDG_STATE_HOME=str(self.repo/'xdg'), HERDR_BIN_PATH=str(herdr))
        self.env.pop('WATCHDOG_FULL_CONTROLS', None)
        for kind, prefix in [('claude','.claude'),('codex','.agents')]:
            folder=self.repo/prefix/'skills/to-spec'; folder.mkdir(parents=True)
            (folder/'SKILL.md').write_text('fixture')

    def live(self, *actors):
        (self.repo/'live.json').write_text(json.dumps([asdict(b) for b in actors]))

    def open(self, actor=None):
        if actor:
            self.old=actor; self.store.save(actor,self.store.load(actor,self.repo))
            self.file=self.store.root/(actor.key+'.json'); self.live(actor)
        terminal=Terminal(['python3','-B','-c',SCRIPT,str(self.repo),str(self.file),str(Path(__file__).parent)], self.env)
        self.addCleanup(terminal.close)
        self.wait(terminal,'Despachar p')
        return terminal

    def wait(self, terminal, text):
        self.assertTrue(terminal.wait_for(text),terminal.output.decode(errors='replace'))

    def test_clear_same_pane_same_process_follows_silently_for_both_harnesses(self):
        # Spec #1 L119,164: /clear retains process and terminal, changes session.
        for kind in ('codex','claude'):
            with self.subTest(kind=kind):
                old=replace(self.old,kind=kind,session='old-'+kind)
                t=self.open(old)
                new=replace(old,session='fresh-'+kind)
                self.live(new); t.output=b''
                self.wait(t,new.session[:8])
                self.assertNotIn(b'Harness alterado',t.output)
                self.assertNotIn(b'identity changed',t.output)
                source=json.loads(self.file.read_text())
                self.assertEqual(source['ownership'],'released')
                target=json.loads(Path(source['successor_binding_file']).read_text())
                self.assertEqual(target['binding'],asdict(new))
                t.close()

    def test_harness_change_updates_skill_prefix_and_warns(self):
        # Spec #1 L120,142,165: prefix is refreshed from the verified harness.
        t=self.open(replace(self.old,pid=99999999))
        self.wait(t,'$to-spec')
        new=replace(self.old,kind='claude',session='claude-new',pid=99999998)
        self.live(new); t.output=b''
        self.wait(t,'/to-spec'); self.wait(t,'Harness alterado: codex → claude')

    def test_other_pane_live_predecessor_or_changed_terminal_are_not_followed(self):
        # Spec #1 L144,190 and T10 acceptance: explicit Religar for ambiguous moves.
        for candidate in (replace(self.old,session='other',pane='project:p9'),
                          replace(self.old,session='other',pid=99999998),
                          replace(self.old,session='other',terminal='replacement')):
            self.live(self.old)
            t=self.open()
            self.live(candidate);t.output=b''
            # Trigger verification through preview; it must refuse the new identity.
            os.write(t.master,b'G')
            self.wait(t,'unavailable')
            self.assertEqual(json.loads(self.file.read_text())['binding'],asdict(self.old))
            t.close()

    def test_religar_selects_workspace_agent_and_resends_existing_group_only_after_confirm(self):
        # Spec #1 L121,123,165: one explicit choice; group/meta stays intact.
        t=self.open()
        new=replace(self.old,session='chosen-new',pane='project:p9',terminal='new-terminal',pid=99999998)
        outside=replace(new,pane='other:p1',workspace='other',session='outside')
        self.live(new,outside)
        from watchdog_app import long_run
        group={'members':['title:A','title:B'],'base':'abc','integration_branch':'integration'}
        with patch.dict(os.environ,self.env):
            from watchdog_app.store import atomic
            atomic(long_run.path_for(self.repo),group)
        os.write(t.master,b'L')
        self.wait(t,'Religar · escolher líder'); self.wait(t,'project:p9')
        self.assertNotIn(b'other:p1',t.output)
        os.write(t.master,b'\r')
        self.wait(t,'Líder ligado');self.wait(t,'chosen-n')
        os.write(t.master,b'G')
        self.wait(t,'Reenviar meta do grupo'); self.wait(t,'Concluir somente')
        os.write(t.master,b'\x1b'); self.wait(t,'Cancelled')
        commands=(self.repo/'commands.jsonl').read_text()
        self.assertNotIn('send-text',commands)
        os.write(t.master,b'Gy');self.wait(t,'Meta reenviada')
        commands=[json.loads(line) for line in (self.repo/'commands.jsonl').read_text().splitlines()]
        sends=[c for c in commands if c[:2]==['pane','send-text']]
        self.assertEqual(len(sends),1);self.assertEqual(sends[0][2],new.pane)
        self.assertIn('/goal Concluir somente',sends[0][3])
        with patch.dict(os.environ,self.env):self.assertEqual(long_run.record(self.repo),group)

    def test_reopened_panel_keeps_religar_available_for_an_unavailable_leader(self):
        # Spec #1 L121,144,190: no automatic move, but explicit Religar still works.
        old=replace(self.old,pid=99999999)
        self.old=old;self.store.save(old,self.store.load(old,self.repo))
        self.file=self.store.root/(old.key+'.json')
        new=replace(old,session='restart-new',pane='project:p9',terminal='new-terminal')
        self.live(new)
        t=self.open()
        os.write(t.master,b'L');self.wait(t,'Religar · escolher líder')
        os.write(t.master,b'\r');self.wait(t,'Líder ligado')

    def test_same_session_resumed_in_another_pane_is_not_followed_automatically(self):
        # Spec #1 L190 and T10 acceptance: even same session needs explicit Religar.
        from types import SimpleNamespace
        from watchdog_app.actions import Session
        old=replace(self.old,pid=99999999)
        self.store.save(old,self.store.load(old,self.repo))
        new=replace(old,pane='project:p9',terminal='new-terminal',pid=99999998)
        def verify(b):
            if b!=new:raise RuntimeError('old is gone')
            return {}
        runtime=SimpleNamespace(Binding=Binding,verify=verify)
        with patch('watchdog_app.bindings.engine',return_value=runtime), \
             patch('watchdog_app.bindings.discover',return_value=([new],[])), \
             patch('watchdog_app.bindings.project_for',return_value=self.repo):
            with self.assertRaises(RuntimeError):Session.for_panel(self.file,self.repo)
        self.assertEqual(json.loads(self.file.read_text())['binding'],asdict(old))

    def test_resend_refuses_a_group_changed_since_preview(self):
        # Spec #1 L123,151: confirmation refers to the current group, never an old one.
        from types import SimpleNamespace
        from watchdog_app.actions import Session
        from watchdog_app import dispatch, long_run
        from watchdog_app.store import atomic
        runtime=SimpleNamespace(Binding=Binding,verify=lambda b:{})
        with patch.dict(os.environ,self.env), patch('watchdog_app.bindings.engine',return_value=runtime), \
             patch('watchdog_app.bindings.project_for',return_value=self.repo):
            atomic(long_run.path_for(self.repo),{'members':['title:A']})
            session=Session(self.file,self.repo)
            offer=dispatch.resend_preview(session)
            atomic(long_run.path_for(self.repo),{'members':['title:A','title:B']})
            with self.assertRaisesRegex(RuntimeError,'grupo mudou'):dispatch.resend(session,offer)
        self.assertFalse((self.repo/'commands.jsonl').exists())

    def test_religar_can_explicitly_move_the_same_conversation(self):
        # Spec #1 L121,190: explicit selection permits a pane move of the same session.
        t=self.open()
        new=replace(self.old,pane='project:p9',terminal='new-terminal',pid=99999998)
        self.live(new)
        os.write(t.master,b'L');self.wait(t,'Religar · escolher líder')
        os.write(t.master,b'\r');self.wait(t,'Líder ligado')
        self.assertEqual(json.loads(self.file.read_text())['binding'],asdict(new))
