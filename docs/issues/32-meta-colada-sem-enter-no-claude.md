---
number: 32
title: "Meta colada no Claude sem Enter: despacho não confirmado, grupo sem goal e Fila travada falsa"
state: open
labels: ["bug", "needs-triage"]
url: https://github.com/viniabdalla/herdr-watchdog/issues/32
blocked_by: []
updated: 2026-11-26
---

## Contexto

Encontrado na rodada A/B/C do aceite T14 (#15). Evidências: `.watchdog/run/2026-11-26/T14-w14-*.json` (rodada A/B/C do aceite T14 no projeto descartável `test-watchdog-erase`, workspace `w14`).

## O que acontece

1. Na prévia do despacho, confirmei com y. O líder era Claude (`w14:p1`).
2. O texto da `/goal` chegou ao prompt como `[Pasted text #2]`, mas o Enter não foi registrado.
3. O Tasks mostrou `Despacho não confirmado; grupo preservado. Confira o pane do líder antes de tentar novamente`.
4. Apertei Enter à mão no pane e o líder começou a trabalhar. O arquivo do grupo ficou sem o campo `goal`, porque o `on_confirm` não rodou.
5. Cerca de 120 s depois, o watcher entregou ao líder `Fila travada no seu pane w14:p1: a entrega da frente (/goal …) está parada há 120 s`, apesar de a meta já estar em execução. Esse texto também ficou no prompt sem Enter.

## O que construir

- A entrega a um Claude confirma o envio mesmo quando o texto chega como colagem.
- Uma entrega que ficou pendente e depois foi enviada à mão não gera "Fila travada".
- O grupo recebe o `goal` quando a meta é aceita pelo líder.

## Critérios de aceite

- [ ] Um texto longo enviado ao Claude é submetido. O teste cobre o caso de colagem (`[Pasted text]`).
- [ ] Quando a meta pendente é submetida depois, o Tasks reconhece e grava o `goal` no grupo.
- [ ] O aviso "Fila travada" só dispara quando a entrega da frente ainda não começou.


## Comentários
