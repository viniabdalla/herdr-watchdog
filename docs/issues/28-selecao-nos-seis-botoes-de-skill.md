---
number: 28
title: "Levar a seleção aos seis botões de skill do Tasks"
state: open
labels: [ready-for-agent]
url: https://github.com/viniabdalla/herdr-watchdog/issues/28
parent: 24
blocked_by: []
updated: 2026-11-25
---

## Spec

#24 · comportamentos 1 a 4 e critérios de aceite.

## Entrega

Ao abrir grill-with-docs, to-spec, to-tickets, retro, code-review ou merge-danger, a pessoa vê na prévia quais tarefas chegarão à conversa do líder. Com a seleção vazia, a skill continua no assunto da conversa.

## Aceite

Conferir a prévia e a mensagem entregue a um líder simulado em terminal isolado, com o prefixo de Claude e de Codex, para as seis skills.

- [ ] Com zero tarefas marcadas e o cursor sobre uma linha, enviar o comando habitual com seus argumentos, sem acrescentar tarefa.
- [ ] Com A marcada e o cursor em B, mostrar e enviar o caminho do TODO da worktree, o título e o ID de A.
- [ ] Com várias marcadas, incluir apenas essas tarefas na ordem do painel. Títulos iguais continuam distinguíveis pelos IDs.
- [ ] Em todos os casos, code-review conserva o intervalo do grupo e to-tickets conserva o caminho da spec quando disponíveis. Conferir também os avisos próprios quando faltarem dados.
- [ ] Enter entrega uma vez o texto exibido, inclusive após edição. Esc cancela a prévia sem envio. Abrir e cancelar preservam a seleção e o grupo.

## Dependências

Pode começar imediatamente e em paralelo com a troca de pasta.
