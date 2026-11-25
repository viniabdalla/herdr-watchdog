---
number: 9
title: "T8 — Kit do líder: abrir executor e fechar tarefa"
state: closed
labels: ["ready-for-agent"]
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


## Comentários

### 2026-11-25T15:40:23Z · viniabdalla

O kit abre um executor em uma worktree da integração, registra o pane e sua sessão e confirma que o contrato iniciou trabalho. Usa a aba da dependência quando há espaço e reaproveita a aba da própria leva quando a anterior lota. O fechamento conserva o comentário e a cópia local, inclusive na recuperação após uma falha parcial.

Commit do executor `dc9e4a0`, integrado em `36835b8`. A suíte rodou 601 testes em cada modo, com 7 ignorados e nenhuma falha. A correção do transporte de avisos no Codex ocupado segue na issue #7.
