---
tags: [moc, fastslr]
aliases: [Início, Index, MOC]
---

# 🏠 FastSLR — Vault do Projeto

> **FastSLR v3.0.0** — Triagem **determinística** universal para Revisões Sistemáticas de Literatura (RSL). Sem machine learning: mesma entrada + mesma configuração → **exatamente** a mesma saída.

Este vault documenta **arquitetura**, **algoritmo**, **objetivo** e o **checklist de validação** do projeto. Abra esta pasta (`vault/`) diretamente como um *vault* no Obsidian.

---

## 🗺️ Mapa de Conteúdo (MOC)

### 1. Visão
- [[Objetivo e Visão]] — para que serve, princípios e público-alvo

### 2. Arquitetura
- [[Arquitetura - Visão Geral]] — camadas e dependências
- [[Arquitetura - Camada Core]] — o motor de triagem
- [[Arquitetura - Camada App e Controller]] — CLI, TUI, i18n e a fachada
- [[Fluxo de Dados]] — do CSV de entrada ao pacote acadêmico

### 3. Algoritmo
- [[Algoritmo - Pipeline de Triagem]] — visão de ponta a ponta
- [[Algoritmo - Pré-triagem T0]] — filtro global
- [[Algoritmo - Avaliação de Bloco]] — positivos, anti-termos, ruído
- [[Algoritmo - Pontuação (Scoring)]] — score por seção, uplift, cap
- [[Algoritmo - Normalização]] — abreviações, variantes, símbolos
- [[Algoritmo - Padrões e Proximidade]] — wildcards, regex, termos compostos
- [[Algoritmo - Decisão Final]] — combinação de blocos
- [[Algoritmo - Políticas de Decisão]] — special / strict / k_of_n

### 4. Configuração
- [[Configuração - config e termos]] — config.json, terms.csv, presets

### 5. Reprodutibilidade
- [[Reprodutibilidade e Pacote Acadêmico]] — hashes, protocol.json, ZIP

### 6. Validação ⚠️
- [[Validação - Checklist]] — checklist mestre de validação (incl. bugs)
- [[Validação - Bugs e Riscos Conhecidos]] — registro detalhado de findings
- [[Validação - Estratégia de Testes]] — cobertura de testes existente

### 7. Apoio
- [[Glossário]] — termos do domínio e do código

---

## 🚦 Estado atual

- ✅ Motor de triagem completo e testado (`core/`)
- ✅ CLI + TUI funcionais (`app/`)
- ✅ Reprodutibilidade via `protocol.json` + SHA-256
- ⚠️ **~15 suspeitas de bug/lógica** catalogadas — ver [[Validação - Bugs e Riscos Conhecidos]]
- 🎯 Prioridade: corrigir itens de **severidade Alta** antes de o usuário final encontrá-los

> [!tip] Como navegar
> Use o **Graph View** do Obsidian para ver as conexões. Comece por [[Objetivo e Visão]] → [[Arquitetura - Visão Geral]] → [[Algoritmo - Pipeline de Triagem]].
