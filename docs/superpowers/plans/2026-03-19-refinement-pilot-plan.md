# FastSLR v3.0.0 — Refinement for Pilot Registration: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare FastSLR for simultaneous academic publication and PyPI/Zenodo registration through JSON Schema validation, complete test suite (>=80% coverage), docstrings, operational README, and Technical Report.

**Architecture:** Interleaved approach — Schema first (foundation), then tests + docstrings in parallel, then README and Technical Report as consolidation. Schema defines the formal config contract that tests validate and docs reference.

**Tech Stack:** Python >=3.10, jsonschema >=4.20, pytest + pytest-cov, Google-style docstrings, Mermaid diagrams in Markdown.

**Spec:** `docs/superpowers/specs/2026-03-19-refinement-pilot-design.md`

---

## File Structure

### New Files
| File | Responsibility |
|---|---|
| `src/fastslr/core/config_schema.json` | JSON Schema (Draft 2020-12) for user-facing config |
| `tests/test_scoring.py` | Unit tests for scoring.py (>=90% coverage target) |
| `tests/test_config.py` | Config loading + schema validation tests |
| `tests/test_io.py` | I/O, adapters, export tests |
| `tests/test_presets.py` | Preset generation and validation tests |
| `tests/test_coverage_analysis.py` | Term coverage analysis tests |
| `tests/test_integration.py` | E2E pipeline tests with synthetic fixtures |
| `tests/fixtures/scenario_a_config.json` | 3-block standard config fixture |
| `tests/fixtures/scenario_a_articles.csv` | Synthetic articles for scenario A |
| `tests/fixtures/scenario_b_config.json` | 2-block strict policy config |
| `tests/fixtures/scenario_b_articles.csv` | Synthetic articles for scenario B |
| `tests/fixtures/scenario_c_config.json` | 3-block k_of_n with T0 config |
| `tests/fixtures/scenario_c_articles.csv` | Synthetic articles for scenario C |
| `tests/fixtures/scenario_d_config.json` | O&G subset regression config |
| `tests/fixtures/scenario_d_articles.csv` | Synthetic O&G articles for scenario D |
| `README.md` | Operational guide for researchers |
| `docs/TECHNICAL_REPORT.md` | Executive-technical reference |

### Modified Files
| File | Change |
|---|---|
| `pyproject.toml` | Add `jsonschema>=4.20` to deps, `pytest-cov>=4.0` to dev deps |
| `src/fastslr/core/config.py` | Add schema validation in `load_config()` |
| `src/fastslr/i18n/locales/en.json` | Add schema error i18n keys |
| `src/fastslr/i18n/locales/pt_BR.json` | Add schema error i18n keys |
| `src/fastslr/i18n/locales/es.json` | Add schema error i18n keys |
| `tests/conftest.py` | Add shared fixtures for new tests |
| All core/ and app/ public functions | Add Google-style docstrings |

---

## Phase 8: JSON Schema

### Task 1: Add jsonschema dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add dependencies**

In `pyproject.toml`, add `jsonschema>=4.20` to `[project.dependencies]` and `pytest-cov>=4.0` to `[project.optional-dependencies] dev`.

- [ ] **Step 2: Install**

Run: `pip install -e ".[dev]"`
Expected: jsonschema and pytest-cov installed successfully.

- [ ] **Step 3: Verify**

Run: `python -c "import jsonschema; print(jsonschema.__version__)"`
Expected: Version >=4.20

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add jsonschema and pytest-cov dependencies"
```

---

### Task 2: Create config_schema.json

**Files:**
- Create: `src/fastslr/core/config_schema.json`

**Reference:** `src/fastslr/core/default_config.json` for structure, `src/fastslr/core/models.py:81` (GlobalParams) for field types/defaults, `src/fastslr/core/constants.py` for valid values.

- [ ] **Step 1: Write the schema**

Create `src/fastslr/core/config_schema.json` with JSON Schema Draft 2020-12. The schema validates the **raw user-facing JSON config** (before term merging from CSV). Key structure:

- `global` (required object): All GlobalParams fields with types, defaults, and ranges.
  - `PONTUACAO_NIVEIS` / `level_scores`: object mapping int to int, minProperties 1
  - `LIMITES_APROVADO` / `approval_thresholds`: object mapping int to (number or null)
  - `LIMITES_SINALIZADO` / `flagging_thresholds`: object mapping int to number
  - `WEIGHTS` / `section_weights`: object with title/abstract/manual_tags as numbers >=0
  - `DECISION_POLICY`: enum ["special", "strict", "k_of_n"]
  - `NOISE_PROFILE`: enum ["relaxed", "balanced", "strict"]
  - `ERROR_POLICY`: enum ["flag", "fail"]
  - Numeric params: NO_TAGS_UPLIFT (>=1.0), MAX_SECTION_SCORE (>0), MAX_GAP_BETWEEN_TERMS (>=0)
  - Boolean params: FAIL_FAST_GLOBAL, ENABLE_PROXIMITY_DETECTION, ENABLE_SPECIAL_APPROVAL_RULE, REQUIRE_NON_WEAK_TERM_FOR_APPROVAL
  - Accept both English and legacy PT key names (both valid)
- `fields` (optional object): id, id_output, title, abstract, manual_tags — all strings
- `output` (optional object): csv (bool), xlsx (bool), csv_sep (string), etc.
- `encoding` (optional string)
- `sep` (optional string)
- `t0` (optional object): `anti_exclude` and `anti_flag` arrays of strings
- `_domain_blocks` (optional array): each item is an object with name (required string), positives (required array), anti_exclude (optional array), anti_flag (optional array)
- `normalization` (optional object): enabled (bool), rules (object)
- `additionalProperties: true` (allow block names as top-level keys for legacy format)

- [ ] **Step 2: Validate schema syntax**

Run: `python -c "import json, jsonschema; s=json.load(open('src/fastslr/core/config_schema.json')); jsonschema.Draft202012Validator.check_schema(s); print('Schema valid')"`
Expected: "Schema valid"

- [ ] **Step 3: Test against default_config.json**

Run: `python -c "import json, jsonschema; s=json.load(open('src/fastslr/core/config_schema.json')); c=json.load(open('src/fastslr/core/default_config.json')); jsonschema.validate(c, s); print('Config valid')"`
Expected: "Config valid"

- [ ] **Step 4: Commit**

```bash
git add src/fastslr/core/config_schema.json
git commit -m "feat: add JSON Schema for config validation (Draft 2020-12)"
```

---

### Task 3: Integrate schema validation into config.py

**Files:**
- Modify: `src/fastslr/core/config.py:26` (load_config function)
- Modify: `src/fastslr/i18n/locales/en.json`, `pt_BR.json`, `es.json`

- [ ] **Step 1: Add i18n keys for schema errors**

Add to all three locale JSON files (`en.json`, `pt_BR.json`, `es.json`):

```json
"schema_error_title": "Configuration validation error",
"schema_error_field": "Invalid field: {field}",
"schema_error_expected": "Expected: {expected}, got: {got}",
"schema_error_type": "Invalid type for '{field}': expected {expected}"
```

(Translate accordingly for pt_BR and es.)

- [ ] **Step 2: Add _validate_config_schema to config.py**

Add a new private function and call it from `load_config()`:

```python
import jsonschema
from pathlib import Path
from fastslr.i18n import _

_SCHEMA_PATH = Path(__file__).parent / "config_schema.json"

def _validate_config_schema(config: dict) -> None:
    """Validate config against JSON Schema. Raises ValueError on failure."""
    if not _SCHEMA_PATH.exists():
        logger.warning("Schema file not found, skipping validation")
        return
    with open(_SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)
    try:
        jsonschema.validate(config, schema)
    except jsonschema.ValidationError as e:
        field = ".".join(str(p) for p in e.absolute_path) or "(root)"
        msg = _("schema_error_field", field=field)
        raise ValueError(f"{_('schema_error_title')}: {msg} -- {e.message}") from e
```

In `load_config()`, add `_validate_config_schema(config)` after `json.load()` and before `return config`.

- [ ] **Step 3: Run existing tests to verify no regression**

Run: `pytest tests/ -v`
Expected: All 51 existing tests pass.

- [ ] **Step 4: Commit**

```bash
git add src/fastslr/core/config.py src/fastslr/i18n/locales/
git commit -m "feat: integrate JSON Schema validation into load_config()"
```

---

## Phase 9a: Test Suite

### Task 4: Expand conftest.py with shared fixtures

**Files:**
- Modify: `tests/conftest.py`

- [ ] **Step 1: Add fixtures for scoring, config, and integration tests**

Add new fixtures:
- `minimal_block_config` — a minimal domain block with 3 positive terms across 2 levels, 1 anti-exclude, 1 anti-flag, empty proximity_positives
- `sample_article_relevant` — dict with title/abstract/manual_tags matching level-1 terms
- `sample_article_irrelevant` — dict with no matching terms
- `sample_article_anti_exclude` — dict triggering anti-exclusion ("cooking oil")
- `fixtures_dir` — Path to tests/fixtures/

- [ ] **Step 2: Create fixtures directory**

Run: `mkdir -p tests/fixtures`

- [ ] **Step 3: Run existing tests to verify no regression**

Run: `pytest tests/ -v`
Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py
git commit -m "test: expand conftest with shared fixtures for new test suite"
```

---

### Task 5: test_scoring.py — Core scoring module tests

**Files:**
- Create: `tests/test_scoring.py`
- Test: `src/fastslr/core/scoring.py`

This is the most critical test file. Target: >=90% coverage of scoring.py (~475 lines).

- [ ] **Step 1: Write TestFindPositiveTerms class**

6 tests covering:
- Exact match in title
- Match in abstract
- Match in manual_tags
- No match returns empty sets
- Multiple levels detected simultaneously
- Case-insensitive matching

Uses `minimal_block_config` fixture. Must call `precompile_patterns(block)` before `find_positive_terms()`.

- [ ] **Step 2: Write TestFindAntiTerms class**

3 tests covering:
- Detects anti-exclude term
- Detects anti-flag term
- No anti terms returns empty list

- [ ] **Step 3: Write TestEvaluateBlock class**

7 tests covering:
- APPROVED when strong terms found
- REJECTED when no terms found
- REJECTED by anti-exclude
- FLAGGED by anti-flag downgrade
- Uplift applied when no manual_tags
- No uplift when tags present
- Section scores are populated in result

- [ ] **Step 4: Write TestMakeFinalDecision class**

9 tests covering all 3 policies:
- All APPROVED returns APPROVED_FINAL
- Any REJECTED returns REJECTED_FINAL
- FLAGGED block returns FLAGGED_FINAL (or APPROVED via special rule)
- Special approval rule: 1 flagged + others >=40 -> APPROVED_FINAL
- Special approval fails when scores < 40
- T0 FLAGGED returns FLAGGED_FINAL
- Strict policy requires all APPROVED
- k_of_n policy with min_approved_blocks
- k_of_n with too many flagged -> FLAGGED_FINAL

Uses helper `_make_eval(status, score, best_level, anti_flag)` to create BlockEvaluation instances.

- [ ] **Step 5: Write TestEvaluateT0 class**

4 tests covering:
- Returns None when no T0 config
- REJECTED on anti-exclude match
- FLAGGED on anti-flag match
- Passes when no anti terms match

- [ ] **Step 6: Run all scoring tests**

Run: `pytest tests/test_scoring.py -v`
Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add tests/test_scoring.py
git commit -m "test: add comprehensive scoring module tests (29 tests)"
```

---

### Task 6: test_config.py — Config + schema validation tests

**Files:**
- Create: `tests/test_config.py`
- Test: `src/fastslr/core/config.py`, `src/fastslr/core/config_schema.json`

- [ ] **Step 1: Write TestLoadConfig class**

3 tests: loads valid config, raises on nonexistent file, raises on invalid JSON.

- [ ] **Step 2: Write TestSchemaValidation class**

4 tests: rejects invalid DECISION_POLICY, rejects invalid NOISE_PROFILE, accepts minimal valid config, accepts config with _domain_blocks.

- [ ] **Step 3: Write TestLoadGlobalParams class**

3 tests: loads defaults from empty config, loads legacy PT keys (PONTUACAO_NIVEIS), loads English keys (level_scores).

- [ ] **Step 4: Write TestParseTermsCsv class**

2 tests: parses valid CSV with blocks, GLOBAL block becomes T0 anti-terms.

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_config.py -v`
Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add tests/test_config.py
git commit -m "test: add config loading and schema validation tests"
```

---

### Task 7: test_presets.py — Presets module tests

**Files:**
- Create: `tests/test_presets.py`
- Test: `src/fastslr/core/presets.py`

- [ ] **Step 1: Write tests**

TestGetPreset: returns binary (level_count=1), simple (3), standard (5), raises on unknown, all presets have required keys.
TestBuildCustomPreset: valid custom preset, raises on zero levels.
TestGenerateConfig: generates config with blocks and standard preset.

- [ ] **Step 2: Run tests**

Run: `pytest tests/test_presets.py -v`
Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add tests/test_presets.py
git commit -m "test: add presets module tests"
```

---

### Task 8: test_io.py — I/O and adapter tests

**Files:**
- Create: `tests/test_io.py`
- Test: `src/fastslr/core/io.py`, `src/fastslr/core/adapters.py`

- [ ] **Step 1: Write TestLoadCsvSafe class**

3 tests: loads valid CSV, loads semicolon-separated, handles empty CSV with headers (0 rows).

- [ ] **Step 2: Write TestDetectFormat class**

4 tests: detects Scopus (EID column), WOS (UT/TI/AB), Zotero (Key/Abstract Note), returns None for unknown.

- [ ] **Step 3: Write TestNormalizeImport class**

2 tests: normalizes Zotero columns, normalizes Scopus columns.

- [ ] **Step 4: Write TestComputeConfigHash and TestProtocolSnapshot classes**

Hash: deterministic (same config twice = same hash), different configs = different hashes.
Snapshot: validates valid snapshot returns 0 issues.

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_io.py -v`
Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add tests/test_io.py
git commit -m "test: add I/O, adapter, and protocol snapshot tests"
```

---

### Task 9: test_coverage_analysis.py — Coverage analysis tests

**Files:**
- Create: `tests/test_coverage_analysis.py`
- Test: `src/fastslr/core/coverage.py`

- [ ] **Step 1: Write tests**

TestAnalyzeTermCoverage: detects dead terms (term with 0 matches), report has required fields.
TestFormatCoverageReport: produces non-empty string output.

- [ ] **Step 2: Run tests**

Run: `pytest tests/test_coverage_analysis.py -v`
Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add tests/test_coverage_analysis.py
git commit -m "test: add term coverage analysis tests"
```

---

### Task 10: Integration test fixtures

**Files:**
- Create: `tests/fixtures/scenario_a_config.json` (3 blocks, standard, special policy)
- Create: `tests/fixtures/scenario_a_articles.csv` (12 synthetic articles)
- Create: `tests/fixtures/scenario_b_config.json` (2 blocks, strict policy)
- Create: `tests/fixtures/scenario_b_articles.csv` (8 articles)
- Create: `tests/fixtures/scenario_c_config.json` (3 blocks, k_of_n, T0)
- Create: `tests/fixtures/scenario_c_articles.csv` (10 articles)
- Create: `tests/fixtures/scenario_d_config.json` (O&G regression subset from v12)
- Create: `tests/fixtures/scenario_d_articles.csv` (10 articles)

- [ ] **Step 1: Create Scenario A fixtures**

Config: 3 blocks (TOPIC, METHOD, DOMAIN), standard preset, special policy. Each block: 3-5 positives across levels 1-3, 1-2 anti-terms.
Articles: 12 synthetic — 3 APPROVED_FINAL, 3 REJECTED_FINAL, 3 FLAGGED_FINAL, 2 anti-exclude rejection, 1 fail-fast test.

- [ ] **Step 2: Create Scenario B fixtures**

Config: 2 blocks, strict policy, fail-fast enabled.
Articles: 8 testing strict policy behavior.

- [ ] **Step 3: Create Scenario C fixtures**

Config: 3 blocks, k_of_n (min_approved=2, max_flagged=1), T0 with anti-terms.
Articles: 10 testing k_of_n and T0 interactions.

- [ ] **Step 4: Create Scenario D fixtures**

Config: 3 blocks (CTX, AI, SCM) with 5-8 terms per block extracted and simplified from validated v12 pilot protocol.
Articles: 10 synthetic O&G domain articles with known expected results.

- [ ] **Step 5: Run pipeline manually on each scenario to generate and verify gold-standard results**

For each scenario, run process_articles() once, inspect outputs, confirm decisions make sense given terms and thresholds. These verified results become the assertions in test_integration.py.

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/
git commit -m "test: add integration test fixtures for 4 E2E scenarios"
```

---

### Task 11: test_integration.py — E2E pipeline tests

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write TestScenarioA class**

4 tests:
- Produces results with Final_Decision column
- Has both APPROVED_FINAL and REJECTED_FINAL decisions
- Deterministic: running twice produces identical DataFrames (assert_frame_equal)
- Fail-fast: articles rejected at first block have NOT_EVALUATED in later blocks

- [ ] **Step 2: Write TestScenarioB class**

1 test: In strict policy, all blocks must be APPROVED for APPROVED_FINAL.

- [ ] **Step 3: Write TestScenarioC class**

2 tests: k_of_n allows partial approval; T0 rejection overrides block results.

- [ ] **Step 4: Write TestScenarioD class**

2 tests: Deterministic regression; produces expected mix of decisions (>=2 unique).

- [ ] **Step 5: Run integration tests**

Run: `pytest tests/test_integration.py -v`
Expected: All tests pass.

- [ ] **Step 6: Run full suite with coverage**

Run: `pytest tests/ -v --cov=src/fastslr --cov-report=term-missing`
Expected: Global >=80%, scoring.py >=90%.

- [ ] **Step 7: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add E2E integration tests for 4 scenarios with determinism verification"
```

---

## Phase 9b: Docstrings (parallel with Phase 9a)

### Task 12: Docstrings for scoring.py and models.py

**Files:**
- Modify: `src/fastslr/core/scoring.py`
- Modify: `src/fastslr/core/models.py`

- [ ] **Step 1: Add docstrings to scoring.py public functions**

Google-style docstrings with Args, Returns, and algorithm context for:
- `find_positive_terms` (line 40)
- `find_anti_terms` (line 105)
- `evaluate_block` (line 183)
- `evaluate_t0_conditional` (line 331)
- `make_final_decision` (line 381)

- [ ] **Step 2: Add docstrings to models.py dataclasses**

Class-level docstrings explaining purpose and fields for:
- `TermMatch` (line 11)
- `AntiHit` (line 29)
- `BlockEvaluation` (line 41)
- `T0Evaluation` (line 67)
- `GlobalParams` (line 81)

- [ ] **Step 3: Run pyright**

Run: `pyright src/fastslr/core/scoring.py src/fastslr/core/models.py`
Expected: 0 errors.

- [ ] **Step 4: Commit**

```bash
git add src/fastslr/core/scoring.py src/fastslr/core/models.py
git commit -m "docs: add Google-style docstrings to scoring.py and models.py"
```

---

### Task 13: Docstrings for engine.py, config.py, patterns.py

**Files:**
- Modify: `src/fastslr/core/engine.py`
- Modify: `src/fastslr/core/config.py`
- Modify: `src/fastslr/core/patterns.py`

- [ ] **Step 1: Add docstrings to engine.py**

- `process_articles` (line 104) — main pipeline loop, fail-fast, error policies
- `collect_statistics` (line 53) — aggregation of results
- `sample_articles` (line 287) — sampling for preview

- [ ] **Step 2: Add docstrings to config.py**

- `load_config` (line 26)
- `parse_terms_csv` (line 140)
- `load_global_params` (line 58)
- `get_domain_blocks` (line 53)
- `_validate_config_schema` (new)

- [ ] **Step 3: Add docstrings to patterns.py**

- `compile_pattern` — regex with word boundaries and wildcards
- `compile_proximity_pattern` — bidirectional proximity
- `detect_compound_terms` — and/or/slash detection
- `precompile_patterns` — batch compilation for a block

- [ ] **Step 4: Run pyright**

Run: `pyright src/fastslr/core/engine.py src/fastslr/core/config.py src/fastslr/core/patterns.py`
Expected: 0 errors.

- [ ] **Step 5: Commit**

```bash
git add src/fastslr/core/engine.py src/fastslr/core/config.py src/fastslr/core/patterns.py
git commit -m "docs: add docstrings to engine, config, and patterns modules"
```

---

### Task 14: Docstrings for io.py, adapters.py, presets.py, coverage.py, controller.py

**Files:**
- Modify: `src/fastslr/core/io.py`
- Modify: `src/fastslr/core/adapters.py`
- Modify: `src/fastslr/core/presets.py`
- Modify: `src/fastslr/core/coverage.py`
- Modify: `src/fastslr/app/controller.py`

- [ ] **Step 1: Docstrings for io.py**

Key functions: `load_csv_safe`, `export_results`, `build_protocol_snapshot`, `validate_protocol_snapshot`, `export_protocol_snapshot`, `generate_report`, `compute_config_hash`, `compute_file_hash`, `export_academic_report`, `export_appendix_pack`.

- [ ] **Step 2: Docstrings for adapters.py**

`detect_format`, `apply_mapping`, `normalize_import`, `ColumnMapping` dataclass.

- [ ] **Step 3: Docstrings for presets.py**

`get_preset`, `build_custom_preset`, `generate_config`.

- [ ] **Step 4: Docstrings for coverage.py**

`analyze_term_coverage`, `format_coverage_report`, `export_coverage_csv`, `TermCoverageReport`.

- [ ] **Step 5: Docstrings for controller.py**

All public functions + dataclasses: `validate_config`, `run_triage`, `preview_triage`, `analyze_coverage`, `diff_results`, `create_project`, `export_academic_package`, `browse_terms`, `ValidationIssue`, `TriageResult`, `PreviewResult`, `DiffEntry`, `DiffReport`, `TermsView`.

- [ ] **Step 6: Run pyright on all modified files**

Run: `pyright src/fastslr/`
Expected: 0 errors.

- [ ] **Step 7: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests pass.

- [ ] **Step 8: Commit**

```bash
git add src/fastslr/core/io.py src/fastslr/core/adapters.py src/fastslr/core/presets.py src/fastslr/core/coverage.py src/fastslr/app/controller.py
git commit -m "docs: add docstrings to io, adapters, presets, coverage, and controller"
```

---

## Phase 10: README

### Task 15: Write README.md

**Files:**
- Create: `README.md` (rewrite)

**Reference:** Spec Deliverable 4 for structure. CLI commands in `src/fastslr/app/cli.py`. Schema in `src/fastslr/core/config_schema.json`.

- [ ] **Step 1: Write Overview + Quick Start + Concepts**

Overview: what FastSLR is, for whom, philosophy (deterministic, transparent, reproducible). Badges: version, Python, license, tests.
Quick Start: pip install, first run in 3 commands (new-project, edit config, run).
Concepts: blocks, levels 1-5, anti-terms (exclusion vs flagging), sections/weights, decisions, fail-fast.

- [ ] **Step 2: Write Configuration Guide**

config.json structure referencing schema, every global parameter explained with type/default/range/effect, how to define blocks/terms/anti-terms, terms CSV format, presets (binary/simple/standard), annotated config examples.

- [ ] **Step 3: Write CLI Reference + TUI Guide**

All 10 commands: run, preview, coverage, diff, new-project, export, terms, profile (save/load/list), tui, version. Each with usage example.
TUI: each of 10 screens described, keyboard shortcuts (1-9, 0, Esc, Q).

- [ ] **Step 4: Write Understanding Results + Academic Use**

Output XLSX structure, per-block columns (RawScore, FinalScore, BestLevel, Status, Highlights, AntiHighlights, Flags), Final_Decision + Final_Reason, protocol snapshot, config hash.
Academic: how to cite, how to report parameters in methods section, academic export ZIP.

- [ ] **Step 5: Write i18n + Development + License**

Languages: en, pt_BR, es. Switch: --lang flag or FASTSLR_LANG env var.
Dev: clone, pip install -e ".[dev]", pytest --cov, ruff check/format, pyright.
License: MIT.

- [ ] **Step 6: Validate README against checklist**

1. pip install instructions are correct
2. new-project -> edit -> run workflow documented
3. All 10 CLI commands documented with examples
4. All global parameters covered

- [ ] **Step 7: Commit**

```bash
git add README.md
git commit -m "docs: add comprehensive operational README for researchers"
```

---

## Phase 11: Technical Report

### Task 16: Write TECHNICAL_REPORT.md — Sections 1-4

**Files:**
- Create: `docs/TECHNICAL_REPORT.md`

**Reference:** Spec Deliverable 5. Code references from scoring.py, engine.py, patterns.py. Mermaid for diagrams.

- [ ] **Step 1: Executive Summary (Section 1)**

Problem, solution, design decision (no ML — conscious trade-off), demonstrated results (505 articles, 38 final corpus, 7.5%).

- [ ] **Step 2: System Architecture (Section 2)**

Layer diagram (Mermaid: UI -> Controller -> Core -> I/O), module map table (module/file/lines/responsibility), technology stack with justifications, design decisions expanded from decision-log.

- [ ] **Step 3: Pipeline (Section 3)**

End-to-end Mermaid flowchart with annotations (fail-fast, anti-terms, uplift points). Input stage (formats, auto-detection, encoding). Pre-processing (normalization, LRU cache). Processing (article loop, fail-fast, error policies). Output (XLSX, CSV, protocol snapshot, academic ZIP, SHA-256 hashes).

- [ ] **Step 4: Algorithm (Section 4)**

Term matching engine (exact, wildcards, proximity, compound splitting). T0 pre-screening (short-circuit). Block evaluation (explicit score formula). Decision thresholds tables (approval + flagging per level, why level 5 has no approval threshold). Final decision logic (Mermaid decision tree for special/strict/k_of_n). Fail-fast justification with 49% measured economy.

- [ ] **Step 5: Commit**

```bash
git add docs/TECHNICAL_REPORT.md
git commit -m "docs: add Technical Report sections 1-4 (architecture, pipeline, algorithm)"
```

---

### Task 17: Write TECHNICAL_REPORT.md — Sections 5-8 + Appendices

**Files:**
- Modify: `docs/TECHNICAL_REPORT.md`

- [ ] **Step 1: Configuration System (Section 5)**

JSON Schema reference, global parameters table (name/type/default/range/effect), domain block structure, terms CSV format and merge behavior.

- [ ] **Step 2: Reproducibility and Audit Trail (Section 6)**

Protocol snapshot v2.1 fields, determinism guarantees (no external state, no randomness), academic package export contents.

- [ ] **Step 3: Quality Assurance (Section 7)**

Test suite summary (files/counts/coverage), stress testing (15 scenarios from log), type safety (pyright standard, zero errors), code quality (ruff, hookify 9 rules).

- [ ] **Step 4: Interfaces (Section 8)**

CLI: 10 commands with flags. TUI: 10 screens with workflows, threading model. i18n: translation system, fallback chain, 3 languages.

- [ ] **Step 5: Appendices**

A: Default configuration reference (full default_config.json annotated).
B: Module API reference (table of all public functions from docstrings).
C: Full-page decision tree (Mermaid).

- [ ] **Step 6: Commit**

```bash
git add docs/TECHNICAL_REPORT.md
git commit -m "docs: complete Technical Report (config, reproducibility, QA, interfaces, appendices)"
```

---

## Final: Coverage Report + Validation

### Task 18: Final validation

- [ ] **Step 1: Run full test suite with coverage report**

Run: `pytest tests/ -v --cov=src/fastslr --cov-report=term-missing --cov-report=html`
Expected: Global >=80%, scoring.py >=90%.

- [ ] **Step 2: Run pyright on entire codebase**

Run: `pyright src/fastslr/`
Expected: 0 errors.

- [ ] **Step 3: Run ruff**

Run: `ruff check src/ tests/ && ruff format --check src/ tests/`
Expected: 0 issues.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: final validation -- all tests pass, coverage >=80%, pyright clean"
```
