---
number: 19
title: "Persistir a sessão recuperada após /clear e preservar o grupo"
state: open
labels: [ready-for-agent]
url: https://github.com/viniabdalla/herdr-watchdog/issues/19
parent: 17
blocked_by: [18]
updated: 2026-11-25
---

## Parent

#17

## What to build

Concluir o percurso em que o mesmo pane e processo passaram de A para B, enquanto o Herdr ainda anunciava A. Ao final, o Tasks reaberto e o Progress acompanham o líder confirmado.

## Acceptance criteria

- [ ] A escolha do pane com registro antigo não anuncia sucesso. Após prova de B, releitura nativa de B e verificação do vínculo salvo, o aviso mostra o pane e o prefixo de B. O cabeçalho reaberto também mostra B.
- [ ] O Progress mantém o líder no pane escolhido e as mesmas 15 tarefas, na mesma ordem, com 14 concluídas. Preservar base, modos e meta. Nenhum despacho, reenvio de meta ou entrega a B de pedidos vinculados a A.
- [ ] Se o Herdr ainda anunciar A, houver mudança do destino ou falha de persistência, não anunciar sucesso. O grupo permanece íntegro e a tentativa pode ser repetida.
- [ ] Resposta tardia de tentativa cancelada não ativa B nem substitui um líder posteriormente confirmado. Repetir uma confirmação concluída não duplica a transferência.
- [ ] Cobrir pelo ponto A com estado temporário, observando o Tasks, o Progress, a reabertura e a ausência de entregas. Citar as linhas da spec local e verificar as duas configurações de controles do projeto.
