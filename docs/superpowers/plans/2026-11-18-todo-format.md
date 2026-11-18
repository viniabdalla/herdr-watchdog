# Plano de implementação — formato único de tarefas

Execução direta pelo agente desta sessão, conforme handoff e aprovação de Vini.
Sem novos agentes, commits, merge, push ou instalação. Revisão pelo próprio líder.

**Objetivo:** implementar o desenho aprovado em
`docs/superpowers/specs/2026-11-18-todo-format-design.md`.
**Arquitetura:** leitor versionado separado, modelo Snapshot compartilhado,
contratos novos por UUID e migração explícita com prévia revisável.
**Tecnologia:** Python e biblioteca padrão; unittest.

## Restrições

Preservar sintaxe antiga, histórico, contratos existentes, atores e painéis.
Trabalhar diretamente neste checkout conforme método indicado pelo usuário.
Não migrar o TODO real nem outros projetos automaticamente.

## Pontos de revisão

Campos e IDs malformados devem falhar antes de qualquer escrita.
Mudança de conteúdo conserva identidade mas não aprova um contrato novo.
Histórico importado não pode virar tarefa executável nem perder texto.
Migração não pode tocar execuções antigas nem passar por execução inacabada.
Prévia antiga ou editada não pode sobrescrever versão concorrente.

## 1. Leitor e ações

Arquivos: `watchdog_app/todo.py`, novo `todo_format.py`, `tests/test_todo_format.py`.
Interface: `Snapshot.parse(repo, raw)`, `Snapshot.format_version`; Task recebe
summary, execution, acceptance, origin, reference, reason e historical.

- Escrever e executar testes de campos, UUID, estado, versões, cercas, CRLF e legado.
- Implementar gramática definida e erros com linha; guardar IDs separados do texto.
- Adaptar `change` para preservar campos/IDs e exigir dados completos ao adicionar
  tarefa v1; reutilizar escrita atômica também na migração.
- Rodar testes do leitor e ações; verificar mudança de estado e concorrência.

## 2. Contratos e consumidores

Arquivos: `mission_scope.py`, `mission.py`, `tasks_ui.py`; testes novos de escopo.
Interface: scope v2 contém `format: 1`, IDs UUID, bloco aprovado e seção;
scope v1 e registros sem scope continuam com o contrato original.

- Testar identidade, conteúdo alterado, sobreposição, conclusão e seleção obsoleta.
- Implementar resolução v2 por UUID com comparação de bloco/seção aprovada.
- Preservar validação antiga; impedir queda silenciosa para outro protocolo.
- Manter confirmação de seleção cancelada quando seu conteúdo muda.
- Rodar testes de missão, ações e UI, sem mudar layout visual.

## 3. Migração e CLI

Arquivos: novos `todo_migrate.py`, `todo_cli.py`, alteração pontual em `app.py`;
testes `test_todo_migrate.py` e `test_todo_cli.py`.
Interfaces: `preview(snapshot, runs)` produz proposta JSON versionada;
`apply(snapshot, proposal, runs, confirmed, root)` valida origem/candidato, bloqueia
execuções inacabadas, confirma e usa escrita atômica com backup.

- Testar prévia sem escrita, campos ausentes, histórico literal e mapeamento.
- Testar recusa sem confirmação, execuções ativas e alterações concorrentes.
- Implementar comandos `watchdog todo validate|preview|apply` com --repo,
  --proposal e --confirm. A prévia é artefato de revisão, não lista paralela.
- Metadados de migração no TODO guardam digest original e mapa de IDs; histórico
  importado usa delimitadores explícitos, nunca sintaxe adivinhada.
- Mudanças de identidade em documento v1 são feitas somente por proposta explícita
  de reidentificação, com mapeamento e bloqueios equivalentes à migração.
- Rodar testes da migração/CLI e integração com as proteções reais de escrita.

## 4. Revisão e entrega

- Documentar formato, comandos, compatibilidade e restrições no README.
- Revisar separadamente os caminhos de falha e cobertura do desenho aprovado.
- Rodar `python3 -B -m unittest discover -s tests -q` e `git diff --check`.
- Atualizar somente o item existente do TODO quando implementado e validado;
  preservar as demais tarefas e registrar o resultado no histórico operacional
  usando UUID 0d526eba-b2b5-4ff4-858b-7950a1d3a41c.

## Registro de execução

Início: plano revisado contra desenho; interfaces comuns Task/Snapshot e scopes
estão declaradas acima. Sem commits autorizados; o próprio diff é a entrega.
Decisão: revisão pelo líder sem subagentes, conforme instrução explícita do usuário.

1. Concluído: leitor e ações versionadas; testes novos observados falhando antes
   da implementação e passando depois. Escrita compartilhada conserva a trava
   existente; a função interna evita adquirir a mesma trava duas vezes.
2. Concluído: escopo v2 por UUID, validação de contrato, conclusão e sobreposição
   por identidade; regressão de escopo antigo passou. Integração em Git temporário
   cobre solicitação, lançamento e envio com instruções multilinha completas.
3. Concluído: prévia JSON, renderização sem escrita, confirmação, validação da
   origem, cópia de segurança, metadados de migração e reidentificação explícita.
   JSON é artefato de revisão; o único arquivo lido pelo painel continua TODO.md.
4. Concluído: documentação, revisão pelo próprio líder e testes. Suíte completa:
   347 testes, sem falhas, 7 opt-in ignorados. `git diff --check` passou.

Revisão final: feita pelo autor/líder por solicitação do usuário, sem revisão
independente. Cobriu esquema, perda de conteúdo, concorrência, execução ativa,
compatibilidade, envio completo, UUID aposentado e escopo. Testes de metadados
malformados e títulos/cercas inválidos foram adicionados e passaram após falhar.
Sem migração do TODO real, alteração de atores/painéis ou comandos Git de escrita.
O item existente do TODO foi concluído com evidências; as outras 11 pendências
continuam abertas. Não houve bloqueio técnico remanescente nesta implementação.
