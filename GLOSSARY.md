# Herdr Watchdog

Painéis no Herdr para o Vini escolher tarefas do TODO de um projeto, entregá-las a uma sessão líder e acompanhar o progresso dos agentes que trabalham nelas.

## Pessoas e sessões

**Líder**:
A sessão de agente (Claude ou Codex) ligada ao painel, que recebe os pedidos do Tasks e coordena o trabalho.
_Avoid_: sessão principal, main, orquestrador

**Executor**:
Um agente novo, aberto pelo líder para uma única tarefa, numa worktree e branch próprias.
_Avoid_: worker, subagente, implementador

**Revisor**:
Um agente novo, aberto pelo líder para um eixo do code review (Standards ou Spec), que só lê e grava um relatório.

**Curador**:
O processo do Watchdog que lê a conversa do líder e propõe marcar tarefas como concluídas.

**Vínculo**:
A ligação entre um painel e o pane do líder; segue o líder quando a sessão é limpa no mesmo pane e precisa ser refeito quando o líder muda de pane.
_Avoid_: binding, conexão

**Harness**:
O cliente de agente em que o líder roda (Claude Code ou Codex), que define como as skills são chamadas.
_Avoid_: cliente, CLI

## Trabalho

**Seleção**:
As tarefas marcadas agora no Tasks, ainda sem nenhum efeito.

**Despacho**:
A entrega de uma seleção ao líder, que soma as tarefas ao grupo.
_Avoid_: dispatch, envio

**Grupo**:
O conjunto acumulado de tarefas despachadas, que o Progress mede; zera quando todas estão concluídas e um novo despacho chega, ou quando o Vini manda.
_Avoid_: long run, lista fixa

**Meta**:
O objetivo persistente dado ao líder para concluir o grupo, que o impede de parar antes do fim.
_Avoid_: goal, objetivo

**Leva**:
Os executores abertos juntos num mesmo momento, que dividem uma aba nomeada pelo tema e pelas tarefas.
_Avoid_: onda, batch, fronteira

**Branch de integração**:
A branch local em que o líder junta o trabalho de cada executor; só sai da máquina por decisão do Vini.

## Risco

**Porta dupla**:
Uma mudança que pode ser desfeita a baixo custo.
_Avoid_: reversível, two-way door

**Porta única**:
Uma mudança que não pode ser desfeita, como perda de dados, envio real ou deploy.
_Avoid_: irreversível, one-way door

**Raio**:
O tamanho do estrago se a mudança der errado.
_Avoid_: blast radius, impacto

**Merge danger**:
A avaliação de porta e raio feita sobre a branch de integração antes de ela sair da máquina.
