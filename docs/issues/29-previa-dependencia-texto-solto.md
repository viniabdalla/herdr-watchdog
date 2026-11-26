---
number: 29
title: "Prévia do despacho classifica errado dependências em texto solto, sem aviso"
state: open
labels: ["bug", "needs-triage"]
url: https://github.com/viniabdalla/herdr-watchdog/issues/29
blocked_by: []
updated: 2026-11-26
---

## Contexto

Encontrado na rodada A/B/C do aceite T14 (#15). Evidências: `.watchdog/run/2026-11-26/T14-w14-*.json` (rodada A/B/C do aceite T14 no projeto descartável `test-watchdog-erase`, workspace `w14`).

## O que acontece

Num TODO sem formato estruturado, a prévia do despacho (p) leu as dependências escritas em texto solto e classificou errado, sem nenhum aviso:

- `B — Média … (depende de A) → [docs/issues/B-media.md](...)` saiu como **depende do Vini**. O regex capturou `A) → [docs/issues/B-media.md](...)` como referência, não achou tarefa com esse nome e tratou como pendência humana.
- `C — Dividir … (aguarda o Vini)` saiu como **livre**, porque "aguarda" não é palavra-chave.

Confirmar com y teria despachado C como livre.

## O que construir

- Quando uma referência de bloqueio não casa com nenhuma tarefa, a prévia mostra "referência não reconhecida: <texto>" em vez de "depende do Vini".
- A prévia avisa quando a tarefa não usa a convenção explícita (`Bloqueado por: T1`), apontando o formato esperado.

## Critérios de aceite

- [ ] Uma referência que não casa com nenhuma tarefa aparece como não reconhecida, com o texto capturado, e não como "depende do Vini".
- [ ] Um TODO sem formato estruturado com texto de dependência mostra um aviso com a convenção esperada.
- [ ] A convenção atual (`Bloqueado por: T1.`, `Bloqueado por: decisão do Vini…`) continua classificando T1 livre, T2 "espera outra da seleção" e T3 "depende do Vini", como na rodada.


## Comentários
