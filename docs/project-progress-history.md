# Durable project progress history

Version-1 TODO remains authoritative. Watchdog keeps a separate operational ledger
under `STATE/project-history/SHA256(canonical-project-path).json`; this is history,
not another task list. Progress observes the current snapshot and displays the last
12 events. UUID, observation timestamp, before/after content digests, source/TODO
digests, transitions and supplied evidence survive TODO edits and process restarts.

The initial observation is dated now, including existing Done tasks. No old date is
invented from a title. Omission records `absent`, never Done. Reappearance, correction
and reopening append events. `change(..., kind='reopen')` explicitly returns a Done
task to Next, retaining its UUID. Existing backups and in-document legacy history
remain available but do not stand in for this ledger.

All writers/observers use the same per-project TODO lock. Before atomic TODO exchange,
a fsynced write-ahead intent records source/target digests and supplied evidence. A
history-write failure before exchange leaves TODO unchanged. Failure after exchange
raises an explicit pending-recovery error. On restart observation finalizes only if
TODO matches the target, or discards the intent if it still matches the source.
A third digest is a recovery conflict and blocks silently attributing another editor's
save. Recovery never changes TODO. Atomic state writes fsync content and directory.

Retries of the same snapshot produce no duplicate event. Concurrent observations
serialize. External edits are observed with evidence `external observation;
verification not established`; they are not promoted into verified completions.
The automated tests exercise concurrent observations, completion/reopening/removal,
and failures before/after exchange. Existing TODO tests cover competing saves.
A recovery conflict requires inspecting the retained intent and actual TODO; the
program refuses automatic reconciliation that could erase an unobserved transition.
