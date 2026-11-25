---
number: 7
title: "T6 — Trava por pane e aviso do executor"
state: open
labels: [ready-for-agent]
url: https://github.com/viniabdalla/herdr-watchdog/issues/7
parent: 1
blocked_by: [2]
updated: 2026-11-25
---

## Parent

#1

## What to build

Toda escrita no pane do líder, vinda do Tasks ou de executores, escreve o texto, dá Enter e só então libera. Os executores ganham um comando de aviso pronto ou BLOQUEIO que já usa a trava, para que dois avisos nunca se misturem com a meta.

## Acceptance criteria

- [ ] Dois avisos simultâneos chegam como duas mensagens inteiras.
- [ ] Um texto do Tasks e um aviso simultâneos não se misturam.
- [ ] O comando de aviso aceita pronto (commit, testes, resumo) e BLOQUEIO (dúvida).
- [ ] O padrão do dispatch passa a usar esse comando no contrato.
- [ ] Testes no ponto de teste B com Herdr falso cobrem os cenários.

## Comentários

### 2026-11-25 · viniabdalla

A entrega do texto e do Enter passa pela mesma trava por pane nos avisos, no despacho e no Verify Leader. Testes concorrentes com Herdr falso verificam mensagens inteiras e falhas de entrega.

Commit do executor `f234e37`, integrado em `bc609c1`. A suíte executou 563 testes em cada modo de controles, com 7 ignorados e nenhuma falha.

### 2026-11-25 · viniabdalla

Reaberto após observação na rodada real: o Codex ocupado deixou o rascunho no editor depois do Enter e recebeu o aviso seguinte dentro do texto anterior. A trava serializou as chamadas ao Herdr, mas os dois eventos não chegaram como mensagens independentes. A correção e o teste de regressão seguem com o executor T6.
