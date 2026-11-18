# TODO único com identidade estável — proposta para aprovação

Estado: desenho aprovado por Vini em 2026-11-18; implementação e validação
registradas no plano e no TODO. Adoção em cada projeto continua explícita.
Escopo: somente “Padronizar o arquivo de tarefas”.

## Resultado

Um TODO.md por projeto contém título simples, resumo do resultado e benefício,
ID fixo, estado, origem, instruções completas e critérios de aceite. O leitor Python usa
somente a biblioteca padrão e valida a estrutura sem inferência por IA.

## Alternativas

Recomendo acrescentar um formato versionado ao Markdown e manter o leitor antigo.
Substituir imediatamente todos os arquivos quebraria a compatibilidade pedida.
Usar um arquivo JSON paralelo criaria outra fonte de tarefas. Essas alternativas
não atendem ao pedido. A escolha da gramática abaixo ainda requer aprovação.

## Sintaxe proposta

O frontmatter do documento declara `watchdog_todo: 1`. Sem esse campo, continua
valendo integralmente a sintaxe atual. Versões desconhecidas são erro explícito.

```markdown
## Próximo
- [ ] Padronizar o arquivo de tarefas
  ID: 613821eb-e1d7-4ae6-9f71-88534c73c843
  Resumo: Reunir as informações da tarefa para facilitar a leitura e a execução.
  Origem: pedido-humano
  Referência: Solicitação explícita desta conversa em 2026-11-18.
  Execução:
    Implementar leitor, validação e migração explícita.
    Preservar arquivos antigos e vínculos de execuções existentes.
  Aceite:
    Renomear e mover a tarefa preserva seu ID.
    IDs duplicados e migrações ambíguas produzem erro explicativo.
```

Exemplo ilustrativo: não é uma nova tarefa a cadastrar.

- O título continua na linha de checkbox. O ID é UUID canônico, criado uma vez.
- O estado vem da seção existente: Em andamento, Próximo, Bloqueado ou Feito;
  checkbox e seção devem ser coerentes. Não haverá dois estados independentes.
- Campos têm dois espaços de recuo; conteúdo multilinha tem quatro. Não são
  YAML genérico. Campos repetidos, desconhecidos, malformados ou ausentes geram
  diagnóstico com linha e tarefa. Blocos de código não viram tarefas.
- IDs não dependem de título, resumo, detalhes, posição, seção ou conclusão.
  Duplicar, remover ou substituir um ID nunca significa renomear automaticamente.
- Um campo opcional `Motivo` permite registrar bloqueio sem alterar o título.
- `Origem` distingue `pedido-humano`, `sugestao-agente` e `legado-nao-confirmado`;
  `Referência` é opcional e só contém evidência disponível. Importação sem prova
  de origem usa `legado-nao-confirmado`, sem inventar autorização. O campo existe
  desde o primeiro formato; registro automático durante conversas é posterior.
  Sugestões não autorizam execução por si mesmas.

## Identidade e instruções de execução

Identidade estável e conteúdo aprovado são verificações diferentes. Novas
execuções guardam ID, versão do formato e uma cópia das instruções selecionadas.
Editar título ou detalhes mantém a tarefa, mas uma alteração no conteúdo aprovado
exige revisão explícita antes de continuar com instruções diferentes. A execução
não recebe automaticamente uma nova versão, nem desaparece ou perde evidências.

O leitor oferece os campos separados e uma representação completa para envio.
Seleção, ações, detecção de sobreposição, revisão e conclusão usam o ID no formato
novo. Conclusão de uma execução não será deduzida por igualdade de título.
As verificações de Git, revisão e versão candidata continuam obrigatórias.

## Compatibilidade e migração

1. Ler documentos antigos sem reescrevê-los ou lhes prometer IDs estáveis.
   Continuar usando os contratos atuais para execuções antigas.
2. Oferecer prévia explícita da migração de um único projeto: versão original,
   IDs antigos, novos UUIDs, conteúdo preservado e campos que precisam de revisão.
   Não inventar aceite ou benefício ausente; pendências impedem aplicar a conversão.
3. Preservar texto, conclusões, datas, referências e notas. As conclusões antigas
   podem permanecer numa seção histórica delimitada e preservada literalmente,
   reconhecida pelo leitor e contabilizada como histórico, sem fingir que têm os
   campos de uma nova tarefa executável. A prévia mostra essa distinção.
4. Antes de aplicar, verificar alterações concorrentes, seleções e execuções que
   ainda dependem do formato antigo. Migração com execução inacabada que seria
   afetada fica bloqueada com identificação da execução e motivo. O usuário pode
   terminar ou encerrar explicitamente essa execução no fluxo existente.
   Não encerrar agentes, painéis ou execuções automaticamente.
5. Aplicar com a proteção de concorrência e cópia de segurança já existente.
   Guardar o mapeamento de migração e seu digest no próprio TODO como metadados
   delimitados; o backup guarda o documento original. A gramática desses metadados
  usa o comentário JSON `watchdog-migration`, descrito no README.
6. Registros de execuções anteriores permanecem intactos. Nenhuma migração muda
   seus IDs, hashes, relatórios ou revisões. Consultas históricas usam a evidência
   registrada; tentar continuar um contrato incompatível produz orientação explícita.
7. A mudança intencional de identidade exige prévia e confirmação específica,
   preservando o ID anterior no registro de migração. Não haverá associação por
   semelhança de título, nem reutilização silenciosa de ID removido.

Migração automática de outros projetos e adoção deste TODO estão fora desta
aprovação de implementação: cada aplicação precisa de prévia revisada.

## Validação prevista

- Mesmos IDs após renomear, detalhar, reordenar, mudar estado e concluir.
- Erros claros para campos inválidos, IDs duplicados e versões desconhecidas.
- Compatibilidade com documentos antigos, português/inglês, CRLF, exemplos em
  cercas Markdown e preservação de notas e conclusões.
- Envio inclui instruções e aceite completos; ação sobre seleção antiga não
  sobrescreve edição concorrente.
- Contratos novos usam identidade estável e detectam mudança de conteúdo;
  contratos antigos mantêm suas verificações atuais.
- Prévia/aplicação da migração, impedimento com execução afetada, histórico e
  mudanças explícitas de identidade, sem tocar registros de runs anteriores.

Rodar testes pertinentes de TODO, ações, escopo, lançamento, revisão e conclusão,
depois a suíte documentada: `python3 -B -m unittest discover -s tests -q`.
Não executar testes vivos na sessão real do usuário.

## Fora desta entrega

Reformulação visual, tradução de controles, registro automático de pedidos,
instalação de AGENTS.md/CLAUDE.md, modo com um executor e histórico agregado de
progresso continuam como tarefas separadas. Preservar atores/painéis existentes,
arquivos protegidos e Left Undone. Sem commit, push ou instalação nesta proposta.
Conforme o handoff agora indicado pelo usuário, implementar diretamente com um
único executor e revisão pelo líder; não criar agentes nem usar o Orchestrate
como se já aceitasse esse modo. Isso substitui a política anterior de dupla
executor/QA para este pacote, sem alterar as verificações do produto.

## Evidência desta preparação

Em 2026-11-18 foram lidos TODO.md, todo.py, mission_scope.py e os consumidores de
IDs em actions.py, mission.py e tasks_ui.py. A leitura real do TODO retornou 22
itens: 12 abertos e 10 concluídos. HEAD observado: bb4b2d8. Existe conteúdo alheio
não rastreado em docs/handoffs/ e ele foi preservado. Não houve mudança de produto,
migração, testes da implementação ou confirmação de término de agentes concorrentes.
