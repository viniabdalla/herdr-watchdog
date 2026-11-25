# Modelo da seção Dispatch para projetos

Copie a seção abaixo para `AGENTS.md`, substitua os campos e importe esse arquivo
no `CLAUDE.md` com `@AGENTS.md` para líderes Claude.

```markdown
## Dispatch

Ao receber uma meta ou atualização do grupo, leia o padrão do dispatch do
Watchdog indicado na mensagem e os ponteiros de aceite de cada tarefa.

Branch de integração: `substitua-pela-branch-local`
Checkout de integração: `<caminho absoluto>`
Modelo dos executores: `<modelo>`
Esforço dos executores: `<esforço>`
Permissões dos executores: `<perfil autorizado>`
Testes obrigatórios: `<comandos e ambientes>`
Limites: `<arquivos, serviços e dados que os executores devem preservar>`
Sempre porta única: `<operações que exigem decisão humana>`

Use worktrees persistentes em `.worktrees/<ticket>` e arquivos de execução em
`.watchdog/run/<data>/`; mantenha ambas as pastas ignoradas pelo git.
Integre somente no checkout de integração; implemente sempre em worktrees.
O contrato de cada tarefa registra panes próprio e do líder e o comando de aviso.
```
