---
number: 39
title: "Gatilho do TODO no docs/agents/issue-tracker.md"
state: open
labels: ["ready-for-agent"]
url: https://github.com/viniabdalla/herdr-watchdog/issues/39
blocked_by: [38]
updated: 2026-11-26
---

## What to build

Origem: pesquisa `docs/pesquisa-regra-do-todo-2026-11-26.md`, recomendação aprovada pelo Vini em 2026-11-26.

Pôr o gatilho do TODO em `docs/agents/issue-tracker.md`, na seção "When a skill says 'publish to the issue tracker'". As skills do Matt leem esse arquivo na hora de publicar e seguem o que ele diz, sem edição das skills.

## Acceptance criteria

- [ ] `docs/agents/issue-tracker.md` deste repositório manda, depois de publicar os tickets, criar ou atualizar o `TODO.md` conforme `docs/agents/todo.md`: um item por ticket, na ordem das dependências.
- [ ] Um modelo dessa seção fica em `docs/templates/`, para copiar em projetos preparados para o Watchdog.
- [ ] Nenhum arquivo em `~/.agents/skills` é editado.


## Comentários
