# Agentes no Progress

A seção AGENTES aparece abaixo das barras, sem ação de envio. O grupo usa o
SHA completo de `long_run.record(repo)['base']` para filtrar o registro do kit.
O TODO informa título e conclusão; a identidade nativa verificada fornece estado
e contexto. Uma sessão publicada depois da abertura só fornece telemetria após
conferência de pane, terminal e diretório da worktree.

Depois de olhar o executor aos 2, 3 e 4 minutos, o líder registra cada checagem:

```bash
/caminho/do/watchdog kit checar --repo /projeto --grupo SHA-COMPLETO --ticket T11 --etapa 1 --resumo 'Rumo conferido; testes em andamento'
```

Use etapas 1, 2 e 3 em ordem. Cada registro conserva horário e resumo em
`.watchdog/executors.json`, sob a mesma trava das aberturas. O Progress mostra
1/3–3/3 somente a partir desses registros. Sem confirmação, mostra a próxima
checagem prevista; tempo decorrido não comprova inspeção. O comando não envia
mensagens, não abre panes e não muda o TODO.

Em painéis baixos, a seção fica antes do checklist e do histórico. As teclas
j/k rolam as linhas para permitir a leitura de todas as levas.
