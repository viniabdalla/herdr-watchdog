# Mission Control Pilot Implementation Plan

> For agentic workers: use superpowers:executing-plans to implement task by task.

**Goal:** Orchestrate selected TODO tasks in a visible execution tab and show
human-readable progress/blockers, then use the feature on Watchdog itself.
**Architecture:** Tasks requests coordination from the exact main Codex thread.
A Watchdog run ledger maps project/task snapshot, main identity, execution tab,
worker/QA branches/worktrees, native session identities and Gossip task IDs.
Use Agent Graph role instructions, Gossip directed task/result exchanges, native
Herdr terminals and exact-thread Codex inbox. Main receives compact reports.
**Tech Stack:** Python standard library; existing Herdr/Codex/Gossip/Agent Graph.
**Spec:** docs/superpowers/specs/2026-11-17-mission-control-pilot-design.md

## Global Constraints

- One new execution tab for all selected tasks, split into worker/QA terminals.
- English plain-language UI; color plus text, not technical-only status codes.
- Main coordinates; worker writes code and fixes; QA assesses exact candidate.
- Each agent has its own branch/worktree. Never merge target main automatically.
- Local Git/commits and the two Codex participants were approved on 2026-11-17.
- No remote creation/push. Preserve protected files, unrelated panes and services.
- All experiments use owned wd-test resources; production only verified rollout.
- TODO remains unchanged by dispatch; model proposals require confirmation.
- Do not change Left Undone state or program; do not alter global configuration.

## Review Focus

- Identity switches must fail closed; never use inherited pane IDs or focus.
- Interrupted launches must not duplicate tabs/worktrees or silently resend.
- Blocked tasks require concrete reasons; lost workers are unavailable, not Done.
- A worker result is awaiting review; only QA + main/user approval can finish.
- Task edits, dependent tasks and shared-file ownership require fresh contracts.

### Task 1: Build the launch and monitoring path (one executor)

**Files:** create focused modules under watchdog_app/ for run ledger, launch,
Gossip transport and Progress UI as needed; modify tasks_ui.py, app.py and panel
entrypoint; add tests under tests/ and update README. Do not edit protected files.
**Consumes:** Session.verify/dispatch, Snapshot, Herdr, state_root/atomic, graph
node instructions and agent-gossip CLI, all already available locally.
**Produces:** documented CLI to launch an approved run with an explicit brief,
report structured status/results/blockers, inspect runs and open execution tab;
Tasks Orchestrate control; Progress monitoring of the same stored run identities.
A request/brief/result carries stable run and task IDs, repo, base SHA, allowed
files, acceptance criteria, test commands, dependencies and return destination.
The main composes the brief; the launcher must not pretend it is an LLM planner.

- [ ] Write meaningful failing tests for confirmation, exact-main recipient,
  ledger transitions/stale selection, owner-checked resources, duplicate-launch
  prevention, blockers/results and loss of contact. Use foreign CLI boundaries.
- [ ] Implement the ledger and CLI lifecycle with bounded subprocesses/locks,
  explicit ownership, atomic persistence and no uncertain retries.
- [ ] Implement Gossip directed assignments/results. Verify correlation and
  idempotent delivery; bridge compact events to the exact main Codex thread.
  Integration must work without asking agents to read whole peer transcripts.
- [ ] Implement launch: verified main binding, clean committed base, task worker
  branch/worktree plus QA inspection worktree; one new tab with visible terminals.
  Use explicit approved participant list. Safe quoting of prompts and file paths.
- [ ] Load applicable Agent Graph role context; preserve the graph's no-target-
  merge and no-leader-code boundaries. No auto recruitment of unrelated peers.
- [ ] Add Tasks [Orchestrate] and confirmation; keep Send, Done and curator.
  Progress shows Ready to start, Working, Needs help, Checking the result, Done,
  task titles, reason/last report, agent and execution-tab navigation. Keep
  project progress distinct; no inferred completion from process exit alone.
- [ ] Run the existing suite and meaningful new tests. Native cases use wd-test;
  validate real Gossip result delivery in owned resources. Commit implementation.

### Task 2: Integrate and QA the complete feature

**Files:** executor commits; QA report in a local evidence file or Gossip artifact.
**Consumes:** exact immutable base and candidate head; acceptance criteria above.
**Produces:** independent verdict with reproducible findings at that head.

- [ ] Main checks commit scope and cleanly integrates into feature branch only.
- [ ] QA reviews exact candidate in its own worktree, runs relevant tests plus
  interruption/identity/blocker scenarios and returns evidence, not just approval.
- [ ] Executor fixes blockers; main integrates; QA rechecks the changed candidate.

### Task 3: Self-test through the actual Tasks control

**Existing project task:** Conversation picker: show account names beside pane
and session. Restrict this assignment to picker/CLI identity presentation and
focused tests; no auth secrets, account changes or global config writes.

- [ ] Roll out verified control/monitoring into owned existing Watchdog panels.
- [ ] Confirm Orchestrate for the real picker task, generate explicit brief and
  run the worker in the single new execution tab, with its isolated branch.
- [ ] Observe Working -> Checking the result; exercise a concrete blocker and
  a clarification/follow-up on the same task without changing scope or IDs.
- [ ] Integrate returned code into feature branch; QA tests exact assembled head.
- [ ] Show useful picker change and truthful visible status; preserve TODO until
  confirmed completion. Keep final main merge for Vini, no push or PR required.
