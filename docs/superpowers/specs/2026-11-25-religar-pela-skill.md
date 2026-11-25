# Religar o Tasks pela skill no pane escolhido

**Proposta de 25/11/2026.** Substitui o fluxo de cópia e confirmação manual descrito na [spec #17](../../issues/17-spec-religar-manual-codex.md) para Codex. O aceite humano relacionado está na [#20](../../issues/20-aceite-manual-religar-codex.md).

## Experiência no Tasks

Depois de um `/clear`, o Codex pode estar na conversa B enquanto o Herdr e o Tasks ainda exibem A. No ensaio local foi possível recuperar B pelo comando nativo do Herdr, conferir a identidade e salvar o vínculo. O grupo conservou as 14 de 15 tarefas concluídas. A recuperação exigiu intervenção pelo terminal.

1. A pessoa aperta **L · Religar** no Tasks. O painel lista os candidatos do projeto com pane e agente. Um registro de sessão desatualizado não deve ocultar um pane vivo e identificável.
2. Ela escolhe o pane Codex e pressiona **Enter**. Esse único Enter autoriza enviar a invocação da skill à conversa visível naquele pane. O Tasks indica o destino e que aguarda confirmação.
3. A skill `$religar` publica um marcador novo na própria conversa e chama `watchdog religar` com a referência da tentativa. A pessoa não precisa copiar texto, digitar um UUID, trocar de pane nem confirmar outra vez.
4. O Tasks exibe **Líder ligado · <pane> · <prefixo da sessão>** quando o registro nativo e o vínculo persistido coincidirem com a conversa comprovada. Ao reabrir o Tasks, o cabeçalho mostra o mesmo prefixo. O Progress identifica o líder no pane escolhido.

## Responsabilidades do código

- **Tasks e Herdr.** Associar cada tentativa ao projeto, ao pane e ao terminal escolhidos. Encaminhar a invocação pelo Herdr para esse destino, inclusive quando ele for diferente do líder salvo. Revalidar o destino antes do envio. O ID anunciado pode estar desatualizado. A autorização cobre apenas a invocação de Religar. Preservar rascunhos e indicar espera quando o agente estiver ocupado. Em caso de entrega incerta, impedir um segundo envio automático.
- **Skill e comando.** Distribuir a skill com o Watchdog. A parte que exige participação do agente é publicar o marcador na conversa e chamar o comando ali. Concentrar a descoberta da identidade, o registro, a persistência e o diagnóstico em código reutilizável. Ler o ID completo da sessão no contexto real do Codex. Cruzar o marcador recente do histórico com o pane visível, o agente em primeiro plano, o terminal, a conta e o projeto.
- **Registro e gravação.** Registrar a identidade comprovada pela interface nativa do Herdr. Cobrir o caso observado após `/clear`, em que uma chamada aparentemente bem-sucedida ainda pode deixar A anunciado. Reler o ID completo no Herdr e, após a transferência, reabrir o vínculo salvo e validar o mesmo ID. Reservar o prefixo para a apresentação.
- **Falha e retomada.** Exibir a etapa e a causa quando a skill estiver indisponível, a prova for ambígua, o destino mudar ou a gravação falhar. Cancelamento invalida a tentativa. Uma resposta atrasada não pode concluir uma tentativa posterior. Retomar uma transferência interrompida sem duplicar grupo, pedido ou invocação. Tornar legíveis os vínculos já gravados por versões anteriores.
- **Grupo e entregas.** Preservar integrantes, ordem, contagem, base, modos e meta. A única entrega autorizada por Religar é a invocação da própria skill. Reenviar meta continua sendo uma ação explícita. Pedidos ligados à sessão anterior permanecem associados a ela.

## Instalação e plataformas

O fluxo completo deve funcionar no Windows, no macOS e no Linux. A entrega ao pane passa pelo Herdr e dispensa a área de transferência e o servidor gráfico. O instalador deve disponibilizar a skill no Codex e resolver os componentes obrigatórios para cada sistema. Dependências adicionais são aceitáveis quando distribuíveis nos sistemas atendidos. Yazi e AI Memory são exemplos permitidos. Artify poderá integrar a instalação quando uma função futura o exigir.

No caminho percorrido pelo Religar, a implementação deve resolver identificação de processos, travas de arquivos, caminhos e execução de programas nas três plataformas. O comando deve localizar a tentativa independentemente do diretório atual do Codex e aceitar caminhos de instalação com espaços. Este aceite cobre a instalação e o uso do Religar com Codex. A recuperação de Claude e o acompanhamento automático de `/clear` têm aceites próprios.

## Critérios de aceite

| Ensaio | Resultado observável |
| --- | --- |
| Após `/clear`, a conversa é B e o registro ainda é A. Pressionar L, selecionar e dar Enter uma vez. | O pane escolhido recebe uma única invocação de `$religar`. O Tasks confirma B e mantém o prefixo de B depois de reaberto. |
| Há dois panes Codex do mesmo projeto e o escolhido difere do líder salvo. | Só o escolhido recebe a invocação. A prova identifica a conversa visível nele. Um marcador encontrado apenas no outro pane não é aceito. |
| A sessão já está correta ou a mesma conclusão é processada duas vezes. | O vínculo aponta para a sessão correta e há um único grupo e uma única transferência efetiva. |
| Há rascunho ou agente ocupado. O terminal é substituído durante a espera, ou o usuário cancela. | O rascunho é preservado. Nada é enviado ao terminal substituto. Uma prova tardia não muda o líder. |
| Falta a skill, a prova é inválida, o Herdr ainda anuncia A ou a gravação é interrompida. | O Tasks identifica a falha e não anuncia sucesso. É possível retomar ou iniciar nova tentativa preservando o grupo. |
| Grupo com 15 integrantes, 14 concluídos e pedidos antigos presos a A. | Comparar integrantes e ordem, base, modos, meta, contagem no Progress e registros de entrega antes e depois. Nenhuma meta nem pedido antigo chega a B. |
| Instalação e uso em Windows, macOS e Linux, com clipboard indisponível. | Pelo instalador da plataforma, abrir Tasks e Codex, selecionar o pane, executar a skill e reabrir o Tasks com o vínculo correto, sem configuração manual do clipboard ou da skill. Registrar um resultado por sistema. |

Automatizar o fluxo pelo Tasks com o ponto A da [spec #1](../../issues/1-spec-watchdog-painel-long-run.md), em recursos isolados. Modelar separadamente a sessão efetiva e a sessão anunciada. Conferir o estado reaberto também após interrupção. Adaptar o ponto B para exercitar o comando contra um binário Herdr falso e um repositório temporário, inclusive quando a releitura do registro devolver A. Nos testes que fixarem comportamento, citar as linhas deste aceite. Para o ensaio humano, guardar as capturas com IDs reais localmente e usar A/B no tracker.
