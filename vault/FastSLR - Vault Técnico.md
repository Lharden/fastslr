---
projeto: FastSLR
tipo: moc
status: atual
atualizado: 2026-08-28
versao_documentada: 3.0.0
tags: [moc, fastslr]
aliases: [Vault Técnico FastSLR, MOC FastSLR Técnico]
---

# 🏠 FastSLR — Vault Técnico

> **FastSLR v3.0.0** — Triagem **determinística** universal para Revisões Sistemáticas de Literatura (RSL). Sem machine learning: mesma entrada + mesma configuração + mesma versão → **exatamente** a mesma saída.

Estas notas descrevem **arquitetura**, **algoritmo**, **objetivo** e **validação** do código. Elas vivem em `vault/` dentro do repositório e são versionadas junto com o código — o diff da nota acompanha o diff da função que ela descreve.

> [!info] Onde esta pasta vive
> No Obsidian principal (`mainframe`) ela aparece em `FastSLR/Vault Técnico`, que é uma **junction NTFS** apontando para `projects\fastslr\vault`. Não existe cópia: editar aqui ou lá é a mesma coisa, e o git do repositório registra a mudança.
> O contexto de projeto — decisões, plano, continuidade, registro PUCPR — fica ao lado, em [[00 Índice|FastSLR/00 Índice]].

---

## 🗺️ Mapa de Conteúdo

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

### 6. Validação
- [[Validação - Checklist]] — checklist mestre
- [[Validação - Estratégia de Testes]] — cobertura da suíte
- [[Validação - Auditoria Completa]] — os 46 findings, um a um *(histórico)*
- [[Validação - Correções Aplicadas]] — o que foi corrigido nas Fases 0–5 *(histórico)*
- [[Validação - Bugs e Riscos Conhecidos]] — registro original da revisão estática *(histórico)*

### 7. Apoio
- [[Glossário]] — termos do domínio e do código

---

## 🚦 Estado do código

| Item | Estado |
|---|---|
| Motor de triagem (`core/`) | ✅ completo e testado |
| CLI + TUI (`app/`) | ✅ funcionais |
| Reprodutibilidade (`protocol.json` + SHA-256) | ✅ |
| Findings da auditoria completa | ✅ 46 confirmados, 46 corrigidos com TDD (Fases 0–5) |
| `adapters.py` | 🗑️ removido — era dead code |
| Distribuição | ✅ `pip install fastslr` (PyPI) |

> [!warning] Contagens de teste variam entre notas
> As notas de validação registram `218 testes` porque essa era a suíte no fim das Fases 0–5. A suíte cresceu depois. Números de auditoria são **carimbos de data**, não estado atual — rode os gates para saber o número de hoje:
> ```powershell
> python -m pytest -q
> ```

---

## 🔎 Índice automático (Dataview)

```dataview
TABLE WITHOUT ID
  file.link AS "Nota",
  tipo AS "Tipo",
  status AS "Estado"
FROM "FastSLR/Vault Técnico"
WHERE tipo != "moc"
SORT tipo ASC, file.name ASC
```

```dataview
LIST
FROM "FastSLR/Vault Técnico"
WHERE status = "historico"
SORT file.name ASC
```

---

> [!tip] Como navegar
> Use o **Graph View** filtrando por `path:"FastSLR"`. Trilha de leitura: [[Objetivo e Visão]] → [[Arquitetura - Visão Geral]] → [[Algoritmo - Pipeline de Triagem]] → [[Reprodutibilidade e Pacote Acadêmico]].
