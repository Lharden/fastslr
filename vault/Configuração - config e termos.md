---
tags: [fastslr, configuracao]
---

# ⚙️ Configuração - config e termos

Dois arquivos controlam toda a triagem: `config.json` (parâmetros) e `terms.csv`/`terms.xlsx` (termos por bloco).

## `config.json`

```json
{
  "global": {
    "DECISION_POLICY": "special",
    "PONTUACAO_NIVEIS": {"1": 10, "2": 8, "3": 6, "4": 4, "5": 2},
    "LIMITES_APROVADO": {"1": 10, "2": 12, "3": 18, "4": 22, "5": null},
    "LIMITES_SINALIZADO": {"1": 6, "2": 6, "3": 6, "4": 7, "5": 12},
    "WEIGHTS": {"title": 2.0, "abstract": 1.0, "manual_tags": 1.5},
    "NO_TAGS_UPLIFT": 1.17,
    "MAX_SECTION_SCORE": 30,
    "FAIL_FAST_GLOBAL": true,
    "ENABLE_PROXIMITY_DETECTION": true,
    "NOISE_PROFILE": "relaxed",
    "ERROR_POLICY": "flag"
  },
  "fields": { "id": "key", "title": "title", "abstract": "abstract", "manual_tags": "manual_tags" },
  "output": { "csv": false, "xlsx": true, "academic_package": true }
}
```

### Parâmetros globais
| Parâmetro | Padrão | Papel |
|---|---|---|
| `DECISION_POLICY` | `special` | [[Algoritmo - Políticas de Decisão\|Política]] de decisão |
| `PONTUACAO_NIVEIS` | {1:10…5:2} | Pontos por nível ([[Algoritmo - Pontuação (Scoring)\|scoring]]) |
| `LIMITES_APROVADO` | {1:10…5:null} | Threshold de aprovação por nível |
| `LIMITES_SINALIZADO` | {1:6…5:12} | Threshold de sinalização por nível |
| `WEIGHTS` | title 2 / abs 1 / tags 1.5 | Pesos por seção |
| `NO_TAGS_UPLIFT` | 1.17 | Multiplicador sem tags |
| `MAX_SECTION_SCORE` | 30 | Cap por seção |
| `FAIL_FAST_GLOBAL` | true | Pula blocos após rejeição |
| `ENABLE_PROXIMITY_DETECTION` | true | Detecta termos compostos |
| `NOISE_PROFILE` | relaxed | `relaxed`/`strict` (ativa filtros de ruído) |
| `ERROR_POLICY` | flag | `flag`/`fail` |

`fields` mapeia colunas do CSV de entrada (com auto-detecção via [[Fluxo de Dados|adapters]]). `output` controla os formatos gerados.

> [!warning] Chaves em PT-BR
> Os nomes de parâmetro são em português (`PONTUACAO_NIVEIS`, `LIMITES_APROVADO`…). `load_global_params` os traduz para o `GlobalParams` interno (chaves de nível viram `int`).

## `terms.csv` (separador `;`)

```
block;kind;term;level;section_scope;is_regex;normalization_type;normalization_target
```

| Coluna | Obrigatória | Valores |
|---|---|---|
| `block` | Sim | nome do bloco ou `GLOBAL` (→ [[Algoritmo - Pré-triagem T0\|T0]]) |
| `kind` | Sim | `pos` / `anti` / `flag` |
| `term` | Sim | texto livre |
| `level` | p/ `pos` | 1–5 |
| `section_scope` | Não | `any`/`title`/`abstract`/`manual_tags` |
| `is_regex` | Não | `0`/`1` |
| `normalization_type` | Não | `abbreviation`/`compound_variant`/`symbol_replacement` |
| `normalization_target` | Não | forma normalizada |

Tipos de termo: `pos` (contribui ao score), `anti` (rejeita o bloco), `flag` (rebaixa para FLAGGED). Ver [[Algoritmo - Avaliação de Bloco]]. Recursos: wildcards, regex, proximidade e normalização — ver [[Algoritmo - Padrões e Proximidade]] e [[Algoritmo - Normalização]].

`parse_terms_csv` valida cada linha (campos obrigatórios, nível, scope), **deduplica** e detecta **conflitos** (mesmo termo como `pos` e `anti`).

## Presets (`new-project -p`)

| Preset | Níveis | Uso |
|---|---|---|
| `binary` | 1 | triagem rápida (relevante ou não) |
| `simple` | 3 | projetos menores |
| `standard` | 5 | recomendado (granularidade fina) |

> [!bug] Fonte de verdade duplicada
> Os defaults de threshold vivem em `constants.py`, `presets.py` **e** `default_config.json`, e divergem no nível 4 (8 vs 7 vs 7). Unificar. Ver item #1 em [[Validação - Bugs e Riscos Conhecidos]].

---

Relacionado: [[Algoritmo - Pontuação (Scoring)]] · [[Algoritmo - Políticas de Decisão]] · [[Reprodutibilidade e Pacote Acadêmico]] · [[Home]]
