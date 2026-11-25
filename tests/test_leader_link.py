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
bindings.engine=lambda:SimpleNamespace(Binding=Binding,verify=verify, processes=lambda:[])
bindings.discover=lambda repo:candidates()
bindings.project_for=lambda b:repo
curate.latest_reply=lambda b:None
from watchdog_app import relink_delivery,leader_link
relink_delivery.choices=lambda session:leader_link.choices(session)
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
        from pane_submission_fixture import IDLE_SCRIPT
        herdr.write_text(IDLE_SCRIPT)
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
        self.wait(terminal, 'Mostrar ações')
        os.write(terminal.master, b'?')
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

    def test_religar_selects_workspace_claude_and_resends_existing_group_only_after_confirm(self):
        # Spec #1 L121,123,165: one explicit choice; group/meta stays intact.
        t=self.open(replace(self.old,kind='claude'))
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
        with patch.dict(os.environ,self.env):
            value=long_run.record(self.repo)
            self.assertEqual(value, dict(group,goal={'kind':'claude','account':new.account,'session':'chosen-new'}))

    def test_reopened_panel_keeps_religar_available_for_an_unavailable_leader(self):
        # Spec #1 L121,144,190: no automatic move, but explicit Religar still works.
        old=replace(self.old,pid=99999999,kind='claude')
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
        t=self.open(replace(self.old,kind='claude'))
        new=replace(self.old,pane='project:p9',terminal='new-terminal',pid=99999998)
        self.live(new)
        os.write(t.master,b'L');self.wait(t,'Religar · escolher líder')
        os.write(t.master,b'\r');self.wait(t,'Líder ligado')
        self.assertEqual(json.loads(self.file.read_text())['binding'],asdict(new))

    def test_resend_uses_each_member_mode_and_rejects_an_empty_group(self):
        # Spec #1 L87,123,138,151 and T5/T10: /clear must preserve identity-scoped modes.
        from types import SimpleNamespace
        from watchdog_app.actions import Session
        from watchdog_app import dispatch, long_run
        from watchdog_app.store import atomic
        runtime=SimpleNamespace(Binding=Binding,verify=lambda b:{})
        with patch.dict(os.environ,self.env), patch('watchdog_app.bindings.engine',return_value=runtime), \
             patch('watchdog_app.bindings.project_for',return_value=self.repo):
            session=Session(self.file,self.repo)
            for modes, phrase in (({'title:A':'here','title:B':'here'},'Implementar nesta sessão'),
                                  ({'title:A':'here','title:B':'dispatch'},'Concluir'),
                                  ({},'Concluir')):
                group={'members':['title:A','title:B'],'modes':modes}
                atomic(long_run.path_for(self.repo),group)
                offer=dispatch.resend_preview(session)
                self.assertIn('/goal '+phrase+' somente',offer['prompt'])
                self.assertIn('modo por identidade no campo modes',offer['prompt'])
                if all(modes.get(key)=='here' for key in group['members']):
                    self.assertNotIn('Despache um executor por tarefa',offer['prompt'])
                else:
                    self.assertNotIn('Despache um executor por tarefa;',offer['prompt'])
                self.assertEqual(long_run.record(self.repo),group)
            atomic(long_run.path_for(self.repo),{'members':[]})
            with self.assertRaisesRegex(RuntimeError,'Não há grupo'):dispatch.resend_preview(session)
        self.assertFalse((self.repo/'commands.jsonl').exists())

    def test_existing_claude_codex_claude_cycle_keeps_progress_and_older_panels(self):
        # Spec #1 L120-123,165,180: explicit A->B->A with both agents alive, no redirect cycle.
        from types import SimpleNamespace
        from watchdog_app.actions import Session
        from watchdog_app.leader_link import connect
        from watchdog_app.session_progress import Progress
        from watchdog_app import long_run
        from watchdog_app.store import atomic
        from test_session_progress import claude_call, claude_result, codex_call, codex_result
        a=replace(self.old,kind='claude',session='A',history=str(self.repo/'a.jsonl'))
        b=replace(self.old,session='B',pane='project:p9',terminal='B-terminal',history=str(self.repo/'b.jsonl'))
        def history(path, records):
            Path(path).write_text(''.join(json.dumps(r)+'\n' for r in records))
        acall=claude_call(); aresult=claude_result()
        acall['sessionId']=aresult['sessionId']='A'
        history(a.history,[acall,aresult])
        bcall=codex_call(); bcall['payload']['arguments']=json.dumps({'plan':[{'step':'Codex work','status':'in_progress'}]})
        history(b.history,[bcall,codex_result()])
        live=[self.old,a,b]
        def verify(actor):
            if actor not in live:raise RuntimeError('identity changed')
            return {'agent_status':'idle'}
        runtime=SimpleNamespace(Binding=Binding,verify=verify)
        self.live(*live)
        with patch.dict(os.environ,self.env), patch('watchdog_app.bindings.engine',return_value=runtime), \
             patch('watchdog_app.bindings.discover',return_value=(live,[])), \
             patch('watchdog_app.bindings.project_for',return_value=self.repo):
            atomic(long_run.path_for(self.repo),{'members':['title:A'],'modes':{'title:A':'here'}})
            group=long_run.path_for(self.repo).read_bytes()
            origin=self.file
            session=Session(origin,self.repo)
            session=connect(session,a)
            afile=session.file
            progress=Progress(self.repo,afile)
            self.assertEqual(progress.poll().current,'Inspect fixtures')
            session=connect(session,b)
            bfile=session.file
            self.assertEqual(progress.poll().current,'Codex work')
            session=connect(session,a)
            self.assertEqual(session.file,afile)
            self.assertEqual(progress.poll().current,'Inspect fixtures')
            for file in (origin,afile,bfile):
                self.assertEqual(Session.for_panel(file,self.repo).binding,a)
            self.assertEqual(json.loads(afile.read_text())['ownership'],'active')
            self.assertNotIn('successor_binding_file',json.loads(afile.read_text()))
            self.assertEqual(json.loads(bfile.read_text())['ownership'],'released')
            self.assertEqual(long_run.path_for(self.repo).read_bytes(),group)
            # Repeat both directions: retired receipts must not form a loop.
            session=connect(session,b);session=connect(session,a)
            self.assertEqual(Session.for_panel(origin,self.repo).binding,a)
            self.assertEqual(progress.poll().current,'Inspect fixtures')

    def test_return_refuses_active_unrelated_or_tampered_ownership_without_writes(self):
        # Spec #1 L121,151: choosing a pane cannot steal another group's panel resources.
        from watchdog_app.herdr import Herdr
        from watchdog_app.store import atomic
        a=replace(self.old,kind='claude',session='A',pane='project:p9')
        b=replace(self.old,session='B',pane='project:p10')
        self.live(self.old,a,b)
        with patch.dict(os.environ,self.env):
            afile=Path(self.store.transfer(self.file,self.old,a,self.repo,'first',api=Herdr()))
            target=json.loads(self.file.read_text())
            cases=[dict(target,ownership='active'), dict(target,ownership='transferring'),
                   dict(target,repo=str(self.repo/'other')), dict(target,yazi_client_id='other-group'),
                   dict(target,outgoing_transfer_operation='tampered'),
                   dict(target,successor_binding_file=str(self.store.root/(b.key+'.json')))]
            for value in cases:
                atomic(self.file,value)
                before={p:p.read_bytes() for p in (afile,self.file)}
                with self.assertRaises((RuntimeError,OSError)):
                    self.store.transfer(afile,a,self.old,self.repo,'return',api=Herdr())
                self.assertEqual({p:p.read_bytes() for p in before},before)
            # An independent released group is not an ancestor, even in the same project.
            atomic(self.file,target)
            self.store.save(b,self.store.load(b,self.repo))
            bfile=self.store.root/(b.key+'.json')
            independent=json.loads(bfile.read_text()); independent.update(ownership='released',
                successor_binding_file=str(bfile),outgoing_transfer_operation='unrelated')
            atomic(bfile,independent)
            before={p:p.read_bytes() for p in (afile,self.file,bfile)}
            with self.assertRaises(RuntimeError):self.store.transfer(afile,a,b,self.repo,'return',api=Herdr())
            self.assertEqual({p:p.read_bytes() for p in before},before)

    def test_religar_existing_claude_panes_both_directions_in_terminal(self):
        # Spec #1 L120-122,165,180: prefix and explicit pane choice in both directions.
        a=replace(self.old,kind='claude',session='A-session')
        b=replace(self.old,kind='claude',session='B-session',pane='project:p9',terminal='B-terminal')
        t=self.open(a)
        self.live(a,b)
        self.wait(t,'/to-spec')
        t.output=b'';os.write(t.master,b'Lj\r')
        self.wait(t,'Líder ligado');self.wait(t,'B-sessio')
        t.output=b'';os.write(t.master,b'L');self.wait(t,'Religar · escolher líder')
        t.output=b'';os.write(t.master,b'\r');self.wait(t,'IN PROGRESS (0)')
        self.assertEqual(json.loads(self.file.read_text())['ownership'],'active')
        self.assertEqual(json.loads(self.file.read_text())['binding'],asdict(a))

    def test_failed_return_leaves_no_two_active_owners(self):
        # Spec #1 L121,151: an interrupted explicit return never gives both panes ownership.
        from types import SimpleNamespace
        from watchdog_app.actions import Session
        from watchdog_app.herdr import Herdr
        a=replace(self.old,kind='claude',session='A',pane='project:p9')
        self.live(self.old,a)
        with patch.dict(os.environ,self.env):
            afile=Path(self.store.transfer(self.file,self.old,a,self.repo,'first',api=Herdr()))
            with patch.object(self.store,'save',side_effect=OSError('simulated disk failure')):
                with self.assertRaisesRegex(OSError,'disk failure'):
                    self.store.transfer(afile,a,self.old,self.repo,'return',api=Herdr())
            self.assertEqual(json.loads(afile.read_text())['ownership'],'transferring')
            self.assertEqual(json.loads(self.file.read_text())['ownership'],'released')
            runtime=SimpleNamespace(Binding=Binding,verify=lambda b:{})
            with patch('watchdog_app.bindings.engine',return_value=runtime), \
                 patch('watchdog_app.bindings.project_for',return_value=self.repo):
                for file in (afile,self.file):
                    with self.assertRaises(RuntimeError):Session.for_panel(file,self.repo)
