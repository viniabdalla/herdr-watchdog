# Mission Control operator guide

An Orchestrate confirmation authorizes one worker plus one QA, with the current
verified Codex conversation coordinating. It queues a request, keeping selected
TODO tasks open. The main prepares the explicit contract and launches it. No
model planning, remote publication, target-branch merge or TODO edit is performed
by these commands.

Use the same installed `watchdog` executable as the panel. A source checkout can
use `python3 /path/to/watchdog` instead. The commands below run in the main
conversation, except `report`, which runs in the assigned participant.

```sh
watchdog mission list --repo /absolute/project
watchdog mission inspect --run RUN_UUID
watchdog mission template --run RUN_UUID > /tmp/mission-brief.json
# Main fills in all contract fields, then launches the already approved team:
watchdog mission launch --run RUN_UUID --brief /tmp/mission-brief.json --confirm
watchdog mission open --run RUN_UUID
```

A brief contains `run_id`, the exact `repo`, a full `base_sha`, and exactly
`participants.worker` and `participants.qa`. Each participant specifies absolute
`account` (Codex account directory), absolute `executable`, and an explicit
`model` and `effort` (`low`, `medium`, `high` or `xhigh`). Both are required.
The template uses `gpt-6.1-sol` with `medium` for worker and routine QA;
higher effort is an explicit choice for a concrete harder problem. The launcher
passes both `--model` and `-c model_reasoning_effort=...`, so a local Astra/xhigh
configuration cannot silently override these choices. Progress shows each
participant's model and effort as secondary details.
The template proposes the current main account and local Codex binary;
verify these before launch. No credentials are copied or read by Watchdog.

Every task contract contains its existing stable `id`, a nonempty `allowed_files`
list of bounded relative paths, nonempty `acceptance` and `tests` lists, and a
`dependencies` list of other selected IDs (empty for independent tasks). The
selected TODO snapshot, main binding and clean committed base must still match.
Cycles, unknown dependencies, extra participants and incomplete contracts fail
before resources are created. Allowed paths and test commands are instructions
for the worker, not a filesystem sandbox enforcement mechanism.

Launch retains worktrees under the run directory, creates a new local Gossip
room, creates one Herdr tab and two panes, loads the Agent Graph
`tropico-coding-team/worker` and `/qa` role context, then starts their Codex
terminals. It uses `workspace-write`, `approval_policy=never`, local runtime
access and network access for Gossip. It preserves Herdr pane context and clears
inherited Codex thread/account environment before setting the approved account.
No existing Gossip is adopted, no advisor is launched, and no unrelated peer is
recruited. A monitor verifies native account/thread/terminal identity and pins
the two newly launched Gossip keys before assigning work. The owned room records
a graph instance and hash, one live `leader: true` entry for the exact main
identity, and worker/QA entries bound to their verified native identities and
pinned keys. Missing, conflicting or replaced graph identities block routing.

The worker receives its explicit contract over Gossip. Reports are small JSON
files, sent with the command included in its bootstrap prompt. For example:

```json
{
  "run_id": "RUN_UUID",
  "task_id": "SELECTED_TASK_ID",
  "status": "blocked",
  "summary": "The required fixture is absent; supply its path within the agreed scope."
}
```

```sh
watchdog mission report --run RUN_UUID --role worker --file /tmp/report.json
watchdog mission followup --run RUN_UUID --task TASK_ID --text 'Use tests/data/example.json; scope is unchanged.'
```

A worker `result` report additionally requires `commits` (ordered full SHAs) and
`tests` (commands and observed results). `working` and `blocked` reports require a
concrete summary. Free-form “done”, process exit, heartbeat loss and an artifact
alone never complete a task. Follow-ups preserve the same run, selected task and
Gossip task identities. Scope changes or task edits require a fresh contract;
a clarification is not authority to broaden the original allowed files.
Progress shows “Guidance sent; waiting for the agent” after a follow-up. The full
instruction and its delivery status remain in the task's `guidance` history,
available through `mission inspect`, including uncertain deliveries.
Participants must use the absolute controller report command in their bootstrap,
so fixes remain available even when their checkout is pinned to an older base.
Publishing checks report structure and the assigned local Gossip key/graph;
the receiving host independently verifies native identity before accepting any
evidence. Publishing never requires visibility of host processes inside a tool
sandbox and never changes authoritative task state directly.

The main checks and integrates commits into its feature branch. For multiple
selected tasks, accept the returned result for sequencing, then dispatch the
next explicit contract. This acceptance does not mark the task Done:

```sh
watchdog mission accept-result --run RUN_UUID --task TASK_ID --confirm
watchdog mission dispatch --run RUN_UUID --task NEXT_TASK_ID
watchdog mission review --run RUN_UUID --candidate FULL_INTEGRATED_SHA
```

QA uses its clean detached worktree at that exact candidate. Its report contains
`run_id`, the assignment's `review_id`, `status: "qa"`, `candidate`, `verdict: "pass"` or `"fail"`, a concrete
`summary`, and a `tests` list. Main delegates fixes through `followup` on the same
worker task, integrates them into its feature branch and invokes `review` again
at the new exact SHA. Each review has a unique attempt ID and captures the implementation evidence
version. New worker evidence invalidates that review, including delayed passes
for the same candidate. Before QA starts, every returned commit must be present
in the candidate or have an equivalent cherry-picked patch. Earlier QA cannot
approve a later result or candidate.

```sh
watchdog mission approve --run RUN_UUID --candidate FULL_INTEGRATED_SHA --confirm
```

Approval requires every implementation result and passing QA at that exact
candidate. It marks only run progress Done. TODO completion still uses the Tasks
panel's existing separate confirmation. Final target-branch merge stays with
the user.

The monitor bridges compact structured events to the exact main Codex account
and thread, retaining report bodies and delivery receipts in the run ledger.
It never reads full participant transcripts. `mission poll --run RUN_UUID`
performs one monitor pass; `mission watch --run RUN_UUID` restarts monitoring
without launching new terminals. Only one monitor can own a run at once.

Each confirmed assignment, follow-up and QA request also queues one short native
Codex notification to the verified participant account and full thread UUID.
It asks the participant to poll its existing Gossip task, ignore already handled
messages and avoid duplicating work. It works while the actor is idle or busy;
the contract and result correlation remain in Gossip. A queued notification is
not proof that the model has consumed the message.

The run's `wakes` history records the recipient, intent, receipt and delivery
status. An identity failure leaves notification pending; an enqueue failure
leaves it uncertain. Progress shows that attention is needed. Inspect the exact
conversation queue before reconciling manually; Watchdog never retries these
notifications automatically or substitutes pane input. Further follow-ups are
blocked while an earlier worker notification remains unconfirmed.

## Interrupted work and limits

Intent is persisted before creating worktrees, tabs, terminals or sending a
message. A timeout or interrupted launch is retained as uncertain/blocked. The
launcher refuses a second launch of that run; it never guesses that an absent
receipt means the operation failed. Uncertain requests, assignments, follow-ups
and summary deliveries are not automatically resent. Inspect the ledger, exact
inbox and owned resources before any manual reconciliation. There is no
one-click reset, cleanup, uncertain-delivery resend or resource adoption in this
pilot. Existing tabs, worktrees and evidence are deliberately retained.

Native registration may be absent even when a terminal is visibly running.
Progress shows the registration problem; it does not guess a thread from pane
focus. Recover the native registration only after checking process, account and
thread, then let the monitor verify it. If main's identity changes, forwarding
stops rather than choosing another conversation. Contact older than 45 seconds
is Unavailable, preserving the last report. No daemon or server is stopped by
Watchdog.

Gossip's CLI addresses nicknames; Watchdog verifies each unique nickname against
its pinned key immediately before sending and correlates incoming task IDs and
keys. The CLI does not offer an atomic key-addressed send. Room isolation and the
native identity checks reduce this boundary's race window; Watchdog does not
claim cryptographic process attestation.

QA and worker accounts remain trusted local actors. Role instructions enforce
who implements, integrates and reviews; Agent Graph is not a launcher or a
security boundary. Only the approved two participant processes are started.

## Verification

```sh
python3 -B -m unittest discover -s tests -q
WATCHDOG_GOSSIP_TEST=1 WATCHDOG_HERDR_TEST=1 python3 -B -m unittest discover -s tests -p test_mission_native.py -v
```

Native tests create owned local Gossip peers and an owned workspace on `wd-test`;
they launch no model agents and send no production messages. The Herdr test uses
`/usr/bin/true` as a stand-in executable, checking actual tab/pane/worktree
behavior. The Gossip test exchanges a real assignment, blocker, same-ID
clarification and result; the final Codex inbox is a controlled foreign boundary.
PTY tests exercise real confirmation and progress rendering, including emitted
ANSI colors. Physical color distinction and the real two-agent self-test remain
part of coordinator QA and the approved pilot rollout.

The launching main process needs filesystem permission for the Watchdog run
state directory and the repository's shared Git directory, plus local Gossip
IPC/network access. A denied operation remains visible and is not retried with
weaker sandbox settings. Run approval does not terminate participant processes
or delete their worktrees; the coordinator can send the final native Gossip
task approval separately when closing the team.
