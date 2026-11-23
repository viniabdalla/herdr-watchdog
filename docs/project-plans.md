# Explicit project plans

`watchdog project-plan --repo PATH --source plan.json --format watchdog-plan-v1`
reads an explicitly selected JSON file inside that project (maximum 256 KiB,
100 tasks). Add `--human` for a readable preview. Output JSON contains contracts,
source/TODO digests and `authorized: false`; commands in tests are data. No model,
conversation import, actor, assignment, TODO edit or command execution occurs.

```json
{"format":"watchdog-plan-v1","tasks":[{"id":"9f4cdfb9-3b30-4d69-a178-aa3ff61301a6","allowed_files":["src/app.py"],"acceptance":["Describe observable behavior"],"tests":["python3 -m unittest"],"dependencies":[]}]}
```

IDs must already be open canonical UUIDs in the selected project's version-1 TODO.
Titles and summaries come from that reader, not inferred conversations. Every task
has explicit files, acceptance, tests and dependencies. Duplicate JSON fields/IDs,
unknown/closed IDs, missing scope, escapes, symlinks, unknown dependencies and cycles
are refused. All open dependencies must be included so edges remain inspectable.
`--expected-digest HASH` rejects a changed plan. `assert_current(repo, preview)`
rechecks both source and TODO before a caller considers a preview reusable. Output
is bounded by input/collection limits and a 1 MiB serialized output cap. Authorizing work or changing TODO still
requires the existing separate human-confirmed APIs; reading a plan grants neither.
