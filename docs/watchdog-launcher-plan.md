# Watchdog launcher implementation plan

Goal: typing `watchdog` selects a verified conversation and one of the four
layouts, reusing this project's preview panes. Keep the working Left Undone
panel next to Files. Automatic task verification and dispatch are later steps.

Spec: watchdog-v1-spec.md, watchdog-mvp-notes.md and Vini's subsequent approval
of conversation binding, a launcher/layout picker, and a working Left Undone.

Implementation stays in this folder: Git initialization, worktrees and commits
are not authorized. Standard library only. Herdr experiments use wd-test.
No code writes Left Undone's state; its native open command runs its own panel.

1. Binding adapter (`watchdog_app/bindings.py`, tests/test_bindings.py): load the
   installed Left Undone runtime, use candidates and verify, reject missing or
   ambiguous identity. Reuse its read-only project association lookup. Prefer
   exact CODEX_THREAD_ID when available; never infer a recipient from focus/cwd.
2. Layout controller (`watchdog_app/herdr.py`, store.py, layouts.py,
   tests/test_layouts.py): explicit native moves/splits, stable terminal checks,
   per-conversation ownership JSON and file lock. Adopt only matching preview
   state. Move panels through a temporary owned tab because same-tab move is a
   no-op. Revalidate the conversation before mutation. All four layouts retain
   the conversation process and unrelated panes; if its tab has unrelated panes,
   use a dedicated tab rather than alter their layout. Never use layout.apply.
3. CLI and picker (`watchdog`, watchdog_app/app.py, picker.py, install.py,
   herdr-plugin.toml, tests/test_cli.py): no arguments opens the layout picker;
   `watchdog layout <1..4>` is direct. Multiple verified conversations get a
   conversation picker. Show drawings, accept arrows/j/k and Enter; remember the
   successfully applied layout, default 2. English CLI, actionable missing-engine
   error. Native panel commands reuse the current preview UI and its limitations.
4. Validation: RED/GREEN unit tests per component; full suite; all four layouts
   exercised with dummy shells in wd-test, checking layout trees and terminal
   survival. Real launcher picker through a disposable PTY. Install the launcher
   and plugin, adopt the current preview and bound Left Undone, apply preset 2
   here. Recheck panel rendering, binding and native collection. A final code
   review follows before reporting completion. No task dispatch during tests.

Review focus: stale inherited pane metadata; ID reuse; mixed projects and multiple
sessions; same-tab moves silently doing nothing; interrupted layout changes;
Left Undone process identity and Yazi link surviving re-layout; caller shell or
other panes left alone. Tests use temporary Watchdog state, never LU real state.

Execution: native in-session implementation. Keep progress below; no Git ledger
scripts because this folder is intentionally not a repository.

## Progress

- Native Left Undone recovery verified the current marker, account, PID and
  transcript. Opened its panel through its CLI and moved it next to Files.
- Baseline: 3 existing tests pass.
- Binding adapter: 5 tests pass; live native recovery/list/verify agree on this
  Codex session, account, process and pane. No use of inherited pane identity.
- Layout controller: real wd-test checks all four presets, repeat application,
  unrelated-pane preservation, terminal reuse and interrupted initialization.
- CLI: keyboard picker, cancel, layout list, validation and saved preference
  tests pass. Temporary-bin install/run/uninstall passed.
- Independent reviewer found four Important issues: interrupted initialization,
  stale native companion ownership, idle companion adoption, and loss of explicit
  filters in a background picker. Regression tests failed, fixes passed; full
  suite: 20 tests. Left Undone's own suite: 117 tests pass.
- Final: fixes cover those four findings; no second reviewer was dispatched.
  Minor deferred: account labels in the conversation selector (pane and session
  are shown). Automatic tracking, dispatch and artifact discovery remain outside
  this step; real layout and native collection were verified by the implementer.
- Installed the launcher and native plugin. Applied preset 2 to the verified
  current conversation, adopting all four preview processes and the active
  Left Undone. Live captures and exported layout are under docs/evidence/.
- Installed CLI picker opened for this exact thread; Escape left the complete
  terminal inventory unchanged. No Git initialization or commits were made.
