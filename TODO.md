---
status: ativo
area: pessoal
prioridade: alta
resumo: Painéis Herdr para tarefas de projetos, progresso das sessões e arquivos criados pela IA
atualizado: 2026-11-18
motivo:
---

# TODO — Herdr Watchdog

Cada projeto usa seu próprio TODO.md com estas seções. O progresso conta as
tarefas atualmente listadas aqui; não estima o projeto inteiro.
Os itens em Próximo são planos pendentes, inclusive os acordos registrados abaixo;
esta organização não implementa esses comportamentos nem adota uma sintaxe nova.

## Em andamento

## Próximo
- [ ] Padronizar o arquivo de tarefas
  Resumo: reunir em um único TODO.md por projeto tudo o que a pessoa precisa entender e o executor precisa receber, sem perder o histórico.
  Definir ID estável, título humano curto, resumo do que será feito e seu benefício, estado e instruções técnicas com critérios de aceite no mesmo arquivo.
  Implementar leitura determinística por código e validação de esquema. Planejar compatibilidade e migração dos arquivos atuais, preservando histórico e tratando mudanças de identidade explicitamente, sem invalidar execuções silenciosamente.
  Aceite: títulos e detalhes podem mudar sem perder a identidade estável; arquivos antigos e execuções existentes têm tratamento explícito. A sintaxe atual continua valendo até essa implementação.
- [ ] Registrar pedidos durante a conversa
  Resumo: manter os pedidos claros do usuário no arquivo do projeto enquanto a conversa acontece, sem esperar um commit.
  O líder registra os pedidos claros antes de commit; ideias dos agentes ficam identificadas separadamente como sugestões, sem virarem pedidos aprovados automaticamente.
  Ler o mesmo TODO.md, sem uma segunda lista de tarefas; detectar alterações e conflitos antes de aplicar atualizações. Regras gerais pertencem ao AGENTS.md e instruções específicas ficam na tarefa.
  Aceite: líder e painel compartilham a mesma fonte, com conflitos visíveis e sugestões distinguíveis de pedidos.
- [ ] Orientar os agentes a manter o TODO atualizado
  Resumo: ajudar a preparar cada projeto para que seus agentes saibam registrar pedidos e atualizar tarefas durante a conversa, sem esperar commit.
  Dependência: implementar primeiro o formato comum e o leitor. O Watchdog define e valida o formato; cada projeto o adota e seu agente líder mantém o conteúdo.
  Oferecer instalação e verificação de instruções em AGENTS.md e CLAUDE.md, preservando regras existentes e evitando duplicações. Explicar título e resumo simples, detalhes técnicos separados, identidade estável, estados, sugestões dos agentes e evidências necessárias para concluir.
  Aceite: identificar instruções ausentes ou desatualizadas, apresentar a atualização antes de aplicá-la e verificar sua leitura pelo agente; não criar outra lista nem alterar TODOs de outros projetos sem autorização.
- [ ] Simplificar a lista de tarefas
  Resumo: mostrar somente o título na lista e abrir, pela setinha, apenas um resumo simples do que será feito e da situação atual.
  Não repetir o nome do projeto dentro dele. Manter instruções técnicas disponíveis no envio ao executor, fora da visualização simples; depende do formato único de tarefas.
  Aceite: a expansão não expõe o bloco técnico; uma tarefa em andamento só indica agente executando quando houver evidência ao vivo.
- [ ] Mostrar a interface em português
  Resumo: apresentar primeiro os painéis Tarefas, Progresso, Arquivos e Agentes em português para facilitar o uso.
  Definir rótulos por código e traduções revisadas; não depender de LLM durante a renderização. Preservar arquivos canônicos dos projetos, protocolos e a integração com Yazi.
  Manter como etapa posterior o seletor português/inglês em Tarefas, aplicado aos quatro painéis, preservando o pedido anterior de opção em inglês. Assistência de LLM pode apoiar a preparação de traduções para revisão, sem traduzir a interface em tempo de execução.
- [ ] Permitir execução com um agente
  Resumo: oferecer um modo econômico explícito com um único executor e revisão pelo líder, reduzindo o consumo de cota.
  O lançador atual exige executor e QA; o suporte a um único executor ainda precisa ser implementado. Definir esse modo e seus critérios de revisão sem afrouxar a validação atual nem afirmar que o suporte já existe.
  Aceite: escolha explícita do modo, revisão pelo líder e evidências verificáveis antes de aceitar a entrega.
- [ ] Ler planos do projeto
  Resumo: transformar um plano explícito do projeto em instruções delimitadas para as tarefas, sem reler o histórico inteiro das conversas.
- [ ] Melhorar o painel de agentes
  Resumo: mostrar agentes verificados do projeto, histórico cronológico de tarefas e contexto restante quando disponível.
  Mostrar canais Gossip verificados, mantendo Gossip opcional. Exibir o painel Herdr verificado de cada agente e sua tarefa mais recente em português simples, com suporte posterior a inglês.
  Indicar indisponibilidade quando não houver telemetria real de contexto. Manter Arquivos ao lado, destacar arquivos vinculados às tarefas e preservar a conexão com Yazi.
- [ ] Descobrir arquivos criados pela IA
  Resumo: descobrir e resumir automaticamente arquivos criados ou alterados pela IA, preservando o vínculo funcional com Yazi.
- [ ] Preservar o progresso do projeto
  Resumo: manter um histórico durável de conclusões para acompanhar o progresso entre edições do TODO.
  As entradas em Feito e as cópias de segurança das edições já existem; falta o histórico durável de progresso entre edições.
- [ ] Validar as sugestões do curador
  Resumo: avaliar propostas de conclusão e bloqueio em conversas reais, mantendo obrigatória a confirmação do usuário.
- [ ] Testar uma execução real completa
  Resumo: confirmar uma tarefa real no novo fluxo Orchestrate e acompanhar seu progresso de ponta a ponta.
  Verificar em Progresso as etapas Preparando → Executando → Verificando → Aguardando aprovação. Esse fluxo ainda não foi exercitado ao vivo, para economizar a cota do Codex.

## Bloqueado

## Feito
- [x] 2026-11-18 Limpeza de sessões sem travas: arquivos fora da lista não travam mais (ficam intactos, sem commit, e aparecem na tela); o formulário já lista os arquivos pendentes; `c` sobre uma operação parada oferece repetir (y, sem refazer passos já feitos) ou fechar (x, mantendo a evidência); painéis reabertos pelo Herdr após reinício são reconhecidos na transferência. Validado ao vivo: operação f6e2e141 transferiu a liderança para wD:p1P. 312 testes passaram.
- [x] 2026-11-17 Correções do fluxo: Orchestrate mostra alterações pendentes e salva um commit local de controle antes da solicitação; execuções esquecidas são marcadas como paradas (Stalled) e encerradas em Progresso (x) ou automaticamente quando aceitas no TODO; ideias e reordenação do TODO não bloqueiam mais o lançamento; estados de execução Preparando/Executando/Verificando/Aguardando/Precisa de decisão (Preparing/Running/Verifying/Waiting/Needs decision); relatórios atrasados ou substituídos permanecem no histórico; o painel fechado do líder volta a ser acompanhado após `codex resume`. 306 testes passaram.
- [x] 2026-11-17 Ponto de controle do Orchestrate: mostrar alterações e novos arquivos do projeto na confirmação e salvar um commit local autorizado antes do lançamento, sem push automático.
- [x] 2026-11-17 Correção ao vivo da limpeza de sessões: sucessor iniciado com `--yolo`; a operação f486dba6-d4aa-4c76-8de6-825fd47737ef concluiu o recebimento automático pelo sucessor com aceitação no ai-memory pelo ID exato, liberação explícita do antecessor e transferência do vínculo do Watchdog para a sessão 01a1ec04-f266-74c1-a435-78501c4286a7 no ponto de controle 1e9b0110701cc277b9c0bde46fcff1dfbf8dc30d. Todos os 50 testes direcionados passaram na verificação. Tentativas bloqueadas anteriores, incluindo a rejeição de aprovação f356165e e a aceitação bem-sucedida posterior, permanecem preservadas como evidência histórica.
- [x] 2026-11-17 Fluxo de limpeza de sessões: automatizar a divisão verificada no Herdr, a inicialização de um novo líder, a entrega delimitada de contexto e o recebimento explícito no backend de passagem de contexto; expor uma ação clara na interface. Reutilizar o procedimento observado ao vivo, preservar os limites entre os modos nativo e legado e manter os agentes atuais intactos. A passagem de contexto apenas pela camada de comandos não conclui esta tarefa.
- [x] 2026-11-17 Escopo da execução: validar somente as tarefas selecionadas para uma execução, evitando que edições não relacionadas do TODO bloqueiem o trabalho ativo; preservar as verificações de identidade, Git e QA da versão candidata exata.
- [x] 2026-11-17 Camada de comandos para passagem de liderança: exportação delimitada, prévia e adoção nativas explícitas e proteções de finalidade da sessão limpa; P1 corrigido e aprovado de forma independente em 0e7125f. Suíte da máquina: 222 testes, sem falhas, 7 ignorados. Execuções reais no Gossip legado continuam restritas à exportação; isso não conclui o fluxo da interface.
- [x] 2026-11-17 Transporte nativo: entrega na caixa de entrada do Codex para a conversa exata, relatórios locais duráveis, proteção contra duplicatas e verificações de recuperação; aprovado de forma independente em 2cf8d68 com uma prova real de entrega e relatório.
- [x] 2026-11-17 Progresso da sessão: ler automaticamente chamadas de checklist compatíveis e bem-sucedidas na conversa e atualizar Progresso. Formatos ausentes ou não suportados permanecem explícitos; os históricos locais reais não tinham pares bem-sucedidos de chamadas diretas de checklist, portanto os dados de teste do protocolo eram sintéticos.
- [x] 2026-11-17 Seletor de conversas: mostrar nomes distintos de contas antes dos identificadores de painel e sessão; nove testes direcionados passaram, incluindo seleção real por teclado em PTY estreito.
