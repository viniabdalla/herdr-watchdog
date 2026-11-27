<!-- Modelo: acrescente este parágrafo à seção 'When a skill says "publish to the issue tracker"'
     do docs/agents/issue-tracker.md de um projeto preparado para o Watchdog. -->

Depois de publicar os tickets (`/to-tickets`), crie ou atualize o `TODO.md` na raiz conforme
`docs/agents/todo.md`: um item por ticket em `## Próximo`, na ordem das dependências, com título
`Tn (#issue) <título>`, `Referência:` para a spec e a issue, e `Execução: Bloqueado por: Tn (#issue).`
Faça isso também sem o Watchdog ligado. Uma spec sozinha (`/to-spec`) não entra no TODO.
