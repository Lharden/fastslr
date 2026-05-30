---
tags: [fastslr, algoritmo, decisao]
---

# ⚖️ Algoritmo - Decisão Final

`make_final_decision()` (`scoring.py`) combina os status dos blocos + T0 em uma decisão: `APPROVED_FINAL`, `FLAGGED_FINAL` ou `REJECTED_FINAL`.

A lógica depende da [[Algoritmo - Políticas de Decisão|política de decisão]] (`special` por padrão). Abaixo, a política `special` (a recomendada e padrão), passo a passo.

## Política `special` (ordem de avaliação)

```
0. T0 == REJECTED                         → REJECTED_FINAL   (sobrepõe tudo)
1. algum bloco REJECTED                   → REJECTED_FINAL
2. T0 == FLAGGED                          → FLAGGED_FINAL
3. algum bloco com anti_flag              → FLAGGED_FINAL
4. REGRA ESPECIAL (ver abaixo)            → APPROVED_FINAL   (se aplicável)
5. algum bloco FLAGGED por score          → FLAGGED_FINAL
6. todos os blocos APPROVED               → APPROVED_FINAL
   (fallback)                             → FLAGGED_FINAL "Inconclusive"
```

A ordem importa: uma rejeição em qualquer bloco vence sobre tudo (exceto que T0 REJECTED é checado antes). Anti-flag (passos 2–3) é checado **antes** da regra especial, então um artigo com anti-flag nunca é aprovado pela regra especial.

## A "regra especial" (passo 4)

> Se **exatamente 1** bloco está `FLAGGED` **por score** (não por anti-flag) e **todos os demais** estão `APPROVED` com `final_score >= SPECIAL_APPROVAL_THRESHOLD` (padrão 40), o artigo é **APROVADO**.

Objetivo: evitar falsos negativos quando um único bloco está na fronteira mas os outros são fortemente relevantes. Controlada por `enable_special_approval_rule` e `special_approval_threshold`.

## Saída por artigo

| Coluna | Conteúdo |
|---|---|
| `Final_Decision` | `APPROVED_FINAL` / `FLAGGED_FINAL` / `REJECTED_FINAL` |
| `Decision_Reason` | Explicação textual da decisão (auditável) |
| `Status_<BLOCO>` | Status individual de cada bloco |
| `Status_T0` etc. | Resultado do T0 (se configurado) |

## Interpretação

| Resultado | Ação recomendada |
|---|---|
| `APPROVED_FINAL` | Incluir na revisão |
| `FLAGGED_FINAL` | **Revisão manual** necessária (fronteira) |
| `REJECTED_FINAL` | Excluir |

---

Relacionado: [[Algoritmo - Políticas de Decisão]] · [[Algoritmo - Avaliação de Bloco]] · [[Algoritmo - Pré-triagem T0]] · [[Home]]
