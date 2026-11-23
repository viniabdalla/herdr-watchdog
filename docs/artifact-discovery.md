# Conversation artifact evidence

A bound Artifacts panel now discovers paths from the exact verified conversation
instead of the manual preview JSON. `watchdog artifacts --repo PATH --binding-file
PATH` prints the same bounded evidence as JSON. Session/project association is
verified before and after discovery. Only complete tool-call/result pairs count.

Supported evidence: successful Codex apply_patch, a literal host wrapper consisting
only of `text(await tools.apply_patch(JSON_STRING));`, and successful Claude
Write/Edit/MultiEdit. Arbitrary shell commands, prose and Git changes are not path
attribution evidence. Unsupported operations remain unproven. A 4 MiB transcript
tail and 8 MiB per-file read limit bound work; truncated/malformed/partial records
are labelled. This is not a complete accounting of every historical operation.

Each artifact retains operation, relative path, conversation identity, source digest,
byte-offset/record-digest references and actual current filesystem state/digest.
`successful-tool-path; current-bytes-unproven` means that the AI tool touched that
path, not that every current byte is AI-authored. A later human edit may exist.
Renamed sources and deleted paths remain missing entries without reveal actions.
Outside-project paths, symlinks and nonregular/hardlinked files are withheld or
unavailable. No source is modified and no transcript is copied into the project.

Enter/click still sends `ya emit-to CLIENT reveal PATH` to the linked Files pane.
Bound use verifies stored client equality, pane identity and foreground Yazi command
before reveal. Receiver zero, missing clients and replaced processes are refused.
Artifacts remains open. Unbound manual preview behavior is retained for disposable
preview fixtures, explicitly labelled manual.

The actual Yazi keyboard/click tests use disposable PTYs and a private runtime
directory, avoiding the host socket's read-only sandbox. They test actual Yazi,
not a mocked reveal. Model authorship and a live host binding remain separate
checks; the worker's sandbox cannot see the host PID needed for native verification.
