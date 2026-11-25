# Padrão do dispatch do Watchdog

Ao receber uma meta ou atualização do grupo do Watchdog, leia este padrão,
o `AGENTS.md` do projeto (seção `## Dispatch`) e o `GLOSSARY.md`.
O grupo é o limite do trabalho: siga apenas as tarefas despachadas, cada uma
com seu ponteiro de aceite (issue e spec, ou seção de plano).
O painel entrega a seleção; o líder coordena a execução.

## Implementar aqui

O Tasks oferece Despachar (p) e Implementar aqui (h), com o modo escolhido,
o texto exato e o pane do líder na prévia. Cancelar não envia nem soma ao grupo.
Ambos usam o mesmo grupo e os mesmos ponteiros de aceite; a escolha vale para
as tarefas novas do envio atual. O JSON do grupo contém `members` (identidades)
e `modes` (modo por identidade): `dispatch` pede executor, `here` pede Implementar
aqui. Antes de trabalhar e a cada "Grupo atualizado", leia esse mapa, mesmo que
a meta original tenha pedido executores. Uma tarefa já no grupo mantém seu modo;
a seleção repetida não troca a escolha anterior. Grupos antigos sem modo para
uma identidade usam Despachar. Recomeçar o grupo ou zerá-lo descarta os modos
anteriores. Em Implementar aqui, o próprio líder implementa nesta sessão,
abrindo sua worktree e branch próprias a partir da branch de integração.
Confere o aceite e os testes, incorpora a integração antes do último commit
e integra exclusivamente no checkout de integração, como faria com a entrega
de um executor. Ao concluir, fecha a issue com evidências e atualiza a cópia
local e o acompanhamento, escrevendo "Tn concluído: commit, testes" na conversa.

## Preparar e abrir uma leva

1. Leia os aceites e suas dependências. Abra somente tarefas liberadas.
   A base da revisão é a ponta da branch de integração anotada pelo Watchdog
   no primeiro despacho confirmado; preserve-a ao somar tarefas ao grupo.
2. Use `watchdog kit abrir` (CLI abaixo) para abrir um Codex novo por tarefa
   no Herdr, em branch e worktree persistentes
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
  Use `watchdog aviso` conforme a CLI abaixo; ela mantém a trava por pane desde
  o texto até a confirmação de consumo do rascunho. Inclua o caminho absoluto do Watchdog no contrato para
  funcionar também na worktree do executor.

### CLI de aviso (kit T6, usada por T7/T8)

```bash
/caminho/do/watchdog aviso --lider w11:p8 --pane w11:pE --ticket T6 pronto --commit abc1234 --testes '12 testes OK' --resumo 'Trava por pane pronta'
/caminho/do/watchdog aviso --lider w11:p8 --pane w11:pE --ticket T6 BLOQUEIO --duvida 'Qual critério decide este caso?'
```

Substitua pane do líder, pane próprio e ticket pelos valores do contrato. O
comando escreve uma mensagem inteira, espera sua materialização no compositor,
dá Enter e confirma que ela foi consumida. `pronto` exige commit, testes e resumo;
`BLOQUEIO` exige dúvida. Para uma sessão Herdr explícita, acrescente
`--session <nome>` antes do evento. Saída zero confirma o consumo, e não apenas
o sucesso dos comandos do Herdr.

Um rascunho existente é preservado: a entrega aguarda o compositor ficar vazio.
Após 30 segundos, saída 2 significa aviso guardado e espera em segundo plano;
o executante não precisa reenviar. O caminho do registro e o PID da espera
aparecem na resposta. Uma segunda entrega fica guardada atrás da primeira.
A espera continua somente para o mesmo pane, terminal, harness e sessão nativa.
Uma troca de identidade ou edição do rascunho depois do paste suspende a entrega
com estado `uncertain`, sem apagar nem colar outra cópia.

O Enter ocorre somente após observar o texto próprio inteiro no compositor.
Se ele não for consumido e continuar exatamente igual em leituras sucessivas,
a entrega pode usar um segundo Enter. Para um aviso simples do Codex ocupado,
essa segunda tecla é Tab (fila visível). Comandos `/...` e `$...`, inclusive
`/goal`, nunca usam Tab. Claude e Codex continuam recebendo texto pelo pane,
inclusive ocupados; a CLI não substitui essa rota pela fila nativa do Codex.

A materialização precisa ser verificável. Paste recolhido em um marcador,
compositor sem leitura reconhecível ou texto alterado não autoriza enviar teclas
às cegas: preserve o registro e informe BLOQUEIO com a evidência. Antes de
retomar um registro suspenso, confira a identidade e o rascunho real. O módulo
`python -m watchdog_app.pane_delivery resume <registro>` continua a etapa salva,
sem repetir o paste; ele não resolve uma entrega `uncertain` automaticamente.

Despacho, Verify Leader e avisos usam a mesma trava por pane e socket Herdr em
`$XDG_STATE_HOME/herdr-watchdog/pane-locks` (padrão `~/.local/state`). A trava
independe da worktree e de `WATCHDOG_STATE_DIR`; executores e painéis devem usar
o mesmo usuário, socket e `XDG_STATE_HOME`. Escritores novos usam
`watchdog_app.pane_delivery.send(pane, texto, api=Herdr(...))` em vez de separar
texto e Enter. Os registros privados `*.pending.json` e `*.queued.*.json`
guardam a mensagem intacta, a identidade e a etapa do envio até sua confirmação;
o log da espera fica ao lado. A trava continua mantida durante paste,
materialização, Enter e consumo. O Herdr 0.9.1 não oferece compare-and-send
atômico da identidade/compositor: eles são conferidos imediatamente antes das
teclas e após o consumo; uma mudança observada suspende o envio.

## Acompanhar e integrar

1. Confira cada executor novo aos 2, 3 e 4 minutos e redirecione cedo se necessário.
   Depois aguarde o aviso, com uma espera em segundo plano como rede de segurança,
   sem polling. O executor deve avisar; ler seu pane não substitui o aviso.
2. A cada aviso, confira todos os critérios de aceite, a costura com o que entrou
   na integração e a referência de spec dos testes novos. Rode os testes exigidos
   no checkout de integração. Só aceite com commit e evidência verificáveis.
3. Integre exclusivamente no checkout de integração. O líder implementa em
   worktrees, inclusive no modo Implementar aqui. Após integrar, feche a issue com
   comentário de evidências usando `watchdog kit fechar` (CLI abaixo), que atualiza
   a cópia local; atualize o TODO, faça commit local e
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


## CLI do kit do líder

Execute o Watchdog pelo caminho absoluto, com `--repo` apontando para o checkout
de integração do projeto acompanhado. Leia o aceite antes de abrir: o kit recebe
a tarefa liberada pelo líder e não decide dependências nem inicia outras tarefas.

```bash
/caminho/do/watchdog kit abrir --repo /projeto --grupo ID-DO-GRUPO --ticket T8 --lider w11:p8 --workspace w11 --leva 'Kit · T8 T9' --aceite docs/issues/9-ticket.md --spec docs/issues/1-spec.md
/caminho/do/watchdog kit abrir --repo /projeto --grupo ID-DO-GRUPO --ticket T9 --lider w11:p8 --workspace w11 --leva 'Kit · T8 T9' --depende T8 --aceite docs/issues/10-ticket.md --spec docs/issues/1-spec.md
/caminho/do/watchdog kit listar --repo /projeto --grupo ID-DO-GRUPO
/caminho/do/watchdog kit fechar --repo /projeto --issue 9 --copia docs/issues/9-ticket.md --comentario 'T8 concluído: commit SHA, testes RESULTADO. Evidências.'
```

`abrir` lê branch de integração, modelo, esforço e permissões do Dispatch do
projeto. Cria `.worktrees/<ticket>` a partir da ponta da integração, com branch
própria; mantém `.watchdog/` e `.worktrees/` fora do git por exclusões locais.
Cria uma aba nomeada pela leva ou divide a aba existente. `--depende` pode ser
repetido para reaproveitar a leva de uma dependência do mesmo grupo; a ocupação
real é limitada por `--capacidade` (padrão 4). Primeiro procura uma aba da
dependência com espaço, depois uma aba viva da mesma leva com espaço; se ambas
estiverem cheias ou fechadas, cria outra aba.
Use `--session NOME` em `abrir` quando o Herdr exigir sessão explícita.

O contrato em `.watchdog/run/<data>/` inclui os ponteiros, configuração, panes,
rodapé comum e aviso com trava. O Codex inicia com `--no-daemon`; o contrato
é submetido com `agent prompt --wait --until working` sob a trava do T6.
O registro `.watchdog/executors.json` versão 1
identifica projeto, grupo, tarefa, leva, branch, base, worktree, pane, terminal,
sessão nativa confirmada quando disponível, modelo, esforço, contrato, estado e
`created_at` (segundos Unix, para a checagem aos 2, 3 e 4 minutos).
`listar` devolve esse registro em JSON, filtrado pelo grupo quando informado;
`watchdog_app.leader_kit.executors(repo, group=None)` oferece a mesma leitura
para Progress e revisão. Sessão nativa indisponível permanece `null`.
`state: ready` confirma abertura, entrega do contrato e início de trabalho; não significa tarefa
concluída. Estados `preparing`/`failed` conservam a operação e os recursos para
inspeção. Confira-os antes de repetir; o kit recusa duplicar a mesma tarefa do
mesmo grupo e nunca remove recursos após resultado incerto.

`fechar` é uma operação externa: use quando o Vini tiver autorizado o fechamento.
Guarda o comentário de evidências em `.watchdog/run/<data>/`, consulta o estado,
confere se o comentário idêntico já existe, publica com `gh issue comment
--body-file` quando necessário, fecha se ainda aberta e consulta novamente. Só então
atualiza estado, corpo e comentários da cópia local, preservando campos próprios
do cabeçalho. Se falhar, confira o estado remoto e o comentário guardado antes
de repetir. O kit não integra branches, atualiza TODO, faz commit ou push.
