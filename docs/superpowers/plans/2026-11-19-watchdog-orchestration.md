# Watchdog orchestration port implementation plan

**Goal:** Bring Left Undone's fresh-worker dispatch workflow into Watchdog without changing Left Undone.
**Architecture:** Adapt launch-time briefs, provider selection, grouped dispatch and planning to Watchdog-owned run records, isolated worktrees and review gates. Preserve existing ledgers and the current identity dependency. Gossip receives no new features.
**Tech Stack:** Python standard library, Herdr, Git, Codex and Claude CLIs.
**Spec:** docs/merge-brainstorm-2026-11-19.md, overridden by the user's scope decisions in this conversation: Watchdog only; Left Undone intact; port orchestration into Watchdog; freeze Gossip.

## Global constraints
- No writes to Left Undone code, installation or state.
- Preserve unrelated working changes and all old run records.
- Native reports remain authenticated to the exact frontend; no pane injection or automatic retry of uncertain launches.
- TODO completion requires explicit acceptance; planning never completes implementation tasks.
- Existing LU identity dependency remains unchanged.
- Decisions not answered by the user remain pending; do not interpret this port as approval of the entire brainstorm.

## Tasks
1. Fresh single executor: request/template/launcher/UI, preserving existing-executor compatibility and leader review. Verify real temporary Git worktrees, one worker, no QA, no duplicate launch and stale/dirty rejection.
2. Provider launch: port Codex/Claude launch choices and launch-time contract delivery; authenticate bridge reports and keep account isolation. Verify provider commands, wrong identities, no Claude queue injection and interrupted delivery.
3. Together/Separate and Plan: port grouping and native planning, keep plan outputs separate from committed implementation evidence. Verify selection mapping, no automatic TODO completion, plan failures and reports.
4. Document scope and frozen Gossip; verify CLI, UI, regression suite and fresh review of the complete change. Leave unrelated migration decisions pending.

## Review focus
- Old single/team and Gossip ledgers retain their original semantics.
- Interrupted launch cannot create duplicate actors or manufacture a receipt.
- Claude reports require real process ancestry, not an environment claim alone.
- A plan or partial grouped result cannot approve implementation.
- Existing uncommitted Agents pane work survives integration.
