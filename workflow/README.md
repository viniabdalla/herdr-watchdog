# Prompts da orquestração do TropicDesk

Em 24 e 25 de novembro de 2026, o Vini usou o Watchdog para acompanhar o trabalho da sessão líder no Herdr. O arquivo reúne os pedidos de planejamento e execução, o texto da meta e os contratos que chegaram aos Codex. Os horários nas transcrições estão em UTC.

[Abrir o fluxograma interativo no Archify](archify/fluxo-watchdog.html) · [Editar a fonte JSON](archify/fluxo-watchdog.json)

## Para retomar o brainstorming

- [Que mensagem iniciou cada etapa](etapas-do-long-run.md) liga os pedidos do Vini às chamadas de skills, aos contratos e à revisão. Inclui o diagnóstico inicial e as cinco rodadas entre Codex e Claude.
- [Desenho em aberto e prompt para a próxima sessão](brainstorm-proxima-sessao.md) registra o comportamento desejado para Matt, a hipótese para outros clientes e as decisões que ainda merecem conversa.
- [Code review observado](code-review-observado.md) registra a aba própria no Herdr, os dois contratos recebidos pelos Codex e os avisos ao líder. [Prompt de code review para adaptar](code-review-da-integracao.txt).
- [Texto proposto para a meta da seleção](meta-da-selecao.txt) traz a regra para trabalhar as liberadas, reavaliar dependências e avisar sobre as que continuarem bloqueadas.

## Comandos do Vini

- [Planejamento e preparação do Watchdog](comandos-planejamento.md) reúne 62 entradas, da definição de escopo ao handoff. Inclui os comandos de skills, as correções e as aprovações curtas na ordem da conversa.
- [Execução do long run](comandos-execucao.md) reúne 25 entradas. O comando `/goal` está na linha 651 da fonte. A configuração dos workers, a espera por avisos, a regra de abrir uma sessão nova por tarefa e a decisão de adiar a auditoria estão na mesma sequência.
- [Preparação pelo líder](preparacao-do-lider.md) reúne a delegação de levantamento, as chamadas de skills e os prompts de passagem de sessão e de meta sugeridos para copiar.

## Prompts do líder recebidos pelos executores

São 21 mensagens distintas em 15 worktrees. Cada arquivo começa com o contrato recebido pelo Codex. Onde houve nova orientação, ela vem em seguida. T5b e T8i foram trabalhos de integração. A verificação visual reuniu o card do T4 e o seletor do T6.

| Trabalho | Painel | Prompts |
| --- | --- | ---: |
| [T2](executores/t2.md) | `wZ:pJ` | 2 |
| [T3](executores/t3.md) | `wZ:pK` | 3 |
| [T6](executores/t6.md) | `wZ:pM` | 3 |
| [T4](executores/t4.md) | `wZ:pN` | 1 |
| [T7](executores/t7.md) | `wZ:pP` | 1 |
| [T5](executores/t5.md) | `wZ:pQ` | 1 |
| [T8](executores/t8.md) | `wZ:pS` | 1 |
| [T9](executores/t9.md) | `wZ:pT` | 1 |
| [T10](executores/t10.md) | `wZ:pV` | 2 |
| [T11](executores/t11.md) | `wZ:pW` | 1 |
| [T5B](executores/t5b.md) | `wZ:pX` | 1 |
| [T8I](executores/t8i.md) | `wZ:pY` | 1 |
| [T12](executores/t12.md) | `wZ:p0` | 1 |
| [T13](executores/t13.md) | `wZ:p11` | 1 |
| [Verificação visual T4 + T6](executores/verificacao.md) | `wZ:p12` | 1 |

## Fontes e cobertura

O planejamento está no registro Claude `2f15e16c-24cf-42d4-8524-e45b2704306d`. A execução começou em `d2f1a2bf-79cf-4dad-b587-fbf3c735e060` e aparece com a continuação em `087c7d8d-5371-49cb-a761-4a1ead6b98a3`. O trecho comum foi contado uma vez. A coleta inclui a revisão da manhã e a autorização do Vini para abrir o Codex de correção, em 2026-11-25T12:31:56.598Z. Os dois contratos de revisão estão em arquivo próprio, fora da contagem dos 15 executores de implementação.

Os textos dos contratos e retornos do líder foram extraídos das mensagens de entrada dos Codex. Cada entrada indica arquivo e linha da transcrição. Quando o mesmo texto reaparece numa cópia da sessão, as duas referências acompanham uma única entrada. Os avisos de conclusão enviados pelos workers, as notificações automáticas e as saídas de ferramentas ficam fora da contagem de comandos humanos. Os identificadores de painel e os caminhos nos prompts são os da execução original.
