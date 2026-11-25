---
number: 17
title: "Spec: Religar o Tasks à sessão atual do Codex após /clear"
state: open
labels: [ready-for-agent]
url: https://github.com/viniabdalla/herdr-watchdog/issues/17
blocked_by: []
updated: 2026-11-25
---

## Problema

No aceite de #15, o Codex passou da conversa A para a conversa B após um `/clear` no mesmo pane. O Herdr continuou anunciando A. Ao selecionar esse pane em **Religar**, o Tasks exibiu “Líder ligado”, mas o cabeçalho ainda identificava A. O Progress conservou as mesmas 15 tarefas, com 14 concluídas. A falha observada foi a confirmação do líder incorreto. A causa do registro antigo no Herdr segue em aberto.

## Solução

Quando a pessoa escolhe novamente o pane do líder Codex e o Herdr ainda devolve o ID já salvo, o Tasks pede confirmação dentro da conversa que está na tela. Mostra o pane escolhido e uma instrução curta para copiar. A conversa produz uma prova de identidade. O Tasks só anuncia sucesso depois de conferir a prova, reler a identidade nativa e verificar o vínculo persistido. A mensagem de sucesso mostra o pane e o prefixo da sessão confirmada.

## Histórias de usuário

1. Como pessoa que usa o Tasks, quero escolher novamente o pane do líder depois de um `/clear`, para recuperar o vínculo sem reiniciar os painéis.
2. Como pessoa que escolheu o pane, quero ver “Confirme a sessão no Codex de <pane>” e uma instrução copiável, para saber onde confirmar sem procurar um UUID.
3. Como pessoa que usa várias conversas no mesmo projeto, quero que a confirmação identifique a conversa visível no pane escolhido, para poder confiar no destino.
4. Como pessoa que confirmou B, quero ver “Líder ligado · <pane> · <prefixo de B>” e o mesmo prefixo no cabeçalho, para conferir o resultado.
5. Como pessoa que selecionou novamente uma conversa que ainda é A, quero que a confirmação aceite A quando a prova identificar A, para continuar com o mesmo líder.
6. Como pessoa que cancelou ou cuja conversa não pôde ser identificada, quero ver que a sessão não foi confirmada e poder repetir a operação.
7. Como pessoa que acompanha o grupo, quero conservar as tarefas, a ordem, o progresso, os modos, a base e a meta ao religar. Quero decidir separadamente se a meta será reenviada.
8. Como pessoa que reabre o Tasks após a recuperação, quero encontrar a sessão confirmada e ver o Progress apontar para o mesmo líder.

## Decisões de implementação

- A confirmação manual se aplica à escolha explícita do mesmo pane Codex quando a descoberta repete o ID salvo. Esse resultado pode significar tanto uma sessão realmente inalterada quanto um registro antigo.
- Reutilizar a recuperação nativa por marcador. A conversa Codex escolhida publica um marcador novo e executa a recuperação em seu próprio contexto. A prova cruza o marcador recente no histórico da sessão atual com o texto visível no pane, a conta e o processo em primeiro plano. O Tasks não solicita que a pessoa digite o ID da sessão.
- Associar a tentativa ao pane e ao terminal escolhidos. Antes de aceitar o resultado, conferir novamente pane, terminal, projeto e identidade nativa completa. Só a apresentação abrevia o ID. Reaproveitar a transferência de vínculo existente quando a sessão confirmada for B.
- Cancelamento, prova ausente, ambiguidade, troca de destino ou falha ao salvar terminam sem anúncio de sucesso. Uma confirmação atrasada de uma tentativa cancelada não pode ativar o vínculo. Em caso inconclusivo, o Tasks exibe “Sessão não confirmada” e conserva o grupo.
- A pessoa cola a instrução na conversa escolhida. Religar por si só não despacha tarefas, não reenvia a meta e não entrega à sessão B pedidos que ficaram presos à identidade A.

## Testes e critérios de aceite

Usar o ponto de teste A da spec #1. Exercitar a tecla Religar no Tasks em pseudo-terminal, observar o Progress e reabrir o painel sobre o estado gravado. Usar estado temporário e um líder falso que represente **separadamente** a conversa efetiva e o ID anunciado pelo Herdr. A simples substituição de A por B na lista de candidatos não reproduz o defeito.

| Cenário | Resultado observável |
| --- | --- |
| Mesmo pane, terminal e processo. Codex já está em B e o Herdr anuncia A. A pessoa aciona Religar. | O Tasks pede confirmação no pane escolhido. Nenhum sucesso antecipado. |
| A conversa comprova B e a releitura nativa confirma B. | O aviso e o cabeçalho mostram B. Após reabrir, o vínculo continua em B. Progress exibe o líder e as mesmas 15 tarefas, na mesma ordem, com 14 concluídas. Base, modos e meta são preservados. Nenhuma entrega de tarefa ou meta. |
| A conversa continua em A e a prova confirma A. | O aviso identifica A. Repetir a confirmação não cria outro grupo nem duplica a transferência. |
| A prova pertence a outro pane, é ambígua, está ausente, o terminal mudou ou o Herdr ainda anuncia A após a prova de B. | O Tasks informa “Sessão não confirmada”. Não ativa B nem anuncia que A foi confirmada. |
| A pessoa cancela antes da resposta, ou a persistência falha. | O painel não anuncia sucesso. Uma resposta tardia não substitui o líder de uma tentativa posterior. O grupo segue íntegro. |

Usar o mesmo cenário A/B no aceite humano de #15. Conferir o ID da conversa a partir do Codex, o cabeçalho do Tasks após reabrir e os membros do grupo no Progress. Os testes que fixarem comportamento devem citar as linhas correspondentes da cópia local desta spec.

## Fora do escopo

Acompanhamento automático de `/clear`, recuperação do Claude por marcador, mudanças no Left Undone e investigação da causa interna no Herdr. A troca explícita de líder entre panes ou harnesses continua regida por #11.

## Referências

Esta spec cobre a recuperação manual identificada no aceite de #15 e complementa a história de Religar da spec #1 e da tarefa #11. O aceite automático de `/clear` continua pendente.
