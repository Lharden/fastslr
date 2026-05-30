---
tags: [fastslr, algoritmo, patterns, regex]
---

# 🧩 Algoritmo - Padrões e Proximidade

Cada termo textual é compilado em um `re.Pattern` por `patterns.py` (`compile_pattern`, `compile_proximity_pattern`, `precompile_patterns`).

## Tipos de termo

### Termo literal
Vira regex com *word boundaries*: `\btermo\b` (após `re.escape`).

### Wildcard (`*`)
`*` no termo → `\w*` no regex. Ex.: `optim*` → casa `optimize`, `optimization`, `optimal`.

> [!bug] Wildcard não cobre hífen/espaço
> `\w*` casa só caracteres de palavra. `data*` **não** casa `data-driven` nem `data driven`. E o `\b` final junto de `\w*` fica ambíguo. Item #5 em [[Validação - Bugs e Riscos Conhecidos]].

### Regex literal (`is_regex=1`)
O termo é usado como regex direto. Ex.: `ML|AI|DL` casa qualquer uma das siglas.

```csv
TECH;pos;ML|AI|DL;2;title;1;;     # is_regex=1
```

## Proximidade (termos compostos)

Termos contendo `and`, `&`, `or` ou `/` são automaticamente expandidos em **busca por proximidade bidirecional**. Ex.: `oil and gas` casa "oil … gas" **ou** "gas … oil" com até `MAX_GAP_BETWEEN_TERMS` palavras entre eles.

```csv
CTX;pos;oil and gas;1;any;0;;     # vira padrão de proximidade
```

Detecção: `detect_compound_terms` via `_COMPOUND_RE`. Padrão de gap: `(?:\s+<token>){0,max_gap}\s+`.

> [!bug] Semântica de gap ambígua
> O padrão sempre exige **pelo menos um** `\s+`, então `max_gap=0` ainda casa termos adjacentes. E só **um** separador por termo é detectado (`a/b and c` perde o `/`). Itens #5/#6 em [[Validação - Bugs e Riscos Conhecidos]].

## Pré-compilação

`precompile_patterns(block_config, engine, params)` compila todos os termos de um bloco de uma vez, separando-os em `positives`, `proximity_positives`, `anti_exclude`, `anti_flag`. É chamado pelo controller em `_prepare_config` para cada bloco e para o T0.

Cada termo compilado guarda: `pattern`, `level`, `scope`, `original_term`, `source_row`, `is_proximity`, `components`.

## Por que isso garante determinismo

Toda a correspondência é **regex compilado** sobre texto normalizado — sem similaridade aproximada, sem ordenação por relevância probabilística. A mesma entrada produz exatamente os mesmos matches. Ver [[Objetivo e Visão]].

---

Relacionado: [[Algoritmo - Normalização]] · [[Algoritmo - Avaliação de Bloco]] · [[Configuração - config e termos]] · [[Home]]
