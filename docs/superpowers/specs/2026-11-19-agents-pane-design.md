# Agents no Watchdog

Aprovado pelo usuário nesta conversa: portar o monitor existente no Left Undone para este repositório, com botão **Agents** no rodapé de WATCHDOG / TASKS. `watchdog pane` seleciona o tipo de painel; `watchdog pane agents` abre diretamente o monitor. Reabrir reutiliza o pane da sessão, sem substituir agentes ou outros painéis.

A implementação usa Python/curses e registros de runs do Watchdog, mantendo os leitores incrementais de uso de contexto do Left Undone. O monitor mostra sessão principal, participantes associados, localização, disponibilidade, entrega e uso de contexto/tokens. Dados ausentes ficam explícitos. Não altera TODO, runs ou banco do Left Undone. A identidade da sessão e o terminal precisam corresponder antes de ler telemetria ou reutilizar um pane.

Abordagem: adaptar o código para módulos locais; importar a UI do Left Undone criaria dependência do banco e dos callbacks daquele produto. Agentes são opcionais no layout e acompanham transferências verificadas de liderança.
