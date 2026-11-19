# Verificação — Despachar para um agente

Tarefa 56b84864-b28d-4a82-b341-84b8d3545e3e, ainda aberta para aceite.

- Suíte final: `python3 -B -m unittest discover -s tests -q`, 385 testes, sem falhas, 7 opt-in ignorados. Baseline: 363 testes, 7 ignorados.
- 22 testes novos: contrato/seleção de destinatário, isolamento Git, revisão do líder, bloqueio de aprovação sem revisão, versão/commit/identidade obsoletos, incerteza de entrega e encerramento do host sem encerrar o agente; teclado/mouse e PTY real.
- Fluxo completo com Git temporário: entrega nativa com fronteira de identidade/fila substituída, relatório persistido, recusa de aprovação sem revisão, revisão registrada e integração local do commit exato. Nenhum modelo real foi iniciado.
- Painéis reais Tarefas (`wD:p8`) e Progresso (`wD:p9`) recarregados nos mesmos terminais; identidades dos quatro painéis preservadas. Nenhum ator/painel foi criado, removido ou movido.
- Revisão do código pelo líder; não é auditoria independente.

Captura nativa da tela de Tarefas, usando `herdr pane read --source visible --format text`:

```text
Despachar
Para um agente · revisão pelo líder
Orquestrar equipe · executor + QA
[Escolher Enter] [Cancelar Esc]
```

A seleção do primeiro modo mostrou:

```text
Escolher executor · uma tarefa por execução
Somente sessões Codex ociosas em worktree limpa deste repositório.
Nenhum executor elegível. Abra uma sessão dedicada em uma worktree
  limpa e isolada do projeto.
```

Falta uma sessão elegível para validação com um modelo real. A seleção foi cancelada e desmarcada; não houve envio de tarefa nem conclusão automática. TODO validado: 24 tarefas, 12 abertas, 12 concluídas (11 históricas). As alterações estão no checkout principal, sem commit ou push nesta entrega.
