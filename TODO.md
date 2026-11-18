---
status: ativo
area: pessoal
prioridade: alta
resumo: Herdr panels for project tasks, session progress and AI-created artifacts
atualizado: 2026-11-17
motivo:
---

# TODO — Herdr Watchdog

Each project uses its own TODO.md with these sections. Progress counts the
tasks currently listed here; it is not an estimate of the entire project.

## In progress

## Next
- [ ] Watchdog UI language: English/Portuguese selector in Tasks applies to Tasks, Progress, Artifacts and Agents; use LLM assistance for UI translations while preserving canonical project files, protocols and Yazi.
- [ ] Agents panel: show verified project agents, chronological task history, remaining context when available and verified Gossip channels; keep Artifacts adjacent, highlight task-linked artifacts and preserve the Yazi connection. Gossip remains optional.
  Show each agent's verified Herdr pane and latest task in plain English or Portuguese; display unavailable when actual context telemetry is missing.
- [ ] Plan reader: read an explicit project plan into bounded task briefs without rereading full conversation histories.
- [ ] Curator validation: evaluate Done and Blocked proposals on real conversations; keep user confirmation required.
- [ ] Artifacts: automatically discover and summarize files created or changed by the AI; preserve the working Yazi link.
- [ ] Project progress: add durable completion history for progress across TODO edits; Done entries and edit backups already exist.
- [ ] Full real Orchestrate run on the new flow: confirm with a real task and watch Preparing → Running → Verifying → Waiting for approval in Progress (not exercised live yet, to save Codex quota).
- [ ] Clean sessions UI: offer close/retry for a blocked operation instead of requiring manual state edits.

## Blocked

## Done
- [x] 2026-11-17 Flow fixes: Orchestrate shows pending changes and saves a local checkpoint commit before requesting; forgotten runs are marked Stalled and closed in Progress (x) or automatically when accepted in TODO; TODO ideas/reordering no longer block launch; run states Preparing/Running/Verifying/Waiting/Needs decision; late or superseded reports stay in history; closed leader pane is re-followed after `codex resume`. 306 tests pass.
- [x] 2026-11-17 Orchestrate checkpoint: show project changes and new files in the confirmation, save an authorized local commit before launching (no automatic push).
- [x] 2026-11-17 Clean sessions live fix: successor started with `--yolo`; operation f486dba6-d4aa-4c76-8de6-825fd47737ef completed automatic successor receipt through exact-ID ai-memory acceptance, explicit predecessor release and Watchdog binding transfer to session 01a1ec04-f266-74c1-a435-78501c4286a7 at checkpoint 1e9b0110701cc277b9c0bde46fcff1dfbf8dc30d. All 50 focused tests passed on verification. Prior blocked attempts, including f356165e approval rejection and subsequent successful acceptance, remain preserved as historical evidence.
- [x] 2026-11-17 Clean sessions workflow: automate verified Herdr split, fresh leader startup, bounded handoff delivery and explicit receipt in the handoff backend; expose a clear UI action. Reuse the observed live procedure, preserve native/legacy boundaries and leave current agents intact. Command-layer handoff alone does not complete this task.
- [x] 2026-11-17 Run scope: validate only the tasks selected for a run so unrelated TODO edits do not block active work; preserve identity, Git and exact-candidate QA checks.
- [x] 2026-11-17 Leader handoff command layer: bounded export, explicit native preview/adoption and clean-session purpose guards; P1 corrected and independently approved at 0e7125f. Host suite: 222 tests, no failures, 7 skipped. Live legacy Gossip runs remain export-only; this does not complete the UI flow.
- [x] 2026-11-17 Native transport: exact-thread Codex inbox delivery, durable local reports, duplicate protection and recovery checks; independently approved at 2cf8d68 with a real delivery/report probe.
- [x] 2026-11-17 Session progress: automatically read supported successful conversation checklist calls and refresh Progress. Unsupported or missing formats remain explicit; real local histories had no successful direct checklist pairs, so protocol fixtures were synthetic.
- [x] 2026-11-17 Conversation picker: show distinct account names before pane/session identifiers; nine focused tests including real narrow-PTY keyboard selection passed.
- [x] 2026-11-17 Task delivery validation: verify the full Codex inbox delivery and receipt in a disposable real conversation; automated UI tests currently simulate transport.
