# Verificação da auditoria independente — 2026-11-23

Contrato `cfd2e586-f9a2-413f-b9cc-5598ef64970d`, run
`4d9a065c-b879-4f18-b95e-6f8fbb2e081e`, base
`ffad902fca5dd0c10ff2ea07a752a81d72483924`.

## Evidências automatizadas

- `python3 -B -m unittest discover -s tests -p 'test_audit*.py' -v`:
  21 testes passaram. Cobrem criação Herdr tab/cwd e novo terminal por API fake,
  confirmação, duplicação, início incerto, wrapper morto, inventário sem modelos
  ocultos/fallback inventado, `thread/start` nova/read-only/never, modelo/cwd/política
  divergentes recusados antes do turno, reroute/falha, MCP/apps desabilitados,
  relatório host com hash, fonte alterada, fila ocupada/incerta/duplicada e
  destinatário exato sem reanexar/escrever binding.
- A fixture `RPCProcessTests` executa um subprocesso Python descartável com JSONL
  real, incluindo eventos anteriores ao ACK. Confirma o uso exclusivo de
  initialize/config-read/thread-start/turn-start, brief sem líder, nova thread,
  sandbox/approval e cwd. Não é um Codex real nem uma demonstração de isolamento
  do kernel. Pedidos de aprovação do servidor interrompem o cliente sem aprovação.
- `python3 -B -m unittest discover -s tests -p 'test_tasks_ui.py' -q`:
  9 testes passaram. Interação curses em PTY real verifica entrada **A** sem seleção,
  escolha conta/modelo, confirmação separada, aviso de Astra 6.1 ausente,
  cancelamento e preservação literal do TODO. A abertura é substituída por fixture.
- `python3 -B -m unittest discover -s tests -p 'test_cli.py' -q`:
  6 testes passaram, incluindo ajuda de `watchdog audit` e recusa sem escolhas
  explícitas antes de qualquer tentativa de abrir auditoria.
- `git diff --check`: passou.

A suíte completa sem variáveis de isolamento inicialmente encontrou duas falhas
no IPC Yazi e uma tentativa de lock TODO fora das raízes graváveis do sandbox.
Com `XDG_RUNTIME_DIR=/tmp/watchdog-audit-runtime` e
`WATCHDOG_STATE_DIR=/tmp/watchdog-audit-test-state`, a suíte completa passou
(459 testes, 7 skips na execução final, incluindo o teste de binding exato). Os diretórios em /tmp contêm apenas estado de teste.

## Limites da demonstração

O contrato autoriza somente worker e QA fornecidos pelo coordenador. Não foi
iniciado terceiro LLM/auditor, aberto pane de auditoria em produção, fechado pane
existente ou reiniciado servidor. A prova de Herdr tab/cwd usa o contrato da API
em fixture. Falta demonstração ao vivo de ponta a ponta: aba Herdr real → thread
Codex nova → sandbox efetivo do runtime → relatório → fila real do líder.

Os schemas usados para verificar o protocolo foram gerados pelo binário Codex
instalado 0.167.0 em /tmp, sem turno de modelo. O cache local observado não listava
`gpt-6.1-astra`; isso não é prova de disponibilidade em outra conta. O produto
consulta `model/list` da conta escolhida e valida a resposta efetiva do provider
antes de iniciar o turno; nenhum modelo alternativo é escolhido silenciosamente.

A implementação usa app-server em um wrapper host na nova aba, não a TUI Codex
interativa nem um ator de missão. Não escreve nem transfere bindings, não cria
worktrees e não usa Clean sessions. O fingerprint Git não captura atomicamente
todos os arquivos: conteúdo ignorado/não rastreado pode mudar sem ser detectado.
O relatório pode representar observações feitas em momentos diferentes.

A entrega do candidato aguarda revisão independente do commit exato e decisão do
coordenador. O TODO permanece aberto.
