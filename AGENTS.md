## Agent skills

### Issue tracker

Issues e specs ficam no GitHub (viniabdalla/herdr-watchdog), com cópia local em docs/issues/. See `docs/agents/issue-tracker.md`.

### Triage labels

Rótulos padrão: needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: GLOSSARY.md na raiz e docs/adr/. See `docs/agents/domain.md`.

### TODO

TODO.md no formato do Watchdog, com tipos, quem cria em cada etapa e arquivos obrigatórios. See `docs/agents/todo.md`.

## Dispatch

Ao receber uma meta ou atualização do grupo, leia o [padrão do dispatch](docs/dispatch.md)
e os ponteiros de aceite de cada tarefa em `docs/issues/`.

Branch de integração: `feat/tasks-somente-leitura`
Checkout de integração: `/home/tropico/Projects/herdr-watchdog/.worktrees/tasks-somente-leitura`
Modelo dos executores: `gpt-6.1-sol`
Esforço dos executores: médio
Permissões dos executores: full access

Testes obrigatórios antes do último commit e na integração:
`env -u WATCHDOG_FULL_CONTROLS python3 -m unittest discover -s tests` e
`WATCHDOG_FULL_CONTROLS=1 python3 -m unittest discover -s tests`.
Faça merge da integração na própria branch antes do último commit.
Use TDD, com recursos isolados, pelos pontos A e B aplicáveis da spec #1;
testes que fixam comportamento citam suas linhas.

Executores preservam `TODO.md`, `HANDOFF*`, issues e suas cópias, Left Undone,
painéis Watchdog em execução e arquivos de outras tarefas.
Use `.worktrees/<ticket>` e `.watchdog/run/<data>/`, ignoradas pelo git.
Integre somente no checkout de integração; implemente sempre em worktrees.
Sempre porta única: push, deploy, envio real externo, perda de dados e merge
para a branch principal. Dependem da decisão do Vini.
