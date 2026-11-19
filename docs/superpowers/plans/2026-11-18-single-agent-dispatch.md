# Single-agent dispatch Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline. Preserve existing actors; no delegation.

**Goal:** Despachar uma tarefa a um executor existente com revisão verificável pelo líder.
**Architecture:** Explicit single/team mode in the existing native ledger; attach the existing host broker to the selected worker, reuse dispatch/results, and gate approval through a leader review bound to candidate and result version. Team remains the default.
**Tech Stack:** Python standard library, unittest, Git, existing Herdr native identity/queue boundary.
**Spec:** docs/superpowers/specs/2026-11-18-single-agent-dispatch-design.md

## Global Constraints

- Biblioteca padrão; Left Undone somente leitura; nunca parar Herdr.
- Nenhuma conversa ou painel existente é reiniciado, encerrado ou substituído.
- Uma tarefa lógica por executor; envio simples e equipe com QA preservados.
- Nenhum merge/push real nem conclusão automática de TODO durante desenvolvimento.

## Review Focus

- Destinatário ocupado, movido ou com conta/thread substituídos entre seleção e lançamento: rejeitar.
- Worktree de outro repo, branch principal compartilhada, head diferente ou arquivos sujos: rejeitar.
- Interrupção entre intenção e recibo do bridge/queue: reter evidência e não reenviar.
- Revisão anterior após follow-up, relatório novo ou troca de líder: não aprovar.
- Teclado/mouse, painel estreito e ausência de executor elegível: seleção explícita e cancelamento sem efeitos.

### Task 1: Native single-executor contract and leader review

**Files:** create watchdog_app/mission_single.py and tests/test_mission_single.py; modify mission.py, mission_launch.py, mission_native.py, mission_transport.py, mission_cli.py, mission_merge.py.
**Interfaces:** request(..., mode='team', executor=None); single.validate_executor(repo, main, executor, base=None); single.launch_existing(store, run, brief); single.review(store, identity, candidate, evidence, confirmed=False); single.review_valid(run, candidate).

- [x] Write failing tests for one-worker mode, recipient/worktree checks, no new actor/pane, uncertainty, leader review evidence/version/candidate/identity, and team QA gate.
- [x] Run `python3 -B -m unittest discover -s tests -p test_mission_single.py -q`; confirm feature failures.
- [x] Implement explicit single mode; keep default team and existing transport reducers. Require verified clean worker head and full result commit ancestry for leader review/approval.
- [x] Run single tests and existing mission tests; confirm passing.

### Task 2: Dispatch selection, confirmation and progress

**Files:** modify tasks_ui.py, progress_ui.py, README.md; create tests/test_single_dispatch_ui.py.
**Interfaces:** consumes Task 1 request and executor choices; menu item identities drive both keyboard and mouse; `mission leader-review --candidate SHA --file JSON --confirm` stores evidence.

- [x] Write failing tests for menu, executor panel selection, confirmation target, cancel, unavailable/busy/stale recipient, simple send preservation and progress review state.
- [x] Run targeted tests; confirm missing behavior failures.
- [x] Implement Despachar options, verified executor list and confirmation, and Portuguese single-mode progress details. Document review JSON and restrictions.
- [x] Run UI tests, full `python3 -B -m unittest discover -s tests -q`, review diff and demonstrate UI in disposable PTY.
- [x] Preserve task open pending user acceptance; report evidence and any live limitations. Record operational history once with verification.

## Evidências da execução

2026-11-18: baseline de 363 testes, 7 opt-in ignorados; suíte final de 385 testes, 7 opt-in ignorados, sem falhas. Testes novos observados em RED antes da implementação e em GREEN após as mudanças. Menu, seleção, confirmação e cancelamento exercitados em PTY real; Git temporário comprovou recusa de aprovação sem revisão e integração do candidato exato após revisão registrada. Revisão do código pelo próprio líder, preservando a restrição de não criar atores; não equivale a auditoria independente. Nenhuma tarefa real foi lançada em um modelo e nenhum TODO foi marcado concluído.

Interface aplicada ao checkout principal e painéis Tarefas/Progresso recarregados nos mesmos terminais. Captura nativa confirmou menu e mensagem de ausência de executor elegível; a seleção foi cancelada e removida, sem solicitar execução. Ajuste de foco conferido contra a CLI Herdr instalada (`agent focus`); suíte final repetida: 385 testes, sem falhas, 7 opt-in ignorados.
