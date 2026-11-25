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
