# Herdr Watchdog

Watch a verified AI conversation alongside project tasks, progress and artifacts.
Linux, Python 3.10+, standard library only, Herdr 0.9.1+, Yazi and `ya`.
The installed Left Undone identity engine is currently required.

## Use

```sh
python3 install.py
watchdog                       # choose the conversation if needed, then layout
watchdog layout 2              # direct preset selection
watchdog layout column-bottom
watchdog layout --list
watchdog list                  # verified conversations in the current project
watchdog status                # inspect the selected conversation without opening panels
```

Run from the project folder, or pass `--repo /path/to/project`. `--pane ID
--session UUID` selects an exact verified conversation. Missing native session
registration is reported; Watchdog never guesses a UUID from focus or cwd.
An existing Codex thread in agent-tool context is matched by CODEX_THREAD_ID.

Four presets are available; number 2 is the initial default. Arrows or j/k move
through the selector, the drawing follows, Enter applies, and Esc cancels without
changing the layout. Successful choices become the next default. All presets
reuse terminals rather than restart them. Unrelated terminals stay in place;
if they share the conversation tab, Watchdog uses a dedicated conversation tab.

The Herdr action “Watchdog: choose a layout” opens a terminal selector when the
action has no interactive terminal. Left Undone is optional as a visible panel:
if its panel is already bound to this conversation, it stays to the right of
Files. Watchdog reads that binding and never edits Left Undone's state.

## Interactive Tasks

Click a task or use arrows/j/k and Space to select it. `s` prepares a request
for the verified Codex conversation; confirm with `y`, or Esc to cancel. Requests
go through Codex's account-specific inbox using the full thread UUID. A working
conversation needs a separate queue confirmation. Tasks stay open after sending.
Claude conversations can be watched, but task delivery is unavailable until a
thread-addressed transport exists; Watchdog does not type into a pane prompt.

`d` requests confirmed completion. `i` moves to In progress; `n` moves to Next.
Section colors: Next blue, In progress yellow, Blocked red, Done green.
Edits preserve notes and completed history, retain backups under Watchdog state,
and reject stale selections. Concurrent editor saves are preserved; a conflict
requires reviewing the file again. Atomic exchange requires Linux renameat2.

The curator uses Codex gpt-6-luna at low effort, independent of the watched AI.
It checks each new completed reply against open TODO tasks and completed titles.
`r` opens suggestions, or requests a fresh review. It proposes Done, Blocked
with a reason, and explicit new tasks. Every proposal displays a supporting
quote. Apply only the proposals you select, with a separate confirmation.

The reviewer uses the current Codex login (`WATCHDOG_CODEX_HOME` can select an
account). It makes model requests; it does not inspect code or prove a completion
claim. Missing mention is not treated as a blocker. Invalid/conflicting proposals
are withheld visibly. New replies or task edits invalidate old confirmations.

## Current limits

The launcher, verified binding, four layouts and artifact-to-Yazi link work.
Tasks is interactive with confirmed curator proposals. Session progress is
manually maintained, and artifacts come from an explicit list. Automatic session
checklist reading and artifact discovery remain pending.
Other projects without the preview source files show missing-source messages;
the remaining data adapters are future work.

This project's TODO.md uses the shared git-todo section format. The displayed
project ratio counts only the currently listed tasks. It is not a prediction
of total project completion.

Runtime state and locks live under ~/.local/state/herdr-watchdog. Override with
WATCHDOG_STATE_DIR for tests. WATCHDOG_LEFT_UNDONE_ROOT can locate an engine
checkout when the left-undone command is not in PATH. No Git repo is required.

## Verify

```sh
python3 -B -m unittest discover -s tests -q
# With the disposable wd-test server running:
WATCHDOG_HERDR_TEST=1 python3 -B -m unittest discover -s tests -q
```

Live layout tests use only their own workspace in wd-test. Yazi tests use
temporary files and real PTYs. `python3 uninstall.py` removes only this checkout's
links and keeps state; it does not close running panels or stop Herdr.
