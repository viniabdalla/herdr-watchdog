---
number: 16
title: "T15 — Fila travada no pane do líder"
state: closed
labels: ["ready-for-agent"]
url: https://github.com/viniabdalla/herdr-watchdog/issues/16
parent: 1
blocked_by: []
updated: 2026-11-25
---

## Parent

#1

## O problema (25/11)

A entrega da frente na fila do pane do líder (aviso antigo do T6, fase "colando") ficou parada 38 min porque o texto saiu da caixa antes de ser enviado. Atrás dela acumularam o aviso do T13 e 4× `$code-review`. O Tasks só mostrava "Aguardando a entrega anterior ao mesmo pane"; o Vini apertou o botão de novo e teve de perguntar ao líder o que fazer.

## Comportamento desejado

Quando a entrega da frente não andar por mais de **2 minutos**, a trava:

1. põe essa entrega de lado (guarda cópia, nada é apagado);
2. digita no pane do líder, com o caminho normal confirmado, a mensagem abaixo;
3. mostra no Tasks "Fila travada · perguntei ao líder" em vez de "Aguardando";
4. deixa a fila seguir.

### Mensagem da trava (campos entre chaves preenchidos pela trava)

```text
Fila travada no seu pane {pane}: a entrega da frente ({resumo da frente}) está parada há {tempo}. Atrás dela: {lista da fila}. Siga "Fila travada" no padrão do dispatch e me diga o que precisa da atenção do Vini.
```

### Seção para `docs/dispatch.md`

```markdown
## Fila travada

Quando o Watchdog avisar "Fila travada", destrave a fila do seu pane:

1. Guarde uma cópia da fila na pasta de execução.
2. Para cada entrega, decida: já tratada (aviso de tarefa integrada) → retire; repetida → mantenha a mais recente; atual → mantenha.
3. Entregue o que ficou, uma vez cada, na ordem.
4. Responda ao Vini numa mensagem: o que retirou e por quê, o que entregou, e o que depende dele.

Pronto quando a fila tem no máximo uma entrega de cada pedido e o Vini sabe o que depende dele.
```

## Teste (ponto B, Herdr falso)

- Entrega parada além do prazo → a cópia fica guardada, a mensagem "Fila travada" chega ao líder uma vez e a fila continua.
- Entrega que anda dentro do prazo → nada muda.
- Tasks mostra "Fila travada · perguntei ao líder" enquanto o líder não destrava.

## Critérios de aceite

- [ ] O prazo de 2 minutos mede falta de progresso da entrega da frente. Um avanço dentro do prazo preserva a entrega normal.
- [ ] Ao estourar o prazo, a entrega parada é arquivada intacta, e o aviso acima é entregue uma única vez pelo caminho confirmado do pane. O líder recebe a identificação do pane, um resumo da frente, o tempo e a fila posterior.
- [ ] O Tasks exibe a frase aprovada enquanto aguarda a resolução do líder. Preservar identidade, rascunho e confirmação de consumo nos dois harnesses.
- [ ] A reconciliação segue a seção “Fila travada”, preservando somente o pedido atual mais recente de cada repetição e a ordem dos que ficaram. A fila volta a andar.
- [ ] Há cobertura no ponto B com relógio controlado e Herdr falso, incluindo a entrega normal, o aviso único, a recuperação da fila e o texto do Tasks. A seção aprovada consta no padrão do dispatch.


## Comentários

### 2026-11-25T17:29:24Z · viniabdalla

Após dois minutos sem progresso, o Watchdog arquiva a frente e a fila, envia ao líder um aviso único pelo pane verificado e mostra o estado Fila travada no Tasks após confirmar a entrega. O líder escolhe os pedidos atuais e o Watchdog mantém o mais recente de cada repetição na ordem. A seção Fila travada documenta a triagem e a recuperação explícita inclusive quando o próprio aviso não chegou. Na prova com os seis registros da ocorrência original e Herdr isolado, o aviso chegou em 123,7 segundos, os seis originais foram preservados, o comando mais recente entrou uma vez e a fila esvaziou.

Commit do executor `4465a99`, integrado em `b650e39`. A suíte executou 674 testes em cada modo de controles, com 7 ignorados e nenhuma falha.
