---
number: 10
title: "T9 — Skill e botão merge-danger"
state: closed
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

## Comentários

### 2026-11-25 · viniabdalla

A skill merge-danger está instalada no projeto para Claude e Codex e aparece com o prefixo do harness. Ela pede porta, raio e decisão por parte e dá precedência às operações sempre de porta única do projeto.

Commit do executor `3015486`, integrado em `419bb3d`. A suíte executou 584 testes em cada modo de controles, com 7 ignorados e nenhuma falha.
