# Left Undone: stale task list and Codex replay

2026-11-16. Investigation requested by Vini after the launcher milestone.
The Left Undone source was inspected without modification. Its state was read
with SQLite mode=ro; list replacement used its native UI and import command.

## Which model is running

The current verified binding is Codex. The corresponding live collector invokes
the Codex branch of runtime.Analyzer: codex exec, gpt-6-luna, low effort, current
verified account, tools/hooks/web search disabled. This panel is not using Haiku.
The separate Claude binding uses Claude Haiku by the existing plugin's design.

## What was tested

Recovered the exact final audit reply, accumulated user request and project list
immediately before that reply. Reversed its single logged wording update using
curation_changes and the original transcript timestamp; preserved status,
version, write permission and canonical flags. There were 16 context items,
13 open. Input is saved under ignored docs/evidence/curator-codex-replay-input.json.

Two explicit, read-only calls used the native Analyzer and the original curator
rules/schema, gpt-6-luna at low effort. Neither result was applied to live state.

1. The first response failed validate(): a duplicate destination was also touched
   elsewhere in the same batch. No raw response was retained from that first
   attempt because validation preceded the capture; the exception was observed.
2. The second response was captured before validation. It proposed eight done
   actions, but failed the exact evidence check. Its quote was:
   `OpenCode/OpenRouter ficou superado: você decidiu usar sempre Codex.`
   The actual reply contains Markdown emphasis:
   `**OpenCode/OpenRouter ficou superado:** você decidiu usar sempre Codex.`
   Removing the emphasis makes the quote cease to be an exact raw substring.
   This invalidates the entire batch, including unrelated valid proposals.
   The model also targeted already-closed item 122 instead of open item 124
   for the workspace correction; the application would ignore that closure.

Second output and validation error are saved under ignored docs/evidence/ as
curator-codex-replay-output.json and curator-codex-replay-validation.json.

These runs show that using Codex alone does not resolve the failure. They do not
prove the exact contents of every earlier production response: the native
curator does not retain rejected model output, and its applied-change log is not
a full model trace. The original audit logged only one wording update.

## Relevant code paths

- core.Collector.poll passes the final assistant reply, accumulated user request
  and event timestamp. It does not inspect repository files or test results.
- curation.validate rejects a batch if any quote is not an exact substring, or
  if a duplicate destination is also being changed. JSON Schema alone cannot
  enforce these cross-action/evidence conditions.
- Curator._review applies proposals only after validation and marks the event
  processed after a valid response. A valid empty or incomplete-in-meaning result
  can therefore leave real work stale without producing a technical error.
- Curator.review returns immediately for a processed event. The collector's
  collect-now request does not make it reconsider that event.
- Curator.refresh skips an unchanged list. If the list changed, it invokes the
  model with empty reply/request. Rules then allow only duplicates/conflicts,
  so it has no completion evidence for the missed deliveries.
- “Curadoria em dia” reports no pending model/list processing at that moment;
  it is not proof that the list matches the repository's implemented behavior.

The strict evidence, identity and stale-write guards serve a purpose. This
investigation did not disable them or change the model. Potential follow-up
design: bounded repair of invalid model proposals before committing a batch,
clear diagnostics for rejected actions, and an explicit reconciliation path that
can revisit recent evidence while preserving timestamps and identity checks.
No such engine behavior change was implemented in this task.

## Task list replacement

Vini explicitly requested that the stale tasks be rewritten. Saved the 13 open
entries to ignored docs/evidence/left-undone-before-reconciliation.json. Selected
them through the native panel, inspected its 13-item completion confirmation,
and clicked the confirmation button. No send-task shortcut was invoked.
Those entries were retired as superseded, not as evidence that their unfinished
features were implemented. Previous done/duplicate records were left alone.

Imported docs/reviewed-project-tasks.md through the native left-undone CLI using
this verified conversation's binding. Read-only verification found exactly
eight open imported items, IDs 130–137, matching that document. Those cover
task dispatch, automatic session progress, the Codex project verifier, real
verification tests, automatic artifacts, completed-task history, account labels
and clean-context sessions. TODO.md now includes the same eight topics.

The native UI can also record manually retired entries as status=done with
dismissed=1; that storage value should not be read as proof of implementation.
This document preserves the distinction for this explicit list replacement.
