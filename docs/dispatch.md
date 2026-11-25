# Padrão do dispatch do Watchdog

Ao receber uma meta ou atualização do grupo do Watchdog, leia este padrão,
o `AGENTS.md` do projeto (seção `## Dispatch`) e o `GLOSSARY.md`.
O grupo é o limite do trabalho: siga apenas as tarefas despachadas, cada uma
com seu ponteiro de aceite (issue e spec, ou seção de plano).
O painel entrega a seleção; o líder coordena a execução.

## Preparar e abrir uma leva

1. Leia os aceites e suas dependências. Abra somente tarefas liberadas.
   A base da revisão é a ponta da branch de integração anotada pelo Watchdog
   no primeiro despacho confirmado; preserve-a ao somar tarefas ao grupo.
2. Abra um Codex novo por tarefa no Herdr, em branch e worktree persistentes
   próprias, criadas a partir da branch de integração. Use `.worktrees/<ticket>`
   dentro do checkout de integração. Modelo e esforço vêm do projeto.
3. Agrupe os executores abertos juntos numa aba nomeada pelo tema e tarefas.
   Tarefas liberadas depois entram na aba da leva de que dependiam enquanto
   houver espaço. Descubra o pane próprio antes de entregar o contrato.
4. Guarde contratos e relatórios em `.watchdog/run/<data>/`, ignorada pelo git.
   O contrato usa ponteiros, sem copiar a conversa do líder: ticket, spec ou plano,
   glossário, worktree, branch, pane próprio e pane do líder. Inclua o rodapé abaixo.

## Rodapé comum do contrato

- Leia `AGENTS.md`, sua seção Dispatch e `GLOSSARY.md` antes de trabalhar.
- Trabalhe apenas na sua worktree e branch, com commit local por marco verificado.
  Push, deploy e merge para a branch principal dependem da decisão do Vini.
- A aprovação da tarefa já cobre repasse de entendimento, brainstorm e plano:
  siga direto; pare apenas se o aceite não decidir algo ou se contradisser.
- Faça TDD pelo comportamento observável nos pontos A e B aplicáveis da spec.
  Testes que fixam comportamento citam a linha da spec que o exige.
  Use dublês e recursos isolados; preserve os serviços e painéis em execução.
- Antes do último commit, incorpore a branch de integração na própria branch e
  rode os testes definidos no Dispatch do projeto. Confira o `git status`.
- Preserve `TODO.md`, `HANDOFF*`, issues, Left Undone e painéis Watchdog em execução;
  o líder revisa, integra e atualiza o acompanhamento.
- Avise o líder pelo pane indicado no contrato, uma mensagem por evento:
  `[Tn · painel <pane próprio>] Tn pronto: commit <sha>, testes <resultado>. <resumo>`.
  Para dúvida não decidida pela spec, envie `BLOQUEIO: <dúvida>` e espere resposta.
  Use o comando de aviso do kit com trava por pane quando disponível. Toda entrega
  ao líder deve manter a trava desde o texto até o Enter. Até a integração do kit,
  use `herdr pane send-text <pane do líder> '<mensagem>'` seguido de
  `herdr pane send-keys <pane do líder> Enter`, conforme o contrato.

## Acompanhar e integrar

1. Confira cada executor novo aos 2, 3 e 4 minutos e redirecione cedo se necessário.
   Depois aguarde o aviso, com uma espera em segundo plano como rede de segurança,
   sem polling. O executor deve avisar; ler seu pane não substitui o aviso.
2. A cada aviso, confira todos os critérios de aceite, a costura com o que entrou
   na integração e a referência de spec dos testes novos. Rode os testes exigidos
   no checkout de integração. Só aceite com commit e evidência verificáveis.
3. Integre exclusivamente no checkout de integração. O líder implementa em
   worktrees, inclusive no modo Implementar aqui. Após integrar, feche a issue com
   comentário de evidências, atualize a cópia local e o TODO, faça commit local e
   escreva na conversa `Tn concluído: commit, testes`. Reavalie as tarefas liberadas.
4. Responda sozinho a bloqueios decididos pela spec. Se ela não decidir, pergunte
   imediatamente ao Vini sem parar as outras tarefas; registre o próximo passo.
5. Ao encerrar, avise o Vini na conversa: concluídos com commit e testes;
   bloqueados com motivo e próximo passo. Não espere que ele volte e pergunte.

## Revisão e saída da máquina

Quando o Vini pedir code review, abra a aba `Code Review` com dois revisores
novos, Standards e Spec, sobre o mesmo intervalo da base anotada à integração.
Cada revisor só lê, salva relatório e avisa. Espere ambos antes de apresentar os
relatórios lado a lado, com contagem e pior achado. Correção só após o ok do Vini,
num executor novo e numa aba nova. Depois seguem `/retro` e o teste do Vini.
O Vini decide merge danger e push; integrar uma tarefa localmente não autoriza
levar a branch para fora da máquina.

## Configuração do projeto

Use [o modelo de Dispatch](templates/dispatch-agents.md) para registrar limites,
testes, branch de integração, modelo e esforço no `AGENTS.md` do projeto.
Mantenha a linha `Branch de integração: \`nome-da-branch\`` nesse formato: o
Watchdog a lê para anotar a base, mesmo quando o líder está em outra branch.
Sem configuração, usa a branch local atual; confira-a antes do despacho.
