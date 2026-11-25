# Painel de acompanhamento do Watchdog · handoff de 25/11/2026

Worktree: `~/Projects/herdr-watchdog/.worktrees/tasks-somente-leitura`, branch `feat/tasks-somente-leitura`, criada a partir da `main` em `ae529e2`. O Vini quer essa versão **só no projeto TropicDesk**: os outros projetos seguem com a `main`.

## O que mudou

- `watchdog_app/tasks_ui.py`, no painel **WATCHDOG / TASKS**:
  - Sem `WATCHDOG_FULL_CONTROLS=1`, aparecem só **[Review r] [Verificar v] [Acompanhar no Progress g] [Quit q]**.
  - As teclas A, m/M, c, C, p, P, 0, o, s, d, i, n são ignoradas (`DISABLED_KEYS`).
  - Space (selecionar), Enter/▸ (resumo) e o curador automático continuam como estão, assim como `r`/`a`/`R` nas propostas.
- **Botão novo [Verificar v]:**
  - Exige tarefas selecionadas.
  - Mostra a prévia, com o painel e a sessão principal anotados no binding.
  - Com `y`, chama `session.verify()` e digita o pedido em uma linha no prompt da sessão principal, via `herdr pane send-text <pane> <texto>` e depois `herdr pane send-keys <pane> enter`.
  - Esc cancela sem enviar.
  - O texto vem de `verification_prompt()`.
- `WATCHDOG_FULL_CONTROLS=1` restaura todos os botões. Os testes de despacho e limpeza habilitam esse modo nas próprias fixtures.
- `tests/test_tasks_monitor.py` (novo) usa um `herdr` falso no PATH, que registra o que seria digitado.
- Space seleciona tarefas abertas. **g** grava um grupo fixo por projeto. Usar **g** com uma nova seleção substitui o grupo. O Vini escolhe o primeiro grupo no Tasks.
- Progress abre com a barra do projeto e a porcentagem concluída do TODO. Com um grupo salvo, a barra do long run vem primeiro e a barra do projeto fica logo abaixo, antes da sessão e das execuções. O curador identifica o grupo no pedido de revisão e suas propostas continuam exigindo confirmação.
- O README ganhou a seção "Painel de acompanhamento".
- Verificação: `python3 -m unittest discover -s tests` executou 547 testes (7 ignorados e nenhuma falha) em cada modo, com e sem a variável.

## Como o painel do TropicDesk está rodando

O pane `wZ:pC` roda este comando (ele não usa o `watchdog` instalado, que aponta para a `main`):

```
python3 ~/Projects/herdr-watchdog/.worktrees/tasks-somente-leitura/tools/watchdog-preview.py tasks --repo /mnt/nextcloud/00-workspaces/01-projects/tropicdesk-kommoclone/tropicdesk-kommoclone --yazi-client-id 1795566405949071921 --binding-file <binding da sessão>
```

- Progress roda em `wZ:pD` com o mesmo comando e argumentos, trocando `tasks` por `progress`.
- O Vini religou o painel à sessão nova do CRM.
- Reaplicar um layout com o `watchdog` da `main` recria o painel na versão antiga.
- Para reabrir, mande `ctrl+c` ao pane antes de usar `herdr pane run`, porque texto solto no prompt quebra o comando.
- Encerre processos pelo PID, nunca com `pkill -f`.

## Pontos em aberto

- Decidir se a mudança vira uma opção por projeto (ex.: configuração no estado do Watchdog ou `--monitor`) em vez da variável de ambiente, e como o layout passa a abrir essa versão só no TropicDesk.
- O README da `main` ainda diz que o Watchdog nunca digita no prompt de sessões Claude. O botão `v` abre essa exceção só para a sessão principal anotada, com prévia e confirmação.
- O curador lê só a conversa ligada ao painel. O fluxo combinado: o Codex termina um ticket, a sessão principal relata a conclusão com o título completo ou ID exato da tarefa e as evidências. O curador pode propor a marcação, que o operador revisa no Tasks.
- Nada de commit, push ou merge sem o Vini pedir.
