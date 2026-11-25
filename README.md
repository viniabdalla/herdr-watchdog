# Herdr Watchdog

Watch a verified AI conversation alongside project tasks, progress and artifacts.
Linux, Python 3.10+, standard library only, Herdr 0.9.1+, Yazi and `ya`.
The installed Left Undone identity engine is currently required.

## Use

```sh
python3 install.py
python3 install-skills.py
watchdog                       # choose the conversation if needed, then layout
watchdog layout 2              # direct preset selection
watchdog layout column-bottom
watchdog layout --list
watchdog list                  # verified conversations in the current project
watchdog status                # inspect the selected conversation without opening panels
```

A skill `merge-danger` fica em `skills/merge-danger`; `install-skills.py` a liga
às pastas `.claude/skills` e `.agents/skills` deste checkout. Para outro projeto
ou conta, passe `--claude-skills-dir` e `--codex-skills-dir`. O instalador preserva
skills de terceiros. Depois da implementação, use o botão na faixa do Tasks,
confira a prévia e informe um intervalo se necessário. A análise lista porta,
raio e decisão por parte; a decisão de levar a integração para fora da máquina
continua com o Vini. A invocação automática está desativada nos dois harnesses.

Run from the project folder, or pass `--repo /path/to/project`. `--pane ID
--session UUID` selects an exact verified conversation. Missing native session
registration is reported; Watchdog never guesses a UUID from focus or cwd.
An existing Codex thread in agent-tool context is matched by CODEX_THREAD_ID.
Conversation rows show the account before the session ID: canonical `~/.codex`
and `~/.claude` use “Default account”; other paths use their final folder name,
with parent folders added when needed to distinguish accounts. Names that still
look identical after control characters become spaces get stable account numbers.
The default account label is reserved for the canonical paths. Labels come only
from the verified binding path, without reading credentials or account settings.

Four presets are available; number 2 is the initial default. Arrows or j/k move
through the selector, the drawing follows, Enter applies, and Esc cancels without
changing the layout. Successful choices become the next default. All presets
reuse terminals rather than restart them. Unrelated terminals stay in place;
if they share the conversation tab, Watchdog uses a dedicated conversation tab.

The Herdr action “Watchdog: choose a layout” opens a terminal selector when the
action has no interactive terminal. Left Undone is optional as a visible panel:
if its panel is already bound to this conversation, it stays to the right of
Files. Watchdog reads that binding and never edits Left Undone's state.

## Painel de acompanhamento (branch feat/tasks-somente-leitura)

Por padrão, **WATCHDOG / TASKS** mostra **[Review Curator r]**, **[Verify Leader v]**, **[Despachar p]** e **[Quit q]**.
Space seleciona tarefas, Enter/▸ abre o Resumo e o curador continua revisando cada resposta.
**Verify Leader (v)** monta um pedido de verificação das tarefas selecionadas, mostra a prévia com o painel e a
sessão do líder anotados e, com **y**, digita o pedido no prompt dessa sessão via
`herdr pane send-text` + Enter, depois de reconfirmar a identidade da sessão. Esc cancela sem enviar.
Selecione as tarefas com Space e use **p** para despachá-las. A prévia mostra a meta e o pane do líder;
**y** confirma e digita o texto seguido de Enter, **Esc** cancela sem alterar o grupo.
A primeira meta aponta para o grupo, o [padrão do dispatch](docs/dispatch.md) e a seção Dispatch do AGENTS.md.
Claude e Codex recebem `/goal`; outros harnesses recebem a mesma frase como mensagem comum.
Cada despacho confirmado soma as tarefas ao grupo, sem duplicá-las. A primeira gravação anota
a ponta da branch de integração como base e a preserva nos acréscimos. Configure a branch na
seção Dispatch conforme o [modelo para projetos](docs/templates/dispatch-agents.md).
O Progress abre com a barra do projeto. Com um grupo, a barra do long run ocupa o topo e a barra geral fica logo abaixo.
Grupos antigos continuam legíveis; a ação de gravar um grupo manualmente foi removida.
O curador recebe as tarefas abertas do grupo como prioridade a cada resposta concluída da sessão vinculada.
A porcentagem muda quando o estado muda no TODO.md, inclusive após aplicar uma proposta do curador.
Orquestração, Agents, Clean sessions, Auditoria e Done/Start/Next ficam desligados;
`WATCHDOG_FULL_CONTROLS=1` restaura esses controles. Os modos anteriores de envio ficam em **Envio avançado D**.

## Agents and individual panels

`watchdog pane` opens a terminal selector for Agents, Tasks, Progress, Artifacts or Files.
`watchdog pane agents` opens the agents monitor directly. Use the same `--repo`,
`--pane` and `--session` options to identify the conversation, or pass its
`--binding-file`. Reopening focuses the existing panel; a closed panel can be
recreated without rebuilding the layout. A busy or replaced terminal is left alone.

In **WATCHDOG / TASKS**, click **Agents m** or press **m** to open the same monitor
below Progress (or beside the existing conversation's panels when Progress is absent).
The monitor shows the main session and native participants recorded for that leader,
with tab/pane, availability, delivery, context usage, percentage bar and abbreviated
cumulative tokens. Missing telemetry appears as **Sem dados**. Old runs remain history;
opening the monitor does not send work, accept deliveries or close TODO items.
For Claude, **B** adjusts its context window; preferences are saved only in Watchdog
state. **q/Esc** exits the monitor, leaving its pane available for reopening.
The usage readers were ported from Left Undone; its monitor and database are not used.

## Interactive Tasks

Click a task or use arrows/j/k and Space to select it. `s` prepares a request
for the verified Codex conversation; confirm with `y`, or Esc to cancel. Requests
go through Codex's account-specific inbox using the full thread UUID. A working
conversation needs a separate queue confirmation. Tasks stay open after sending.
This legacy `s` action requires Codex's thread-addressed transport. The group
dispatch action `p` uses the leader's pane for both Claude and Codex.

`d` requests confirmed completion. `i` moves to In progress; `n` moves to Next.
Section colors: Next blue, In progress yellow, Blocked red, Done green.
Edits preserve notes and completed history, retain backups under Watchdog state,
and reject stale selections. Concurrent editor saves are preserved; a conflict
requires reviewing the file again. Atomic exchange requires Linux renameat2.

The curator uses Codex gpt-6-luna at low effort, independent of the watched AI.
It checks each new completed reply against open TODO tasks and completed titles.
**Review Curator (r)** opens suggestions, or requests a fresh curator review. It proposes Done, Blocked
with a reason, and explicit new tasks. Every proposal displays a supporting
quote. Apply only the proposals you select, with a separate confirmation.

The reviewer uses the current Codex login (`WATCHDOG_CODEX_HOME` can select an
account). It makes model requests; it does not inspect code or prove a completion
claim. Missing mention is not treated as a blocker. Invalid/conflicting proposals
are withheld visibly. New replies or task edits invalidate old confirmations.

## Independent project audit

In Tasks, **Auditoria A** opens a separate read-only audit without selecting TODO
items. Choose a verified Codex account, a model listed by that account's provider,
and confirm. GPT Astra 6.1 is preferred only when actually listed; otherwise you
must choose another model. The new Herdr tab starts in the project directory and
runs a host wrapper with a new Codex app-server session. It displays audit output,
not an interactive Codex TUI. No leader conversation is copied or resumed.

The provider must confirm the requested model, new empty session, cwd, read-only
sandbox and approval `never` before execution. Connected tools and account lifecycle hooks are disabled; hooks are disabled before
app-server initialization. Audit entrypoints verify the original leader without
reattaching or rewriting its binding.
Press **A** again to follow running/completed/failed/uncertain status, effective
model and report path. Reports return to the exact original verified Codex leader;
a busy leader requires explicit **Entregar ao líder original** after it becomes
idle. Uncertain deliveries are retained and never automatically resent. A changed
project keeps the report as historical evidence without delivery. Audits never
close tasks, accept missions, merge, push or assume leadership.

```sh
watchdog audit models --account /absolute/codex-account
watchdog audit open --repo /project --binding-file /watchdog/state/binding.json \
  --account /absolute/codex-account --model MODEL_FROM_LIST --confirm
watchdog audit list --repo /project
watchdog audit inspect --audit-id UUID
watchdog audit deliver --audit-id UUID  # explicit retry only for busy/unavailable recipient
```

`--executable` selects an installed Codex binary; the default uses the installed
mise Codex path, refusing the mise shim itself. `--state-dir` overrides the audits
folder (default `$WATCHDOG_STATE_DIR/audits`). Passing the same `--audit-id` to
`open` never launches twice. Read the [audit design](docs/superpowers/specs/2026-11-23-independent-audit-design.md)
and [verification limits](docs/verification-audit-2026-11-23.md) before treating
mocked provider evidence as a live-model demonstration.

## Current limits

The launcher, verified binding, four layouts and artifact-to-Yazi link work.
Tasks is interactive with confirmed curator proposals. Progress reads successful
native checklist calls from the explicitly verified conversation; it no longer
reads the manual preview checklist. Missing or unsupported checklist data has
an explicit status without a percentage. Artifacts still uses an explicit list;
automatic artifact discovery remains pending. See [Session progress](docs/session-progress.md)
for supported formats and evidence limits.

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

## Fresh workers and planning

In Tasks, select tasks and use **0** (new executor), **P** (plan only), or the
**Envio avançado D** menu (with full controls). Several tasks offer **Juntas** (one worker and one contract
covering all selected IDs) or **Separadas** (one fresh worker per task). The
confirmation lists the project checkpoint before any dispatch. One message asks
the verified leader to prepare the contracts, choose a model and effort, and launch.

The fresh-worker template accepts `kind: codex` or `kind: claude` plus explicit
account and executable paths. Each worker starts in a separate owned Git worktree
with a standalone brief, adapted from Left Undone's dispatch flow. Reports use
Watchdog's authenticated host bridge. Follow-ups start fresh attempts at the
previous worker's clean committed checkpoint; older worktrees and reports remain.
Codex leaders use their exact-thread queue. Claude leaders must be idle to receive
a dispatch; reports remain pending while a Claude leader is busy.

Planning uses the provider's native plan mode and stores a proposal in the run
ledger and `plan-<attempt>.md` in Watchdog state. It does not complete TODO items,
produce implementation evidence, merge or push. A planner that changes source or
commits is blocked with its changes retained. Read the proposal in its execution
tab; explicitly dispatch implementation afterward. A preceding proposal with the same complete task scope
is included in the leader's new request. Questions become blocked reports
for the leader. Implementation results still require exact-candidate leader review;
a Together result must cover every selected task.

Only Watchdog code/state changes in this port. Left Undone's code, buttons,
installation and data remain intact. Its existing identity dependency is unchanged.
Gossip is frozen for maintenance; no new integrations are planned, and legacy run
records remain readable. Fresh dispatch uses native launch/report paths.

## Mission Control pilot

Select open tasks in Tasks with full controls and press **D / Envio avançado**. Choose **Para um agente**
for one existing executor with leader review, or **Orquestrar equipe** for worker
and QA. **o / Orchestrate** still opens the team confirmation directly. Confirm the project,
main conversation, account and team. This queues a coordination request to that
exact Codex thread. Send keeps its existing current-conversation behavior. The
main prepares the task contracts; the launcher does not invent a plan. Neither
requesting work nor approving a run edits TODO.md.

**Checkpoint.** The confirmation lists every modified and new project file. `y`
saves exactly that list in one local commit (never pushed) and the run starts from
it; a list that changed after confirmation is refused. Merge conflicts must be
resolved first. While the main prepares the brief, editing TODO.md (new ideas,
reordering) does not block the launch; other dirty files do, with their names.

New requests pin versioned selected task blocks and sections. After a clean
launch, unrelated TODO edits and new ideas may shift rows without blocking the
run; selected content, notes, completion and section changes require a new
contract. Ambiguous duplicate blocks are rejected. Recorded task IDs and exact
candidate QA remain pinned. Existing runs retain whole-TODO digest validation
and are never migrated. See [selected run scope](docs/mission-control.md#selected-scope-for-new-runs)
for compatibility, strict matching and Git boundary details.

Progress reads the run ledger. Each run has one state: **Preparing**, **Running**,
**Verifying**, **Waiting for approval**, **Needs your decision**, **Stalled** (no
monitor and no activity for 20 minutes), **Done** or **Closed**; Tasks shows the
same line for unfinished runs. Tasks show agent, last update and reason, and
Enter/click opens the execution tab. `x` twice closes a run: agents are not
stopped and evidence is kept. Finished runs collapse to one line. A run never
blocks new work once its tasks are marked Done in TODO.md or it is stalled:
Orchestrate closes it, visibly, in the confirmation. Late or superseded reports
are kept as history without notifying the main. Moving a task that belongs to an
unfinished run explains how to continue instead of silently breaking the run.
If the watched conversation pane is closed, `codex resume <session>` in the
project is followed automatically. Actual colors follow the terminal palette.

Each launch records an explicit model and reasoning effort. The brief template
uses gpt-6.1-sol with medium effort for worker and routine QA, with actual CLI
overrides; Progress displays those choices.

In team mode, the initial team is exactly one worker and one QA. Both terminals share one new
tab; each has its own worktree. Each later implementation task requires a NEW
executor conversation at the preceding accepted commit; every review requires a
NEW QA conversation. Probes require dedicated disposable conversations and must
never use real-task executors. Main supplies those actors; no automatic reuse. The
first independent task is dispatched once the exact native Codex identity and
role enrollment are verified. New runs use the Codex queue and durable local
reports by default; Gossip is an explicit legacy adapter. Existing runs retain
their transport. See [Native transport](docs/native-transport.md) for delivery
receipts, identity boundaries and the safe idle test path. Main reviews each result before dispatching the next
contract. QA reviews the complete integrated candidate at its full commit SHA.
The main/user approves completion separately. `mission approve --confirm` integrates
the approved exact candidate into the project branch and pushes to its configured
upstream; a missing upstream leaves a local integration with an explicit notice.

The operator lifecycle is documented in [Mission Control](docs/mission-control.md).
The run ledger is in `$WATCHDOG_STATE_DIR/runs` (normally
`~/.local/state/herdr-watchdog/runs`). Keep it: it contains exact native identities,
source snapshots, assignments, results and owned resource mappings.


### Para um agente

Choose one open task, then **p → Para um agente**, select the executor by its
verified panel, account and session, and confirm. It must be an idle Codex session
dedicated to this task in a clean linked worktree of the same repository, at the
project's committed HEAD. Main and executor must be distinct. No agent, pane or
worktree is created or restarted by this mode. Existing conversations used for
another task/review/purpose cannot be reused. Commit project code first; unrelated
TODO changes retain the existing selected-scope rules.

The leader receives the confirmed recipient, prepares the explicit contract with
`mission template`, and launches it with `mission launch --brief FILE --confirm`.
The native host attaches to the selected actor; enrollment and delivery keep the
existing exact-thread, role, attempt and receipt checks. An uncertain attachment
or queue delivery is retained for inspection and never blindly retried. Progress
shows the chosen panel and **Aguardando revisão do líder**; Enter opens that
existing executor. Closing the run preserves its actor, pane and evidence.

After reading the complete result and independently running the relevant checks,
the leader records observed evidence (values below are placeholders):

```json
{
  "run_id": "RUN_UUID",
  "candidate": "FULL_40_CHARACTER_COMMIT_SHA",
  "result_version": 1,
  "verdict": "pass",
  "summary": "Findings from the leader's review, including limitations",
  "tests": ["Command actually run and observed output/exit status"]
}
```

Use the current `result_version` from `mission inspect`, then:

```sh
watchdog mission leader-review --run RUN_UUID --candidate FULL_SHA --file REVIEW.json --confirm
watchdog mission approve --run RUN_UUID --candidate FULL_SHA --confirm
```

Both commands verify the selected task source; review also verifies worker
commit ancestry and clean HEAD. Approval rechecks that same HEAD and requires a
passing leader review for the exact commit, current result version and current
leader identity. Follow-ups and newer reports invalidate earlier reviews. A
failed review blocks approval. Sending, reviewing and approving leave TODO open
until the user's separate acceptance. Ledgers without `execution_mode: single`
retain the original independent-QA requirement, including legacy runs.


## Leader handoff / Clean sessions

Tasks' **c / Clean sessions** requests the verified current leader to reconcile
TODO and save a real ai-memory MCP handoff in one action. The leader identifies
owned changes in the verified Herdr worktree. Commits made during preparation
are accepted if every intervening commit is linear and touches only those files.
Use **Shift+C** to choose files, destination, approved branches or startup settings
explicitly. A worktree without an upstream opens the destination form.
The backend commits owned changes, fast-forwards only approved branches, verifies
the pushed checkpoint, creates a fresh Herdr split/Codex frontend, delivers bounded
context to its exact thread and waits for actual receiver receipt and predecessor
release. If the original process and pane have both exited, Watchdog verifies
the successor receipt and checks Herdr for a resumed predecessor before transferring.
Store then transfers Tasks/Progress and the existing Orchestrate target,
preserving panel terminals, Artifacts, Files/Yazi and layout. Left Undone is read-only.
Pending/blocked/partial/received/released outcomes and uncertain effects stay visible;
no blind resend or relaunch occurs. Active native runs must finish first.

The separate `watchdog mission handoff-export`/preview/adopt APIs retain their
bounded run-evidence and freshness guards. Legacy ledgers stay export-only; project
baton transfer never forges native legacy adoption. See
[Leader handoff](docs/leader-handoff.md) for the workflow, boundaries and evidence.
Tests use real isolated Git/remotes and UI controls with labelled simulated
model/native/ai-memory/Herdr boundaries; production end-to-end acceptance is separate.

The clean-session policy supersedes older transport-probe examples: never use a
real-task executor for a probe. The current grandfathered worker finishes only
Leader handoff. Native policy claims reject known executor/QA/probe reuse;
separate probe RunStores must explicitly share the main session-policy registry.

## Formato único do TODO.md

O formato antigo continua aceito, sem conversão automática. Para adotar o formato
versionado, o frontmatter declara `watchdog_todo: 1`. Cada tarefa tem UUID fixo,
título na linha do checkbox, resumo, origem, execução e aceite no próprio TODO:

```markdown
---
watchdog_todo: 1
---
# TODO

## Próximo
- [ ] Recuperar os áudios
  ID: 613821eb-e1d7-4ae6-9f71-88534c73c843
  Resumo: Recuperar a fila para continuar o atendimento.
  Origem: pedido-humano
  Referência: pedido explícito na conversa do projeto
  Execução:
    Investigar a fila e preservar os arquivos originais.
  Aceite:
    Demonstrar recuperação com evidências verificáveis.

## Feito
```

Gramática determinística, implementada em Python sem dependências adicionais:

- Seções de estado: `Em andamento`, `Próximo`, `Bloqueado`, `Feito`, ou seus nomes
  atuais em inglês. Só Feito aceita `[x]`; as demais usam `[ ]`.
- Título: uma linha de 1–500 caracteres imprimíveis. O UUID canônico no campo
  `ID` é único no documento e permanece igual ao editar título, detalhes ou estado.
- Campos obrigatórios: `ID`, `Resumo`, `Origem`, `Execução`, `Aceite`.
  Opcionais: `Referência`, `Motivo`. Nomes e capitalização são exatos.
- Campos começam com dois espaços. Resumo, Execução e Aceite aceitam conteúdo
  multilinha com quatro espaços, incluindo checklists e código. Linhas em branco
  são permitidas dentro desses campos. Demais campos têm uma linha.
- Origem: `pedido-humano`, `sugestao-agente` ou `legado-nao-confirmado`.
  Uma sugestão não se autoriza por existir no arquivo. Referência só registra
  evidência disponível; a importação não inventa autoria, aceite ou benefício.
- Campos repetidos/desconhecidos, UUIDs duplicados, estados incoerentes e versões
  desconhecidas produzem erro com linha. Exemplos em cercas Markdown são ignorados.
  Adicionar uma tarefa v1 exige os campos completos; a proposta antiga de adição
  contendo apenas título precisa ser completada antes de poder ser aplicada.

O painel mostra somente títulos com `▸`. Clicar na setinha ou no título, ou
pressionar Enter, abre `Resumo` e `Situação` com espaçamento e quebras de linha;
outro clique ou Enter recolhe. Setas direita/esquerda também abrem/recolhem.
O checkbox e Espaço continuam selecionando tarefas independentemente da expansão.
Os detalhes técnicos permanecem completos na confirmação e no envio ao executor.
Arquivos antigos mostram apenas seu `Resumo:` declarado, sem expor instruções
como substituto de resumo. A instalação de orientações para agentes permanece
uma tarefa separada.

Validação e migração explícita de um projeto:

```bash
./watchdog todo validate --repo /caminho/do/projeto
./watchdog todo preview --repo /caminho/do/projeto > /tmp/todo-proposta.json
# Revisar o JSON e preencher os campos vazios em tasks; conservar original,
# source_digest, old_id e IDs atribuídos pela prévia.
./watchdog todo render --repo /caminho/do/projeto --proposal /tmp/todo-proposta.json
./watchdog todo apply --repo /caminho/do/projeto --proposal /tmp/todo-proposta.json --confirm
```

`preview`, `render` e `validate` não alteram o TODO. A prévia JSON é um artefato
de revisão; o painel continua lendo exclusivamente TODO.md. `render` mostra o
Markdown exato que será aplicado e acusa campos ausentes. A proposta conserva a
versão original para revisão. As instruções antigas permanecem integralmente em
Execução; critérios e resumo já declarados são copiados, sem inferência.

`apply` exige confirmação, a mesma origem e nenhuma execução afetada inacabada;
informa os IDs que bloqueiam. `blocked_runs` na prévia é informativo: os registros
são consultados novamente ao aplicar. Primeiro termine ou encerre explicitamente
essas execuções pelos controles existentes. Nenhum run ou agente é encerrado pela
migração. `--state-dir` permite selecionar o diretório de runs, como no comando
`mission`; sem ele, usa o diretório normal do Watchdog.

A escrita usa trava, comparação do documento original, troca atômica e backups
em `$WATCHDOG_STATE_DIR/todo-backups` (normalmente
`~/.local/state/herdr-watchdog/todo-backups`). Edições concorrentes são preservadas
e interrompem a operação. Notas e conclusões importadas permanecem no documento;
conclusões antigas são delimitadas por `<!-- watchdog-history:begin -->` e
`<!-- watchdog-history:end -->`, contadas como histórico e nunca executáveis.
Estados antigos incoerentes precisam de revisão explícita antes da conversão.
Comentários `watchdog-migration` contêm a versão, digest de origem e mapa de IDs.
O arquivo original também fica preservado integralmente no backup.

Novas execuções de tarefas v1 guardam escopo v2: UUID, formato, bloco aprovado e
estado. Alterar o texto conserva o UUID, mas exige revisão do contrato antes de
continuar a execução. Reordenar linhas sem mudar o bloco aprovado é permitido.
Contratos antigos conservam suas regras e seus registros; nunca são atualizados
silenciosamente. Contratos inacabados de formatos diferentes exigem resolução
explícita antes de iniciar trabalho que poderia se sobrepor.

Para substituir intencionalmente a identidade de uma tarefa já migrada:

```bash
./watchdog todo preview --repo /caminho/do/projeto --task UUID_ATUAL > /tmp/todo-identidade.json
./watchdog todo render --repo /caminho/do/projeto --proposal /tmp/todo-identidade.json
./watchdog todo apply --repo /caminho/do/projeto --proposal /tmp/todo-identidade.json --confirm
```

A prévia atribui outro UUID; `--new-id UUID_NOVO` permite especificá-lo. O mapa
antigo→novo fica no TODO; IDs aposentados não podem ser reutilizados. Execuções
afetadas em aberto impedem a troca e seus registros históricos ficam intactos.
Editar diretamente um ID não faz correspondência por título: contratos que o
referenciam acusam identidade ausente, exigindo revisão explícita.

### Explicit project preparation and evidence

- [Project instructions](docs/project-instructions.md): `watchdog project-instructions
  preview|check|apply --repo PATH` previews managed AGENTS.md/CLAUDE.md changes and
  applies only an explicitly confirmed, unchanged preview. Actual agent reading
  remains a separate observed/manual check.
- [Project plans](docs/project-plans.md): `watchdog project-plan --repo PATH --source
  plan.json --format watchdog-plan-v1` emits bounded, non-authorizing contracts from
  version-1 TODO identities. `--human` displays the preview.
- [Artifact discovery](docs/artifact-discovery.md): bound panels discover successful
  tool paths with source references and current filesystem state. Reveal stays in
  the exact linked Yazi Files pane.
- [Project progress history](docs/project-progress-history.md): durable observed
  UUID transitions, explicit recovery after save failures, and recent events in Progress.
- [Curator validation](docs/curator-validation.md): human-confirmed proposals,
  source/recipient staleness checks, and honest real-source replay limitations.
- [Real-run evidence](docs/verification-real-run-2026-11-23.md): read-only observer,
  observed launch stages, and gates still to be recorded by the coordinator.
