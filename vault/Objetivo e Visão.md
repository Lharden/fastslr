---
tags: [fastslr, visao, objetivo]
---

# 🎯 Objetivo e Visão

## O problema

A fase de **screening (triagem)** de uma Revisão Sistemática de Literatura exige avaliar manualmente centenas ou milhares de artigos contra critérios de inclusão/exclusão. É lento, cansativo e — pior para uma RSL — **difícil de reproduzir e auditar**. Dois revisores podem decidir de forma diferente, e o processo raramente é documentável com rigor metodológico.

## A proposta do FastSLR

FastSLR automatiza a triagem com um pipeline **100% mecânico e determinístico**:

> **Mesma entrada + mesma configuração + mesma versão → exatamente a mesma saída.**

Nenhum componente estocástico: sem machine learning, sem *fuzzy matching*, sem embeddings. Todo o *matching* é feito por **regex compilado** sobre níveis de relevância configuráveis. Isso garante três propriedades que importam para publicação acadêmica:

| Propriedade | Como é garantida |
|---|---|
| **Reprodutível** | Algoritmo determinístico + hashes SHA-256 da entrada/config (ver [[Reprodutibilidade e Pacote Acadêmico]]) |
| **Auditável** | Cada decisão tem `Decision_Reason`; termos casados ficam destacados (`***termo***`) |
| **Transparente** | Toda a lógica é configuração legível (`config.json` + `terms.csv`), não um modelo opaco |

## Princípios de design

1. **Determinismo acima de tudo** — qualquer escolha de design que introduza não-determinismo é rejeitada (ver [[Arquitetura - Visão Geral]]).
2. **Motor estável, shell flexível** — o motor de triagem (`core/`) é tratado como código de risco baixo e testado; a inovação fica na camada de aplicação (`app/`). Ver decisão **D3** em [[Arquitetura - Visão Geral]].
3. **Universalidade** — não é amarrado a um domínio. O usuário define **blocos temáticos** arbitrários (ex.: Contexto, Tecnologia, Escopo) e **níveis de relevância** (1 a 5). Serve para RSL de qualquer área.
4. **Saída de dados em inglês, interface traduzível** — nomes de colunas, chaves JSON e valores de decisão (`APPROVED_FINAL`) **nunca** são traduzidos, para que o resultado seja idêntico entre locales. Só a interface tem i18n (en/pt_BR/es). Ver decisão **D4**.

## Público-alvo

Pesquisadores de **qualquer área**, em sua maioria **não-programadores**. Daí a existência de:
- uma **TUI** guiada (`fastslr tui`),
- o comando **`doctor`** (verifica setup antes de rodar),
- presets de configuração (`binary`/`simple`/`standard`),
- scaffolding de projeto (`fastslr new-project`).

## Conceitos centrais

- **Bloco de domínio** — uma dimensão temática da revisão. Um artigo precisa passar nos blocos relevantes. Ver [[Algoritmo - Avaliação de Bloco]].
- **Nível de importância (1–5)** — 1 = essencial, 5 = tangencial. Cada nível tem uma pontuação. Ver [[Algoritmo - Pontuação (Scoring)]].
- **T0** — pré-filtro global aplicado antes dos blocos. Ver [[Algoritmo - Pré-triagem T0]].
- **Decisão final** — `APPROVED_FINAL`, `FLAGGED_FINAL`, `REJECTED_FINAL`. Ver [[Algoritmo - Decisão Final]].

---

Relacionado: [[Home]] · [[Arquitetura - Visão Geral]] · [[Glossário]]
