---
number: 33
title: "Curador mostra falha em estados transitórios depois do /clear"
state: open
labels: ["bug", "needs-triage"]
url: https://github.com/viniabdalla/herdr-watchdog/issues/33
blocked_by: []
updated: 2026-11-26
---

## Contexto

Encontrado na rodada A/B/C do aceite T14 (#15). Evidências: `.watchdog/run/2026-11-26/T14-w14-*.json` (rodada A/B/C do aceite T14 no projeto descartável `test-watchdog-erase`, workspace `w14`).

## O que acontece

Depois do `/clear` no Claude (`w14:p1`), o Tasks seguiu sozinho da sessão `293f2207` para a `15dbea79`, como esperado. A linha do curador, porém, mostrou `Codex review failed: Conversation identity is unavailable: the watched co…` até a sessão nova ter a primeira resposta concluída.

Antes disso, logo ao abrir o layout, a mesma linha mostrou `Codex review failed: Evidence source changed during review` enquanto o TODO ainda era escrito.

## O que construir

Num estado transitório previsível (sessão nova ainda sem resposta, TODO mudando durante a revisão), o curador mostra espera, não falha.

## Critérios de aceite

- [ ] Logo depois do `/clear`, a linha do curador diz que aguarda a primeira resposta da sessão nova.
- [ ] Uma mudança do TODO durante a revisão gera uma nova tentativa, não "review failed".
- [ ] Falhas reais continuam aparecendo como falha.


## Comentários
