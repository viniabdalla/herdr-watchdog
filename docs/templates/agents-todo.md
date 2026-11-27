<!-- Modelo: copie para docs/agents/todo.md num projeto preparado para o Watchdog. -->

# TODO.md neste projeto

Esta regra vale mais que a regra global do TODO (git-todo). O que ela não cobre continua valendo pela global.
O `TODO.md` na raiz é o to-do vivo: o Watchdog (Tasks, Progress, curador e despacho) lê esse arquivo.
Ele nasce no planejamento, mesmo sem o Watchdog ligado:
`/grill-with-docs` → `/to-spec` → `/to-tickets` → Watchdog (Tasks → Despachar).

## Quem cria e quando

- **Fim do `/grill-with-docs`:** garanta os arquivos de domínio (ver "Arquivos obrigatórios").
- **`/to-spec` publicou uma spec:** se não há `TODO.md`, crie a partir de
  `docs/templates/todo.md` do Watchdog (`/home/tropico/Projects/herdr-watchdog`). Acrescente em `## Próximo` o item `[Spec #n] <título>`,
  com `Referência:` para a issue e a cópia em `docs/issues/`.
- **`/to-tickets` publicou os tickets:** não crie um item por ticket. No item da spec, liste os
  tickets em `Referência:` e as dependências em `Execução:`, como `Bloqueado por: T1 (#2).`
- **Issue de defeito aberta:** um item `[Bug #n]` por issue. Nunca junte vários bugs num item.
- Fora desses momentos, só mexa no TODO para refletir uma mudança real de estado.

## Tipos (o prefixo do título diz qual é)

- **Spec** `[Spec #n]`: issue-mãe que descreve uma entrega inteira e o aceite dela.
- **Ticket**: sub-issue de uma spec, uma fatia que um executor entrega sozinho. Fica dentro do item
  da spec; vira item próprio (`[Ticket #n]`) só quando é executado fora de uma spec.
- **Bug** `[Bug #n]`: defeito observado, com reprodução. Depois de triado, vira ticket ou entra numa spec.
- **Feature** `[Feature]`: capacidade nova ainda sem spec, incluindo achados de revisão que vão virar spec.
- **Verificação** `[Verificação]`: conferência ou aceite que não pede código novo.
- **Plano**: documento local com o "como" de uma spec ou ticket (`docs/superpowers/plans/`).
  Não é item do TODO; aparece em `Referência:` do item que implementa.

## Formato (`watchdog_todo: 1`)

- Cabeçalho YAML com `watchdog_todo: 1`, `status`, `area`, `prioridade`, `resumo`, `atualizado`, `motivo`.
- Seções `Em andamento`, `Próximo`, `Bloqueado`, `Feito`. Só `Feito` usa `[x]`, com data `AAAA-MM-DD` no título.
- Todo item, **inclusive os de Feito**, tem `ID` (UUID novo, nunca reaproveitado), `Resumo`,
  `Origem` (`pedido-humano`, `sugestao-agente` ou `legado-nao-confirmado`), `Execução` e `Aceite`.
  `Referência` e `Motivo` são opcionais. Campos com dois espaços de recuo; conteúdo multilinha com quatro.
- Dependências só em `Execução:`, como `Bloqueado por: T1 (#2).` ou `Bloqueado por: decisão do Vini sobre X.`
  O Watchdog não entende texto solto como "depende de A" ou "aguarda o Vini".
- Não pode `Feito` automaticamente: o Progress conta os itens listados. Pergunte ao Vini antes de remover concluídos.
- Valide com `watchdog todo validate --repo <projeto>`. Gramática completa no README, seção "Formato único do TODO.md".

## Arquivos obrigatórios

Crie só o que falta, nunca sobrescreva; num arquivo que já existe, acrescente só a parte que falta.
Repositório git e branch de integração: pergunte ao Vini, não crie por conta própria.

| Momento | Arquivo |
|---|---|
| Fim do `/grill-with-docs` | `GLOSSARY.md` com os termos decididos na conversa (o contrato do executor exige o arquivo) |
| `/to-spec` | `TODO.md` (modelo acima) e `docs/issues/` com a cópia local da issue |
| `/to-spec` | Seção "Cópia local" em `docs/agents/issue-tracker.md`; sem esse arquivo, avise para rodar `/setup-matt-pocock-skills` |
| `/to-tickets` ou antes de abrir o Watchdog | `AGENTS.md` com `## Dispatch` (modelo `docs/templates/dispatch-agents.md` do Watchdog (`/home/tropico/Projects/herdr-watchdog`)) |
| `/to-tickets` ou antes de abrir o Watchdog | `CLAUDE.md` com `@AGENTS.md` e `.gitignore` com `.worktrees/` e `.watchdog/` |

## Manutenção

- Antes de todo commit, atualize o TODO no mesmo commit: mova o concluído para `Feito`, registre o
  pendente ou o descoberto em `Próximo` ou `Bloqueado`, deixe no máximo 3 itens em `Em andamento` e
  atualize `atualizado:`.
- Itens curtos e acionáveis, escritos para quem retoma amanhã sem contexto.
- Não mude `status:` por conta própria. Se o projeto parecer `pausado` ou `descontinuado`, pergunte.
- Executores de um long run não editam o TODO; quem atualiza é o líder.
