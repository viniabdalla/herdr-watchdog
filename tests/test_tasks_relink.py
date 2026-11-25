"""Religar spec 2026-11-25 L10-12,16,19,32-37: Tasks controller contract."""
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from test_leader_link import Binding
from watchdog_app.tasks_ui import TasksUI


class TasksRelinkTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.repo=Path(self.temp.name)
        self.b=Binding()
        self.candidate=replace(self.b,pane='project:p9',session='stale-A')
        self.ref='a'*32
        self.state={'state':'pending','pane':self.candidate.pane,'notice':'aguardando prova'}
        self.core=SimpleNamespace(begin=Mock(return_value=self.ref),read=lambda ref:self.state,
            guard=lambda file:None,cancel=Mock(side_effect=lambda ref:self.state.update(state='cancelled')),pending_for=lambda path:self.ref)
        self.modules=patch.dict(sys.modules,{'watchdog_app.relink':self.core})
        self.modules.start();self.addCleanup(self.modules.stop)
        self.ui=TasksUI.__new__(TasksUI)
        self.ui.screen=SimpleNamespace(getmaxyx=lambda:(30,120))
        self.ui.repo=self.repo;self.ui.mode='relink';self.ui.pending=None
        self.ui.session=SimpleNamespace(binding=self.b,file=self.repo/'a.json')
        self.ui.binding_file=self.ui.session.file
        self.ui.job=Mock();self.ui.notice='';self.ui.cursor=self.ui.scroll=0
        self.ui.leader_choices=[self.candidate];self.ui.visible_identifiers=[0]
        self.ui.last_auto_key=self.ui.result=None
    def test_one_enter_starts_skill_and_waits_without_claiming_success(self):
        # L10-12,32-33: binding cannot change just because the advertised A is selectable.
        with patch('watchdog_app.relink_delivery.start',side_effect=lambda session,candidate,begin:begin(session,candidate)) as start:
            self.ui.handle('enter')
        self.assertEqual(self.ui.mode,'relink_wait')
        self.assertEqual(self.ui.session.binding,self.b)
        self.assertNotIn('Líder ligado',self.ui.notice)
        start.assert_called_once_with(self.ui.session,self.candidate,self.core.begin)
        self.ui.handle('enter')
        self.core.begin.assert_called_once()
    def test_cancel_invalidates_attempt_before_returning_to_tasks(self):
        # L19,35: Esc invalidates the reference, including already sent invocation.
        self.ui.mode='relink_wait';self.ui.relink_ref=self.ref
        with patch('watchdog_app.relink_delivery.step'):
            self.ui.handle('escape')
        self.core.cancel.assert_called_once_with(self.ref)
        self.assertEqual(self.ui.mode,'tasks')
    def test_confirmed_only_after_opening_verified_successor(self):
        # L18,32: UI reopens saved successor, not an in-memory candidate.
        self.ui.mode='relink_wait';self.ui.relink_ref=self.ref
        self.state.update(state='confirmed',successor=str(self.repo/'b.json'))
        new=SimpleNamespace(binding=replace(self.candidate,session='BBBBBBBB-full'))
        with patch('watchdog_app.relink_delivery.step',return_value={'state':'sent','notice':'enviado'}), \
             patch('watchdog_app.tasks_ui.Session.for_panel',return_value=new) as reopen:
            self.ui.poll_relink()
        reopen.assert_called_once_with(self.repo/'b.json',self.repo)
        self.assertIs(self.ui.session,new)
        self.assertIn('Líder ligado · project:p9 · BBBBBBBB',self.ui.notice)
    def test_reopen_observes_existing_attempt_without_preparing_or_resending(self):
        # L19,34: restart resumes observation only.
        self.ui.mode='tasks'
        with patch('watchdog_app.relink_delivery.prepare') as prepare, \
             patch('watchdog_app.relink_delivery.step',return_value={'state':'sent','notice':'aguardando prova'}):
            self.ui.restore_relink()
            self.ui.poll_relink()
        prepare.assert_not_called()
        self.assertEqual(self.ui.relink_ref,self.ref)
        self.assertIn('aguardando prova',self.ui.notice)
    def test_reopen_finds_attempt_started_from_a_previously_transferred_binding(self):
        # L19: older panel launch path may precede the active binding file.
        self.ui.mode='tasks'
        self.ui.session.file=self.repo/'active-child.json'
        self.core.pending_for=lambda path:self.ref if Path(path)==self.ui.session.file else None
        self.ui.restore_relink()
        self.assertEqual(self.ui.mode,'relink_wait')
        self.assertEqual(self.ui.relink_ref,self.ref)

    def test_failed_core_or_uncertain_delivery_never_claims_success(self):
        # L19,36: real stage/cause is visible; uncertain transport isn't confirmation.
        self.ui.mode='relink_wait';self.ui.relink_ref=self.ref
        with patch('watchdog_app.relink_delivery.step',return_value={'state':'uncertain','notice':'rascunho alterado'}):
            self.ui.poll_relink()
        self.assertIn('rascunho alterado',self.ui.notice)
        self.assertEqual(self.ui.session.binding,self.b)
        self.state.update(state='failed',notice='registro ainda anuncia A')
        with patch('watchdog_app.relink_delivery.step',return_value={'state':'failed','notice':'registro ainda anuncia A'}):
            self.ui.poll_relink()
        self.assertIn('registro ainda anuncia A',self.ui.notice)
        self.assertNotIn('Líder ligado',self.ui.notice)

if __name__=='__main__':unittest.main()
