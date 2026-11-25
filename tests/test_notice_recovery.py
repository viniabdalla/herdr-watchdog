"""Issue #16 L58-62; spec #1 L58-60,137,172-175; T15 reaberta: não entrega."""
import json
from unittest.mock import patch
import sys
import test_stalled_queue as stalled
from pane_submission_fixture import SubmissionFixture
from watchdog_app import pane_delivery as d
from watchdog_app.store import atomic


class NoticeRecoveryTests(SubmissionFixture):
    setup_queue = stalled.StalledQueueTests.setup_queue
    tick = stalled.StalledQueueTests.tick
    def failed_notice(self):
        self.setup_queue();self.tick()
        job=json.loads(self.pending.read_text())
        job.update(phase='pasting')
        d.suspend(job,self.pending,'Paste encerrado, histórico sem alerta')
        self.incident=json.loads(d.queue_state_path(self.pending).read_text())['archive']
        self.original=self.pending.read_bytes()

    def recover(self, action='rearm', token='decisao-1', evidence='Histórico conferido: não entregue; paste anterior encerrado', **kw):
        return d.recover_notice('w11:p8',self.incident,action,token,evidence,**kw)

    def test_never_delivered_notice_can_be_rearmed_once_without_false_receipt(self):
        self.failed_notice()
        with self.assertRaises(RuntimeError):d.reconcile(self.pending,'materialized','campo vazio')
        with self.assertRaises(RuntimeError):d.reconcile(self.pending,'retired','nunca entregue')
        with self.assertRaises(RuntimeError):d.resolve_queue('w11:p8',[],'sem recibo')
        with self.assertRaises(RuntimeError):self.recover()
        self.assertEqual(self.pending.read_bytes(),self.original)
        command=[sys.executable,'-m','watchdog_app.pane_delivery','recover-notice',
                 '--pane','w11:p8','--incident',self.incident,'--action','rearm',
                 '--recovery-id','decisao-1','--not-delivered','--evidence',
                 'Histórico conferido: não entregue; paste anterior encerrado']
        self.finish(self.start(command))
        rearmed=self.pending.read_bytes()
        self.assertEqual(self.actual()['submitted'],[])
        self.assertEqual(d.queue_notice('w11:p8'),'')
        self.recover(not_delivered=True)
        self.assertEqual(self.pending.read_bytes(),rearmed)
        self.assertEqual(d.resume(self.pending),0)
        self.assertEqual(len(self.actual()['submitted']),1)
        self.recover(not_delivered=True)  # repeat after consumption never pastes again
        self.assertFalse(self.pending.exists())
        self.assertEqual(len(self.actual()['submitted']),1)
        self.assertEqual(d.queue_notice('w11:p8'),'Fila travada · perguntei ao líder')
        receipt=next(d.Path(self.incident).glob('notice-recovery.*.json'))
        saved=json.loads(receipt.read_text())
        self.assertEqual(saved['notice_serialized'],self.original.decode())
        self.assertTrue(saved['not_delivered'])
        self.assertEqual(saved['observed_composer'],[])
        d.resolve_queue('w11:p8',['0','1','2','3'],'T6 integrado; fila atual conferida')
        for path in d.queued_paths(self.pending):d.resume(path)
        self.assertEqual(self.actual()['submitted'][1:],['T13 pronto','outro pedido','$code-review'])

    def test_rearm_preserves_unrelated_draft_and_does_not_retry_automatically(self):
        self.failed_notice()
        self.state['draft']='rascunho do Vini';self.save()
        self.recover(not_delivered=True)
        with self.assertRaises(d.DeliveryPending):
            d.advance(d.Herdr(),json.loads(self.pending.read_text()),self.pending,deadline=d.time.monotonic()+.15)
        self.assertEqual(self.actual()['draft'],'rascunho do Vini')
        self.assertEqual(self.actual()['submitted'],[])
        self.assertEqual(d.queue_notice('w11:p8'),'')
        self.state['draft']='';self.save()
        d.resume(self.pending)
        self.assertEqual(len(self.actual()['submitted']),1)

    def changed_leader(self):
        self.state['session']='22222222-2222-4222-8222-222222222222';self.save()
        current=dict(self.front,delivery_id='current',phase='waiting',text='pedido atual',
                     identity=['w11:p8','term1','codex',self.state['session']])
        path=self.pending.with_name(self.pending.name.replace('.pending.json','.queued.z-current.json'))
        atomic(path,current)
        return path

    def test_changed_identity_closes_obsolete_incident_without_input_or_receipt(self):
        self.failed_notice();self.changed_leader()
        with self.assertRaisesRegex(RuntimeError,'Identidade'):
            self.recover(not_delivered=True)
        self.recover(action='close',evidence='Líder antigo encerrado; incidente obsoleto; pedidos atuais preservados')
        self.assertFalse(self.pending.exists())
        self.assertEqual(d.queue_notice('w11:p8'),'')
        self.assertFalse(any(c[0]=='pane' for c in self.commands()))
        self.recover(action='close',evidence='Líder antigo encerrado; incidente obsoleto; pedidos atuais preservados')
        jobs=[json.loads(p.read_text()) for p in d.queued_paths(self.pending)]
        self.assertEqual([job['text'] for job in jobs],['pedido atual'])
        for path in d.queued_paths(self.pending):d.resume(path)
        self.assertEqual(self.actual()['submitted'],['pedido atual'])
        receipt=json.loads(next(d.Path(self.incident).glob('notice-recovery.*.json')).read_text())
        self.assertEqual(len(receipt['retired']),4)
        self.assertEqual(receipt['notice_serialized'],self.original.decode())

    def test_restart_finishes_rearm_before_any_paste_and_command_remains_idempotent(self):
        self.failed_notice()
        original_atomic=d.atomic
        def interrupted(path,value):
            if path==d.queue_state_path(self.pending) and value.get('status')=='awaiting':
                raise RuntimeError('crash antes do fim')
            return original_atomic(path,value)
        with patch.object(d,'atomic',side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError,'crash antes do fim'):
                self.recover(not_delivered=True)
        self.assertFalse(any(c[0]=='pane' for c in self.commands()))
        self.assertEqual(d.queue_notice('w11:p8'),'')
        d.resume(self.pending)  # a fresh production worker resumes the saved decision
        self.assertEqual(len(self.actual()['submitted']),1)
        self.recover(not_delivered=True)
        self.assertFalse(self.pending.exists())

    def test_restart_finishes_documentary_close_preserving_late_arrivals(self):
        self.failed_notice();self.changed_leader()
        def interrupted(*args):raise RuntimeError('crash com decisão salva')
        with patch.object(d,'finish_notice_recovery',side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError,'crash com decisão salva'):
                self.recover(action='close')
        late=self.pending.with_name(self.pending.name.replace('.pending.json','.queued.zz-late.json'))
        current=json.loads(next(p for p in d.queued_paths(self.pending) if 'z-current' in p.name).read_text())
        atomic(late,dict(current,delivery_id='late',text='posterior à decisão'))
        d.resume(self.pending)
        self.assertFalse(any(c[0]=='pane' for c in self.commands()))
        self.assertEqual(d.queue_notice('w11:p8'),'')
        for path in d.queued_paths(self.pending):d.resume(path)
        self.assertEqual(self.actual()['submitted'],['pedido atual','posterior à decisão'])

    def test_close_interrupted_after_retirement_can_finish_by_repeating_same_decision(self):
        # T15 reaberta + issue #16 L58-62: no receipt, even after pending disappears.
        self.failed_notice();self.changed_leader()
        def interrupted(*args):raise RuntimeError('crash após retirar aviso')
        with patch.object(d,'finish_resolution',side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError,'crash após retirar aviso'):
                self.recover(action='close')
        self.assertFalse(self.pending.exists())
        self.assertEqual(d.queue_notice('w11:p8'),'')
        self.recover(action='close')
        self.recover(action='close')
        self.assertFalse(any(c[0]=='pane' for c in self.commands()))
        for path in d.queued_paths(self.pending):d.resume(path)
        self.assertEqual(self.actual()['submitted'],['pedido atual'])

    def test_same_recovery_id_rejects_different_decision_and_stale_incident(self):
        self.failed_notice()
        with self.assertRaises(RuntimeError):
            d.recover_notice('w11:p8',str(d.Path(self.incident).with_name('outro-incidente')),
                             'rearm','id','histórico verificado',not_delivered=True)
        self.recover(not_delivered=True)
        with self.assertRaisesRegex(RuntimeError,'outra decisão'):
            self.recover(evidence='Outra afirmação',not_delivered=True)
        self.assertFalse(any(c[0]=='pane' for c in self.commands()))
