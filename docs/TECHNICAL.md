# FastSLR v3.0.0 — Descritivo Tecnico do Sistema

## 1. Visao Geral

**FastSLR** (Fast Systematic Literature Review) e um sistema de triagem deterministica universal para Revisoes Sistematicas de Literatura (RSL). Ele processa artigos academicos atraves de um pipeline de filtragem multi-estagio baseado em correspondencia de termos configuravel e regras de pontuacao, permitindo selecao rapida, reproduzivel e auditavel de artigos.

**Principio fundamental:** nenhum componente estocastico (ML, fuzzy matching) e utilizado. Todo o matching e baseado em regex compilado, garantindo que a mesma entrada + configuracao sempre produzem a mesma saida.

---

## 2. Estrutura do Projeto

```
fastslr/
├── src/fastslr/
│   ├── __init__.py
│   ├── core/                    # Motor de triagem (logica pura)
│   │   ├── __init__.py          # API publica exportada
│   │   ├── constants.py         # Constantes globais e defaults
│   │   ├── models.py            # Dataclasses do dominio (5 classes)
│   │   ├── engine.py            # Pipeline principal de processamento
│   │   ├── scoring.py           # Logica de avaliacao e arvore de decisao
│   │   ├── patterns.py          # Compilacao de padroes regex/proximity
│   │   ├── config.py            # Carregamento de config e parsing de termos CSV
│   │   ├── normalization.py     # Motor de normalizacao com cache LRU
│   │   ├── coverage.py          # Analise de cobertura de termos
│   │   ├── io.py                # I/O: CSV/XLSX, export, auditoria, protocolo
│   │   ├── adapters.py          # Deteccao de formato (Zotero/Scopus/WOS)
│   │   ├── presets.py           # Presets de niveis (binary/simple/standard)
│   │   └── default_config.json  # Template de configuracao padrao
│   ├── app/                     # Camada de aplicacao
│   │   ├── __init__.py
│   │   ├── cli.py               # CLI via Typer (10 comandos)
│   │   ├── tui.py               # TUI interativa via Textual (10 telas)
│   │   ├── controller.py        # Orquestrador unico CLI↔TUI↔Core
│   │   └── profiles.py          # Gerenciamento de perfis de configuracao
│   └── i18n/                    # Internacionalizacao
│       ├── __init__.py          # Sistema de traducao com fallback
│       └── locales/
│           ├── en.json          # Ingles (53 chaves)
│           ├── pt_BR.json       # Portugues brasileiro
│           └── es.json          # Espanhol
├── tests/                       # Suite de testes pytest
│   ├── conftest.py              # Fixtures compartilhadas
│   ├── test_engine.py           # Testes end-to-end do pipeline
│   ├── test_compliance.py       # Testes de conformidade
│   ├── test_normalization.py    # Testes do motor de normalizacao
│   └── test_patterns.py         # Testes de compilacao de padroes
├── docs/                        # Documentacao
├── data/                        # Diretorio de dados
├── pyproject.toml               # Build config (setuptools)
└── LICENSE                      # MIT
```

---

## 3. Modelo de Dados

### 3.1 Classes do Dominio (`core/models.py`)

| Classe | Descricao | Campos Principais |
|--------|-----------|-------------------|
| `TermMatch` | Match positivo encontrado em uma secao | `term`, `level`, `section`, `source_row`, `match_type`, `components` |
| `AntiHit` | Match de anti-termo (exclusao/sinalizacao) | `term`, `section`, `source_row` |
| `BlockEvaluation` | Resultado da avaliacao de um bloco tematico | `status`, `reason`, `raw_score`, `final_score`, `best_level`, `matches`, `anti_exclude`, `anti_flag`, `uplift_applied`, `section_scores` |
| `T0Evaluation` | Resultado da pre-triagem global T0 | `status`, `reason`, `scope`, `anti_exclude`, `anti_flag` |
| `GlobalParams` | 22 parametros configuraveis do motor | `level_scores`, `section_weights`, `approval_thresholds`, `flagging_thresholds`, `decision_policy`, `noise_profile`, etc. |

### 3.2 Status Possiveis

**Nivel de Bloco:**
- `APPROVED` — artigo aprovado no bloco
- `FLAGGED` — artigo sinalizado para revisao manual
- `REJECTED` — artigo rejeitado no bloco
- `NOT_EVALUATED` — bloco nao avaliado (fail-fast ou T0 excluiu)

**Nivel Final:**
- `APPROVED_FINAL` — aprovado para inclusao na RSL
- `FLAGGED_FINAL` — requer revisao humana
- `REJECTED_FINAL` — excluido da RSL

---

## 4. Algoritmo de Triagem — Pipeline Completo

### 4.1 Diagrama de Fluxo

```
Entrada (CSV/XLSX)
    │
    ▼
┌─────────────────────────┐
│  load_csv_safe()        │  Auto-deteccao de encoding e separador
│  Auto-map colunas       │  Mapeamento: key, title, abstract, manual_tags
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  _prepare_config()      │  1. Carrega config.json
│                         │  2. Faz merge com terms.csv (parse_terms_csv)
│                         │  3. Extrai regras de normalizacao
│                         │  4. Precompila todos os padroes regex
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│                  LOOP POR ARTIGO                            │
│  ┌───────────────────────┐                                  │
│  │  Estagio 1: T0        │  evaluate_t0_conditional()       │
│  │  Pre-triagem Global   │  Anti-termos globais             │
│  │                       │  → REJECTED: pula todos blocos   │
│  │                       │  → FLAGGED: marca e continua     │
│  │                       │  → PASSED: continua normalmente  │
│  └───────────┬───────────┘                                  │
│              │                                              │
│              ▼                                              │
│  ┌───────────────────────┐                                  │
│  │  Estagio 2: Blocos    │  Para cada bloco de dominio:     │
│  │  de Dominio           │  evaluate_block()                │
│  │  (CTX, TECH, SCM...) │                                  │
│  │                       │  1. find_positive_terms()        │
│  │                       │  2. find_anti_terms()            │
│  │                       │  3. _compute_section_scores()    │
│  │                       │  4. Aplica uplift (sem tags)     │
│  │                       │  5. Filtros de ruido             │
│  │                       │  6. Compara com thresholds       │
│  │                       │                                  │
│  │  [fail-fast: se       │                                  │
│  │   REJECTED, pula      │                                  │
│  │   blocos restantes]   │                                  │
│  └───────────┬───────────┘                                  │
│              │                                              │
│              ▼                                              │
│  ┌───────────────────────┐                                  │
│  │  Estagio 3: Decisao   │  make_final_decision()          │
│  │  Final                │  Combina resultados dos blocos   │
│  │                       │  via politica configurada        │
│  │                       │  → APPROVED_FINAL                │
│  │                       │  → FLAGGED_FINAL                 │
│  │                       │  → REJECTED_FINAL                │
│  └───────────┬───────────┘                                  │
│              │                                              │
│              ▼                                              │
│  ┌───────────────────────┐                                  │
│  │  Highlight + Output   │  Anota termos encontrados no     │
│  │  Row                  │  texto com ***TERMO***           │
│  └───────────────────────┘                                  │
└─────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────┐
│  collect_statistics()   │  Distribuicao de decisoes, scores,
│                         │  performance por bloco, tempo
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Exportacao             │  - triage_results.xlsx
│                         │  - triage_report.txt
│                         │  - config_audit.json
│                         │  - protocol.json (reprodutibilidade)
│                         │  - academic_report.md
│                         │  - academic_package.zip
└─────────────────────────┘
```

### 4.2 Algoritmo de Scoring Detalhado

O scoring opera **por bloco de dominio**, avaliando o artigo em tres secoes: `title`, `abstract` e `manual_tags`.

#### Passo 1: Busca de Termos Positivos (`find_positive_terms`)

```
Para cada termo configurado no bloco:
    1. Determinar secoes-alvo (scope: "any" → todas, ou secao especifica)
    2. Para cada secao-alvo:
        a. Normalizar texto da secao (lowercase, expansao de abreviaturas, etc.)
        b. Executar pattern.search(texto_normalizado)
        c. Se match encontrado:
           - Registrar TermMatch(term, level, section, source_row, match_type)
           - Adicionar level ao conjunto found_levels
```

Termos compostos (ex: "oil and gas") sao automaticamente decompostos em padroes de proximidade bidirecional: `oil ... gas` OU `gas ... oil` com gap maximo configuravel.

#### Passo 2: Busca de Anti-Termos (`find_anti_terms`)

```
Para cada anti-termo (exclude ou flag):
    1. Mesma logica de busca dos positivos
    2. Registrar AntiHit(term, section, source_row)
```

#### Passo 3: Calculo de Score por Secao (`_compute_section_scores`)

```
Para cada secao (title, abstract, manual_tags):
    1. Coletar niveis UNICOS encontrados na secao
       (multiplos matches no mesmo nivel contam apenas 1x)
    2. sec_raw = SUM( level_scores[nivel] para cada nivel unico )
    3. sec_raw = MIN( sec_raw, MAX_SECTION_SCORE )  // cap em 30 por padrao
    4. sec_score = sec_raw × section_weight
       - title: peso 2.0
       - abstract: peso 1.0
       - manual_tags: peso 1.5

raw_score = SUM( sec_score para todas secoes )
```

**Exemplo concreto:**
```
Artigo: "Machine Learning for Supply Chain Optimization"
Bloco TECH, termos encontrados:
  title:   "machine learning" (L1, score=10), "optimization" (L3, score=6)
  abstract: "machine learning" (L1, score=10)

Calculo:
  title_raw    = 10 + 6 = 16 (capped at 30) → 16 × 2.0 = 32.0
  abstract_raw = 10 (capped at 30)           → 10 × 1.0 = 10.0
  tags_raw     = 0                           →  0 × 1.5 =  0.0
  raw_score    = 32.0 + 10.0 + 0.0 = 42.0
```

#### Passo 4: Aplicacao de Uplift

```
Se manual_tags esta vazio E no_tags_uplift > 1.0 E raw_score > 0:
    final_score = raw_score × 1.17  (padrao)
Senao:
    final_score = raw_score
```

Isso compensa artigos sem tags manuais, evitando penalizacao por dados incompletos.

#### Passo 5: Filtros de Ruido (noise_profile = "strict")

Quando o perfil de ruido e "strict", filtros adicionais sao aplicados antes da aprovacao:

```
1. Se unique_terms < min_unique_terms_for_approval → REJECTED
2. Se sections_with_hits < min_sections_with_hits_for_approval → REJECTED
3. Se require_non_weak_term E apenas weak_levels encontrados → REJECTED
```

#### Passo 6: Decisao do Bloco

```
Se anti-exclude encontrado:
    → REJECTED (imediato, independe do score)

Se best_level (menor nivel encontrado) != None:
    Se final_score >= approval_threshold[best_level]:
        status = APPROVED
    Senao se final_score >= flagging_threshold[best_level]:
        status = FLAGGED
    Senao:
        status = REJECTED

Se anti-flag encontrado E status == APPROVED:
    → Rebaixa para FLAGGED
```

### 4.3 Algoritmo de Decisao Final (`make_final_decision`)

Tres politicas configuraveis:

#### Politica "special" (padrao)

```
1. T0 REJECTED → REJECTED_FINAL
2. Qualquer bloco REJECTED → REJECTED_FINAL
3. T0 FLAGGED → FLAGGED_FINAL
4. Qualquer bloco com anti-flag → FLAGGED_FINAL
5. Regra especial: se exatamente 1 bloco FLAGGED por score
   E todos os demais APPROVED com scores >= special_approval_threshold:
   → APPROVED_FINAL
6. Qualquer bloco FLAGGED por score → FLAGGED_FINAL
7. Todos blocos APPROVED → APPROVED_FINAL
8. Caso contrario → FLAGGED_FINAL (inconclusivo)
```

#### Politica "strict"

```
Todos blocos APPROVED → APPROVED_FINAL
Qualquer bloco FLAGGED → FLAGGED_FINAL
Qualquer bloco REJECTED → REJECTED_FINAL
```

#### Politica "k_of_n"

```
Se aprovados >= min_approved_blocks E sinalizados <= max_flagged:
    → APPROVED_FINAL
Se tem aprovados ou sinalizados:
    → FLAGGED_FINAL
Senao:
    → REJECTED_FINAL
```

---

## 5. Sistema de Padroes (`core/patterns.py`)

### 5.1 Compilacao de Termos

Cada termo e compilado para um `re.Pattern`:

| Tipo | Entrada | Regex Gerada |
|------|---------|--------------|
| Exato | `supply chain` | `\bsupply\ chain\b` |
| Wildcard | `optim*` | `\boptim\w*\b` |
| Regex | `ML\|AI\|DL` | `ML\|AI\|DL` (case-insensitive) |
| Proximidade | `supply and chain` | `\bsupply(?:\s+\S+){0,2}\s+chain\b \| \bchain(?:\s+\S+){0,2}\s+supply\b` |

### 5.2 Deteccao de Termos Compostos

O regex `_COMPOUND_RE` detecta padroes como:
- `"oil and gas"` → `(oil, gas)`
- `"supply & demand"` → `(supply, demand)`
- `"risk or hazard"` → `(risk, hazard)`
- `"input/output"` → `(input, output)`

Para cada par detectado, um padrao de proximidade bidirecional e gerado automaticamente.

---

## 6. Sistema de Normalizacao (`core/normalization.py`)

### 6.1 Motor de Normalizacao (`NormalizationEngine`)

Pipeline de transformacao deterministica com cache LRU (2000 entradas):

```
Texto bruto
    │
    ▼  1. Expansao de abreviaturas (case-insensitive, word-boundary)
    │     Ex: "AI" → "artificial intelligence"
    │
    ▼  2. Lowercase
    │
    ▼  3. Substituicao de simbolos
    │     Ex: "&" → "and"
    │
    ▼  4. Unificacao de variantes compostas (word-boundary)
    │     Ex: "supply-chain" → "supply chain"
    │
    ▼  5. Colapso de whitespace + trim
    │
    Texto normalizado
```

### 6.2 Extracao de Regras

Regras sao extraidas automaticamente do CSV de termos via colunas `normalization_type` e `normalization_target`:

| normalization_type | Exemplo term | normalization_target |
|-------------------|--------------|---------------------|
| `abbreviation` | AI | artificial intelligence |
| `compound_variant` | supply-chain | supply chain |
| `symbol_replacement` | & | and |

---

## 7. Camada de Configuracao

### 7.1 Estrutura do config.json

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
  "fields": {
    "id": "key", "title": "title",
    "abstract": "abstract", "manual_tags": "manual_tags"
  },
  "output": {
    "csv": false, "xlsx": true, "academic_package": true
  }
}
```

### 7.2 Estrutura do terms.csv

```
block;kind;term;level;section_scope;is_regex;normalization_type;normalization_target
CTX;pos;oil and gas;1;any;0;compound_variant;oil_gas
CTX;pos;energy sector;2;title;0;;
TECH;pos;machine learning;1;any;0;;
TECH;pos;optim*;3;any;0;;
TECH;anti;systematic review;0;any;0;;
GLOBAL;anti;book review;0;any;0;;
GLOBAL;flag;conference abstract;0;any;0;;
```

### 7.3 Presets de Niveis

| Preset | Niveis | Uso Recomendado |
|--------|--------|-----------------|
| `binary` | 1 | Triagem rapida: relevante ou nao |
| `simple` | 3 | Projetos com poucos termos |
| `standard` | 5 | Recomendado para RSL completas |

---

## 8. Arquitetura de Camadas

```
┌─────────────────────────────────────────────┐
│              Camada de Interface             │
│  ┌─────────────┐     ┌──────────────────┐   │
│  │  CLI (Typer) │     │  TUI (Textual)   │   │
│  │  10 comandos │     │  10 telas        │   │
│  └──────┬──────┘     └────────┬─────────┘   │
│         │                     │              │
│         └─────────┬───────────┘              │
│                   ▼                          │
│  ┌─────────────────────────────────────┐     │
│  │      Controller (controller.py)     │     │
│  │  Ponto unico de orquestracao        │     │
│  │  Validacao, preparacao, despacho    │     │
│  └──────────────────┬──────────────────┘     │
└─────────────────────┼───────────────────────┘
                      │
┌─────────────────────┼───────────────────────┐
│              Camada Core                     │
│                     ▼                        │
│  ┌──────────────────────────────────────┐    │
│  │  engine.py — process_articles()      │    │
│  │  Pipeline principal                  │    │
│  └────────┬──────────────┬──────────────┘    │
│           │              │                   │
│   ┌───────▼───────┐  ┌──▼──────────────┐    │
│   │  scoring.py   │  │  patterns.py     │    │
│   │  Avaliacao    │  │  Compilacao      │    │
│   └───────┬───────┘  └──┬──────────────┘    │
│           │              │                   │
│   ┌───────▼──────────────▼──────────────┐    │
│   │  normalization.py + config.py       │    │
│   │  Normalizacao e parametrizacao      │    │
│   └─────────────────────────────────────┘    │
│                                              │
│   ┌─────────────────────────────────────┐    │
│   │  io.py + coverage.py               │    │
│   │  I/O, export, auditoria, cobertura │    │
│   └─────────────────────────────────────┘    │
└──────────────────────────────────────────────┘
```

**Regra arquitetural:** CLI e TUI **nunca** importam diretamente do `core`. Toda comunicacao passa pelo `controller.py`, que atua como fachada unica.

---

## 9. Sistema de I/O e Auditoria

### 9.1 Carregamento de Entrada

`load_csv_safe()` implementa deteccao automatica:
1. Detecta encoding via `chardet` (ou assume UTF-8)
2. Tenta separadores na ordem: `;`, `,`, `\t`
3. Aceita CSV com >= 3 colunas
4. Auto-mapeia colunas por aliases (ex: "Abstract Note" → "abstract")

### 9.2 Artefatos de Saida

Uma execucao completa gera:

| Artefato | Formato | Proposito |
|----------|---------|-----------|
| `triage_results.xlsx` | Excel | Resultados com scores, decisoes e highlights |
| `triage_report.txt` | Texto | Relatorio legivel com estatisticas |
| `config_audit.json` | JSON | Configuracao sanitizada para auditoria |
| `protocol.json` | JSON | Snapshot de protocolo para reprodutibilidade |
| `academic_report.md` | Markdown | Relatorio academico formatado |
| `academic_package.zip` | ZIP | Pacote completo para publicacao |

### 9.3 Hashing para Reprodutibilidade

- **Config hash:** SHA-256 truncado (16 hex) da configuracao serializada (sort_keys, sem patterns compilados)
- **File hash:** SHA-256 truncado (16 hex) do conteudo binario do arquivo
- **Execution ID:** UUID parcial (`run_<12 hex>`) para identificacao unica de cada execucao

### 9.4 Protocolo Snapshot (v2.1)

Estrutura completa para reprodutibilidade academica:
```json
{
  "protocol_version": "2.1",
  "schema_id": "rsl-triage-protocol-v2.1",
  "execution_id": "run_abc123def456",
  "triage_version": "3.0.0",
  "inputs": { "input_hash": "...", "terms_hash": "...", "config_hash": "..." },
  "configuration": { "decision_policy": "...", "domain_blocks": [...] },
  "processing": { "total_articles": 500, "processing_time_seconds": 1.2 },
  "reproducibility": { "deterministic_engine": true }
}
```

---

## 10. Sistema de Highlighting

Termos encontrados sao marcados no texto original com `***TERMO***`:

```
Entrada:  "Machine learning for supply chain optimization"
Saida:    "***MACHINE LEARNING*** for ***SUPPLY CHAIN*** ***OPTIMIZATION***"
```

O algoritmo:
1. Coleta spans de todos os matches via `pattern.finditer()`
2. Ordena e faz merge de spans sobrepostos
3. Insere marcadores em ordem reversa (para preservar indices)

---

## 11. Internacionalizacao (i18n)

### 11.1 Deteccao de Locale

Prioridade: `FASTSLR_LANG` env var → locale do sistema → `en`

### 11.2 Funcao de Traducao

```python
from fastslr.i18n import _

_("version_info", version="3.0.0")  # → "FastSLR v3.0.0"
```

Fallback chain: locale ativo → ingles → chave literal.

### 11.3 Idiomas Suportados

`en` (Ingles), `pt_BR` (Portugues BR), `es` (Espanhol)

---

## 12. Tratamento de Erros

Duas politicas configuraveis via `ERROR_POLICY`:

| Politica | Comportamento |
|----------|---------------|
| `"flag"` (padrao) | Artigos com erro sao marcados como `FLAGGED_FINAL` com razao do erro |
| `"fail"` | Levanta excecao no primeiro erro, interrompendo o processamento |

---

## 13. Dependencias

| Pacote | Versao Minima | Funcao |
|--------|--------------|--------|
| pandas | >= 2.0 | Processamento de DataFrames, I/O CSV/XLSX |
| openpyxl | >= 3.1 | Escrita de Excel formatado |
| typer | >= 0.12 | Framework CLI com tipagem |
| rich | >= 13.0 | Estilizacao de terminal (tabelas, progress bars) |
| textual | >= 0.80 | Framework TUI interativa |
| chardet | >= 5.0 (opcional) | Auto-deteccao de encoding |

**Python:** >= 3.10 (uso de `X | Y` union types)

---

## 14. Build e Distribuicao

- **Build system:** setuptools >= 68.0
- **Entry point:** `fastslr = "fastslr.app.cli:app"`
- **Tipo de pacote:** `py.typed` (suporte a type checking)
- **Licenca:** MIT
