---
watchdog_todo: 1
status: ativo
area: pessoal
prioridade: alta
resumo: Painéis Herdr para tarefas de projetos, progresso das sessões e arquivos criados pela IA
atualizado: 2026-11-26
motivo:
---

# TODO — Herdr Watchdog

Cada projeto usa seu próprio TODO.md com estas seções. O progresso conta as
tarefas atualmente listadas aqui; não estima o projeto inteiro.
Os itens em Próximo são planos pendentes, inclusive os acordos registrados abaixo;
o estado de cada tarefa indica o que foi entregue e o que falta.
Este TODO adota o formato versionado do Watchdog desde 2026-11-18;
os pedidos e as conclusões anteriores foram preservados na migração.

A spec #1 tem os tickets T1–T13 em Feito. O aceite manual T14 (#15) está em andamento.

O brainstorm foi encerrado na spec anterior. Em 25/11, Vini retirou do escopo a transferência de orquestração entre Watchdog e Left Undone.

Como escrever neste arquivo: `docs/agents/todo.md` (um item por ticket, criado depois do `/to-tickets`).

## Em andamento

## Próximo
- [ ] T20 (#42) Preparar projeto novo com a regra e o gatilho do TODO
  ID: e6ae5354-2679-462f-94b0-0983ece6b9dc
  Resumo:
    Preparar projeto novo com a regra e o gatilho do TODO.
  Origem: pedido-humano
  Referência: docs/pesquisa-regra-do-todo-2026-11-26.md e issue #42 (docs/issues/42-preparar-projeto-com-regra-todo.md)
  Execução:
    Bloqueado por: T16 (#38), T17 (#39).
  Aceite:
    Num projeto sem esses arquivos, a preparação cria só o que falta, com prévia e confirmação.
    Arquivos existentes nunca são sobrescritos. Seção ausente é acrescentada.
    Sem `docs/agents/issue-tracker.md`, a preparação avisa para rodar `/setup-matt-pocock-skills` e não inventa o arquivo.
    Testes isolados cobrem criação, preservação e aviso.
- [ ] [Bug #29] Prévia do despacho classifica errado dependências em texto solto
  ID: 1cdb7fd0-2848-4f93-a26d-9bfd2bd00a7a
  Resumo:
    Visto na rodada A/B/C do aceite T14 em test-watchdog-erase.
  Origem: pedido-humano
  Referência: docs/issues/29-previa-dependencia-texto-solto.md
  Execução:
    Aguarda a triagem do Vini (needs-triage).
  Aceite:
    Os critérios da issue #29.
- [ ] [Bug #30] Um item do TODO sem ID derruba o Tasks inteiro
  ID: d08d60fb-90ff-4286-9b3b-84573aa17eff
  Resumo:
    Visto na rodada A/B/C do aceite T14 em test-watchdog-erase.
  Origem: pedido-humano
  Referência: docs/issues/30-todo-item-sem-id-derruba-tasks.md
  Execução:
    Aguarda a triagem do Vini (needs-triage).
  Aceite:
    Os critérios da issue #30.
- [ ] [Bug #31] Seleção guarda tarefas que sumiram do TODO e trava o despacho
  ID: 1c768125-eac9-42cf-917d-394c99e7b9c2
  Resumo:
    Visto na rodada A/B/C do aceite T14 em test-watchdog-erase.
  Origem: pedido-humano
  Referência: docs/issues/31-selecao-fantasma-trava-despacho.md
  Execução:
    Aguarda a triagem do Vini (needs-triage).
  Aceite:
    Os critérios da issue #31.
- [ ] [Bug #32] Meta colada no Claude sem Enter: despacho não confirmado e Fila travada falsa
  ID: fabe3044-b23a-4475-a920-71c8c7077d63
  Resumo:
    Visto na rodada A/B/C do aceite T14 em test-watchdog-erase. É o mais grave: travou a fila do líder e deixou o grupo sem goal.
  Origem: pedido-humano
  Referência: docs/issues/32-meta-colada-sem-enter-no-claude.md
  Execução:
    Aguarda a triagem do Vini (needs-triage).
  Aceite:
    Os critérios da issue #32.
- [ ] [Bug #33] Curador mostra falha em estados transitórios depois do /clear
  ID: ee7dfc7b-de01-4441-a248-160bbfe66e3d
  Resumo:
    Visto na rodada A/B/C do aceite T14 em test-watchdog-erase.
  Origem: pedido-humano
  Referência: docs/issues/33-curador-falha-transitoria-apos-clear.md
  Execução:
    Aguarda a triagem do Vini (needs-triage).
  Aceite:
    Os critérios da issue #33.
- [ ] [Bug #34] kit abrir para na tela de confiança do Codex e entrega sem trava
  ID: 13e604b6-d07e-481a-9543-8b79a0857acb
  Resumo:
    Visto na rodada A/B/C do aceite T14 em test-watchdog-erase.
  Origem: pedido-humano
  Referência: docs/issues/34-kit-abrir-tela-de-confianca-codex.md
  Execução:
    Aguarda a triagem do Vini (needs-triage).
  Aceite:
    Os critérios da issue #34.
- [ ] [Bug #35] Progress mostra executor ativo como Bloqueado com JSON cru
  ID: 515fcc72-d3e2-40c3-a401-51733c0aef30
  Resumo:
    Visto na rodada A/B/C do aceite T14 em test-watchdog-erase.
  Origem: pedido-humano
  Referência: docs/issues/35-progress-executor-ativo-bloqueado.md
  Execução:
    Aguarda a triagem do Vini (needs-triage).
  Aceite:
    Os critérios da issue #35.
- [ ] [Feature] Correções da revisão R3: três P2 no Progress e um P3 no instalador
  ID: fb43c591-17d7-4201-b5a8-5b416e7bb648
  Resumo:
    Vini pediu spec antes de implementar; depois os tickets vão para o Dispatch.
  Origem: pedido-humano
  Referência: .watchdog/run/2026-11-25/R3-Integral-Spec-c6ed3067-relatorio.md e R3-Integral-Standards-8ea9753c-relatorio.md
  Execução:
    Ainda não iniciada.
  Aceite:
    Spec publicada com aprovação do Vini e tickets prontos para o Dispatch.
- [ ] T21 (#26) Trocar e lembrar a pasta da aba
  ID: e81f510c-ae62-4ee9-8e2b-6b937b521fc4
  Resumo:
    Trocar e lembrar a pasta da aba.
  Origem: pedido-humano
  Referência: spec #25 e issue #26 (docs/issues/26-trocar-e-lembrar-a-pasta-da-aba.md)
  Execução:
    Liberado. A spec #25 teve as duas recusas reproduzidas numa worktree Git temporária.
  Aceite:
    A lista contém as worktrees do repositório do Tasks, inclusive a original, e identifica a atual.
    Ao escolher B, o Tasks passa a ler o TODO de B e Progress, Artifacts e Yazi passam a acompanhar B. Os quatro conservam os mesmos panes.
    Reabrir o Watchdog recupera B. Selecionar A na mesma lista traz os quatro painéis de volta.
    Quando a troca é recusada, o Tasks informa na tela o motivo e o próximo passo.
    Demonstrar o percurso com duas worktrees e uma segunda aba em recursos isolados. Conferir que os painéis da outra aba e o state.db compartilhado ficam intactos.
- [ ] T22 (#27) Despachar ao mesmo líder depois de trocar a pasta
  ID: daff81d9-4574-42fc-9bd2-ea09e2e2d9c1
  Resumo:
    Despachar ao mesmo líder depois de trocar a pasta.
  Origem: pedido-humano
  Referência: spec #25 e issue #27 (docs/issues/27-despachar-ao-mesmo-lider-depois-da-troca.md)
  Execução:
    Bloqueado por: T21 (#26).
  Aceite:
    Em recursos isolados, ligar o líder em A, trocar a aba para B, marcar uma tarefa de B e confirmar o primeiro despacho. Conferir na mensagem recebida a tarefa e o caminho de B, na mesma conversa.
    Repetir com um grupo que já tem meta nessa conversa. A atualização incremental também leva o caminho de B. Ao voltar para A, o próximo despacho leva o caminho de A.
    Religar mantém a conferência de identidade. Se o líder começou em A e o Tasks está em B, uma religação recusada identifica as duas pastas e orienta voltar a A ou abrir um líder em B.
    Toda recusa de despacho ou religação explica o motivo e o próximo passo na tela. Conferir que as ações preservam os painéis da outra aba e o state.db compartilhado.
- [ ] T23 (#28) Levar a seleção aos seis botões de skill do Tasks
  ID: da3dc660-82bc-4771-ac62-6e07bf5e5c6c
  Resumo:
    Levar a seleção aos seis botões de skill do Tasks.
  Origem: pedido-humano
  Referência: spec #24 e issue #28 (docs/issues/28-selecao-nos-seis-botoes-de-skill.md)
  Execução:
    Liberado; pode começar em paralelo com T21 (#26). Reproduzido em terminal isolado que grill-with-docs envia só o nome da skill mesmo com tarefa marcada.
  Aceite:
    Com zero tarefas marcadas e o cursor sobre uma linha, enviar o comando habitual com seus argumentos, sem acrescentar tarefa.
    Com A marcada e o cursor em B, mostrar e enviar o caminho do TODO da worktree, o título e o ID de A.
    Com várias marcadas, incluir apenas essas tarefas na ordem do painel. Títulos iguais continuam distinguíveis pelos IDs.
    Em todos os casos, code-review conserva o intervalo do grupo e to-tickets conserva o caminho da spec quando disponíveis. Conferir também os avisos próprios quando faltarem dados.
    Enter entrega uma vez o texto exibido, inclusive após edição. Esc cancela a prévia sem envio. Abrir e cancelar preservam a seleção e o grupo.
- [ ] [Verificação] Conferir o limite de contexto e a leitura após compactação
  ID: e3f85c0d-2191-449c-a650-95e52a95c3e2
  Resumo:
    Confirmar o limite usado por cada sessão e observar a leitura depois de compactar.
  Origem: pedido-humano
  Execução:
    O Progress já mostra usado/limite, barra por nível e ausência de dados (spec #21, a74a7ae e tests/test_progress_board.py). Agents mostra o percentual e permite ajustar a janela do Claude. O mesmo UUID consta em Feito na branch feat/bundled-matt-workflow (9fb46f3). Neste checkout o Codex usa a janela informada pela sessão. Resta confirmar a política dos 500.000 tokens e observar uma compactação real.
  Aceite:
    mostrar usado/limite, percentual e estado em texto e cor. Sugestão: verde abaixo de 80%, amarelo a partir de 80%, vermelho ao atingir ou ultrapassar 100%. Dado ausente aparece como indisponível. Verificar o limite exato e a atualização após compactação.
- [ ] [Verificação] Validar a auditoria independente em uma aba real
  ID: cfd2e586-f9a2-413f-b9cc-5598ef64970d
  Resumo:
    A auditoria já existe. Falta observar a sessão nova na pasta do projeto e a entrega do relatório ao líder.
  Origem: pedido-humano
  Execução:
    O run 4d9a065c-b879-4f18-b95e-6f8fbb2e081e integrou d7f5ca1 em 4803b90. Auditoria está disponível no modo de controles completos. docs/verification-audit-2026-11-23.md registra a escolha de modelo, a sessão somente leitura e o relatório com Herdr e Codex simulados. O aceite de ponta a ponta continua pendente.
  Aceite:
    Demonstrar com evidência verificável o resultado já solicitado: abrir uma nova janela no Herdr para uma sessão com contexto limpo, iniciada no diretório do projeto e dedicada à leitura do estado atual.
- [ ] [Verificação] Confirmar a leitura das instruções de TODO por um agente
  ID: 9f4cdfb9-3b30-4d69-a178-aa3ff61301a6
  Resumo:
    A instalação e a verificação de AGENTS.md e CLAUDE.md já existem. Falta o registro da leitura pelo agente do projeto.
  Origem: legado-nao-confirmado
  Execução:
    O run cb0a2492-8455-45ed-ba2b-1b3b39638fdb integrou o trabalho em ae529e2. O comando project-instructions oferece preview, apply com confirmação e check. Conforme docs/project-instructions.md, resta o agente confirmar na conversa a versão lida, como registra pedidos e sugestões e qual evidência exige para concluir.
  Aceite:
    identificar instruções ausentes ou desatualizadas, apresentar a atualização antes de aplicá-la e verificar sua leitura pelo agente; não criar outra lista nem alterar TODOs de outros projetos sem autorização.
- [ ] [Feature] Trazer a tradução já existente para os painéis desta branch
  ID: ba3b21fa-c410-4952-8fe8-222a5bc6f9de
  Resumo:
    A tradução EN/pt-BR e o seletor compartilhado foram entregues no P9 da branch feat/bundled-matt-workflow.
  Origem: legado-nao-confirmado
  Execução:
    Run 7aa353c2-9f6d-4e2f-b038-886a7fd92115, candidato b1b75b3 integrado naquela branch. O guia de lá é docs/interface-languages.md e o fechamento do P9 está em d45b935. Este checkout ainda tem rótulos em inglês e não contém o catálogo do P9. Resta conferir o reaproveitamento nos quatro painéis e o idioma inicial. O P9 inicia em inglês.
  Aceite:
    Demonstrar com evidência verificável o resultado já solicitado: apresentar primeiro os painéis Tarefas, Progresso, Arquivos e Agentes em português para facilitar o uso.

## Bloqueado
- [ ] [Verificação] Dar aceite ao modo Para um agente
  ID: 56b84864-b28d-4a82-b341-84b8d3545e3e
  Resumo:
    O modo econômico já teve execução real com um executor e revisão pelo líder.
  Origem: pedido-humano
  Execução:
    Implementação 98c09e4. Menu, escolha do executor e confirmação verificados em docs/verification/2026-11-18-single-agent-dispatch.md. O run 539166d4-316b-4906-b5ef-5336a50a8717 terminou em modo single, com executor existente. O líder aprovou o candidato 8b93f6e na versão 12 e o integrou em 2f207ad.
  Aceite:
    escolha explícita do modo, revisão pelo líder e evidências verificáveis antes de aceitar a entrega.
  Motivo: O teste com modelo real já ocorreu. Falta o aceite do Vini previsto na tarefa.

## Feito
- [x] 2026-11-26 T16 (#38) Regra do TODO: um item por ticket, criado no /to-tickets
  ID: 1bf9aa52-7c42-413f-81c4-ec054474ed41
  Resumo:
    Regra do TODO: um item por ticket, criado no /to-tickets.
  Origem: pedido-humano
  Referência: docs/pesquisa-regra-do-todo-2026-11-26.md e issue #38 (docs/issues/38-regra-todo-um-item-por-ticket.md)
  Execução:
    Liberado.
    Concluído: docs/agents/todo.md reescrito (um item por ticket, seção Como escrever cada tipo) e modelos docs/templates/agents-todo.md e todo.md; preâmbulo do TODO virou uma linha.
  Aceite:
    `docs/agents/todo.md` diz: um item por ticket com título `Tn (#issue) título`, `Referência:` com a spec e a issue, e dependências em `Execução: Bloqueado por: Tn (#issue).`
    Os tipos `[Bug #n]`, `[Feature]` e `[Verificação]` continuam valendo para o que não é ticket. O prefixo `[Spec #n]` deixa de existir como item.
    `docs/templates/agents-todo.md` e `docs/templates/todo.md` seguem a mesma regra. O preâmbulo do `TODO.md` vira uma linha que aponta para `docs/agents/todo.md`.
    `watchdog todo validate --repo .` passa.
- [x] 2026-11-26 T17 (#39) Gatilho do TODO no docs/agents/issue-tracker.md
  ID: c0e90ca1-adbe-4bfd-ada9-1ab2c131510e
  Resumo:
    Gatilho do TODO no docs/agents/issue-tracker.md.
  Origem: pedido-humano
  Referência: docs/pesquisa-regra-do-todo-2026-11-26.md e issue #39 (docs/issues/39-gatilho-todo-no-issue-tracker.md)
  Execução:
    Bloqueado por: T16 (#38).
    Concluído: Gatilho na seção 'publish to the issue tracker' de docs/agents/issue-tracker.md; modelo em docs/templates/issue-tracker-todo.md; nenhuma skill editada.
  Aceite:
    `docs/agents/issue-tracker.md` deste repositório manda, depois de publicar os tickets, criar ou atualizar o `TODO.md` conforme `docs/agents/todo.md`: um item por ticket, na ordem das dependências.
    Um modelo dessa seção fica em `docs/templates/`, para copiar em projetos preparados para o Watchdog.
    Nenhum arquivo em `~/.agents/skills` é editado.
- [x] 2026-11-26 T18 (#40) Converter as specs #24 e #25 do TODO nos tickets #26, #27 e #28
  ID: 3abbcc32-cb2f-4282-ab9f-8424e89a7327
  Resumo:
    Converter as specs #24 e #25 do TODO nos tickets #26, #27 e #28.
  Origem: pedido-humano
  Referência: docs/pesquisa-regra-do-todo-2026-11-26.md e issue #40 (docs/issues/40-converter-specs-24-25-em-tickets.md)
  Execução:
    Bloqueado por: T16 (#38).
    Concluído: [Spec #25] virou T21 (#26) e T22 (#27, Bloqueado por T21); [Spec #24] virou T23 (#28). classify() confirma T22 esperando T21.
  Aceite:
    `[Spec #25] Trocar a pasta dos painéis` vira os itens dos tickets #26 e #27, com o #27 `Bloqueado por: #26` no formato aceito.
    `[Spec #24] Botões de skill` vira o item do ticket #28.
    Os IDs dos itens antigos não são reaproveitados. `watchdog todo validate --repo .` passa e o Tasks mostra os itens.
- [x] 2026-11-26 T19 (#41) Atualizar o diagrama regra-todo para o gatilho no /to-tickets
  ID: 364c9718-c8fa-4366-86b5-d2a5ff670384
  Resumo:
    Atualizar o diagrama regra-todo para o gatilho no /to-tickets.
  Origem: pedido-humano
  Referência: docs/pesquisa-regra-do-todo-2026-11-26.md e issue #41 (docs/issues/41-diagrama-regra-todo-to-tickets.md)
  Execução:
    Bloqueado por: T16 (#38), T17 (#39).
    Concluído: workflow/archify/regra-todo.html refeito: TODO nasce no /to-tickets pelo issue-tracker.md; finalize do Archify passou nas quatro verificações.
  Aceite:
    O TODO sai de `/to-spec` e passa a nascer em `/to-tickets`, pelo gatilho em `docs/agents/issue-tracker.md`.
    O diagrama mostra `docs/agents/todo.md` como regra, os modelos em `docs/templates` e o global só com o git-todo e a linha de ponteiro.
    O `finalize` do Archify passa em todas as verificações.
- [x] 2026-11-26 [Feature] Regra do TODO por projeto em docs/agents/todo.md
  ID: 8492d3f9-f93b-4f10-a327-2ad23727b08d
  Resumo:
    Tipos, formato watchdog_todo, quem cria o TODO em cada etapa (grill, to-spec, to-tickets) e arquivos obrigatórios passam a viver no projeto; o global ficou só com o git-todo e uma linha que aponta para docs/agents/todo.md.
  Origem: pedido-humano
  Referência: docs/agents/todo.md; modelos docs/templates/agents-todo.md e docs/templates/todo.md; diagrama workflow/archify/regra-todo.html
  Execução:
    Globais conferidos por diff (cópias em .watchdog/run/2026-11-26/globais-antes/). oracle, left-undone-herdr e omarchy-bar-groups não têm docs/agents/todo.md e seguem só o git-todo.
  Aceite:
    Projeto sem docs/agents/todo.md segue a regra git-todo de antes; este projeto segue docs/agents/todo.md.
- [x] 2026-11-26 T14 (#15) Aceite manual
  ID: 82e42465-81ee-4d70-9f7b-72f856cf71b9
  Resumo:
    o Vini testa /clear no Claude e no Codex, handoff Claude e Codex, uma rodada real A/B/C e o code review com as abas.
  Origem: pedido-humano
  Referência: spec #1 e issue #15 (docs/issues/)
  Execução:
    Aceite humano iniciado. As 13 dependências técnicas da #15 estão fechadas. A revisão R1 abriu dois revisores na aba Code Review e a correção na aba seguinte (R1-Correcao-fechamento.md).
    No Codex, o /clear deixou a sessão antiga no painel. A recuperação manual por CLI foi registrada às 17h15. Às 18h43 o Religar pela skill confirmou a nova conversa no mesmo pane. Conferidos os 15 integrantes na mesma ordem, base, modos e meta. O Progress mostra 14 de 15; no histórico da conversa de destino só entraram a invocação e a definição da skill durante a tentativa. Evidências em .watchdog/run/2026-11-25/T14-retomada-aceite-real.json.
    Próxima etapa com Vini: em uma sessão de aceite do Claude vinculada ao Tasks, observar o painel antes e depois de /clear. Ainda faltam a troca Claude ↔ Codex pelos dois prefixos e a rodada real A/B/C. O resultado negativo do acompanhamento automático no Codex continua registrado.
    Preparação em 26/11: estado da aba e do grupo guardado em .watchdog/run/2026-11-26/T14-antes-de-vincular-Claude-163725.json.
    Aceite em 26/11 no projeto descartável test-watchdog-erase (w14): /clear no Claude manteve o painel e seguiu sozinho de 293f2207 para 15dbea79; rodada A/B/C terminou 3 de 3 (T1 ed1c5b7, T2 7a4e29b, T3 353c810, 12 testes OK) com T2 esperando T1 e T3 aguardando a decisão do Vini. Direções Claude ↔ Codex confirmadas pelo Vini. Achados viraram as issues #29 a #35. Evidências em .watchdog/run/2026-11-26/T14-w14-*.json.
  Aceite:
    /clear no Claude e no Codex mantém o painel. Handoff Claude para Codex com Religar mostra $; Codex para Claude volta a /. Rodada real com A livre, B dependente de A e C dependente do Vini termina com o aviso certo. O code review abre as duas abas e a correção em aba nova.

- [x] Validar as sugestões do curador
  ID: a7b83b35-b133-451a-bbd7-85c7477bd849
  Resumo:
    Avaliar propostas reais de conclusão e bloqueio, mantendo a confirmação do usuário.
  Origem: legado-nao-confirmado
  Execução:
    Em 25/11, conferidas as duas citações da revisão 5577d0ee6db9 no turno Codex 01a1efe4-3d4a-7970-afc1-ca91953fac92. O curador propôs concluir e bloquear a mesma tarefa. Ao reavaliar a resposta completa, o validador reteve ambas. Na revisão 2b1131967a14, turno 01a20909-cf6, também reteve um bloqueio com contexto contraditório. Nenhuma proposta foi aplicada. Os 36 testes de curadoria passaram, incluindo confirmação e revalidação.
  Aceite:
    Demonstrar com evidência verificável o resultado já solicitado: avaliar propostas de conclusão e bloqueio em conversas reais, mantendo obrigatória a confirmação do usuário.
- [x] Registrar pedidos durante a conversa
  ID: 4f9fae9f-54e0-49c4-9700-8f2e90929246
  Resumo:
    manter os pedidos claros do usuário no arquivo do projeto enquanto a conversa acontece, sem esperar um commit.
  Origem: legado-nao-confirmado
  Execução:
    Resumo: manter os pedidos claros do usuário no arquivo do projeto enquanto a conversa acontece, sem esperar um commit.
    O líder registra os pedidos claros antes de commit; ideias dos agentes ficam identificadas separadamente como sugestões, sem virarem pedidos aprovados automaticamente.
    Ler o mesmo TODO.md, sem uma segunda lista de tarefas; detectar alterações e conflitos antes de aplicar atualizações. Regras gerais pertencem ao AGENTS.md e instruções específicas ficam na tarefa.
    Aceite: líder e painel compartilham a mesma fonte, com conflitos visíveis e sugestões distinguíveis de pedidos.
    Verificação: O pedido Trocar pasta foi registrado durante a conversa como pedido-humano no TODO lido pelo Tasks. tests/test_todo_format.py cobre sugestao-agente e recusa de edição obsoleta.
  Aceite:
    líder e painel compartilham a mesma fonte, com conflitos visíveis e sugestões distinguíveis de pedidos.
- [x] Ler planos do projeto
  ID: e3d9935a-b4c3-4256-b3a5-f0fa08dffe24
  Resumo:
    transformar um plano explícito do projeto em instruções delimitadas para as tarefas, sem reler o histórico inteiro das conversas.
  Origem: legado-nao-confirmado
  Execução:
    Resumo: transformar um plano explícito do projeto em instruções delimitadas para as tarefas, sem reler o histórico inteiro das conversas.
    Verificação: docs/project-plans.md e tests/test_project_plans.py. O leitor gera contratos a partir do plano explícito e verifica IDs, escopo e mudanças de conteúdo.
  Aceite:
    Demonstrar com evidência verificável o resultado já solicitado: transformar um plano explícito do projeto em instruções delimitadas para as tarefas, sem reler o histórico inteiro das conversas.
- [x] Descobrir arquivos criados pela IA
  ID: bad09fc3-a213-4fa6-9877-a33a7cf65aa4
  Resumo:
    descobrir e resumir automaticamente arquivos criados ou alterados pela IA, preservando o vínculo funcional com Yazi.
  Origem: legado-nao-confirmado
  Execução:
    Resumo: descobrir e resumir automaticamente arquivos criados ou alterados pela IA, preservando o vínculo funcional com Yazi.
    Verificação: docs/artifact-discovery.md, tests/test_artifacts.py e tests/test_artifacts_yazi.py. Conferidas a descoberta por conversa e a abertura do arquivo no Yazi por teclado e mouse.
  Aceite:
    Demonstrar com evidência verificável o resultado já solicitado: descobrir e resumir automaticamente arquivos criados ou alterados pela IA, preservando o vínculo funcional com Yazi.
- [x] Preservar o progresso do projeto
  ID: 7b33fb64-2f30-4140-b9bb-e09d5095011b
  Resumo:
    manter um histórico durável de conclusões para acompanhar o progresso entre edições do TODO.
  Origem: legado-nao-confirmado
  Execução:
    Resumo: manter um histórico durável de conclusões para acompanhar o progresso entre edições do TODO.
    Verificação: docs/project-progress-history.md e tests/test_project_history.py. O histórico registra transições por UUID e recupera gravações interrompidas.
  Aceite:
    Demonstrar com evidência verificável o resultado já solicitado: manter um histórico durável de conclusões para acompanhar o progresso entre edições do TODO.
- [x] Testar uma execução real completa
  ID: b6cb93d7-46ca-4f00-8d4d-ce3ac0dce6fe
  Resumo:
    confirmar uma tarefa real no novo fluxo Orchestrate e acompanhar seu progresso de ponta a ponta.
  Origem: legado-nao-confirmado
  Execução:
    Resumo: confirmar uma tarefa real no novo fluxo Orchestrate e acompanhar seu progresso de ponta a ponta.
    Verificar em Progresso as etapas Preparando → Executando → Verificando → Aguardando aprovação.
    Verificação: Run cb0a2492-8455-45ed-ba2b-1b3b39638fdb. O verificador encontrou as quatro etapas em ordem, com QA do candidato ae529e2 e integração confirmada.
  Aceite:
    Demonstrar com evidência verificável o resultado já solicitado: confirmar uma tarefa real no novo fluxo Orchestrate e acompanhar seu progresso de ponta a ponta.
- [x] 2026-11-25 T15 (#16) Fila travada no pane do líder
  ID: 184d02f0-64ad-48c1-9af4-c75d8fd5d1d2
  Resumo:
    Detectar dois minutos sem progresso, preservar a entrega e avisar o líder pelo pane.
  Origem: pedido-humano
  Referência: Spec #1 e issue #16 (docs/issues/16-t15-fila-travada.md).
  Execução:
    Implementar em worktree própria na integração após a correção da revisão R1.
  Aceite:
    Aviso único, cópia preservada, fila retomada e estado visível no Tasks. Ver critérios e seção aprovada na issue.
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
