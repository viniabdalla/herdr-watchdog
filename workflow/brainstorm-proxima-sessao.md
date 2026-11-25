# Brainstorming do Watchdog Tasks a partir do long run do TropicDesk

## O pedido do Vini

O Vini quer preservar o jeito como trabalhou nesta sessão. Ele conversava com o líder, escolhia o próximo passo e via as tarefas no Watchdog. O líder recebia instruções curtas, acionava o workflow em uso e coordenava os executores. A preferência atual é pelo workflow de Matt Pocock. Em outro cliente, o mesmo painel deveria poder aproveitar o pacote que a sessão tiver disponível, como Superpowers.

A ideia mais concreta é marcar algumas tarefas no Tasks e pedir uma meta padrão: “faça as tarefas que estão marcadas e as que estão bloqueadas, deixa o aviso no final”. O nome dito foi “/gol”. O comando que aparece no histórico do Claude é `/goal`. O Vini pediu para guardar a ideia e discutir o desenho em outra sessão.

### Nas palavras do Vini

```text
Eu quero que ele só dê prompts e chame algumas coisas, entendeu? Por exemplo, se o cliente tiver o workflow do Matt, ele consegue puxar o workflow do Matt, entendeu?
```

```text
Esse /goal é interessante. Depois que eu marcar algumas tarefas, assim eu posso dar um /gol e nesse /gol que ele seja padrão, "faça as tarefas que estão marcadas e as que estão bloqueadas, deixa o aviso no final", entendeu? Tipo isso.
```

```text
Eu não quero que você implemente, eu quero só que você salve tudo para eu poder brainstormar com a próxima sessão para fazer com que funcione do jeito que eu quero, que é do jeito que funcionou essa sessão aqui. Entendeu?
```

## Como usar o que já funcionou

| Peça | O que funcionou no TropicDesk | Ideia para discutir |
| --- | --- | --- |
| Ação curta no painel | Em **Verificar**, o Tasks obtém os títulos marcados, monta uma pergunta, mostra a prévia com a sessão de destino e entrega ao líder após confirmação. | Aproveitar essa interação para preparar uma meta ou o próximo comando de skill. A seleção já permite preencher o pedido sem redigitar a lista. [Implementação de Verificar](../watchdog_app/tasks_ui.py) |
| Contexto para o líder | O handoff inicialmente misturava religação e publicação. Depois que o painel estava ligado, bastou o comando de tickets com a referência da spec, os bloqueios e o formato do TODO. | Resolver projeto e destino pelo vínculo atual, inserir só o contexto que a etapa exige e mostrar o texto final. IDs e caminhos históricos são exemplos. [Prompts sucessivos](preparacao-do-lider.md) |
| Contexto para o executor | Cada contrato incluiu issue, spec, aceite, worktree, limites de produção, testes e para onde avisar. O líder resolveu ambiguidades que a spec já decidia. | Deixar essa parte com o líder e o workflow do projeto. Modelo, acesso, serviços, política de merge e publicação foram escolhas específicas daquela execução. [Contrato do T3 e esclarecimento](executores/t3.md) |
| Resultado no painel | O curador examina a última resposta concluída da sessão vinculada. **Review** apresenta propostas. O **Progress** acompanha o TODO, inclusive quando o líder o edita diretamente. | Pedir ao líder um resumo final com títulos exatos, evidências e motivos dos bloqueios. Isso dá ao operador uma devolutiva legível mesmo quando ele volta horas depois. [Curador](../watchdog_app/curate.py) · [Progress](../watchdog_app/progress_ui.py) |

## A meta sobre tarefas marcadas

O [rascunho de /goal](meta-da-selecao.txt) contém o texto para discutir. Os dois campos entre chaves representam o projeto e as tarefas marcadas no instante de preparar a meta. Esta versão é uma adaptação proposta agora. A meta usada naquela madrugada fixava o intervalo T3–T13, a branch, o modelo, o destino dos avisos e os limites operacionais do CRM. [Meta histórica](comandos-execucao.md)

**Exemplo para avaliar juntos.** Vini marca A, B e C. A está livre. B depende de A. C depende de uma credencial humana. O líder conclui A, reavalia B, conclui B e encerra com um aviso: “A e B concluídas, com estas evidências. C continua bloqueada pela credencial; falta o responsável liberá-la.” Se todas já começarem bloqueadas, o resultado esperado nesse rascunho é avisar na hora. Se uma dependência for um ticket fora da seleção, o rascunho a aponta no aviso. A seleção é o limite de trabalho desta meta.

**Duas escolhas que precisam de decisão.** No long run original, um bloqueio fora da spec gerava uma pergunta ao Vini. Na nova ideia, o Vini quer receber no final o que ficou bloqueado. Vale decidir quando uma pergunta imediata ainda compensa. Também há duas listas hoje: o que está marcado em Tasks e o grupo persistido por **Acompanhar no Progress**. Na implementação atual, salvar o grupo limpa a seleção transitória. Vale decidir se gerar a meta também salva o grupo, se usa o grupo já salvo ou se as duas ações devem continuar independentes. [Seleção e grupo no Tasks](../watchdog_app/tasks_ui.py)

## Matt primeiro, outros pacotes quando existirem

Para repetir o caso com Matt, há três tipos de passo que o painel precisa saber apresentar.

1. **Comandos do pacote.** Entrevistar, sintetizar e quebrar em tickets corresponderam a `grilling`, `/to-spec` e `/to-tickets`. O setup apareceu porque faltava configurar o tracker do projeto. No ambiente consultado, `grill-with-docs`, `to-spec`, `to-tickets` e `implement-spec` trazem `disable-model-invocation: true`. Na sessão real, o Claude recusou a chamada interna de `to-spec`, e o Vini executou o comando no prompt do cliente. Mostrar ou copiar o comando para o usuário é uma opção concreta para esses passos. [Sequência e evidência da recusa](etapas-do-long-run.md)
2. **Comandos do cliente.** O `/goal` era uma capacidade do cliente líder. A origem do comando importa: uma instalação do pacote de Matt, por si só, não comprova que o cliente aceita `/goal`. Para outra sessão, vale verificar o que ela anuncia e decidir se uma instrução em texto atende quando a meta nativa está indisponível.
3. **Ações do Watchdog e do líder.** Selecionar, conferir o destino, apresentar o prompt, acompanhar o TODO e revisar sugestões já têm referências no painel. Abrir uma worktree, despachar um Codex, desbloquear e integrar foram ações coordenadas pelo líder. O pacote de Matt também oferece `/implement-spec` para um grafo inteiro e `/code-review` sobre a integração. O Vini escolheu a meta na madrugada e pediu a auditoria global na manhã seguinte, em aba própria com dois Codex visíveis e aviso ao líder. [Mapa das etapas](etapas-do-long-run.md)

**Possível recorte para a primeira versão:** concentrar a discussão em duas ações, “preparar próxima etapa do Matt” e “preparar meta da seleção”. A montagem do texto pode seguir o exemplo de `verification_prompt`. O transporte é uma decisão separada: copiar para o usuário, preencher o prompt para ele submeter ou enviar diretamente, conforme o cliente, a skill e a ação escolhida. Na gravação original, um aviso de T3 entrou no fim do `/goal`; esse é um caso real para avaliar ao escolher entre essas opções.

**Como experimentar a ideia de outro cliente:** imaginar a mesma seleção em uma sessão que anuncia apenas Superpowers. Ali podem existir etapas como `brainstorming`, `writing-plans` e `executing-plans`. O nome invocável, o tipo de entrada e o resultado de cada etapa vêm do catálogo daquela sessão. O plano de Superpowers pode apontar para um arquivo, enquanto os tickets de Matt podem apontar para issues. A unidade compartilhada pelo Tasks pode ser pequena: etapa escolhida, artefato de entrada, texto para a sessão líder e resultado esperado. Como obter esse catálogo por cliente e por projeto continua em aberto.

## A ação de code review que o Vini quer discutir

O [prompt reutilizável de revisão](code-review-da-integracao.txt) reúne a chamada ao líder em uma única mensagem. Ao discutir como preenchê-la no Tasks, use a branch e o intervalo da integração, a spec, os tickets e o destino do líder daquela sessão. O resultado esperado são dois relatórios independentes, em uma nova aba do Herdr, com aviso ao término. Depois de apresentá-los, o líder propõe a correção por um Codex novo. [Pedido do Vini e contratos efetivamente recebidos](code-review-observado.md)

## Prompt para abrir a próxima conversa

```text
Quero brainstormar o modo de prompts do Watchdog Tasks. Trabalhe na worktree feat/tasks-somente-leitura do repo herdr-watchdog. Leia workflow/README.md, workflow/etapas-do-long-run.md, workflow/brainstorm-proxima-sessao.md, workflow/meta-da-selecao.txt e workflow/code-review-observado.md. Use o long run do TropicDesk como referência do comportamento que quero repetir. Quero usar o workflow de Matt agora e aproveitar o que a sessão do cliente já tiver instalado. Quero marcar algumas tarefas e gerar uma meta padrão que faça as liberadas e me avise no fim do que ficou bloqueado. Discuta comigo uma decisão por vez e traga sua sugestão. Comece por me mostrar o que aconteceria se eu marcasse A livre, B dependente de A e C bloqueada por mim. Nesta conversa quero só brainstorming. Espere meu pedido antes de implementar.
```
