---
name: religar
description: Use when invoked with a Watchdog Religar attempt reference in the chosen Codex conversation.
---

Receive exactly one `<ref>`: 32 lowercase ASCII hexadecimal characters. If missing
or invalid, report the error and stop.

1. Publish exactly `LU-<ref>` as a commentary message in this conversation,
   substituting the supplied reference. Finish publishing before running step 2.
2. Execute `watchdog religar <ref>` in this conversation's real tool environment.
   Preserve CODEX_THREAD_ID and the active account environment.
3. Report the command result. A failure is a failure; the command owns identity,
   registration and persistence. Never infer success from the marker alone.
