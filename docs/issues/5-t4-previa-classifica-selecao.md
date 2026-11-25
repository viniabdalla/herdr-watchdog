---
number: 5
title: "T4 — Prévia que classifica a seleção"
state: open
labels: [ready-for-agent]
url: https://github.com/viniabdalla/herdr-watchdog/issues/5
parent: 1
blocked_by: [2]
updated: 2026-11-25
---

## Parent

#1

## What to build

A prévia do despacho lê os bloqueios do TODO e mostra cada tarefa como livre, esperando outra da seleção, esperando uma fora da seleção ou dependendo do Vini. Se nada puder começar, oferece incluir a dependência, cancelar ou mandar assim mesmo. Também avisa quando o projeto não tem a seção Dispatch ou o CLAUDE.md com import do AGENTS.md.

## Acceptance criteria

- [ ] A prévia mostra a classificação de cada tarefa selecionada.
- [ ] Sem nenhuma tarefa livre, nada é enviado até o Vini escolher incluir, cancelar ou mandar assim mesmo.
- [ ] Incluir a dependência acrescenta a tarefa bloqueadora à seleção.
- [ ] Projeto sem seção Dispatch ou sem import no CLAUDE.md mostra um aviso, sem impedir o envio.
