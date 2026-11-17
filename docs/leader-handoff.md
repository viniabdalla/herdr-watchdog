# Leader handoff / Clean sessions

This CLI-first MVP prepares a fresh leader to coordinate the **existing** worker
and QA. It does not start a conversation, clear an actor's context, move/focus a
tab or restart anything. An actual new main must be supplied explicitly by the
operator. No production leadership switch is implied by exporting a capsule or
by the automated tests.

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
This feature does not create or modify that file. Then:

```sh
python3 /absolute/controller/watchdog mission handoff-preview \
  --run RUN_UUID --state-dir /path/to/runs --file /tmp/continuation.json \
  --binding-file /explicit/new-main-binding.json
# Inspect the exact old/new identities and returned offer_id.
python3 /absolute/controller/watchdog mission handoff-adopt \
  --run RUN_UUID --state-dir /path/to/runs --file /tmp/continuation.json \
  --binding-file /explicit/new-main-binding.json --offer OFFER_UUID --confirm
```

Preview checks live identities and writes only a private offer, not run
ownership. Confirmation must name that exact target file and offer. Capsule
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
coordinates existing actors, and preserves uncompleted tasks. Run approval,
TODO completion and target merge remain separate. No actual new main was
supplied for this implementation task; real export is safe, while replacement
is demonstrated only with isolated Git/RunStore fixtures and substituted native
identity boundaries.
