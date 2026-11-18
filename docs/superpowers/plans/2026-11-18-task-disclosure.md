# Lista de tarefas com resumo expansível

Desenho aprovado por Vini nesta conversa: somente título na lista; setinha abre
Resumo e Situação com espaçamento; outro clique recolhe. Instruções técnicas
continuam completas no envio. Checkbox mantém a seleção independente da expansão.

Execução direta e revisão pelo líder; sem novos agentes, commit ou push.

1. Adicionar testes para linhas recolhidas/expandidas, mouse, Enter, setas,
   painel estreito e envio completo. Observar falha antes da implementação.
2. Alterar `tasks_ui.py`: estado local de expansão por ID, apresentação simples
   e alvos separados para checkbox e setinha. Suportar TODO antigo e v1.
3. Rodar regressão pertinente e suíte completa. Revisar os caminhos de confirmação
   e garantir que expandir não altera TODO, seleção ou execuções.
4. Aplicar a migração já autorizada neste projeto, preservando todas as tarefas e
   conclusões. Reiniciar somente os processos de painéis Tarefas/Progresso em seus
   terminais existentes e verificar o painel vivo, sem parar Herdr ou agentes.
5. Registrar evidências no item existente do TODO e histórico operacional.

Entrega em 2026-11-18: passos concluídos. Oito testes novos observaram falha antes
da implementação e passaram depois, incluindo mouse e teclado no terminal real
descartável, painel estreito, campos ocultos, expansão independente da seleção e
guarda de execução por UUID após mudança de texto. Revisão pelo próprio líder.
Suíte completa: 355 testes sem falhas, 7 opt-in ignorados. `git diff --check` passou.

Aplicação real: uma prévia obsoleta foi recusada sem escrita; outra sessão havia
acrescentado dois pedidos e reordenado o arquivo. A prévia refeita preservou todos
os 24 itens e as 11 conclusões históricas. A tarefa Simplificar foi concluída
após validação, mantendo as outras 12 pendências abertas.

Somente os processos de Tarefas e Progresso foram recarregados por saída normal
nos mesmos painéis wD:p8 e wD:p9. Herdr, agentes, Artifacts e Files permaneceram
intactos. Leitura do viewport vivo confirmou títulos recolhidos, abertura do
primeiro resumo e Situação: Pendente, sem campos técnicos no corpo da lista.
