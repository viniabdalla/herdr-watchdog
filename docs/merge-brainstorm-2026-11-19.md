# Brainstorm response: merging Left Undone, Herdr Watchdog and the Agent Handoff Protocol

## Approved scope correction — 2026-11-19

Vini narrowed execution in the implementation conversation:
- Make changes **only in Watchdog**. Leave Left Undone intact for another situation.
- **Bring/adapt Left Undone orchestration into Watchdog**, rather than making Watchdog invoke the LU dispatcher.
- **Freeze Gossip**: no new features or integrations; preserve existing ledgers and compatibility.

This supersedes the proposed LU-as-Inbox product merge and all steps that would edit LU, retire its buttons, change its identity facade, promote/migrate its items, or merge its curator/state. The existing read-only LU identity dependency remains unchanged.

The authorized implementation ports fresh Codex/Claude workers, leader-prepared launch briefs, Separate/Together selection and native planning into Watchdog's run ledger and isolated worktrees. Existing exact-candidate review and explicit TODO acceptance remain. See [implementation plan](superpowers/plans/2026-11-19-watchdog-orchestration.md).

The remaining product choices (curator policy, handoff fallback, context thresholds/limit, human decision policy and Telegram timing) were **not** approved by the scope correction. Their recommendations below remain proposals. The original text below is retained as background, not as authorization to change LU.

## Context

The brief (`omarchy2:~/Downloads/brainstorm-3-way-merge.md`) asks for a brainstorm, not code. It wants options, trade-offs and one recommended direction for turning three separately built pieces into one system:
- **Left Undone (LU)**, the tool in heaviest daily use
- **Herdr Watchdog (WD)**, the newer control room
- **Agent Handoff Protocol**, a design document with no code

Inputs read: the protocol (from omarchy2), the LU README, CLAUDE.md, TODO.md and module outlines, and the WD README, TODO, concept note, mission-control, leader-handoff, native-transport and `bindings.py`. I also read the uncommitted agents-pane spec and Hermes `orquestracao.md`.

Two facts the brief does not mention change the picture:
1. **WD has already ported LU's agents monitor** (`watchdog_app/agents_ui.py`, `agent_usage.py`, plus the uncommitted spec `docs/superpowers/specs/2026-11-19-agents-pane-design.md`). The rule it used was "port the code, don't import LU's UI or DB". That is the merge pattern already in practice.
2. **WD already queues worker reports in a durable store before it notifies the leader** (native-transport), and `mission handoff-adopt` can already move a live run to a new leader while the worker and QA keep running. So most of the protocol's "drain" step is already built. It just isn't connected to Clean sessions.

The original brainstorm was initially saved without code changes. The approved scope correction above governs the subsequent implementation.

---

## 1. Recommended architecture (5.1)

**Recommendation: A. Layered**, with one adjustment: LU stays a separate install, as the inbox, until the decisions below are made.

| | A. Layered (recommended) | B. One app | C. Two apps + contract |
|---|---|---|---|
| LU becomes | Identity engine + capture inbox panel | Modules inside WD | Unchanged, minus duplicate features |
| WD becomes | The product: cockpit, Mission Control, handoffs, decisions | The whole thing | Unchanged |
| Deleted | LU dispatch `0`/`P`, LU `H`, LU `M`, `.left-undone/tasks.md` (each after WD reaches parity) | Same, plus LU's separate install/state | Only whichever duplicate loses |
| Migration risk | Low: each step is additive | High: two daily tools change at once, and LU state has to be merged | Lowest, but the duplication stays |
| What users see | One command (`watchdog`). LU appears as the "Inbox" pane | Same | Two tools that overlap |

- **Real-world basis.** A shared library plus a product built on it, for example libgit2 under GitHub Desktop. Also GTD's *capture inbox → processed project list* (David Allen), which is exactly LU's raw items being promoted into TODO.md.
- **Why not B now.** Both apps are in daily use, and LU's collector and curator are mature. Merging the databases gains nothing the user can see.
- **Runner-up.** B as a *later packaging step*: one installer that installs both plugins, once A has stabilized.
- **Why not C.** It locks in the overlap the brief wants removed.

**For Vini, in plain words:** Left Undone becomes the notepad that listens to the conversation and writes down everything that was promised. Watchdog becomes the control room: it holds the official task list, sends work to agents, checks the result and hands the leader's job to a fresh session. You open one thing (`watchdog`), and the notepad is one of its panes. The old buttons in Left Undone that send work out or hand off the session are switched off only after Watchdog does the same job, Claude included.

---

## 2. Topic by topic (5.2–5.10)

### 5.2 One task source of truth
- **Options.**
  - (a) TODO.md v1 only
  - (b) a ledger outside the repo only, as the protocol proposes
  - (c) **three layers, each with one job** (recommended)
- **Recommendation.** Each layer has one job:
  - **TODO.md v1 is the backlog.** It is human-facing, versioned with the code and written only by the leader or WD's locked writer, on the main checkout.
  - **The run ledger is the execution state.** It changes often and stays outside git.
  - **LU items are the capture inbox.** They are per conversation and disposable.

  LU gets a **Promote** action that writes a complete v1 task into TODO.md. It uses `Origem: pedido-humano` when the item has a user-quote evidence passage, and `sugestao-agente` otherwise.
- **`.left-undone/tasks.md`** is retired for projects that use `watchdog_todo: 1`. A one-time import brings its open items into TODO.md as `legado-nao-confirmado`. Projects without v1 keep tasks.md.
- **Why the protocol's worry doesn't apply.** Its objection to a board in the repo was that each worktree diverges and agents hit merge conflicts. WD avoids this already: workers never write TODO.md, and runs pin selected task blocks instead of the whole file.
- **Real-world basis.** A ROADMAP/TODO file versioned with the code (git-todo). CI run history kept outside the repo (GitHub Actions). A GTD inbox.

### 5.3 One dispatch system
- **Recommendation.** Mission Control is the one dispatcher. LU's `0`/`P` first becomes a shortcut that queues a Mission Control request when WD is installed, and is retired after that.
- **What Mission Control must gain from LU first:**
  1. **Fresh-executor creation in single mode.** Today "Para um agente" needs an existing idle executor in a clean linked worktree, which is the friction LU doesn't have. The fix is to reuse team mode's launcher without QA.
  2. **Claude workers.** Fresh-actor-per-task means the brief can be **delivered at launch** as the initial prompt, and reports go through the `mission report` CLI, which works for any agent. Only *follow-ups* need a thread-addressed transport. Until one exists, a follow-up for a Claude worker becomes a new attempt with a fresh worker at `worker_head`. **(adaptation)**: it relies on the fresh-actor rule, not on a real-world precedent.
  3. **Together.** This becomes one contract covering several TODO IDs as one logical task. Real-world basis: one PR that closes several issues.
  4. **Plan mode.** This becomes a "plan contract" whose result is a plan report and no commits; the leader turns it into implementation contracts. Real-world basis: a spike or design doc before implementation.
  5. **Model and effort chosen by the leader.** This already exists in briefs. Keep LU's guidance: the weakest model that works for execution, the strongest for planning.
- **Worktrees.** Use them everywhere. Same-worktree workers are the protocol's "worktree collision" failure mode. Real-world basis: a feature branch per developer, with CI checkouts in their own workspace.

### 5.4 One leader handoff
Map of the protocol's 12 steps onto Clean sessions (CS):

| # | Protocol step | CS today | Gap or action |
|---|---|---|---|
| 1 | Trigger | Manual `c` | Context threshold suggests it (see 5.5) |
| 2 | Cordon/drain | Refuses active runs | **Gap.** Reports are already durable, so: stop dispatching, pause forwarding, run `handoff-adopt` per active run |
| 3 | Checkpoint | TODO reconcile + ai-memory handoff + pushed commit | ✅ stronger than the protocol (pushed and verified) |
| 4 | Spawn fresh successor | ✅ split + fresh Codex frontend | Claude successor still missing (LU `H` has one) |
| 5 | Reconciliation | Git/identity gates | ✅ |
| 6 | Q&A | ❌ | Optional; the predecessor stays alive until release, so it is possible |
| 7 | Read-back | Receipt confirms token, digest, memory | **Add a `synthesis` field** to the receipt: mission, priorities, active runs, pending decisions, next action |
| 8 | Confirmation | Release reply | Predecessor confirms or corrects the synthesis in its release |
| 9 | Explicit transfer | ✅ activation message | |
| 10 | Announce to workers | ❌ | **Not needed. (adaptation)** Workers report to the host bridge, which routes to whoever is the current main, the way callers dial a dispatch centre's number rather than a person. Already true for adopted runs |
| 11 | Resume | ✅ | |
| 12 | Heightened watch | ❌ | Cheap to add: for the first N actions the successor re-verifies state before acting (FAA AM08-16) |

- **Pick.** CS is the one implementation. LU `H` delegates to it when WD is installed, then retires once CS supports Claude leaders. LU's plug-and-play idea stays: name the project's handoff skill only when one is installed.
- **ai-memory.** Keep it as the default and add a file fallback (an `ORCHESTRATOR_HANDOFF.md` capsule in WD state) for colleagues who don't have ai-memory. This is a product decision: **DEC-004**.

### 5.5 Worker context and mid-task handoff
- **Today.** Codex auto-compacts. If a worker stops reporting, the run goes **Stalled** after 20 minutes. There is no worker handoff.
- **Recommendation.** No new worker-handoff machinery. Build it from existing pieces:
  - At **≥70%** worker context, WD asks the worker to commit a `wip:` checkpoint and send a `blocked` report with a HANDOFF-style summary.
  - The leader then dispatches a **new attempt to a fresh executor at that commit**, which is the existing follow-up path plus the `worker_head` rule.
  - Read-back is the new worker's first `working` report.
  - Real-world basis: shift change with handoff notes, and the protocol's own §4.4–4.6 mapped onto existing primitives.
- **Where it lives.** The Agents pane, which is already ported. It shows a bar per agent. At 60% the bar turns yellow and notes it; at 70% the action above starts.
  - For the leader, 60% suggests Clean sessions. Starting it automatically is **DEC-005**, because Clean sessions pushes.
  - Which limit applies (500k or the model's real window) is **DEC-006**. Vini deferred this earlier.

### 5.6 One curator
- **Recommendation.** One engine (LU's evidence-checked curator, with one prompt set) and **two policies by destination**:
  - **Inbox (LU items).** Auto-apply with evidence. It is private and cheap to undo.
  - **Backlog (TODO.md).** Propose only, with **one key to apply every proposal that has evidence**, so it doesn't cost Vini attention item by item.

  A real failure supports this split: the curator closed "check SATA errors" while the error count was rising (LU TODO). Shared state shouldn't be auto-closed.
- **Model.** Use the watched agent's own CLI and account: gpt-6-luna for Codex, Haiku for Claude, as LU does today. WD currently always uses Codex.
- **Real-world basis.** A mail filter auto-files your own inbox; a bookkeeper proposes ledger entries and the owner signs them.
- The batching policy is **DEC-003**.

### 5.7 State, ledger and event log
- **Keep two state dirs, split by owner.** LU keeps capture state; WD keeps runs, clean-sessions, backups and decisions. Merging the databases would break the "both keep working" rule and gives nothing the user can see.
- **No new unified event log.** The append-only sources already exist: run events, durable intents, `curation_changes`, `panel_organization`, clean-session records and TODO history blocks. Add a **read-only Timeline view** that merges them when it reads. Real-world basis: log aggregation (ELK) over services that each own their log.
- **XDG.** The spec allows both readings: `state` is meant for history, while `data` is meant for important files. Leave everything where it is, since moving it is a migration risk for no gain. Add `watchdog backup`/export for the run ledger, because Vini says to keep it. This is a technical call, so it is not listed as a decision.

### 5.8 The human interface
- **Decisions queue.** Put it at the **top of WD Tasks**, as a section that only appears when it is non-empty. It collects:
  - runs in "Needs your decision"
  - LU dispatches in `question` or `blocked` (read-only)
  - curator "For you" items (`VOCÊ ·`)
  - blocked Clean-sessions operations

  The leader writes each one in DECISION_REQUEST format. WD stores it (a `decisions` record in WD state), Vini answers with one letter, and WD queues the answer to the exact leader thread. Non-urgent items are batched. Real-world basis: an executive's decision memo plus a batched inbox (the protocol's §4.8).
- **Workers never contact the human.** The one real exception is approval prompts in worker tabs; workers already run with approvals disabled. Flag any prompt that does appear as "Needs your decision" instead of expecting Vini to notice the tab. **DEC-007** asks whether to forbid direct contact outright.
- **Plain-language summaries.**
  - Every field Vini sees has a plain `Resumo`; technical text goes in `Execução`.
  - Summaries are written by whoever produces the event: the leader writes run and decision summaries, and the curator model writes artifact summaries (which are still pending).
  - WD renders these from stored text and never translates them with a model while drawing the screen.

### 5.9 Conventions for target repos
- **`watchdog init`** creates or validates:
  1. TODO.md v1, using the existing migrate flow when a file already exists
  2. a **managed block** in AGENTS.md with the rules
  3. CLAUDE.md importing `@AGENTS.md`
  4. `.ai-memory.toml` if ai-memory is used
  5. `.gitignore` entries

  It shows a diff before writing. Skip the PR template and ADRs for now: Vini doesn't review PRs. Leader decisions go in TODO `Motivo` or the decisions queue.
- **One worktree rule.** Managed worktrees live under the run directory in WD state, which is already how it works. `.claude/worktrees/` and sibling folders are for ad-hoc work only and are never managed. Real-world basis: CI runners check out code in their own workspace.

### 5.10 Hermes
- **Outside the core.** Add one integration point: a **notification hook**, a command WD runs when a new DECISION_REQUEST appears or a run stalls, so Hermes can send it to Telegram. Answers still come back through WD.
- Hermes' `orquestracao.md` is a manual version of this same protocol: briefs, reply files and gates. It can move onto WD once Mission Control supports non-Codex workers. Real-world basis: PagerDuty and webhook integrations.
- Timing is **DEC-008**.

---

## 3. What happens to each duplicated feature

| Feature | Fate | Lives in |
|---|---|---|
| Identity engine | **Keep**, behind a versioned facade | LU (`left_undone/runtime.py`) |
| Transcript collection and curation | **Keep**; one engine with two policies | LU engine; WD calls it for TODO proposals |
| Per-conversation items | **Keep** as the inbox | LU |
| `.left-undone/tasks.md` | **Retire** for v1 projects; one-time import | — |
| TODO.md v1 | **Keep** as the backlog | WD |
| WD curator (Codex-only) | **Merge** into the LU engine | — |
| LU dispatch `0`/`P` | **Retire** after Mission Control gains fresh-executor, Claude, Together and Plan | WD Mission Control |
| Mission Control single/team | **Keep** | WD |
| LU Done/Not-done review | **Merge** into leader review on the exact SHA | WD |
| LU `H` | **Retire** after Clean sessions supports Claude | WD Clean sessions |
| Clean sessions | **Keep**, plus drain, read-back and heightened watch | WD |
| LU `M` monitor | **Retire** (already ported) | WD Agents pane |
| Context thresholds | **New** | WD Agents pane |
| Two state dirs | **Keep split**, plus a Timeline view and a backup command | Both |
| `question` / Needs decision | **Merge** into the Decisions queue | WD Tasks |
| LU `1` send / `V` review | **Keep** (inbox actions) | LU |
| agent-gossip transport + Agent Graph roles | **Retire for new runs** (already the default); legacy runs stay readable and export-only; drop "show Gossip channels" from the Agents pane task | WD `mission_transport.py` legacy adapter only |

**On agent-gossip.** It is not part of the merged system. WD already switched new runs to the native Codex queue plus durable local reports; the native path needs neither `agent-gossip` nor Agent Graph. Gossip survives only as an opt-in `--transport gossip` adapter and for the old ledgers that used it, which must remain readable. Recommendation: no new work on that adapter. Remove the "show verified Gossip channels" line from the Agents pane task. Delete the adapter itself only once no unfinished run uses it, and keep old ledgers export-only. **(DEC-009)** For Claude parity (5.3) the answer is launch-time brief plus bridge reports, not Gossip.

## 4. Migration path (smallest useful step first; each step leaves both apps working)

0. **Docs only.** Update the protocol (§6 below) and freeze new features in LU dispatch and `H`; bug fixes only.
1. **Versioned identity facade** in LU (`engine_api.VERSION`). WD checks the version and fails clearly if it doesn't match.
2. **Decisions section in WD Tasks**, read-only at first, fed by runs and LU dispatch states.
3. **LU Promote → TODO.md**: LU calls `watchdog todo` through the CLI when it is installed, so LU never imports WD. Also the one-time import of tasks.md.
4. **Fresh-executor launch in single mode.**
5. **Claude workers**: brief at launch, reports through the bridge, follow-up as a new attempt.
6. **Plan contracts and Together bundles.**
7. **LU `0`/`P` delegates to Mission Control** when WD is present. Retire after a period of real use.
8. **Clean sessions**: drain through `handoff-adopt`, read-back synthesis, heightened watch, then a Claude leader. After that, LU `H` delegates to it.
9. **Context threshold actions** in Agents.
10. **`watchdog init`.**
11. **Timeline view and `watchdog backup`.**
12. **Unified curator policies, and the Hermes notification hook.**

Existing run ledgers, TODO migrations, LU state and dispatch rows are never rewritten. Old runs keep their own rules, as WD already guarantees.

## 5. Decisions only Vini can make

## DEC-001 — Shape of the product
**Context:** Watchdog becomes the main product and Left Undone becomes its "notepad" pane. The question is whether they stay two installs or become one now.
**Options:** A) Two installs, one command, with Left Undone as Watchdog's Inbox pane → low risk, nothing breaks during the change · B) Merge into one app now → one install sooner, but both daily tools change at once and Left Undone's saved data has to be moved
**Recommendation:** A, and package them as one installer later.
**Answer with:** A, B, or a short instruction.

## DEC-002 — Switching off the old Left Undone buttons
**Context:** Left Undone's "send to sub-agent" (0/P) and "new session" (H) do the same job as Watchdog's. Keeping both means two ways to do one thing.
**Options:** A) Switch them off once Watchdog does the same job, Claude included → one way to work · B) Keep both for good → more to maintain, and more chances of doing it the "wrong" way
**Recommendation:** A.
**Answer with:** A, B, or a short instruction.

## DEC-003 — How the official task list gets updated
**Context:** The AI suggests "this is done" or "this is new" for TODO.md, always with a quote as evidence. Once it closed a task by mistake.
**Options:** A) Show suggestions and apply them all with one key → one key press per review · B) Confirm each one → more clicks · C) Apply automatically → no attention needed, but mistakes go straight into the official list
**Recommendation:** A.
**Answer with:** A, B, C, or a short instruction.

## DEC-004 — Is ai-memory required for a new leader session?
**Context:** Today the leader's handoff to a fresh session needs ai-memory. Colleagues may not have it installed.
**Options:** A) Use ai-memory when present, otherwise a local handoff file → it works for everyone · B) Always require ai-memory → one way, but colleagues must install it
**Recommendation:** A.
**Answer with:** A, B, or a short instruction.

## DEC-005 — A full leader starts its own fresh session
**Context:** When the leader's memory gets full (around 60%), a fresh session could take over. That step commits and pushes the TODO and the leader's own files.
**Options:** A) Just warn me in the panel → I press `c` · B) Start it automatically → no attention needed, but a push happens without my ok
**Recommendation:** A for now, B after a few weeks without surprises.
**Answer with:** A, B, or a short instruction.

## DEC-006 — How full counts as "full"
**Context:** The context bar needs a limit. You chose 500k tokens earlier and left the final decision for later.
**Options:** A) 500k for every agent → simple and the same everywhere · B) Each model's real limit → more accurate, but the bars aren't comparable
**Recommendation:** A, adjustable per agent.
**Answer with:** A, B, or a number.

## DEC-007 — Can workers talk to me directly?
**Context:** Today you can answer a worker in its own tab. The protocol says everything should go through the leader.
**Options:** A) Only through the leader; anything a worker needs from me shows up as a decision → less attention, one place to look · B) Keep the direct tab → faster for small questions, but things get lost in tabs
**Recommendation:** A.
**Answer with:** A, B, or a short instruction.

## DEC-008 — Hermes sending decisions to Telegram
**Context:** Watchdog can run a command whenever it needs you, so Hermes can forward it to Telegram.
**Options:** A) Later, after the decisions queue works in the panel → less to build now · B) Now → you get alerts away from the PC sooner
**Recommendation:** A.
**Answer with:** A, B, or a short instruction.

## DEC-009 — Remove the old agent-gossip messaging
**Context:** Watchdog used to pass messages between agents through agent-gossip. New runs already use Codex's own message queue; Gossip is kept only as an opt-in option and to read old runs.
**Options:** A) Freeze it now; delete it once no unfinished run uses it, keeping old records readable → less code to maintain · B) Keep it as an option for good → it can still be used later, but it costs ongoing maintenance and tests
**Recommendation:** A.
**Answer with:** A, B, or a short instruction.

## 6. Proposed changes to `agent-handoff-protocol.md`
- **§1, add:** a fresh actor per task and a fresh reviewer per review. "The best handoff is no handoff" becomes a rule, not just a preference.
- **§4.1 / 4.1b:**
  - The board is **TODO.md v1** in the repo (backlog), written only by the leader or backend on the main checkout. The coordination ledger is the WD run ledger plus decisions.
  - Add a fixed UUID and origin labels (`pedido-humano`, `sugestao-agente`, `legado-nao-confirmado`).
  - Workers never write the board.
- **§4.2:** thresholds are actions in the Agents pane. A worker at 70% does a wip commit, then a `blocked` report, then a new attempt with a fresh executor at that commit.
- **§4.3 / 5b, brief:** the contract has `allowed_files`, `acceptance`, `tests` and `dependencies`, plus an **explicit model and effort per actor** (the weakest that works for execution, the strongest for planning).
- **§4.7:**
  - Drain means durable reports plus per-run adoption; step 10 (announce) is replaced by routing through the host bridge.
  - Add a pushed, verified checkpoint, an **explicit predecessor release**, exit and resume checks, and **side-effect intents saved before any change**.
  - Never resend blindly.
- **§4.9:** QA runs on the **exact full candidate SHA and result version**. Newer evidence invalidates earlier reviews. Approve integrates and pushes; a production deploy is still a human decision.
- **§4 new, run states:** Preparing, Running, Verifying, Waiting for approval, Needs your decision, **Stalled** (no activity for 20 minutes), Done, Closed.
- **§5e:** completion needs **textual evidence or commits plus tests**. A process exit, heartbeat, "done" text or artifact alone never completes a task.
- **§8, open questions:** close the questions on context measurement (transcript token counts, already ported) and on the decision channel (WD Tasks first, a Hermes hook later).

## Verification (of this brainstorm)
- Every claim about current behaviour is traceable to the files read: the LU README and CLAUDE.md; the WD README, mission-control, leader-handoff, native-transport and `bindings.py`; and the agents-pane spec.
- After you approve, check that the saved file is identical to this plan and that the omarchy2 copy exists, using `ssh … ls ~/Downloads`.
- Then record the task with `activity_client.py` and confirm it shows `"verified": true`.
