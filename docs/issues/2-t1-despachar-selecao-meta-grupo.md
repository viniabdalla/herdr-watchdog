---
number: 2
title: "T1 — Despachar a seleção com a meta do grupo"
state: open
labels: [ready-for-agent]
url: https://github.com/viniabdalla/herdr-watchdog/issues/2
parent: 1
blocked_by: []
updated: 2026-11-25
---

## Parent

#1

## What to build

O Vini marca tarefas no Tasks e aperta Despachar. A prévia mostra o texto e o pane do líder; ao confirmar, o Tasks digita a meta curta e dá Enter no pane do líder. A meta aponta para o grupo do Watchdog e cita o padrão do dispatch e a seção Dispatch do AGENTS.md do projeto. As tarefas despachadas somam ao grupo do Progress. Inclui o primeiro texto do padrão do dispatch (camada 1) e um modelo da seção Dispatch para projetos.

## Acceptance criteria

- [ ] Despachar A, B e C sem meta ativa digita a meta curta no pane do líder, com Enter, e o grupo do Progress mostra 0 de 3.
- [ ] Despachar soma ao grupo existente e uma tarefa já presente não conta duas vezes.
- [ ] No primeiro despacho de um grupo, a ponta da branch de integração do projeto fica anotada como base.
- [ ] A meta cita pelo nome o padrão do dispatch e a seção Dispatch do AGENTS.md.
- [ ] O padrão do dispatch existe com as regras acordadas na spec (executor por tarefa, worktree, aviso, espera sem polling, checagem de spec, integração só no checkout principal, aviso final).
- [ ] A ação antiga de gravar o grupo à mão não existe mais.
- [ ] Testes no ponto de teste A cobrem os cenários acima.
