---
number: 35
title: "Progress mostra executor ativo como Bloqueado com JSON cru"
state: open
labels: ["bug", "needs-triage"]
url: https://github.com/viniabdalla/herdr-watchdog/issues/35
blocked_by: []
updated: 2026-11-26
---

## Contexto

Encontrado na rodada A/B/C do aceite T14 (#15). Evidências: `.watchdog/run/2026-11-26/T14-w14-*.json` (rodada A/B/C do aceite T14 no projeto descartável `test-watchdog-erase`, workspace `w14`).

## O que acontece

Com o executor de T1 trabalhando no `w14:p6` (o herdr mostrava `codex working`), o Progress mostrou:

```
● T1 · w14:p6 · Bloqueado · 49,2k/475k ▰▱▱▱▱▱▱▱▱▱ 10% · { [ir] [unblock]
```

A tarefa aparece na seção BLOQUEADOS, e no lugar do motivo vem o início de um JSON (`{"`, depois `{`). Pode ter relação com a abertura marcada como failed (#34) e com a entrega sem trava.

## O que construir

O Progress mostra o executor ativo como trabalhando. Um motivo de bloqueio que não é texto legível nunca aparece cru.

## Critérios de aceite

- [ ] Um executor com o herdr em `working` aparece como trabalhando, fora de BLOQUEADOS, salvo bloqueio explícito.
- [ ] Um motivo que vier como JSON ou estrutura é resumido em texto ou omitido, nunca mostrado cru.


## Comentários
