"""Real temporary Git/remotes and Store; native model, Herdr and queue simulated."""
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import patch

from test_actions import FakeBinding
from watchdog_app import bindings, clean_sessions as clean
from watchdog_app.actions import Session
from watchdog_app.store import Store


def git(repo,*args):
    return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.STDOUT,text=True).strip()


class Binding(FakeBinding):
    @property
    def key(self):
        import hashlib
        return hashlib.sha256((self.kind+'\0'+self.account+'\0'+self.session).encode()).hexdigest()


class NativeSimulation:
    """Controlled external boundary; no production actors or queue deliveries."""
    Binding=Binding
    def __init__(self,repo):
        self.repo=repo;self.actors={};self.deliveries=[];self.fail_queue=False
    def verify(self,binding):
        if self.actors.get(binding.session)!=asdict(binding):raise RuntimeError('replaced native identity')
        return {'agent_status':'idle'}
    def candidates(self):return [FakeBinding(**b) for b in self.actors.values()],[]
    def queue(self,binding,text):
        self.verify(binding);self.deliveries.append((binding.session,text))
        if self.fail_queue:raise RuntimeError('simulated uncertain delivery')
        return str(uuid.uuid4())


class HerdrSimulation:
    def __init__(self):self.calls=[];self.fail=None
    def checked(self,pane):return pane
    def call(self,*args):
        self.calls.append(args)
        if self.fail==args[:2]:raise RuntimeError('simulated Herdr uncertainty')
        if args[:2]==('pane','split'):
            return {'pane':{'pane_id':'project:new','terminal_id':'new-terminal','workspace_id':'project','tab_id':'project:tab'}}
        return {}


class CleanSessionsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.repo=self.root/'repo';self.repo.mkdir()
        git(self.repo,'init','-b','main');git(self.repo,'config','user.email','test@example.test');git(self.repo,'config','user.name','Test')
        (self.repo/'TODO.md').write_text('## Next\n- [ ] Unfinished\n');(self.repo/'owned.py').write_text('old\n')
        git(self.repo,'add','.');git(self.repo,'commit','-m','base')
        self.remote=self.root/'remote.git';git(self.root,'init','--bare',str(self.remote))
        git(self.repo,'remote','add','origin',str(self.remote));git(self.repo,'push','-u','origin','main')
        self.account=self.root/'account';self.account.mkdir()
        self.old=Binding(session=str(uuid.uuid4()),account=str(self.account),history=str(self.root/'old.jsonl'))
        self.new=Binding(session=str(uuid.uuid4()),account=str(self.account),history=str(self.root/'new.jsonl'),pane='project:new',terminal='new-terminal',pid=456,started='789')
        for b in (self.old,self.new):Path(b.history).touch()
        env=patch.dict(os.environ,{'WATCHDOG_STATE_DIR':str(self.root/'state')});env.start();self.addCleanup(env.stop)
        self.runtime=NativeSimulation(self.repo);self.runtime.actors[self.old.session]=asdict(self.old)
        self.api=HerdrSimulation();self.store=Store(self.root/'state')
        self.file=self.store.root/(self.old.key+'.json')
        self.panes={r:{'pane_id':r,'terminal_id':r+'-terminal'} for r in ('tasks','progress','artifacts','files')}
        self.state={'repo':str(self.repo),'binding':asdict(self.old),'panes':self.panes,'yazi_client_id':'keep-client','layout':2,'binding_file':str(self.file)}
        self.file.parent.mkdir();self.file.write_text(json.dumps(self.state))
        for p in (patch.object(bindings,'engine',return_value=self.runtime),patch.object(bindings,'project_for',return_value=self.repo),patch.object(bindings,'discover',side_effect=lambda repo:self.runtime.candidates())):
            p.start();self.addCleanup(p.stop)
        self.session=Session(self.file,self.repo)
        self.policy={'remote':'origin','branch':'main','owned_paths':['TODO.md','owned.py'],'integrate':[],
                     'executable':'/usr/bin/true','model':'gpt-6.1-sol','effort':'medium'}

    def request(self):return clean.request(self.session,self.policy,confirmed=True,store=self.store)
    def tick(self):return clean.advance(self.store,self.op['operation_id'],api=self.api)
    def reply(self,binding,kind,**extra):
        op=clean.load(self.store,self.op['operation_id'])
        payload={'operation_id':op['operation_id'],'token':op['tokens'][kind],'kind':kind,**extra}
        with Path(binding.history).open('a') as f:
            f.write(json.dumps({'type':'event_msg','payload':{'type':'task_complete','turn_id':str(uuid.uuid4()),'last_agent_message':'WATCHDOG_CLEAN '+json.dumps(payload)}})+'\n')
    def prepared(self):
        self.reply(self.old,'prepared',todo_reconciled=True,memory_handoff_id=str(uuid.uuid4()),summary='Continue pending work',open_questions=['Question'],unfinished_tasks=['Unfinished'],next_steps=['Next'],references=[])
    def to_receipt(self):
        self.op=self.request();self.prepared();self.tick() # verified preparation, commit/integrate/push checkpoint
        self.tick() # split and startup command
        self.runtime.actors[self.new.session]=asdict(self.new)
        clean.atomic(clean.folder(self.store,self.op['operation_id'])/'leader-proof.json',{'native':asdict(self.new)})
        return self.tick() # native verification and bounded continuation delivery
    def receive(self):
        op=clean.load(self.store,self.op['operation_id'])
        self.reply(self.new,'received',checkpoint=op['checkpoint'],handoff_sha256=op['handoff_sha256'],memory_handoff_id=op['preparation']['memory_handoff_id'])
        return self.tick()

    def test_requires_explicit_confirmation_and_requests_exact_current_leader(self):
        with self.assertRaisesRegex(RuntimeError,'confirmation'):clean.request(self.session,self.policy,store=self.store)
        before=(self.repo/'TODO.md').read_bytes();self.op=self.request()
        self.assertEqual(self.op['state'],'pending')
        self.assertEqual(self.runtime.deliveries[0][0],self.old.session)
        self.assertIn('memory_handoff_begin',self.runtime.deliveries[0][1]);self.assertIn(str(self.repo),self.runtime.deliveries[0][1])
        self.assertEqual((self.repo/'TODO.md').read_bytes(),before)
        with self.assertRaisesRegex(RuntimeError,'existing|pending'):self.request()

    def test_full_flow_commits_pushes_receives_releases_and_rebinds_orchestrate(self):
        (self.repo/'owned.py').write_text('new\n')
        before=(self.repo/'TODO.md').read_bytes()
        op=self.to_receipt();self.assertEqual(op['state'],'pending');self.assertEqual(op['stage'],'receipt')
        self.assertEqual(git(self.remote,'rev-parse','refs/heads/main'),op['checkpoint'])
        self.assertNotEqual(op['checkpoint'],op['base_sha']);self.assertEqual(self.runtime.deliveries[-1][0],self.new.session)
        self.assertEqual(json.loads(self.file.read_text())['binding'],asdict(self.old),'queue is not receipt')
        self.receive();op=clean.load(self.store,self.op['operation_id']);self.assertEqual(op['state'],'received')
        self.assertEqual(self.runtime.deliveries[-1][0],self.old.session)
        self.reply(self.old,'released',checkpoint=op['checkpoint'],successor=self.new.session)
        op=self.tick();self.assertEqual(op['state'],'released')
        successor=Session(op['new_binding_file'],self.repo)
        self.assertEqual(successor.binding.session,self.new.session)
        new_state=json.loads(Path(op['new_binding_file']).read_text());old_state=json.loads(self.file.read_text())
        self.assertEqual(new_state['panes'],self.panes);self.assertEqual(new_state['yazi_client_id'],'keep-client');self.assertEqual(new_state['layout'],2)
        self.assertEqual(old_state['panes'],{});self.assertEqual(old_state['successor_binding_file'],op['new_binding_file'])
        from watchdog_app.mission import request,RunStore
        from watchdog_app.todo import Snapshot
        snap=Snapshot.read(self.repo)
        run=request(successor,snap,{snap.tasks[0].id},confirmed=True,store=RunStore(self.root/'new-runs'))
        self.assertEqual(run['main'],asdict(self.new));self.assertEqual(self.runtime.deliveries[-1][0],self.new.session)
        self.assertEqual((self.repo/'TODO.md').read_bytes(),before)
        count=len(self.api.calls);self.tick();self.assertEqual(len(self.api.calls),count)

    def test_only_explicit_approved_branch_is_integrated_using_real_remote(self):
        git(self.repo,'checkout','-b','approved');(self.repo/'owned.py').write_text('approved\n');git(self.repo,'commit','-am','approved')
        candidate=git(self.repo,'rev-parse','HEAD');git(self.repo,'checkout','main')
        self.policy['integrate']=['approved'];self.op=self.request();self.prepared();op=self.tick()
        self.assertEqual(op['checkpoint'],candidate);self.assertEqual(git(self.remote,'rev-parse','main'),candidate)

    def test_dirty_unowned_or_staged_files_block_without_commit_or_push(self):
        for staged in (False,True):
            with self.subTest(staged=staged):
                (self.repo/'foreign').write_text('not ours')
                if staged:git(self.repo,'add','foreign')
                self.op=self.request();self.prepared();op=self.tick()
                self.assertEqual(op['state'],'partial');self.assertIn('unowned',op['problem'])
                self.assertEqual(git(self.repo,'rev-parse','HEAD'),op['base_sha'])
                self.assertEqual(self.api.calls,[])
                # Fresh fixture operation after explicit removal of blocked operation, not automatic recovery.
                clean.path(self.store,self.op['operation_id']).unlink();git(self.repo,'reset');(self.repo/'foreign').unlink()

    def test_missing_memory_handoff_is_partial_not_false_transferred(self):
        self.op=self.request();self.reply(self.old,'prepared',todo_reconciled=True,memory_handoff_id=None)
        op=self.tick();self.assertEqual(op['state'],'partial');self.assertIn('ai-memory',op['problem']);self.assertFalse(self.api.calls)

    def test_queue_uncertainty_and_split_uncertainty_are_never_retried(self):
        self.runtime.fail_queue=True;self.op=self.request();self.assertEqual(self.op['state'],'partial')
        count=len(self.runtime.deliveries);self.tick();self.assertEqual(len(self.runtime.deliveries),count)
        clean.path(self.store,self.op['operation_id']).unlink();self.runtime.fail_queue=False
        self.op=self.request();self.prepared();self.tick();self.api.fail=('pane','split')
        op=self.tick();self.assertEqual(op['state'],'partial');count=len(self.api.calls)
        self.tick();self.assertEqual(len(self.api.calls),count)

    def test_stale_checkpoint_tampered_receipt_or_replaced_native_cannot_rebind(self):
        self.to_receipt();self.reply(self.new,'received',checkpoint='0'*40,handoff_sha256='tampered',memory_handoff_id='wrong')
        op=self.tick();self.assertEqual(op['state'],'partial');self.assertEqual(json.loads(self.file.read_text())['binding'],asdict(self.old))

    def test_foreign_account_successor_and_changed_branch_or_remote_are_rejected(self):
        self.op=self.request();self.prepared();self.tick();self.tick()
        bad=asdict(self.new);bad['account']='/foreign';self.runtime.actors[self.new.session]=bad
        clean.atomic(clean.folder(self.store,self.op['operation_id'])/'leader-proof.json',{'native':bad})
        self.assertEqual(self.tick()['state'],'partial')

    def test_active_native_run_and_legacy_ledger_stay_byte_untouched(self):
        from watchdog_app.mission import RunStore
        rs=RunStore(self.store.root/'runs');legacy={'id':str(uuid.uuid4()),'repo':str(self.repo),'phase':'active','created':0,'transport':{'kind':'gossip'}}
        rs.save(legacy);before=rs.path(legacy['id']).read_bytes();self.op=self.request()
        self.assertEqual(rs.path(legacy['id']).read_bytes(),before)
        clean.path(self.store,self.op['operation_id']).unlink()
        native=dict(legacy,id=str(uuid.uuid4()),transport={'kind':'native'});rs.save(native)
        with self.assertRaisesRegex(RuntimeError,'native run'):self.request()
        self.assertEqual(rs.path(legacy['id']).read_bytes(),before)

    def test_checkpoint_changed_after_delivery_blocks_release_and_preserves_panels(self):
        self.to_receipt();git(self.repo,'commit','--allow-empty','-m','unapproved concurrent head')
        op=self.tick();self.assertEqual(op['state'],'partial');self.assertIn('Checkpoint',op['problem'])
        self.assertEqual(json.loads(self.file.read_text())['panes'],self.panes)

    def test_duplicate_successor_receipt_is_visible_and_does_not_release(self):
        op=self.to_receipt()
        fields=dict(checkpoint=op['checkpoint'],handoff_sha256=op['handoff_sha256'],memory_handoff_id=op['preparation']['memory_handoff_id'])
        self.reply(self.new,'received',**fields);self.reply(self.new,'received',**fields)
        op=self.tick();self.assertEqual(op['state'],'partial');self.assertIn('Duplicate',op['problem'])
        self.assertNotIn('release',op['effects'])

    def test_receipt_in_file_or_noncompleted_native_message_is_not_acknowledgement(self):
        self.to_receipt()
        (self.root/'receipt.json').write_text('{"kind":"received"}')
        with Path(self.new.history).open('a') as f:f.write(json.dumps({'type':'response_item','payload':{'role':'assistant','content':'received'}})+'\n')
        op=self.tick();self.assertEqual(op['stage'],'receipt');self.assertNotIn('receiver_receipt',op)

    def test_replaced_native_or_foreign_project_after_delivery_cannot_release(self):
        self.to_receipt();self.runtime.actors[self.new.session]['started']='recycled'
        self.assertEqual(self.tick()['state'],'partial');self.assertEqual(json.loads(self.file.read_text())['panes'],self.panes)

    def test_unavailable_push_retains_commit_and_never_splits_or_retries(self):
        (self.repo/'owned.py').write_text('owned new content\n')
        self.op=self.request();self.prepared()
        hook=self.remote/'hooks/pre-receive';hook.write_text('#!/bin/sh\nexit 1\n');hook.chmod(0o755)
        op=self.tick();self.assertEqual(op['state'],'partial');self.assertEqual(op['effects']['push']['state'],'uncertain')
        self.assertNotEqual(git(self.repo,'rev-parse','HEAD'),op['base_sha']);self.assertEqual(self.api.calls,[])
        hook.unlink();again=self.tick();self.assertEqual(again['effects']['push']['state'],'uncertain')
        self.assertEqual(git(self.remote,'rev-parse','main'),op['base_sha'])

    def test_changed_approved_integration_ref_is_not_merged(self):
        git(self.repo,'branch','approved');self.policy['integrate']=['approved'];self.op=self.request()
        git(self.repo,'checkout','approved');git(self.repo,'commit','--allow-empty','-m','changed approved ref');git(self.repo,'checkout','main')
        self.prepared();op=self.tick();self.assertEqual(op['state'],'partial');self.assertIn('integration branch changed',op['problem'])
        self.assertEqual(git(self.repo,'rev-parse','HEAD'),op['base_sha'])

    def test_startup_uncertainty_keeps_created_pane_and_does_not_repeat_run(self):
        self.op=self.request();self.prepared();self.tick();self.api.fail=('pane','run')
        op=self.tick();self.assertEqual(op['state'],'partial');self.assertIn('pane',op)
        calls=list(self.api.calls);self.tick();self.assertEqual(self.api.calls,calls)

    def test_changed_push_remote_before_preparation_is_blocked(self):
        self.op=self.request();self.prepared();git(self.repo,'remote','set-url','origin',str(self.root/'foreign.git'))
        op=self.tick();self.assertEqual(op['state'],'partial');self.assertIn('remote changed',op['problem']);self.assertFalse(self.api.calls)

    def test_continuation_tampering_blocks_exact_thread_delivery(self):
        self.op=self.request();self.prepared();self.tick();self.tick()
        self.runtime.actors[self.new.session]=asdict(self.new)
        clean.atomic(clean.folder(self.store,self.op['operation_id'])/'leader-proof.json',{'native':asdict(self.new)})
        clean.atomic(clean.folder(self.store,self.op['operation_id'])/'continuation.json',{'tampered':True})
        op=self.tick();self.assertEqual(op['state'],'partial');self.assertNotIn('continuation',op['effects'])

    def test_rebind_failure_relinquishes_old_ownership_and_never_retries(self):
        self.to_receipt();self.receive();op=clean.load(self.store,self.op['operation_id'])
        self.reply(self.old,'released',checkpoint=op['checkpoint'],successor=self.new.session)
        with patch.object(self.store,'save',side_effect=OSError('simulated Store write interruption')):
            op=self.tick()
        self.assertEqual(op['state'],'partial');self.assertEqual(json.loads(self.file.read_text())['ownership'],'transferring')
        with self.assertRaisesRegex(RuntimeError,'released'):self.session.verify()
        self.assertEqual(self.tick()['effects']['rebind']['state'],'sending')

    def test_pushurl_is_verified_instead_of_unrelated_fetch_remote(self):
        push_remote=self.root/'push.git';git(self.root,'clone','--bare',str(self.remote),str(push_remote))
        git(self.repo,'remote','set-url','--push','origin',str(push_remote))
        (self.repo/'owned.py').write_text('push destination only\n')
        self.op=self.request();self.prepared();op=self.tick()
        self.assertEqual(op['state'],'pending',op.get('problem'))
        self.assertEqual(op['checkpoint'],git(push_remote,'rev-parse','main'))
        self.assertEqual(git(self.remote,'rev-parse','main'),op['base_sha'])

    def test_fresh_wrapper_sanitizes_thread_environment_and_restores_terminal(self):
        self.op=self.request();self.prepared();self.tick();self.tick()
        self.runtime.actors[self.new.session]=asdict(self.new)
        child=SimpleNamespace(pid=self.new.pid,poll=lambda:None,wait=lambda:0)
        from watchdog_app import mission_terminal
        with patch.dict(os.environ,{'CODEX_THREAD_ID':'must-not-inherit','AI_MEMORY_SESSION_ID':'old','OPENAI_API_KEY':'secret'}), \
             patch.object(clean,'Herdr',return_value=self.api), \
             patch.object(clean.subprocess,'Popen',return_value=child) as popen, \
             patch.object(mission_terminal,'TerminalLease') as terminal:
            self.assertEqual(clean.leader(self.store,self.op['operation_id']),0)
        launch_env=popen.call_args.kwargs['env']
        self.assertNotIn('CODEX_THREAD_ID',launch_env);self.assertNotIn('AI_MEMORY_SESSION_ID',launch_env);self.assertNotIn('OPENAI_API_KEY',launch_env)
        self.assertEqual(launch_env['CODEX_HOME'],self.old.account)
        self.assertIn(self.policy['model'],popen.call_args.args[0]);terminal.return_value.restore.assert_called_once()
        proof=clean.handoff.read_json(clean.folder(self.store,self.op['operation_id'])/'leader-proof.json')
        self.assertEqual(proof['native'],asdict(self.new))
        with patch.object(clean,'Herdr',return_value=self.api):
            with self.assertRaises(FileExistsError):clean.leader(self.store,self.op['operation_id'])

    def test_wrapped_frontend_exit_keeps_pane_and_restores_terminal(self):
        self.op=self.request();self.prepared();self.tick();self.tick()
        child=SimpleNamespace(pid=456,poll=lambda:1)
        from watchdog_app import mission_terminal
        with patch.object(clean,'Herdr',return_value=self.api),patch.object(clean.subprocess,'Popen',return_value=child),patch.object(mission_terminal,'TerminalLease') as terminal:
            with self.assertRaisesRegex(RuntimeError,'exited'):clean.leader(self.store,self.op['operation_id'])
        terminal.return_value.restore.assert_called_once()
        self.assertTrue(clean.folder(self.store,self.op['operation_id']).joinpath('leader-error.json').exists())
        self.assertFalse(any('kill' in c or 'close' in c for c in self.api.calls))

    def test_pending_cleanup_blocks_new_orchestrate_and_send_until_transfer(self):
        from watchdog_app.mission import request,RunStore
        from watchdog_app.todo import Snapshot
        self.op=self.request();snap=Snapshot.read(self.repo)
        count=len(self.runtime.deliveries)
        with self.assertRaisesRegex(RuntimeError,'Clean sessions'):
            request(self.session,snap,{snap.tasks[0].id},confirmed=True,store=RunStore(self.store.root/'runs'))
        with self.assertRaisesRegex(RuntimeError,'Clean sessions'):
            self.session.dispatch(snap,{snap.tasks[0].id})
        self.assertEqual(len(self.runtime.deliveries),count)

    def test_explicit_leader_blocker_is_visible_without_git_side_effects(self):
        self.op=self.request();value={'operation_id':self.op['operation_id'],'token':self.op['tokens']['prepared'],'kind':'blocked','reason':'ai-memory MCP unavailable'}
        with Path(self.old.history).open('a') as f:f.write(json.dumps({'type':'event_msg','payload':{'type':'task_complete','last_agent_message':clean.PREFIX+json.dumps(value)}})+'\n')
        op=self.tick();self.assertEqual(op['state'],'blocked');self.assertIn('ai-memory',op['problem']);self.assertFalse(self.api.calls)
