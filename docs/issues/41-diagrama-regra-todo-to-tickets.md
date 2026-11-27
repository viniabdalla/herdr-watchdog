---
number: 41
title: "Atualizar o diagrama regra-todo para o gatilho no /to-tickets"
state: closed
labels: ["ready-for-agent"]
url: https://github.com/viniabdalla/herdr-watchdog/issues/41
blocked_by: [38, 39]
updated: 2026-11-26
---

## What to build

Origem: pesquisa `docs/pesquisa-regra-do-todo-2026-11-26.md`, recomendação aprovada pelo Vini em 2026-11-26.

Atualizar o diagrama `workflow/archify/regra-todo.html`.

## Acceptance criteria

- [x] O TODO sai de `/to-spec` e passa a nascer em `/to-tickets`, pelo gatilho em `docs/agents/issue-tracker.md`.
- [x] O diagrama mostra `docs/agents/todo.md` como regra, os modelos em `docs/templates` e o global só com o git-todo e a linha de ponteiro.
- [x] O `finalize` do Archify passa em todas as verificações.


## Comentários

### 2026-11-26 · viniabdalla (via Claude)

Concluído no commit b327fa9 (feat/tasks-somente-leitura, local). workflow/archify/regra-todo.html refeito: o TODO nasce no /to-tickets pelo issue-tracker.md, docs/agents/todo.md define a regra, modelos em docs/templates. O finalize do Archify passou em validate, deliver, check e browser-check.
