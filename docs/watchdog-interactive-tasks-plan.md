# Interactive Tasks and review proposals

Approved in conversation: keyboard/mouse task selection, explicit send to the
verified current conversation, separately confirmed completion, section colors
(Next blue, In progress yellow, Blocked red, Done green). Vini then selected
Codex proposals for confirmation and asked it to identify completion or blockers.

Approach: keep TODO.md authoritative; use a focused Tasks panel and a small
reviewer. No Left Undone database writes. Keep native Left Undone alongside it.
Programming choices below implement that approved behavior; no Git init/commit.

1. `watchdog_app/todo.py`: parse sections and tasks with snapshot IDs; preserve
   metadata and unrelated prose. Locked, atomic writes require the same file
   digest. Move selected tasks or add reviewed tasks, recording a backup first.
   Completed tasks stay in Done; do not discard old completions in this step.
   Tests: preserved English/Portuguese sections, stale snapshots, duplicate IDs,
   literal text, code examples ignored, completion and blocked reason.
2. `watchdog_app/actions.py`: load a Watchdog-owned binding file, verify the
   native account/session/process and project association before every action.
   Prepare a send confirmation snapshot; send once, retaining tasks as open.
   Busy Codex can be queued only after explicit confirmation; no uncertain retry.
   Tests use foreign API boundaries, never real prompts or real task writes.
3. `watchdog_app/curate.py`: latest completed reply from the verified transcript
   versus current open TODO tasks, with completed titles as context. Always
   Codex gpt-6-luna low, tools off. Outputs: done, blocked with reason, additions.
   Quotes must match normalized prose (harmless Markdown emphasis removed before
   inference); no fuzzy evidence. Reject unknown IDs and conflicting statuses.
   Cache by conversation, source event, file digest and rules; show rejected
   proposals, do not silently treat them as success. No automatic task changes.
   Review on a new completed reply, plus an explicit Review control. A cancellable
   background worker keeps the panel responsive and cleans up its own CLI child.
   Apply needs explicit confirmation, current file and current source evidence.
4. `watchdog_app/tasks_ui.py`: colored section labels, selectable task rows,
   visible controls, send/done/queue confirmation, proposal review with evidence.
   Start/Next moves are explicit. Done rows cannot be sent. Escape cancels.
   Narrow terminals still show instructions without accidental actions. Add a
   binding-file argument to native panel launch and preview Tasks routing.
5. Validation: failing tests first, then unit and real-PTY tests; isolated
   wd-test only for layout/process checks; one synthetic real-Codex review.
   Independent final review, then reload only the owned Tasks process and verify
   live colors/controls/source. Never send test tasks into Vini's real session.

Scope: manual proposals confirmed by Vini, not autonomous code inspection or
automatic task completion. No fresh-session orchestration in this step. Progress
and Artifacts retain their current behavior. Native Left Undone work remains in
its own handoff/worktree. The live sender must receive an explicit Watchdog
binding file, never infer a recipient from neighboring panes or inherited IDs.

## Execution notes

- Implementation stays in this intentionally non-Git folder. Existing baseline
  suite is checked before editing; native integration tests use wd-test.

- Implemented all five parts. Independent review exposed a no-final-newline
  heading bug, an editor-save race, and pane-based delivery identity race.
  Regression tests reproduce them. Atomic Linux exchange preserves displaced
  editor versions and restores conflicts; all Codex deliveries use full UUID
  and account inbox transport. Claude sending fails closed until such a transport
  exists. Busy Codex still needs separate queue confirmation.
- Synthetic real-Codex review returned both Done and Blocked with matching quotes.
  This demonstrates login/model/schema behavior for that example, not independent
  code verification or broad accuracy. The real-conversation validation task stays
  open. Native tests use wd-test; interactive tests use isolated real PTYs.

## Real Codex delivery validation — 2026-11-17

Passed in an owned disposable wd-test workspace, using a temporary project and
real interactive Codex gpt-6-luna at low effort. Hooks, shell tools, web and
configured MCP servers were disabled. Initial reply: READY_WD_DELIVERY_7C4F.
The test registered the exact thread with Herdr's herdr:codex source after
matching the unique initial transcript cwd, account, foreground process and
session metadata. This tests delivery after verified registration; it does not
prove automatic native registration with hooks disabled.

Used unmodified Watchdog Session and Snapshot, native binding/project validation,
and Session.dispatch. The native queue acknowledged message
01a1e994-a342-7a20-9456-33bc1eb59c6d for full thread UUID
01a1e993-e0ee-71d1-ace4-e10331007dac. The transcript contained exactly one task
request and a completed reply RECEIVED_WD_DELIVERY_7C4F. No receiver tool calls.
Temporary TODO.md remained byte-identical and its task remained open. Only after
those assertions was the project's validation task moved to Done.

The test-owned workspace w18 was closed; the wd-test server stayed running.
Detailed local evidence: docs/evidence/codex-inbox-delivery-2026-11-17.json.
No production conversation received synthetic prompts. The user also reported
that this validation request itself was sent using the Tasks manager and it
arrived in the intended current conversation.

Limits: real idle-thread delivery tested. Busy-thread confirmation/queue policy
has automated boundary tests; this probe did not exercise real busy-thread
consumption or Claude sending. No code changes were needed for delivery.
