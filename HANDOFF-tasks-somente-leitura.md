# Handoff do Watchdog Tasks · 25/11/2026 · implementação da spec #1

A próxima sessão é o **líder implementador** da spec #1. O brainstorm terminou, a spec e os tickets T1–T14 estão publicados e o painel já acompanha o grupo. A implementação começa quando o Vini mandar o `/goal`. Antes disso, o líder só lê e repassa o entendimento.

## Onde está tudo

- **Worktree e branch de integração:** `~/Projects/herdr-watchdog/.worktrees/tasks-somente-leitura`, branch `feat/tasks-somente-leitura`, commit `7b2f3cf`. Esta worktree é o **checkout de integração**: aqui o líder só junta e confere. Sem push até o Vini pedir.
- **Spec:** issue #1 de `viniabdalla/herdr-watchdog`, cópia em `docs/issues/1-spec-watchdog-painel-long-run.md`.
- **Tickets:** T1–T14 são as issues #2–#15, sub-issues da #1 com bloqueio nativo; cópias em `docs/issues/2-t1-…` a `15-t14-…`; no `TODO.md` em `## Próximo`, como "Tn (#n) título", na ordem de execução. T14 é o aceite do Vini (`ready-for-human`) e fica fora do trabalho dos agentes.
- **Tracker:** `docs/agents/issue-tracker.md`. GitHub com cópia local obrigatória em `docs/issues/`, atualizada na mesma operação.
- **Vocabulário:** `GLOSSARY.md`. Use os termos dele: líder, executor, grupo, despacho, meta, leva, porta dupla/única.
- **Origem das decisões:** a pasta `workflow/` (prompts reais do long run anterior, contratos dos executores em `workflow/executores/`, code review em `workflow/code-review-observado.md`) e o mockup aprovado em `workflow/mockups/progress-agentes.py`.

## Ordem das levas

```
Leva 1:  T1 (#2), T2 (#3)
Leva 2:  T3 (#4), T4 (#5), T5 (#6), T6 (#7), T7 (#8)    depois do T1
Leva 3:  T8 (#9) depois do T6; T9 (#10) e T10 (#11) depois do T7
Leva 4:  T11 (#12) depois do T8; T12 (#13) depois do T7 e T8; T13 (#14) depois do T6 e T11
Fim:     T14 (#15), o Vini
```

**Conflitos:** T1, T2, T3, T4, T5 e T7 mexem na mesma tela do Tasks; T11 e T13 na mesma seção do Progress. Podem rodar em paralelo, mas junte um de cada vez e confira as costuras de cada um contra o que já entrou.

## Regras do dispatch (valem até o T1 escrever o padrão definitivo)

Estas são as regras que funcionaram no long run anterior, já com as decisões do brainstorm. O T1 transforma isto no padrão do Watchdog; até lá, valem daqui.

1. **Um Codex novo por ticket**, visível no Herdr, numa worktree persistente em `.worktrees/<ticket>` dentro desta worktree, com branch própria criada a partir de `feat/tasks-somente-leitura`. Nunca em `/tmp`. Modelo **gpt-6.1-sol**, esforço **médio**, full access, salvo instrução diferente do Vini.
2. **Uma aba por leva** no workspace `w11`, nomeada pelo tema e pelos tickets (por exemplo "Leva 1 T1 T2"). Tickets liberados depois entram na aba da leva de que dependiam, enquanto houver espaço.
3. **Contrato do executor** com ponteiros, não cópias: issue do ticket, spec #1, glossário, worktree e branch, regras abaixo e aviso. Rodapé comum:
   - leia `AGENTS.md` e `GLOSSARY.md` antes;
   - trabalhe só na sua worktree e branch; commit por marco verificado, sem push;
   - teste primeiro (TDD), pelos pontos de teste A e B da spec;
   - a aprovação do ticket pelo Vini já cobre qualquer pedido de "repassar o entendimento e esperar ok": siga direto, só pare se a spec não decidir algo ou se contradisser;
   - não edite `TODO.md` nem `HANDOFF*`, não comente nem feche issues: o líder revisa e integra;
   - não mexa no Left Undone nem nos painéis do Watchdog em execução;
   - antes do último commit, faça `git merge feat/tasks-somente-leitura` na sua branch e rode `python3 -m unittest discover -s tests` duas vezes: com `WATCHDOG_FULL_CONTROLS` ausente e com `WATCHDOG_FULL_CONTROLS=1`;
   - **aviso ao líder**: ao terminar, `herdr pane send-text <pane do líder> '[Tn · painel <seu pane>] Tn pronto: commit <sha>, testes <resultado>. <resumo de 1-2 linhas>'` e depois `herdr pane send-keys <pane do líder> Enter`; para dúvida que a spec não decide, o mesmo com `BLOQUEIO: <dúvida em até 3 linhas>`, e espere a resposta. Uma mensagem por evento.
4. **Checagem inicial**: olhe cada executor novo aos 2, 3 e 4 minutos e redirecione se estiver no rumo errado. Depois disso, só espere o aviso, com uma espera em segundo plano como rede de segurança. Sem polling.
5. **A cada aviso**, antes de integrar: confira cada critério de aceite do ticket, as costuras com o que já entrou e se algum teste novo congela comportamento sem citar a linha da spec. Rode as duas suítes no checkout de integração.
6. **Integrar**: merge na `feat/tasks-somente-leitura`, comentário de fechamento e fechar a issue, atualizar a cópia em `docs/issues/`, mover a tarefa para `## Feito` no `TODO.md` com data, commit sem push, e escrever na conversa **"Tn concluído: commit, testes"**. É assim que o curador e o Progress acompanham.
7. **Bloqueio coberto pela spec**: responda e desbloqueie. **Não coberto**: pergunte ao Vini na hora, sem parar os outros tickets; se ele não responder, o bloqueio vai para o aviso final.
8. **Integração só aqui**: este checkout não recebe trabalho de implementação. O líder trabalha só em worktrees.
9. **Aviso final**: concluídos com commit e testes; bloqueados com motivo e próximo passo.
10. **Depois de tudo**: o Vini pede o code review (aba "Code Review", dois Codex, Standards e Spec, relatórios lado a lado), a correção vai para uma aba nova só depois do ok dele, depois `/retro` e o teste dele (T14). O Vini decide o merge danger e o push.

Guarde contratos, relatórios e comentários de fechamento em `.watchdog/run/2026-11-25/` dentro desta worktree; confira se `.watchdog/` está no `.gitignore` e acrescente se não estiver.

## Painéis do Watchdog

O layout do Watchdog (layout 2) está na aba `w11:t1`: conversa em `w11:p1`, Tasks em `w11:p4`, Progress em `w11:p5`, Artifacts em `w11:p6`, Yazi em `w11:p7`. Os painéis rodam o código **desta worktree** e estão ligados à sessão anterior (`w11:p1`, sessão `a2735162`).

- **Religar ao novo líder:** o vínculo atual exige a mesma sessão viva, então `/clear` ou sessão nova quebram o vínculo (o T10 resolve isso). Peça ao Vini a confirmação e religue os painéis à sua sessão. No long run anterior isso foi feito pela transferência de vínculo do Watchdog (`Store` e `bindings`, como em `workflow/etapas-do-long-run.md`); a alternativa simples é fechar os panes `w11:p4`–`w11:p7` e rodar `./watchdog layout 2 --repo <esta worktree> --pane <seu pane> --session <sua sessão>`.
- **Grupo do Progress:** T1–T14 já estão salvos como grupo (0 de 14). O grupo fica no estado do Watchdog, não na sessão, então sobrevive à religação.
- **Painel que muda a si mesmo:** como os painéis rodam o código desta worktree, cada merge que mexe no Tasks ou no Progress só aparece depois de reiniciar o painel. Antes de reiniciar, confira o pane e o binding em uso e encerre o processo pelo PID.

## Prompt para colar na nova sessão

```text
Leia HANDOFF-tasks-somente-leitura.md nesta worktree. Você é o líder implementador da spec #1 do herdr-watchdog. Leia a spec (docs/issues/1-spec-watchdog-painel-long-run.md), os tickets T1–T14 em docs/issues/, o TODO.md, o GLOSSARY.md e o AGENTS.md. Ainda não implemente, não abra worktrees nem Codex e não religue os painéis. Repasse para mim o que você entendeu: a ordem das levas e os bloqueios, como vai abrir e acompanhar os executores, o que confere antes de integrar, quando me pergunta e como me avisa no fim. Depois espere meu ok e o /goal.
```
