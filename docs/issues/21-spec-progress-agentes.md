---
number: 21
title: "Spec: AGENTES do Progress mostra quem faz o quê e onde"
state: open
labels: [ready-for-agent]
url: https://github.com/viniabdalla/herdr-watchdog/issues/21
blocked_by: []
updated: 2026-11-25
---

## Problema

A seção AGENTES do Progress lista só o grupo do long run atual. Um executor de outra rodada, como o Religar-18, não aparece. A faixa "Meta encerrada" ocupa o topo depois que a meta acabou. Executores concluídos mostram "Identidade indisponível · Contexto Sem dados". As linhas quebram num pane estreito e parecem um parágrafo só. Não há como ir até um executor, fechar um executor ocioso ou pedir ajuda ao líder para destravar um bloqueio.

## Solução

Abaixo das barras Long run e Projeto, que não mudam, AGENTES responde "quem está fazendo o quê, e onde". Bloqueados e itens na fila vêm primeiro, num bloco vermelho. Depois vem o líder e, em seguida, os executores agrupados pela tab do Herdr. Cada agente ocupa uma linha com bolinha de estado, pane, estado, contexto e botões. Quem está trabalhando ganha uma segunda linha curta com a atividade atual.

## Histórias de usuário

1. Como Vini, quero ver primeiro o que está bloqueado ou na fila, em vermelho, para agir onde o trabalho parou.
2. Como Vini, quero ver o líder e cada executor com estado e contexto usado, para saber quem está fazendo o quê, e onde.
3. Como Vini, quero os executores agrupados pela tab do Herdr, com grupos que abrem e recolhem (▶/▼), para o painel caber num pane baixo.
4. Como Vini, quero um botão [ir] em cada agente que me leva ao pane dele. Só o clique exato no botão me leva; clicar no resto da linha só seleciona.
5. Como Vini, quero fechar pelo painel um executor ocioso, com confirmação por Y, sem conseguir fechar um executor trabalhando ou bloqueado.
6. Como Vini, quero um botão [unblock] em cada item do bloco vermelho que pede ao líder para destravar, sem me chamar se não for imperativo.
7. Como Vini, quero cores sutis: só a bolinha, os separadores e a barra de contexto têm cor; o bloco vermelho é a exceção.
8. Como Vini, quero ver executores de qualquer rodada do líder e, num grupo "Outros", qualquer executor registrado fora delas.

## Decisões de implementação

- Ordem: BLOQUEADOS, LÍDER, grupos por tab. O topo do Progress (título, Long run, Projeto) não muda. A faixa "Meta encerrada" sai do topo; o resumo final vira uma linha recolhida no fim de AGENTES, que abre as evidências com um clique. Seções separadas por uma linha em branco. Perguntas que aguardam o Vini continuam no topo de AGENTES.
- Bloqueado: executor cujo pane o Herdr marca como bloqueado, cujo contrato falhou, ou que enviou `BLOQUEIO` pelo aviso e ainda não enviou `pronto` nem foi desbloqueado pelo líder. Um executor trabalhando há mais de um minuto depois do aviso de bloqueio deixa o bloco vermelho.
- Na fila: tarefa do grupo ainda sem executor. Fica no bloco vermelho com bolinha amarela e a marca "na fila", com o motivo (espera outra tarefa, depende do Vini, aguardando executor).
- Rodadas do líder: registros do kit cujo líder é o pane do líder ligado, ou cujo grupo é a base do long run atual (herdada no Religar). Os demais registros vivos vão para o grupo "Outros", que só aparece quando existe.
- Grupos: um por tab do Herdr (`tC · Religar Codex`, com o nome da leva). Recolher só esconde linhas. Grupo sem ninguém trabalhando começa recolhido e mostra um resumo (`▶ t8 · Code Review · 2 feitos`). Executores cujo pane já foi fechado não aparecem.
- Estados e cores da bolinha: bloqueado vermelho, trabalhando verde, na fila amarelo, feito azul, ocioso sem ter terminado cinza. Feito é tarefa concluída no TODO ou aviso `pronto` enviado com o executor parado.
- Barra de contexto com a cor do nível de contexto: verde abaixo de 80%, amarelo a partir de 80%, vermelho a partir de 100%. Texto em cor normal.
- Segunda linha só para quem está trabalhando: a atividade atual (ou o título da tarefa) e a checagem inicial, cortada na largura do pane. Os demais ficam numa linha. Linhas de agente não quebram: o texto é cortado e os botões ficam no fim.
- [ir] usa `herdr agent focus <pane>`, que abre a tab e seleciona o pane. Teclado: `i` no agente selecionado.
- [fechar] aparece só na linha selecionada, se o executor está ocioso, não bloqueado e o terminal do pane é o registrado. Pede "Fechar <ticket> (<pane>)? Y confirma · outra tecla cancela". Y fecha o pane com `herdr pane close`. Worktree e commits não mudam. O líder nunca é fechado pelo painel.
- [unblock] envia ao pane do líder, pela entrega com confirmação, um prompt curto: quem e onde, o motivo nas palavras do executor, o caminho absoluto do contrato e a regra "desbloqueie e responda no pane do executor; se a decisão não muda o desenho, decida e conte depois; só pergunte ao Vini se for imperativo (desenho, escopo, push, deploy, envio externo, perda de dados, merge na main), trazendo sua sugestão de desbloqueio". O mesmo bloqueio não é reenviado enquanto o painel estiver aberto. O prompt inclui o comando do kit que limpa o bloqueio depois da resposta.
- O painel continua com uma linha de rodapé e cabe num pane de ~60×20. Configurações futuras abrem numa janela. Sessão sem checklist, execuções encerradas, "No active runs" e o histórico do projeto não aparecem.

## Testes e critérios de aceite

Ponto de teste A da spec #1: Progress em pseudo-terminal com Herdr, kit e TODO isolados.

| Cenário | Resultado observável |
| --- | --- |
| Worker de outra rodada do mesmo líder trabalhando. | Aparece no grupo da tab dele, com bolinha verde e segunda linha de atividade. |
| Worker registrado por outro líder. | Aparece só no grupo "Outros". |
| Worker com `BLOQUEIO`, tarefa na fila e executor com pane bloqueado. | Os três estão no bloco BLOQUEADOS, acima do líder; a tarefa na fila tem "na fila". |
| Clique no [ir] de um executor. | Uma chamada `agent focus` com o pane do executor. Clique fora do botão só seleciona. |
| Worker trabalhando ou bloqueado selecionado. | Sem [fechar]. |
| Worker ocioso selecionado, [fechar], depois outra tecla. | Nada fecha. Com Y, uma chamada `pane close` com o pane do executor. |
| [unblock] duas vezes no mesmo bloqueio. | Uma entrega ao pane do líder com o contrato e a regra; a segunda vez só avisa que já foi enviado. |
| Contexto a 85% e a 100%. | Barra amarela e vermelha; texto em cor normal. |
| Grupo sem ninguém trabalhando. | Começa recolhido com resumo; clique no cabeçalho abre. |
| Meta encerrada registrada. | A faixa não aparece no topo; uma linha recolhida no fim de AGENTES abre o resumo final. |

## Fora do escopo

Rodadas múltiplas nas barras do topo ("Também aberta: ...", barra do Long run seguindo a rodada ativa do líder). Fica para a próxima tarefa, porque o estado do long run guarda um grupo só por projeto. Janela de configurações. Mudanças no Tasks, no Left Undone e no registro de grupos pelo líder.

## Referências

Desenho fechado com o Vini em 25/11/2026 na sessão de supervisão (`.watchdog/run/2026-11-25/desenho-progress-agentes.md`). Achados 1–3 do handoff de supervisão. Spec #1, seção AGENTES (#12, T11).
