# Agentes no Progress

A seção AGENTES aparece abaixo das barras, sem ação de envio. O grupo usa o
SHA completo de `long_run.record(repo)['base']` para filtrar o registro do kit.
O TODO informa título e conclusão; a identidade nativa verificada fornece estado
e contexto. Uma sessão publicada depois da abertura só fornece telemetria após
conferência de pane, terminal e diretório da worktree.

Depois de olhar o executor aos 2, 3 e 4 minutos, o líder registra cada checagem:

```bash
/caminho/do/watchdog kit checar --repo /projeto --grupo SHA-COMPLETO --ticket T11 --etapa 1 --resumo 'Rumo conferido; testes em andamento'
```

Use etapas 1, 2 e 3 em ordem. Cada registro conserva horário e resumo em
`.watchdog/executors.json`, sob a mesma trava das aberturas. O Progress mostra
1/3–3/3 somente a partir desses registros. Sem confirmação, mostra a próxima
checagem prevista; tempo decorrido não comprova inspeção. O comando não envia
mensagens, não abre panes e não muda o TODO.

Em painéis baixos, a seção fica antes do checklist e do histórico. As teclas
j/k rolam as linhas para permitir a leitura de todas as levas.


## Perguntas para o Vini e encerramento

Um BLOQUEIO do executor chega primeiro ao líder. Quando a spec não decide,
o líder pergunta ao Vini na conversa e registra a pergunta no painel:

```bash
/caminho/do/watchdog kit perguntar --repo /projeto --grupo SHA-COMPLETO --tarefa 'C' --duvida 'Qual destino devemos usar?'
/caminho/do/watchdog kit responder --repo /projeto --grupo SHA-COMPLETO --tarefa 'C'
```

`--tarefa` (também `--ticket`) aceita UUID, chave estável do grupo, título
inequívoco ou atalho Tn. Consulte `members` no JSON do grupo para as chaves.
Título ou atalho ambíguo é rejeitado. Apenas encaminhe perguntas que dependem
do Vini; o Progress não interpreta todo BLOQUEIO como uma pergunta para ele.
A faixa permanece após reabrir o painel e sai com `responder`.

Ao terminar, avise na conversa e registre o mesmo resumo:

```bash
/caminho/do/watchdog kit encerrar --repo /projeto --grupo SHA-COMPLETO --concluida 'A|commit abc123, 8 testes OK' --concluida 'B|commit def456, 12 testes OK' --bloqueada 'C|Falta escolher destino|Vini escolhe; líder retoma C'
```

Repita `--concluida 'TAREFA|EVIDÊNCIA'` e
`--bloqueada 'TAREFA|MOTIVO|PRÓXIMO PASSO'` para cobrir cada membro uma única vez.
O TODO precisa confirmar as concluídas. Campos vazios e membros ausentes ou
ambíguos impedem o registro. Bloqueio e próximo passo aparecem no título da
faixa e da notificação, antes das evidências das concluídas. O encerramento
aparece antes de perguntas antigas; as evidências detalhadas ficam depois
das linhas dos agentes. A faixa permanece
até o próximo despacho confirmado, inclusive se o grupo ainda estiver
incompleto. Cancelar a prévia ou uma entrega sem confirmação preserva a faixa.
Zerar explicitamente o grupo também remove seus avisos.

Os comandos chamam `notify-send` uma vez por evento novo; repetir o mesmo
registro não repete a notificação. Falhas do desktop aparecem no Progress e
preservam o evento gravado. O painel só lê esses registros, sem reenviar
notificações a cada atualização. Os comandos não enviam mensagens ao líder,
não modificam TODO e não encerram sessões ou metas nativas do harness.
