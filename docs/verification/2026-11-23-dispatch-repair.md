# Correção dos bloqueios de dispatch

Comportamento aprovado pelo usuário em 2026-11-23: QA novo por revisão sem encerrar
atores anteriores; equipe pode tratar tarefas selecionadas como pacote explícito.

## Comandos

- `watchdog mission renew-qa --run UUID --candidate SHA --confirm`: somente equipe
  nativa ativa, com resultados commitados e revisão anterior encerrada/confirmada.
  Cria worktree e pane novos na aba existente, mantém os anteriores em `qa_history`,
  usa uma nova identidade nativa e broker separado. Não reutiliza contexto do QA.
- `watchdog mission prepare-team --run UUID --confirm`: somente solicitação ainda
  sem atores, entregas ou tentativa de execução. Registra agrupamento e checkpoint
  Git atual limpo; conserva checkpoint anterior e todos os IDs selecionados.
  Regenerar o template/brief depois desta confirmação.
- Orchestrate de várias tarefas confirma uma entrega conjunta. O contrato contém
  todos os membros e suas dependências, com uma tentativa comum. Resultado parcial
  é recusado; correções atualizam todos os membros. A API de tarefas separadas e
  seus contratos anteriores não mudam silenciosamente.

## Verificação

Os testes reproduziram a falta de comandos, ausência de tentativa nos membros do
pacote e ausência de agrupamento explícito. Cobertura usa Git e ledger temporários,
substituindo somente a fronteira Herdr/identidade/fila: preservação do QA anterior,
worktree/pane novos, confirmação, startup incerto sem retry, resultado completo,
follow-up conjunto e restrição a solicitações ainda não iniciadas.

Nenhum comando fecha TODO, relaxa a revisão do candidato exato ou encerra agentes.
Falhas de provisionamento conservam recursos e intenção para inspeção.

Suíte do controlador em 2026-11-23: `python3 -B -m unittest discover -s tests -q`
— 441 testes, sem falhas, 7 ignorados (58,626 s). Seis testes novos de manutenção
passaram. Os testes de escopo legados e agrupamento também foram repetidos após
preservar o agrupamento explícito na API e confirmar o pacote pela interface.
