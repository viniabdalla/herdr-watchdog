---
number: 15
title: "T14 — Aceite manual"
state: closed
labels: [ready-for-human]
url: https://github.com/viniabdalla/herdr-watchdog/issues/15
parent: 1
blocked_by: [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
updated: 2026-11-26
---

## Parent

#1

## What to build

Teste humano depois de tudo integrado.

## Acceptance criteria

- [x] /clear no Claude e no Codex mantém o painel.
- [x] Handoff Claude para Codex com Religar mostra $; Codex para Claude volta a /.
- [x] Rodada real com A livre, B dependente de A e C dependente do Vini termina com o aviso certo.
- [x] O code review abre as duas abas e a correção em aba nova.

## Comentários

### 2026-11-26 · viniabdalla (via Claude)

Aceite manual dado pelo Vini em 2026-11-26.

- **/clear no Claude:** no `w14:p1`, o Tasks e o Progress seguiram sozinhos de `293f2207` para `15dbea79`, sem Religar. **/clear no Codex:** recuperado pelo Religar no mesmo pane em 25/11 (`.watchdog/run/2026-11-25/T14-retomada-aceite-real.json`).
- **Claude ↔ Codex:** o Vini confirmou as duas direções várias vezes, com `$` e `/`.
- **Rodada real A/B/C** no projeto descartável `test-watchdog-erase`: a prévia mostrou T1 livre, T2 esperando T1 e T3 dependendo do Vini. A rodada terminou com 3 de 3: T1 `ed1c5b7`, T2 `7a4e29b`, T3 `353c810`, 12 testes OK. O líder deu o aviso final "T3 concluído" depois da decisão do Vini.
- **Code review:** a R1 abriu as duas abas de revisão e a correção numa aba nova (25/11).

Achados da rodada, publicados à parte: #29 a #35 (o #32, meta colada sem Enter no Claude, é o mais grave). Evidências em `.watchdog/run/2026-11-26/T14-w14-*.json`.

