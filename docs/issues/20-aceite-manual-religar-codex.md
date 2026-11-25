---
number: 20
title: "Aceite manual do Religar após /clear no Codex"
state: open
labels: [ready-for-human]
url: https://github.com/viniabdalla/herdr-watchdog/issues/20
parent: 17
blocked_by: [19]
updated: 2026-11-25
---

## Parent

#17

## What to build

Validar com o Vini o cenário de recuperação manual encontrado durante #15. Usar uma sessão de aceite e comparar o que a conversa atual, o Tasks e o Progress mostram.

## Acceptance criteria

- [ ] Registrar a sessão A, pane, terminal, integrantes e progresso do grupo antes do /clear. Usar uma situação em que o Codex está em B e o Herdr ainda anuncia A. Se esse estado não ocorrer, registrar o cenário como não reproduzido.
- [ ] Acionar Religar e conferir a instrução no Tasks. Confirmar pela conversa escolhida. Verificar que o prefixo mostrado na mensagem e no cabeçalho após reabrir corresponde ao ID de B obtido no Codex.
- [ ] Comparar os integrantes e o progresso do grupo antes e depois, incluindo 14 de 15 concluídas. Verificar que não houve reenvio de meta nem entrega de pedidos antigos. Registrar o resultado da recuperação manual separadamente do acompanhamento automático de /clear.
- [ ] Guardar as evidências locais e publicar no ticket apenas o resultado com identificadores fictícios A/B.
