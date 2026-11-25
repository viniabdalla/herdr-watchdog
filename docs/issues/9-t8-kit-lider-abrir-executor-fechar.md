---
number: 9
title: "T8 — Kit do líder: abrir executor e fechar tarefa"
state: open
labels: [ready-for-agent]
url: https://github.com/viniabdalla/herdr-watchdog/issues/9
parent: 1
blocked_by: [7]
updated: 2026-11-25
---

## Parent

#1

## What to build

O Watchdog traz o kit que funcionou no long run: abrir um executor novo numa worktree e branch a partir da integração, numa aba nomeada pela leva, com o rodapé comum do contrato e o próprio pane no aviso; registrar o executor para o painel; guardar contratos, relatórios e comentários numa pasta padrão do projeto ignorada pelo git; fechar a issue com comentário e atualizar a cópia local.

## Acceptance criteria

- [ ] Abrir executor cria a worktree e a branch a partir da integração e o pane na aba da leva.
- [ ] Tarefas liberadas depois entram na aba da leva de que dependiam, enquanto houver espaço.
- [ ] O executor aberto fica registrado para o painel, com tarefa e pane.
- [ ] Modelo e esforço vêm da seção Dispatch do projeto.
- [ ] Fechar tarefa comenta e fecha a issue e atualiza a cópia local.
- [ ] O padrão do dispatch passa a citar o kit, a checagem aos 2, 3 e 4 minutos e o merge da integração antes do aviso.
- [ ] Testes no ponto de teste B cobrem abrir e fechar.
