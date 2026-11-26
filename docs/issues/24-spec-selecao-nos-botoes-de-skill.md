---
number: 24
title: "Spec: botões de skill do Tasks usam as tarefas marcadas"
state: open
labels: [ready-for-agent]
url: https://github.com/viniabdalla/herdr-watchdog/issues/24
blocked_by: []
updated: 2026-11-25
---

## Problema

Ao marcar uma tarefa e abrir uma skill pelo Tasks, o líder recebe o comando sem a referência à tarefa. O usuário precisa explicar qual item escolheu. Isso foi reproduzido com grill-with-docs.

## Comportamento

1. A regra vale para os seis botões de skill do Tasks disponíveis no harness do líder: `grill-with-docs`, `to-spec`, `to-tickets`, `retro`, `code-review` e `merge-danger`.
2. Com tarefas marcadas, a prévia do comando inclui o caminho do TODO da worktree e o título e ID de cada tarefa marcada, na ordem do painel. A linha sob o cursor só entra quando sua caixa está marcada.
3. Com a seleção vazia, a skill segue na conversa atual do líder. O Tasks abre a prévia habitual, com os argumentos próprios da skill. Por exemplo, grill-with-docs recebe apenas o comando. Code-review conserva o intervalo de commits do grupo e to-tickets conserva a spec quando já preenchida. Esses argumentos também acompanham a seleção quando há tarefas marcadas.
4. O usuário pode editar a prévia. Confirmar entrega o texto exibido ao líder. Esc cancela. A seleção e o grupo são preservados ao abrir ou cancelar a prévia.

## Aceite

Verificar pelos botões ou atalhos do Tasks em terminal isolado. Observar a prévia e a mensagem entregue a um líder simulado em Claude e Codex, usando o prefixo do harness.

- [ ] **Zero marcadas.** Para cada uma das seis skills, deixar o cursor sobre uma tarefa e abrir a prévia. Confirmar entrega o comando habitual com seus argumentos e sem referência a tarefas.
- [ ] **Uma marcada.** Marcar A, mover o cursor para B e abrir cada skill. A prévia e a entrega identificam somente A pelo título, ID e caminho do TODO.
- [ ] **Várias marcadas.** Abrir cada skill com duas tarefas marcadas, inclusive com títulos iguais. Seus IDs aparecem na ordem do painel e as desmarcadas ficam de fora.
- [ ] **Argumentos próprios.** Com zero, uma ou várias marcadas, conferir o intervalo de code-review e o caminho da spec de to-tickets quando disponíveis. Manter os avisos existentes quando faltarem dados.
- [ ] **Edição e cancelamento.** Confirmar entrega o texto editado uma vez. Esc encerra a prévia sem enviar mensagem. Conferir que as marcações e o grupo continuam como estavam.

Esta regra se aplica à faixa de skills da #8. Despachar, Implementar aqui e Verify Leader conservam suas regras de seleção.
