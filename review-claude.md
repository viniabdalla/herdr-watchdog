# REVIEW — CLAUDE

Review of `herdr-watchdog-concept.md`, done 2026-11-15.
These are suggestions. Accept them, change them, or delete them with `dd`.


## Verdict

Good idea, with a real differentiator.
- left-undone answers: *"what did the AI promise and not do?"*
- watchdog should answer: *"what is stuck, and who is it waiting on?"*

That second question is the one that fixes the problem you describe.


## What is strong

- **Points 1 and 2 (me vs. the LLM):** the core of the project. Passwords, logins and test rounds are exactly what gets lost in the terminal scroll.
- **Point 6 (dogfooding):** watchdog tracks its own development from day one.
- **The intro ("managing is mine, programming is yours"):** a good contract with the LLMs. Keep it at the top.


## What I would reorganize

1. **Point 5 is the problem; points 1 and 2 are the symptoms.**
   Open the section with "things get stuck and the terminal gets overwhelming".
   Then the rest reads as "so watchdog needs to...".

2. **Take the name literally: watch the agents.**
   Herdr already knows each agent's state: `idle`, `working`, `blocked`, `done`.
   `blocked` or `done` often means **"waiting on you"**.
   Example alert: *"2 agents waiting on you for 15 min"*.
   This attacks "things get stuck" directly, with no LLM needed.

3. **Dependencies: who decides what blocks what?**
   An LLM guessing on its own will get it wrong.
   Suggestion: the LLM *proposes* ("this looks like it blocks that"), you confirm.

4. **Points 3 and 7: watch the scope.**
   Two layouts + multiple sessions + a framework = three projects.
   Start with **one panel and three blocks**:

   ```
   ┌ YOU ──────────────┐
   │ test login flow   │
   ├ LLM ──────────────┤
   │ fix export bug    │
   ├ BLOCKED ──────────┤
   │ deploy ← password │
   └───────────────────┘
   ```

   Layouts come later. The framework comes only when a second real feature shows up.


## The big decision missing from the text

**Reuse left-undone-herdr, or start from scratch?**

- The hardest part there (identifying the right conversation, collecting events) still has open bugs.
- It already marks **YOU** tasks and shares tasks between sessions of the same project.
- Option: build watchdog as a **view layer** on top of:
  - the left-undone data,
  - Herdr's agent states,
  - the `TODO.md` files your projects already have (`status`, `prioridade` frontmatter).
- That way you don't rewrite the fragile part.


## Missing from the text

- **Offline:** without internet, LLM curation doesn't work. The panel must stay useful anyway (files + agent states).
- **Where the data lives:** a hidden SQLite database, or Markdown you edit in Neovim? Given how you work, I'd go with Markdown.
- **A "done" sentence for v1:** e.g. *"v1 is done when I open the panel and know within 5 seconds what's on me."*


## Side note

`vim-motions-mix/conceito.md` is a different project (Vim-style shortcuts for a mixing app).
It should get its own folder, `~/Projects/vim-motions-mix`, so the LLMs don't mix the two contexts.
