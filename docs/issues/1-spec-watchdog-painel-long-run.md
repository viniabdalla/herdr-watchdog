---
number: 1
title: "Spec: Watchdog como painel de comando do long run (despacho, grupo, agentes e skills de Matt)"
state: open
labels: [ready-for-agent]
url: https://github.com/viniabdalla/herdr-watchdog/issues/1
blocked_by: []
updated: 2026-11-25
---

## Problem Statement

O Vini conduz projetos com uma sessão **líder** (Claude Code ou Codex) que abre **executores** Codex visíveis no Herdr, um por tarefa, espera os avisos deles, integra o trabalho numa **branch de integração** e no fim pede um code review em dois eixos. Num projeto real esse jeito funcionou muito bem: ele marcava as tarefas, o líder levava a **meta** até o fim de madrugada, e no dia seguinte vinham code review, correção, `/retro` e o teste dele.

Mas tudo dependeu de coisas que não se repetem sozinhas:

- As regras de execução estavam espalhadas num handoff do projeto, em mensagens digitadas turno a turno e no AGENTS.md. Um líder novo não sabe nada disso.
- O líder inventou um kit próprio (abrir worktree e Codex, rodapé comum do contrato, fechar issue) numa pasta privada do projeto, fora do git. Na próxima vez ele é refeito do zero.
- O Watchdog Tasks só sabe marcar tarefas, gravar um grupo fixo à mão e mandar um pedido de verificação. Não monta a meta, não soma tarefas novas a uma meta em andamento e não mostra o que cada executor está fazendo.
- Duas mensagens digitadas ao mesmo tempo no pane do líder já se misturaram numa só (um aviso de executor colou no fim da meta).
- O Vini só soube que a madrugada terminou porque voltou e perguntou "terminou tudo?".
- Ele troca muito de líder: `/clear` no mesmo pane para manter o contexto pequeno, ou handoff de Claude para Codex. Hoje o vínculo do painel quebra no `/clear` e os botões não sabem qual harness está do outro lado.
- Os passos do workflow de Matt Pocock (`/to-spec`, `/to-tickets`, `/code-review`, `/retro`) não podem ser chamados pelo modelo; o Vini precisa digitá-los, e com prefixo diferente em cada harness.

## Solution

O Watchdog passa a ser o painel de comando desse fluxo, sem virar orquestrador. O Vini continua escolhendo e o líder continua coordenando.

- No Tasks, o Vini marca tarefas (a **seleção**) e escolhe **Despachar** (um executor novo por tarefa) ou **Implementar aqui** (o próprio líder faz). A prévia mostra o texto exato e o destino; ao confirmar, o Tasks digita no pane do líder e dá Enter, como se fosse o Vini.
- O primeiro **despacho** manda uma **meta** curta que aponta para o **grupo** do Watchdog. Despachos seguintes só somam tarefas ao grupo e avisam "Grupo atualizado: +…", sem trocar a meta.
- As regras ficam em três camadas: um padrão do Watchdog (como despachar, avisar, esperar, revisar, integrar), um ponteiro de aceite por tarefa (issue, spec ou plano, conforme o workflow) e uma seção Dispatch no AGENTS.md do projeto (o que nunca tocar, testes, branch de integração, modelo e esforço).
- O Watchdog traz o kit que funcionou: abrir executor em worktree e aba da leva, rodapé comum do contrato com aviso e trava, fechar issue com cópia local.
- O Progress mede o grupo, o TODO inteiro e mostra a seção AGENTES sempre visível (estado, contexto ao vivo e o que cada um faz), com faixa de pergunta pendente e de meta encerrada, mais notificação no desktop.
- Uma faixa com as skills de Matt instaladas digita o comando com `/` no Claude e `$` no Codex. Inclui uma skill nova, `merge-danger`, para avaliar porta e raio antes de a integração sair da máquina.
- O vínculo segue o líder no `/clear` do mesmo pane, detecta troca de harness e oferece **Religar** para outro pane.

## User Stories

### Seleção, despacho e grupo

1. Como Vini, quero marcar tarefas no Tasks e despachá-las ao líder com uma tecla, para não redigitar a lista.
2. Como Vini, quero ver na prévia o texto exato que será digitado e o pane de destino, para confirmar antes de enviar.
3. Como Vini, quero escolher entre Despachar e Implementar aqui a cada envio, para decidir quando vale abrir executores.
4. Como Vini, quero que o despacho some as tarefas ao grupo do Progress, para medir exatamente o que o líder recebeu.
5. Como Vini, quero que um segundo despacho com a meta ativa some ao grupo (3 + 3 = 6) em vez de substituí-lo, para acompanhar tudo junto.
6. Como Vini, quero que uma tarefa já no grupo não conte duas vezes quando eu a marcar de novo, para o percentual não mentir.
7. Como Vini, quero que o grupo zere sozinho no próximo despacho quando tudo nele estiver concluído, para recomeçar a medição sem perder o "3 de 3" antes da hora.
8. Como Vini, quero zerar o grupo à mão no Progress, para recomeçar quando eu quiser.
9. Como Vini, quero que o primeiro despacho mande uma meta curta que aponte para o grupo, para que tarefas somadas depois entrem na mesma meta.
10. Como Vini, quero que despachos com meta ativa mandem só "Grupo atualizado: +D, +E, +F", para não trocar a condição da meta.
11. Como Vini, quero ser avisado na prévia quando nenhuma tarefa da seleção puder começar, com as opções incluir a dependência, cancelar ou mandar assim mesmo, para não gastar uma volta do líder.
12. Como Vini, quero que o líder nunca pegue tarefa que eu não marquei, para que a seleção seja o limite do trabalho.
13. Como Vini, quero que a meta funcione igual no Claude e no Codex, porque os dois têm meta nativa por sessão.
14. Como Vini, quero que num harness sem meta nativa a mesma frase vá como mensagem comum, para não travar o fluxo.

### Entrega ao líder

15. Como Vini, quero que o Tasks digite no pane do líder e dê Enter, igual para Claude e Codex, para usar a fila normal de cada harness.
16. Como Vini, quero que avisos de executores e textos do Tasks nunca se misturem no pane do líder, para não repetir a meta colada com um aviso.
17. Como executor, quero um comando de aviso que já respeite a trava do pane, para não precisar saber como ela funciona.

### Regras do dispatch

18. Como líder, quero ler um padrão único do Watchdog sobre como despachar, para agir igual em qualquer projeto.
19. Como líder, quero ler na seção Dispatch do AGENTS.md o que nunca tocar, o comando de teste, a branch de integração e o modelo e esforço dos executores, para respeitar o projeto.
20. Como líder, quero que a meta cite os dois arquivos pelo nome, para lê-los mesmo quando o harness não carrega o AGENTS.md sozinho.
21. Como Vini, quero ser avisado na prévia quando o projeto não tiver a seção Dispatch ou o CLAUDE.md com import do AGENTS.md, para corrigir antes.
22. Como líder, quero apontar cada tarefa para sua fonte de aceite (issue e spec, ou seção de um plano), para que o dispatch sirva a qualquer workflow.

### Executores e acompanhamento

23. Como líder, quero abrir um executor novo por tarefa, numa worktree e branch próprias a partir da integração, para isolar o trabalho.
24. Como líder, quero agrupar os executores abertos juntos numa aba nomeada pelo tema e pelas tarefas, para o Vini ver as levas na tela.
25. Como líder, quero que tarefas liberadas depois entrem na aba da leva de que dependiam, enquanto houver espaço.
26. Como líder, quero olhar cada executor novo aos 2, 3 e 4 minutos e redirecionar se ele estiver no rumo errado, porque muitos erros aparecem no começo.
27. Como líder, quero depois disso só esperar o aviso, com uma espera em segundo plano como rede, para não gastar tokens.
28. Como executor, quero um contrato com ponteiros (tarefa, aceite, worktree, regras, testes, aviso), para começar sem ler a conversa do líder.
29. Como executor, quero que o contrato diga que a aprovação da tarefa já cobre o "repasse o entendimento e espere ok" do projeto, para não parar à toa.
30. Como executor, quero fazer merge da integração na minha branch e rodar os testes antes do último commit, para entregar algo que junta limpo.
31. Como executor, quero avisar "pronto" com commit e testes, ou "BLOQUEIO" com a dúvida, uma mensagem por evento.
32. Como líder, quero a cada aviso conferir os critérios da tarefa, as costuras com o que já foi integrado e se um teste novo que congela comportamento cita a linha da spec, antes de integrar.
33. Como líder, quero integrar na branch de integração, fechar a issue com a cópia local e escrever "Tn concluído: commit, testes", para o curador e o Progress acompanharem.
34. Como líder, quero reavaliar o que ficou livre a cada conclusão e abrir os próximos executores.
35. Como líder, quero responder sozinho um bloqueio que a spec decide.
36. Como Vini, quero que um bloqueio que a spec não decide chegue a mim na hora, sem parar as outras tarefas, e vá para o aviso final se eu não responder.
37. Como líder, quero integrar só no checkout principal e trabalhar sempre em worktrees, para não misturar trabalho com integração.
38. Como líder, no modo Implementar aqui, quero abrir minha própria worktree e fazer merge na integração como faria com um executor, para manter um único fluxo de git.

### Progress, AGENTES e avisos

39. Como Vini, quero ver no Progress a barra do grupo e a do TODO inteiro.
40. Como Vini, quero uma seção AGENTES sempre visível, sem botão, com uma linha por líder e executor: pane, estado, contexto usado e o que está fazendo.
41. Como Vini, quero ver o contexto ao vivo de cada agente, para saber quando é hora de limpar a sessão.
42. Como Vini, quero ver na linha de cada executor a checagem inicial em andamento (1/3, 2/3, 3/3).
43. Como Vini, quero ver as tarefas do grupo que esperam outra ou que dependem de mim.
44. Como Vini, quero uma faixa "pergunta de X aguarda você" e uma notificação no desktop quando chegar um bloqueio para mim.
45. Como Vini, quero uma faixa fixa "Meta encerrada · 2 de 3 · C depende de você" e uma notificação no desktop no fim, para saber sem voltar ao pane do líder.
46. Como Vini, quero que o aviso final do líder liste o concluído com evidência e o bloqueado com motivo e próximo passo.

### Code review, correção e merge danger

47. Como Vini, quero uma faixa com as skills de Matt instaladas (grill-with-docs, to-spec, to-tickets, code-review, retro, merge-danger), para disparar cada passo com um clique.
48. Como Vini, quero que cada botão digite `/skill` no Claude e `$skill` no Codex, para funcionar nos dois.
49. Como Vini, quero ver só os botões das skills que o harness do líder enxerga.
50. Como Vini, quero editar o texto na prévia antes do Enter.
51. Como Vini, quero que o to-tickets venha com a spec preenchida quando o painel a encontrar.
52. Como Vini, quero que a prévia do to-spec e do to-tickets avise quando o tracker do projeto não guarda cópia local das issues.
53. Como Vini, quero que o code-review venha com a base anotada no primeiro despacho do grupo e a branch de integração, para revisar só a rodada.
54. Como líder, quero rodar o code review numa aba "Code Review" com dois revisores novos e visíveis, Standards e Spec, com o mesmo intervalo de commits.
55. Como revisor, quero um contrato-modelo do meu eixo (fontes, foco, pistas, exclusões, só leitura, relatório curto, aviso), para revisar sem contexto do líder.
56. Como líder, quero segurar a apresentação até os dois avisos e mostrar os relatórios lado a lado, com contagem e pior achado.
57. Como Vini, quero que a correção só comece com meu ok, num único executor novo, numa aba nova só dele.
58. Como Vini, quero seguir depois para `/retro` e meu teste.
59. Como Vini, quero apertar merge-danger sobre a integração no dia seguinte e receber porta (dupla ou única) e raio de cada parte, para decidir o que testar antes de levar a integração para fora da máquina.
60. Como Vini, quero que relatórios e arquivos do kit fiquem dentro do projeto, numa pasta padrão ignorada pelo git.

### Vínculo e harness

61. Como Vini, quero que após `/clear` no mesmo pane e no mesmo harness o vínculo siga a sessão nova sem aviso, porque limpo o contexto com frequência.
62. Como Vini, quero que, quando o harness do líder mudar, os botões troquem de prefixo e apareça um aviso curto.
63. Como Vini, quero uma tecla Religar no Tasks que liste os panes com agente do workspace, para ligar o painel ao novo líder com um toque.
64. Como Vini, quero continuar podendo pedir ao novo líder, em texto, que se ligue ao Watchdog.
65. Como Vini, quero reenviar a meta do grupo com um toque depois de um `/clear`, porque a meta nativa morre com a sessão.

### Nomes no Tasks

66. Como Vini, quero que a revisão das propostas do curador se chame Review Curator, para não confundir com code review.
67. Como Vini, quero que a pergunta "isto está mesmo pronto?" ao líder se chame Verify Leader.
68. Como Vini, quero que a ação antiga de gravar o grupo à mão saia, porque o despacho já cuida do grupo.

## Implementation Decisions

- **Painel, não orquestrador.** O Watchdog lê o TODO, monta a seleção, digita comandos curtos e mostra o progresso. Todo o "como trabalhar" fica em texto lido pelo líder.
- **Três camadas de regra.** Camada 1: um documento-padrão do dispatch que vem com o Watchdog. Camada 2: ponteiro de aceite por tarefa, vindo do workflow. Camada 3: seção `## Dispatch` no AGENTS.md do projeto. A meta cita a camada 1 e a 3 pelo nome.
- **Conteúdo da camada 1**: executor novo por tarefa em worktree e branch próprias; abas por leva; checagem inicial aos 2, 3 e 4 minutos; rodapé comum do contrato (aprovação cobre o repasse de entendimento, merge da integração e testes antes do último commit, aviso pronto/BLOQUEIO com trava); espera sem polling com rede em segundo plano; checagem de spec a cada aviso; integração só no checkout principal; pergunta imediata sem travar o resto; aviso final; revisão em dois eixos; correção em aba nova após ok.
- **Kit do líder** vem com o Watchdog: abrir executor (worktree, aba da leva, harness, prompt com o próprio pane), rodapé comum, enviar aviso com trava por pane, fechar issue e atualizar a cópia local. Modelo e esforço vêm da camada 3.
- **Trava por pane**: toda escrita no pane do líder, do Tasks ou de executores, escreve, dá Enter e só então libera.
- **Meta aponta para o grupo.** Primeiro despacho: meta curta. Com meta ativa: só "Grupo atualizado". Implementar aqui troca "Concluir" por "Implementar nesta sessão".
- **Grupo** passa a ser alimentado pelo despacho, soma e deduplica, zera quando tudo está concluído e chega um novo despacho, ou à mão. No primeiro despacho de um grupo, anota a ponta da branch de integração como base do code review.
- **Prévia de despacho** classifica a seleção pelo que o TODO já diz (livre, espera outra da seleção, espera fora da seleção, depende do Vini) e bloqueia o envio quando nada pode começar, com as três opções.
- **Seção AGENTES no Progress** reaproveita o monitor de agentes e o medidor de contexto já portados para o Watchdog; sem botão, sempre visível; faixa de pergunta e de fim; notificação no desktop.
- **Faixa de skills**: detectada pelas pastas de skills que o harness do líder lê; prefixo `/` no Claude e `$` no Codex; harness detectado pelo agente que o Herdr informa no pane ligado; prévia editável.
- **Skill `merge-danger`** nova, chamada só pelo botão: classifica porta e raio usando a definição da skill de PR de Matt e a lista de "sempre mão única" da camada 3; devolve integra/integra e revisar/não integra e perguntar por parte.
- **Vínculo**: segue sessão nova no mesmo pane e mesmo harness; troca de harness atualiza botões e avisa; Religar lista os panes com agente do workspace.
- **Arquivos de execução** (contratos, relatórios de revisão, comentários de fechamento) numa pasta padrão do projeto, ignorada pelo git.
- **Nomes**: Review Curator, Verify Leader; a ação de gravar grupo à mão sai.
- **Layout padrão** do projeto acompanhado: conversa à esquerda, Tasks e Progress à direita, Artifacts e arquivos embaixo.

## Testing Decisions

**O que é um bom teste.** Testar o comportamento visível nas fronteiras: teclas no painel, texto que seria digitado no pane do líder, grupo e estado gravados, comandos enviados ao Herdr. Nunca detalhes internos. Cada cenário é entrada (tecla, aviso, troca de sessão) e efeito observável.

**Ponto de teste A: o painel num terminal real com o líder falso.** Tasks e Progress rodam num pseudo-terminal; vínculo e entrega trocados por um falso que grava o texto digitado, o harness e o estado da sessão; TODO e estado em pasta temporária. Cenários obrigatórios:
- despachar A, B, C sem meta grava a meta curta e o grupo fica 0/3;
- despachar D, E, F com meta ativa grava só "Grupo atualizado: +D, +E, +F" e o grupo fica 0/6;
- marcar de novo uma tarefa do grupo não aumenta o total;
- grupo todo concluído e novo despacho recomeça em 0/n; grupo com tarefa aberta soma;
- zerar à mão esvazia o grupo;
- seleção sem nenhuma tarefa livre mostra o aviso e não envia;
- Implementar aqui gera o texto de implementar nesta sessão;
- prévia avisa projeto sem seção Dispatch e sem import no CLAUDE.md;
- líder Claude mostra `/to-spec`, líder Codex mostra `$to-spec`, skill ausente não aparece;
- code-review sai com a base anotada no primeiro despacho e a branch de integração;
- `/clear` no mesmo pane e harness mantém o vínculo sem aviso;
- troca de harness troca os prefixos e mostra o aviso; Religar liga ao pane escolhido;
- aviso de pergunta mostra a faixa e chama a notificação; meta encerrada mostra a faixa fixa;
- seção AGENTES mostra estado, contexto e checagem inicial de cada executor;
- Review Curator e Verify Leader com os nomes novos; a ação de gravar grupo à mão não existe.

Prior art: os testes do Tasks em terminal com runtime falso, os de monitor de agentes, de progresso e de long run.

**Ponto de teste B: o kit contra um Herdr falso.** Os comandos do kit rodam contra um binário Herdr falso e um repo git temporário. Cenários obrigatórios:
- abrir executor cria worktree e branch a partir da integração e o pane na aba da leva;
- dois avisos simultâneos chegam como duas mensagens inteiras;
- um texto do Tasks e um aviso simultâneos não se misturam;
- fechar issue atualiza a cópia local com estado e comentário.

Prior art: os testes de transporte e de missão com Herdr falso.

**Aceite manual (depois dos testes):** `/clear` no Claude e no Codex mantém o vínculo; handoff Claude → Codex com Religar mostra `$`; Codex → Claude volta a `/`; uma rodada real A livre, B depende de A, C depende do Vini termina com o aviso certo; o code review abre as duas abas e a correção em aba nova.

## Out of Scope

- O Watchdog não chama `/implement` nem `/implement-spec`; Despachar e Implementar aqui ocupam esse papel.
- Merge danger durante a meta: o merge de tarefa na integração é porta dupla; o botão é usado depois da implementação.
- Revisor de spec por merge com agente extra.
- Mudar o Left Undone; só a parte visual do monitor já foi portada.
- O hook de TODO que dá falso positivo com arquivos sujos de outra sessão.
- Push, deploy e merge para a branch principal, que continuam decisão do Vini.
- Detectar handoff para outro pane sozinho, sem Religar.

## Further Notes

- O material de origem (prompts reais, contratos dos executores, fluxograma) está na pasta de workflow desta branch e no glossário do repo.
- O vínculo atual exige a mesma sessão viva; por isso o `/clear` hoje quebra o painel.
- O mockup aprovado da seção AGENTES está junto do material de workflow.
- Depois desta spec, o próprio Watchdog pode acompanhar a implementação dela: os tickets entram no TODO e aparecem no Tasks.
