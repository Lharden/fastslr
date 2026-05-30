---
tags: [fastslr, algoritmo, politicas]
---

# 🗳️ Algoritmo - Políticas de Decisão

`DECISION_POLICY` controla como os status dos blocos viram a decisão final em `make_final_decision()`. Três políticas.

## `special` (padrão, recomendada)

Lógica original "v11". Qualquer bloco rejeitado → rejeita o artigo; possui a **regra especial** de aprovar quando só 1 bloco está na fronteira e os outros são fortes. Detalhe completo em [[Algoritmo - Decisão Final]].

Parâmetros: `enable_special_approval_rule` (bool), `special_approval_threshold` (padrão 40).

## `strict`

Todos os blocos devem aprovar.

```
todos APPROVED              → APPROVED_FINAL
senão, se há FLAGGED        → FLAGGED_FINAL
senão                       → REJECTED_FINAL
```

Mais conservadora — maximiza precisão, pode aumentar falsos negativos.

## `k_of_n`

Pelo menos **K** blocos devem aprovar.

```
algum REJECTED                                   → REJECTED_FINAL
approved >= MIN_APPROVED_BLOCKS
   E flagged <= MAX_FLAGGED_BLOCKS_FOR_APPROVAL  → APPROVED_FINAL
senão, se há flagged ou approved                 → FLAGGED_FINAL
senão                                            → REJECTED_FINAL
```

Parâmetros: `MIN_APPROVED_BLOCKS` (`min_approved_blocks`, padrão 1), `MAX_FLAGGED_BLOCKS_FOR_APPROVAL` (`max_flagged_blocks_for_approval`, padrão 0).

## Como escolher

| Política | Quando usar |
|---|---|
| `special` | Maioria das RSLs — equilíbrio com proteção contra falso negativo de fronteira |
| `strict` | Quando todos os critérios são obrigatórios e indispensáveis |
| `k_of_n` | Quando relevância parcial (K de N dimensões) já basta para incluir |

## Comparação rápida (3 blocos)

| Status dos blocos | `special` | `strict` | `k_of_n` (K=2) |
|---|---|---|---|
| A,A,A | APPROVED | APPROVED | APPROVED |
| A,A,F | APPROVED* / FLAGGED | FLAGGED | APPROVED (se F≤max) |
| A,A,R | REJECTED | REJECTED | REJECTED |
| A,F,F | FLAGGED | FLAGGED | FLAGGED |

\* depende da regra especial (scores ≥ threshold).

---

Relacionado: [[Algoritmo - Decisão Final]] · [[Configuração - config e termos]] · [[Home]]
