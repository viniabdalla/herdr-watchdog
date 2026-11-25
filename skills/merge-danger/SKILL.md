---
name: merge-danger
description: Use when Vini invokes merge-danger after implementation to assess the integration branch or an explicit commit range before it leaves the machine.
disable-model-invocation: true
---

# Merge danger

Avalie em leitura e entregue uma decisão por parte. Esta chamada produz análise;
merge, push, deploy e envio real continuam dependendo da decisão do Vini.
É uma etapa depois da implementação, fora da meta de concluir o grupo.

1. Leia o GLOSSARY.md e a seção `## Dispatch` do AGENTS.md do projeto,
   seguindo o ponteiro para o padrão do dispatch quando houver. Consulte a
   skill `pr` disponível para as definições de porta e raio. Se ela não estiver
   instalada, use as definições abaixo, derivadas da seção Merge Danger de `pr`.
2. Fixe o escopo antes de avaliar: use o intervalo explícito recebido. Sem ele,
   use a base do primeiro despacho registrada no grupo e a branch de integração
   do Dispatch. Registre base, ponta e hashes resolvidos. Se faltar uma dessas
   referências, pergunte ao Vini; não substitua pela branch atual, HEAD~1 ou main.
3. Leia o diff completo, arquivos relacionados e evidências dos testes. Divida
   por comportamento ou operação com riscos próprios, cobrindo todo o intervalo.
   Considere efeitos no uso da mudança, além do efeito de aplicar o diff.
4. Para cada parte, determine porta, raio, evidência, teste útil e decisão segundo
   os critérios abaixo. Evidência ausente vira incerteza explícita. Uma mudança
   mista mantém sua operação de porta única visível em uma parte própria.

**Porta dupla:** é barato voltar atrás. **Porta única:** ação destrutiva ou
que exige reverter uma decisão difícil, como perda de dados ou envio real.
Reverter o código não desfaz dados perdidos nem algo já enviado.
**Raio:** alcance do estrago possível: quem, quais dados, consumidores ou serviços
podem ser atingidos, incluindo efeitos indiretos; descreva alcance e consequência.

A lista de “sempre porta única” (ou “sempre mão única”) da seção Dispatch do
projeto prevalece sobre uma estimativa de reversão barata. Neste projeto inclui
push, deploy, envio real externo, perda de dados e merge para a branch principal:
cada operação dessas é **sempre porta única**, mesmo se houver rollback de código.
Um merge local de tarefa na branch de integração é porta dupla; não equivale ao
merge para a principal. Quando faltar a regra do projeto, informe essa lacuna.

Decida por parte:

- **integra e segue**: porta dupla, raio delimitado e evidência suficiente.
- **integra e revisar**: porta dupla, mas raio amplo ou evidência incompleta;
  diga o teste ou revisão que falta antes de sair da máquina.
- **não integrar e perguntar**: porta única, escopo indefinido ou dúvida que
  impede delimitar o estrago; formule a pergunta concreta para o Vini.

Entregue o intervalo com os hashes e uma tabela:

| Parte / evidência | Porta | Raio / consequência | Decisão | Teste ou pergunta |
| --- | --- | --- | --- | --- |

Finalize com as pendências que condicionam a decisão do Vini. As decisões são
recomendações, não executam integração nem autorizam saída da máquina. Se salvar
um relatório, use `.watchdog/run/<data>/` ignorada pelo git no projeto.
