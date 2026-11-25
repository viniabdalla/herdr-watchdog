---
number: 4
title: "T3 — Despacho com meta ativa e zerar o grupo"
state: open
labels: [ready-for-agent]
url: https://github.com/viniabdalla/herdr-watchdog/issues/4
parent: 1
blocked_by: [2]
updated: 2026-11-25
---

## Parent

#1

## What to build

Com uma meta ativa, um novo despacho só soma tarefas ao grupo e digita "Grupo atualizado: +D, +E, +F", sem trocar a meta. Quando todo o grupo está concluído, o próximo despacho recomeça a contagem. O Vini também pode zerar o grupo à mão no Progress.

## Acceptance criteria

- [ ] Com meta ativa, despachar D, E e F digita só "Grupo atualizado: +D, +E, +F" e o grupo passa de 3 para 6.
- [ ] Com todo o grupo concluído, o próximo despacho começa um grupo novo e uma base nova.
- [ ] Com tarefa aberta no grupo, o próximo despacho soma.
- [ ] Zerar à mão esvazia o grupo e a próxima prévia volta a ser a meta.
- [ ] A prévia mostra qual dos dois textos será enviado.
