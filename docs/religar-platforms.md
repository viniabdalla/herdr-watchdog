# Religar: instalação e plataformas

Requisitos: Python 3.10+ disponível como `python`, Git e Herdr 0.9.1+ com
integração Codex. Os layouts completos também usam Yazi/ya. O fluxo Religar usa
a CLI nativa do Herdr; não usa clipboard nem servidor gráfico.

Em Linux/macOS execute `python install.py`. Em Windows, no PowerShell,
execute `python .\install.py`. O instalador cria `.watchdog-runtime` com psutil
(e windows-curses no Windows), registra o plugin e instala Religar em
`$CODEX_HOME/skills` ou `~/.codex/skills`. Não requer symlinks. A instalação
precisa de rede para pip e de Python com venv/pip. O Python inicial precisa
fornecer curses nos sistemas Unix (pacote Python completo da distribuição).

O comando fica em `~/.local/bin` por padrão; passe `--bin-dir` para uma pasta
já no PATH ou use o caminho completo. No Windows o launcher é `watchdog.cmd`.
A skill contém os caminhos absolutos do Python e do Watchdog: sua execução
independe do cwd, do PATH do launcher e aceita espaços. Cada conta Codex precisa
receber a skill: rode o instalador com seu CODEX_HOME ativo, ou use
`--codex-skills-dir CAMINHO/skills`. Reabra o Codex caso ele já tenha carregado
sua lista de skills antes da instalação.

Ações/panes do plugin chamam `plugin-boot.py`, que seleciona o Python instalado
antes de importar a aplicação. A instalação GitHub pelo Herdr usa o build do
manifesto; `plugin link` não executa build, por isso execute nosso instalador
antes de usar um checkout local. O build sem terminal permite escolher os aplicativos depois com `python install.py --tools-only`. `--no-plugin` prepara somente app/skill;
`--skip-dependencies` reutiliza o Python atual e exige dependências já presentes.

`python uninstall.py` remove somente launcher/skill pertencentes a este checkout
e seu registro de plugin. Passe os mesmos --bin-dir/--codex-skills-dir utilizados
na instalação. Estado, painéis e runtime ficam preservados. Um comando ou skill
de terceiro impede a instalação antes de qualquer alteração nesses destinos.
Reinstalar o mesmo checkout é seguro. Outro checkout não substitui silenciosamente
uma instalação existente.

## Identidade e limites

No Linux, o engine Left Undone existente continua sendo usado quando disponível;
sem ele, ou em macOS/Windows, entra `watchdog_app.portable_runtime`. A interface
Binding e o hash de identidade são compatíveis. Herdr confirma o processo em
primeiro plano, psutil fornece processo/conta/início e o histórico confirma a
sessão completa e o projeto. PID reutilizado ou conta inacessível falham de forma
explícita. Em macOS, restrições do sistema podem impedir `Process.environ()`;
isso resulta em falha, nunca em inferência da conta pelo cwd/foco. A recuperação
Claude e as funções opcionais Analyzer/queue de Left Undone não fazem parte do
fallback Codex. O fluxo Religar não chama essa fila.

Travas usam flock nativo em Unix e msvcrt locking no byte zero em Windows.
A troca atômica grava/fsync o arquivo; o fsync de diretório é aplicado em Unix.
SIGHUP é registrado somente nas plataformas que o expõem. Comandos de abertura
de painéis usam quoting Unix, ou PowerShell no Windows (shell padrão esperado).
Os comandos do manifesto são argv e não passam por esse quoting de shell.

## Evidência desta entrega

| Sistema | Executado | Limite |
| --- | --- | --- |
| Linux | Testes isolados de runtime/Herdr falso; instalação real com pip em cópia temporária com espaços; boot `--help`; instalação repetida/desinstalação em conta temporária | Sem operar painéis ou agentes reais; ensaio humano de ponta a ponta pertence à integração |
| Windows | Dublês das fronteiras msvcrt, quote PowerShell, launcher `.cmd` e manifesto | Host Windows indisponível: instalação, curses e seleção real de pane não executadas |
| macOS | Interface portátil e falha explícita de acesso a processo exercitadas com dublês | Host macOS indisponível: permissões reais de leitura de processos e fluxo humano não executados |

O Vini aceitou nesta entrega a pendência de validação nativa em Windows/macOS.
Os testes com dublês não constituem esse ensaio operacional.

Validação da branch após incorporar a integração com a correção `da7c305`:

- `env -u WATCHDOG_FULL_CONTROLS python3 -m unittest discover -s tests`:
  691 testes, OK, 7 pulados (286,315 s).
- `WATCHDOG_FULL_CONTROLS=1 python3 -m unittest discover -s tests`:
  691 testes, OK, 7 pulados (288,001 s).
- Os 17 testes focados estão em `tests/test_portable_relink.py` e
  `tests/test_platform_compat.py`, com referências às linhas da spec.

As primeiras rodadas expuseram uma intermitência em um teste de fila: o patch
global de `time.sleep` também atingia a espera interna de subprocessos. O líder
corrigiu o isolamento do relógio em `da7c305`; os resultados acima incluem essa
correção. A implementação de entrega da fila recebeu apenas o import portátil
de locking nesta frente.

Fontes oficiais consultadas em 25/11/2026:

- [Herdr plugins](https://herdr.dev/tui/docs/plugins/): comandos argv,
  build e plataformas; link local não roda build.
- [Herdr Windows](https://herdr.dev/tui/docs/windows-beta/): plugins Windows
  são preview/best effort; detecção de processos usa descendentes do shell.
- [Herdr API](https://herdr.dev/tui/docs/socket-api/): CLI recomendada para
  portabilidade Windows; transporte bruto usa named pipes em Windows.
- [Python msvcrt](https://docs.python.org/3/library/msvcrt.html): região de
  locking relativa à posição do arquivo.
- [psutil](https://psutil.readthedocs.io/stable/): suporte às três plataformas,
  create_time e restrições de environ em macOS.
