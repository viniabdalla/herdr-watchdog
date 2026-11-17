# Mission Control pilot

Proposed scope for Vini's approval, 2026-11-17. No product changes or Git actions
are authorized by this document alone.

## Experience

Select open project tasks and choose Orchestrate. A confirmation shows tasks,
project, main conversation, and the team to open. One new Herdr tab holds the
team's terminals in separate panes. The main conversation prepares self-contained
assignments and receives compact results, questions and blockers, rather than
reading worker transcripts. Existing Send retains its current-thread behavior.
All product text is English, with plain-language labels and color plus text.

Progress becomes the monitoring view for this work: Ready to start (blue),
Working (yellow), Needs help (red, with a concrete reason), Checking the result
(purple), and Done (green). Display task, current agent, last update, and a way
to reach the execution tab. Distinguish project TODO progress from active-run
status. Waiting or missing evidence never counts as Done. Lost contact is shown
as unknown/unavailable, never silently inferred to be completed.

## Components and approach

Use Herdr for visible terminals, Agent Graph for role instructions and Gossip
for directed assignments and structured returns. Watchdog owns the mapping and
monitoring state. Agent Graph is not itself a launcher or an enforcement layer.
A standalone app and Hermes-specific profiles are unnecessary for this pilot;
future executors may use other programs without changing the role contract.

Reuse tropico-coding-team's leader, worker and QA boundaries. No active gossip
or unrelated peer is adopted automatically. Initial team is the current main
conversation, one explicitly approved new Codex executor and one new Codex QA.
An advisor is optional and is not launched for this pilot. All team terminals
are in the single execution tab; the main conversation stays in Mission Control.

Every executor uses a separate branch/worktree. The leader prepares task scope,
acceptance criteria and allowed files, receives commits/tests/blockers, and
integrates only into a feature branch. QA checks the complete integrated
candidate at an exact commit. The user makes the final merge. Workers implement
fixes and resolve source conflicts; the leader delegates those back.

The leader can clarify within agreed scope. Credentials, spending, destructive
actions and scope changes require the user. An unresolved blocker remains
visible. TODO changes require confirmation; dispatch never completes a task.

## Bootstrap and self-test

First implement the launch, mappings, structured status/results and visible
controls using the current manual Herdr/Gossip path. Test process and routing
behavior only in owned wd-test resources. Do not use production sessions as an
experiment or stop either Herdr server.

Then use the new Orchestrate button on the existing Conversation picker task:
show account names beside pane and session. One executor implements that bounded
feature in its worktree; QA checks the assembled result. This exercises the real
Tasks-to-team path with useful work on Watchdog itself. Subsequent runs tackle
automatic session progress and artifact discovery after the pilot passes.

Acceptance: one explicit confirmed dispatch, correct project/account/thread,
one new execution tab, isolated worktrees, visible state transitions, actionable
blocker return and follow-up on the same task, QA evidence for exact candidate,
unchanged TODO on sending, and no final-branch merge by an agent. Preserve
unrelated panes and processes; retain run evidence and owned-resource mappings.

## Required decisions before execution

This folder is not a Git repository. Earlier user rules prohibit git init and
commits until explicitly authorized. Need permission for local Git initialization,
a reviewed initial snapshot, task branches/worktrees and local commits. No remote
creation, publication or push is part of this permission.

Need approval to open the two new Codex participant sessions named above. This
is the explicit participant authorization required by the graph template.
