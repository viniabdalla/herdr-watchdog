# Agents Pane Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans; execução local autorizada pelo usuário, preservando atores existentes.

**Goal:** Abrir o monitor de agentes pelo Tasks e por `watchdog pane [agents]`.
**Architecture:** Portar leitores/medidor do Left Undone e adaptar a fonte para os runs do Watchdog. Um abridor comum conserva binding, estado e panes existentes.
**Tech Stack:** Python, curses, unittest, Herdr CLI.
**Spec:** docs/superpowers/specs/2026-11-19-agents-pane-design.md

## Global Constraints

Sem novos agentes, sem alterações no Left Undone, sem conclusão automática de tarefas. Reutilização exige identidade e processo do painel correspondentes. Comandos incertos não são repetidos automaticamente.

## Review Focus

- Pane fechado pode ser recriado; pane substituído ou ocupado deve ser recusado.
- Sessão diferente no mesmo pane não recebe telemetria da sessão anterior.
- Runs de outra sessão e runs legados permanecem fora da coordenação.
- Transcript parcial/rotacionado não duplica tokens nem quebra atualização.
- Seletor cancelado não cria recursos; reabrir não duplica painel.

### Task 1: Monitor e abertura

**Files:** watchdog_app/agent_usage.py, watchdog_app/agents_ui.py, watchdog_app/panes.py, watchdog_app/app.py, watchdog_app/tasks_ui.py, watchdog_app/layouts.py; tests/test_agents.py, tests/test_panes.py, tests/test_tasks_ui.py; README.md.

- [x] Testar leitores incrementais, sessão trocada, associação de runs, seletor e reabertura/recusa de pane ocupado.
- [x] Executar testes e confirmar falha por funcionalidade ausente.
- [x] Portar leitores e UI para dados locais; adicionar abertura de painel, CLI e botão.
- [x] Executar testes pertinentes e suíte completa.
- [x] Revisar diff e verificar abertura/reabertura real no Herdr, preservando IDs existentes; registrar evidências.

Aprovação de implementação já dada pelo usuário ("isso"); seguir sem nova rodada de permissão. Não fazer commit/push nesta tarefa.

## Execution evidence

Implementação feita nesta sessão, sem criar agentes nem mudar de checkout. Leitores incrementais e medidor portados do Left Undone; associação dos atores e abertura são locais ao Watchdog. A infraestrutura de identidade existente continua usando o motor compartilhado.

Testes reproduziram ausência dos módulos, foco incorreto de um pane comum e reutilização indevida de outro binding antes das correções. A verificação real criou somente wD:p23; os 7 panes/terminais anteriores foram preservados. CLI direto e atalho m reutilizaram o mesmo pane. Capturas textuais e snapshots estão em docs/evidence/2026-11-19-agents-pane/ (ignorados no Git).

Revisão local: abertura de pane comum usa o método nativo pane.focus; monitor exige binding, sessão e terminal correspondentes; segue apenas redirects correlacionados de Clean sessions. Nenhum TODO ou run foi alterado. As 12 tarefas anteriores continuam abertas.

Verificação final: `python3 -m unittest discover -s tests -q` — 400 testes, sem falhas, 7 ignorados (58,913 s). `git diff --check` sem erros. CLI sem binding explícito, seletor cancelado e atalho m verificados no Herdr.
