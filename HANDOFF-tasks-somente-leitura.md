# Handoff do Watchdog Tasks · 25/11/2026

A próxima conversa é para brainstormar com o Vini como repetir, pelo Tasks, o long run do TropicDesk. Ele quer continuar escolhendo as tarefas e comandando o líder. O painel prepararia os prompts e chamaria as etapas disponíveis no cliente do líder. A preferência atual é pelo workflow de Matt Pocock. Implementar, despachar agentes ou publicar a branch exige um novo pedido.

## Abrir esta versão no Herdr

```bash
herdr worktree open --cwd "$HOME/Projects/herdr-watchdog" --branch feat/tasks-somente-leitura --focus
```

No terminal que abrir, rode `codex` para começar uma conversa nova. A worktree existente fica em `~/Projects/herdr-watchdog/.worktrees/tasks-somente-leitura`. O código do painel está no commit `c5494e8`, conferido na branch de mesmo nome do remoto `nas`. Nesta branch, a pasta `workflow/` reúne os prompts e o fluxograma usados para retomar a conversa.

## Prompt para colar na nova conversa

```text
Leia HANDOFF-tasks-somente-leitura.md nesta worktree e o roteiro em workflow/brainstorm-proxima-sessao.md. Quero só brainstormar como repetir no Watchdog Tasks o long run do TropicDesk. Eu marco as tarefas. O Tasks prepara o prompt para o líder e aproveita o workflow que o cliente dele tiver, começando pelo do Matt. Quero discutir o /goal da seleção e depois o prompt de code review. Comece com um exemplo: marquei A, que está livre, B, que depende de A, e C, que depende de mim. O que eu vejo no Tasks, o que o líder recebe e qual aviso eu recebo no final? Traga uma decisão por vez e espere minha resposta. Espere meu pedido antes de implementar.
```

## Material para a conversa

| Quando o Vini perguntar… | Onde conferir |
| --- | --- |
| Qual mensagem minha iniciou cada etapa e que skill entrou ali? | [Etapas do long run](workflow/etapas-do-long-run.md), [comandos de planejamento](workflow/comandos-planejamento.md) e [comandos de execução](workflow/comandos-execucao.md) |
| O que mudou entre a instrução do operador e o prompt entregue? | [Preparação do líder](workflow/preparacao-do-lider.md) e [prompts dos executores](workflow/executores/) |
| Como ficou o desenho inteiro? | [Fluxograma Archify](workflow/archify/fluxo-watchdog.html) e [fonte editável](workflow/archify/fluxo-watchdog.json) |
| Como formular o próximo /goal? | [Rascunho da meta](workflow/meta-da-selecao.txt) e [decisões em aberto](workflow/brainstorm-proxima-sessao.md) |
| Qual revisão o Vini pediu no pane do líder wZ:pG? | [Prompt reutilizável](workflow/code-review-da-integracao.txt) e [contratos que os revisores receberam](workflow/code-review-observado.md) |

O [índice do workflow](workflow/README.md) reúne o restante do material. Os prompts dos executores registram ações de uma execução passada.

## Decisões que ficaram para o brainstorming

1. **Escopo da meta.** Hoje, Espaço marca tarefas no Tasks e `g` grava um grupo fixo para o Progress. Gravar o grupo limpa a seleção transitória. Decidir qual lista alimenta o `/goal`. No rascunho, o líder faz A, volta a B quando A termina e relata no fim por que C depende do Vini. Falta combinar quando avisar se todas já começam bloqueadas.
2. **Entrega ao líder.** O botão Verificar já monta o texto com a seleção, mostra uma prévia e identifica a sessão de destino. Decidir quando o operador copia, quando o painel preenche e quando envia após confirmação. No long run, o Vini chamou `/to-spec` diretamente no cliente. O `/goal` também depende do cliente líder. Para Superpowers, a próxima sessão deve considerar as skills realmente disponíveis.
3. **Code review da integração.** O pedido foi abrir uma nova aba visível “Code Review” no Herdr, com dois Codex independentes, um para padrões do repo (Standards) e outro para aderência à especificação (Spec). Os dois recebem a mesma base e o mesmo HEAD e avisam o líder ao terminar. O líder apresenta os relatórios e aguarda o ok do Vini para abrir um terceiro Codex para correções. A sequência prevista segue para retro e teste manual pelo Vini. O botão Review do Tasks continua sendo a revisão das propostas do curador.

## Estado e operação do painel do TropicDesk

- No modo padrão, o Tasks oferece Review, Verificar, Acompanhar no Progress e Quit. Espaço seleciona, Enter expande uma tarefa e `v` abre a prévia do pedido de verificação. Confirmar com `y` envia o pedido à sessão principal registrada no binding. Esc cancela.
- O Vini escolhe o grupo do long run. O Progress mostra a porcentagem concluída do grupo salvo e do TODO inteiro. O curador lê a conversa vinculada e identifica o grupo ao propor marcações. Para uma conclusão aparecer como proposta, o líder deve relatar o título completo ou ID da tarefa e as evidências. O operador revisa a proposta no Tasks.
- A prévia desta branch foi usada só no TropicDesk, em `wZ:pC` (Tasks) e `wZ:pD` (Progress). Abrir a worktree para conversar é independente de reiniciar esses painéis. Se o Vini pedir um reinício, confira o pane e recupere o caminho do binding em uso antes de enviar Ctrl+C. Use a prévia desta worktree. Encerre processos individuais pelo PID.
- Comando da prévia registrado para o Tasks, substituindo o último argumento pelo caminho vigente do binding. Para o Progress, troque `tasks` por `progress`.

```bash
python3 ~/Projects/herdr-watchdog/.worktrees/tasks-somente-leitura/tools/watchdog-preview.py tasks \
  --repo /mnt/nextcloud/00-workspaces/01-projects/tropicdesk-kommoclone/tropicdesk-kommoclone \
  --yazi-client-id 1795566405949071921 --binding-file "<caminho do binding vigente>"
```

O registro da última verificação do código informa 547 testes em cada modo, com 7 ignorados e nenhuma falha em ambos. Para futuras mudanças de UI, apresentar o antes/depois e aguardar o ok do Vini. Depois da mudança, rodar `python3 -m unittest discover -s tests` com a variável `WATCHDOG_FULL_CONTROLS` ausente e novamente com `WATCHDOG_FULL_CONTROLS=1`. Esse segundo modo restaura os controles completos. Uma configuração por projeto para o layout segue em aberto. Trabalhar nesta worktree e aguardar pedido explícito antes de commit, push ou merge.
