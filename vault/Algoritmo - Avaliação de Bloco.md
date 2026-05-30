---
tags: [fastslr, algoritmo, bloco]
---

# 🧱 Algoritmo - Avaliação de Bloco

Cada **bloco de domínio** é uma dimensão temática da revisão (ex.: Contexto, Tecnologia). A função `evaluate_block()` (`scoring.py`) decide o status do artigo **naquele bloco**: `APPROVED`, `FLAGGED` ou `REJECTED`.

## Passos (em ordem)

```
1. find_positive_terms  → found_levels, matches por seção
2. find_anti_terms      → anti_exclude, anti_flag
3. _compute_section_scores → raw_score
4. uplift (se sem tags) → final_score
5. SE anti_exclude → REJECTED (curto-circuito)
6. best_level = min(found_levels)
7. filtros de ruído (se NOISE_PROFILE != relaxed)
8. threshold do best_level → APPROVED / FLAGGED / REJECTED
9. anti_flag rebaixa APPROVED → FLAGGED
```

## 1–2. Matching de termos

- **Positivos** (`pos`): contribuem para o score. Cada match registra o **nível** (1–5), a seção e o tipo (`exact` ou `proximity`). Ver [[Algoritmo - Padrões e Proximidade]].
- **Anti-exclusão** (`anti`): se **qualquer um** for encontrado → bloco `REJECTED` imediato, independente do score.
- **Anti-flag** (`flag`): se encontrado, rebaixa `APPROVED` → `FLAGGED` no fim.

O matching busca nas seções conforme `scope` do termo (`any` = todas; ou `title`/`abstract`/`manual_tags`). O texto é normalizado antes (ver [[Algoritmo - Normalização]]).

## 3–4. Score
Ver nota dedicada: [[Algoritmo - Pontuação (Scoring)]]. Resumo: soma das pontuações dos **níveis únicos por seção**, ponderada por seção, com cap por seção e **uplift de 1.17** se o artigo não tiver tags.

## 6. Melhor nível
`best_level = min(found_levels)` — o **menor** número é o **mais importante** (nível 1 = essencial). O threshold de aprovação/sinalização é escolhido por esse melhor nível.

## 7. Filtros de ruído

Só ativos quando `NOISE_PROFILE != "relaxed"` (ex.: `strict`). Rejeitam o bloco se:

| Filtro | Parâmetro | Rejeita se… |
|---|---|---|
| Poucos termos únicos | `min_unique_terms_for_approval` | nº de termos únicos < limite |
| Poucas seções | `min_sections_with_hits_for_approval` | nº de seções com hit < limite |
| Só termos fracos | `require_non_weak_term_for_approval` + `weak_levels` (padrão {5}) | todos os níveis encontrados são "fracos" |

## 8. Decisão por threshold

Com `best_level` definido:
```
final_score >= approval_threshold[best_level]  → APPROVED
final_score >= flagging_threshold[best_level]  → FLAGGED
senão                                          → REJECTED
```
Se `approval_threshold[best_level]` for `null` (caso do nível 5), o bloco **nunca aprova por threshold** — só pode chegar a `FLAGGED` (ou ser aprovado via [[Algoritmo - Políticas de Decisão|regra especial]] na decisão final). Sem nenhum positivo → `REJECTED` ("No positive terms found").

## 9. Anti-flag
Se há anti-flag e o status era `APPROVED`, vira `FLAGGED`. (Não afeta `REJECTED`/`FLAGGED`.)

> [!bug] Riscos relacionados a este fluxo
> - Wildcards (`data*`) não casam `data-driven` (hífen) — ver [[Algoritmo - Padrões e Proximidade]].
> - Score conta **níveis únicos**, não nº de matches — comportamento intencional, mas confunde. Ver [[Algoritmo - Pontuação (Scoring)]].
> - Detalhes em [[Validação - Bugs e Riscos Conhecidos]].

---

Relacionado: [[Algoritmo - Pontuação (Scoring)]] · [[Algoritmo - Padrões e Proximidade]] · [[Algoritmo - Decisão Final]] · [[Home]]
