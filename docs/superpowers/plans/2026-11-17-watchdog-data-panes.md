# Watchdog live data and validation plan

> Implementer: use executing-plans and meaningful TDD. Main coordinates; the
> single approved executor writes code, one QA reviews the complete integration.

Goal: implement the four remaining selected data tasks and verify the already
completed account picker. English, human status text and color plus words;
Python standard library only. Preserve four layouts, native binding, Mission
Control, confirmation-based TODO edits and Artifacts → adjacent Yazi navigation.

One new execution tab, one Codex worker and one QA, both gpt-6.1-sol/medium.
No advisor, extra coding agents, target/main merge, push, global config or Left
Undone writes. Protected concept, review-claude.md and vim-motions-mix unchanged.
All runtime experiments use owned wd-test/temp resources; real histories read
only. Never stop a Herdr server or close unrelated resources. Reports go under
/tmp, not into Git worktrees. Use canonical report CLI and existing task IDs.

Sequence: picker verification → session checklist → artifacts → completion
history → real curator evaluation. Each task starts at the worker head explicitly
accepted by main; no overlapping assignments. QA sees the complete candidate
with immutable base/head and scope context. Main checks commit scope, merges
only into the feature integration branch, and runs final native checks.

## 0. Verify account picker (already implemented)

Read-only verification of existing account labels, printable uniqueness,
default-name reservation, reordered/duplicate paths and binding identity/PTY
selection. No source changes or invented commits. Return current clean base
HEAD as the verified snapshot with observed tests and explicit verification-only
summary. Parent accepts that evidence before dispatching implementation.

## 1. Session progress

Create focused transcript/checklist modules (e.g. transcripts.py and
session_progress.py), tests and Progress integration. Progress receives the
explicit main binding file and verifies identity before reading that session.
Use actual successful native checklist events (Codex update_plan; Claude
TodoWrite/TaskCreate/TaskUpdate where observed). Inspect real recorded structures;
do not assume shell output or assistant prose is a native checklist.

Bounded incremental reads, matching tool results, inode/truncation recovery,
partial trailing JSON, sidechain exclusion, stale/new-turn handling and duplicate
replay. Keep no-checklist, loading, unsupported and unavailable distinct from
0%/100%. Native current checklist shows counts/bar/current step. Preserve run
states and independent project progress; never substitute project TODO for the
conversation checklist. Test adapters on redacted genuine records when available,
plus adversarial/partial fixtures and live PTY refresh. No Left Undone store use.

## 2. Artifacts

Create artifacts index/UI modules and tests; use session reader where useful.
Project scope includes canonical repo and verified owned run worktrees with the
same Git common directory. Automatically detect confirmed file changes from
successful correlated tool records and verified run-result Git commits. Support
the real Codex orchestration wrappers; tool input text, read-only commands,
quoted patch examples and failed writes alone are not proof of a change.

A bounded filesystem baseline may identify otherwise unseen project changes,
but label unproven authorship explicitly; never attribute every concurrent disk
change to the active AI. Explain unsupported write paths/coverage honestly.
No JS/Python/shell from a transcript is executed. Keep source/time/agent/evidence
and short factual English descriptions without per-file model requests or
invented semantic purposes. Retain history and missing-file state, deduplicate
replay and isolate projects. Don't import an entire initial tree as new artifacts.

Click/Enter reveals a current, scope-validated file in the existing unique
positive Yazi client; never broadcast0 or open a nested Yazi. Allow a verified
worktree path with an explicit not-yet-integrated label, reject traversal and
symlink escape. Keep preview entries as labelled migration/fallback, not false
automatic discoveries. Tests include real isolated Yazi PTY, spaces, failed and
read-only calls, wrapper records, duplicate replay, deleted files, project
isolation and verified-commit coverage. State lives only under Watchdog state.

## 3. Durable project completion history

Create history.py (or equivalent) and integrate confirmed todo.change actions,
external snapshot observation and project section of Progress. Own stdlib SQLite
or journal only; never Left Undone/global activity DB. Preserve original TODO
text/format and backups. Stable event identity must survive line moves/pruning;
replay cannot duplicate completions. Import existing Done as a labelled baseline.

Show recorded completed work versus current open work, with the denominator
policy in plain English; scope changes can change the ratio. Pruning Done must
not erase prior completions. Reopening, duplicate titles and renamed/deleted
rows need explicit conservative semantics, not fuzzy matches or invented Done.
Confirmed edits and crash/retry/history-write failures must be recoverable and
visible. No completion from model proposals, dispatch or process exit.

Test persistence/reopen, Done pruning, replay, duplicates/rename ambiguity,
project isolation, interrupted write and concurrent observers, with rendered
Progress using durable totals. Document limits without pretending stable IDs can
be inferred perfectly from unrestricted Markdown edits. Read-only viewers must
stay responsive when history is unavailable.

## 4. Curator evaluation on real conversations

Read-only real Watchdog conversation samples and verified outcome evidence.
Create a reproducible private corpus/evaluator, tests and a concise report;
redact only tracked fixtures, retain provenance/hashes privately. Don't commit
raw conversations, accounts, credentials or global personal history. Synthetic
controls remain explicitly synthetic. Never adjust expected labels to fit output.

Use existing Codex gpt-6-luna/low curator with tools off, up to8 bounded model
requests for this evaluation; no extra interactive actors. Include real Done,
concrete Blocked, pending/unmentioned, negation/quoted examples, stale/already
closed tasks and evidence rejection. Separate reader end-to-end coverage from
semantic review of extracted real utterances. Report sample counts, provenance,
raw versus accepted actions, false positives/negatives, invalid quotes and limits.
If real sources for a category are absent say so rather than call invented text
real. Preserve evidence validation, cache identity and explicit confirmation;
automatic task changes stay disabled regardless of measured accuracy.

Small general fixes discovered by evidence belong to curate.py/tests with RED
regression. Do not silently turn evaluation into broad verifier redesign or
claim universal quality. QA independently reviews gold labels and results.

## Finish

Each task returns full commit SHAs and observed tests, short human summary,
delivery metadata in separate fields. If sandbox protects shared Git, use the
already approved temporary-clone/verified-bundle delivery, based at the exact
published current task base. Main verifies byte-identical source, imports,
synchronizes only owned branch/index without editing source, accepts result and
explicitly dispatches the next contract. Keep worktrees clean; no REPORT.json.

Relevant test cycle: default suite; affected real PTYs; owned wd-test/Gossip native
suite. No fake pass when source/evidence is missing. Final QA is exact candidate,
then main approves only the run; project TODO completion and target merge remain
separate confirmations. No automatic repeated work for delayed notifications.
