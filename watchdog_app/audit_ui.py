"""Portuguese Tasks controls for independent project audits; no TODO selection needed."""
from dataclasses import asdict
from . import audit
from .accounts import account_labels


def status_rows(value):
    state = {'launching': 'Abrindo', 'running': 'Em andamento', 'completed': 'Concluída',
             'failed': 'Falhou', 'uncertain': 'Incerta · inspecione antes de tentar novamente'}[value['state']]
    delivery = {'pending': 'pendente', 'busy': 'líder ocupado · entrega manual pendente',
                'stale': 'destinatário indisponível', 'stale_source': 'projeto mudou · relatório histórico', 'sending': 'incerta · envio iniciado',
                'uncertain': 'incerta · não reenviar', 'sent': 'entregue'}[value['delivery']]
    return [f"Auditoria {value['audit_id']} · {state}",
            'Modelo solicitado: ' + value['requested_model'],
            'Modelo efetivo: ' + (value.get('effective_model') or 'ainda não confirmado'),
            'Relatório: ' + value['report_file'], 'Entrega: ' + delivery,
            *([value['problem']] if value.get('problem') else []),
            *([value['delivery_problem']] if value.get('delivery_problem') else [])]


class AuditUI:
    def __init__(self, session, store=None):
        session.verify()
        if session.binding.kind != 'codex':
            raise RuntimeError('Auditoria requer líder Codex verificado')
        self.recipient = asdict(session.binding)
        self.store = store or audit.AuditStore()
        self.accounts = audit.accounts(session)
        self.labels = account_labels(self.accounts)
        self.inventory = []; self.account = None; self.model = None
        self.stage = 'accounts'; self.values = []
        self.refresh(session)

    def refresh(self, session):
        # Do not show another owner's audit as if it belonged to this conversation.
        self.values = [audit.inspect(self.store, value['audit_id']) for value in self.store.list(session.repo)
                       if value['recipient'] == self.recipient]

    def rows(self):
        rows = [('Auditoria independente · somente leitura', 'In progress', None)]
        if self.stage == 'accounts':
            rows.append(('Escolha a conta Codex para consultar os modelos disponíveis:', None, None))
            for i, account in enumerate(self.accounts):
                rows.append((self.labels[i] + ' · ' + account, None, ('account', i)))
            if not self.accounts: rows.append(('Nenhuma conta Codex verificada neste projeto.', 'Blocked', None))
            for value in self.values:
                rows.append(('', None, None))
                for line in status_rows(value): rows.append((line, None, None))
                if value['state'] == 'completed' and value['delivery'] in ('busy', 'stale', 'pending'):
                    rows.append(('Entregar ao líder original · confirmar', None, ('deliver', value['audit_id'])))
        elif self.stage == 'models':
            rows.append(('Conta: ' + self.account, None, None))
            if not audit.preferred(self.inventory):
                rows.append(('GPT Astra 6.1 não listado. Escolha explicitamente outro modelo.', None, None))
            for model in self.inventory:
                rows.append((model['label'] + ' · ' + model['model'], None, ('model', model['model'])))
            if not self.inventory: rows.append(('Nenhum modelo listado; abertura indisponível.', 'Blocked', None))
        elif self.stage == 'confirm':
            rows.extend([(line, None, None) for line in (
                'Confirmar nova auditoria', 'Conta: ' + self.account, 'Modelo solicitado: ' + self.model,
                'Modelo efetivo será confirmado pelo provedor antes da execução.',
                'Nova aba Herdr · nova sessão limpa · diretório atual do projeto.',
                'Somente leitura · sem escalada de aprovação · sem conversa do líder.',
                'Relatório com evidências, lacunas e próximos passos para o líder original.',
                'TODO permanece aberto. Concluir auditoria não aceita nem integra código.',
                'y/Enter: abrir · Esc: cancelar')])
        elif self.stage == 'deliver':
            rows.extend([(line, None, None) for line in (
                'Confirmar entrega ao líder original', 'Auditoria: ' + self.delivery_id,
                'Líder ocupado ou substituído preserva o relatório sem envio.',
                'Entrega incerta não será repetida.', 'y/Enter: entregar · Esc: cancelar')])
        return rows

    def choose(self, identity):
        kind, value = identity
        if kind == 'account':
            self.account = self.accounts[value]
            self.inventory = audit.models(self.account)
            self.stage = 'models'
            preferred = audit.preferred(self.inventory)
            return next((i for i, m in enumerate(self.inventory) if m['model'] == preferred), 0)
        if kind == 'model':
            self.model = value; self.stage = 'confirm'
        if kind == 'deliver':
            self.delivery_id = value; self.stage = 'deliver'
        return 0

    def confirm(self, session):
        session.verify()
        if asdict(session.binding) != self.recipient:
            raise RuntimeError('Líder mudou; cancele e abra novamente a auditoria')
        if self.stage == 'deliver':
            value = audit.deliver(self.store, self.delivery_id)
            return ' · '.join(status_rows(value)[:1]) + ' · entrega: ' + value['delivery']
        value = audit.launch(session, self.account, self.model, confirmed=True, store=self.store)
        return 'Auditoria ' + value['audit_id'] + ' · abrindo nova aba · A: acompanhar relatório'
