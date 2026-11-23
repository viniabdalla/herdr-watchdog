# Native transport

New Mission Control requests and launch templates default to `native`. Watchdog
owns run state and explicit contracts; Herdr owns the tabs and terminals. Codex's
existing verified queue delivers a contract to the full thread UUID in its exact
account, terminal and frontend. Busy and idle actors both receive queued work;
there is no focus-based routing, Enter simulation or pane text injection.

`watchdog mission template` includes `"transport": "native"`. An operator may
explicitly select `--transport gossip` at launch (or in the brief) for the legacy
adapter. A persisted ledger without a native kind continues using its existing
Gossip adapter. No active legacy run is migrated, re-bound or closed. Native
launch, bootstrap, enrollment, dispatch, receive, report, monitor and QA do not
need `agent-gossip`, its context files or Agent Graph commands.

## Delivery and reports

A stable selected task ID names the work. Each assignment or coordinator
follow-up gets a new `attempt_id`, while retaining the task and run IDs. The full
contract, exact native recipient, actor generation and `sending` intent are
persisted before queue submission; only a valid native queue UUID receipt marks
it sent. An ambiguous send, malformed receipt or interrupted `sending` intent
stays **uncertain** and is never automatically resent. Inspect the exact queue
and retained ledger before deciding recovery. There is no automatic resend or
actor replacement command.

The owned host wrapper writes `<role>-identity.json`. The actor enrolls from its
own conversation using the prompt's canonical controller command. Contracts are
queued in full; `mission receive --after N` is a bounded inspection fallback,
returning at most one newer contract for that role with its sequence cursor.
Do not replay work because a notification or receive response was seen twice.
Use the contract's attempt ID on all reports for that attempt. A follow-up
supersedes old attempts, including their late reports.

`watchdog mission report --run UUID --role worker|qa --file /tmp/report.json`
uses the scoped host bridge. Native reports include:

```json
{
  "run_id": "UUID supplied in the contract",
  "task_id": "selected task ID (worker reports)",
  "attempt_id": "UUID supplied in the contract",
  "event_id": "stable UUID for this report, reused on retry",
  "status": "working | blocked | result",
  "summary": "Short concrete human summary"
}
```

Worker results also require ordered full commit SHAs and observed test evidence.
QA uses the supplied `review_id` and exact `candidate`, with `status: qa`,
`verdict: pass|fail` and test evidence, or `working`/`blocked` during review.
Reports are authenticated and reduced into RunStore **before** notifying the
exact main conversation. Identical retries of an event ID are no-ops; changing
its content or actor is rejected. Wrong actors, roles, generations, attempts,
review IDs and candidates cannot supply accepted evidence. Superseded QA is
retained and forwarded explicitly as rejected evidence, never approval.

Native QA attempts are terminal after a QA verdict or Blocked report. Fresh
Working, Blocked or verdict reports on that finished attempt are rejected;
identical retries remain no-ops. Main must request a new review attempt to
resume QA. Approval also defensively requires `qa_finished: true`, current
`status: qa` and a passing verdict at the exact candidate and result version;
a retained earlier pass cannot approve an unfinished or non-passing review.

A committed pending event can be forwarded by the monitor after a restart. A
notification whose send began but lost its receipt stays uncertain and is never
resent automatically. Restart recovery reconciles every task/review `sending`
intent, including interruptions before a delivery record exists and after a
receipt was committed. Only a known sent receipt matching the role, recipient,
generation, attempt and task/review scope finalizes delivery. Missing or
inconsistent receipt evidence becomes an inspectable blocked/uncertain state;
no queue call is repeated and no delivery record or receipt is invented. A
current attempt's later authenticated report survives receipt reconciliation. Progress shows pending/uncertain main notifications and
uncertain native assignments; retained evidence is inspectable even when main
cannot currently be contacted. No dispatch, report, process exit or model
proposal completes TODO.md.

## Authentication boundary

The host independently discovers and verifies the exact Codex thread, account,
terminal, frontend PID and start time. It pins a boot ID, actor generation and
live host-wrapper PID/start. A private typed Unix socket uses `SO_PEERCRED` plus
actual process ancestry to that frontend. The caller's thread claim is an
additional check, not authority. The broker rechecks caller liveness after
identity validation and before the finite operation, using its immutable proof.
Only enrollment, role-scoped receive and structured report are available; no
shell, arbitrary file operation or cross-role endpoint exists. Requests and
responses are bounded. No host `/proc` view is exposed to the sandbox.

This supports tools descended from a dedicated verified frontend. A shared
app-server ancestor alone is insufficient, and same-frontend multi-thread
isolation is **not** claimed. The local user/runtime and host controller are
trusted; arbitrary hostile host code with unrestricted same-UID access is
outside this boundary. The child receives a clean launch environment; no active
conversation changes `CODEX_THREAD_ID` or signs as another peer.

## Safe idle proof using existing approved actors

Old wrappers retain their loaded code, including the old liveness implementation.
Never restart a busy actor merely to load an update. After integration and at a
verified idle boundary, an operator can use an **isolated native RunStore** with
the explicitly approved existing actor bindings, resources and owned worktrees.
Keep the production/legacy ledger and historical IDs intact. The test brief can
request a transport-only Working/Blocked report with no implementation or TODO
completion; do not fabricate results for any selected task.

The ledger must already pin the actor's full `native` binding. From the host,
with the existing main binding verified, run:

```sh
python3 /absolute/controller/watchdog mission native-host \
  --run TEST_RUN_UUID --role worker --state-dir /tmp/owned-native-test-runs --confirm
```

This helper only attaches a fresh scoped broker to an explicitly pinned idle
actor with no dispatched work and no previous bridge attempt. It creates no
agent, tab or model session and sends no signals. The same actor then enrolls
against that test run, receives a probe through the exact-thread queue, and
returns a correlated report through the native bridge. Verify the real queue
receipt, actor inbox response and persisted event before calling this an
end-to-end proof. Closing the helper closes its own socket and revokes that
bridge's enrollment; the actor and legacy wrapper remain intact. A rejected or
interrupted attachment retains evidence for inspection instead of retrying.

The included automated tests exercise real temporary Git worktrees, durable
state and a real Unix socket/ancestry, substituting the external Codex
identity/queue boundary. They do **not** claim a real Codex inbox experiment.
Main also exercised an approved existing Codex actor through this idle host path
on the original native candidate: enrollment, queue receipt, authenticated report
persistence/forwarding and duplicate retry were verified. Only the helper was
closed; the actor was preserved. That transport probe does not approve a
candidate or cover later repairs. The QA transition and crash-window corrections
use isolated regression fixtures; they do not repeat the live probe.

## QA and current scope limit

Independent QA still requires a clean owned inspection worktree, the full exact
candidate SHA, the approved base and every reported worker commit (or verified
cherry-pick equivalent). Passing QA applies only to that candidate and result
version. Run approval, project TODO completion and target merge remain separate.
The whole-TODO digest/selection and **every-selected-task result** gate remain
unchanged. This step cannot finalize a partially implemented legacy run merely
because one part received an advisory pass; missing tasks need their actual
contracts and results. Run-scope changes and leader/session handoff are later
work. No Left Undone state or global configuration is written.

## Fresh launch contracts

Fresh single workers carry `provisioning: fresh`; `grouping: together` identifies
a bundle and `purpose: plan` identifies a proposal-only run. Legacy ledgers omit
these fields and retain their previous behavior. Launch contracts are persisted
before starting a frontend. Their receipts use `method: launch` and the verified
frontend PID/start time, never a fabricated Codex queue receipt. Bootstrap and
enrollment still gate worker reports through the same process-ancestry broker.
Claude callbacks derive the claimed session from the owned proof; the server
independently checks actual process ancestry and the exact pinned native identity.

Planning is collected by the owned host wrapper from the provider's native plan
response, without giving a completion callback to the planner. Proposals cannot
pass the implementation result/review gate. Gossip is frozen: preserve historical
compatibility, but do not add new integrations or use it for provider parity.
