---
number: 14
title: "T13 — Pergunta pendente e meta encerrada"
state: open
labels: [ready-for-agent]
url: https://github.com/viniabdalla/herdr-watchdog/issues/14
parent: 1
blocked_by: [7, 12]
updated: 2026-11-25
---

## Parent

#1

## What to build

Quando um executor manda BLOQUEIO que vai para o Vini, a seção AGENTES mostra a faixa "pergunta de X aguarda você" e o desktop recebe uma notificação. Quando a meta termina, fica uma faixa fixa com o resumo (concluídas, bloqueadas e por quê) e outra notificação.

## Acceptance criteria

- [ ] Pergunta para o Vini mostra a faixa e dispara a notificação.
- [ ] Meta encerrada mostra a faixa fixa até o próximo despacho e dispara a notificação.
- [ ] O aviso final do líder segue o formato concluídas com evidência e bloqueadas com motivo e próximo passo.
