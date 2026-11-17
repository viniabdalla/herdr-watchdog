# Session progress

Progress receives the same explicit `--binding-file` as Tasks. It verifies the
native conversation and project association before each transcript read, using
the existing read-only identity engine. An unbound or changed conversation shows
**Unavailable**; project TODO counts and Mission Control remain independent.
Reopen Watchdog to select a conversation if its identity changes.

The session section shows **Ready** (blue), **Working** (yellow) or **Done**
(green) only for a successful, correlated native checklist. It displays completed
steps over all current steps, a bar, and the current active step (or next pending
step). This measures the agent's own checklist, not independently verified work
and not project completion. Empty plans show **No checklist**, without `0/0`.

**No checklist**, **Catching up** (purple), **Unsupported** and **Unavailable**
(gray) do not display a ratio. Catching up includes an incomplete trailing row;
previous counts stay hidden until that source is caught up. A new native turn or
Claude user prompt clears the previous checklist until a new successful update.
Completed plans remain visible through the end of their turn. Project TODO is
never substituted for a conversation checklist. This reader never writes TODO,
Left Undone state, native histories or global configuration.

## Supported records and limits

The conservative direct adapters recognize:

- Codex `response_item` / `function_call` named `update_plan` (optionally in the
  `functions` namespace), with JSON `plan` entries containing `step` and
  `pending`, `in_progress` or `completed` status. Only a matching
  `function_call_output` with native `Plan updated` success text applies it.
- Claude assistant `tool_use` named `TodoWrite`, with `todos` containing
  `content` and those same statuses. Only a matching non-error user
  `tool_result` starting with the native successful TodoWrite message applies
  it. Failed calls and unrelated results preserve the previous valid checklist.
- Claude `TaskCreate` / `TaskUpdate` pairs show **Unsupported** after a non-error
  matching result. There is no inferred task ID, guessed mutation or percentage
  for these formats yet. Unknown successful checklist schemas are unsupported.

On 2026-11-17, read-only inspection of the available 158 Codex and 17 Claude
JSONL histories found native call/result and turn envelopes, but no direct
successful checklist-tool pairs. Consequently direct checklist tests are
explicitly synthetic protocol controls. A redacted observed Claude result
envelope tests exclusion of unrelated output. No native checklist fixture is
claimed as observed. Live PTY coverage uses a temporary bound source and tests
CLI forwarding, append refresh, colored progress and stale-turn clearing; it is
not a production conversation experiment.

Codex orchestration `exec` code, shell commands, stdin, assistant text and project
TODO are not parsed as checklist calls. No transcript code is evaluated. Claude
sidechains, agent records and mismatched session IDs are excluded; Codex session
metadata and available native turn attribution must match. Tool results must
follow their matching calls in the same reader generation and turn. Unknown
formats remain honest missing/unsupported data, rather than inferred progress.

Each panel keeps one in-memory incremental reader: at most 256 KiB of new bytes
per refresh plus small source anchors, with a 1 MiB line limit. Partial UTF-8/JSON
rows resume after append; malformed and oversized rows are discarded without
blocking later records; skipped rows hide old counts until a fresh checklist or
turn can be read, since the gap might contain a turn boundary. Non-regular sources cannot block the panel. Inode
replacement, shrinkage, changed prefix or changed read-boundary anchor resets
checklist state and replays the new generation in bounded chunks. Arbitrary
in-place edits in the middle of an append-only history, preserving both anchors,
are outside this detection contract. Reopening the panel replays from the start;
no whole-history reread occurs on each frame.

Memory is bounded to 128 pending checklist calls, 256 steps / 32 KiB of text per
plan, 4,096 event fingerprints and 4,096 applied call IDs. Replay deduplication
covers this bounded window, not unlimited historical duplication. IDs and text
have additional length limits. Standard library only; there is no model request,
Left Undone store access, transcript execution or project-state mutation.
