# Despachar para um agente

Tarefa: 56b84864-b28d-4a82-b341-84b8d3545e3e. Entendimento aprovado pelo usuário em 2026-11-18.

A ação Despachar oferece Para um agente e Orquestrar equipe. Para um agente seleciona um executor Codex ocioso, identificado por painel, sessão e conta, em uma worktree limpa e isolada do mesmo repositório. Confirma destinatário e tarefa antes de solicitar o contrato ao líder. Não inicia nem reinicia conversas; preserva envio simples e equipe com QA. Uma tarefa lógica por execução, conforme a política atual de conversas dedicadas.

## Abordagem

Reutilizar o ledger, o transporte nativo, o host bridge para atores existentes, o contrato delimitado e o monitor. Escolha de implementação: modo explícito `single` com revisão `leader`; ledgers sem modo continuam `team` e exigem QA. Evita um segundo mecanismo de relatório ou interpretar texto de conversa como sucesso. A alternativa de iniciar um executor automaticamente não permite escolher o painel já existente; remover QA globalmente enfraqueceria o fluxo de equipe.

O executor é verificado novamente na confirmação e no lançamento, incluindo conta/thread, terminal/PID, disponibilidade, worktree, branch e commit base. Ledger registra intenção antes de iniciar bridge/notificar; entrega incerta não é reenviada automaticamente. Nenhuma injeção de texto no painel. Progresso abre o painel existente e mostra revisão pelo líder.

O resultado continua exigindo commits completos e evidências de testes. O líder registra resumo, testes observados, veredito, commit candidato e versão do resultado em uma revisão explícita; o backend verifica os commits relatados, o head limpo do executor e a identidade do líder. Novo relatório ou follow-up invalida a revisão. Aprovação separada exige revisão aprovada para o commit/versão exatos e conserva integração existente. Enviar, revisar e aprovar não conclui TODO automaticamente.

## Restrições e verificação

Somente biblioteca padrão Python. Left Undone somente leitura. Nunca parar Herdr ou alterar atores/painéis existentes. Não alterar arquivos protegidos ou execuções legadas. Exercitar Git temporário, filas falsas nas fronteiras nativas, teclado/mouse de seleção e confirmação, falhas de identidade/entrega, rejeição de revisão obsoleta e regressão da equipe. Não lançar tarefas reais nem consumir cota de modelos para demonstrar este recurso.
