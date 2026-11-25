"""Spec #1 L58-60,137,174-175: visible paste/materialization/consumption."""
import json
import subprocess
import sys
import time
from pane_submission_fixture import SubmissionFixture


class PaneSubmissionTests(SubmissionFixture):
    def test_idle_and_busy_pane_messages_materialize_and_are_consumed_separately(self):
        # Spec #1 L58-59,137,174-175; reported paste+Enter race.
        for agent,status in (('codex','idle'),('codex','working'),('claude','working')):
            with self.subTest(agent=agent,status=status):
                self.state.update(draft='',submitted=[],status=status,agent=agent)
                self.save()
                self.send('T9 pronto\ntexto intacto');self.send('T5 pronto')
                self.assertEqual(self.actual()['submitted'],['T9 pronto\ntexto intacto','T5 pronto'])
                self.assertEqual(self.actual()['draft'],'')
                self.assertFalse(any(c[:2]==['agent','prompt'] for c in self.commands()))
                self.assertEqual(self.actual()['queued'],[])

    def test_human_draft_is_preserved_and_delivery_is_saved_for_later(self):
        # T6 correction: wait instead of deleting/concatenating human input.
        self.state['draft']='rascunho humano\nsegunda linha';self.save()
        self.send('aviso',success=False)
        self.assertEqual(self.actual()['draft'],self.state['draft'])
        self.assertFalse(any(c[0]=='pane' for c in self.commands()))
        self.assertTrue(list((self.root/'xdg/herdr-watchdog/pane-locks').glob('*.pending.json')))

    def test_human_draft_with_placeholder_words_or_prompt_marker_is_preserved(self):
        # T6 correction: neither placeholder words nor a quoted › mean empty input.
        for draft in ('Ask Codex to do anything','humano\n› '):
            with self.subTest(draft=draft):
                for path in (self.root/'xdg/herdr-watchdog/pane-locks').glob('*.pending.json'):path.unlink()
                self.state['draft']=draft;self.save()
                self.send('aviso',success=False)
                self.assertEqual(self.actual()['draft'],draft)

    def test_real_codex_word_wrap_removes_only_tui_margin_and_keeps_logical_space(self):
        # T6 real proof 9c61a992 supplied by leader; no live pane interaction.
        from watchdog_app.pane_delivery import composer, matches
        lines = [
            '› Prova do envio real 9c61a992 2. Mensagem independente',
            '  para verificar que um aviso chega inteiro ao Codex',
            '  ocupado. Preserve os arquivos do projeto.']
        screen = '\n'.join('\x1b[0m\x1b[48;2;51;30;30m'+line+'\x1b[0m' for line in lines)
        screen += '\n\n  GPT-6.1-Sol medium · Context 24%'
        text = ('Prova do envio real 9c61a992 2. Mensagem independente '
                'para verificar que um aviso chega inteiro ao Codex '
                'ocupado. Preserve os arquivos do projeto.')
        actual = composer(screen)
        self.assertEqual(actual, [line[2:] for line in lines])
        self.assertTrue(matches(actual,text))
        self.assertFalse(matches(actual,text.replace('inteiro ao','inteiro  ao')))

    def test_real_proof_text_submits_after_visible_word_wrapping(self):
        # T6 proof 9c61a992 through the complete fake-Herdr transport.
        self.state.update(wrap=True,status='working',needs_tab=True);self.save()
        text = ('Prova do envio real 9c61a992 2. Mensagem independente '
                'para verificar que um aviso chega inteiro ao Codex '
                'ocupado. Preserve os arquivos do projeto.')
        self.send(text)
        self.assertEqual(self.actual()['submitted'],[text])
        self.assertEqual(self.actual()['keys'],['enter','tab'])

    def test_zero_exit_without_consumption_blocks_later_writer(self):
        # T6 correction: preserve an uncertain owned draft, never concatenate B.
        self.state['stall']=True;self.save()
        self.send('T9',success=False)
        self.assertEqual(self.actual()['draft'],'T9')
        before=self.commands()
        self.send('T5',success=False)
        self.assertEqual([c for c in self.commands() if c[0]=='pane'],[c for c in before if c[0]=='pane'])
        self.assertEqual(self.actual()['draft'],'T9')

    def test_busy_codex_uses_tab_only_after_enter_left_the_exact_owned_message(self):
        # T6 correction authorized visible Tab queue fallback for simple Codex messages.
        self.state.update(status='working',needs_tab=True);self.save()
        self.send('Aviso íntegro')
        self.assertEqual(self.actual()['submitted'],['Aviso íntegro'])
        self.assertEqual(self.actual()['keys'],['enter','tab'])
        self.assertEqual(self.actual()['queued'],[])

    def test_goal_busy_never_uses_tab_or_native_queue(self):
        # Spec #1 L49,53,58: preserve /goal as native TUI command even while busy.
        self.state.update(status='working',needs_tab=True);self.save()
        self.send('/goal meta',success=False)
        self.assertNotIn('tab',self.actual().get('keys',[]))
        self.assertEqual(self.actual()['queued'],[])
        self.assertEqual(self.actual()['draft'],'/goal meta')

    def test_identity_change_prevents_fallback_or_retry(self):
        # T6 correction: keep pane + terminal + harness + session pinned through ack.
        self.state.update(change_identity=True,stall=True);self.save()
        self.send('aviso',success=False)
        self.assertEqual(self.actual()['keys'],['enter'])
        self.send('outro',success=False)
        self.assertEqual(self.actual()['keys'],['enter'])

    def test_human_edit_after_enter_is_not_submitted_by_fallback(self):
        # Spec #1 L58-60,137,174-175 + issue #7 L45 (2026-11-25T16:01:29Z):
        # confirmed pane delivery preserves human drafts; fallback needs exact own text.
        self.state.update(alter_on_enter=True,status='working');self.save()
        self.send('aviso',success=False)
        self.assertEqual(self.actual()['draft'],'edição humana')
        self.assertEqual(self.actual()['keys'],['enter'])
        self.assertEqual(self.actual()['submitted'],[])
        job=json.loads(self.pending().read_text())
        self.assertEqual(job['observed_composer'],['edição humana'])

    def test_collapsed_paste_without_exact_materialization_sends_no_enter(self):
        # Spec #1 L58-60,137 + issue #7 L45 (2026-11-25T16:01:29Z):
        # inferred conservative guard: a collapsed label cannot confirm intact text.
        self.state['collapsed']=True;self.save()
        self.send('texto longo',success=False)
        self.assertEqual(self.actual()['draft'],'texto longo')
        self.assertEqual(self.actual().get('keys',[]),[])

    def test_blocked_agent_receives_no_input(self):
        # Spec #1 L58-60,137 + issue #7 L45 (2026-11-25T16:01:29Z):
        # inferred fail-closed guard for unverified input readiness, not an explicit
        # spec requirement for blocked; preserve drafts and the Claude/Codex pane route.
        self.state['status']='blocked';self.save()
        self.send('aviso',success=False)
        self.assertFalse(any(c[0]=='pane' for c in self.commands()))

    def pending(self):
        return next((self.root/'xdg/herdr-watchdog/pane-locks').glob('*.pending.json'))

    def transport(self, action, path, *args):
        return self.start([sys.executable,'-m','watchdog_app.pane_delivery',action,str(path),*args])

    def test_empty_after_paste_background_suspends_and_late_paste_requires_reconciliation(self):
        # Spec #1 L58-60,137,174-175 + R1 approved P1: uncertainty is not consumption.
        self.state['paste_delay']=60;self.save()
        self.send('Aviso A',success=False)
        pending=self.pending()
        # Foreground deadline preserves the stage for the normal background worker.
        self.finish(self.transport('resume',pending),success=False)
        job=json.loads(pending.read_text())
        self.assertEqual(job['phase'],'uncertain')
        self.assertEqual(job['observed_composer'],[])
        self.assertEqual(job['text'],'Aviso A')
        self.send('Aviso B',success=False)
        self.send('Aviso C',success=False)
        queued=sorted(pending.parent.glob('*.queued.*.json'))
        # A late paste must not cause automatic retry/resume or let B concatenate.
        current=self.actual();current.update(materialized_at=0,paste_delay=.12)
        (self.root/'state.json').write_text(json.dumps(current))
        self.finish(self.transport('resume',pending),success=False)
        self.assertEqual(self.actual()['draft'],'Aviso A')
        self.assertEqual(self.actual().get('keys',[]),[])
        self.finish(self.transport('reconcile',pending,'--resolution','materialized',
                                   '--evidence','Paste atrasado conferido integralmente'))
        self.finish(self.transport('resume',pending))
        for path in queued:self.finish(self.transport('resume',path))
        self.assertEqual(self.actual()['submitted'],['Aviso A','Aviso B','Aviso C'])
        self.assertEqual(len([c for c in self.commands() if c[:2]==['pane','send-text']]),3)
        self.assertTrue(list(pending.parent.glob('*.reconciled.*.json')))

    def test_old_r1_pasting_record_recovers_with_human_draft_without_repaste(self):
        # Spec #1 L59,137 + issue #7 L45; R1 P1 explicitly includes old records.
        self.state.update(draft='humano',paste_delay=60);self.save()
        self.send('Aviso A',success=False)
        pending=self.pending();job=json.loads(pending.read_text())
        job['phase']='pasting'  # R1-fila/*.pending.json: version 1, no delivery id or timestamp.
        job.pop('delivery_id',None)
        job.pop('confirmation_started_at',None)
        pending.write_text(json.dumps(job))
        self.finish(self.transport('resume',pending),success=False)
        suspended=json.loads(pending.read_text())
        self.assertEqual(suspended['phase'],'uncertain')
        self.assertEqual(self.actual()['draft'],'humano')
        self.send('Aviso B',success=False)
        queued=next(pending.parent.glob('*.queued.*.json'))
        self.finish(self.transport('reconcile',pending,'--resolution','materialized',
                                   '--evidence','Não corresponde'),success=False)
        self.assertEqual(json.loads(pending.read_text()),suspended)
        self.finish(self.transport('reconcile',pending,'--resolution','retired',
                                   '--evidence','Paste antigo encerrado; A cancelado manualmente; rascunho humano preservado'))
        # Retiring A does not confirm it, run its callback, or discard the human draft.
        self.send('Aviso C',success=False)
        self.assertEqual(self.actual()['draft'],'humano')
        self.assertFalse(any(c[0]=='pane' for c in self.commands()))
        current=self.actual();current.update(draft='',paste_delay=.12)
        (self.root/'state.json').write_text(json.dumps(current))
        self.finish(self.transport('resume',queued))
        later=next(pending.parent.glob('*.queued.*.json'))
        self.finish(self.transport('resume',later))
        self.assertEqual(self.actual()['submitted'],['Aviso B','Aviso C'])

    def test_changed_session_can_retire_old_item_but_never_submit_it(self):
        # Spec #1 L58-60,119-121,137 + R1 P1: retire stale A explicitly after Religar.
        self.state.update(paste_delay=60);self.save()
        self.send('Aviso A',success=False)
        pending=self.pending()
        current=self.actual();current.update(session='22222222-2222-4222-8222-222222222222')
        current.pop('paste',None);current['paste_delay']=.12
        (self.root/'state.json').write_text(json.dumps(current))
        self.finish(self.transport('resume',pending),success=False)
        self.finish(self.transport('reconcile',pending,'--resolution','materialized',
                                   '--evidence','Sessão mudou'),success=False)
        self.finish(self.transport('reconcile',pending,'--resolution','retired',
                                   '--evidence','Religar conferido; paste antigo encerrado; A cancelado'))
        self.send('Aviso B')
        self.assertEqual(self.actual()['submitted'],['Aviso B'])
        self.assertEqual(self.actual()['keys'],['enter'])
        archive=json.loads(next(pending.parent.glob('*.reconciled.*.json')).read_text())
        self.assertNotEqual(archive['job']['identity'][-1],archive['observed_identity'][-1])

    def test_reconciliation_rejects_pending_reused_while_operator_waited_for_lock(self):
        # Spec #1 L59,137 + R1 P1: reusable pane filename is not a delivery identity.
        from contextlib import contextmanager
        from unittest.mock import patch
        from watchdog_app import pane_delivery as delivery
        from watchdog_app.store import atomic
        pending=self.root/'delivery.pending.json'
        original=dict(pane='w11:p8',session=None,identity=['w11:p8','term1','codex',self.state['session']],
                      phase='uncertain',uncertain_phase='pasting',text='A')
        atomic(pending,original)
        replacement=dict(original,text='B')
        @contextmanager
        def replaced(*args):
            atomic(pending,replacement)
            yield pending
        with patch.object(delivery,'pane_lock',replaced), patch.object(delivery,'Herdr') as api:
            with self.assertRaisesRegex(RuntimeError,'mudou'):
                delivery.reconcile(pending,'retired','A encerrado manualmente')
            api.assert_not_called()
        self.assertEqual(json.loads(pending.read_text()),replacement)

    def test_valid_observation_after_slow_cli_precedes_confirmation_timeout(self):
        # Spec #1 L58-60,137 + R1 P1: a valid late observation is evidence, not timeout.
        from unittest.mock import patch
        from watchdog_app import pane_delivery as delivery
        from watchdog_app.store import atomic
        for phase,rows in (('pasting',['A']),('submitting',[])):
            with self.subTest(phase=phase):
                pending=self.root/'slow.pending.json'
                job=dict(pane='w11:p8',identity=['p','t','codex','s'],text='A',phase=phase,
                         confirmation_started_at=0,enter='Enter')
                atomic(pending,job)
                with patch.object(delivery,'live',return_value={'agent_status':'working','agent':'codex'}), \
                     patch.object(delivery,'surface',side_effect=[rows,['A'],['A'],[]] if phase=='pasting' else [rows]), \
                     patch.object(delivery.time,'sleep'), patch.object(delivery,'Herdr') as api:
                    self.assertEqual(delivery.advance(api,job,pending),'consumed')
                self.assertFalse(pending.exists())

    def test_slow_key_cli_is_followed_by_valid_consumption_observation(self):
        # Spec #1 L58-60,137 + R1 P1: do not time out before reading after slow send-keys.
        from unittest.mock import patch, Mock
        from watchdog_app import pane_delivery as delivery
        from watchdog_app.store import atomic
        pending=self.root/'slow-key.pending.json'
        job=dict(pane='w11:p8',identity=['p','t','codex','s'],text='A',phase='materialized',
                 confirmation_started_at=0,enter='Enter')
        atomic(pending,job)
        now=[0]
        api=Mock()
        api.call.side_effect=lambda *a:now.__setitem__(0,10)
        with patch.object(delivery,'live',return_value={'agent_status':'working','agent':'codex'}), \
             patch.object(delivery,'surface',side_effect=[['A'],['A'],[]]), \
             patch.object(delivery.time,'time',side_effect=lambda:now[0]), patch.object(delivery.time,'sleep'):
            self.assertEqual(delivery.advance(api,job,pending),'consumed')
        self.assertFalse(pending.exists())

    def test_changed_composer_at_last_key_check_suspends_without_blind_input(self):
        # Spec #1 L58-60,137 + issue #7 L45: last observation still owns the draft.
        from unittest.mock import patch, Mock
        from watchdog_app import pane_delivery as delivery
        from watchdog_app.store import atomic
        pending=self.root/'changed.pending.json'
        job=dict(pane='w11:p8',identity=['p','t','codex','s'],text='A',phase='materialized',
                 enter='Enter')
        atomic(pending,job)
        api=Mock()
        with patch.object(delivery,'live',return_value={'agent_status':'working','agent':'codex'}), \
             patch.object(delivery,'surface',side_effect=[['A'],['humano']]), patch.object(delivery.time,'sleep'):
            with self.assertRaisesRegex(RuntimeError,'rascunho mudou'):
                delivery.advance(api,job,pending)
        api.call.assert_not_called()
        self.assertEqual(json.loads(pending.read_text())['phase'],'uncertain')

    def test_lock_covers_delayed_consumption_and_both_notices_stay_whole(self):
        # Spec #1 L137,174: release after consumption, not after Enter exit zero.
        self.state['consume_delay']=.3;self.save()
        a=self.start(self.notice('pronto','--commit','abc1234','--testes','12 OK','--resumo','Feito'))
        self.wait_for('paste-started')
        b=self.start(self.notice('BLOQUEIO','--duvida','Qual aceite?'))
        self.finish(a);self.finish(b)
        self.assertEqual(self.actual()['submitted'],[
            '[T6 · painel w11:pE] T6 pronto: commit abc1234, testes 12 OK. Feito',
            '[T6 · painel w11:pE] BLOQUEIO: Qual aceite?'])

    def test_second_notice_is_saved_while_first_delivery_waits(self):
        # Spec #1 L59,174: pending A must not drop B or append B to a draft.
        self.state.update(draft='humano',status='working',wrap=True,needs_tab=True);self.save()
        def call(text):
            return [sys.executable,'-c',
                'from watchdog_app.pane_delivery import send; import sys; send("w11:p8",sys.argv[1],timeout=.4,background=False)',text]
        one=self.start(call('Aviso A'));two=self.start(call('Aviso B'))
        self.finish(one,success=False);self.finish(two,success=False)
        self.assertFalse(any(c[0]=='pane' for c in self.commands()))
        root=self.root/'xdg/herdr-watchdog/pane-locks'
        pending=list(root.glob('*.pending.json'))[0]
        queued=list(root.glob('*.queued.*.json'))
        self.assertEqual(len(queued),1)
        a=self.start([sys.executable,'-m','watchdog_app.pane_delivery','resume',str(pending)])
        b=self.start([sys.executable,'-m','watchdog_app.pane_delivery','resume',str(queued[0])])
        time.sleep(.15)
        current=self.actual();self.assertEqual(current['draft'],'humano')
        current['draft']='';p=self.root/'state-new.json';p.write_text(json.dumps(current));p.replace(self.root/'state.json')
        self.finish(a);self.finish(b)
        self.assertCountEqual(self.actual()['submitted'],['Aviso A','Aviso B'])

    def test_saved_waiter_delivers_after_human_finishes_without_repaste_or_resend(self):
        # T6 correction: durable waiting with a background worker, no caller retry.
        self.state['draft']='humano';self.save()
        self.send('Aviso salvo',success=False)
        pending=list((self.root/'xdg/herdr-watchdog/pane-locks').glob('*.pending.json'))[0]
        worker=self.start([sys.executable,'-m','watchdog_app.pane_delivery','resume',str(pending)])
        time.sleep(.15)
        current=self.actual();self.assertEqual(current['draft'],'humano')
        current['draft']='';(self.root/'state.json').write_text(json.dumps(current))
        self.finish(worker)
        self.assertEqual(self.actual()['submitted'],['Aviso salvo'])
        self.assertEqual(len([c for c in self.commands() if c[:2]==['pane','send-text']]),1)
