---
tags: [fastslr, algoritmo, scoring]
---

# 🔢 Algoritmo - Pontuação (Scoring)

Como um bloco transforma termos casados em um número (`final_score`). Implementação: `_compute_section_scores()` + uplift em `evaluate_block()` (`scoring.py`).

## Regra fundamental: níveis únicos por seção

> O score é baseado em **níveis únicos encontrados por seção**, **não** no número de matches.

Se três termos de nível 1 casam no título, o nível 1 conta **uma vez** naquela seção. Isso evita inflar o score com sinônimos repetidos.

## Fórmula

Para cada seção `s ∈ {title, abstract, manual_tags}`:

```
sec_raw(s)   = Σ  level_scores[lvl]      para cada nível único encontrado em s
sec_raw(s)   = min(sec_raw(s), MAX_SECTION_SCORE)        # cap por seção
sec_score(s) = sec_raw(s) × WEIGHTS[s]                   # peso da seção

raw_score    = Σ sec_score(s)
```

### Pontuação por nível (`PONTUACAO_NIVEIS`)
| Nível | Pontos (padrão) | Significado |
|---|---|---|
| 1 | 10 | Essencial / exato |
| 2 | 8 | Muito relevante |
| 3 | 6 | Relevante |
| 4 | 4 | Parcialmente relevante |
| 5 | 2 | Tangencial |

### Pesos por seção (`WEIGHTS`)
| Seção | Peso padrão |
|---|---|
| `title` | 2.0 |
| `abstract` | 1.0 |
| `manual_tags` | 1.5 |

### Cap (`MAX_SECTION_SCORE`)
Padrão **30**. Limita o quanto uma única seção contribui (antes do peso), evitando dominância.

## Uplift sem tags (`NO_TAGS_UPLIFT`)

```
SE artigo não tem manual_tags válidas E raw_score > 0:
    final_score = raw_score × NO_TAGS_UPLIFT   (padrão 1.17)
SENÃO:
    final_score = raw_score
```

Compensa artigos sem palavras-chave (que perdem a contribuição da seção `manual_tags`). "Sem tags" = vazio ou em `{nan, none, null}`. O flag `uplift_applied` é registrado.

## Exemplo

Artigo com `machine learning` (nível 1) no título e no resumo, sem tags:
```
title:    {1} → 10, ×2.0 = 20
abstract: {1} → 10, ×1.0 = 10
tags:     {}  → 0
raw_score = 30
final_score = 30 × 1.17 = 35.1   (uplift, pois sem tags)
```
Com `best_level=1` e `approval_threshold[1]=10` → `35.1 >= 10` → **APPROVED** no bloco.

## Thresholds (decisão do bloco)

São consultados em [[Algoritmo - Avaliação de Bloco|evaluate_block]] usando o `best_level`:
- `LIMITES_APROVADO` (`approval_thresholds`): score mínimo para `APPROVED`. `null` = nunca aprova por threshold.
- `LIMITES_SINALIZADO` (`flagging_thresholds`): score mínimo para `FLAGGED`.

> [!bug] Divergência de thresholds (Alta)
> `LIMITES_SINALIZADO` nível 4 vale **8** em `constants.py`, mas **7** em `presets.py` e em `default_config.json`. O resultado da triagem depende de qual caminho de configuração foi usado. Ver item #1 em [[Validação - Bugs e Riscos Conhecidos]].

---

Relacionado: [[Algoritmo - Avaliação de Bloco]] · [[Configuração - config e termos]] · [[Algoritmo - Decisão Final]] · [[Home]]
