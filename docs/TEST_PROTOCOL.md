# FastSLR — Protocolo de Testes do Sistema

> **Versao**: 1.0  •  **Data**: 2026-04-24  •  **Branch base**: `master @ 7a18258`  •  **Alvo**: FastSLR v3.0.0
>
> Este protocolo cobre quatro frentes: (1) **arquitetura-conceitual**, (2) **bugs e falhas silenciosas confirmados**, (3) **logica/feature gaps**, e (4) **estrategia de testes automatizados**. Para o roteiro de **testes manuais de UX**, ver [`docs/MANUAL_UX_TEST_GUIDE.md`](MANUAL_UX_TEST_GUIDE.md).

---

## Sumario

1. [Visao geral do sistema sob teste](#1-visao-geral-do-sistema-sob-teste)
2. [Arquitetura conceitual — premissas a validar](#2-arquitetura-conceitual--premissas-a-validar)
3. [Catalogo de achados (bugs, falhas silenciosas, gaps)](#3-catalogo-de-achados-bugs-falhas-silenciosas-gaps)
4. [Plano de testes por modulo](#4-plano-de-testes-por-modulo)
5. [Plano de testes de integracao](#5-plano-de-testes-de-integracao)
6. [Plano de testes end-to-end (CLI)](#6-plano-de-testes-end-to-end-cli)
7. [Plano de testes de regressao](#7-plano-de-testes-de-regressao)
8. [Estrategia de cobertura e ferramentas](#8-estrategia-de-cobertura-e-ferramentas)
9. [Matriz de prioridades](#9-matriz-de-prioridades)

---

## 1. Visao geral do sistema sob teste

| Camada | Modulos | Responsabilidade |
|---|---|---|
| **Interface** | `app/cli.py` (Typer, ~513 LOC), `app/tui.py` (Textual, ~1017 LOC, 10 telas) | Entrada do usuario, parsing de flags, navegacao TUI |
| **Orquestracao** | `app/controller.py` (~719 LOC) | Fachada unica entre UI e nucleo, validacoes pre-execucao, callbacks de progresso |
| **Nucleo** | `core/engine.py` (~366 LOC), `core/scoring.py` (~480 LOC) | Pipeline de triagem (T0 → blocos → decisao final), regras de scoring |
| **Suporte** | `core/normalization.py`, `core/patterns.py`, `core/coverage.py` | Normalizacao de texto, compilacao de patterns, analise de cobertura de termos |
| **I/O & Config** | `core/io.py` (~670 LOC), `core/config.py` (~476 LOC) | Carga/escrita CSV/XLSX/JSON, hashing, parse de `terms.csv`, JSON Schema |
| **i18n** | `i18n/locales/{en,pt_BR,es}.json` | Traducoes (~53 chaves base) |

**Estado atual de testes**: 67 testes em 8 arquivos (~1239 linhas). Cobre core (scoring, patterns, normalization, regressions), I/O parcial. **Nao cobre** CLI, TUI, i18n, profiles, edge cases de encoding.

---

## 2. Arquitetura conceitual — premissas a validar

Estas sao as premissas implicitas no design. Cada uma vira um teste ou um experimento.

### A1 — Determinismo absoluto
> "Mesma entrada + mesma config + mesma terms.csv → mesma saida bit-a-bit."

- **Risco**: `run_timestamp` em `engine.py:296,325` injeta tempo no row. Hashes de protocolo podem mudar.
- **Teste**: rodar `fastslr run` duas vezes em sequencia; comparar sha256 dos arquivos de saida **exceto** colunas de timestamp.
- **Variante**: pedir o mesmo run em duas maquinas (Windows vs WSL). Diferenca de quebra de linha (LF vs CRLF) deve ser tratada (vimos warnings `LF will be replaced by CRLF`).

### A2 — Isolamento de UI ↔ core
> "Nucleo nao conhece CLI nem TUI. Toda interacao passa pelo `controller`."

- **Teste estatico**: `grep -r "from fastslr.app" src/fastslr/core/` deve retornar zero matches. `grep -r "import typer\|import rich\|import textual" src/fastslr/core/` idem.
- **Teste dinamico**: importar `fastslr.core.engine` em script puro Python (sem Typer, sem Textual instalados) — deve funcionar.

### A3 — Configuracao validavel
> "Toda config invalida e detectada antes do processamento (fail-fast)."

- **Teste**: alimentar `config.json` com `DECISION_POLICY: "magic_unicorn"` (string invalida) → deve falhar **antes** de iterar artigos, com mensagem clara.
- **Teste**: `LIMITES_APROVADO: {"1": -5}` (negativo absurdo) → comportamento esperado?

### A4 — Reprodutibilidade auditavel
> "`protocol.json` v2.1 captura todos os hashes (config, input, terms) com SHA-256 truncado."

- **Teste**: alterar 1 byte de `terms.csv` (espaco trailing em uma celula) → hash do `terms` muda, hashes de `config` e `input` permanecem iguais.
- **Teste**: alterar `_compiled_pattern` em memoria → hash de config **nao deve mudar** (io.py:55-77 ignora pattern compilado).

### A5 — Internacionalizacao consistente
> "Todas as 53 chaves estao traduzidas em en/pt_BR/es; chave ausente cai para `en` ou para a propria chave."

- **Teste**: `diff` de chaves entre os 3 locales — deve ser vazio.
- **Teste**: setar `FASTSLR_LANG=zz` (locale inexistente) → fallback para `en`, sem crash.

### A6 — Politica de erros honrada
> "`ERROR_POLICY: 'fail'` aborta no primeiro erro; `'flag'` continua e marca o artigo problematico."

- **Teste**: injetar 1 artigo com `title=None` (forcado) em corpus de 100 → com `'fail'`, deve abortar; com `'flag'`, deve produzir `ID=ERR_X` com `Final_Decision=FLAGGED_FINAL`.
- **Teste de limite**: `MAX_ERROR_RATE=0.01` em corpus de 100 com 5 erros → deve abortar com mensagem `"5/100 (5.0%) > 1.0%"` mesmo com policy=`'flag'`.

---

## 3. Catalogo de achados (bugs, falhas silenciosas, gaps)

> Achados **confirmados** via leitura direta dos arquivos. Cada um tem severidade (S1 critico, S2 alto, S3 medio, S4 baixo) e uma proposta de teste regressivo.

### F-01 [S2] — Erros de processamento descem para `logger.debug` (silenciamento em producao)
- **Arquivo**: `src/fastslr/core/engine.py:313-317`
- **Trecho confirmado**:
  ```python
  except Exception as exc:
      error_count += 1
      if error_policy == "fail":
          raise
      logger.debug("Error processing article %d: %s", count, exc)
  ```
- **Problema**: em logging level `INFO` (padrao), erros nao aparecem. Usuario ve `Final_Decision=FLAGGED_FINAL` com `Decision_Reason="Processing error: ..."` mas nao ve o stack trace nem o `count` afetado.
- **Risco**: se 30% do corpus falha por bug interno (ex.: regex invalida em um termo especifico), o usuario nao percebe ate auditar manualmente.
- **Teste regressivo proposto** (`tests/test_engine.py`):
  - Forcar excecao em uma linha (ex.: monkeypatch em `evaluate_block` para lancar `ValueError` quando title contem string `"BOOM"`).
  - Rodar com `error_policy='flag'`, `caplog.at_level(logging.WARNING)`.
  - Asserir que **algum** registro de WARNING ou superior contem o texto do erro.
- **Fix sugerido**: trocar `logger.debug` por `logger.warning` (ou `logger.exception`).

### F-02 [S2] — `error_rate` zero quando corpus vazio mascara dataframe degenerado
- **Arquivo**: `src/fastslr/core/engine.py:339-345`
- **Trecho confirmado**:
  ```python
  stats["error_rate"] = error_count / total if total > 0 else 0
  if (error_policy == "flag" and total > 0 and ... and stats["error_rate"] > global_params.max_error_rate):
      raise RuntimeError(...)
  ```
- **Problema**: Corpus vazio (`total=0`) → `error_rate=0` → guarda `total > 0` evita o raise. **OK aqui**, mas o caller nao recebe sinal de que rodou em vazio.
- **Risco**: usuario aponta CSV errado (vazio depois de filtros), `fastslr run` sai com sucesso e `result_df` vazio. Saida tem so headers.
- **Teste regressivo proposto**:
  - Rodar `process_articles` com DataFrame vazio.
  - Asserir que `stats` contem chave nova `total_articles=0` E que controlador emite warning para o usuario.
- **Fix sugerido**: adicionar `if total == 0: logger.warning("Empty corpus")` ou erro explicito.

### F-03 [S2] — `manual_tags` "ausentes" detectadas via lista hardcoded
- **Arquivo**: `src/fastslr/core/scoring.py:213-217`
- **Trecho confirmado**:
  ```python
  has_tags = bool(
      manual_tags
      and manual_tags.strip()
      and manual_tags.strip().lower() not in {"nan", "none", "null"}
  )
  ```
- **Problema**: usuarios que exportam de Zotero/Mendeley podem ter `"---"`, `"N/A"`, `"sem tags"`, `"-"` como placeholder. Esses valores sao tratados como **tags reais** → `has_tags=True` → uplift **nao aplicado** → score artificialmente baixo.
- **Teste regressivo proposto**:
  - `pytest.parametrize` com `["---", "N/A", "n/a", "sem tags", "-", " - ", "tbd"]`.
  - Asserir que `has_tags=False` para todos esses.
- **Fix sugerido**: aceitar lista configuravel `EMPTY_TAG_MARKERS` em `default_config.json`, ou usar regex `^[\s\-_/\.\(]*(n[/\\]?a|none|null|nan|tbd|---+|sem\s+tags?)[\s\-_/\.\)]*$`.

### F-04 [S3] — Comparacao de float em threshold (`>=` em decimal)
- **Arquivo**: `src/fastslr/core/scoring.py:294,297`
- **Trecho confirmado**:
  ```python
  if approval_threshold is not None and final_score >= approval_threshold:
  ```
- **Problema**: `final_score` resulta de multiplicacoes (`raw_score * 1.17`) que produzem floats imprecisos (ex.: `10.0 * 1.17 = 11.700000000000001`). Compatibilidade entre reruns OK, mas thresholds **inteiros** vs scores **float** podem dar resultados surpreendentes em casos de borda.
- **Teste regressivo proposto** (property-based com `hypothesis`):
  - Gerar pares (raw_score, uplift) que produzam final_score exatamente `threshold ± 1e-10`.
  - Verificar comportamento documentado.
- **Fix sugerido**: arredondar para 2 casas decimais antes de comparar (consistente com `round(ev.raw_score, 2)` em engine.py:281), OU usar `math.isclose` com tolerancia explicita.

### F-05 [S3] — Anti-flag so age sobre `APPROVED`, nunca sobre `FLAGGED` ja existente
- **Arquivo**: `src/fastslr/core/scoring.py:310-312`
- **Trecho confirmado**:
  ```python
  if anti_flag and status == "APPROVED":
      status = "FLAGGED"
      reason = f"Downgraded to flagged: anti-flag term '{anti_flag[0].term}'"
  ```
- **Problema**: se status ja esta `FLAGGED` (por threshold), anti_flag e **silenciosamente perdido**. O motivo da flag fica como score-baseado, nao como anti-flag. Auditoria fica enganosa.
- **Teste regressivo proposto**:
  - Construir caso onde score cai entre flag/approval thresholds **e** anti_flag dispara.
  - Asserir que `Flags_BLOCK` no output contem o termo anti_flag e que `Decision_Reason` mencionar **ambos** os motivos (ou pelo menos o anti_flag).
- **Fix sugerido**: sempre concatenar motivo de anti_flag a reason, mesmo que status nao mude.

### F-06 [S3] — `norm_engine` para T0 herdada do **primeiro** dominio
- **Arquivo**: `src/fastslr/core/engine.py:233-237`
- **Trecho confirmado**:
  ```python
  norm_engine = (
      config.get(domain_blocks[0], {}).get("normalization_engine")
      if domain_blocks else None
  )
  ```
- **Problema**: T0 e global, mas pega normalizacao do primeiro bloco listado em `config.json`. Se o usuario reordena blocos, normalizacao do T0 muda silenciosamente.
- **Teste regressivo proposto**:
  - Criar config com `T0` + 2 blocos com `normalization_engine` diferentes.
  - Comparar saidas reordenando `domain_blocks`. Verificar se T0 produz match identico ou nao.
- **Fix sugerido**: T0 deve ter seu proprio `normalization_engine` no config, ou usar engine "neutra" (sem normalizacao customizada).

### F-07 [S3] — `try/except` silenciador em normalization e patterns
- **Arquivos**:
  - `src/fastslr/core/normalization.py:~176` (regras de expansao com `regex_target` ignoradas em erro)
  - `src/fastslr/core/scoring.py:~99` (find_positive_terms com regex invalido — checar)
- **Problema**: regex malformado em `terms.csv` na coluna `normalization_target` ou `is_regex` e silenciosamente ignorado. Usuario acha que regra esta ativa.
- **Teste regressivo proposto**:
  - terms.csv com termo `[invalid(` em linha onde `is_regex=True`.
  - Asserir que `parse_terms_csv` ou `precompile_patterns` levanta erro **explicito**, OU que registra WARNING.
- **Fix sugerido**: substituir `except: continue` por `except re.error as e: logger.warning("Invalid regex %r: %s", target, e); continue`.

### F-08 [S2] — Wildcard `*` muda semantica sem documentacao no terms.csv
- **Arquivo**: `src/fastslr/core/patterns.py:~34`
- **Trecho confirmado** (do mapeamento): `escaped = escaped.replace(r"\*", r"\w*")`
- **Problema**: usuario escreve termo literal `"AT*"` (ex.: simbolo proprio de marca registrada) → vira regex `AT\w*` → matches `"ATM"`, `"ATOM"`, `"ATE"` etc. Documentacao nao deixa claro que `*` e meta.
- **Teste regressivo proposto**:
  - terms.csv com termo `"*test*"` (literal) — verificar comportamento documentado.
  - Adicionar terms.csv com `"*"` sozinho — espera-se que valide (rejeite com erro).
- **Fix sugerido**: documentar wildcard explicitamente em `docs/TECHNICAL.md` e em uma das 21 validacoes de `terms.csv`. Se usuario quer `*` literal, exigir `is_regex=False, escape_wildcards=True`.

### F-09 [S3] — String vazia em `title`/`abstract` passa silenciosa
- **Arquivo**: `src/fastslr/core/engine.py:223-224`
- **Trecho confirmado**:
  ```python
  title = "" if pd.isna(title_value) else str(title_value)
  abstract = "" if pd.isna(abstract_value) else str(abstract_value)
  ```
- **Problema**: artigo com `title=""` e `abstract=""` (CSV mal exportado) e processado normalmente, gera `Final_Decision=REJECTED` com motivo "No positive terms found". Indistinguivel de artigo legitimamente fora do escopo.
- **Teste regressivo proposto**:
  - Asserir que stats incluem `articles_with_empty_text` e que `Decision_Reason` distingue `"Empty title and abstract"` de `"No positive terms found"`.
- **Fix sugerido**: logar warning ou marcar com decision distinta (`SKIPPED_EMPTY`).

### F-10 [S2] — BOM/encoding nao normalizam nomes de colunas
- **Arquivo**: `src/fastslr/core/io.py:~107-133` (`_header_score`)
- **Problema** (do mapeamento): CSV com BOM UTF-8 inicial faz a primeira coluna virar `﻿ID` em vez de `ID` → auto-detect falha → controller pede mapeamento manual ou rejeita.
- **Teste regressivo proposto**:
  - Carregar CSV com BOM.
  - Asserir que `auto_map_columns` retorna mapeamento correto.
- **Fix sugerido**: tratar BOM em `load_table_safe`.

### F-11 [S4] — `LRU cache` de normalizacao com tamanho hardcoded (2000)
- **Arquivo**: `src/fastslr/core/normalization.py:~27-50`
- **Problema**: para corpora grandes (>10k artigos com titulos unicos), cache evicta cedo. Sem metricas de hit rate.
- **Teste proposto** (performance, nao funcional):
  - Benchmark com 1k, 10k, 100k artigos. Medir tempo total. Esperado: O(n).
  - Verificar se variando `cache_maxsize` afeta tempo.

### F-12 [S2] — Regex de parsing de highlight em coverage e fragil
- **Arquivo**: `src/fastslr/core/coverage.py:~25,42`
- **Trecho** (mapeamento): `_HIGHLIGHT_TERM_RE = re.compile(r'term="([^"]+)"\s+sec=(\w+)')`
- **Problema**: se highlight gerado tem aspas escapadas, espaco extra, ordem diferente — match falha → termo conta como "morto" (zero hits) na coverage analysis.
- **Teste regressivo proposto**:
  - Pipeline E2E: rodar `fastslr run` sobre corpus que **certamente** contem termo X.
  - Rodar `fastslr coverage` sobre o mesmo corpus.
  - Asserir que termo X aparece com `count > 0` em coverage. **Hoje pode estar 0**.

### F-13 [S3] — Ausencia de testes para CLI/TUI/profiles/i18n
- **Modulos sem cobertura**: `app/cli.py`, `app/tui.py`, `app/profiles.py` (se existir), `i18n/__init__.py`.
- **Risco**: refactor de Typer ou Textual pode quebrar comandos sem teste pegar.
- **Plano**:
  - CLI: usar `typer.testing.CliRunner` para cada subcomando. Capturar stdout, exit codes.
  - TUI: usar `textual.pilot.Pilot` async para simular navegacao em pelo menos 3 telas criticas.
  - i18n: teste simples comparando keys() dos 3 JSON.

### F-14 [S2] — `data/Final_Corpus_Raw.csv` nao versionado, mas referenciado implicitamente
- **Observacao**: arquivo presente em `data/` (agora gitignored). Sem fixture pequena equivalente em `tests/fixtures/`, novos contribuidores nao conseguem rodar smoke local.
- **Plano**: criar `tests/fixtures/sample_corpus_10.csv` (10 artigos sintetizados, MIT-friendly).

### F-15 [S3] — Politicas de decisao "special_approval_rule" sem teste de boundary
- **Arquivo**: `src/fastslr/core/scoring.py:~451-461` (mapeamento)
- **Problema**: regra que aprova `1 FLAGGED + N-1 APPROVED com score >= threshold`. Boundaries nao tem testes:
  - 0 FLAGGED + N APPROVED → deve aprovar via politica normal.
  - 2 FLAGGED + N-2 APPROVED → deve **nao** aprovar via special.
  - 1 FLAGGED + N-1 APPROVED com 1 score < threshold → deve **nao** aprovar.
- **Plano**: adicionar 3 testes parametrizados em `test_main_findings_regressions.py`.

---

## 4. Plano de testes por modulo

> Notacao: **U** = unit, **I** = integration, **R** = regression, **P** = property-based, **E** = E2E.

### 4.1 `core/engine.py`
| Caso | Tipo | Descricao |
|---|---|---|
| Pipeline T0 → bloco unico → APPROVED | I | corpus minimo, config minima, asserir Final_Decision |
| Fail-fast: bloco 1 REJECTED → blocos 2,3 com `_create_not_evaluated` | U | mock evaluations |
| `error_policy='fail'` + erro → raise imediato | U | monkeypatch evaluate_block |
| `error_policy='flag'` + erro → ERR_X row | R | **F-01** |
| Corpus vazio → stats com total=0 | R | **F-02** |
| `MAX_ERROR_RATE` excedido → RuntimeError | U | corpus 10, force 5 erros, max=0.4 |
| Determinismo: 2 runs identicos → outputs iguais (sans timestamp) | I | **A1** |
| `id_value=""` → article_id="" (nao "NO_ID") | R | **F-09 variante** |
| `title=""` e `abstract=""` → decision distinta | R | **F-09** |
| BOM em CSV de entrada | I | **F-10** |

### 4.2 `core/scoring.py`
| Caso | Tipo | Descricao |
|---|---|---|
| Uplift aplicado quando `has_tags=False` e `raw_score>0` | U | parametrize |
| `has_tags=False` para `["", "nan", "n/a", "---", "tbd"]` | R | **F-03** |
| Threshold edge: `final_score == threshold` exato | R | **F-04** |
| Anti_flag em status APPROVED → FLAGGED | U | OK |
| Anti_flag em status FLAGGED → reason mencionar | R | **F-05** |
| Special approval rule: 0,1,2 FLAGGED variantes | R | **F-15** |
| Noise filter: unique_terms < min_unique → REJECTED | U | OK |
| Weak-only levels → REJECTED se `require_non_weak_term_for_approval` | U | OK |
| Section weight cap (`max_section_score=30`) | U | titulo com 5 termos L1 — score capped |

### 4.3 `core/normalization.py`
| Caso | Tipo | Descricao |
|---|---|---|
| Abreviacoes basicas (e.g., `AI` → `artificial intelligence`) | U | OK |
| Regex invalido em `normalization_target` → WARNING | R | **F-07** |
| LRU cache hit em re-chamada com mesma string | U | mock |
| Strings com unicode PT-BR (ç, ã, ê) | U | preservar acentos? rebaixar? |
| Symbol replacement: `&` em `AT&T` | R | mapeamento mencionou risco |
| Cache size pressure: >2000 strings unicas | P | nao falhar, so degradar |

### 4.4 `core/patterns.py`
| Caso | Tipo | Descricao |
|---|---|---|
| Wildcard `*` em termo literal | R | **F-08** |
| Compound term hifenizado (`machine-learning`) | R | mapeamento mencionou |
| Proximity matching: gap=2 com palavras intermediarias | U | OK |
| Proximity bidirecional (`oil and gas` ↔ `gas and oil`) | U | OK |
| Word boundary: termo `"AI"` nao deve casar `"AID"` | U | OK |
| Case-insensitive | U | OK |
| Termo com regex e `is_regex=True` | U | OK |
| Termo com regex invalido e `is_regex=True` | R | **F-07** variante |

### 4.5 `core/coverage.py`
| Caso | Tipo | Descricao |
|---|---|---|
| Highlight parsing happy path | U | regex match |
| Highlight com aspas escapadas | R | **F-12** |
| Termo morto (zero hits) reportado | U | OK |
| Termo amplo (>80% hits) reportado | U | OK |
| Total_articles=0 → pct calculation | R | divisor=1 mascarado |

### 4.6 `core/io.py`
| Caso | Tipo | Descricao |
|---|---|---|
| Load XLSX com `openpyxl` | U | OK |
| Load CSV com `;` separador | U | OK |
| Load TSV | U | OK |
| Load CSV com BOM | R | **F-10** |
| Encoding latin-1 (chardet detecta) | U | OK |
| `compute_file_hash` truncado SHA-256 | U | OK |
| `protocol.json` v2.1 schema | I | jsonschema validate |
| Export multi-formato (xlsx, csv, txt, json, zip) | I | OK |

### 4.7 `core/config.py`
| Caso | Tipo | Descricao |
|---|---|---|
| `parse_terms_csv` com 21 validacoes (commit 9bbff37) | U | cada validacao em teste separado |
| Coluna obrigatoria faltante | U | OK |
| Levels nao-inteiros | U | OK |
| Termo duplicado (mesmo escopo+level) | U | OK |
| `DECISION_POLICY` invalida em config.json | R | **A3** |
| `LIMITES_APROVADO` com chave nao-int | U | OK |
| Merge de defaults + user config | U | OK |

### 4.8 `app/cli.py`
| Caso | Tipo | Descricao |
|---|---|---|
| `fastslr version` → exit 0, version string | E | CliRunner |
| `fastslr run` sem args → exit 2, help | E | OK |
| `fastslr doctor` com config valida → exit 0 | E | OK |
| `fastslr doctor` com config invalida → exit 1 | E | OK |
| `fastslr preview -s 50` → 50 rows | E | OK |
| `fastslr coverage` → tabela | E | OK |
| `fastslr diff v1.xlsx v2.xlsx` → transitions | E | OK |
| `fastslr new-project nome -b "A,B,C"` → cria estrutura | E | OK |
| `fastslr profile save/load/list` | E | OK |
| `--lang pt_BR` → mensagens em PT | E | OK |

### 4.9 `app/tui.py`
| Caso | Tipo | Descricao |
|---|---|---|
| Boot da TUI sem crash | E | textual Pilot |
| Navegar 10 telas (NewProject, LoadProfile, EditConfig, BrowseTerms, RunTriage, ResultsExplorer, Coverage, Compare, Export, Settings) | E | OK |
| Atalho de saida (q ou Esc) em cada tela | E | OK |
| Run real com corpus pequeno via TUI | E | OK |

### 4.10 `i18n/`
| Caso | Tipo | Descricao |
|---|---|---|
| Chaves de en/pt_BR/es coincidem | U | `set(en) == set(pt_BR) == set(es)` |
| Locale invalido → fallback en | U | OK |
| Chave inexistente → retorna a chave | U | OK |

---

## 5. Plano de testes de integracao

| ID | Cenario |
|---|---|
| INT-01 | Pipeline completo CSV→XLSX com config minima, 100 artigos sinteticos |
| INT-02 | Pipeline com config T0 + 3 blocos + politica `special` |
| INT-03 | `error_policy='flag'` com 5 artigos quebrados em corpus de 100 |
| INT-04 | Reproducibilidade: 2 runs sequenciais → outputs identicos (excetuando timestamp) |
| INT-05 | `protocol.json` valida contra JSON Schema |
| INT-06 | Coverage analysis sobre output do INT-01 |
| INT-07 | Diff de outputs do INT-01 e INT-02 (mesma corpus, configs diferentes) |
| INT-08 | Export multi-formato → unzip → comparar conteudo |

---

## 6. Plano de testes end-to-end (CLI)

> Cada cenario E2E e um shell script ou pytest com `subprocess.run(["fastslr", ...])`. Criar `tests/e2e/test_cli_e2e.py`.

| ID | Comando | Asserts |
|---|---|---|
| E2E-01 | `fastslr version` | exit 0, contem "3.0.0" |
| E2E-02 | `fastslr new-project demo -b "A,B,C"` | cria `demo/` com config.json e terms.csv template |
| E2E-03 | `fastslr doctor --input fixture.csv -c demo/config.json -t demo/terms.csv` | exit 0, "OK" em stdout |
| E2E-04 | `fastslr run fixture.csv -c demo/config.json -t demo/terms.csv -o out/` | exit 0, gera 6+ arquivos em out/ |
| E2E-05 | `fastslr preview fixture.csv -c demo/config.json -s 5` | exit 0, 5 rows em stdout |
| E2E-06 | `fastslr coverage fixture.csv -c demo/config.json -t demo/terms.csv` | exit 0, tabela com termos |
| E2E-07 | `fastslr diff out1/results.xlsx out2/results.xlsx` | exit 0, transicoes listadas |
| E2E-08 | `fastslr run fixture.csv ...` 2x → outputs identicos sem timestamp | hash igual |
| E2E-09 | Mesmo cenario com `-l pt_BR` | mensagens em PT |
| E2E-10 | `--quiet` suprime progresso mas nao erros | stderr vazio em sucesso |

---

## 7. Plano de testes de regressao

> Cada `F-XX` do catalogo vira um teste em `tests/test_main_findings_regressions.py` (ja existe). Sugestao de organizacao:

```python
class TestF01_ErrorLogging:
    def test_processing_error_logged_at_warning_level(self, caplog): ...

class TestF03_EmptyTagsDetection:
    @pytest.mark.parametrize("placeholder", ["", " ", "nan", "n/a", "---", "tbd"])
    def test_empty_tag_placeholders_trigger_uplift(self, placeholder): ...

class TestF05_AntiFlagOnFlagged:
    def test_anti_flag_recorded_when_already_flagged(self): ...

# ... etc
```

---

## 8. Estrategia de cobertura e ferramentas

### 8.1 Ferramentas
- **Runner**: pytest (ja em uso)
- **Cobertura**: `pytest-cov` (adicionar em `[project.optional-dependencies]` `dev`)
- **Property-based**: `hypothesis` (adicionar)
- **CLI testing**: `typer.testing.CliRunner` (vem com Typer)
- **TUI testing**: `textual.pilot.Pilot` (vem com Textual)
- **JSON Schema**: `jsonschema`

### 8.2 Comando padrao
```bash
pytest --cov=src/fastslr --cov-report=term-missing --cov-report=html -v
```

### 8.3 Meta de cobertura
- **Linha**: 80% global, 90% em `core/`
- **Branch**: 70% global
- **Funcoes publicas**: 100%

### 8.4 CI
Criar `.github/workflows/tests.yml`:
- matrix: Python 3.10, 3.11, 3.12
- jobs: ruff, pyright, pytest+cov, smoke E2E
- gate: cobertura nao pode cair vs branch base

---

## 9. Matriz de prioridades

| Achado | Severidade | Esforco | Prioridade |
|---|---|---|---|
| F-01 (silent errors) | S2 | XS | **P0** |
| F-03 (empty tag markers) | S2 | XS | **P0** |
| F-08 (wildcard semantica) | S2 | S | **P0** |
| F-12 (highlight regex fragil) | S2 | S | **P0** |
| F-13 (CLI/TUI sem testes) | S2 | M | **P1** |
| F-14 (sample corpus) | S2 | XS | **P1** |
| F-02 (corpus vazio) | S2 | XS | **P1** |
| F-10 (BOM encoding) | S2 | XS | **P1** |
| F-04 (float threshold) | S3 | S | **P2** |
| F-05 (anti_flag perdido) | S3 | XS | **P2** |
| F-06 (norm_engine T0) | S3 | XS | **P2** |
| F-07 (silent regex error) | S3 | XS | **P2** |
| F-09 (empty title) | S3 | XS | **P2** |
| F-15 (special approval boundaries) | S3 | XS | **P2** |
| F-11 (LRU cache size) | S4 | M | **P3** |

> **P0**: bloqueia release. **P1**: deve entrar no proximo sprint. **P2**: backlog priorizado. **P3**: nice-to-have.

---

## Apendice A — Comandos uteis

```bash
# Rodar suite completa
pytest -v

# So regressions
pytest tests/test_main_findings_regressions.py tests/test_config_regressions.py -v

# So core, com cobertura
pytest tests/ --cov=src/fastslr/core --cov-report=term-missing -v

# Smoke E2E
pytest tests/e2e/ -v -m smoke

# Property-based (Hypothesis)
pytest tests/property/ -v --hypothesis-show-statistics

# Ruff + pyright
ruff check src/ tests/
ruff format --check src/ tests/
pyright src/
```

## Apendice B — Roteiro de manual UX

Ver [`docs/MANUAL_UX_TEST_GUIDE.md`](MANUAL_UX_TEST_GUIDE.md). Esse arquivo conduz **voce** atraves de cenarios de uso real, com checkpoints e perguntas de avaliacao.
