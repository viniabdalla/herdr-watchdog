# Gossip identity and the Codex sandbox

Watchdog uses one Gossip peer for each verified Codex conversation. The leader
coordinates through its own peer. It never publishes using a worker's nickname.

The host wrapper first starts Codex, then checks its native account, thread,
terminal, PID and process start. It binds Gossip to that frontend, not to the
wrapper. Each participant enrolls, receives tasks and reports through its own
host wrapper's typed Unix socket. The sandbox keeps its original
`CODEX_THREAD_ID`; Watchdog does not expose the host `/proc` or relax Gossip.

The bridge accepts only enrollment, receiving events, and structured reports.
It checks the socket's real peer credentials and a process ancestry ending at
the exact pinned frontend PID and start time. A shared app-server ancestor,
same UID, or a claimed thread in a payload is insufficient. Unsupported runtimes
are refused. The normal native conversation and Graph checks remain in place.
The host pins the peer key, account, terminal, thread, boot and context generation.

The context registry is mutable. Before a finite Gossip command, the bridge
holds a shared lock on the same private canonical lock file that Gossip's Rust
`bind` locks exclusively. It revalidates the pinned generation after acquiring
that lock and retains it until the command finishes. A changed generation is
rejected rather than adopted. Private snapshot paths are not accepted by the
installed Gossip CLI. Receiving events uses a short poll, not an unbounded
long-poll holding the context lock.

Sockets live in the private run folder, use mode 0600, limit requests and replies
to 128 KiB, and allow at most two active handlers. Payload reads time out after
five seconds. Context-lock acquisition times out after two seconds. Gossip
subcommands have finite subprocess timeouts. The client waits at most 60 seconds;
an uncertain report is inspected, not blindly repeated.

This isolates cooperative local agent sessions. It is not a security boundary
against malicious code with unrestricted access to the same host UID. Such code
could modify processes or private files belonging to that same Unix user,
independently of Watchdog.

The wrapper restores terminal kernel modes, mouse capture, keyboard reporting
and the alternate screen even if its Codex child exits without TUI cleanup.
Recovery resets the owned terminal through its output descriptor, not by typing
escape sequences into the shell. It preserves conversation IDs, branches,
worktrees and prior launch records. No delivery marks project TODO tasks done.

## Current validation

Unit tests cover frontend ancestry, shared-server rejection, wrong user/thread,
PID reuse, child exit, stale context generation, Python/Rust lock interoperability,
leader-only registration reads, private context enrollment and real PTY mode
restoration. Native run evidence is stored separately under `docs/evidence/`.
These tests do not claim support for arbitrary shared app-server deployments.
The native validation used distinct frontends. The declared thread plus frontend
ancestry does not establish isolation between multiple threads sharing one frontend.

The final additional client-PID recheck passed unit tests but is not loaded in the
currently active wrappers. Apply and test it at the next safe participant transition;
do not restart a busy worker just to load that revision. Further Gossip bridge
extensions are deferred; native Watchdog transport is the next priority.
