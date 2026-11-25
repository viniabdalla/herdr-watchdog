---
number: 10
title: "T9 — Skill e botão merge-danger"
state: open
labels: [ready-for-agent]
url: https://github.com/viniabdalla/herdr-watchdog/issues/10
parent: 1
blocked_by: [8]
updated: 2026-11-25
---

## Parent

#1

## What to build

Uma skill nova, merge-danger, avalia a branch de integração (ou um intervalo) e diz, por parte, se é porta dupla ou única e qual o raio, usando a definição da skill de PR de Matt e a lista de "sempre mão única" da seção Dispatch. Devolve integra e segue, integra e revisar, ou não integrar e perguntar. O Vini a chama por um botão na faixa, depois da implementação.

## Acceptance criteria

- [ ] A skill fica instalada para Claude e Codex.
- [ ] O botão aparece na faixa com o prefixo do harness.
- [ ] A resposta lista porta, raio e decisão por parte.
- [ ] Itens da lista de "sempre mão única" do projeto saem sempre como porta única.
