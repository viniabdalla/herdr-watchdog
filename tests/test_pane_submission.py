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
        # T6 correction: Tab/second Enter require the own exact message again.
        self.state.update(alter_on_enter=True,status='working');self.save()
        self.send('aviso',success=False)
        self.assertEqual(self.actual()['draft'],'edição humana')
        self.assertEqual(self.actual()['keys'],['enter'])
        self.assertEqual(self.actual()['submitted'],[])

    def test_collapsed_paste_without_exact_materialization_sends_no_enter(self):
        # T6 correction: hidden paste bytes cannot be confirmed by matching a label.
        self.state['collapsed']=True;self.save()
        self.send('texto longo',success=False)
        self.assertEqual(self.actual()['draft'],'texto longo')
        self.assertEqual(self.actual().get('keys',[]),[])

    def test_blocked_agent_receives_no_input(self):
        self.state['status']='blocked';self.save()
        self.send('aviso',success=False)
        self.assertFalse(any(c[0]=='pane' for c in self.commands()))

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
