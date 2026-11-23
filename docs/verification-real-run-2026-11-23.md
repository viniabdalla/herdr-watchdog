# Real Mission Control run: observed evidence, 2026-11-23

Run `cb0a2492-8455-45ed-ba2b-1b3b39638fdb`, worker attempt
`b70d16e7-b03b-4b02-9d2b-11969a066b0a`, base
`4803b90686c032080e0ea689f1d9c95f188f1abf`. This is one logical six-member
bundle. Dispatch, result delivery and run approval never close project TODO tasks.

Read-only reproduction from the candidate worktree:

```sh
python3 -B -m watchdog_app.verification \
  --run cb0a2492-8455-45ed-ba2b-1b3b39638fdb \
  --state-dir /home/tropico/.local/state/herdr-watchdog/runs \
  --observations /home/tropico/.local/state/herdr-watchdog/runs/cb0a2492-8455-45ed-ba2b-1b3b39638fdb/progress-observations.jsonl
```

The observer reads bounded regular files and emits source SHA-256s. It performs no
assignment, verification request, approval, merge, push, pane operation or TODO write.
The observation file was explicitly supplied by the coordinator. It is a host event
record, not evidence manufactured by tests. Ledger assessments attest only to what
these durable records show; they are not kernel/model execution attestations.

Worker observation at `2026-11-23T15:12:08.453485+00:00`:

- Preparing was recorded during launch operations, then Running at phase active.
- Initial requested state was `stalled` at epoch `1795446230.0741916` before launch;
  retain this observation rather than silently converting it to Preparing.
- Latest tasks were working. Candidate was null, QA absent, integration absent.
- Missing: Verifying and Waiting for approval. `complete: false`.
- Observation file digest:
  `3a6e40f67681a81a2fb3babe34c8112fb857d63dbadaff3d6524b6f8de6f14f3`.
- Ledger snapshot digest:
  `84767a9c53d484b5d76ed070adc34f718204bba5fdd5a97ac7d4af0d6efe655d`.

The real participant enrollment and working report succeeded through the scoped host
bridge. Working event `ba69ff92-42a3-42c7-b868-ad6ecafc9799` returned persisted true
and notification sent. The worker first encountered a busy receive operation, then
received queued contract sequence 1. No message was injected into a pane and no
additional actor/conversation was created.

A native host-PID verification from inside the sandbox failed because
`/proc/3300107/stat` is not visible there. This is an observed environment boundary,
not proof the host worker exited. Real-source curator replay is documented separately
in [curator-validation.md](curator-validation.md); successful live model curation and
actual installed-agent rule reading remain unperformed.

The actual Yazi PTY tests initially failed with `Cannot emit command: Read-only file
system (os error 30)` when using the host runtime socket. Isolating the tests' runtime
in their disposable fixture directory made keyboard and mouse reveal pass. This
observes real Yazi behavior in PTYs, without altering the existing approved panes.

## Coordinator continuation after the exact-candidate gate

This section deliberately contains no claimed completed future gate. After worker
result and independent QA, the coordinator appends actual timestamped observations
with `status: verifying`, then `status: decision` and the exact `candidate` SHA to
the supplied JSONL when each corresponding state is observed. Record run ID, candidate,
review contract/result version and evidence reference. A blocked decision is not an
approval stage. Re-run the observer against the saved ledger.

Waiting for approval requires passing independent QA whose candidate, review ID,
verified commits and result version match the current review contract and every
returned result. Only main may invoke the existing mission approval after that gate.
After approval, the saved integration record must match the candidate and a valid
integrated head. Report push outcome separately (`pushed` can remain false). Fixtures
exercise matching/mismatching candidates, stale versions, ordering and partial logs;
they do not establish that these future live stages happened.
