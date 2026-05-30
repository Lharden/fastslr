---
tags: [fastslr, validacao, bugs, riscos]
---

# 🐞 Validação - Bugs e Riscos Conhecidos

Registro dos **problemas de lógica e robustez** identificados na auditoria do código (revisão estática de `core/` e `app/`). Status inicial: **🔴 ABERTO** para todos — corrigir antes que o usuário final os encontre.

> Legenda severidade: 🔥 **Alta** (pode produzir resultado de triagem incorreto / inconsistente) · 🟧 **Média** (matching/UX errado em casos comuns) · 🟨 **Baixa** (edge case / cosmético).

---

## 🔥 Severidade Alta

### #1 — Thresholds de flag divergentes (fonte de verdade tripla)
- **Onde**: `core/constants.py` (`DEFAULT_FLAGGING_THRESHOLDS` nível 4 = **8**) vs `core/presets.py` (preset `standard` nível 4 = **7**) vs `core/default_config.json` (nível 4 = **7**).
- **Risco**: a decisão de bloco depende de **qual caminho de config** foi carregado → mesma RSL pode dar resultados diferentes. Fere o princípio de reprodutibilidade.
- **Fix sugerido**: definir uma **única** fonte de verdade (provavelmente `constants.py`) e fazer presets/JSON derivarem dela; adicionar teste que garante igualdade entre as três.
- **Relacionado**: [[Algoritmo - Pontuação (Scoring)]], [[Configuração - config e termos]].

### #2 — Parsing de highlights quebra com aspas no termo
- **Onde**: `core/coverage.py` (`_HIGHLIGHT_TERM_RE = r'term="([^"]+)"...'`) consome o formato de `pack_highlights` em `core/io.py`.
- **Risco**: se um termo contém `"` (possível em regex), `[^"]+` trunca → contagem de cobertura corrompida.
- **Fix sugerido**: trocar a serialização de highlights por um formato com escape robusto (ou estrutura, não string regex-parsed). Confirmar com teste de termo contendo aspas.

### #3 — Falso-positivo de "dead term"
- **Onde**: `core/coverage.py` — compara `original_term` (config) contra `m.term` (extraído do highlight).
- **Risco**: se o highlight emite o **termo normalizado** em vez do original, termos que casaram aparecem como "dead" (0 matches) → o usuário remove termos válidos na calibração.
- **Fix sugerido**: garantir que cobertura compare a **mesma chave** que `pack_highlights` emite (alinhar `original_term` ↔ `m.term`). Teste: termo com normalização que casa deve contar como vivo.

---

## 🟧 Severidade Média

### #4 — Normalização: heurística de símbolo + ordem frágil
- **Onde**: `core/normalization.py`.
- **Risco**: (a) símbolo com letra (`c++`) vira `\bc\+\+\b` cujo `\b` final não casa → substituição silenciosamente ignorada; (b) ordem de aplicação (abreviação antes do lowercase, símbolos no meio) pode normalizar texto e termo de formas diferentes → **mismatch silencioso**.
- **Fix sugerido**: revisar geração de regex de símbolo (não usar `\b` cego) e documentar/fixar a ordem; testes para `c++`, `c#`, símbolos puros.
- **Relacionado**: [[Algoritmo - Normalização]].

### #5 — Wildcard `*` não cobre hífen/espaço
- **Onde**: `core/patterns.py` (`*` → `\w*`).
- **Risco**: `data*` não casa `data-driven`/`data driven`; usuário espera que case. `\b` junto de `\w*` fica ambíguo.
- **Fix sugerido**: avaliar `[\w-]*` ou tratar hífen/espaço; revisar boundary. Testes de wildcard com hífen.
- **Relacionado**: [[Algoritmo - Padrões e Proximidade]].

### #6 — Semântica de proximidade/gap ambígua
- **Onde**: `core/patterns.py` (`compile_proximity_pattern`).
- **Risco**: o padrão sempre exige ≥1 `\s+`, então `max_gap=0` ainda casa adjacentes; só **um** separador por termo é detectado (`a/b and c` perde `/`); `\b` falha quando termo termina em não-word-char após escape.
- **Fix sugerido**: definir semântica explícita de gap e testá-la; detectar múltiplos separadores se necessário.

### #7 — Default de export `csv` contraditório
- **Onde**: `core/io.py` (`get_export_opts` default `csv=True`) vs `core/default_config.json` (`csv:false`).
- **Risco**: sem seção `output` explícita, CSV é exportado contra a intenção do default JSON.
- **Fix sugerido**: alinhar o default de código ao JSON (`csv=False`).

### #8 — Detecção de separador de CSV por contagem de colunas
- **Onde**: `core/io.py` (escolhe separador que gera mais colunas).
- **Risco**: CSV com `;` legítimo mas headers atípicos pode perder para `,` (split espúrio) → colunas erradas silenciosamente.
- **Fix sugerido**: priorizar separador por *header score* conhecido; permitir override explícito.

### #9 — `run` não valida `--terms` ausente
- **Onde**: `app/cli.py` (valida `input` e `config`, não `terms`).
- **Risco**: arquivo de termos inexistente estoura traceback cru em vez da mensagem i18n amigável (o `doctor` trata, o `run` não).
- **Fix sugerido**: validar existência de `--terms` no `run`, como no `doctor`.

### #10 — `diff` não marca "MISSING" corretamente
- **Onde**: `app/controller.py` (`diff_results`, merge `outer`).
- **Risco**: para IDs ausentes em um lado, o valor é `NaN` (não a string `"MISSING"`); `row.get("Final_Decision_a","MISSING")` não dispara o default → relatório de diff impreciso.
- **Fix sugerido**: usar `fillna("MISSING")` após o merge; testar IDs presentes só em um lado.

### #11 — `diff` com fallback de coluna de ID arriscado
- **Onde**: `app/controller.py` (usa `df_a.columns[0]` se não achar coluna de ID conhecida; `merge(on=id_col)` quebra se `df_b` não tiver).
- **Fix sugerido**: validar que ambas têm a coluna antes do merge, com erro amigável.

---

## 🟨 Severidade Baixa

### #12 — `new_project` sobrescreve projeto existente
- **Onde**: `app/controller.py` (`mkdir(exist_ok=True)` + `write_text` sem confirmar).
- **Risco**: perda de `config.json`/`terms` de projeto pré-existente.
- **Fix sugerido**: detectar pasta não-vazia e exigir `--force`/confirmação.

### #13 — `_(key)` engole erro de formatação
- **Onde**: `app/i18n/__init__.py` (`except (KeyError, IndexError): pass`).
- **Risco**: tradução com placeholder errado mostra o template sem substituir, sem erro visível.
- **Fix sugerido**: logar warning quando o `.format` falhar.

### #14 — Highlight força UPPERCASE e pode corromper `***`
- **Onde**: `core/io.py` (`result[start:end].upper()`; aninhamento de `***`).
- **Risco**: perde case original do trecho casado; texto com `***` pré-existente corrompe marcador.
- **Fix sugerido**: reavaliar a necessidade de `.upper()`; escapar marcadores.

### #15 — Outros menores
- `row_num = int(idx)+2` assume índice 0-based sequencial (`config.py`, `normalization.py`) → número de linha reportado pode ficar errado.
- `pd.isna(str_value)` após `str(...)` é checagem morta (sempre `False`).
- Broad-term usa `>` estrito contra `total*0.8` (termo em exatos 80% não é reportado).
- Match de subset por `astype(str)` falha com float-formatting de IDs (`"1.0"` vs `"1"`).
- `adapters.detect_format` com threshold `>=2` e colunas genéricas pode dar falso-positivo de formato.
- Cache LRU manual em `normalization.py` é O(n) e não thread-safe (irrelevante single-thread).
- `browse_terms` muta lista interna do config ao fazer `append("T0")` (verificar se `get_domain_blocks` copia).

---

## Findings já resolvidos (stress test 2026-03-17)

Do `docs/stress-test-log.md` — **já corrigidos**, mantidos como referência:
- ✅ CSV vazio (só headers) lançava `ValueError` → fix em `io.py` (`len(df.columns) >= 3`).
- ✅ `profile load` inexistente → mensagem traduzida em `cli.py`.
- ✅ `diff` sem coluna `Final_Decision` → validação antes do merge.
- ✅ Thresholds negativos → `validate_config()` emite warning.

---

Ver o checklist acionável em [[Validação - Checklist]]. Relacionado: [[Validação - Estratégia de Testes]] · [[Home]].
