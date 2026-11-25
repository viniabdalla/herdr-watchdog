---
number: 18
title: "Religar no mesmo pane e confirmar a conversa atual do Codex"
state: closed
labels: ["ready-for-agent"]
url: https://github.com/viniabdalla/herdr-watchdog/issues/18
parent: 17
blocked_by: []
updated: 2026-11-25
---

## Parent

#17

## What to build

Quando a pessoa escolhe novamente o pane do líder Codex e o Herdr repete o ID salvo, o Tasks permite comprovar a conversa que está visível. Este primeiro percurso termina com a confirmação de A quando a sessão realmente continua em A.

## Acceptance criteria

- [ ] Ao acionar Religar, o Tasks identifica o pane escolhido e oferece uma instrução curta para copiar na conversa. Enquanto aguarda, não anuncia sucesso nem envia texto ao líder.
- [ ] A recuperação executa na conversa escolhida com marcador novo. Só aceita prova única associada ao histórico da sessão atual, conta, processo, pane, terminal e projeto, seguida de releitura da identidade nativa completa.
- [ ] Quando a conversa confirma A e a identidade nativa concorda, o aviso e o cabeçalho mostram o pane e o prefixo de A. Repetir conserva o vínculo e o grupo.
- [ ] Prova ausente ou ambígua, outro pane, mudança de terminal ou cancelamento resultam em “Sessão não confirmada”. A pessoa pode repetir. Nenhuma prova inconclusiva muda o líder ou dispara entrega.
- [ ] Demonstrar o fluxo pela tecla Religar em pseudo-terminal isolado (ponto A), modelando em separado a conversa efetiva e o ID anunciado pelo Herdr. Citar nos testes as linhas da spec local.


## Comentários

### 2026-11-25T19:17:58Z · viniabdalla

Implementado na branch de integração local, commit 5c6584da6589. O Tasks pede confirmação no mesmo pane Codex e só reconhece a sessão A após a prova. Foram verificados cancelamento, prova inválida, cópia em painel estreito e reabertura. A suíte da integração executou 680 testes em cada configuração (controles padrão e completos), com 7 ignorados por modo e nenhuma falha. O aceite humano continua em #20.
