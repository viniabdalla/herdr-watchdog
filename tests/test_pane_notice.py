"""Executor CLI validation at the real process boundary."""
from pane_submission_fixture import SubmissionFixture


class PaneNoticeTests(SubmissionFixture):
    def test_incomplete_ready_notice_is_rejected_without_sending(self):
        # Spec #1 L80: ready requires commit, tests and summary.
        self.finish(self.start(self.notice('pronto','--resumo','Sem evidência')),success=False)
        self.assertEqual(self.commands(),[])

    def test_cli_ready_and_blocker_submit_as_whole_messages(self):
        # Spec #1 L60,80,174: the shared CLI reports one complete event.
        self.finish(self.start(self.notice('pronto','--commit','abc1234','--testes','12 OK','--resumo','Feito')))
        self.finish(self.start(self.notice('BLOQUEIO','--duvida','Qual aceite?')))
        self.assertEqual(self.actual()['submitted'],[
            '[T6 · painel w11:pE] T6 pronto: commit abc1234, testes 12 OK. Feito',
            '[T6 · painel w11:pE] BLOQUEIO: Qual aceite?'])
