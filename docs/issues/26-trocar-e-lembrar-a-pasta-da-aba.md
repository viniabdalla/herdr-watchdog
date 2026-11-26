---
number: 26
title: "Trocar e lembrar a pasta da aba"
state: open
labels: [ready-for-agent]
url: https://github.com/viniabdalla/herdr-watchdog/issues/26
parent: 25
blocked_by: []
updated: 2026-11-25
---

## Spec

#25 · itens 1, 2 e 4, aceites (a), (b) e (c).

## Entrega

Na aba que acompanha a pasta A, o usuário abre **Trocar pasta** no Tasks, escolhe a worktree B e passa a acompanhar B nos quatro painéis já abertos. A escolha pode ser retomada depois de reabrir o Watchdog e desfeita pela mesma lista.

## Aceite

- [ ] A lista contém as worktrees do repositório do Tasks, inclusive a original, e identifica a atual.
- [ ] Ao escolher B, o Tasks passa a ler o TODO de B e Progress, Artifacts e Yazi passam a acompanhar B. Os quatro conservam os mesmos panes.
- [ ] Reabrir o Watchdog recupera B. Selecionar A na mesma lista traz os quatro painéis de volta.
- [ ] Quando a troca é recusada, o Tasks informa na tela o motivo e o próximo passo.
- [ ] Demonstrar o percurso com duas worktrees e uma segunda aba em recursos isolados. Conferir que os painéis da outra aba e o state.db compartilhado ficam intactos.

## Dependências

Pode começar imediatamente.
