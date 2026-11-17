# Watchdog: revised scope and disposable preview

2026-11-16. This records Vini's corrections after the original v1 proposal.
The preview is disposable; it is not the finished plugin or an automatic verifier.

## Launcher milestone (subsequently approved and implemented)

The `watchdog` command and native plugin are now installed. It uses Left Undone's
verified identity engine, offers the four-layout picker, remembers the chosen
layout and reuses the running panels. The active native Left Undone panel sits
beside Files and has completed collection rounds for the current Codex session.
Tasks now supports confirmed edits, exact-thread Codex requests and curator
proposals. Progress and Artifacts retain preview sources. See README.md and
watchdog-interactive-tasks-plan.md.
Current runtime ownership is in per-binding JSON files under Watchdog's own
state folder; preview.json is the older migration snapshot, not current truth.

## Confirmed decisions

- Standalone Watchdog plugin, English panels, intended for public distribution.
- Project tasks and conversation promises are separate. Watchdog manages project
  tasks; the existing Left Undone panel is an optional complement.
- Project tasks use a TODO.md per project, with a consistent format. All sessions
  of that project share it. Creating this project's TODO.md is now authorized.
  Git initialization and commits remain unauthorized.
- Both session and project progress matter. Label what each bar measures.
- Artifacts list AI-created or changed files. Selecting an entry should allow
  inspecting it through Yazi.
- The proposed verifier always uses Codex, independent of the AI being watched.
  Start with gpt-6-luna at low effort. Free providers are deferred, not required.
- Future direction: Vini chooses whether to send a project task to an existing
  conversation or a fresh conversation carrying only the required context.
  Evaluate the friend's agent-gossip repository for clean sessions; current-thread
  dispatch is implemented.
- Keep all four presets and preset 2 as the default for the eventual plugin.
  The preview now uses preset 2 around the visible Codex conversation in tab 2
  of the herdr-watchdog workspace. Existing git-todo panes are in their original
  tabs. All terminal processes were preserved.

## Spike: tested in herdr --session wd-test

Client/server: Herdr 0.9.1, protocol 22. An isolated headless server was started;
no server was stopped. Existing real-session panes were not used for experiments.

### 1. layout.apply does not preserve the existing terminals tested

On a disposable tab with two existing shells, submitted a tree referencing both
pane IDs plus a new Python command pane. The response was layout_not_found, but
live inventory showed that the old tab and panes had been replaced. New IDs and
new terminal IDs appeared, including the command pane.

Reduced the experiment to a fresh disposable tab with one shell and a root of
`{"type":"pane","pane_id":"<existing id>"}`. This returned success, but a
different tab, pane and terminal were created. The original IDs disappeared.
Therefore pane_id references in layout.apply cannot be used to preserve a live
conversation on this installed version. Even an error can follow a mutation.

Fallback tested: pane split with an explicit pane ID, ratio and --no-focus.
The original terminal ID remained unchanged. Built the preview using only
explicit splits and commands. Proposed production change: use splits/moves and
an ownership ledger; never apply replacement trees to a live conversation.

### 2. Plugin actions have explicit context

Linked a temporary watchdog-spike plugin, only for the isolated test, and invoked
its probe action with explicit target context. The process wrote only HERDR_*
environment variables to a temporary file. Verified:

- HERDR_PANE_ID, HERDR_TAB_ID, HERDR_WORKSPACE_ID
- HERDR_SESSION=wd-test and the isolated HERDR_SOCKET_PATH
- HERDR_PLUGIN_ID, HERDR_PLUGIN_ACTION_ID, HERDR_PLUGIN_ROOT
- HERDR_PLUGIN_CONTEXT_JSON, including focused_pane_id, focused_pane_cwd,
  workspace_id, tab_id and invocation_source

This tested socket action invocation, not clicking a menu in the Herdr TUI.
Session binding must still verify the conversation rather than infer it from cwd.

### 3. A second tab can be created explicitly

Tested tab create --workspace <returned ID> --cwd <path> --label <label>
--no-focus. The response provides the tab and root pane IDs. Subsequent explicit
splits produced a four-panel tab. No tab_id was inferred from a name or number.

### 4. Real Codex patch records include an orchestration wrapper

Read local Codex JSONL records without modifying them. Here, actual patches were
response_item rows with payload.type=custom_tool_call, payload.name=exec and an
input containing JavaScript that calls tools.apply_patch with a quoted patch.
Their results were custom_tool_call_output rows matched by call_id; outputs can
be lists of content objects rather than a single string.

This differs from the assumed direct apply_patch call with JSON arguments.
The parser proposal needs revision: support the actual wrapper and successful
result correlation, not merely a text search for patch headers. Commands that
read or mention patches must not count as artifact writes. Arbitrary shell edits
are another coverage limit. No production artifact parser was written yet.

## Codex verifier probe: tested separately

Codex CLI 0.167.0 lists gpt-6-luna in the local model cache as fast and affordable.
This is not a measured price comparison across all models.

Ran one ephemeral request from a temporary directory, ignoring user configuration
and rules, disabling shell tools, hooks, MCP configuration loading, skill
discovery and web search. Model: gpt-6-luna; reasoning effort: low. Used the
current Codex login, not the watched conversation's provider.

Synthetic input: task "Run unit tests"; reply "All 3 unit tests passed. The
artifact browser is still pending." A JSON Schema required completed and evidence.
Exit code 0; completed=true; evidence="All 3 unit tests passed."; no tool calls.
This establishes working authentication, model access and structured output only.
It does not establish real-world verification quality or independent test proof.

## What the preview actually does

Run from this folder:

```sh
python3 tools/watchdog-preview.py tasks --repo "$PWD"
python3 tools/watchdog-preview.py progress --repo "$PWD"
# Use the same unique positive ID for this pair of panes:
WATCHDOG_YAZI_ID="$(date +%s%N)"
# Launch these in separate panes, supplying that same ID to both:
yazi --client-id "$WATCHDOG_YAZI_ID" "$PWD"
python3 tools/watchdog-preview.py artifacts --repo "$PWD" --yazi-client-id "$WATCHDOG_YAZI_ID"
```

- Tasks reads TODO.md; English and existing Portuguese section names work.
  Keyboard/mouse selection, confirmed edits, Codex delivery and curator proposals
  are now implemented; see README.md for controls.
- Progress reads the manually maintained docs/preview-session.json and TODO.md.
  It does not read the AI's native checklist yet. The project bar measures only
  checked tasks divided by all tasks currently listed, not total project scope.
- Artifacts reads an explicit docs/preview-artifacts.json list. It is not an
  automatically discovered history. Click a file row or press Enter to reveal
  it in the separate linked Files pane. Artifacts stays visible. Each pair uses
  a unique positive Yazi client ID; receiver 0 (broadcast) is rejected. Enter and
  simulated mouse clicks passed real-PTY tests against Yazi; a physical mouse
  click has not been observed by the agent.
- Tasks now calls Codex and writes confirmed TODO.md changes. Progress and
  Artifacts remain preview displays. No panel writes Left Undone state.
- Tested in wd-test: all panels render, checklist source changes refresh the
  progress display, Enter selects TODO.md in the separate Files pane without
  starting Yazi inside Artifacts. A real-PTY regression also checks a filename
  containing spaces and confirms q exits Artifacts directly.
- Preset 2: tested pane moves and a swap in wd-test before moving the live
  conversation and all four preview panes. Verified the exported tree and that
  every terminal ID survived; unrelated panes stayed in their original tabs.
  Artifacts and Files retained the same Yazi connection. The manual session
  checklist remains a preview; moving the conversation does not enable parsing.
- On this tooling host, inherited HERDR_PANE_ID and the session metadata on its
  idle shell were stale. The actual target was verified against the visible
  transcript and a live Codex foreground process in the herdr-watchdog workspace.
  Runtime ownership now records that explicit target; do not use --current from
  this tooling environment to locate the visible conversation.

## Build proposal after the spike

Keep the original order: layouts, Progress, Artifacts, packaging. Revise the
implementation to avoid layout.apply for live panes, add a standalone Codex
project-task verifier, and handle the actual Codex transcript wrapper. Left
Undone becomes optional. Automatic completion needs evidence validation and
real-conversation tests before it can change project tasks.

Pause after showing the preview and spike findings for Vini's approval before
building the production plugin. No plugin installation, Git initialization,
commit or production collector is implied by this disposable preview.
