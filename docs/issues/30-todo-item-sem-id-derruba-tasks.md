---
number: 30
title: "Um item do TODO sem ID derruba o Tasks inteiro"
state: open
labels: ["bug", "needs-triage"]
url: https://github.com/viniabdalla/herdr-watchdog/issues/30
blocked_by: []
updated: 2026-11-26
---

## Contexto

Encontrado na rodada A/B/C do aceite T14 (#15). Evidências: `.watchdog/run/2026-11-26/T14-w14-*.json` (rodada A/B/C do aceite T14 no projeto descartável `test-watchdog-erase`, workspace `w14`).

## O que acontece

Num TODO com `watchdog_todo: 1`, dois itens em `## Feito` sem o campo `ID` derrubaram o painel inteiro:

```
Cannot read TODO.md: TODO linha 51: campo obrigatório ausente: ID
TODO.md is unavailable. Create or fix it in the project folder.
```

As três tarefas abertas, que estavam corretas, sumiram junto. Depois da correção, o aviso antigo continuou na tela por um ciclo.

## O que construir

Um item inválido não tira do ar as tarefas válidas. O painel aponta a linha e o campo e continua mostrando o resto.

## Critérios de aceite

- [ ] Com um item `## Feito` sem ID, o Tasks mostra as tarefas abertas válidas e um aviso com a linha e o campo.
- [ ] A seleção e o despacho continuam recusando um item inválido.
- [ ] O aviso some na primeira leitura válida do TODO.


## Comentários
