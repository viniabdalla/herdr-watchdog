---
number: 12
title: "T11 — Seção AGENTES no Progress"
state: open
labels: [ready-for-agent]
url: https://github.com/viniabdalla/herdr-watchdog/issues/12
parent: 1
blocked_by: [9]
updated: 2026-11-25
---

## Parent

#1

## What to build

O Progress mostra, abaixo das barras do grupo e do TODO, uma seção AGENTES sempre visível. Cada agente tem uma linha com nome, pane, estado, contexto usado e o que está fazendo, inclusive a checagem inicial 1/3 a 3/3. Tarefas do grupo sem executor aparecem como esperando outra ou dependendo do Vini. Segue o mockup aprovado.

## Acceptance criteria

- [ ] O líder e cada executor registrado aparecem com pane, estado e contexto ao vivo.
- [ ] A checagem inicial aparece na linha do executor.
- [ ] Tarefas que esperam outra ou dependem do Vini aparecem sem pane.
- [ ] A seção não tem botão e não envia nada.
