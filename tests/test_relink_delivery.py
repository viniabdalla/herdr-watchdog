"""Religar spec 2026-11-25 L16,19,32-37: isolated transport boundaries."""
from dataclasses import asdict
from contextlib import contextmanager
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from test_leader_link import Binding
from watchdog_app import pane_delivery as delivery


class FakeHerdr:
    session = None
    def __init__(self, binding):
        self.binding = binding
        self.status, self.draft = 'idle', ''
        self.sent, self.keys = [], []
        self.consume = True
    def call(self, *args):
        if args[:2] == ('agent', 'get'):
            b = self.binding
            return {'agent': dict(pane_id=b.pane, terminal_id=b.terminal, agent=b.kind,
                agent_status=self.status, agent_session=dict(kind='id', value=b.session))}
        if args[:2] == ('pane', 'send-text'):
            self.sent.append((args[2], args[3])); self.draft = args[3]
        elif args[:2] == ('pane', 'send-keys'):
            self.keys.append(args[3])
            if self.consume:self.draft = ''
        return {}
    def output(self, *args):
        return '› ' + self.draft + '\n'


class RelinkDeliveryTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.env=patch.dict(os.environ, XDG_STATE_HOME=str(self.root), WATCHDOG_STATE_DIR=str(self.root/'state'))
        self.env.start();self.addCleanup(self.env.stop)
        self.b=Binding(account=str(self.root/'account'))
        skill=Path(self.b.account)/'skills/religar/SKILL.md'
        skill.parent.mkdir(parents=True);skill.write_text('fixture')
        engine=patch('watchdog_app.bindings.engine',return_value=SimpleNamespace(Binding=Binding))
        engine.start();self.addCleanup(engine.stop)
        self.api=FakeHerdr(self.b)
        self.ref='a'*32
        self.attempt={'state':'pending','pane':self.b.pane}
        from watchdog_app import relink_delivery
        self.d=relink_delivery
        self.guard=patch.object(self.d,'validate',side_effect=lambda *args:self.api.call('agent','get')['agent'])
        self.validator=self.guard.start();self.addCleanup(self.guard.stop)
    def start(self):
        self.d.prepare(self.ref,self.b,self.root,api=self.api)
    def step(self):
        return self.d.step(self.ref,self.attempt,api=self.api)
    def test_one_skill_invocation_to_selected_pane_then_no_resend_after_reopen(self):
        # L32-34: stale announced A never itself becomes proof; exactly one command.
        self.start()
        for _ in range(8):self.step()
        self.assertEqual(self.api.sent,[(self.b.pane,'$religar '+self.ref)])
        self.assertEqual(self.api.keys,['Enter'])
        self.assertEqual(self.step()['state'],'sent')
    def test_draft_and_working_agent_wait_without_mutation(self):
        # L16,35: no paste into draft or working agent; no explicit queue consent.
        self.start();self.api.draft='texto humano'
        self.assertIn('rascunho',self.step()['notice'])
        self.api.draft='';self.api.status='working'
        self.assertIn('ocupado',self.step()['notice'])
        self.assertEqual(self.api.sent,[])
        self.api.status='idle'
        for _ in range(5):self.step()
        self.assertEqual(len(self.api.sent),1)
    def test_cancel_waiting_removes_authorization_and_late_poll_never_sends(self):
        # L19,35: cancellation invalidates the old invocation.
        self.start();self.api.draft='human';self.step()
        self.attempt['state']='cancelled';self.step()
        self.api.draft=''
        for _ in range(4):self.step()
        self.assertEqual(self.api.sent,[])
    def test_uncertain_paste_never_repeats_or_overtakes(self):
        # L16,19,35: ambiguous result freezes transport even after reopening.
        self.start();self.api.consume=False
        self.step();self.api.draft='edição humana'
        for _ in range(6):self.step()
        self.assertEqual(len(self.api.sent),1)
        self.assertEqual(self.api.keys,[])
        self.assertEqual(self.step()['state'],'uncertain')
    def test_old_delivery_worker_cannot_advance_with_announced_A_and_effective_B(self):
        # L20,37: actual shared queue worker must stop, not merely omit UI resend.
        self.start()
        pending=delivery.pending_path(self.b.pane)
        for phase in ('pasting','materialized','submitting','uncertain'):
            old=dict(version=1,delivery_id='old',pane=self.b.pane,session=None,
                identity=list(delivery.identity(self.api.call('agent','get')['agent'])),text='pedido antigo de A',
                phase=phase,enter='Enter',last_progress_at=0)
            delivery.atomic(pending,old)
            with self.assertRaises(delivery.DeliveryPending):
                delivery.advance(self.api,old,pending,deadline=__import__('time').monotonic()+.1)
            for _ in range(3):self.step()
            self.assertEqual(self.api.sent,[])
            self.assertEqual(json.loads(pending.read_text())['text'],'pedido antigo de A')
            self.assertIn('anterior',self.step()['notice'])
    def test_waiting_old_request_is_held_and_recovery_invocation_can_pass(self):
        # L20,37 + combined acceptance: no paste yet may be held, never replayed to B.
        self.start()
        pending=delivery.pending_path(self.b.pane)
        old=dict(version=1,delivery_id='old',pane=self.b.pane,session=None,
            identity=list(delivery.identity(self.api.call('agent','get')['agent'])),text='pedido antigo A',
            phase='waiting',enter='Enter',last_progress_at=0)
        delivery.atomic(pending,old)
        for _ in range(8):self.step()
        self.assertEqual(self.api.sent,[(self.b.pane,'$religar '+self.ref)])
        held=list(self.d.record_path(self.ref).with_suffix('.held').glob('*.json'))
        self.assertEqual(len(held),1)
        self.assertEqual(json.loads(held[0].read_text()),old)
        self.attempt.update(state='confirmed',notice='B comprovada')
        self.step()
        for _ in range(3):self.step()
        self.assertEqual(len(self.api.sent),1)
        self.assertEqual(json.loads(held[0].read_text())['identity'][-1],self.b.session)

    def test_replaced_terminal_during_wait_is_rejected_before_paste(self):
        # L16,35: changed destination never receives even the recovery command.
        self.start();self.api.draft='human';self.step()
        self.validator.side_effect=RuntimeError('terminal substituído')
        self.api.draft=''
        result=self.step()
        self.assertEqual(result['state'],'failed')
        self.assertIn('substituído',result['notice'])
        self.assertEqual(self.api.sent,[])
    def test_cancel_uncertain_paste_keeps_fence_and_blocks_new_attempt(self):
        # L16,19: cancellation of proof does not erase a transport uncertainty.
        self.start();self.step();self.api.draft='human edit';self.step()
        self.attempt['state']='cancelled'
        for _ in range(3):self.step()
        with self.assertRaisesRegex(RuntimeError,'anterior'):
            self.d.prepare('b'*32,self.b,self.root,api=self.api)
        self.assertEqual(len(self.api.sent),1)

    def test_second_panel_reloads_delivery_after_taking_the_pane_lock(self):
        # L19,34: concurrent observers cannot resend a stale waiting snapshot.
        self.start()
        original=delivery.pane_lock
        @contextmanager
        def concurrent(*args,**kwargs):
            with original(*args,**kwargs) as pending:
                job=json.loads(self.d.record_path(self.ref).read_text())
                job.update(state='sent',notice='already consumed by other panel')
                delivery.atomic(self.d.record_path(self.ref),job)
                yield pending
        with patch.object(delivery,'pane_lock',concurrent):
            self.step()
        self.assertEqual(self.api.sent,[])
    def test_cancellation_is_rechecked_inside_transport_lock(self):
        # L19,35: a stale UI observation isn't current authorization.
        self.start()
        result=self.d.step(self.ref,self.attempt,api=self.api,
            read_attempt=lambda ref:dict(state='cancelled',notice='cancelada'))
        self.assertEqual(self.api.sent,[])
        self.assertEqual(result['state'],'cancelled')

    def test_skill_removed_during_wait_is_reported_without_invocation(self):
        # L16,36: availability must still hold when the draft becomes free.
        self.start();self.api.draft='human';self.step();self.api.draft=''
        with patch.object(self.d,'skill_available',return_value=False):
            result=self.step()
        self.assertEqual(result['state'],'failed')
        self.assertEqual(self.api.sent,[])

    def test_recovery_fence_prevents_worker_from_replacing_waiting_request_with_stall_notice(self):
        # L20,37: the old queue stays intact while proof is pending, even if old.
        self.start();pending=delivery.pending_path(self.b.pane)
        old=dict(version=1,delivery_id='old',pane=self.b.pane,session=None,
            identity=[self.b.pane,self.b.terminal,'codex',self.b.session],text='old A',
            phase='waiting',enter='Enter',last_progress_at=0)
        delivery.atomic(pending,old)
        delivery.check_stalled(pending)
        self.assertEqual(json.loads(pending.read_text()),old)
        self.assertFalse(delivery.queue_state_path(pending).exists())

    def test_core_attempt_starts_under_same_pane_lease_as_its_transport_fence(self):
        # L16,37: do not create a proof window before pausing the old queue worker.
        session=SimpleNamespace(repo=self.root)
        events=[];original=delivery.pane_lock
        @contextmanager
        def lease(*args,**kwargs):
            with original(*args,**kwargs) as pending:
                events.append('locked')
                yield pending
                events.append('released')
        def begin(current,candidate):
            self.assertEqual(events,['locked'])
            events.append('begin')
            return self.ref
        with patch.object(delivery,'pane_lock',lease):
            self.assertEqual(self.d.start(session,self.b,begin,api=self.api),self.ref)
        self.assertEqual(events,['locked','begin','released'])
        self.assertTrue(self.d.fence_path(delivery.pending_path(self.b.pane)).exists())

    def test_explicit_new_attempt_after_cancelled_wait_does_not_release_old_A_request(self):
        # L19,35-37: cancelling a waiting attempt must still permit recovery.
        self.start();pending=delivery.pending_path(self.b.pane)
        old=dict(version=1,delivery_id='old',pane=self.b.pane,session=None,
            identity=[self.b.pane,self.b.terminal,'codex',self.b.session],text='old A',
            phase='waiting',enter='Enter',last_progress_at=0)
        delivery.atomic(pending,old)
        self.attempt['state']='cancelled';self.step()
        ref=self.d.start(SimpleNamespace(repo=self.root),self.b,lambda *args:'b'*32,api=self.api)
        for _ in range(8):self.d.step(ref,dict(state='pending'),api=self.api)
        self.assertEqual(self.api.sent,[(self.b.pane,'$religar '+'b'*32)])
        held=list(self.d.record_path(ref).with_suffix('.held').glob('*.json'))
        self.assertEqual([json.loads(p.read_text()) for p in held],[old])

    def test_missing_skill_refuses_before_sending(self):
        # L36: unavailable skill produces an actionable failure.
        (Path(self.b.account)/'skills/religar/SKILL.md').unlink()
        with patch.object(self.d,'skill_available',return_value=False):
            with self.assertRaisesRegex(RuntimeError,'Skill'):self.start()
        self.assertEqual(self.api.sent,[])



class RelinkCandidateTests(unittest.TestCase):
    def test_live_codex_with_missing_old_history_is_selectable_but_foreground_change_is_rejected(self):
        # L10,16,32: discovery cannot require the obsolete history to exist.
        from watchdog_app import relink_delivery as d
        b=Binding()
        process=dict(pid=b.pid,started=b.started,kind=b.kind,account=b.account,pane=b.pane)
        engine=SimpleNamespace(Binding=Binding,processes=lambda:[process],process_info=lambda pid:process)
        agent=dict(pane_id=b.pane,terminal_id=b.terminal,workspace_id=b.workspace,
            agent='codex',agent_session=dict(kind='id',value='old-A'),agent_status='idle')
        class Api:
            def call(self,*args):
                if args[:2]==('agent','list'):return {'agents':[agent]}
                if args[:2]==('agent','get'):return {'agent':agent}
                return {'process_info':{'foreground_processes':[{'pid':b.pid}]}}
            def checked(self,pane):return dict(cwd='/project',terminal_id=b.terminal)
        api=Api()
        session=SimpleNamespace(binding=b,repo=Path('/project'))
        with patch('watchdog_app.leader_link.choices',return_value=[]), \
             patch.object(d.bindings,'engine',return_value=engine),patch.object(d,'Herdr',return_value=api):
            result=d.choices(session)
            self.assertEqual([x.pane for x in result],[b.pane])
            self.assertEqual(result[0].session,'old-A')
            self.assertEqual(result[0].history,'')
            process['started']='changed-process'
            with self.assertRaisesRegex(RuntimeError,'Processo'):
                d.validate(result[0],session.repo,api)

if __name__=='__main__':unittest.main()
