# Leader handoff / Clean sessions

Tasks now has **c / Clean sessions**, independent of task selection. It shows
this project, the full current native thread/account, and an editable scope:
configured push remote, current destination branch, exact owned files, explicitly
approved integration branches, dedicated Codex executable, model and effort.
Tab/Up/Down selects a field, Ctrl+U clears it, Enter reviews and **y** confirms.
The upstream supplies destination defaults; there is no guessed push destination.
Only `TODO.md` is authorized by default. Add other owned file paths explicitly;
branch integration defaults to none and supports fast-forward only.

Confirmation queues a precise request to the verified current leader. That
leader reconciles TODO honestly and must call the **actual ai-memory MCP
`memory_handoff_begin`** with a concise summary, questions, unfinished work and
next steps. The request supplies the exact tool/argument conventions and response
format. Semantic TODO reconciliation and memory save/accept are **leader
attestations**, not deterministic semantic checks or a new memory backend. Missing
ai-memory produces a visible blocker; a handwritten replacement file is not
memory transfer. The bounded continuation JSON is transport/checkpoint evidence
referencing that real handoff, never an independent memory service.

The backend verifies the preparation reply from **new completed assistant events**
in the pinned native history, then commits only authorized owned files, integrates
only the pinned approved branch heads and pushes to the explicit destination.
Unowned dirty/staged files, moved refs, non-fast-forward integration, changed
remotes or failed push stop the operation. It verifies the actual push URL's
remote SHA before recording the checkpoint. TODO completion is never inferred
from dispatch, file presence or a queue receipt.

At that checkpoint it performs the observed `Herdr().call('pane', 'split',
verified_leader.pane, '--direction', 'right', '--cwd', repo, '--no-focus')['pane']`
and runs a dedicated fresh Codex frontend. The wrapper uses the approved account,
executable/model/effort, removes inherited thread/auth/memory environment, and
restores its owned terminal with `TerminalLease`. Native full thread, account,
project, pane, terminal, PID/start and freshness claims are checked. Continuation
is queued through `bindings.engine().queue` to that exact full thread. Existing
actors and panes stay intact.

A queue receipt means delivery only. A correlated **completed native successor
reply** must confirm operation/token, checkpoint, continuation digest and actual
ai-memory handoff receipt (the exact hook-supplied handoff, or
`memory_handoff_list` followed by `memory_handoff_accept` for that ID). Then the
predecessor receives an explicit release request, replies with the exact
operation/checkpoint/successor and parks. Only after both real completed replies
and final idle/native/Git checks does Store relinquish old ownership and activate
the successor. Tasks and Progress follow the correlated Watchdog redirect in the
same terminals. Artifacts, Files/Yazi client and layout are retained; Left Undone
stays read-only. An activation message then tells the successor it may lead. The
existing **Orchestrate** action uses the successor's authoritative Session binding.
New Send/Orchestrate requests are serialized against pending/partial cleanup.

Tasks and Progress show `pending` (with the exact current stage), `blocked`,
`partial`, `received` and `released`. Side-effect intents are durable before Git,
Herdr, queue or ownership mutations. Duplicate or uncertain confirmations,
replaced history/identity, stale checkpoints and interrupted writes fail visibly.
A crash between Store writes leaves ownership unavailable rather than creating
two active coordinators. No failed queue, split, startup, push or rebind is
repeated automatically. Keep a panel open to advance the workflow; the other
panel can continue it if one closes. After closing both, reopen either panel.

Inspect retained evidence with:

```sh
watchdog clean-sessions inspect --operation OPERATION_UUID --state-dir WATCHDOG_STATE_ROOT
```

Evidence is under `WATCHDOG_STATE_ROOT/clean-sessions/`. A blocked/partial operation
requires operator inspection of its exact Git/queue/pane/ownership outcome;
there is deliberately no blind resume/resend or automatic claim removal. Do not
delete operation or purpose records to bypass an uncertain outcome.

This **project baton** flow refuses active native runs until their existing owner
has finished them. It does not silently rewrite a run's whole-TODO digest or
replace its coordinator. The separate native run preview/adopt API below retains
its existing safety checks. Historical Gossip ledgers (including the original
legacy run and digest) remain byte-untouched and export-only. A project baton is
not a native adoption of a legacy ledger. Later Run scope, Agents and Plan reader
work remain outside this feature.

Validation uses real temporary Git repositories/bare remotes, real Store/Session
and Tasks controls (including a curses PTY), with explicitly **simulated** model,
ai-memory replies, native registry/queue, frontend child and Herdr boundaries.
Tests cover UI request through receipt/release and existing Orchestrate routing,
owned commit/approved integration/push and failure injection without resend.
No production model sessions or leadership transfer were executed by these tests;
a live end-to-end demonstration with the actual ai-memory service and fresh
native frontend remains an operator acceptance step.

## Existing run capsule CLI

The independent CLI-first run handoff APIs below export bounded evidence and
adopt an already supplied fresh native main. They do not perform the project UI
workflow described above, create a frontend, or transfer panel ownership.

## Bounded continuation evidence

```sh
python3 /absolute/controller/watchdog mission handoff-export \
  --run RUN_UUID --state-dir /path/to/runs --file /tmp/continuation.json \
  --context-file /tmp/explicit-context.json \
  --attachment /path/to/explicit/coordinator-sidecar.json
```

`--context-file` and repeated `--attachment` are optional. Context is a small JSON
object with `decisions` (short string list), `priority` (short string list),
`next_action` (short string) and `blockers` (short string list). Supply current
explicit user decisions; do not put credentials in context, task labels or
summaries. The default priority reflects the current approved sequence: Leader
handoff/Clean sessions → Run scope → Plan reader → remaining original tasks.
Picker was delivered earlier and needs verification, not a rewrite.

The capsule includes a short English continuation prompt, project/Git identity
and head, original run/task/attempt/result/review identities and statuses,
approved actor identities, owned tabs/worktrees, acceptance/test evidence
references, next action and blockers. Remote URLs are fingerprinted, not
embedded. Raw histories, role prompts, review context, arbitrary resource fields,
auth files, environment variables and attachment contents are not imported.
Explicit context and bounded human task/evidence excerpts are operator-provided
data, not a universal secret detector or instructions to execute.

The output is capped at 64 KiB. It contains at most 16 task excerpts and eight
recent event references. Omitted counts and exact source JSON pointers/digests
remain visible; missing work is never silently treated as complete. The owned
source ledger is capped at 8 MiB for this operation. Up to eight explicit
attachments, each at most 256 KiB, are referenced by path, size and SHA256 only.
There is no broad state-directory scrape. A referenced contract/report digest
identifies the full evidence even where displayed text is shortened.

**Conversation checklist**, **project TODO** and **run evidence** are separate.
Coordinator sidecars and advisory reviews are not fabricated selected-task
results. Exporting the real legacy parent preserves its incomplete selected
work and does not bypass the every-selected-task QA gate or whole-TODO digest.
Future Run scope and Plan reader work are outside this feature.

Output must be outside RunStore and every approved Git/worktree root. It cannot
overwrite a binding/source or arbitrary existing file; only this run's own
previous capsule can be replaced. Export never changes the run JSON or binding
files. Native export additionally creates a private Watchdog-owned digest seal;
legacy export creates no adoption authority and never uses/rebinds Gossip.

## Native preview and confirmed adoption

The operator first supplies an already existing Watchdog binding JSON for the
new Codex main: the same canonical `repo` plus its fully registered `binding`.
This run-adoption API does not create or modify that file. Then:

```sh
python3 /absolute/controller/watchdog mission handoff-preview \
  --run RUN_UUID --state-dir /path/to/runs --file /tmp/continuation.json \
  --binding-file /explicit/new-main-binding.json
# Inspect the exact old/new identities and returned offer_id.
python3 /absolute/controller/watchdog mission handoff-adopt \
  --run RUN_UUID --state-dir /path/to/runs --file /tmp/continuation.json \
  --binding-file /explicit/new-main-binding.json --offer OFFER_UUID --confirm
```

Preview checks live identities, reserves the known current main’s purpose,
and writes a private offer without changing run ownership. Confirmation must name that exact target file and offer. Capsule
content, source snapshot, target file bytes and full native identity must match
the issued records. Export seals expire after 15 minutes; preview offers expire
after at most five minutes. Modified, expired, stale, consumed or mismatched
capsules/offers are rejected. Export/preview again after newer evidence or a
changed target; never edit a seal or retry a consumed transfer.

The trusted host operator must use the following conservative boundary:

- A native active/blocked run with no unfinished controller operation.
- Old and new main both verified **idle/done**, with the same approved account
  and team workspace. Each thread/account/project/history source/terminal/
  frontend PID/start is checked through the existing identity engine. The run's
  boot and current worker/QA generations/host owners are verified as well.
- The fresh main uses a distinct thread, pane, terminal and dedicated frontend.
  Worker/QA identities cannot become main. A shared frontend with another thread
  is rejected; same-frontend multi-thread isolation is not claimed.
- The project and owned worktrees are clean, committed and unchanged since
  export. Worker/QA may remain alive with sent assignments or an active review
  at this committed boundary; no work is repeated and no actor is restarted.
  If a worker is editing, wait for its clean commit/result boundary and export
  fresh context instead of discarding its changes.
- No sending/uncertain assignment, follow-up, QA intent, controller startup or
  coordination request. Every retained native delivery must already be sent.
- No pending/sending/uncertain main notification. Forward pending evidence under
  the current owner or inspect uncertain receipts; no automatic resend occurs.

Old main need not be closed or idle to **export**. Adoption is a host operation
at the idle boundary, not an in-turn self-election by an actor. There is no
fallback to focus, current pane, environment claims, another account or Gossip.
Legacy adoption is always refused. Moving a team between workspaces is not part
of this MVP; the new main stays in its existing workspace so execution-tab
ownership/navigation checks remain valid.

## Ownership and report boundary

The state machine is **exported/sealed → previewed → consumed**, or expired/stale
at any precommit check. The per-run lock serializes adoption with dispatch,
reports, monitor forwarding and other controller operations. Concurrent requests
receive an explicit busy rejection; retry the same report event ID after the
boundary. No report is acknowledged before persistence. A report committed
before adoption changes the snapshot and invalidates the old capsule. Every
old-owner notification must already have a confirmed queue receipt. A receipt
means queued/accepted, not proof that the old leader has read it; the evidence
remains in the ledger and capsule.

Adoption updates only the canonical main binding pointer/identity, increments
`leader_generation`, and appends the from/to identities and consumed capsule/
offer IDs in **one atomic RunStore record**, with file/directory fsync. The old
binding file, conversations, tabs, worktrees, assigned attempts, candidate,
results and QA remain intact. Later authenticated reports load the new main
binding and notify it exactly; old sent events remain evidence and are not
resent. Lost reply after commit cannot perform the transfer twice: inspect
`leader_generation` and `leader_handoffs` to determine whether it committed.

The old conversation is not closed or cryptographically disabled as a local
user. The operator must park its coordinating role after adoption; do not run
two leaders. This trusts the host user/runtime and canonical controller, as the
native transport does. Hostile unrestricted same-UID code and same-frontend
multi-thread isolation are outside the boundary. Git/Herdr verification is
rechecked before the atomic run update, not a transaction over arbitrary
external filesystem/editor actions. No stronger concurrency guarantee is
claimed for an operator changing those resources during adoption.

A capsule and attached result file are **evidence**, not approval. The new leader
checks actual commits, test logs and exact independent QA before accepting work,
preserves uncompleted tasks and current assignments, and delegates every later
task to a NEW executor and every review to a NEW QA conversation. Run approval,
TODO completion and target merge remain separate. No actual new main was
supplied for this implementation task; real export is safe, while replacement
is demonstrated only with isolated Git/RunStore fixtures and substituted native
identity boundaries.


## One task per executor; fresh QA and disposable probes

This is the explicit policy correction, superseding earlier instructions to
reuse the worker/QA. The current executor is grandfathered **only** to finish
Leader handoff and its corrections. It must decline later implementation or
probe assignments in this conversation. Main coordinates future sessions;
this feature does not spawn them.

Every subsequent implementation task uses a NEW executor conversation, starting
from the preceding accepted commit with only its bounded task brief. Corrections
within the same logical task may use its current executor. Every QA review,
including a recheck at the same candidate, uses a NEW QA conversation. Transport
probes require their own declared disposable conversation, never a real-task
executor. Never transfer a full transcript to any new actor.

Native dispatch/followup/review reserve an account/thread claim before sending.
The default private registry is `RunStore/session-policy`; a claim permits only
one run/project and one logical implementation/probe task, or one QA review ID.
Known pre-policy delivery records in that run are checked too. Failed/uncertain
sends retain the claim rather than quietly assigning unrelated work. Policy
rejections do not enqueue anything. Existing native identity, account, boot,
role, clean owned-worktree and exact-head gates still run. The next executor's
head must match `worker_head` set by verified result acceptance (or the initial
explicit brief base); the assignment carries that exact accepted base.

Separate disposable probe stores MUST explicitly set
`session_policy.registry_dir` to the same main registry **outside** the probe's
own isolated RunStore, and declare `participants.worker.purpose: probe` plus
`purpose: probe` on the probe task contract. Real executor and QA purposes are
`implementation` and `qa`. A fresh isolated registry is not permission to reuse
an executor. A native launch brief may supply the shared registry path; there
is no environment/focus guess. Registry metadata is bounded scope/identity data,
not conversation content, and it is kept outside Git/worktrees. Use one canonical
registry across the operator's related runs; do not remove claims to bypass the
policy. Probes and implementation can never exchange their claimed conversation.

The trusted host operator must actually supply unused, verified conversations.
The code checks registered claims and the current run's known delivery history;
it does not scrape unrelated projects or transcripts to infer arbitrary earlier
use outside Watchdog. It cannot protect against a trusted operator deliberately
choosing unrelated registries or falsifying provisioning. This is the same
explicit host/runtime trust boundary as native transport, not a claim of hostile
same-UID isolation.

Capsules contain the versioned session rules and registry reference; capsules
from the old reuse policy cannot be adopted, even if their old seal still
matches. Current actors/results/attempts remain historical/current evidence, not
permission to assign those conversations new work. Supplying fresh participants
is a main/operator lifecycle action: this task adds guards, not automatic
participant rotation, actor restart or a new-session launcher. If a fresh
verified participant has not been supplied, dispatch/review blocks with a reason.
The original whole-selected-task gate is unchanged; later Run scope work remains
separate. Tests exercise these policies in isolated fixtures with new logical
bindings only; no real executor, QA or disposable probe actor was created here.


## Main purpose and interrupted reservations

Preview and final adoption reject any target with a shared registry claim,
retained current-run worker/QA/probe delivery, or retained leader identity.
Rotating a participant does not erase its history. A → B → A is refused;
supply a fresh conversation C. Both the initial main (before assignment) and
adopted mains receive a lifetime `main` purpose claim. They cannot later become
executors, QA or probes in any run sharing the canonical registry.

Role claims and adoption acquire the same per-conversation nonblocking locks
in deterministic order. Final adoption holds those locks through its native,
Git and expiry rechecks, durable target reservation and atomic ownership save.
A role claim arriving after preview therefore blocks adoption; one arriving
during the final boundary receives busy and sends nothing. No transcript is
read to make these decisions. Version 2 session rules invalidate older capsules.

The target main reservation is durably written **before** ownership is saved.
A crash before that save leaves the old owner intact and the target reserved;
a reservation alone never proves adoption. Inspect the canonical run’s main,
generation and leader history, then supply another fresh target. Do not delete
claims or automatically retry with the reserved conversation. A crash after the
ownership save leaves the new owner and consumed transfer recorded; the same
offer cannot execute twice. This deliberately fails closed instead of rolling
back a lifetime purpose claim after an uncertain crash. The initial main’s
reservation is also kept if a subsequent assignment is rejected.
