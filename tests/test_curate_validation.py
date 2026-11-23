from dataclasses import asdict, replace
import json
from pathlib import Path
import tempfile
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from test_actions import FakeBinding
from watchdog_app import curate
from watchdog_app.todo import Snapshot
from watchdog_app.todo_format import render
ID='9f4cdfb9-3b30-4d69-a178-aa3ff61301a6'
class CuratorValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.repo=Path(self.tmp.name)
        env=patch.dict(os.environ,{'WATCHDOG_STATE_DIR':str(self.repo/'state')});env.start();self.addCleanup(env.stop)
        (self.repo/'TODO.md').write_text('---\nwatchdog_todo: 1\n---\n## Next\n'+render('Colors',dict(id=ID,summary='Colors',origin='pedido-humano',execution='Details',acceptance='Verify colors')))
        self.snap=Snapshot.read(self.repo);self.log=self.repo/'real-selected.jsonl'
        self.binding=FakeBinding(history=str(self.log));self.session=SimpleNamespace(repo=self.repo,binding=self.binding,verify=lambda:None)
        self.reply('Colors implemented and tests passed.')
    def reply(self,text):self.log.write_text(json.dumps(dict(type='event_msg',payload=dict(type='task_complete',turn_id='t',last_agent_message=text)))+'\n')
    def output(self,quote):return dict(done=[dict(id=ID,evidence=quote)],blocked=[],add=[])
    def test_replay_is_labelled_and_never_calls_model_or_changes_task_before_selection(self):
        with patch.object(curate,'ask_codex',side_effect=AssertionError('no model')):
            result=curate.validate_existing(self.session,self.snap,self.output('Colors implemented and tests passed.'))
        self.assertEqual(result['observation'],'bounded-replay; no curator model invoked')
        self.assertEqual((self.repo/'TODO.md').read_bytes(),self.snap.raw)
        curate.apply_review(self.session,self.snap,result,set())
        self.assertEqual((self.repo/'TODO.md').read_bytes(),self.snap.raw)
        self.assertTrue(curate.apply_review(self.session,self.snap,result,{0}).tasks[0].done)
    def test_unsupported_and_contradicted_completion_withheld(self):
        for text in ['Colors still pending.','Colors implemented. Colors are not done.','Colors partially implemented.','Unrelated feature implemented.','Colors não concluído.','Colors implemented. Colors remains unfinished.']:
            result=curate.validate_proposals(self.output(text),self.snap,text)
            self.assertFalse(result['actions'],text);self.assertTrue(result['rejected'])
    def test_recipient_stale_source_and_partial_refused(self):
        result=curate.validate_existing(self.session,self.snap,self.output('Colors implemented and tests passed.'))
        self.session.binding=replace(self.binding,session='different')
        with self.assertRaises(RuntimeError):curate.apply_review(self.session,self.snap,result,{0})
        self.session.binding=self.binding
        with self.log.open('a') as f:f.write('{"type":')
        with self.assertRaises(RuntimeError):curate.apply_review(self.session,self.snap,result,{0})
        with self.assertRaises(RuntimeError):curate.validate_existing(self.session,self.snap,self.output('Colors implemented and tests passed.'))
    def test_duplicate_proposals_and_blocking_without_impediment_withheld(self):
        raw=self.output('Colors implemented and tests passed.');raw['done']*=2
        self.assertFalse(curate.validate_proposals(raw,self.snap,'Colors implemented and tests passed.')['actions'])
        raw=dict(done=[],blocked=[dict(id=ID,reason='Waiting',evidence='Colors are next.')],add=[])
        self.assertFalse(curate.validate_proposals(raw,self.snap,'Colors are next.')['actions'])

    def test_bound_conversation_cannot_apply_other_project_snapshot(self):
        self.session.repo=self.repo/'another-project'
        with self.assertRaises(RuntimeError):
            curate.validate_existing(self.session,self.snap,self.output('Colors implemented and tests passed.'))

    def test_qa_literal_counterexamples_and_uncertain_completion_are_withheld(self):
        cases=[
            'Colors tests passed, but the implementation does not work.',
            'Colors implemented. Ainda falta verificar o aceite.',
            'Colors tests passed for another project; this task has not been started.',
            'Colors implemented. Aguardando ajuda para commit.',
            'Colors concluído. Aguardando aceite do usuário.',
            'Colors implementado. Não funciona.',
            'Colors implementado. O aceite ainda não foi verificado.',
            'Colors tests passed.',
            'Colors works.',
            'Colors completed tests.',
            'Completed task: Colors dashboard.',
            'Complete task: Colors.',
            'Colors implemented. Waiting for help committing the changes.',
            'Colors implementado em outro projeto.',
            'Colors implemented. Acceptance verification remains.',
        ]
        for text in cases:
            with self.subTest(reply=text):
                result=curate.validate_proposals(self.output(text),self.snap,text)
                self.assertEqual(result['actions'],[])
                self.assertTrue(result['rejected'])

    def test_apply_revalidates_old_or_tampered_proposal_against_full_reply(self):
        for text in [
            'Colors tests passed, but the implementation does not work.',
            'Colors implemented. Ainda falta verificar o aceite.',
            'Colors tests passed for another project; this task has not been started.',
            'Colors implemented. Aguardando ajuda para commit/aceite.',
        ]:
            with self.subTest(reply=text):
                (self.repo/'TODO.md').write_bytes(self.snap.raw)
                self.reply(text)
                quote=text.split('.')[0]+'.' if '. ' in text else text
                raw=self.output(quote)
                result=curate.validate_existing(self.session,self.snap,raw)
                # Mimic a cached action produced by the previous permissive filter.
                result['actions']=[dict(kind='done',id=ID,evidence=quote)]
                with self.assertRaises(RuntimeError):
                    curate.apply_review(self.session,self.snap,result,{0})
                self.assertEqual((self.repo/'TODO.md').read_bytes(),self.snap.raw)

    def test_completion_requires_full_task_identity_not_a_shared_word(self):
        raw=self.snap.raw.replace(b'- [ ] Colors',b'- [ ] Colors dashboard')
        snapshot=Snapshot.parse(self.repo,raw)
        result=curate.validate_proposals(self.output('Colors implemented.'),snapshot,'Colors implemented.')
        self.assertFalse(result['actions']);self.assertTrue(result['rejected'])
        result=curate.validate_proposals(self.output('Colors dashboard is complete.'),snapshot,'Colors dashboard is complete.')
        self.assertEqual(len(result['actions']),1)

    def test_affirmative_task_completion_in_supported_formats_and_native_sources(self):
        for version in (0,1):
            for kind in ('codex','claude'):
                for quote in ('Colors implemented and tests passed.', 'Colors is complete.',
                              'Colors concluído e aceite verificado.', 'Colors finalizado.',
                              'Completed task: Colors.'):
                    with self.subTest(version=version,kind=kind,quote=quote):
                        raw=self.snap.raw if version else b'## Next\n- [ ] Colors\n'
                        (self.repo/'TODO.md').write_bytes(raw);snapshot=Snapshot.read(self.repo)
                        key=snapshot.tasks[0].id
                        if kind=='codex':self.reply(quote)
                        else:
                            self.log.write_text(json.dumps(dict(type='assistant',message=dict(id='m',stop_reason='end_turn',content=[dict(type='text',text=quote)])))+'\n')
                        self.session.binding=replace(self.binding,kind=kind)
                        output=dict(done=[dict(id=key,evidence=quote)],blocked=[],add=[])
                        result=curate.validate_existing(self.session,snapshot,output)
                        self.assertEqual(len(result['actions']),1,result['rejected'])
                        self.assertEqual((self.repo/'TODO.md').read_bytes(),raw)
                        self.assertTrue(curate.apply_review(self.session,snapshot,result,{0}).tasks[0].done)

    def test_qa_cases_are_revalidated_in_both_todo_and_transcript_formats(self):
        replies=[
            'Colors tests passed, but the implementation does not work.',
            'Colors implemented. Ainda falta verificar o aceite.',
            'Colors tests passed for another project; this task has not been started.',
            'Colors implemented. Aguardando ajuda para commit/aceite.',
        ]
        for version in (0,1):
            for kind in ('codex','claude'):
                for text in replies:
                    with self.subTest(version=version,kind=kind,reply=text):
                        raw=self.snap.raw if version else b'## Next\n- [ ] Colors\n'
                        (self.repo/'TODO.md').write_bytes(raw);snapshot=Snapshot.read(self.repo)
                        key=snapshot.tasks[0].id
                        self.session.binding=replace(self.binding,kind=kind)
                        if kind=='codex':self.reply(text)
                        else:
                            self.log.write_text(json.dumps(dict(type='assistant',message=dict(id='m',stop_reason='end_turn',content=[dict(type='text',text=text)])))+'\n')
                        output=dict(done=[dict(id=key,evidence=text)],blocked=[],add=[])
                        result=curate.validate_existing(self.session,snapshot,output)
                        self.assertFalse(result['actions']);self.assertTrue(result['rejected'])
                        result['actions']=[dict(kind='done',id=key,evidence=text)]
                        with self.assertRaises(RuntimeError):curate.apply_review(self.session,snapshot,result,{0})
                        self.assertEqual((self.repo/'TODO.md').read_bytes(),raw)

    def test_exact_uuid_can_identify_affirmative_completion(self):
        text='Task '+ID+' is complete.'
        self.reply(text);result=curate.validate_existing(self.session,self.snap,self.output(text))
        self.assertEqual(len(result['actions']),1,result['rejected'])
        self.assertTrue(curate.apply_review(self.session,self.snap,result,{0}).tasks[0].done)

    def test_blocking_qa_cases_and_fabricated_reasons_are_withheld_on_all_paths(self):
        cases=[
            ('Colors is not blocked.','Waiting for credentials'),
            ('Deployment is blocked because credentials expired.','Waiting for credentials'),
            ('Colors is blocked. Colors is no longer blocked; access restored.','Waiting for credentials'),
            ('Colors is blocked because credentials expired.','Waiting for approval'),
            ('Colors is blocked because credentials expired. Access restored.','credentials expired'),
            ('Colors não está bloqueado.','credenciais expiradas'),
            ('Colors is blocked because credentials are not expired.','credentials are not expired'),
            ('Colors is blocked because credentials expired. This blocker has been cleared.','credentials expired'),
            ('Colors is blocked because credentials expired. Approval granted.','credentials expired'),
            ('Colors está bloqueado porque as credenciais expiraram. Bloqueio resolvido.','as credenciais expiraram'),
        ]
        for version in (0,1):
            for text,reason in cases:
                with self.subTest(version=version,reply=text,reason=reason):
                    raw=self.snap.raw if version else b'## Next\n- [ ] Colors\n'
                    (self.repo/'TODO.md').write_bytes(raw);snapshot=Snapshot.read(self.repo);key=snapshot.tasks[0].id
                    self.reply(text)
                    output=dict(done=[],blocked=[dict(id=key,reason=reason,evidence=text)],add=[])
                    direct=curate.validate_proposals(output,snapshot,text)
                    self.assertEqual(direct['actions'],[]);self.assertTrue(direct['rejected'])
                    result=curate.validate_existing(self.session,snapshot,output)
                    self.assertFalse(result['actions'])
                    result['actions']=[dict(kind='blocked',id=key,reason=reason,evidence=text)]
                    with self.assertRaises(RuntimeError):curate.apply_review(self.session,snapshot,result,{0})
                    self.assertEqual((self.repo/'TODO.md').read_bytes(),raw)

    def test_blocking_current_specific_impediment_with_literal_reason_in_pt_and_en(self):
        cases=[
            ('Colors is blocked because credentials expired.','credentials expired'),
            ('Colors cannot run because login expired.','login expired'),
            ('Colors está bloqueado porque as credenciais expiraram.','as credenciais expiraram'),
            ('Colors não consegue prosseguir porque o acesso foi negado.','o acesso foi negado'),
            ('Task '+ID+' is blocked because credentials are missing.','credentials are missing'),
        ]
        for version in (0,1):
            for text,reason in cases:
                with self.subTest(version=version,reply=text):
                    raw=self.snap.raw if version else b'## Next\n- [ ] Colors\n'
                    (self.repo/'TODO.md').write_bytes(raw);snapshot=Snapshot.read(self.repo);key=snapshot.tasks[0].id
                    # Version 0 has a snapshot identity rather than the v1 UUID.
                    text=text.replace(ID,key);self.reply(text)
                    output=dict(done=[],blocked=[dict(id=key,reason=reason,evidence=text)],add=[])
                    result=curate.validate_existing(self.session,snapshot,output)
                    self.assertEqual(len(result['actions']),1,result['rejected'])
                    self.assertEqual((self.repo/'TODO.md').read_bytes(),raw)
                    curate.apply_review(self.session,snapshot,result,set())
                    self.assertEqual((self.repo/'TODO.md').read_bytes(),raw)
                    self.assertEqual(curate.apply_review(self.session,snapshot,result,{0}).tasks[0].section,'Blocked')

    def test_apply_rejects_adulterated_block_reason_and_unquoted_resolution(self):
        for source,quote,reason in [
            ('Colors is blocked because credentials expired.', 'Colors is blocked because credentials expired.', 'Waiting for approval'),
            ('Colors is blocked because credentials expired. Access restored.', 'Colors is blocked because credentials expired.', 'credentials expired'),
        ]:
            with self.subTest(source=source,reason=reason):
                (self.repo/'TODO.md').write_bytes(self.snap.raw);self.reply(source)
                output=dict(done=[],blocked=[dict(id=ID,reason=reason,evidence=quote)],add=[])
                result=curate.validate_existing(self.session,self.snap,output)
                result['actions']=[dict(kind='blocked',id=ID,reason=reason,evidence=quote)]
                with self.assertRaises(RuntimeError):curate.apply_review(self.session,self.snap,result,{0})
                self.assertEqual((self.repo/'TODO.md').read_bytes(),self.snap.raw)

    def test_blocker_gate_with_claude_and_codex_records_in_both_todo_formats(self):
        for version in (0,1):
            for kind in ('codex','claude'):
                for resolved in (False,True):
                    with self.subTest(version=version,kind=kind,resolved=resolved):
                        raw=self.snap.raw if version else b'## Next\n- [ ] Colors\n'
                        (self.repo/'TODO.md').write_bytes(raw);snapshot=Snapshot.read(self.repo);key=snapshot.tasks[0].id
                        quote='Colors is blocked because credentials expired.'
                        text=quote+(' Access restored.' if resolved else '')
                        self.session.binding=replace(self.binding,kind=kind)
                        if kind=='codex':self.reply(text)
                        else:self.log.write_text(json.dumps(dict(type='assistant',message=dict(id='m',stop_reason='end_turn',content=[dict(type='text',text=text)])))+'\n')
                        output=dict(done=[],blocked=[dict(id=key,reason='credentials expired',evidence=quote)],add=[])
                        result=curate.validate_existing(self.session,snapshot,output)
                        self.assertEqual(len(result['actions']),0 if resolved else 1,result['rejected'])
                        if resolved:
                            result['actions']=[dict(kind='blocked',id=key,reason='credentials expired',evidence=quote)]
                            with self.assertRaises(RuntimeError):curate.apply_review(self.session,snapshot,result,{0})
                            self.assertEqual((self.repo/'TODO.md').read_bytes(),raw)
                        else:self.assertEqual(curate.apply_review(self.session,snapshot,result,{0}).tasks[0].section,'Blocked')
