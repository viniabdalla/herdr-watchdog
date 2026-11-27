---
number: 42
title: "Preparar projeto novo com a regra e o gatilho do TODO"
state: closed
labels: ["ready-for-agent"]
url: https://github.com/viniabdalla/herdr-watchdog/issues/42
blocked_by: [38, 39]
updated: 2026-11-26
---

## What to build

Origem: pesquisa `docs/pesquisa-regra-do-todo-2026-11-26.md`, recomendação aprovada pelo Vini em 2026-11-26.

Fechar a lacuna dos projetos novos: preparar um projeto para o Watchdog instala o ponteiro `### TODO` no `AGENTS.md`, o `docs/agents/todo.md` e a seção do gatilho em `docs/agents/issue-tracker.md`, a partir de `docs/templates/`. A pesquisa aponta o comando existente `watchdog project-instructions` como ponto de partida.

## Acceptance criteria

- [ ] Num projeto sem esses arquivos, a preparação cria só o que falta, com prévia e confirmação.
- [ ] Arquivos existentes nunca são sobrescritos. Seção ausente é acrescentada.
- [ ] Sem `docs/agents/issue-tracker.md`, a preparação avisa para rodar `/setup-matt-pocock-skills` e não inventa o arquivo.
- [ ] Testes isolados cobrem criação, preservação e aviso.


## Comentários

### 2026-11-27T01:41:47Z · viniabdalla

T20 concluído: commit 7f6dd8c (executor Codex w11:p18), integrado em 93e7238 na feat/tasks-somente-leitura. Testes na integração: 772 por modo, OK, 7 ignorados, nos dois modos (com e sem WATCHDOG_FULL_CONTROLS). watchdog project-instructions preview/apply instala o ponteiro ### TODO no AGENTS.md, docs/agents/todo.md com esqueleto local e o gatilho no docs/agents/issue-tracker.md; avisa se o tracker faltar, sem criá-lo.
