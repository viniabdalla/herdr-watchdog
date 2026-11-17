# Herdr Watchdog — v1 spec and handoff

Written by Claude on 2026-11-16, after reading `herdr-watchdog-concept.md` and `review-claude.md`, inspecting Herdr 0.9.1, Left Undone and git-todo on the machine `tropico-2`, and asking Vini four questions.

**Status: draft. Vini has not approved the build yet.** Sections 2 and 4 are his decisions. Section 3 holds assumptions he has not confirmed. Sections 7 to 9 are a proposal: how to program it is the coder's call, as the concept file says ("Programming is your decision. Managing is mine.").

## 1. What Watchdog is

Working with AIs in a terminal gets messy: what was done, what is left and what is waiting on Vini get buried in the scroll. Watchdog is a Herdr plugin that opens a set of panes around an AI conversation to keep that organized.

- It is built on top of tools that already exist (Left Undone, Herdr's own features, the `TODO.md` files), not from scratch.
- Everything shown to Vini is in plain language. He manages; the AIs program.
- Detecting "stuck" agents is a possible later feature, not the core.
- Other people who work with Vini are expected to use it later, so installation must stay simple.

## 2. Decisions made by Vini (2026-11-16)

| Topic | Decision |
|---|---|
| Default layout | Preset 2, "Column + bottom strip" (section 4) |
| Other layouts | All four presets are kept. He picks one in the terminal with a picker: list on the left, a drawing of the selected layout on the right, Enter applies |
| Artifacts | Every file an AI created or changed, each with one plain-language line. Example: "review-claude.md: Claude's opinion on the concept" |
| Progress | Both sources: the checklist the AI makes for itself while working, and the project's `TODO.md` |
| Session vs. global | His words: "some windows are just for a conversation with notice of what we need globally.. there would be panes for a session and panes for global tasks" |

How that last answer was read:

| Pane | Follows | Shows |
|---|---|---|
| Left Undone (exists) | the conversation | open tasks and promises, as today |
| Progress, top half | the conversation | the AI's current checklist: step N of M, bar, current step |
| Progress, notice line | the project | for example "Projeto: 2 com você · 5 abertas · 1 bloqueada" |
| Progress, bottom half | the project | `TODO.md`: in progress, next, blocked, done |
| Artifacts | the project | files touched by any AI, tagged Claude or Codex, one-line summary |
| Files | the project | yazi opened at the project folder |

## 3. Assumptions Vini has not confirmed

Ask before relying on any of these.

- "Global" means the whole **project folder**, not all projects. (git-todo in the Omarchy bar already covers all projects.)
- Panel text is in **Portuguese**, like Left Undone and git-todo.
- This folder becomes a git repo with a `TODO.md` in his standard format, so Watchdog tracks its own development (concept point 6). His global rule: create `TODO.md` only when he asks, and commit only when he asks.
- Watchdog is its own plugin and reuses Left Undone's panel instead of copying its code.

## 4. Layout presets

All four are saved as presets. Preset 2 is the default.

**1. Right column**

```
┌───────────────────┬─────────────┐
│                   │ LEFT UNDONE │
│                   ├─────────────┤
│  AI CONVERSATION  │ PROGRESS    │
│                   ├─────────────┤
│                   │ ARTIFACTS   │
│                   ├─────────────┤
│                   │ FILES (yazi)│
└───────────────────┴─────────────┘
```

**2. Column + bottom strip (default)**

```
┌───────────────────┬─────────────┐
│                   │ LEFT UNDONE │
│  AI CONVERSATION  │             │
│                   ├─────────────┤
│                   │ PROGRESS    │
├─────────┬─────────┴─────────────┤
│ARTIFACTS│ FILES (yazi)          │
└─────────┴───────────────────────┘
```

**3. Separate Watchdog tab**

```
TAB 1                 TAB 2 (Watchdog)
┌──────────────────┐  ┌─────────┬─────────┐
│                  │  │ LEFT    │PROGRESS │
│ AI CONVERSATION  │  │ UNDONE  │         │
│                  │  ├─────────┼─────────┤
│                  │  │ARTIFACTS│ FILES   │
└──────────────────┘  └─────────┴─────────┘
```

**4. Slim column + tab**

```
TAB 1                      TAB 2
┌──────────────┬────────┐  ┌─────────┬────────┐
│              │ LEFT   │  │         │        │
│ AI           │ UNDONE │  │ARTIFACTS│ FILES  │
│ CONVERSATION ├────────┤  │         │ (yazi) │
│              │PROGRESS│  │         │        │
└──────────────┴────────┘  └─────────┴────────┘
```

Picker behaviour wanted: a command opens the picker; arrows or `j`/`k` move through the list; the drawing on the right follows the selection; Enter applies the layout and remembers it as the default. A direct form (`watchdog layout <name>`) applies a preset without the picker.

## 5. Not in v1

- Alerts for stuck agents.
- Dependencies between tasks.
- The "framework" for extra utilities (concept point 7).
- Sync between PCs.
- `vim-motions-mix/` is a different project. Leave it alone.
- Line 30 of `herdr-watchdog-concept.md` is a cut-off duplicate of line 32. It is Vini's text. Do not edit it.

### agent-gossip, for later

Vini pointed to a friend's repo, `github.com/agent-habilis/agent-gossip`, as a possible orchestration piece.

- What it is: AIs in different terminals talk to each other, hand out tasks with dependencies, and run "one orchestrator, several workers". Rust, MIT, has a CLI and an MCP server. Not installed on `tropico-2`.
- It is the doing layer; Watchdog is the watching layer. They fit together instead of overlapping.
- It is the natural source for two things left out of v1: task dependencies, and a "team" pane showing which AI works on which task.
- Only its README and one team definition were read. Its commands for reading shared state and task status are not checked yet.
- To keep the door open, make each data source in Watchdog its own module, so a gossip source can be added without touching the panes.

## 6. Facts checked on tropico-2 (2026-11-16)

Re-check anything you rely on. The installed binary is the authority: `herdr --help`, `herdr <group>`, `herdr api schema --json`, `herdr --skill`.

### Herdr 0.9.1

- **Socket API.** `~/.config/herdr/herdr.sock`, one JSON object per line: `{"id": "...", "method": "...", "params": {...}}`. Tested with `layout.export`.
- **`layout.export`** (params `tab_id` or `pane_id`) returns the tab as a tree. Real result for a tab with a conversation and Left Undone:
  ```json
  {"type":"split","direction":"right","ratio":0.67,
   "first":{"type":"pane","pane_id":"wD:p1","cwd":"/home/tropico/Projects/herdr-watchdog"},
   "second":{"type":"pane","pane_id":"wD:p3","label":"Left Undone","command":["python3","left-undone","panel"]}}
  ```
- **`layout.apply`** takes `root` (the same tree shape), plus optional `tab_id`, `workspace_id`, `tab_label`, `focus`. A pane node accepts `pane_id`, `command`, `cwd`, `env`, `label`. A split node needs `direction`, `ratio`, `first`, `second`. **Read from the schema only; never called.** There is no CLI command for it, only the socket.
- **Plugin manifest** (`herdr-plugin.toml`) can declare `actions`, `panes`, `events` (each with `on` and `command`), `startup`, `link_handlers`, `build`.
- **Plugin panes:** `herdr plugin pane open --plugin ID --entrypoint ID [--placement overlay|popup|split|tab|zoomed] [--target-pane PANE] [--direction right|down] [--cwd PATH] [--env KEY=VALUE] [--focus|--no-focus]`. A plugin pane process has `HERDR_PLUGIN_ENTRYPOINT_ID` in its environment.
- **Events:** `events.subscribe` and `events.wait` exist. Event kinds include `pane_agent_status_changed`, `pane_created`, `pane_closed`, `layout_updated`.
- **Agent states:** `idle`, `working`, `blocked`, `done`, `unknown`. `herdr agent list` and `herdr pane list --workspace ID` return JSON with the agent kind, session id, cwd and status.
- **Caller context:** every managed pane has `HERDR_ENV=1`, `HERDR_WORKSPACE_ID`, `HERDR_TAB_ID`, `HERDR_PANE_ID`.
- **Tools present:** `yazi`, `nvim`, `bat`, `fzf`, `lazygit`. `glow` is not installed.

### Left Undone (`~/Projects/left-undone-herdr`, plugin id `left-undone`)

Read its `CLAUDE.md` first; it explains the architecture in one page.

- Python 3.10+, standard library only, curses panes, one SQLite file.
- `left-undone list --repo <folder>` prints verified live sessions as JSON under `sessions`, and the reasons others are unavailable under `unavailable`. Each session carries at least the agent kind, session id, pane and `history` (the path of the conversation record). Run it to see the exact shape.
- `left-undone open --pane <id> --session <id>` opens its panel beside that pane, or reuses the open one, and prints the pane id (`left_undone/app.py: open_panel`).
- Identity of a conversation is the hard part and still has open bugs after `/new` and `/resume` in Codex (its `TODO.md`). Do not re-solve it; call the commands above.
- Record reading: `left_undone/core.py`.
  - `Collector.poll` reads the JSONL record incrementally with a cursor (offset plus file identity), complete lines only.
  - `task_events` holds the checklist rules: Claude `TodoWrite`, `TaskCreate`, `TaskUpdate`; Codex `update_plan`.
  - Claude sidechain rows are ignored.
- Left Undone stores checklist items only as open or done. It does not keep "in progress" or the latest full checklist, so Watchdog needs its own small reader for the progress bar.
- Database: `~/.local/state/left-undone-herdr/state.db` (WAL). Tables `items` (`session`, `origin`, `text`, `status`) and `project_sessions` (`session`, `project`). Shared project tasks have `origin` in `task`/`import`. Tasks owned by Vini start with `VOCÊ · `.
- AI calls: `left_undone/runtime.py: Analyzer.command` runs the logged-in CLI (`claude -p --model haiku` or `codex exec`) in a temp dir with tools, hooks and MCP off, at low effort. Vini uses several Claude and Codex accounts, so the account matters.
- Packaging to copy: `herdr-plugin.toml`, `install.py`, `uninstall.py`, the `left-undone` launcher.

### git-todo (`~/Projects/git-todo`)

- Defines the `TODO.md` format (YAML header, then `Em andamento`, `Próximo`, `Bloqueado`, `Feito`) in its README.
- Section headings are matched by keyword in Portuguese or English in `bin/gittodo.jq` (`section_kind`). Use the same buckets.
- `Feito` keeps only the last 10 items, so "done ÷ total" from `TODO.md` is not a true project percentage. Show counts per section and say what the bar measures.

## 7. Unknowns to settle first

Settle these in a throwaway session (`herdr --session wd-test`), never in Vini's real session.

1. Can `layout.apply` mix existing panes (the conversation, Left Undone) with new panes that run a command? If not, fall back to a sequence of `plugin pane open --target-pane --direction` and `pane split --ratio`.
2. Which environment variables does a plugin **action** receive to know the focused pane and workspace?
3. How is the second tab created for presets 3 and 4?
4. What does a Codex record look like when Codex creates or edits a file (`apply_patch`)? Check a real record before writing the parser. For Claude it is a `tool_use` block named `Write`, `Edit` or `NotebookEdit` with `input.file_path`.

## 8. Proposed build

Plugin id `watchdog`, Python standard library only, same style as Left Undone.

```
herdr-plugin.toml        actions: open, layout · panes: progress, artifacts, layout-picker
watchdog                 launcher script
watchdog_app/
  app.py                 CLI: open | layout [name|--list] | panel progress|artifacts | collect
  herdr.py               wrapper for the herdr CLI + socket call for layout.apply / layout.export
  layouts.py             the 4 presets as data: name, description, drawing, pane tree
  picker.py              curses picker with the drawing on the right
  transcripts.py         incremental reader of Claude and Codex records
  todo_md.py             TODO.md parser
  left_undone.py         read-only queries on Left Undone's database
  summarize.py           one-line summaries through the logged-in CLI
  store.py               Watchdog's own SQLite in ~/.local/state/herdr-watchdog/
  panels/progress.py
  panels/artifacts.py
tests/
install.py, uninstall.py
README.md (Portuguese), CLAUDE.md, AGENTS.md, TODO.md, .gitignore
```

Steps, each one usable on its own:

1. **Spike.** Answer the four unknowns in section 7. Write down what was found.
2. **Skeleton and layouts.**
   - Manifest, launcher, `install.py`.
   - `watchdog open`: find the conversation, ask Left Undone to open its panel, apply the default preset with yazi and placeholder panes.
   - `watchdog layout`: the picker, and the direct form.
   - Switching layout closes and reopens only panes Watchdog created, tracked by pane id and terminal id.
   - From here on, Watchdog is used on its own development.
3. **Progress pane.**
   - A collector per conversation reads the record and keeps the latest checklist.
   - The pane draws the bar and current step, the notice line, and the `TODO.md` sections with in-progress and blocked items first.
   - Must work with no internet; no AI call is involved.
4. **Artifacts pane.**
   - The collector also records file touches.
   - The list appears immediately with file, who and when.
   - Summaries are requested once per finished turn for new or changed files, then cached by file content.
   - If the AI call fails or there is no internet, the list stays, without summaries.
5. **Wrap-up.** README in Portuguese, `CLAUDE.md`, `AGENTS.md`, `TODO.md`.

## 9. Rules while building

- Experiments run in `herdr --session wd-test`. Never stop the Herdr server, never close panes, tabs or workspaces you did not create.
- Never write to Left Undone's database or state folder. Open it read-only (`file:...?mode=ro`).
- Tests use a temporary state folder (`WATCHDOG_STATE_DIR`) and fixture records, never real state.
- No `.venv`, `node_modules` or build output is needed; the standard library is enough.
- No commit, no `git init`, no `TODO.md` until Vini says so.
- Text for Vini is short and in plain language: the technical label first, then what it means for him.
- Do not treat the "how things work" guesses in the concept file as facts. What he wants from the program is the part to trust.

## 10. How to check it works

- `python3 -m unittest discover -s tests -q` covers record parsing (Claude and Codex fixtures), `TODO.md` parsing, layout trees, the summary cache, and pty tests for both panes and the picker.
- In `wd-test`: run `watchdog open`, check the tree with `layout.export`, read each pane with `herdr pane read`, switch through all four presets, close and reopen.
- In a real project workspace, with Vini's ok: the checklist bar moves as steps complete, files created during the work show up in Artifacts with a readable summary, and Left Undone keeps working unchanged.
- Left Undone's own test suite still passes.
