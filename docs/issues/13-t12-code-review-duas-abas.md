---
number: 13
title: "T12 — Code review em duas abas"
state: closed
labels: ["ready-for-agent"]
url: https://github.com/viniabdalla/herdr-watchdog/issues/13
parent: 1
blocked_by: [8, 9]
updated: 2026-11-25
---

## Parent

#1

## What to build

O botão code-review digita a chamada curta com a base anotada e a branch de integração. O padrão do dispatch descreve a revisão: aba Code Review com dois revisores novos e visíveis abertos pelo kit, contratos-modelo de cada eixo, espera pelos dois avisos, apresentação lado a lado, e correção num único executor novo, numa aba nova, só depois do ok do Vini; depois /retro e teste do Vini.

## Acceptance criteria

- [ ] O botão sai com a base do grupo e a branch de integração, editáveis.
- [ ] O padrão traz os contratos-modelo de Standards e Spec.
- [ ] Os relatórios ficam na pasta de execução do projeto.
- [ ] A correção abre numa aba nova só depois do ok.


## Comentários

### 2026-11-25T15:57:06Z · viniabdalla

A prévia do code review traz o intervalo editável do grupo. O kit fornece contratos de leitura Standards e Spec com hashes fixos e relatórios distintos. O Dispatch exige os dois relatórios e o ok do Vini antes do executor de correção em aba nova.

Commit do executor `6786b9c`, integrado em `23fe38f`. A suíte executou 627 testes em cada modo de controles, com 7 ignorados e nenhuma falha.
