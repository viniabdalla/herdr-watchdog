# Curator evidence validation

Proposal generation and authoritative TODO changes remain separate. The existing
Tasks confirmation screen is required before `apply_review`; cancel/empty selection
writes no task. A selected proposal is revalidated against the exact recipient,
TODO digest and completed-reply/tail source before application. The result contains
that context, so replacing an account, conversation or history invalidates it.

`validate_existing(session, snapshot, output)` evaluates supplied proposals against
the bound existing conversation without starting a model. It reports
`bounded-replay; no curator model invoked`. A normal existing curator review reports
`live-curator-model; assistant claim requires human verification`. Neither label
asserts implementation or acceptance independently of the human reviewer.

Evidence must be a literal quote from a completed assistant reply. In version 1,
completion must identify the task and contain a completion assertion. Negation,
partial/pending/failed work, contradictory statuses, duplicate proposals and unknown
or closed IDs are withheld. Blocking needs an actual stated impediment. Omission
still proves nothing. Partial/malformed transcript tails are refused. These are
conservative syntactic guardrails, not a semantic proof of every acceptance criterion;
ambiguous language can require manual review. Human confirmation remains mandatory.

Observed real-source replay in this worker conversation on 2026-11-23:

- Session `01a208ef-57df-7203-8c6c-099c5b030c06` (the enrolled worker).
- Completed reply `01a208ef-5922-7fa1-b55d-3eaaf2f4d63a`.
- Source key `df61fd3f3b714cbb96a2ce183e8d9e0af27ad866e3593a14c80bbfae33f31345`.
- A supplied completion proposal using its enrollment acknowledgement was rejected:
  `Evidence does not identify the task`. No TODO change and no model invocation.

This was a bounded replay of an actual existing reply, not a live curator output.
Disposable fixtures exercise accept/cancel, recipient/source/task staleness, partial
records, unsupported/contradictory conclusions and duplicate proposals. A real live
curator/model proposal and native binding check remain unperformed: host PID
`3300107` is outside the worker sandbox's process namespace. The coordinator can
perform the host-side check with the same existing conversation; no extra actor is
needed. A rejection replay does not establish successful live completion curation.
