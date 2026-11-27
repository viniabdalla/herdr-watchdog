# Pesquisa: onde guardar o modelo e a regra do TODO.md (Claude Code + Codex CLI)

Data: 2026-11-26. Versões locais: Claude Code 2.1.319, codex-cli 0.167.0.
Commits consultados: `mattpocock/skills@6f7f783`, `openai/codex@b9e830f`, `vercel-labs/skills@57217cf`.

## 1. Resumo e recomendação

- **(a) Modelo:** a fonte deve ser o **repositório do Watchdog** (`docs/templates/todo.md`). É o mesmo repositório que define e lê a gramática `watchdog_todo: 1` (README "Formato único do TODO.md"; `watchdog_app/todo.py`), então os dois mudam juntos. Na preparação, copie o esqueleto (cerca de 15 linhas) para dentro do `docs/agents/todo.md` do projeto, para o projeto não depender de um caminho de fora. Não use `~/.ai-shared`: o Codex não tem imports (seção 3.3), esse arquivo fica fora de versionamento e hoje `~/.ai-shared/todo-modelo.md` nem existe.
- **(b) Regras:** coloque as regras em **`docs/agents/todo.md` no repositório do projeto**. No `AGENTS.md`, acrescente uma linha `See docs/agents/todo.md` dentro de `## Agent skills`, no padrão do Matt (o `CLAUDE.md` já faz `@AGENTS.md`). O preâmbulo do TODO.md deve ficar em uma linha que só aponta para a regra. Nos globais, nada específico do Watchdog: a linha "Se o projeto tiver `docs/agents/todo.md`, siga-o" já existe nos dois arquivos e basta.
- **(c) Garantir a atualização depois do `/to-tickets`:** o gatilho deve ficar em **`docs/agents/issue-tracker.md`**, na seção "When a skill says 'publish to the issue tracker'". O próprio upstream diz que as skills leem esse arquivo na hora de publicar e "do what it says". Ele está no repositório do projeto, então sobrevive ao update das skills, vale para Claude e para Codex e não depende do Watchdog. Um reforço opcional só para o Claude é um hook `UserPromptExpansion` com matcher `to-spec|to-tickets` em `.claude/settings.json` do projeto.
- **Divergência a decidir antes de fechar a regra:** o rascunho diz "não crie um item por ticket", mas `dispatch_preview.py` só resolve `Bloqueado por: T1 (#2)` contra **itens do TODO** cujo título começa com `T1 (#2)` (seção 3.6). Com os tickets dentro do item da spec, toda dependência fica sem resolução e aparece como "depende do Vini". Isso fica para decisão do Vini.

## 2. Opções x critérios

Legenda das fontes: [CM] Claude memory, [CH] Claude hooks, [CS] Claude skills, [XA] Codex AGENTS.md, [XH] Codex hooks, [MP] doc do Matt, [L] fato local. As URLs estão na seção 3.

### (b) Onde pôr as regras

| Opção | Carrega sozinho no Claude? | Carrega sozinho no Codex? | Sobrevive a update das skills? | Funciona sem Watchdog? | Quanto vai para o global | Custo de contexto |
|---|---|---|---|---|---|---|
| Preâmbulo dentro do TODO.md | Não. Só quando o agente abre o arquivo | Não, idem | Sim | Sim | 0 | Baixo, mas duplica e diverge do resto [L] |
| `CLAUDE.md`/`AGENTS.md` do repositório (texto inline) | Sim, no início da sessão [CM] | Sim, no início da sessão [XA] | Sim | Sim | 0 | Alto: entra em toda sessão. O Codex corta em 32 KiB no total [XA]; o Claude recomenda menos de 200 linhas [CM] |
| `docs/agents/todo.md` + linha no `AGENTS.md` | Só o ponteiro. O arquivo é lido quando o agente decide abri-lo [CM, "A CLAUDE.md that tells Claude in words…"] | Idem | Sim (o arquivo é do projeto) [MP] | Sim | 0 | Mínimo até o uso |
| `docs/agents/todo.md` importado com `@docs/agents/todo.md` | Sim. O import entra junto com o arquivo que o chama [CM] | Não: o Codex não tem import documentado [XA] | Sim | Sim | 0 | Alto no Claude; import não reduz custo [CM] |
| `.claude/rules/todo.md` com `paths: ["/TODO.md"]` | Sim, quando o Claude lê ou edita o TODO.md [CM] | Não existe no Codex | Sim | Sim | 0 | Só quando o TODO.md é tocado |
| Global (`~/.claude/CLAUDE.md` + `~/.codex/AGENTS.md`) | Sim [CM] | Sim [XA] | Sim | Sim | Tudo, e duplicado: o Codex não tem import [XA] | Alto em **todos** os projetos |

### (a) Onde pôr o modelo

| Opção | Versionado com o parser? | Acessível sem Watchdog rodando? | Claude e Codex | Global |
|---|---|---|---|---|
| `~/.ai-shared/todo-modelo.md` | Não | Sim | Sim, por caminho | Sim. Hoje o arquivo não existe [L] |
| Repositório do Watchdog | Sim [L: README e `todo.py` no mesmo repositório] | Sim. Ler um arquivo não exige o painel aberto | Sim, por caminho absoluto. O caminho precisa existir em cada máquina | Não |
| Cópia no projeto (dentro de `docs/agents/todo.md`) | Copiado na preparação; pode envelhecer | Sim | Sim | Não |

### (c) Como disparar a atualização depois do `/to-tickets`

| Mecanismo | Claude | Codex | Sobrevive a update? | Sem Watchdog? | Determinístico? |
|---|---|---|---|---|---|
| Seção em `docs/agents/issue-tracker.md` | Sim [MP] | Sim [MP] | Sim | Sim | Não (é instrução ao modelo) |
| Hook `UserPromptExpansion`, matcher `to-tickets` | Sim: injeta `additionalContext` quando o usuário digita `/to-tickets` [CH] | Não existe | Sim | Sim | Sim (a injeção é garantida; seguir a instrução, não) |
| Hook `UserPromptSubmit` do Codex procurando `$to-tickets` | n/a | Talvez: o campo `prompt` existe [XH], mas não foi confirmado que contém `$to-tickets` | Sim | Sim | Não confirmado |
| Botão de skill do Watchdog (`matt_skills.py`) | Sim | Sim | Sim | **Não** (precisa do Watchdog) [L] | Sim |
| Editar o SKILL.md | — | — | **Não** [MP, vercel] | — | — |

## 3. Fatos por fonte

### 3.1 Claude Code: memória (https://code.claude.com/docs/en/memory)
- Escopos: usuário em `~/.claude/CLAUDE.md`; projeto em `./CLAUDE.md` ou `./.claude/CLAUDE.md` (seção "Choose where to put CLAUDE.md files").
- Os arquivos da árvore acima do diretório de trabalho carregam na abertura. Os de subpastas carregam "once Claude reads, writes, or edits another file in that subdirectory" (seção "How CLAUDE.md files load").
- Imports: `@path`, relativo ao arquivo que importa, "maximum depth of four hops". Imports "don't reduce its context cost" (seções "Import additional files" e "Write effective instructions").
- Tamanho: "target under 200 lines per CLAUDE.md file". Sobre conflitos: "if two instructions contradict each other, Claude may pick one arbitrarily".
- Regras por caminho: em `.claude/rules/*.md` com `paths:`, carregam "when Claude uses the Read, Write, or Edit tool on a matching file". Também existem regras de usuário em `~/.claude/rules/`, com padrões relativos ao diretório de trabalho principal (seção "Path-specific rules").
- AGENTS.md: quando existe um `CLAUDE.md`, o Claude lê só o `CLAUDE.md`; `@AGENTS.md` dentro dele inclui o AGENTS.md. Um CLAUDE.md que só manda ler o AGENTS.md em palavras faz o Claude ver o arquivo "only if it decides to open the file" (seção "Remove an earlier AGENTS.md workaround"). A mesma lógica vale para qualquer ponteiro do tipo "See docs/agents/…".

### 3.2 Claude Code: hooks e skills
- https://code.claude.com/docs/en/hooks, seção UserPromptExpansion: "Runs when a user-typed command expands into a prompt… a hook matching a review skill can append the team's review checklist as `additionalContext`". Esse evento cobre o caminho que o `PreToolUse` não cobre, porque digitar `/skillname` "bypasses `PreToolUse`". O matcher é `command_name`.
- Os hooks podem ficar em `~/.claude/settings.json`, `.claude/settings.json` (versionável), `.claude/settings.local.json`, num plugin ou no frontmatter de uma skill. O texto do contexto deve ser escrito "as factual statements rather than imperative system instructions".
- https://code.claude.com/docs/en/skills: `disable-model-invocation: true` impede que o Claude carregue a skill sozinho. Ao invocar, "the rendered SKILL.md content enters the conversation as a single message". `skillOverrides` só controla a visibilidade das skills; não altera o conteúdo delas.

### 3.3 Codex CLI
- AGENTS.md (https://learn.chatgpt.com/docs/agent-configuration/agents-md; `openai/codex/docs/agents_md.md` aponta para lá):
  - global: `AGENTS.override.md` ou `AGENTS.md` em `~/.codex`;
  - projeto: da raiz até o diretório atual, "at most one file per directory", concatenados da raiz para baixo;
  - `project_doc_max_bytes` tem padrão de 32 KiB e o Codex "stops adding files once the combined size reaches the limit";
  - o encadeamento é montado na inicialização. A página não menciona imports nem leitura sob demanda.
- Skills (https://learn.chatgpt.com/docs/build-skills): lidas de `.agents/skills` (subindo até a raiz do repositório) e de `$HOME/.agents/skills`. Invocação com `$skill` ou `/skills`. `allow_implicit_invocation: false` ainda permite `$skill` explícito. `[[skills.config]]` só desliga skills.
- Hooks (https://learn.chatgpt.com/docs/hooks): os eventos incluem `UserPromptSubmit`, `PostToolUse` e `Stop`, com `additionalContext`. Configuração em `~/.codex/hooks.json` e em `.codex/hooks.json` de projeto confiável. A página não descreve hook de invocação de skill. "Hooks are enabled by default"; localmente, `[features] hooks = true` [L].

### 3.4 Especificação agents.md (https://agents.md/)
- "AGENTS.md is just standard Markdown", sem estrutura obrigatória. Vale "the closest AGENTS.md to the edited file". Não há sintaxe de import.

### 3.5 Skills do Matt e mecanismo de update
- `docs/engineering/setup-matt-pocock-skills.md`, linhas 5, 26 e 78 (github.com/mattpocock/skills):
  - "The skills themselves are identical everywhere. They read `docs/agents/issue-tracker.md` at run time and do what it says… you never edit a skill file."
  - "There is no user-level or global mode."
- O modelo `issue-tracker-github.md` tem a seção "When a skill says 'publish to the issue tracker'" na linha 33. O `to-tickets/SKILL.md` diz, na linha 11, que o tracker "should have been provided to you", e manda publicar "depends on the tracker `/setup-matt-pocock-skills` configured" na linha 60.
- README do upstream: "A plugin updates itself. skills.sh copies editable files… you update them by hand". Para o Claude, o plugin "Updates itself by default".
- vercel-labs/skills: `npx skills update` reinstala as skills. O lock global fica em `$XDG_STATE_HOME/skills/.skill-lock.json` ou `~/.agents/.skill-lock.json` (`src/skill-lock.ts`, linhas 73–81).
- [L] Os SKILL.md locais de `to-tickets`, `to-spec` e `setup-matt-pocock-skills` são idênticos aos do upstream em `6f7f783`. Os `agents/openai.yaml` têm `allow_implicit_invocation: false`.

### 3.6 Fatos locais
- `watchdog_app/dispatch_preview.py`:
  - linhas 11–18: os aliases de ticket vêm do **título do item** (`^(T\d+)\b(?:\s+\(#(\d+)\))?`);
  - linha 26: os bloqueios são lidos de `Execução`/`Motivo`;
  - linhas 31–36: uma referência sem item correspondente vai para `unresolved`, que vira "depende do Vini" (linha 39).
- O TODO.md desta branch tem histórico de itens `T1 (#2)…T15 (#16)` e preâmbulo novo dizendo o contrário (linha 26).
- Já existem dois mecanismos no Watchdog:
  - `watchdog project-instructions preview|check|apply`, que instala um bloco gerenciado no AGENTS.md e no CLAUDE.md (`watchdog_app/project_instructions.py`, `docs/project-instructions.md`);
  - o botão `/to-tickets` em `watchdog_app/matt_skills.py`, que avisa quando falta a "Cópia local" (linhas 34–38).
- `~/.claude/CLAUDE.md` foi alterado durante esta sessão. No início ele importava `@~/.ai-shared/regras-todo.md`; agora tem um bloco "TODO.md (git-todo)" inline. Nem `~/.ai-shared/regras-todo.md` nem `~/.ai-shared/todo-modelo.md` existem. O `~/.codex/AGENTS.md` (9.599 B) tem o mesmo bloco, copiado à mão.
- Conflito entre global e projeto: o global manda "mantenha só os 10 últimos itens em Feito", e o `docs/agents/todo.md` manda perguntar antes de remover. A frase de precedência existe, mas o Claude "may pick one arbitrarily" [CM].

## 4. Não confirmado

- **Como as skills foram instaladas em `~/.agents/skills`.** Não há `.skill-lock.json` em `~/.agents` nem em XDG. O plugin `mattpocock-skills@claude-plugins-official` aparece instalado em escopo de projeto e **desabilitado**. Não confirmei localmente que um update vá sobrescrever esses arquivos. A sobrescrita só está documentada para o plugin e para `npx skills update`.
- Se rodar `/setup-matt-pocock-skills` de novo preserva seções extras do `docs/agents/issue-tracker.md`, como a "Cópia local". A skill mostra um rascunho antes de gravar, mas não garante a preservação.
- Se o `command_name` do `UserPromptExpansion` é `to-tickets` ou `mattpocock-skills:to-tickets` quando a skill vem de plugin.
- Se o `prompt` do `UserPromptSubmit` do Codex contém o texto `$to-tickets`. Também não confirmei se o Codex aceita matcher nesse evento.
- Se uma regra por caminho carrega **antes** de um `Write` que cria um TODO.md novo.
- Se `project_doc_max_bytes` conta o `~/.codex/AGENTS.md` global.
- Se os agentes de fato seguem um ponteiro "See docs/agents/todo.md". Isso precisa de observação real; o próprio `docs/project-instructions.md` marca esse ponto como `manual-unobserved`.

## 5. Proposta mínima

**Globais:** nenhum texto novo. Basta tirar o conflito: no bloco git-todo dos dois globais, trocar "mantenha só os 10 últimos itens em `## Feito`" por "mantenha só os 10 últimos itens em `## Feito`, salvo regra do projeto".

**Repositório do projeto** (pode ser instalado pelo `watchdog project-instructions` ou à mão):

1. `AGENTS.md`, dentro de `## Agent skills`:
   ```markdown
   ### TODO

   TODO.md no formato do Watchdog (`watchdog_todo: 1`). See `docs/agents/todo.md`.
   ```
2. `docs/agents/issue-tracker.md`, na seção "When a skill says 'publish to the issue tracker'", acrescentar:
   ```markdown
   Depois de publicar uma spec, tickets ou um bug, atualize o `TODO.md` na mesma operação,
   seguindo `docs/agents/todo.md`; se o `TODO.md` não existir, crie-o pelo esqueleto de lá.
   ```
3. `docs/agents/todo.md`: as regras atuais mais o esqueleto copiado de `docs/templates/todo.md` do Watchdog. A regra sobre "item por ticket" deve ser fechada antes; ver a divergência na seção 1.
4. Preâmbulo do TODO.md, uma linha: `Regras deste arquivo: docs/agents/todo.md.`
5. Opcional, só Claude, em `.claude/settings.json` do projeto:
   ```json
   {"hooks":{"UserPromptExpansion":[{"matcher":"to-spec|to-tickets","hooks":[{"type":"command",
     "command":"printf '%s' '{\"hookSpecificOutput\":{\"hookEventName\":\"UserPromptExpansion\",\"additionalContext\":\"Neste projeto, publicar spec ou tickets inclui atualizar TODO.md conforme docs/agents/todo.md.\"}}'"}]}]}}
   ```
