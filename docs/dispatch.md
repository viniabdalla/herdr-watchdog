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
   Registre a pergunta no painel com `watchdog kit perguntar`; após a resposta,
   use `watchdog kit responder` (comandos em [Agentes no Progress](agents/progress-agentes.md)).
5. Ao encerrar, avise o Vini na conversa: concluídos com commit e testes;
   bloqueados com motivo e próximo passo. Não espere que ele volte e pergunte.
   Registre esse mesmo resumo com `watchdog kit encerrar` para manter a faixa
   no Progress e notificar no desktop; veja [os comandos](agents/progress-agentes.md).

## Revisão e saída da máquina

Quando o Vini pedir code review, o botão preenche `/code-review BASE..INTEGRACAO`
no Claude ou `$code-review BASE..INTEGRACAO` no Codex, usando a base e a branch
salvas no primeiro despacho do grupo. A prévia permite editar ambos. Grupo
antigo ou ausente sem esses dados mostra um aviso: preencha o intervalo; não
invente a base a partir do HEAD atual.

O líder resolve as duas pontas para hashes uma vez antes de abrir a revisão.
Abra pelo kit dois revisores novos e visíveis, Standards e Spec, numa mesma aba
`Code Review`, cada um na sua worktree, sobre esses mesmos hashes. Use tickets
únicos por rodada e a mesma leva nos dois comandos. Por exemplo, substituindo
os valores BASE_SHA e FIM_SHA pelos hashes já resolvidos e os demais dados
pelos do contrato do líder:

```bash
/caminho/do/watchdog kit abrir --repo /projeto --grupo ID-DO-GRUPO --ticket R1-Standards --lider w11:p8 --workspace w11 --leva 'Code Review' --aceite docs/issues/tarefa.md --spec docs/issues/spec.md --revisor Standards --base BASE_SHA --fim FIM_SHA
/caminho/do/watchdog kit abrir --repo /projeto --grupo ID-DO-GRUPO --ticket R1-Spec --lider w11:p8 --workspace w11 --leva 'Code Review' --aceite docs/issues/tarefa.md --spec docs/issues/spec.md --revisor Spec --base BASE_SHA --fim FIM_SHA
```

O kit usa os modelos abaixo em vez do rodapé de executor. Salva contratos e
reserva caminhos distintos para os relatórios em
`/projeto/.watchdog/run/<data>/`, ignorada pelo git. Cada revisor recebe os
caminhos absolutos, o intervalo fixo e seu comando de aviso com trava.
Modelo e esforço continuam vindo do Dispatch. O líder fornece os ponteiros de
aceite de toda a rodada; se forem vários, use um índice na pasta de execução.

Espere os dois avisos e confira os dois relatórios salvos antes de apresentar
qualquer conclusão. Mostre uma tabela lado a lado, com eixo, número de achados,
pior severidade e link para o relatório completo; liste achados com arquivo e
linha, evidência e consequência. Se um revisor bloquear ou falhar, informe isso
e aguarde sua conclusão, sem apresentar revisão parcial como completa.

Após apresentar, aguarde o ok explícito do Vini para corrigir. Só então abra
um único executor novo pelo kit, com ticket e leva novos, numa aba nova só dele,
e entregue a lista de correções aprovada e os dois relatórios. Não reutilize os
revisores para implementar. Confira os aceites e testes antes de integrar.
Depois seguem `/retro` (ou `$retro` no Codex) e o teste do Vini. O Vini decide
merge danger e push; integrar localmente não autoriza sair da máquina.

### Contrato-modelo Standards

Você é o revisor Standards. Faça uma revisão somente leitura do intervalo fixo
informado no cabeçalho, na worktree fornecida. Leia AGENTS.md, GLOSSARY.md e
as normas documentadas apontadas pelo projeto, incluindo ADRs aplicáveis.
Consulte `git diff BASE..FIM` e o contexto dos arquivos alterados; use os hashes
do contrato, mesmo que a integração avance durante a revisão.

Foco: violações dos padrões documentados do repositório. Pistas: instruções
locais dos diretórios alterados, convenções explícitas e invariantes descritas
nas normas. Cite a regra e sua fonte para cada achado. Preferências pessoais e
problemas anteriores fora do intervalo ficam excluídos. A conformidade com
critérios funcionais pertence ao eixo Spec.

Escreva somente o relatório no caminho absoluto reservado no cabeçalho;
preserve código, índices git, TODO.md, HANDOFF*, issues, Left Undone e serviços
ou painéis em execução. Não faça correções, commits, merges, push ou envios
externos. Se faltar uma fonte, registre a limitação ou envie BLOQUEIO ao líder
pelo comando do contrato. Não abra outros agentes.

Relatório curto: eixo e intervalo; fontes lidas; contagem por severidade e pior
achado; para cada achado, arquivo:linha, regra, evidência e consequência.
Declare explicitamente zero achados quando for o caso e liste limitações.
Depois de salvar o relatório, envie um único aviso ao líder com seu caminho,
contagem e pior severidade, usando o comando fornecido no contrato.

### Contrato-modelo Spec

Você é o revisor Spec. Faça uma revisão somente leitura do intervalo fixo
informado no cabeçalho, na worktree fornecida. Leia AGENTS.md, GLOSSARY.md,
os ponteiros de aceite e a spec/plano indicados no contrato para toda a rodada.
Consulte `git diff BASE..FIM`, o contexto e os testes relevantes, usando os hashes
do contrato mesmo que a integração avance durante a revisão.

Foco: atendimento aos critérios de aceite e comportamento observável exigido
pela spec, inclusive suas costuras entre tarefas. Pistas: cenários de usuário,
fronteiras, erros, pontos de teste A e B aplicáveis e referências de linha da
spec nos testes que fixam comportamento. Relacione cada lacuna à fonte e linha
que exige o comportamento. Hipóteses sem evidência e funcionalidades fora do
escopo ficam excluídas. Estilo e padrões documentados pertencem a Standards.

Escreva somente o relatório no caminho absoluto reservado no cabeçalho;
preserve código, índices git, TODO.md, HANDOFF*, issues, Left Undone e serviços
ou painéis em execução. Não faça correções, commits, merges, push ou envios
externos. Verificações usam apenas dublês e recursos isolados. Se faltar uma
fonte, registre a limitação ou envie BLOQUEIO ao líder pelo comando do contrato.
Não abra outros agentes.

Relatório curto: eixo e intervalo; fontes lidas; contagem por severidade e pior
achado; para cada achado, arquivo:linha, requisito com linha, evidência e
consequência. Declare explicitamente zero achados quando for o caso e liste
limitações. Depois de salvar, envie um único aviso ao líder com caminho,
contagem e pior severidade, usando o comando fornecido no contrato.

### Fim dos contratos de revisão

Os modelos acima se aplicam apenas aos revisores; executores de correção usam
o rodapé comum e os testes do Dispatch.

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

### Recuperar entrega suspensa (R1)

Depois de colar, falta de confirmação por 2 segundos de observações suspende a
entrega em `uncertain`; não confirma consumo. Uma observação válida de texto
materializado ou consumo tem precedência sobre esse prazo, inclusive após um
CLI lento. Antes de colar, rascunho humano continua sendo espera legítima, sem
esse prazo. Registros antigos em `pasting`, sem timestamp, recebem uma janela
persistida na primeira retomada. Texto, identidade, fase e compositor observado
ficam no registro; os próximos itens continuam guardados em ordem FIFO.

`resume` nunca resolve `uncertain`. Confira o registro e o pane, a identidade e
o rascunho real. Um paste pode aparecer atrasado: campo vazio não prova envio,
cancelamento nem que seja seguro liberar a próxima mensagem. Não apague o
registro nem repita o paste. Para observar e suspender um registro antigo:

```sh
python3 -m watchdog_app.pane_delivery resume /caminho/registro.pending.json
```

Se o paste atrasado já terminou e o compositor mostra exatamente a mensagem
inteira de A, autorize explicitamente continuar a partir dela, sem novo paste:

```sh
python3 -m watchdog_app.pane_delivery reconcile /caminho/registro.pending.json \
  --resolution materialized --evidence 'Texto inteiro e identidade conferidos; paste encerrado'
python3 -m watchdog_app.pane_delivery resume /caminho/registro.pending.json
```

Se A foi resolvido manualmente (enviado ou cancelado), primeiro confirme fora do
Watchdog que o paste antigo terminou e não voltará a escrever. Só então retire
explicitamente A, registrando o que observou e como resolveu. Isso cancela a
entrega automática, **não confirma envio** nem executa sua atualização de grupo:

```sh
python3 -m watchdog_app.pane_delivery reconcile /caminho/registro.pending.json \
  --resolution retired --evidence 'Paste encerrado; A cancelado manualmente; rascunho humano preservado'
```

A retirada preserva o rascunho humano e arquiva a entrega com a evidência e a
identidade observada em `*.reconciled.*.json`. Os workers já em espera retomam a
fila; se não houver worker, use `resume` nos registros `*.queued.*.json`, na
ordem dos nomes. B só cola quando o compositor estiver vazio. Após Religar, uma
entrega antiga jamais tecla na sessão nova: somente a retirada explícita é
permitida; itens posteriores presos à sessão antiga também precisam de retirada
com evidência. Novos envios usam a identidade nova. A reconciliação compara o
registro lido com o que ainda está sob a trava; se tiver mudado, releia e decida
novamente. Nenhum desses passos deve ser aplicado ao pane real como teste.

## Fila travada

Quando o Watchdog avisar "Fila travada", destrave a fila do seu pane:

1. Guarde uma cópia da fila na pasta de execução.
2. Para cada entrega, decida: já tratada (aviso de tarefa integrada) → retire; repetida → mantenha a mais recente; atual → mantenha.
3. Entregue o que ficou, uma vez cada, na ordem.
4. Responda ao Vini numa mensagem: o que retirou e por quê, o que entregou, e o que depende dele.

Pronto quando a fila tem no máximo uma entrega de cada pedido e o Vini sabe o que depende dele.

Os registros `*.stalled.json` na pasta compartilhada de trava por pane apontam
para a cópia intacta da frente (`front.json`) e da fila (`queue.json`). As novas
entregas continuam guardadas em `*.queued.*.json`; nenhuma sai antes da decisão.
Copie esses registros para a pasta de execução. Leia o snapshot da triagem, com
IDs estáveis inclusive para os registros antigos sem `delivery_id`:

```bash
python -m watchdog_app.pane_delivery queue-snapshot --pane PANE
```

O snapshot é o da detecção da trava; entregas posteriores ficam preservadas
mesmo quando não constam em `--keep`. Textos iguais com callbacks ou identidades
diferentes são pedidos distintos.
Depois de conferir que o paste antigo terminou e que o compositor está vazio,
registre a decisão com:

```bash
python -m watchdog_app.pane_delivery resolve-queue --pane PANE --keep ID_ATUAL ID_OUTRO --evidence 'Motivos das retiradas e confirmação do paste antigo encerrado'
```

Use `--session NOME` quando o vínculo usa uma sessão Herdr explícita. Sem IDs
em `--keep`, todas as entregas do snapshot são retiradas; posteriores sobrevivem. Os IDs escolhidos são entregues
pelo worker na ordem original; textos repetidos preservam somente o mais recente.
A decisão e todos os originais ficam arquivados. Se o processo de espera foi
interrompido, retome `python -m watchdog_app.pane_delivery watch REGISTRO` usando
um registro pendente ou enfileirado; não reenvie o pedido original.

Se o próprio aviso estiver `uncertain`, o worker não o reenvia nem cria outro.
Confira identidade, compositor e consumo real. A reconciliação R1 com
`--resolution materialized` continua um paste comprovadamente materializado.
Para um aviso já lido pelo líder cujo consumo não foi observado, use
`python -m watchdog_app.pane_delivery reconcile REGISTRO --resolution consumed
--evidence 'Confirmação do líder e compositor vazio'` (na mesma linha).
Essa confirmação exige o mesmo líder e compositor vazio. Só então resolva a
fila. O worker retoma uma decisão interrompida sem liberar cópias descartadas.

Se o alerta **nunca entrou no histórico**, `consumed` não é uma saída: não há
recibo. Um compositor vazio sozinho também não prova não entrega. Confira o
histórico da identidade exata, encerre qualquer paste atrasado e registre essa
evidência antes de rearmar. Um rascunho humano é preservado; o aviso continuará
esperando o compositor vazio. Se o próprio alerta já está materializado, use a
continuação R1 em vez de colar outra cópia.

O campo `archive` de `*.stalled.json` identifica o incidente. Escolha um ID para
a decisão e mantenha **o mesmo ID e os mesmos argumentos** em qualquer retomada:

```bash
python -m watchdog_app.pane_delivery recover-notice --pane PANE \
  --incident /caminho/do/incidente.stalled.ID --action rearm \
  --recovery-id DECISAO_ID --not-delivered \
  --evidence 'Histórico da sessão conferido sem o alerta; paste anterior encerrado; evidência e localização'
python -m watchdog_app.pane_delivery watch /caminho/do/registro.pending.json
```

O primeiro comando grava a decisão sem enviar tecla ou declarar consumo. O
worker ativo, ou o segundo comando, continua o mesmo incidente pelo caminho
confirmado do pane. O aviso só reaparece no Tasks como “perguntei ao líder” após
o recibo real. Repetir a decisão completa uma interrupção; não rearma novamente
uma decisão já aplicada, mesmo depois do consumo. Se houver nova falha de
não entrega, releia os registros e faça **outra decisão explícita, com outro ID**.
Não existe repetição automática de um alerta incerto. A decisão salva inclui o
aviso original, identidade, compositor, evidência e etapa da recuperação.

Se a identidade do líder mudou, rearmar é recusado: esta rota não transfere o
alerta nem pedidos antigos para outra sessão. Encerre documentalmente o
incidente obsoleto, com uma decisão explícita:

```bash
python -m watchdog_app.pane_delivery recover-notice --pane PANE \
  --incident /caminho/do/incidente.stalled.ID --action close \
  --recovery-id DECISAO_ID \
  --evidence 'Identidade antiga encerrada; incidente obsoleto; motivos e evidências'
```

O encerramento não envia texto, tecla nem recibo para a sessão nova. Arquiva
integralmente o aviso e os pedidos presos a identidades obsoletas, sem executar
seus callbacks. Preserva os pedidos da identidade atual na ordem, inclusive
os que chegaram depois da triagem ou durante a recuperação. O worker normal
pode entregar esses pedidos com suas próprias identidades verificadas; eles
não são um reenvio do alerta antigo. Rascunhos continuam intocados. Todos os
originais permanecem no incidente para consulta. A faixa some pelo encerramento
documental, sem ter sido falsamente marcada como entregue.

Use `--session NOME` nos comandos quando aplicável. Após uma interrupção, repita
o comando `recover-notice` com o mesmo ID, incidente e argumentos, inclusive se
o `pending.json` já desapareceu. Um worker que encontra a decisão em andamento
a termina antes de qualquer entrada no pane. Para iniciar um worker sem registro
pendente, use um registro enfileirado atual. Reconciliação R1 continua disponível
para um paste materializado ou um recibo realmente confirmado; não a use para
inventar consumo nem cancelar uma recuperação ainda em andamento.
