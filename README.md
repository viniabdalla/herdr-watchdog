# Herdr Watchdog

Watch a verified AI conversation alongside project tasks, progress and artifacts.
Linux, Python 3.10+, standard library only, Herdr 0.9.1+, Yazi and `ya`.
The installed Left Undone identity engine is currently required.

## Use

```sh
python3 install.py
watchdog                       # choose the conversation if needed, then layout
watchdog layout 2              # direct preset selection
watchdog layout column-bottom
watchdog layout --list
watchdog list                  # verified conversations in the current project
watchdog status                # inspect the selected conversation without opening panels
```

Run from the project folder, or pass `--repo /path/to/project`. `--pane ID
--session UUID` selects an exact verified conversation. Missing native session
registration is reported; Watchdog never guesses a UUID from focus or cwd.
An existing Codex thread in agent-tool context is matched by CODEX_THREAD_ID.
Conversation rows show the account before the session ID: canonical `~/.codex`
and `~/.claude` use “Default account”; other paths use their final folder name,
with parent folders added when needed to distinguish accounts. Names that still
look identical after control characters become spaces get stable account numbers.
The default account label is reserved for the canonical paths. Labels come only
from the verified binding path, without reading credentials or account settings.

Four presets are available; number 2 is the initial default. Arrows or j/k move
through the selector, the drawing follows, Enter applies, and Esc cancels without
changing the layout. Successful choices become the next default. All presets
reuse terminals rather than restart them. Unrelated terminals stay in place;
if they share the conversation tab, Watchdog uses a dedicated conversation tab.

The Herdr action “Watchdog: choose a layout” opens a terminal selector when the
action has no interactive terminal. Left Undone is optional as a visible panel:
if its panel is already bound to this conversation, it stays to the right of
Files. Watchdog reads that binding and never edits Left Undone's state.

## Interactive Tasks

Click a task or use arrows/j/k and Space to select it. `s` prepares a request
for the verified Codex conversation; confirm with `y`, or Esc to cancel. Requests
go through Codex's account-specific inbox using the full thread UUID. A working
conversation needs a separate queue confirmation. Tasks stay open after sending.
Claude conversations can be watched, but task delivery is unavailable until a
thread-addressed transport exists; Watchdog does not type into a pane prompt.

`d` requests confirmed completion. `i` moves to In progress; `n` moves to Next.
Section colors: Next blue, In progress yellow, Blocked red, Done green.
Edits preserve notes and completed history, retain backups under Watchdog state,
and reject stale selections. Concurrent editor saves are preserved; a conflict
requires reviewing the file again. Atomic exchange requires Linux renameat2.

The curator uses Codex gpt-6-luna at low effort, independent of the watched AI.
It checks each new completed reply against open TODO tasks and completed titles.
`r` opens suggestions, or requests a fresh review. It proposes Done, Blocked
with a reason, and explicit new tasks. Every proposal displays a supporting
quote. Apply only the proposals you select, with a separate confirmation.

The reviewer uses the current Codex login (`WATCHDOG_CODEX_HOME` can select an
account). It makes model requests; it does not inspect code or prove a completion
claim. Missing mention is not treated as a blocker. Invalid/conflicting proposals
are withheld visibly. New replies or task edits invalidate old confirmations.

## Current limits

The launcher, verified binding, four layouts and artifact-to-Yazi link work.
Tasks is interactive with confirmed curator proposals. Progress reads successful
native checklist calls from the explicitly verified conversation; it no longer
reads the manual preview checklist. Missing or unsupported checklist data has
an explicit status without a percentage. Artifacts still uses an explicit list;
automatic artifact discovery remains pending. See [Session progress](docs/session-progress.md)
for supported formats and evidence limits.

This project's TODO.md uses the shared git-todo section format. The displayed
project ratio counts only the currently listed tasks. It is not a prediction
of total project completion.

Runtime state and locks live under ~/.local/state/herdr-watchdog. Override with
WATCHDOG_STATE_DIR for tests. WATCHDOG_LEFT_UNDONE_ROOT can locate an engine
checkout when the left-undone command is not in PATH. No Git repo is required.

## Verify

```sh
python3 -B -m unittest discover -s tests -q
# With the disposable wd-test server running:
WATCHDOG_HERDR_TEST=1 python3 -B -m unittest discover -s tests -q
```

Live layout tests use only their own workspace in wd-test. Yazi tests use
temporary files and real PTYs. `python3 uninstall.py` removes only this checkout's
links and keeps state; it does not close running panels or stop Herdr.

## Mission Control pilot

Select open tasks in Tasks, press **o / Orchestrate**, and confirm the project,
main conversation, account and team. This queues a coordination request to that
exact Codex thread. Send keeps its existing current-conversation behavior. The
main prepares the task contracts; the launcher does not invent a plan. Neither
requesting work nor approving a run edits TODO.md.

Progress now reads the run ledger: **Ready to start** (blue), **Working** (yellow),
**Needs help** (red), **Checking the result** (purple), **Done** (green), and
**Unavailable** when contact cannot be verified. It shows task, agent, last update,
reason and execution-tab navigation with Enter/click. Project TODO counts are a
separate section. Actual colors follow the terminal palette.

Each launch records an explicit model and reasoning effort. The brief template
uses gpt-6.1-sol with medium effort for worker and routine QA, with actual CLI
overrides; Progress displays those choices.

The initial team is exactly one worker and one QA. Both terminals share one new
tab; each has its own worktree. Each later implementation task requires a NEW
executor conversation at the preceding accepted commit; every review requires a
NEW QA conversation. Probes require dedicated disposable conversations and must
never use real-task executors. Main supplies those actors; no automatic reuse. The
first independent task is dispatched once the exact native Codex identity and
role enrollment are verified. New runs use the Codex queue and durable local
reports by default; Gossip is an explicit legacy adapter. Existing runs retain
their transport. See [Native transport](docs/native-transport.md) for delivery
receipts, identity boundaries and the safe idle test path. Main reviews each result before dispatching the next
contract. QA reviews the complete integrated candidate at its full commit SHA.
The main/user approves completion separately. No command merges or pushes code.

The operator lifecycle is documented in [Mission Control](docs/mission-control.md).
The run ledger is in `$WATCHDOG_STATE_DIR/runs` (normally
`~/.local/state/herdr-watchdog/runs`). Keep it: it contains exact native identities,
source snapshots, assignments, results and owned resource mappings.


## Leader handoff / Clean sessions

Tasks' **c / Clean sessions** requests the verified current leader to reconcile
TODO and save a real ai-memory MCP handoff. Review the exact project/thread and
explicit owned-file, approved-branch, push and fresh-frontend scope, then confirm.
The backend commits owned changes, fast-forwards only approved branches, verifies
the pushed checkpoint, creates a fresh Herdr split/Codex frontend, delivers bounded
context to its exact thread and waits for actual receiver receipt and predecessor
release. Store then transfers Tasks/Progress and the existing Orchestrate target,
preserving panel terminals, Artifacts, Files/Yazi and layout. Left Undone is read-only.
Pending/blocked/partial/received/released outcomes and uncertain effects stay visible;
no blind resend or relaunch occurs. Active native runs must finish first.

The separate `watchdog mission handoff-export`/preview/adopt APIs retain their
bounded run-evidence and freshness guards. Legacy ledgers stay export-only; project
baton transfer never forges native legacy adoption. See
[Leader handoff](docs/leader-handoff.md) for the workflow, boundaries and evidence.
Tests use real isolated Git/remotes and UI controls with labelled simulated
model/native/ai-memory/Herdr boundaries; production end-to-end acceptance is separate.

The clean-session policy supersedes older transport-probe examples: never use a
real-task executor for a probe. The current grandfathered worker finishes only
Leader handoff. Native policy claims reject known executor/QA/probe reuse;
separate probe RunStores must explicitly share the main session-policy registry.
