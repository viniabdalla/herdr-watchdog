# Project instructions

`watchdog project-instructions preview|check|apply --repo PATH` targets only the
explicitly selected existing project: AGENTS.md, CLAUDE.md,
`docs/agents/todo.md` and, when present, `docs/agents/issue-tracker.md`. It uses
TODO format version 1; it neither creates a second task list nor changes TODO.md.
The project leader owns its content. A worker contract can further restrict edits.

Preview is read-only and includes each file's status, SHA-256, complete proposed
content and exact unified diff. `--human` renders the diff directly. Check reports
absent/outdated/current per file. Preserve the JSON preview for confirmation:

```sh
watchdog project-instructions preview --repo "$project_dir" > /tmp/instructions-preview.json
watchdog project-instructions preview --repo "$project_dir" --human
watchdog project-instructions apply --repo "$project_dir" --preview-file /tmp/instructions-preview.json --confirm
watchdog project-instructions check --repo "$project_dir" --human
```

Apply displays the supplied diff before writing and requires `--confirm`. It
recomputes the whole preview under the project lock, so another project, modified
proposal, changed user rules or stale source fails closed. User text outside the
managed markers stays byte-for-byte intact, including CRLF and trailing content.
A second installation is a no-op. Unsupported/fenced/ambiguous marker boundaries,
unmanaged conflicting copies, symlinks and hard links require manual resolution.
Concurrent saves are detected at atomic exchange; competing versions are retained
in Watchdog state. Each file is installed independently. A later-file failure
reports partial installation and requires a fresh preview rather than rolling back
a user's concurrent save. A process crash can likewise require preview/check again.

The managed block explains a plain title and Resumo; technical details belong in
Execução and evidence/criteria in Aceite. Canonical UUIDs survive moves, corrections,
completion and reopening. It explains open/in-progress/blocked/done states and the
Origem distinction between human requests, agent suggestions and unconfirmed legacy
work. Dispatch and approval do not themselves complete TODO work.

After installation, the real agent must read the block in its actual conversation
and acknowledge version 1, how it records a request during the conversation, how it
labels a suggestion, and what evidence permits completion. Save that acknowledgement
as a source reference. `agent_reading: manual-unobserved` is intentional: installation
and fixture tests cannot attest model reading. This run installed no real project's
instructions; that actual-agent reading check remains manual/unperformed.


## Markdown context before writing

The second review reproduced an unsafe first-install path in which a file with an
unclosed backtick fence accepted an appended block, then failed a later check after
both files had been written. Preview now validates Markdown context **before** either
first installation or managed replacement, and validates the complete proposed output.
An unresolved backtick or tilde fence anywhere in either file is refused. Managed
markers inside a code fence remain ambiguous and are refused; valid closed fenced
examples are preserved byte-for-byte.

Apply recomputes this validation for **both** files under the lock before its first
file write, even for an old or adulterated preview. Disposable regressions verify the
exact `# Rules\n```text\nexample left open\n` bytes, tilde fences, both filenames,
old/tampered payloads, closed examples, and markers inside examples. Refusal preserves
the original bytes and leaves the other instruction file absent. Markdown checking is
a conservative fence parser; ambiguous or unresolved source context requires manual
reconciliation rather than claiming that installed text will be read as instructions.


## Preparar a regra do TODO

A mesma prévia inclui o ponteiro `### TODO` dentro de `## Agent skills` no
AGENTS.md, as seções ausentes da regra `docs/templates/agents-todo.md` e um
esqueleto de `docs/templates/todo.md` embutido em `docs/agents/todo.md`.
O projeto pode consultar o esqueleto sem depender do caminho do Watchdog.
Seções já existentes da regra são preservadas; a preparação acrescenta as ausentes.
O `TODO.md` do projeto continua sendo criado no momento definido pela regra.

O gatilho de `docs/templates/issue-tracker-todo.md` é acrescentado à seção
`When a skill says "publish to the issue tracker"` do issue tracker existente.
Se faltar a seção, ela é acrescentada. Se faltar o arquivo, a prévia e o check
avisam para rodar `/setup-matt-pocock-skills`; a preparação não o cria.
Avisos aparecem em `warnings` no JSON e também na saída `--human`.

Todos esses arquivos participam da mesma confirmação e conferência de hashes.
A ausência do tracker é conferida novamente ao aplicar: se alguém o criar depois
da prévia, é necessário gerar uma prévia nova. A preparação preserva texto fora
do bloco gerenciado e das inserções e recusa diretórios intermediários simbólicos.
A instalação dos arquivos não comprova que um agente seguiu a regra.
