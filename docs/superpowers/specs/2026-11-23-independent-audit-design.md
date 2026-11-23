# Auditoria independente do projeto

A ação **Auditoria A** de Tasks abre uma avaliação de leitura, independente de
missões de implementação/planejamento. Não exige seleção de TODO. O usuário
escolhe uma conta Codex verificada no projeto, consulta `model/list` dessa conta,
escolhe o modelo e confirma uma nova aba. A CLI permite informar outra conta
explicitamente. GPT Astra 6.1 só recebe preferência se `gpt-6.1-astra` estiver
listado; sua ausência exige escolha explícita.

A aba Herdr nasce com `--cwd` do projeto. Um wrapper host roda o Codex app-server
nessa aba e cria uma sessão por `thread/start`; não abre a TUI interativa. Nenhum
resume/clone/handoff é utilizado. O brief contém apenas ID da auditoria, caminho,
revisão Git, fingerprint do estado e contrato de saída limitado a 8 KiB. Não há
texto de conversa do líder, tarefas selecionadas ou transferência de liderança.

O provider deve confirmar modelo solicitado, cwd, nova thread sem turnos,
`readOnly` sem rede de ferramentas e aprovação `never` antes de `turn/start`.
Uma divergência ou reroute interrompe a auditoria, sem fallback. O host consulta
`config/read` para desabilitar todos os servidores MCP da configuração efetiva,
apps, memórias, hooks e multi-agent nessa thread. O processo recebe
`-c features.hooks=false` antes de `app-server`, impedindo hooks de ciclo de vida
já na inicialização e antes de criar thread; nenhum config real é alterado.
Pedidos RPC de ferramenta/aprovação
são recusados. O runtime permanece somente biblioteca padrão e Python 3.10+.
A conta Codex continua guardando sua própria sessão/autenticação; o sandbox de
leitura se aplica às ferramentas do auditor, não aos arquivos operacionais do host.

O host coleta o resultado em `audits/<UUID>/report.md`, sela SHA256 e registra
modelo efetivo, sessão/turno, prova do provider e identidade integral do líder.
Saídas parciais ficam na evidência de falha. A entrega usa a fila nativa do líder
original e requer conta/thread/pane/processo, projeto e binding ainda idênticos.
Nenhum binding é reanexado ou redirecionado pela verificação do destinatário.
A mesma validação raw se aplica às entradas CLI, abertura UI, confirmação e
lançamento: não chamam construtor, `verify` nem `routing` de `Session`. O
lançamento adquire diretamente o lease de Clean sessions, verifica operações
não encerradas e recusa identidade original indisponível, mesmo se a mesma
conversa tiver reaparecido em outro pane.

Intenções persistem antes de criar aba, iniciar wrapper ou enviar resultado.
Uma auditoria ativa/incerta impede outra para esse mesmo líder/projeto. Timeout
não repete efeitos nem fecha panes. Wrapper morto/início não confirmado vira
incerto. O resultado final tem uma tentativa automática de entrega: líder ocupado
ou destinatário indisponível preserva o relatório para entrega manual explícita;
entrega incerta/enviada não pode ser repetida. Mudança detectada no estado Git
preserva relatório histórico sem envio. Não há aceitação de tarefa, alterações
no TODO, merge ou push em nenhuma transição.

O fingerprint detecta revisão, status e diff rastreado. Ele não é uma captura
atômica do filesystem e não atesta conteúdo de arquivos ignorados/não rastreados.
Achados precisam declarar essa lacuna e citar as evidências efetivamente lidas.
