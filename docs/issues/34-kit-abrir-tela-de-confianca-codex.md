---
number: 34
title: "kit abrir para na tela de confiança do Codex e entrega o contrato sem trava"
state: open
labels: ["bug", "needs-triage"]
url: https://github.com/viniabdalla/herdr-watchdog/issues/34
blocked_by: []
updated: 2026-11-26
---

## Contexto

Encontrado na rodada A/B/C do aceite T14 (#15). Evidências: `.watchdog/run/2026-11-26/T14-w14-*.json` (rodada A/B/C do aceite T14 no projeto descartável `test-watchdog-erase`, workspace `w14`).

## O que acontece

O líder Claude abriu o executor de T1 com `watchdog kit abrir` numa pasta nova (`test-watchdog-erase/.worktrees/T1`), conforme o relato dele:

- O Codex parou na tela de confiança da pasta. O líder aceitou à mão.
- O kit marcou a abertura como **failed**.
- Como o Codex ainda não tinha sessão registrada, o líder entregou o contrato com `herdr agent prompt`, sem passar pela trava por pane.

## O que construir

- O kit reconhece a tela de confiança da pasta do Codex. Aceita quando a pasta é a worktree que o próprio kit acabou de criar, ou avisa o líder com instrução clara.
- O kit espera o registro da sessão antes de declarar falha, e a entrega do contrato passa pela trava.

## Critérios de aceite

- [ ] Abrir um executor numa worktree nova, com tela de confiança, termina com sucesso, sem intervenção manual.
- [ ] O status `failed` só aparece quando o executor realmente não subiu.
- [ ] O contrato é entregue pela trava por pane mesmo na primeira abertura.


## Comentários
