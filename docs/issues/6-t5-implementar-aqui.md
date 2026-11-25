---
number: 6
title: "T5 — Implementar aqui"
state: closed
labels: [ready-for-agent]
url: https://github.com/viniabdalla/herdr-watchdog/issues/6
parent: 1
blocked_by: [2]
updated: 2026-11-25
---

## Parent

#1

## What to build

Além de Despachar, o Vini pode escolher Implementar aqui. A meta pede que o líder implemente as tarefas na própria sessão, numa worktree própria a partir da integração, com o mesmo fluxo de checagem, merge e "Tn concluído".

## Acceptance criteria

- [ ] A prévia mostra qual modo foi escolhido.
- [ ] Implementar aqui digita a meta com o texto de implementar nesta sessão.
- [ ] O padrão do dispatch descreve o modo Implementar aqui e o uso de worktree pelo líder.
- [ ] O grupo soma igual ao Despachar.

## Comentários

### 2026-11-25 · viniabdalla

Implementar aqui preserva o modo ao incluir uma dependência. Com meta ativa, cada tarefa nova conserva seu modo no grupo, e a mensagem ao líder lista somente as adições. O padrão orienta a leitura desses modos.

Commit do executor `aaf9c53`, integrado em `810f9cc`. A suíte executou 589 testes em cada modo de controles, com 7 ignorados e nenhuma falha.
