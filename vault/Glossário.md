---
tags: [fastslr, glossario]
---

# 📖 Glossário

## Domínio (RSL)

| Termo | Definição |
|---|---|
| **RSL / SLR** | Revisão Sistemática de Literatura. FastSLR automatiza a fase de *screening*. |
| **Screening / Triagem** | Avaliar artigos contra critérios de inclusão/exclusão. |
| **Bloco de domínio** | Dimensão temática da revisão (ex.: CTX, TECH). Ver [[Algoritmo - Avaliação de Bloco]]. |
| **Nível de importância** | 1 (essencial) a 5 (tangencial). Define a pontuação do termo. |
| **T0** | Pré-triagem global por anti-termos, antes dos blocos. Ver [[Algoritmo - Pré-triagem T0]]. |

## Tipos de termo

| Termo | Significado |
|---|---|
| **`pos`** | Positivo — contribui para o score. |
| **`anti`** | Anti-exclusão — rejeita o bloco imediatamente. |
| **`flag`** | Anti-sinalização — rebaixa `APPROVED` → `FLAGGED`. |
| **Proximidade** | Termo composto ("oil and gas") buscado bidirecionalmente com gap. |
| **Wildcard** | `*` → `\w*` no regex. |

## Status e decisões

| Termo | Significado |
|---|---|
| **APPROVED / FLAGGED / REJECTED** | Status de um bloco. |
| **NOT_EVALUATED** | Bloco não avaliado (fail-fast ou T0 rejeitou). |
| **PASSED** | T0 sem anti-termos. |
| **APPROVED_FINAL / FLAGGED_FINAL / REJECTED_FINAL** | [[Algoritmo - Decisão Final\|Decisão final]] do artigo. |

## Parâmetros (config ↔ código)

| Config (PT-BR) | `GlobalParams` | Papel |
|---|---|---|
| `PONTUACAO_NIVEIS` | `level_scores` | pontos por nível |
| `LIMITES_APROVADO` | `approval_thresholds` | threshold de aprovação |
| `LIMITES_SINALIZADO` | `flagging_thresholds` | threshold de sinalização |
| `WEIGHTS` | `section_weights` | pesos por seção |
| `NO_TAGS_UPLIFT` | `no_tags_uplift` | multiplicador sem tags |
| `MAX_SECTION_SCORE` | `max_section_score` | cap por seção |
| `FAIL_FAST_GLOBAL` | `fail_fast_enabled` | pula blocos pós-rejeição |
| `DECISION_POLICY` | `decision_policy` | special/strict/k_of_n |
| `NOISE_PROFILE` | `noise_profile` | ativa filtros de ruído |
| `ERROR_POLICY` | `error_policy` | flag/fail |

## Estruturas de dados (`models.py`)

| Dataclass | Papel |
|---|---|
| `TermMatch` | Um match positivo (termo, nível, seção, tipo). |
| `AntiHit` | Um match de anti-termo. |
| `BlockEvaluation` | Resultado de um bloco (status, scores, matches, anti-hits). |
| `T0Evaluation` | Resultado do T0. |
| `GlobalParams` | Contrato de parâmetros do motor. |

## Componentes

| Termo | Onde |
|---|---|
| **Engine** | `core/engine.py` — orquestra o pipeline. |
| **Controller** | `app/controller.py` — fachada app↔core. |
| **NormalizationEngine** | `core/normalization.py`. |

---

Relacionado: [[Home]] · [[Objetivo e Visão]] · [[Algoritmo - Pipeline de Triagem]]
