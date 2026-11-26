---
number: 31
title: "Seleção guarda tarefas que sumiram do TODO e trava o despacho"
state: open
labels: ["bug", "needs-triage"]
url: https://github.com/viniabdalla/herdr-watchdog/issues/31
blocked_by: []
updated: 2026-11-26
---

## Contexto

Encontrado na rodada A/B/C do aceite T14 (#15). Evidências: `.watchdog/run/2026-11-26/T14-w14-*.json` (rodada A/B/C do aceite T14 no projeto descartável `test-watchdog-erase`, workspace `w14`).

## O que acontece

1. Selecionei A, B e C no Tasks e cancelei a prévia.
2. O TODO foi reescrito com IDs novos para as mesmas tarefas.
3. Ao selecionar de novo, o Tasks mostrou **6 task(s) selected**, com 3 marcadas na tela.
4. Ao apertar p: `Selection is empty, completed or no longer matches the task list`.

Os IDs antigos ficaram em `self.selected`, e não dá para desmarcá-los pela tela porque não aparecem. O despacho só destravou matando e reabrindo o painel Tasks.

## O que construir

Quando o TODO muda, a seleção descarta as identidades que não existem mais e avisa quantas saíram.

## Critérios de aceite

- [ ] Depois de uma releitura do TODO, a contagem de selecionadas mostra só tarefas existentes e abertas.
- [ ] O aviso informa quantas seleções foram descartadas.
- [ ] A seleção das tarefas que continuam existindo é preservada.
- [ ] Teste: selecionar, trocar os IDs no TODO e apertar p abre a prévia só com as tarefas atuais.


## Comentários
