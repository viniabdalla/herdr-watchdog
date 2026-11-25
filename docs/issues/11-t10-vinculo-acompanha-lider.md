---
number: 11
title: "T10 — Vínculo que acompanha o líder"
state: closed
labels: ["ready-for-agent"]
url: https://github.com/viniabdalla/herdr-watchdog/issues/11
parent: 1
blocked_by: [8]
updated: 2026-11-25
---

## Parent

#1

## What to build

Depois de um /clear no mesmo pane e no mesmo harness, o painel segue a sessão nova sem aviso. Se o harness do líder mudar, os botões trocam de prefixo e aparece um aviso curto. A tecla Religar lista os panes com agente do workspace para ligar o painel a outro líder. Depois de um /clear, a prévia oferece reenviar a meta do grupo.

## Acceptance criteria

- [ ] /clear no Claude mantém o vínculo sem aviso.
- [ ] /clear no Codex mantém o vínculo sem aviso.
- [ ] Troca de harness troca os prefixos e mostra o aviso.
- [ ] Religar liga o painel ao pane escolhido.
- [ ] Outro pane ou sessão antiga ainda viva não é seguido sozinho.
- [ ] Reenviar a meta digita a meta do grupo atual.


## Comentários

### 2026-11-25T15:48:03Z · viniabdalla

O vínculo segue a sessão nova no mesmo pane e preserva a escolha explícita ao trocar de pane. Religar permite a ida e volta Claude–Codex–Claude. O reenvio da meta respeita os modos do grupo e exige confirmação. O ciclo de retorno foi validado com Store real e Herdr falso.

Commit do executor `e3df91e`, integrado em `d4f87c1`. A suíte executou 614 testes em cada modo de controles, com 7 ignorados e nenhuma falha.
