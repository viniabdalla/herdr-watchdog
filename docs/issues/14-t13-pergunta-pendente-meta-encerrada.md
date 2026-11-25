---
number: 14
title: "T13 — Pergunta pendente e meta encerrada"
state: closed
labels: ["ready-for-agent"]
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


## Comentários

### 2026-11-25T16:17:41Z · viniabdalla

O líder registra perguntas encaminhadas ao Vini e o encerramento pelo kit. O Progress prioriza o motivo do bloqueio e o próximo passo, com uma notificação por evento e faixa final preservada até o próximo despacho confirmado. Os testes cobrem A/B/C, identidades estáveis, perguntas sem resposta e terminal de 20 linhas.

Commit do executor `a1008ed`, integrado em `d673646`. A suíte executou 650 testes em cada modo de controles, com 7 ignorados e nenhuma falha.
