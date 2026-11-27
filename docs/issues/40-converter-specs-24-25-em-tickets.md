---
number: 40
title: "Converter as specs #24 e #25 do TODO nos tickets #26, #27 e #28"
state: closed
labels: ["ready-for-agent"]
url: https://github.com/viniabdalla/herdr-watchdog/issues/40
blocked_by: [38]
updated: 2026-11-26
---

## What to build

Origem: pesquisa `docs/pesquisa-regra-do-todo-2026-11-26.md`, recomendação aprovada pelo Vini em 2026-11-26.

Aplicar a regra corrigida ao `TODO.md` deste repositório.

## Acceptance criteria

- [x] `[Spec #25] Trocar a pasta dos painéis` vira os itens dos tickets #26 e #27, com o #27 `Bloqueado por: #26` no formato aceito.
- [x] `[Spec #24] Botões de skill` vira o item do ticket #28.
- [x] Os IDs dos itens antigos não são reaproveitados. `watchdog todo validate --repo .` passa e o Tasks mostra os itens.


## Comentários

### 2026-11-26 · viniabdalla (via Claude)

Concluído no commit b327fa9 (feat/tasks-somente-leitura, local). [Spec #25] virou T21 (#26) e T22 (#27, Bloqueado por: T21 (#26).); [Spec #24] virou T23 (#28). IDs novos. classify() do Watchdog mostra T22 esperando T21 e T21/T23 livres. `watchdog todo validate` passa.
