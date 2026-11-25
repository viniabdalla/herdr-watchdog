# Preparação e passagem de sessão

As chamadas do líder e as mensagens que ele sugeriu ao Vini para copiar estão identificadas em cada entrada. Há versões sucessivas dos prompts de passagem de sessão.

## Chamada de skill · /grilling

2026-11-24T23:26:10.644Z · 2f15e16c-24cf-42d4-8524-e45b2704306d, linha 166

```text
/grilling Plano para deixar a Janaína operacional amanhã no TropicDesk CRM (deploy sem ajuda). Usar os docs do repo (HANDOFF.md, PROGRESSO.md, TODO.md, AGENTS.md, docs/superpowers/plans e specs, docs/AGENTES-AUDIO-HERMES.md, docs/REA-QUADRO-AUTOMACOES-20261016.md) para levantar o que está pendente e planejar um longrun. Requisitos novos do Vini: (1) Janaína pode responder, mas em modo aprovação: para cada resposta gera relatório publicado na Vercel, notifica via Telegram, Vini libera ou adapta e então ela envia; serve para treiná-la; (2) outro perfil Hermes responsável por mover clientes de estágio: ao terminar a qualificação, um webhook manda a info para esse perfil, que decide se muda de estágio ou não. Já acordado: entrada ao vivo com 6 cenários, bot 83422, humanizar com workflow como guardrail, autoridade humana dupla, reinício com prazo persistido, entrega incerta só com ID, conflito com bots do Kommo no mesmo número.
```

## Delegação · Levantar pendências nos docs do CRM

2026-11-24T23:26:31.945Z · 2f15e16c-24cf-42d4-8524-e45b2704306d, linha 176

```text
Repo: /mnt/nextcloud/00-workspaces/01-projects/tropicdesk-kommoclone/tropicdesk-kommoclone (TropicDesk, clone local do Kommo CRM, Node, SQLite). Somente leitura; não rode serviços nem altere arquivos. Medium-thorough.

Quero um relatório factual (PT-BR, conciso, com caminhos de arquivo:linha) para planejar deixar a agente Hermes "Janaína" operacional amanhã. Levante:

1. Pendências abertas segundo HANDOFF.md (topo), PROGRESSO.md, TODO.md, PLANO.md, AGENTS.md, HARD_STOP.json, docs/superpowers/plans/*.md (checkboxes não marcados, especialmente 2026-10-16-automatize-caixinhas-execucao.md Task 5 humanização e 2026-11-03-hermes-25-clientes.md), docs/AGENTES-AUDIO-HERMES.md, docs/REA-QUADRO-AUTOMACOES-20261016.md, docs/OPERACAO.md, docs/CUSTOS-E-TROCA.md. Agrupe por: entrada WhatsApp, humanização/Hermes, envio/outbox/autoridade humana, worker de áudio, TTS, backup/virada, Kommo.
2. No código (src/): o que existe para (a) chamada de perfil Hermes (hermes-profile-provider, agent-runtime, agent-policy, bot-composer, lead-context) — qual contrato/endpoint, há modo de aprovação humana antes do envio?; (b) webhooks de saída (existe ação webhook em bots/gatilhos? docs/GATILHOS.md cita 2 webhooks); (c) Telegram (qualquer integração/notificação); (d) Vercel ou publicação de relatório; (e) mudança de etapa de lead por bot (change_status) e se o fluxo 198416 tem passos 120/121 change_status ativos; (f) controle de envio existente (sending_enabled), outbox, autoridade humana; (g) projectWhatsAppMessage em src/channels/whatsapp-inbox.mjs e o retorno quando falta lead_id.
3. Fora do repo, apenas verificar existência (sem ler segredos): ~/.hermes (perfis existentes como janaina? config de gateway Telegram existe?), e se a API Hermes 8642 é mencionada nos docs como necessária.
Entregue: lista de pendências bloqueantes para "Janaína respondendo com aprovação humana amanhã", lista do que já existe e pode ser reaproveitado, e lacunas sem nenhum código.
```

## Tentativa recusada de chamar /to-spec pelo modelo

2026-11-25T00:05:07.744Z · 2f15e16c-24cf-42d4-8524-e45b2704306d, linha 554. Na linha 555, a ferramenta devolveu `disable-model-invocation` e orientou o usuário a invocá-la diretamente.

```text
/to-spec Deploy de 25/11: Janaína em Shadow no TropicDesk. Decisões já fechadas em docs/superpowers/specs/2026-11-24-janaina-shadow-gerente.md (9 tarefas do deploy + 3 posteriores). Usar esse documento e o levantamento do código desta conversa.
```

## Sugestão para copiar · /to-spec

2026-11-25T00:05:11.909Z · 2f15e16c-24cf-42d4-8524-e45b2704306d, linha 557

```text
/to-spec Deploy de 25/11: Janaína em Shadow no TropicDesk. Base: docs/superpowers/specs/2026-11-24-janaina-shadow-gerente.md (9 tarefas do deploy + 3 posteriores).
```

## Sugestão para copiar · /to-tickets

2026-11-25T00:05:11.909Z · 2f15e16c-24cf-42d4-8524-e45b2704306d, linha 557

```text
/to-tickets
```

## Sugestão para copiar · /to-spec

2026-11-25T00:07:26.818Z · 2f15e16c-24cf-42d4-8524-e45b2704306d, linha 587

```text
/to-spec Deploy de 25/11: Janaína em Shadow no TropicDesk. Base: docs/superpowers/specs/2026-11-24-janaina-shadow-gerente.md (9 tarefas do deploy + 3 posteriores).
```

## Sugestão para copiar · /setup-matt-pocock-skills

2026-11-25T00:10:34.409Z · 2f15e16c-24cf-42d4-8524-e45b2704306d, linha 655

```text
/setup-matt-pocock-skills
```

## Chamada de skill · /ai-memory-handoff

2026-11-25T00:52:24.998Z · 2f15e16c-24cf-42d4-8524-e45b2704306d, linha 1376

```text
/ai-memory-handoff Salvar handoff do CRM TropicDesk para a próxima sessão (resumo no topo de HANDOFF.md).
```

## Sugestão para copiar · /to-tickets

2026-11-25T00:53:25.546Z · 2f15e16c-24cf-42d4-8524-e45b2704306d, linha 1436

```text
/to-tickets #1 — Publicar os 14 tickets já aprovados (T1–T14) exatamente como estão no TODO.md (mesma ordem, nomes, resumos e bloqueios), sem refazer a quebra. Antes, leia o topo do HANDOFF.md e a spec docs/superpowers/specs/2026-11-24-janaina-shadow-gerente.md. Me mostre os bloqueios para um ok final, depois publique como sub-issues da #1 com bloqueio nativo e rótulo ready-for-agent (T1 e T14 como ready-for-human), salve a cópia de cada uma em docs/issues/ e anote o número de cada issue no TODO.md, mantendo o formato título + "Resumo:" que o Watchdog lê.
```

## Sugestão para copiar · /implement

2026-11-25T00:53:25.546Z · 2f15e16c-24cf-42d4-8524-e45b2704306d, linha 1436

```text
/implement #<número da issue> — Trabalhe numa worktree persistente em .worktrees/<ticket>, nunca em /tmp. Não toque no serviço 8766, no Baileys nem no banco do Kingston; use SQLite isolado e falsos. Commit por marco verificado, e ao final atualize a issue e a cópia em docs/issues/.
```

## Sugestão para copiar · /to-tickets

2026-11-25T00:56:01.500Z · 2f15e16c-24cf-42d4-8524-e45b2704306d, linha 1444

```text
/to-tickets #1 — Antes de tudo, religue o Watchdog a esta sessão: o painel Tasks deste projeto está no pane wZ:pC rodando a versão de acompanhamento em ~/Projects/herdr-watchdog/.worktrees/tasks-somente-leitura (branch feat/tasks-somente-leitura), ainda ligado à sessão anterior 2f15e16c. Descubra o ID desta sessão (jsonl mais recente em ~/.claude/projects/-mnt-nextcloud-00-workspaces-01-projects-tropicdesk-kommoclone-tropicdesk-kommoclone/) e o seu pane ($HERDR_PANE_ID). Rode python3 ~/Projects/herdr-watchdog/.worktrees/tasks-somente-leitura/watchdog layout 2 --repo "$PWD" --pane "$HERDR_PANE_ID" --session <ID desta sessão>. Confira com pgrep -af "watchdog-preview.py tasks --repo /mnt/nextcloud" que o Tasks em wZ:pC roda a partir da worktree tasks-somente-leitura com o binding desta sessão. Se estiver rodando a versão da main ou a sessão antiga, encerre só aquele processo pelo PID e reabra no mesmo pane com herdr pane run wZ:pC "python3 ~/Projects/herdr-watchdog/.worktrees/tasks-somente-leitura/tools/watchdog-preview.py tasks --repo <repo> --yazi-client-id <o mesmo de antes> --binding-file <binding desta sessão>". Confirme lendo a tela (herdr pane read wZ:pC) que aparecem [Review r] [Verificar v] [Quit q] e o ID desta sessão. Não altere a main do Watchdog nem outros projetos.

Depois: publicar os 14 tickets já aprovados (T1–T14) exatamente como estão no TODO.md (mesma ordem, nomes, resumos e bloqueios), sem refazer a quebra. Leia antes o topo do HANDOFF.md e a spec docs/superpowers/specs/2026-11-24-janaina-shadow-gerente.md. Me mostre os bloqueios para um ok final; depois publique como sub-issues da #1 com bloqueio nativo e rótulo ready-for-agent (T1 e T14 como ready-for-human), salve a cópia de cada uma em docs/issues/ e anote o número de cada issue no TODO.md, mantendo o formato título + "Resumo:" que o Watchdog lê.
```

## Sugestão para copiar · /to-tickets

2026-11-25T00:58:50.478Z · 2f15e16c-24cf-42d4-8524-e45b2704306d, linha 1475

```text
/to-tickets #1 — Antes de tudo, religue o Watchdog a esta sessão: o painel Tasks deste projeto está no pane wZ:pC rodando ~/Projects/herdr-watchdog/.worktrees/tasks-somente-leitura (branch feat/tasks-somente-leitura), ligado à sessão anterior 2f15e16c. Descubra o ID desta sessão (jsonl mais recente em ~/.claude/projects/-mnt-nextcloud-00-workspaces-01-projects-tropicdesk-kommoclone-tropicdesk-kommoclone/) e o seu pane ($HERDR_PANE_ID); rode python3 ~/Projects/herdr-watchdog/.worktrees/tasks-somente-leitura/watchdog layout 2 --repo "$PWD" --pane "$HERDR_PANE_ID" --session <ID desta sessão>. Confira com pgrep -af "watchdog-preview.py tasks --repo /mnt/nextcloud" que o Tasks em wZ:pC roda da worktree com o binding desta sessão; se não, encerre só aquele processo pelo PID, mande ctrl+c ao pane e reabra com herdr pane run wZ:pC "python3 ~/Projects/herdr-watchdog/.worktrees/tasks-somente-leitura/tools/watchdog-preview.py tasks --repo <repo> --yazi-client-id 1795566405949071921 --binding-file <binding desta sessão>". Confirme com herdr pane read wZ:pC. Não altere a main do Watchdog.

Depois publique os 14 tickets já aprovados (T1–T14) exatamente como estão no TODO.md, sem refazer a quebra. Leia antes o topo do HANDOFF.md e a spec docs/superpowers/specs/2026-11-24-janaina-shadow-gerente.md. Mostre os bloqueios para um ok final; publique como sub-issues da #1 com bloqueio nativo e rótulo ready-for-agent (T14 como ready-for-human), salve a cópia em docs/issues/ e anote o número de cada issue no TODO.md, mantendo título + "Resumo:".
```

## Sugestão para copiar · /implement

2026-11-25T00:58:50.478Z · 2f15e16c-24cf-42d4-8524-e45b2704306d, linha 1475

```text
/implement — Implemente nesta sessão, em ordem de dependência, todos os tickets da #1 que não dependem dos 4 itens da seção Bloqueado do TODO.md (token do Telegram, senha da Vercel, autorização Baileys/envio, campos da qualificação): T1 a T13. Use falsos no lugar do token e da senha; não faça deploy na Vercel nem crie projeto Neon sem meu ok (use um Postgres local ou falso para o contrato). Deixe para amanhã de manhã só esses 4 itens e a T14 (go-live).
Regras: worktree persistente em .worktrees/<ticket>, nunca /tmp; não toque no serviço 8766, no Baileys nem no banco do Kingston (a T1 só lê o banco para gerar o backup e restaura numa cópia isolada); commit por marco verificado; npm test verde a cada ticket; feche cada issue com evidência e atualize docs/issues/ e o TODO.md (mover para Feito com data). Ao concluir cada ticket, escreva "Tn concluído: commit, testes" para o curador do Watchdog marcar.
```

## Sugestão para copiar · /to-tickets

2026-11-25T01:02:04.548Z · 2f15e16c-24cf-42d4-8524-e45b2704306d, linha 1489

```text
/to-tickets #1 — Publique os 14 tickets já aprovados (T1–T14) exatamente como estão no TODO.md: mesma ordem, nomes, resumos e bloqueios, sem refazer a quebra. Leia antes o topo do HANDOFF.md. Mostre os bloqueios para um ok final, depois publique como sub-issues da #1 com bloqueio nativo e rótulo ready-for-agent (T14 como ready-for-human). Salve a cópia em docs/issues/ e anote o número de cada issue no TODO.md, mantendo título + "Resumo:".
```

## Sugestão para copiar · handoff do Watchdog

2026-11-25T01:03:27.683Z · 2f15e16c-24cf-42d4-8524-e45b2704306d, linha 1526

```text
Vamos fazer mais algumas modificações no painel Tasks do Watchdog nesta worktree (branch feat/tasks-somente-leitura). Leia antes HANDOFF-tasks-somente-leitura.md aqui na raiz e o diff atual (git diff + tests/test_tasks_monitor.py), que ainda não tem commit. Essa versão roda só no projeto TropicDesk, no pane wZ:pC. Não mexa na main nem nos outros projetos, e não faça commit, push ou merge sem eu pedir. Para cada mudança de UI, me repasse o entendimento com um antes/depois e espere meu ok. Depois rode os testes com e sem WATCHDOG_FULL_CONTROLS=1. Para eu ver no painel, mande ctrl+c ao pane wZ:pC e reabra o watchdog-preview.py da worktree com o comando que está no handoff (encerre processos só pelo PID). Me pergunte agora quais modificações eu quero.
```

## Sugestão de meta para o long run

2026-11-25T01:24:39.573Z · 087c7d8d-5371-49cb-a761-4a1ead6b98a3, linha 615. O comando aplicado está em [comandos de execução](comandos-execucao.md).

```text
Levar os tickets T3–T13 da spec #1 até integrados na branch implementacao, um Codex novo por ticket (gpt-6.1-sol, esforço médio, full access, worktree em .worktrees/), respeitando os bloqueios do TODO.md (T3→T4→T5 em sequência). Esperar sem polling: os Codex avisam no painel wZ:pG; manter só uma espera em segundo plano como rede de segurança. A cada aviso: revisar (diff, focais, npm test), integrar, fechar a issue com comentário, atualizar docs/issues/ e TODO.md, commitar sem push e escrever "Tn concluído: commit, testes". Bloqueio coberto pela spec: desbloquear; não coberto: parar e perguntar ao Vini. Nas partes que dependem de Neon, Vercel e Telegram, construir com os falsos e parar antes de usar credenciais reais. T14 fica fora. Nunca tocar no serviço 8766, no Baileys nem no sending_enabled.
```
