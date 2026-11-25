---
number: 3
title: "T2 — Nomes Review Curator e Verify Leader"
state: closed
labels: [ready-for-agent]
url: https://github.com/viniabdalla/herdr-watchdog/issues/3
parent: 1
blocked_by: []
updated: 2026-11-25
---

## Parent

#1

## What to build

No Tasks, a revisão das propostas do curador passa a se chamar Review Curator e o pedido de verificação ao líder passa a se chamar Verify Leader, para não confundir com o code review.

## Acceptance criteria

- [ ] O Tasks mostra Review Curator e Verify Leader nos botões, dicas e prévias.
- [ ] O README usa os nomes novos.
- [ ] Os testes do Tasks passam nos dois modos de controles.

## Comentários

### 2026-11-25 · viniabdalla

Os botões, dicas e prévias do Tasks usam **Review Curator** e **Verify Leader**. O README identifica as duas ações. Conferi os rótulos no pane real do Tasks depois de recarregar a integração.

Commit do executor `f5b9bbc`, integrado em `a34066b`. A suíte unittest executou 548 testes em cada modo de controles, com 7 ignorados e nenhuma falha em ambos.
