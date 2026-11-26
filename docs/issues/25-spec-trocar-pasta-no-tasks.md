---
number: 25
title: "Spec: Trocar pasta no Tasks"
state: open
labels: [ready-for-agent]
url: https://github.com/viniabdalla/herdr-watchdog/issues/25
blocked_by: []
updated: 2026-11-25
---

# Trocar pasta no Tasks

1. O Tasks define a pasta da aba. **Trocar pasta** lista as worktrees do repositório do Tasks com `git worktree list` e marca a pasta atual. Para voltar, escolha a pasta original na mesma lista.
2. Progress, Artifacts e Yazi seguem o Tasks da mesma aba. Ao trocar de pasta, os quatro painéis passam a usar a pasta escolhida, cada um no mesmo pane.
3. O líder já ligado continua ligado. **Despachar** entrega à mesma conversa e inclui o caminho atual do Tasks. **Religar** mantém a conferência de identidade que já faz hoje. Toda recusa de religação, troca de pasta ou despacho mostra na tela o motivo em uma frase e indica o próximo passo. Exemplo de recusa ao religar: “Não religuei: este líder começou em git-todo e o Tasks está em git-todo-rumo. Volte o Tasks para git-todo ou abra um líder em git-todo-rumo.”
4. A pasta escolhida persiste ao reabrir o Watchdog. Nenhuma dessas ações grava no `state.db` ou altera painéis de outras abas.

## Aceite

- **(a)** Trocar a pasta no Tasks muda os quatro painéis da aba nos mesmos panes. Despachar entrega à mesma conversa com o caminho novo.
- **(b)** Reabrir o Watchdog mantém a pasta escolhida. Escolher a original na mesma lista faz os painéis voltarem.
- **(c)** Toda recusa mostra o motivo e o próximo passo. Os painéis de outra aba e o `state.db` ficam intactos.
