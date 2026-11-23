# Watchdog orchestration port — verification, 2026-11-19

## Scope

The user approved changing Watchdog only, leaving Left Undone intact, importing/adapting its orchestration workflow, and freezing Gossip. This delivery adds fresh worker dispatch, Codex/Claude launch-time briefs, authenticated reports, clean-checkpoint follow-ups, Separate/Together selection and provider-native planning. Other brainstorm product choices remain pending.

No Left Undone source, installation or state was written. Its existing read-only identity dependency remains. Existing-executor, team and legacy Gossip behavior is retained. Codex keeps Watchdog's workspace sandbox; Claude uses its provider-specific permissions mode. This is a deliberate adaptation of LU launch behavior.

## Evidence

- Original working baseline: 400 tests, OK, 7 skipped.
- Final reviewed implementation: `python3 -B -m unittest discover -s tests -q`: **435 tests, OK, 7 skipped**.
- Real temporary Git worktrees test fresh launch, interrupted/duplicate launch rejection, clean checkpoints, grouped scope and review gates.
- A real Unix socket tests Claude enrollment/reporting and process-ancestry rejection. Identity discovery itself is substituted in these tests.
- A real local subprocess stands in for the Codex app-server and exercises startup, native plan protocol and deadline handling without a model call.
- Curses controls are covered by existing PTY tests and new grouping/confirmation tests. Actual terminal rendering was inspected in an owned temporary Foot window. Local captures: `docs/evidence/orchestration-port/01-grouping.png` and `02-confirmation.png`. The preview uses temporary tasks and a test session; it is not evidence of a live model dispatch.
- No authenticated Codex/Claude model session was launched. Real provider end-to-end acceptance remains pending in TODO.md.

## Independent review and fixes

A fresh reviewer examined the full implementation. All six Critical/Important findings were reproduced and corrected:
1. Codex planning passed an unsupported argument to Popen. A real subprocess test now covers the launch, with an actual response deadline.
2. Rejected follow-ups cleared prior state. Base validation now precedes replacement, and pre-side-effect failure restores the previous assignment/review.
3. Follow-ups replaced a live monitor's PID. The verified existing monitor is reused.
4. A joint plan could authorize extra tasks in a smaller execution. Automatic proposal reuse now requires the same complete task scope.
5. Dead planning wrappers stayed Working. PID/start/boot identity and startup timeout reconciliation now produce a retained blocker.
6. Large proposals could never reach the leader. Oversized notifications link to the stored proposal instead of embedding it.

The final suite passed after these fixes. There was no second independent review. No minor findings were deferred.

## Delivery

Implementation was prepared in the managed worktree on `codex/watchdog-orchestration-port`. Its baseline commit `ac657b0` includes the user's pre-existing uncommitted Agents pane changes solely to preserve the working baseline. Only the diff after that baseline is applied back to the original checkout; the baseline commit is not merged. No push is part of this delivery.
