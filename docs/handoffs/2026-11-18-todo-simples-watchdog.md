# Handoff — TODO simples para Vini e completo para os agentes

Data: 18/11/2026 · America/Fortaleza
Destino: agente responsável por `/home/tropico/Projects/herdr-watchdog`.
Origem: conversa de Vini no projeto git-todo.
Entrega: Vini levará este arquivo ao agente. Nenhum novo run foi aberto para esta implementação.

## Prompt pronto para o agente destinatário

```text
Trabalhe no repositório /home/tropico/Projects/herdr-watchdog.

Leia este handoff inteiro, o TODO.md atual e as instruções locais aplicáveis.
Vini quer uma única lista de tarefas por projeto: linguagem simples para ele
decidir e instruções completas para o agente executar, dentro do mesmo TODO.md.
O Watchdog deve ler os campos por código, mostrar somente o título e expandir
pela setinha apenas o resumo simples e a situação. Os detalhes técnicos devem
acompanhar a tarefa enviada ao executor, sem poluir a lista do usuário.

O Watchdog é responsável por definir e implementar o formato comum e ajudar a
instalar/verificar as orientações dos agentes nos projetos. O líder de cada
projeto mantém o conteúdo do TODO durante a conversa, antes de qualquer commit.
Pedidos claros do usuário são tarefas; ideias dos agentes são sugestões.

Comece verificando o estado atual e preservando as alterações não commitadas do
TODO.md. Use os acordos e a ordem de implementação abaixo para preparar o desenho
técnico curto que falta: sintaxe, migração, compatibilidade e atualização segura.
Não reabra decisões de produto já combinadas. Apresente escolhas novas que
mudem o comportamento antes de implementá-las, conforme as regras do projeto.
Depois do desenho aprovado, implemente e valide por etapas, atualizando o TODO
durante o trabalho. Não considere esta documentação como implementação pronta.

Economize: um único executor; revisão pelo líder. Não abra uma dupla executor/QA
nem outros agentes. Se você próprio for o executor, trabalhe diretamente.
O Orchestrate atual exige dois participantes; não o use fingindo que aceita um,
nem remova suas verificações para contornar essa limitação. O modo econômico
precisa de implementação explícita e é uma etapa separada.

Priorize formato/leitor, atualização durante a conversa, exibição simples e
orientações aos agentes. Interface em português agora; opção de inglês depois.
Preserve tarefas, histórico, execuções e regras existentes. Não faça commit,
push, merge, instalação global ou migração de outros projetos sem autorização
específica. Não reative missões antigas ao ler este arquivo.

Ao concluir cada etapa, informe em português simples o que mudou, como foi
verificado e o que falta. Só marque uma tarefa como feita quando seu resultado
estiver implementado e validado; dispatch, documentação ou commit não bastam.
```

## O que Vini quer e já combinou

- Vini não é desenvolvedor. Precisa entender o resultado útil, escolher prioridades e saber o que está acontecendo.
- Uma tarefa tem duas camadas de leitura no mesmo TODO: informação simples para Vini e instruções de execução para o agente.
- Um único TODO por projeto; Watchdog não mantém uma segunda lista traduzida independente.
- Renderização e leitura do formato são feitas por código. IA não é necessária para transformar cada linha toda vez que a tela abre.
- Na lista aparece só o título. Uma setinha expande o resumo simples e a situação, sem mostrar o bloco técnico.
- Dentro do CRM, o título é “Resolver o problema com os áudios”, sem prefixo “CRM”. Nome do projeto faz sentido numa visão agregada, como a do Atlas.
- Cada tarefa precisa de identidade fixa, independente do título, posição ou seção. Mudar a redação não pode criar outra tarefa.
- Pedidos novos entram durante a conversa; não se espera commit. O líder atualiza o mesmo arquivo que o Watchdog lê.
- Pedidos claros de Vini e ideias dos agentes devem ser distinguíveis. Sugestão não vira compromisso automaticamente.
- “Tarefa em andamento” e “agente executando agora” são informações diferentes. Sem evidência atual, indicar ausência de informação, nunca inventar atividade.
- Interface em português nesta etapa. Tradução/opção de inglês fica para depois.
- Um executor por vez, com revisão pelo líder, para economizar.

## Conteúdo de uma tarefa

Campos de produto acordados; a sintaxe exata ainda precisa ser definida e validada:

| Parte | Conteúdo | Uso |
| --- | --- | --- |
| Identificação | ID estável | Ligar tarefa, execução, revisão e histórico |
| Título | Resultado em palavras simples | Linha principal do Watchdog |
| Resumo | O que será feito e para que serve | Expansão da setinha |
| Situação | Estado da tarefa e eventual motivo de espera/bloqueio | Expansão; atividade do agente vem de evidência separada |
| Origem | Pedido humano com referência disponível ou sugestão do agente | Distinguir autorização de ideia |
| Execução | Contexto, arquivos, diagnóstico, passos, limites e dependências | Instruções do executor |
| Aceite | Como verificar o resultado e evidências esperadas | Revisão e conclusão |

Exemplo conceitual, não uma sintaxe já implantada nem uma nova tarefa a cadastrar:

```text
Título: Resolver o problema com os áudios
Resumo: Investigar a interrupção no processamento e permitir que os áudios pendentes continuem.
Situação: Aguardando sua escolha
Origem: Pendência existente no projeto; importância atual ainda precisa ser revalidada.

Detalhes para o executor:
  Contexto: consultar o diagnóstico existente, sem assumir que continua atual.
  Arquivo: src/audio/worker.mjs, no projeto CRM.
  Verificar: reutilização de PID, execução de um único worker e recuperação da fila.
  Aceite: demonstrar reprodução e correção com verificações pertinentes.
```

O exemplo mostra por que o texto técnico deve continuar acessível ao agente sem ocupar a lista de Vini. Não inferir prazo ou promessa de entrega para preencher campos.

## Responsabilidades e fonte da informação

- **Watchdog:** define formato, lê/valida, exibe, recebe escolhas e envia instruções completas. Ajuda a preparar os projetos para esse funcionamento.
- **Líder do projeto:** registra pedidos, mantém estados e detalhes, lida com sugestões e registra verificações. Não precisa editar uma lista paralela do Watchdog.
- **Executor:** recebe o contexto da tarefa, executa e relata evidências ao líder pelo fluxo autorizado.
- **Atlas:** faz curadoria entre projetos e recomenda prioridades. Não assume a autoria dos pedidos nem altera automaticamente os TODOs na v1. Sua curadoria continua na base própria já existente.
- **AGENTS.md / CLAUDE.md:** regras gerais para manter o TODO. As instruções específicas do trabalho ficam na tarefa.

O Atlas adota o formato definido pelo Watchdog; não criar dois formatos concorrentes. A regra de uma única lista não elimina o banco de curadoria nem o histórico operacional existentes.

## Ordem sugerida de implementação

1. **Formato e leitor:** fechar sintaxe versionável, validar campos, introduzir IDs fixos e tratar arquivos antigos e execuções em curso explicitamente.
2. **Atualização segura:** refletir mudanças do arquivo durante a conversa; preservar alterações concorrentes, seleções e histórico. Pedidos e sugestões continuam separados.
3. **Exibição simples:** título, setinha com mouse/teclado e resumo; o envio ao executor recebe detalhes completos. Diferenciar estado da tarefa e atividade real.
4. **Orientações aos agentes:** disponibilizar instalação/verificação de instruções em AGENTS.md e CLAUDE.md, preservando conteúdo existente, com atualização revisável e sem duplicação. Mostrar o que falta ou está desatualizado.
5. **Português:** traduzir rótulos da interface por código, preservando protocolos, arquivos dos projetos e Yazi. Manter inglês como etapa posterior.
6. **Modo econômico:** implementar suporte explícito a um executor e revisão do líder, sem fingir QA independente ou remover controles do modo existente.

As etapas podem ser divididas em entregas pequenas. Não migrar todos os projetos nem ampliar para todas as pendências antigas do TODO neste pacote.

## Estado verificado nesta passagem

- HEAD do Watchdog observado: `55cfead4393d18c1161c3071c47843b74c6e1168`.
- Checkout **não está limpo**: TODO.md foi traduzido e reorganizado nesta conversa. Este handoff é outro arquivo novo. Preservar ambos e verificar outras alterações ao assumir.
- TODO do Watchdog: 13 tarefas pendentes e 10 concluídas; as 10 conclusões, datas, referências e limitações foram preservadas. Recontar se outro agente tiver alterado o arquivo.
- Tarefas relevantes já registradas: “Padronizar o arquivo de tarefas”, “Registrar pedidos durante a conversa”, “Orientar os agentes a manter o TODO atualizado”, “Simplificar a lista de tarefas”, “Mostrar a interface em português” e “Permitir execução com um agente”.
- Foi usado **um único agente** para traduzir/organizar o TODO, e o líder revisou. Nenhuma dessas funcionalidades foi implementada por essa tarefa documental.
- Leitura real pelo parser e `git diff --check` passaram para a organização dos TODOs. A suíte de produto não foi executada para essa alteração documental; resultados históricos não são testes desta implementação futura.
- O TODO de `/home/tropico/Projects/git-todo` também foi organizado. Sua primeira dependência é adotar o formato que o Watchdog definir.
- A interface ainda está em inglês e ainda junta título/detalhes. Traduzir o TODO não traduziu os controles.
- A versão simples aprovada do relatório Atlas é uma exportação local: `/home/tropico/.local/state/atlas/reports/rumo-2026-11-18.html`. Ela recebeu texto simples, links Git e pastas; a geração automática e o painel operacional ainda não receberam essas mudanças.

## Pontos de atenção no código atual

- `watchdog_app/todo.py`: `Snapshot.read` lê TODO.md. O ID atual usa hash da posição e do bloco de texto; isso não é identidade estável. Linhas indentadas são incorporadas a `task.text`.
- `watchdog_app/tasks_ui.py`: a lista usa `task.text`, por isso mistura título e detalhes. Não basta acrescentar subtítulos ao Markdown para obter a interface acordada.
- `watchdog_app/mission_launch.py`: `validate_brief` exige exatamente `worker` e `qa`. O modo com um executor não existe.
- `watchdog_app/actions.py`, `mission.py` e os módulos `mission_*`: conferir efeitos de identidade/migração sobre seleção, envio, revisão e conclusão. Não substituir IDs de runs antigos sem uma migração explícita e verificada.
- `tests/test_todo.py`, `tests/test_tasks_ui.py`, `tests/test_actions.py`, `tests/test_mission*.py`: referências para os testes pertinentes.
- Após a queda de energia, os quatro painéis do Watchdog foram recuperados na aba do git-todo, sem reiniciar agentes. Isso foi uma recuperação operacional de vínculo; não significa que recuperação automática após queda esteja implementada.
- Há uma missão histórica sobre usar o painel por dias distintos, `f1fe10f6-284b-4ae1-8d95-accd85ced797`. Sua entrega documental não concluiu o TODO. Não usar esse run para estas novas tarefas nem tratar este handoff como aprovação de sua conclusão.

## Verificação esperada

- Leitor aceita exemplos válidos e arquivos antigos suportados; explica erros de formato sem adivinhar campos.
- IDs permanecem iguais ao renomear, mover ou detalhar uma tarefa; duplicação de ID é detectada.
- Edições concorrentes não sobrescrevem silenciosamente trabalho; novas tarefas aparecem antes de commit.
- Expandir/recolher funciona por mouse e teclado, inclusive em painel estreito, sem expor detalhes técnicos no resumo.
- Envio ao executor preserva instruções, referências, dependências e aceite completos.
- Atualizar AGENTS.md/CLAUDE.md não duplica nem remove regras; instalação repetida é segura e o conteúdo efetivamente consumido pelo agente é conferido.
- Sugestões não se tornam compromissos nem tarefas concluídas sem o fluxo definido. Atividade exibida corresponde a evidência real.
- Histórico, seleções, revisões e execuções existentes continuam íntegros ou recebem tratamento explícito na migração.

Comando da suíte documentado no README, a executar no checkout de implementação:

```bash
python3 -B -m unittest discover -s tests -q
git diff --check
```

Testes vivos do Herdr são opt-in (`WATCHDOG_HERDR_TEST=1`) e devem usar o ambiente descartável próprio indicado no README, nunca reorganizar a sessão real do usuário como teste. Conferir a interface real antes de afirmar que a alteração visual está pronta.

## Resultado esperado da próxima etapa

Um desenho técnico curto para a sintaxe/migração que ainda não foi fechada, seguido da implementação aprovada em etapas. Relatar mudanças e limites em português simples. Atualizar os itens existentes do TODO, sem duplicar este pacote como várias listas independentes.
