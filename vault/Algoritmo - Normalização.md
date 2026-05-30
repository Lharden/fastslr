---
tags: [fastslr, algoritmo, normalizacao]
---

# 🔤 Algoritmo - Normalização

Antes de qualquer *matching*, o texto do artigo (e os termos) passa pelo `NormalizationEngine` (`normalization.py`). Isso unifica variações para que um único termo configurado capture múltiplas formas.

## Quando ocorre

Em `_normalize_sections()` (`scoring.py`): cada seção é normalizada com o engine (se houver) ou, no mínimo, *lowercased* e com espaços colapsados (`re.sub(r"\s+", " ", text.lower().strip())`).

## Tipos de regra (coluna `normalization_type` no terms.csv)

| Tipo | Exemplo | Efeito |
|---|---|---|
| `abbreviation` | `AI` → `artificial intelligence` | Expande sigla para a forma completa |
| `compound_variant` | `supply-chain` → `supply chain` | Unifica variantes hifenizadas/juntas |
| `symbol_replacement` | símbolo → substituto | Normaliza símbolos |

```csv
TECH;pos;AI;1;any;0;abbreviation;artificial intelligence
CTX;pos;supply-chain;2;any;0;compound_variant;supply chain
```

## Ordem de aplicação

1. Abreviações (com `re.IGNORECASE`)
2. Substituição de símbolos
3. Variantes compostas
4. *lowercase* + colapso de espaços

> [!bug] A ordem é frágil
> Como a expansão de abreviação roda **antes** do *lowercase*, e a substituição de símbolos vem entre as etapas, a interação entre regras é dependente de ordem e **não documentada**. Texto e termo podem normalizar de formas sutilmente diferentes → **mismatch silencioso**. Item #4 em [[Validação - Bugs e Riscos Conhecidos]].

## Heurística de símbolos (risco)

Para `symbol_replacement`, o engine decide entre `\b...\b` (se o símbolo contém letra) e `str.replace` (caso contrário).

> [!bug] `c++` quebra
> Um símbolo como `c++` contém letra, então vira `\bc\+\+\b`. Mas `\b` depois de `+` não casa onde se espera (não há *word boundary* entre `+` e espaço) → a substituição é **silenciosamente ignorada**. Item #4 em [[Validação - Bugs e Riscos Conhecidos]].

## Cache

O engine mantém um cache **LRU manual** (dict + lista de ordem). É O(n) por acesso (usa `list.remove`) e não é thread-safe — irrelevante em execução single-thread, mas vale anotar.

---

Relacionado: [[Algoritmo - Padrões e Proximidade]] · [[Algoritmo - Avaliação de Bloco]] · [[Configuração - config e termos]] · [[Home]]
