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

## Affirmative causal grammar after the negated-cause review

Review `bae8acd2-06f1-4fd4-8810-b03f455f7583` of parent
`8688e258ef7f07c4a3959430d252b70e3867e847` demonstrated two further false positives:
`credentials never expired` and `no permission is required` still contained keywords
accepted by the previous cause search. Both literal replies were reproduced RED in
TODO v0/v1 with Codex/Claude records, including direct validation, supplied replay and
application. The correction replaces keyword presence with **full-clause matching**
of a finite affirmative grammar, rather than adding two negation exclusions.

Declared English resources are credentials, login, access, permission and approval
(with the supported singular/plural forms and optional `the`). Supported affirmative
states are expired, missing, denied, unavailable, offline, pending and required, with
an optional explicit auxiliary such as `is`, `are`, `was`, `were`, `has` or `has been`.
Examples: `credentials expired`, `credentials are missing`, `access is denied`,
`permission is required` and `approval is pending`. Explicit forms such as
`missing credentials`, `waiting for approval` and `awaiting permission` are supported.

Portuguese forms cover the named resources credenciais, login, acesso, permissão and
aprovação, optionally with an article and a supported copula, followed by the declared
affirmative states (for example expiraram, expiradas, ausentes, faltando, negado,
indisponível, pendente, necessária). Examples include `as credenciais expiraram`,
`o acesso foi negado`, `permissao necessaria`, `aprovacao pendente`, `faltam credenciais`,
`falta de acesso` and `aguardando aprovacao`. Case and accents are normalized for matching.

`no access` and `sem acesso` are **specific allowed absence forms**: lack of access can
be the reported impediment. They do not authorize arbitrary negative clauses such as
`no access is needed`, `no permission is required`, `credentials never expired`,
`credentials aren't missing`, `credenciais nunca expiraram`, `nenhuma permissao e
necessaria` or `permissao desnecessaria`. Extra words, negations or unknown modifiers
prevent a complete match. The reason must still equal the complete supported cause.

The outer statement must itself affirm a current task-specific blocker. Supported
inability predicates use explicit action verbs (run/proceed/continue/start/execute/
connect/deploy/authenticate, and the declared Portuguese counterparts). `cannot fail`
and `cannot not run` do not assert one of these supported inability statements.
Word boundaries prevent malformed `blockedby` from becoming an affirmative claim.

The same finite-context check applies to relevant **whole-reply** sentences. Another
explicitly named TODO task retains its own context. Otherwise each relevant sentence
must be a supported current blocker statement or an affirmative causal clause; unknown
unscoped context stays uncertain. Thus an accepted initial cause cannot hide
`Credentials never expired.` or `No permission is required.` after the selected quote,
or a contrary clause after a semicolon. This intentionally withholds some legitimate
replies containing unrelated unscoped narrative; the human must review or obtain a
clearer source reply. Existing resolution, contradictory-state, fabricated-reason,
stale-source/recipient and confirmation checks remain in force.

Disposable regressions cover never/not/no/isnt, Portuguese nunca/não/nenhuma/
desnecessária, the declared missing/expired/denied/permission/approval vocabulary,
accepted absence forms, unknown predicates, and context outside the selected quote.
All three validation/application paths run on both TODO and native-record formats.
These tests establish deterministic grammar behavior, not universal language
understanding, external truth, live model inference, or acceptance of the real task.
No real proposal was applied and no new model was invoked.

## Complete normalized reply admission

Review `37348a55-c5ed-46b3-bc3c-15bbf7d3997d` of parent
`ec9fa49f5aa0b62b64a2972df63cb6a113d018b7` reproduced another context bug: the reader
kept only the last 12,000 characters of a completed reply. A contrary prefix could
therefore disappear while its affirmative suffix reached review and application.
The eight done/blocked × TODO v0/v1 × Codex/Claude cases were reproduced RED before
correction. A suffix is no longer considered a completed reply.

Admission is now explicit: at most **12,000 Unicode code points in the complete
normalized reply**, inclusive. This uses Python string length, not UTF-8 bytes or
rendered graphemes. 11,999 and 12,000 are admitted; 12,001 is refused with
`Completed reply exceeds 12000 normalized Unicode characters; no proposals admitted`.
No prefix, suffix, or other excerpt is selected to fit. Accented letters and emoji
are tested with their actual code-point lengths. Existing Markdown normalization
removes presentation emphasis/inline backticks and closed fenced examples and converts
line endings; the cap applies after that normalization. It does not strip substantive
prose or truncate for size. An unclosed normalization fence is ambiguous/incomplete
and is refused rather than silently dropping the rest of the reply.

The reader first selects the **latest complete native reply**, then normalizes and
admits that entire reply. If the latest reply is too large, it refuses instead of
falling back to an older eligible reply. A later small completed reply can be admitted
normally even if an earlier one was oversized. Empty latest prose supplies no reply,
not an older fallback. Direct `validate_proposals` callers must supply the complete
normalized prose; the function independently enforces its size before validating any
proposal. Internal `validate_existing`, `review` and `apply_review` always re-read the
complete bound source and enforce admission. Cached or adulterated result metadata
cannot authorize an oversized current source. Model generation is never called for
an inadmissible reply, and the existing Tasks UI displays the unavailable reason
without starting review or changing TODO.

The independent transcript intake bound remains **4 MiB of raw JSONL evidence**, not
12,000 bytes. The shared bounded tail reader supplies complete records and explicit
partial/malformed flags. If no complete selected reply fits that window, the curator
reports unavailable; it does not use a JSON fragment or substitute an older reply.
Partial or malformed source also fails closed. The bounded window may omit older
conversation records: this feature validates the latest completed reply, not the
entire conversation's history. Freshness context now retains transcript file
identity, window start and file size as well as binding and tail digest, so identical
repeated bytes after growth/replacement do not masquerade as the same source.

Disposable regressions cover normalization, multibyte text, all admission boundaries,
contrary prefixes, old/adulterated results, direct/latest/replay/review/application
paths, both TODO/native formats, later recovery with a small reply, raw record/window
limits and unresolved fences. Model calls are mocked or asserted absent. A test of
the existing Tasks UI state checks that the reason is surfaced and no review or task
write occurs; no UI production file was changed. These establish bounded admission
and freshness behavior, not external truth, universal language understanding, live
model inference or human acceptance. No real proposal was applied.
