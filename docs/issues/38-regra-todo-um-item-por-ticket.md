---
number: 38
title: "Regra do TODO: um item por ticket, criado no /to-tickets"
state: open
labels: ["ready-for-agent"]
url: https://github.com/viniabdalla/herdr-watchdog/issues/38
blocked_by: []
updated: 2026-11-26
---

## What to build

Origem: pesquisa `docs/pesquisa-regra-do-todo-2026-11-26.md`, recomendação aprovada pelo Vini em 2026-11-26.

Corrigir a regra do TODO do projeto: o TODO tem **um item por ticket**, criado ou atualizado depois do `/to-tickets`. O `/to-spec` não escreve no TODO. A spec aparece só em `Referência:`. O código só reconhece `Bloqueado por: T1 (#2)` quando existe um item cujo título começa com `T1 (#2)` (`watchdog_app/dispatch_preview.py`, linhas 11–18 e 31–39).

## Acceptance criteria

- [ ] `docs/agents/todo.md` diz: um item por ticket com título `Tn (#issue) título`, `Referência:` com a spec e a issue, e dependências em `Execução: Bloqueado por: Tn (#issue).`
- [ ] Os tipos `[Bug #n]`, `[Feature]` e `[Verificação]` continuam valendo para o que não é ticket. O prefixo `[Spec #n]` deixa de existir como item.
- [ ] `docs/templates/agents-todo.md` e `docs/templates/todo.md` seguem a mesma regra. O preâmbulo do `TODO.md` vira uma linha que aponta para `docs/agents/todo.md`.
- [ ] `watchdog todo validate --repo .` passa.


## Comentários
