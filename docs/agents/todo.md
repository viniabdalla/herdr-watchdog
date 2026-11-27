# TODO.md neste projeto

Esta regra vale mais que a regra global do TODO (git-todo). O que ela não cobre continua valendo pela global.
O `TODO.md` na raiz é o to-do vivo: o Watchdog (Tasks, Progress, curador e despacho) lê esse arquivo.
Ele nasce no planejamento, mesmo sem o Watchdog ligado:
`/grill-with-docs` → `/to-spec` → `/to-tickets` (cria o TODO) → Watchdog (Tasks → Despachar).

## Quem cria e quando

- **Fim do `/grill-with-docs`:** garanta os arquivos de domínio (ver "Arquivos obrigatórios").
- **`/to-spec`:** não escreve no TODO. A spec só aparece depois, em `Referência:` dos tickets.
- **`/to-tickets` publicou os tickets:** crie o `TODO.md` se faltar (modelo `docs/templates/todo.md`
  do Watchdog) e acrescente em `## Próximo` **um item por ticket**, na ordem das dependências.
  O gatilho está em `docs/agents/issue-tracker.md`, que as skills leem na hora de publicar.
- **Issue de defeito aberta:** um item `[Bug #n]` por issue. Nunca junte vários bugs num item.
- Fora desses momentos, só mexa no TODO para refletir uma mudança real de estado.

## Como escrever cada tipo

- **Ticket** (sub-issue de uma spec, ou ticket avulso): título `Tn (#issue) <título da issue>`,
  com `n` sequencial no projeto. `Referência: spec #m e issue #issue (docs/issues/...)`.
  Dependências em `Execução:`, como `Bloqueado por: T1 (#26).` O Watchdog só reconhece a
  dependência quando existe um item cujo título começa com `T1 (#26)`.
- **Bug** `[Bug #n] <título>`: defeito observado, com reprodução, ainda não triado. Depois de
  triado, vira ticket (`Tn (#n)`) ou entra numa spec.
- **Feature** `[Feature] <título>`: capacidade nova ainda sem spec, incluindo achados de revisão que vão virar spec.
- **Verificação** `[Verificação] <título>`: conferência ou aceite que não pede código novo.
- **Spec** não é item: é a issue-mãe, citada em `Referência:` dos tickets dela.
- **Plano** não é item: documento local (`docs/superpowers/plans/`) citado em `Referência:`.

## Formato (`watchdog_todo: 1`)

- Cabeçalho YAML com `watchdog_todo: 1`, `status`, `area`, `prioridade`, `resumo`, `atualizado`, `motivo`.
- Seções `Em andamento`, `Próximo`, `Bloqueado`, `Feito`. Só `Feito` usa `[x]`, com data `AAAA-MM-DD` no título.
- Todo item, **inclusive os de Feito**, tem `ID` (UUID novo, nunca reaproveitado), `Resumo`,
  `Origem` (`pedido-humano`, `sugestao-agente` ou `legado-nao-confirmado`), `Execução` e `Aceite`.
  `Referência` e `Motivo` são opcionais. Campos com dois espaços de recuo; conteúdo multilinha com quatro.
- Dependências só em `Execução:`, como `Bloqueado por: T1 (#2).` ou `Bloqueado por: decisão do Vini sobre X.`
  O Watchdog não entende texto solto como "depende de A" ou "aguarda o Vini".
- Não apague itens de `Feito` por conta própria: o Progress conta os itens listados. Pergunte ao Vini antes.
- Valide com `watchdog todo validate --repo <projeto>`. Gramática completa no README, seção "Formato único do TODO.md".

## Arquivos obrigatórios

Crie só o que falta, nunca sobrescreva; num arquivo que já existe, acrescente só a parte que falta.
Repositório git e branch de integração: pergunte ao Vini, não crie por conta própria.

| Momento | Arquivo |
|---|---|
| Fim do `/grill-with-docs` | `GLOSSARY.md` com os termos decididos na conversa (o contrato do executor exige o arquivo) |
| `/to-spec` | `docs/issues/` com a cópia local da spec |
| `/to-tickets` | `TODO.md` (modelo acima), um item por ticket |
| `/to-spec` | Seção "Cópia local" em `docs/agents/issue-tracker.md`; sem esse arquivo, avise para rodar `/setup-matt-pocock-skills` |
| `/to-tickets` ou antes de abrir o Watchdog | `AGENTS.md` com `## Dispatch` (modelo `docs/templates/dispatch-agents.md` do Watchdog) |
| `/to-tickets` ou antes de abrir o Watchdog | `CLAUDE.md` com `@AGENTS.md` e `.gitignore` com `.worktrees/` e `.watchdog/` |

## Manutenção

- Antes de todo commit, atualize o TODO no mesmo commit: mova o concluído para `Feito`, registre o
  pendente ou o descoberto em `Próximo` ou `Bloqueado`, deixe no máximo 3 itens em `Em andamento` e
  atualize `atualizado:`.
- Itens curtos e acionáveis, escritos para quem retoma amanhã sem contexto.
- Não mude `status:` por conta própria. Se o projeto parecer `pausado` ou `descontinuado`, pergunte.
- Executores de um long run não editam o TODO; quem atualiza é o líder.
