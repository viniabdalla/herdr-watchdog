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

Evidence must be a literal quote from a completed assistant reply. For both TODO
formats, completion requires the **full task title or exact ID** in an affirmative
completion statement. Shared words, passing tests, saying the implementation works,
and a generic implementation report do not establish task completion. For example,
`Colors is complete.`, `Colors implemented and tests passed.` and
`Task UUID is complete.` are supported claims; `Colors tests passed.` is uncertain.

Known negations, contrary statements, partial/pending work, waiting for help with
commit/acceptance, and references to another project withhold the proposal. The
filter checks the **whole reply**, including an unquoted next sentence. An explicitly
named different TODO task can have its own blocker; unscoped caveats remain relevant
to the proposed completion. Duplicate proposals and unknown/closed IDs are withheld.
Blocking needs an actual stated impediment; omission proves nothing. Partial or
malformed transcript tails are refused. The same checks run again in `apply_review`,
so a cached/tampered action cannot bypass them by obtaining human confirmation.

This is a restricted bilingual claim grammar and conservative uncertainty vocabulary,
not universal semantic understanding or proof of every acceptance criterion. Unknown
completion phrasing stays uncertain; known affirmative phrasing can still require a
human to inspect scope, acceptance evidence and implementation. Conservative false
negatives (including unscoped caveats about other work) require manual review or a
clearer completed reply. Human confirmation is mandatory **after** this evidence
gate; it does not substitute for the gate.

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


## QA correction of the first candidate

Independent review of `d8d812068c9f4bfd7abc9a71f929a394550470d7` found that a shared
word plus `passed`/`works` and a narrow negative regex admitted these literal replies:

- `Colors tests passed, but the implementation does not work.`
- `Colors implemented. Ainda falta verificar o aceite.`
- `Colors tests passed for another project; this task has not been started.`

The correction was reproduced RED before implementation. Disposable regressions now
withhold all three, commit/acceptance-help caveats, Portuguese negations, test-only
reports, and completion of a different longer title. They exercise direct validation
and application revalidation in both TODO formats and Codex/Claude record formats.
Affirmative full-title and UUID completion claims still pass; cancellation/stale
source/recipient checks remain in place. No real proposal was applied and no model
was invoked for these regressions.

The host-supplied replay recorded in `host-source-replay.json` accepted a generic
implementation report under the earlier filter. That observation is historical and
is not evidence of live curator inference, acceptance, or the corrected gate passing.
The earlier real enrollment-quote rejection remains a bounded replay observation.
Actual installed-agent rule reading and live model curation remain unperformed;
the coordinator's host verification resolves process visibility only, not those gaps.


## Current blocking evidence and reason support

The second independent review of parent
`c4beecf44e784dd34f563ef2a5dcdd39aa5df371` found that the old blocking keyword gate
could accept a denial, an unrelated Deployment blocker, or a resolved Colors blocker,
and attach a fabricated `Waiting for credentials` reason. These cases were reproduced
RED before correction, including old/adulterated `apply_review` payloads.

A blocking proposal now requires an affirmative **current impediment** naming the
full task title or exact ID, together with a causal relation and a concrete cause.
Examples supported by the restricted bilingual grammar:

- `Colors is blocked because credentials expired.` → reason `credentials expired`.
- `Colors cannot run because login expired.` → reason `login expired`.
- `Colors está bloqueado porque as credenciais expiraram.` → reason
  `as credenciais expiraram`.
- `Colors não consegue prosseguir porque o acesso foi negado.` → reason
  `o acesso foi negado`.

The reason must copy the complete causal text, allowing normalized case/accents and
terminal punctuation; it cannot introduce a paraphrase, waiting condition or other
cause. Generic `Colors is blocked.` without a cause remains uncertain. Negation of
the blocker or its cause, known resolution/restoration claims, contrary later
sentences and other-project evidence withhold the proposal, even if omitted from the
selected quote. Unscoped contrary context stays relevant; another explicitly named
TODO task can have its own separate status. The gate runs in `validate_proposals`,
`validate_existing` and again in `apply_review` before any confirmed change.

Disposable tests cover both TODO formats, Codex/Claude records, literal QA failures,
fabricated reasons, omitted resolution, cancel, application revalidation and legitimate
Portuguese/English blockers. They do not establish external truth of an impediment or
universal language understanding. This finite grammar/cause vocabulary deliberately
withholds unknown formulations and can produce conservative false negatives. Human
confirmation follows the evidence gate. No real proposal or new model was used.
