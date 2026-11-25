---
watchdog_todo: 1
status: ativo
area: pessoal
prioridade: alta
resumo: Painéis Herdr para tarefas de projetos, progresso das sessões e arquivos criados pela IA
atualizado: 2026-11-25
motivo:
---

# TODO — Herdr Watchdog

Cada projeto usa seu próprio TODO.md com estas seções. O progresso conta as
tarefas atualmente listadas aqui; não estima o projeto inteiro.
Os itens em Próximo são planos pendentes, inclusive os acordos registrados abaixo;
o estado de cada tarefa indica o que foi entregue e o que falta.
Este TODO adota o formato versionado do Watchdog desde 2026-11-18;
os pedidos e as conclusões anteriores foram preservados na migração.

Spec #1 (Watchdog como painel do long run): tickets T1–T14 em Próximo, na ordem de execução. Conflitos para paralelizar: T3, T4, T5 e T7 mexem na mesma tela do Tasks (juntar com cuidado e checar as costuras); T11 e T13 na mesma seção do Progress (em sequência).

## Em andamento

## Próximo
- [ ] T14 (#15) Aceite manual
  ID: 82e42465-81ee-4d70-9f7b-72f856cf71b9
  Resumo:
    o Vini testa /clear no Claude e no Codex, handoff Claude e Codex, uma rodada real A/B/C e o code review com as abas.
  Origem: pedido-humano
  Referência: spec #1 e issue #15 (docs/issues/)
  Execução:
    Bloqueado por: T1 (#2), T2 (#3), T3 (#4), T4 (#5), T5 (#6), T6 (#7), T7 (#8), T8 (#9), T9 (#10), T10 (#11), T11 (#12), T12 (#13), T13 (#14).
  Aceite:
    /clear no Claude e no Codex mantém o painel. Handoff Claude para Codex com Religar mostra $; Codex para Claude volta a /. Rodada real com A livre, B dependente de A e C dependente do Vini termina com o aviso certo. O code review abre as duas abas e a correção em aba nova.
- [ ] Decidir os itens restantes do brainstorm do Watchdog
  ID: 0b6c2f1e-8a4d-4e39-9c71-5d2a7e4b9f13
  Resumo:
    definir as políticas restantes de curadoria, handoff, contexto e avisos; a portabilidade da orquestração para Watchdog já foi autorizada.
  Origem: pedido-humano
  Referência: brief brainstorm-3-way-merge.md (omarchy2, 2026-11-19)
  Execução:
    Brainstorm salvo em docs/merge-brainstorm-2026-11-19.md (recomendação: Watchdog como produto, Left Undone como inbox; Gossip fora das execuções novas).
    Correção aprovada em 2026-11-19: mudanças apenas no Watchdog, LU intacto, orquestração trazida do LU para o Watchdog e Gossip congelado. Fusão dos aplicativos e mudanças no LU saem deste escopo.
  Aceite:
    Registrar as escolhas restantes antes de implementar mudanças nessas políticas.
- [ ] Mostrar o uso de contexto por agente
  ID: e3f85c0d-2191-449c-a650-95e52a95c3e2
  Resumo:
    comparar a ocupação atual da janela de contexto de cada sessão com o limite escolhido pelo usuário, inicialmente 500.000 tokens.
  Origem: pedido-humano
  Execução:
    Resumo: comparar a ocupação atual da janela de contexto de cada sessão com o limite escolhido pelo usuário, inicialmente 500.000 tokens.
    Aceite: mostrar usado/limite, percentual e estado em texto e cor. Sugestão: verde abaixo de 80%, amarelo a partir de 80%, vermelho ao atingir ou ultrapassar 100%. Dado ausente aparece como indisponível. Verificar o limite exato e a atualização após compactação.
  Aceite:
    mostrar usado/limite, percentual e estado em texto e cor. Sugestão: verde abaixo de 80%, amarelo a partir de 80%, vermelho ao atingir ou ultrapassar 100%. Dado ausente aparece como indisponível. Verificar o limite exato e a atualização após compactação.
- [ ] Permitir execução com um agente
  ID: 56b84864-b28d-4a82-b341-84b8d3545e3e
  Resumo:
    oferecer um modo econômico explícito com um único executor e revisão pelo líder, reduzindo o consumo de cota.
  Origem: pedido-humano
  Execução:
    Resumo: oferecer um modo econômico explícito com um único executor e revisão pelo líder, reduzindo o consumo de cota.
    O fluxo de equipe mantém executor e QA. O modo Para um agente foi implementado: seleciona um executor Codex ocioso pelo painel em uma worktree limpa do projeto; o líder registra revisão com evidências para o commit e a versão exatos do resultado. Aguarda aceite do usuário.
    Aceite: escolha explícita do modo, revisão pelo líder e evidências verificáveis antes de aceitar a entrega.
    Proposta de interface: ação Despachar com opções Para um agente e Orquestrar equipe. Na primeira, escolher o executor identificado pelo painel, confirmar o destinatário e acompanhar o resultado em Progresso. Preservar o envio simples já existente.
    Entrega verificada em 2026-11-18: menu Despachar, seleção por painel/conta/sessão, confirmação separada e Progresso com revisão pelo líder; uma tarefa lógica por execução. Equipe e envio simples preservados. 385 testes sem falhas, 7 opt-in ignorados; teclado/mouse e fluxo em PTY real, integração Git temporária com rejeição de aprovação sem revisão. Painel real recarregado e menu conferido nos terminais existentes. A lista ao vivo não encontrou executor elegível; falta uma sessão dedicada ociosa em worktree limpa para validar uma execução real de modelo. Tarefa permanece aberta para aceite.
    Reconciliação em 2026-11-19: implementação commitada em 98c09e4529ea9d8a1d053aae74de5deef6637004 e enviada ao origin/main por autorização do usuário antes desta passagem de contexto. Suíte repetida: 385 testes, sem falhas, 7 ignorados. Execução com modelo real e aceite do usuário continuam pendentes; commit, push e abertura dos painéis não concluem a tarefa.
  Aceite:
    escolha explícita do modo, revisão pelo líder e evidências verificáveis antes de aceitar a entrega.
- [ ] Abrir uma auditoria independente do projeto
  ID: cfd2e586-f9a2-413f-b9cc-5598ef64970d
  Resumo:
    abrir uma nova janela no Herdr para uma sessão com contexto limpo, iniciada no diretório do projeto e dedicada à leitura do estado atual.
  Origem: pedido-humano
  Execução:
    Resumo: abrir uma nova janela no Herdr para uma sessão com contexto limpo, iniciada no diretório do projeto e dedicada à leitura do estado atual.
    Permitir escolher o modelo, com preferência por GPT Astra 6.1 quando disponível. Exibir o modelo efetivo. Entregar ao líder achados com evidências, lacunas e próximos passos, sem herdar a conversa ou assumir a liderança.
  Aceite:
    Demonstrar com evidência verificável o resultado já solicitado: abrir uma nova janela no Herdr para uma sessão com contexto limpo, iniciada no diretório do projeto e dedicada à leitura do estado atual.
- [ ] Registrar pedidos durante a conversa
  ID: 4f9fae9f-54e0-49c4-9700-8f2e90929246
  Resumo:
    manter os pedidos claros do usuário no arquivo do projeto enquanto a conversa acontece, sem esperar um commit.
  Origem: legado-nao-confirmado
  Execução:
    Resumo: manter os pedidos claros do usuário no arquivo do projeto enquanto a conversa acontece, sem esperar um commit.
    O líder registra os pedidos claros antes de commit; ideias dos agentes ficam identificadas separadamente como sugestões, sem virarem pedidos aprovados automaticamente.
    Ler o mesmo TODO.md, sem uma segunda lista de tarefas; detectar alterações e conflitos antes de aplicar atualizações. Regras gerais pertencem ao AGENTS.md e instruções específicas ficam na tarefa.
    Aceite: líder e painel compartilham a mesma fonte, com conflitos visíveis e sugestões distinguíveis de pedidos.
  Aceite:
    líder e painel compartilham a mesma fonte, com conflitos visíveis e sugestões distinguíveis de pedidos.
- [ ] Orientar os agentes a manter o TODO atualizado
  ID: 9f4cdfb9-3b30-4d69-a178-aa3ff61301a6
  Resumo:
    ajudar a preparar cada projeto para que seus agentes saibam registrar pedidos e atualizar tarefas durante a conversa, sem esperar commit.
  Origem: legado-nao-confirmado
  Execução:
    Resumo: ajudar a preparar cada projeto para que seus agentes saibam registrar pedidos e atualizar tarefas durante a conversa, sem esperar commit.
    Dependência: implementar primeiro o formato comum e o leitor. O Watchdog define e valida o formato; cada projeto o adota e seu agente líder mantém o conteúdo.
    Oferecer instalação e verificação de instruções em AGENTS.md e CLAUDE.md, preservando regras existentes e evitando duplicações. Explicar título e resumo simples, detalhes técnicos separados, identidade estável, estados, sugestões dos agentes e evidências necessárias para concluir.
    Aceite: identificar instruções ausentes ou desatualizadas, apresentar a atualização antes de aplicá-la e verificar sua leitura pelo agente; não criar outra lista nem alterar TODOs de outros projetos sem autorização.
  Aceite:
    identificar instruções ausentes ou desatualizadas, apresentar a atualização antes de aplicá-la e verificar sua leitura pelo agente; não criar outra lista nem alterar TODOs de outros projetos sem autorização.
- [ ] Mostrar a interface em português
  ID: ba3b21fa-c410-4952-8fe8-222a5bc6f9de
  Resumo:
    apresentar primeiro os painéis Tarefas, Progresso, Arquivos e Agentes em português para facilitar o uso.
  Origem: legado-nao-confirmado
  Execução:
    Resumo: apresentar primeiro os painéis Tarefas, Progresso, Arquivos e Agentes em português para facilitar o uso.
    Definir rótulos por código e traduções revisadas; não depender de LLM durante a renderização. Preservar arquivos canônicos dos projetos, protocolos e a integração com Yazi.
    Manter como etapa posterior o seletor português/inglês em Tarefas, aplicado aos quatro painéis, preservando o pedido anterior de opção em inglês. Assistência de LLM pode apoiar a preparação de traduções para revisão, sem traduzir a interface em tempo de execução.
  Aceite:
    Demonstrar com evidência verificável o resultado já solicitado: apresentar primeiro os painéis Tarefas, Progresso, Arquivos e Agentes em português para facilitar o uso.
- [ ] Ler planos do projeto
  ID: e3d9935a-b4c3-4256-b3a5-f0fa08dffe24
  Resumo:
    transformar um plano explícito do projeto em instruções delimitadas para as tarefas, sem reler o histórico inteiro das conversas.
  Origem: legado-nao-confirmado
  Execução:
    Resumo: transformar um plano explícito do projeto em instruções delimitadas para as tarefas, sem reler o histórico inteiro das conversas.
  Aceite:
    Demonstrar com evidência verificável o resultado já solicitado: transformar um plano explícito do projeto em instruções delimitadas para as tarefas, sem reler o histórico inteiro das conversas.
- [ ] Descobrir arquivos criados pela IA
  ID: bad09fc3-a213-4fa6-9877-a33a7cf65aa4
  Resumo:
    descobrir e resumir automaticamente arquivos criados ou alterados pela IA, preservando o vínculo funcional com Yazi.
  Origem: legado-nao-confirmado
  Execução:
    Resumo: descobrir e resumir automaticamente arquivos criados ou alterados pela IA, preservando o vínculo funcional com Yazi.
  Aceite:
    Demonstrar com evidência verificável o resultado já solicitado: descobrir e resumir automaticamente arquivos criados ou alterados pela IA, preservando o vínculo funcional com Yazi.
- [ ] Preservar o progresso do projeto
  ID: 7b33fb64-2f30-4140-b9bb-e09d5095011b
  Resumo:
    manter um histórico durável de conclusões para acompanhar o progresso entre edições do TODO.
  Origem: legado-nao-confirmado
  Execução:
    Resumo: manter um histórico durável de conclusões para acompanhar o progresso entre edições do TODO.
    As entradas em Feito e as cópias de segurança das edições já existem; falta o histórico durável de progresso entre edições.
  Aceite:
    Demonstrar com evidência verificável o resultado já solicitado: manter um histórico durável de conclusões para acompanhar o progresso entre edições do TODO.
- [ ] Validar as sugestões do curador
  ID: a7b83b35-b133-451a-bbd7-85c7477bd849
  Resumo:
    avaliar propostas de conclusão e bloqueio em conversas reais, mantendo obrigatória a confirmação do usuário.
  Origem: legado-nao-confirmado
  Execução:
    Resumo: avaliar propostas de conclusão e bloqueio em conversas reais, mantendo obrigatória a confirmação do usuário.
  Aceite:
    Demonstrar com evidência verificável o resultado já solicitado: avaliar propostas de conclusão e bloqueio em conversas reais, mantendo obrigatória a confirmação do usuário.
- [ ] Testar uma execução real completa
  ID: b6cb93d7-46ca-4f00-8d4d-ce3ac0dce6fe
  Resumo:
    confirmar uma tarefa real no novo fluxo Orchestrate e acompanhar seu progresso de ponta a ponta.
  Origem: legado-nao-confirmado
  Execução:
    Resumo: confirmar uma tarefa real no novo fluxo Orchestrate e acompanhar seu progresso de ponta a ponta.
    Verificar em Progresso as etapas Preparando → Executando → Verificando → Aguardando aprovação. Esse fluxo ainda não foi exercitado ao vivo, para economizar a cota do Codex.
  Aceite:
    Demonstrar com evidência verificável o resultado já solicitado: confirmar uma tarefa real no novo fluxo Orchestrate e acompanhar seu progresso de ponta a ponta.

## Bloqueado
- [ ] Trazer a orquestração do Left Undone para o Watchdog
  ID: 9a1da315-9c0d-40b1-a576-dd3bdcfc65d2
  Resumo:
    abrir novos executores Codex ou Claude pelo Watchdog, com tarefas juntas ou separadas e planejamento antes da execução.
  Origem: pedido-humano
  Execução:
    Escopo corrigido por Vini em 2026-11-19: modificar apenas Watchdog, manter Left Undone intacto e congelar Gossip.
    Adaptar o fluxo do LU ao registro de execuções e às worktrees do Watchdog; não chamar o dispatcher nem alterar dados do LU.
    Implementado em 2026-11-19: novo executor, contrato no lançamento, callbacks autenticados, continuação em nova tentativa, agrupamento, planejamento nativo e confirmação na interface. Verificação: 435 testes, sem falhas, 7 ignorados; revisão independente com seis correções comprovadas por regressões; telas conferidas em janela temporária. Evidências em docs/verification-orchestration-2026-11-19.md.
    Não interpretar a entrega como aprovação das outras decisões do brainstorm. Validação com modelos reais e aceite operacional continuam separados dos testes automatizados.
  Aceite:
    Comprovar despacho e retorno no Watchdog para Codex e Claude, sem alterar LU; propostas não concluem implementação e resultados aguardam revisão do líder.
  Motivo: adiada pelo Vini em 2026-11-25; depois da spec #1 a orquestração vai do Watchdog para o Left Undone, não o contrário.

## Feito
- [x] 2026-11-25 T13 (#14) Pergunta pendente e meta encerrada
  ID: 595712f8-ab5f-4540-b943-940648397038
  Resumo:
    faixa de pergunta de X aguarda você, faixa fixa de fim com resumo e notificação no desktop nos dois casos.
  Origem: pedido-humano
  Referência: spec #1 e issue #14 (docs/issues/)
  Execução:
    Bloqueado por: T6 (#7), T11 (#12).
  Aceite:
    Pergunta para o Vini mostra a faixa e dispara a notificação. Meta encerrada mostra a faixa fixa até o próximo despacho e dispara a notificação. O aviso final do líder segue o formato concluídas com evidência e bloqueadas com motivo e próximo passo.
- [x] 2026-11-25 T6 (#7) Trava por pane e aviso do executor
  ID: bc16b8da-9694-472d-8f6d-1d7ffb994683
  Resumo:
    toda escrita no pane do líder passa por uma trava; comando de aviso pronto/BLOQUEIO para executores.
  Origem: pedido-humano
  Referência: spec #1 e issue #7 (docs/issues/)
  Execução:
    Bloqueado por: T1 (#2).
  Aceite:
    Dois avisos simultâneos chegam como duas mensagens inteiras. Um texto do Tasks e um aviso simultâneos não se misturam. O comando de aviso aceita pronto (commit, testes, resumo) e BLOQUEIO (dúvida). O padrão do dispatch passa a usar esse comando no contrato. Testes no ponto de teste B com Herdr falso cobrem os cenários.
- [x] 2026-11-25 T12 (#13) Code review em duas abas
  ID: fdc62343-7c2f-4cfc-99de-347a7cf816e5
  Resumo:
    botão code-review com a base do grupo; aba Code Review com Standards e Spec pelo kit; lado a lado; correção em aba nova após o ok.
  Origem: pedido-humano
  Referência: spec #1 e issue #13 (docs/issues/)
  Execução:
    Bloqueado por: T7 (#8), T8 (#9).
  Aceite:
    O botão sai com a base do grupo e a branch de integração, editáveis. O padrão traz os contratos-modelo de Standards e Spec. Os relatórios ficam na pasta de execução do projeto. A correção abre numa aba nova só depois do ok.
- [x] 2026-11-25 T11 (#12) Seção AGENTES no Progress
  ID: 8d30059f-5d67-4f25-81ed-c09fd01c5eb3
  Resumo:
    sempre visível, sem botão: líder e executores com estado, contexto ao vivo e checagem inicial; tarefas que esperam ou dependem do Vini.
  Origem: pedido-humano
  Referência: spec #1 e issue #12 (docs/issues/)
  Execução:
    Bloqueado por: T8 (#9).
  Aceite:
    O líder e cada executor registrado aparecem com pane, estado e contexto ao vivo. A checagem inicial aparece na linha do executor. Tarefas que esperam outra ou dependem do Vini aparecem sem pane. A seção não tem botão e não envia nada.
- [x] 2026-11-25 T10 (#11) Vínculo que acompanha o líder
  ID: 7fc2a094-f6c5-4838-b6f3-2f144bae2dd0
  Resumo:
    /clear no mesmo pane segue sem aviso; troca de harness troca os botões e avisa; tecla Religar; reenviar a meta depois do /clear.
  Origem: pedido-humano
  Referência: spec #1 e issue #11 (docs/issues/)
  Execução:
    Bloqueado por: T7 (#8).
  Aceite:
    /clear no Claude mantém o vínculo sem aviso. /clear no Codex mantém o vínculo sem aviso. Troca de harness troca os prefixos e mostra o aviso. Religar liga o painel ao pane escolhido. Outro pane ou sessão antiga ainda viva não é seguido sozinho. Reenviar a meta digita a meta do grupo atual.
- [x] 2026-11-25 T8 (#9) Kit do líder: abrir executor e fechar tarefa
  ID: b50f11f9-edf0-4402-9061-33885c8e1436
  Resumo:
    abrir executor em worktree e aba da leva, rodapé comum do contrato, pasta de execução no projeto, fechar issue com cópia local.
  Origem: pedido-humano
  Referência: spec #1 e issue #9 (docs/issues/)
  Execução:
    Bloqueado por: T6 (#7).
  Aceite:
    Abrir executor cria a worktree e a branch a partir da integração e o pane na aba da leva. Tarefas liberadas depois entram na aba da leva de que dependiam, enquanto houver espaço. O executor aberto fica registrado para o painel, com tarefa e pane. Modelo e esforço vêm da seção Dispatch do projeto. Fechar tarefa comenta e fecha a issue e atualiza a cópia local. O padrão do dispatch passa a citar o kit, a checagem aos 2, 3 e 4 minutos e o merge da integração antes do aviso. Testes no ponto de teste B cobrem abrir e fechar.
- [x] 2026-11-25 T5 (#6) Implementar aqui
  ID: 0270c2fe-4bf9-4c92-b1ff-06cde89a21b6
  Resumo:
    segundo modo de despacho, em que o próprio líder implementa numa worktree própria e faz merge na integração.
  Origem: pedido-humano
  Referência: spec #1 e issue #6 (docs/issues/)
  Execução:
    Bloqueado por: T1 (#2).
  Aceite:
    A prévia mostra qual modo foi escolhido. Implementar aqui digita a meta com o texto de implementar nesta sessão. O padrão do dispatch descreve o modo Implementar aqui e o uso de worktree pelo líder. O grupo soma igual ao Despachar.
- [x] 2026-11-25 T9 (#10) Skill e botão merge-danger
  ID: 28d47bb7-865e-44f9-9c45-ce72d2baa1c1
  Resumo:
    skill nova que classifica porta e raio da integração e devolve integra, revisar ou não integrar; botão na faixa.
  Origem: pedido-humano
  Referência: spec #1 e issue #10 (docs/issues/)
  Execução:
    Bloqueado por: T7 (#8).
  Aceite:
    A skill fica instalada para Claude e Codex. O botão aparece na faixa com o prefixo do harness. A resposta lista porta, raio e decisão por parte. Itens da lista de "sempre mão única" do projeto saem sempre como porta única.
- [x] 2026-11-25 T3 (#4) Despacho com meta ativa e zerar o grupo
  ID: 052f8c88-b706-4299-8624-9ce1ac07ffff
  Resumo:
    com meta ativa, enviar só "Grupo atualizado: +…"; zerar sozinho quando tudo está concluído e chega novo despacho; tecla para zerar à mão.
  Origem: pedido-humano
  Referência: spec #1 e issue #4 (docs/issues/)
  Execução:
    Bloqueado por: T1 (#2).
  Aceite:
    Com meta ativa, despachar D, E e F digita só "Grupo atualizado: +D, +E, +F" e o grupo passa de 3 para 6. Com todo o grupo concluído, o próximo despacho começa um grupo novo e uma base nova. Com tarefa aberta no grupo, o próximo despacho soma. Zerar à mão esvazia o grupo e a próxima prévia volta a ser a meta. A prévia mostra qual dos dois textos será enviado.
- [x] 2026-11-25 T7 (#8) Faixa de skills do Matt
  ID: 43ab9d91-244f-45d3-8185-29c844e2de7c
  Resumo:
    botões só das skills instaladas para o harness do líder, com / no Claude e $ no Codex, prévia editável e aviso de tracker sem cópia local.
  Origem: pedido-humano
  Referência: spec #1 e issue #8 (docs/issues/)
  Execução:
    Bloqueado por: T1 (#2).
  Aceite:
    Líder Claude mostra /to-spec e líder Codex mostra $to-spec. Skill não instalada para aquele harness não aparece. O texto pode ser editado antes do Enter. to-tickets vem com a referência da spec quando o painel a encontra. Tracker sem a seção de cópia local mostra o aviso.
- [x] 2026-11-25 T4 (#5) Prévia que classifica a seleção
  ID: ab2a4cc9-bd50-4311-8733-942263533c3a
  Resumo:
    classificar cada tarefa (livre, espera outra, espera fora da seleção, depende do Vini); bloquear quando nada pode começar; avisar projeto sem Dispatch ou sem import no CLAUDE.md.
  Origem: pedido-humano
  Referência: spec #1 e issue #5 (docs/issues/)
  Execução:
    Bloqueado por: T1 (#2).
  Aceite:
    A prévia mostra a classificação de cada tarefa selecionada. Sem nenhuma tarefa livre, nada é enviado até o Vini escolher incluir, cancelar ou mandar assim mesmo. Incluir a dependência acrescenta a tarefa bloqueadora à seleção. Projeto sem seção Dispatch ou sem import no CLAUDE.md mostra um aviso, sem impedir o envio.
- [x] 2026-11-25 T1 (#2) Despachar a seleção com a meta do grupo
  ID: 69bef575-046d-43ab-99de-89c91bea4782
  Resumo:
    primeira versão ponta a ponta: Despachar com prévia digita a meta curta que aponta para o grupo; o grupo soma e deduplica; anota a base da integração; o g sai.
  Origem: pedido-humano
  Referência: spec #1 e issue #2 (docs/issues/)
  Execução:
    Sem bloqueio; pode começar.
  Aceite:
    Despachar A, B e C sem meta ativa digita a meta curta no pane do líder, com Enter, e o grupo do Progress mostra 0 de 3. Despachar soma ao grupo existente e uma tarefa já presente não conta duas vezes. No primeiro despacho de um grupo, a ponta da branch de integração do projeto fica anotada como base. A meta cita pelo nome o padrão do dispatch e a seção Dispatch do AGENTS.md. O padrão do dispatch existe com as regras acordadas na spec (executor por tarefa, worktree, aviso, espera sem polling, checagem de spec, integração só no checkout principal, aviso final). A ação antiga de gravar o grupo à mão não existe mais. Testes no ponto de teste A cobrem os cenários acima.
- [x] 2026-11-25 T2 (#3) Nomes Review Curator e Verify Leader
  ID: 87c5ccbf-3c5d-47e7-9ff7-2d253c321d9e
  Resumo:
    renomear Review para Review Curator e Verificar para Verify Leader no Tasks, no README e nos testes.
  Origem: pedido-humano
  Referência: spec #1 e issue #3 (docs/issues/)
  Execução:
    Sem bloqueio; pode começar.
  Aceite:
    O Tasks mostra Review Curator e Verify Leader nos botões, dicas e prévias. O README usa os nomes novos. Os testes do Tasks passam nos dois modos de controles.
- [x] 2026-11-25 Brainstorm do Watchdog como painel do long run, setup das skills do Matt, spec #1 e tickets T1–T14 publicados
  ID: f14cf1e7-f4e0-42dc-9482-22f8a43b93b9
  Resumo:
    decisões D1–D23 sintetizadas na spec #1; T1–T14 como sub-issues com bloqueio nativo e cópia em docs/issues/; GLOSSARY.md, AGENTS.md e CLAUDE.md criados.
  Origem: pedido-humano
  Execução:
    Spec #1 e issues #2–#15 em viniabdalla/herdr-watchdog.
  Aceite:
    Spec e tickets visíveis no GitHub e no Tasks; grupo T1–T14 no Progress.
- [x] Melhorar o painel de agentes
  ID: 5daa552a-b547-441a-b2f2-12976b061e72
  Resumo:
    mostrar agentes verificados do projeto, histórico cronológico de tarefas e contexto restante quando disponível.
  Origem: pedido-humano
  Execução:
    Resumo: mostrar agentes verificados do projeto, histórico cronológico de tarefas e contexto restante quando disponível.
    Gossip congelado: não adicionar canais ou novas integrações. Exibir o painel Herdr verificado de cada agente e sua tarefa mais recente em português simples, com suporte posterior a inglês.
    Indicar indisponibilidade quando não houver telemetria real de contexto. Manter Arquivos ao lado, destacar arquivos vinculados às tarefas e preservar a conexão com Yazi.
    Aceite adicional: para duas sessões do mesmo projeto, mostrar uma linha por agente, com papel, diretório de trabalho e endereço Herdr (workspace e painel) verificados por sessão.
  Aceite:
    Com duas sessões no mesmo projeto, identificar cada agente pelo papel, diretório e painel Herdr. Conferir o histórico de tarefas e a disponibilidade da leitura de contexto por sessão.
- [x] Simplificar a lista de tarefas
  ID: 944eefe8-edd3-41fa-b35f-e748d3c91681
  Resumo:
    mostrar somente o título na lista e abrir, pela setinha, apenas um resumo simples do que será feito e da situação atual.
  Origem: legado-nao-confirmado
  Execução:
    Resumo: mostrar somente o título na lista e abrir, pela setinha, apenas um resumo simples do que será feito e da situação atual.
    Não repetir o nome do projeto dentro dele. Manter instruções técnicas disponíveis no envio ao executor, fora da visualização simples; depende do formato único de tarefas.
    Aceite: a expansão não expõe o bloco técnico; uma tarefa em andamento só indica agente executando quando houver evidência ao vivo.
    Entrega verificada em 2026-11-18: lista com títulos e setinha; clique/Enter e setas expandem/recolhem Resumo e Situação. Checkbox seleciona separadamente. Instruções técnicas continuam completas no envio. Testes de mouse e teclado em PTY, painel estreito e proteção de execução por UUID. Suíte: 355 testes sem falhas, 7 opt-in ignorados. Painéis Tarefas e Progresso recarregados nos terminais existentes e conferidos ao vivo; formato v1 adotado neste projeto com histórico preservado.
  Aceite:
    a expansão não expõe o bloco técnico; uma tarefa em andamento só indica agente executando quando houver evidência ao vivo.
<!-- watchdog-history:begin -->
- [x] 2026-11-18 Padronizar o arquivo de tarefas
  Resumo: reunir em um único TODO.md por projeto tudo o que a pessoa precisa entender e o executor precisa receber, sem perder o histórico.
  Definir ID estável, título humano curto, resumo do que será feito e seu benefício, estado e instruções técnicas com critérios de aceite no mesmo arquivo.
  Implementar leitura determinística por código e validação de esquema. Planejar compatibilidade e migração dos arquivos atuais, preservando histórico e tratando mudanças de identidade explicitamente, sem invalidar execuções silenciosamente.
  Aceite: títulos e detalhes podem mudar sem perder a identidade estável; arquivos antigos e execuções existentes têm tratamento explícito. A sintaxe atual continua valendo até essa implementação.
  Entrega validada em 2026-11-18: formato versionado com UUID fixo, campos separados e validação determinística; contratos novos por identidade estável com revisão explícita de conteúdo alterado; compatibilidade com contratos antigos; comandos todo validate/preview/render/apply, migração com backup, histórico literal e bloqueio por execução afetada, e troca explícita de identidade com registro.
  Verificação: suíte de 347 testes sem falhas, 7 opt-in ignorados; testes de integração em Git temporário e revisão pelo líder. O TODO real permanece no formato antigo; a conversão exige prévia revisada. Interface simples, tradução e registro automático de pedidos continuam em suas tarefas próprias.
<!-- watchdog-history:end -->
<!-- watchdog-history:begin -->
- [x] 2026-11-18 Painéis voltam após reinício do Herdr: `watchdog` reconhece os painéis restaurados (IDs de terminal novos) e religa Artifacts e Files; Clean sessions concluído vira uma linha que some em 10 min.
<!-- watchdog-history:end -->
<!-- watchdog-history:begin -->
- [x] 2026-11-18 Líder junta o trabalho sozinho: quando o QA aprova, o líder recebe o comando de aprovação, e aprovar junta o trabalho aprovado na branch do projeto (fast-forward ou merge) e envia para o origin; conflito desfaz tudo e diz para pedir ao worker um rebase. O usuário não precisa mais olhar branches. 316 testes passaram.
<!-- watchdog-history:end -->
<!-- watchdog-history:begin -->
- [x] 2026-11-18 Limpeza de sessões sem travas: arquivos fora da lista não travam mais (ficam intactos, sem commit, e aparecem na tela); o formulário já lista os arquivos pendentes; `c` sobre uma operação parada oferece repetir (y, sem refazer passos já feitos) ou fechar (x, mantendo a evidência); painéis reabertos pelo Herdr após reinício são reconhecidos na transferência. Validado ao vivo: operação f6e2e141 transferiu a liderança para wD:p1P. 312 testes passaram.
<!-- watchdog-history:end -->
<!-- watchdog-history:begin -->
- [x] 2026-11-17 Correções do fluxo: Orchestrate mostra alterações pendentes e salva um commit local de controle antes da solicitação; execuções esquecidas são marcadas como paradas (Stalled) e encerradas em Progresso (x) ou automaticamente quando aceitas no TODO; ideias e reordenação do TODO não bloqueiam mais o lançamento; estados de execução Preparando/Executando/Verificando/Aguardando/Precisa de decisão (Preparing/Running/Verifying/Waiting/Needs decision); relatórios atrasados ou substituídos permanecem no histórico; o painel fechado do líder volta a ser acompanhado após `codex resume`. 306 testes passaram.
<!-- watchdog-history:end -->
<!-- watchdog-history:begin -->
- [x] 2026-11-17 Ponto de controle do Orchestrate: mostrar alterações e novos arquivos do projeto na confirmação e salvar um commit local autorizado antes do lançamento, sem push automático.
<!-- watchdog-history:end -->
<!-- watchdog-history:begin -->
- [x] 2026-11-17 Correção ao vivo da limpeza de sessões: sucessor iniciado com `--yolo`; a operação f486dba6-d4aa-4c76-8de6-825fd47737ef concluiu o recebimento automático pelo sucessor com aceitação no ai-memory pelo ID exato, liberação explícita do antecessor e transferência do vínculo do Watchdog para a sessão 01a1ec04-f266-74c1-a435-78501c4286a7 no ponto de controle 1e9b0110701cc277b9c0bde46fcff1dfbf8dc30d. Todos os 50 testes direcionados passaram na verificação. Tentativas bloqueadas anteriores, incluindo a rejeição de aprovação f356165e e a aceitação bem-sucedida posterior, permanecem preservadas como evidência histórica.
<!-- watchdog-history:end -->
<!-- watchdog-history:begin -->
- [x] 2026-11-17 Fluxo de limpeza de sessões: automatizar a divisão verificada no Herdr, a inicialização de um novo líder, a entrega delimitada de contexto e o recebimento explícito no backend de passagem de contexto; expor uma ação clara na interface. Reutilizar o procedimento observado ao vivo, preservar os limites entre os modos nativo e legado e manter os agentes atuais intactos. A passagem de contexto apenas pela camada de comandos não conclui esta tarefa.
<!-- watchdog-history:end -->
<!-- watchdog-history:begin -->
- [x] 2026-11-17 Escopo da execução: validar somente as tarefas selecionadas para uma execução, evitando que edições não relacionadas do TODO bloqueiem o trabalho ativo; preservar as verificações de identidade, Git e QA da versão candidata exata.
<!-- watchdog-history:end -->
<!-- watchdog-history:begin -->
- [x] 2026-11-17 Camada de comandos para passagem de liderança: exportação delimitada, prévia e adoção nativas explícitas e proteções de finalidade da sessão limpa; P1 corrigido e aprovado de forma independente em 0e7125f. Suíte da máquina: 222 testes, sem falhas, 7 ignorados. Execuções reais no Gossip legado continuam restritas à exportação; isso não conclui o fluxo da interface.
<!-- watchdog-history:end -->
<!-- watchdog-history:begin -->
- [x] 2026-11-17 Transporte nativo: entrega na caixa de entrada do Codex para a conversa exata, relatórios locais duráveis, proteção contra duplicatas e verificações de recuperação; aprovado de forma independente em 2cf8d68 com uma prova real de entrega e relatório.
<!-- watchdog-history:end -->
<!-- watchdog-migration: {"ids": {"00eb1de35a1fcf96ba66903b7c2c6b2c697960ef9c55aa5cd9104961bf157203": "4f9fae9f-54e0-49c4-9700-8f2e90929246", "023155d8d2dcd83c61f20780b53b75cf0f3c04ca849177bf311dd3fda51b22de": "a7b83b35-b133-451a-bbd7-85c7477bd849", "05f311a3d386e819aa23f4007986db61b5f2c6a8c0e22725b98bd920f70f37bb": "ba3b21fa-c410-4952-8fe8-222a5bc6f9de", "0c691b1f22e9965e397819828b592d0c6328eae668a05d9309213878e4b3581b": "9f4cdfb9-3b30-4d69-a178-aa3ff61301a6", "1417483645f63b7001939bb37a557f3d41fad9e9306a0ca3632979ad2f662f1a": "944eefe8-edd3-41fa-b35f-e748d3c91681", "49fe617b823b415094f7eb794334249316c8c6ef64e3c4a3f9216df359caa194": "e3f85c0d-2191-449c-a650-95e52a95c3e2", "51d9accd180b87bf76f9b1c704bdc5189c5e41bdcb2a01ae82db15b6e6a210e6": "bad09fc3-a213-4fa6-9877-a33a7cf65aa4", "556d274e78555a5b8dc61947d2c529e09e6b8204f98f0bb41edbbabfa2d72612": "7b33fb64-2f30-4140-b9bb-e09d5095011b", "66f82084ab40c4c5917f1005f62d039b01ddc96f75dc5f34d8cdad85bfb5f3b3": "b6cb93d7-46ca-4f00-8d4d-ce3ac0dce6fe", "71c1026b3f651ebe86e004425c3e33c84341a4d0ab82f2122ae026da94b4d98f": "cfd2e586-f9a2-413f-b9cc-5598ef64970d", "7253bfbdd6948564b09e933528b41fe3ad8800965649d9ed048d298570683593": "56b84864-b28d-4a82-b341-84b8d3545e3e", "7a2b326088b99377fe188f731d14a825d4640ac16a0c41dc92c56e960e1a6dea": "5daa552a-b547-441a-b2f2-12976b061e72", "861b1d2f695313a6353823e5f8b17da9d07d04562d24c0b6add0e81991e3dcb4": "e3d9935a-b4c3-4256-b3a5-f0fa08dffe24"}, "kind": "legacy", "source_digest": "4e64080060c73cee838740ab2d6995f6a1b00ca37e1efca967362834b5124c90", "version": 1} -->
