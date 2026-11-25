---
number: 8
title: "T7 — Faixa de skills do Matt"
state: closed
labels: [ready-for-agent]
url: https://github.com/viniabdalla/herdr-watchdog/issues/8
parent: 1
blocked_by: [2]
updated: 2026-11-25
---

## Parent

#1

## What to build

O Tasks mostra uma faixa com as skills de Matt que o harness do líder enxerga (grill-with-docs, to-spec, to-tickets, retro). Cada botão abre uma prévia editável e digita o comando com / no Claude e $ no Codex. O to-tickets vem com a spec preenchida quando encontrada. A prévia avisa quando o tracker do projeto não guarda cópia local das issues.

## Acceptance criteria

- [ ] Líder Claude mostra /to-spec e líder Codex mostra $to-spec.
- [ ] Skill não instalada para aquele harness não aparece.
- [ ] O texto pode ser editado antes do Enter.
- [ ] to-tickets vem com a referência da spec quando o painel a encontra.
- [ ] Tracker sem a seção de cópia local mostra o aviso.

## Comentários

### 2026-11-25 · viniabdalla

O Tasks oferece as skills instaladas do harness do líder, com prévia editável, prefixo próprio e aviso sobre cópia local. A prévia de to-tickets preenche a spec identificada. O envio usa a trava integrada em T6.

Commit do executor `378826f`, integrado em `0e34c40`. A suíte executou 569 testes em cada modo de controles, com 7 ignorados e nenhuma falha.
