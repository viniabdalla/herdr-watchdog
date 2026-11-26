---
number: 27
title: "Despachar ao mesmo líder depois de trocar a pasta"
state: open
labels: [ready-for-agent]
url: https://github.com/viniabdalla/herdr-watchdog/issues/27
parent: 25
blocked_by: [26]
updated: 2026-11-25
---

## Spec

#25 · itens 3 e 4, aceites (a) e (c).

## Entrega

O líder já ligado em A continua recebendo os despachos depois que o Tasks passa para B. A mensagem identifica a pasta atual do Tasks, inclusive quando o líder já recebeu a meta do grupo.

## Aceite

- [ ] Em recursos isolados, ligar o líder em A, trocar a aba para B, marcar uma tarefa de B e confirmar o primeiro despacho. Conferir na mensagem recebida a tarefa e o caminho de B, na mesma conversa.
- [ ] Repetir com um grupo que já tem meta nessa conversa. A atualização incremental também leva o caminho de B. Ao voltar para A, o próximo despacho leva o caminho de A.
- [ ] Religar mantém a conferência de identidade. Se o líder começou em A e o Tasks está em B, uma religação recusada identifica as duas pastas e orienta voltar a A ou abrir um líder em B.
- [ ] Toda recusa de despacho ou religação explica o motivo e o próximo passo na tela. Conferir que as ações preservam os painéis da outra aba e o state.db compartilhado.
