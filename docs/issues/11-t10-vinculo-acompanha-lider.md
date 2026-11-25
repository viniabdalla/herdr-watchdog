---
number: 11
title: "T10 — Vínculo que acompanha o líder"
state: open
labels: [ready-for-agent]
url: https://github.com/viniabdalla/herdr-watchdog/issues/11
parent: 1
blocked_by: [8]
updated: 2026-11-25
---

## Parent

#1

## What to build

Depois de um /clear no mesmo pane e no mesmo harness, o painel segue a sessão nova sem aviso. Se o harness do líder mudar, os botões trocam de prefixo e aparece um aviso curto. A tecla Religar lista os panes com agente do workspace para ligar o painel a outro líder. Depois de um /clear, a prévia oferece reenviar a meta do grupo.

## Acceptance criteria

- [ ] /clear no Claude mantém o vínculo sem aviso.
- [ ] /clear no Codex mantém o vínculo sem aviso.
- [ ] Troca de harness troca os prefixos e mostra o aviso.
- [ ] Religar liga o painel ao pane escolhido.
- [ ] Outro pane ou sessão antiga ainda viva não é seguido sozinho.
- [ ] Reenviar a meta digita a meta do grupo atual.
