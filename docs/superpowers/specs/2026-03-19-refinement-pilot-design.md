# FastSLR v3.0.0 — Refinement for Pilot Registration

**Date:** 2026-03-19
**Status:** Approved
**Goal:** Prepare FastSLR for simultaneous academic publication and software registration (PyPI + Zenodo DOI)

## Context

FastSLR v3.0.0 is a deterministic, rule-based SLR triage engine — 100% mechanical, zero AI/ML dependencies. This is a conscious design decision: the system prioritizes transparency, determinism, traceability and reproducibility over ML-based classification. Borderline errors are an accepted trade-off, mitigated by the FLAGGED mechanism. Fail-fast is core methodology: all researcher-defined domain blocks are mandatory by definition.

The system has been validated on a real RSL (505 articles → 38 final corpus, 7.5% inclusion rate) and is ready for refinement toward pilot registration.

## Scope

Three refinement axes, executed in the "Interleaved" approach:

1. **JSON Schema validation** (foundation — unblocks tests and docs)
2. **Complete test suite** (scoring, config, io, coverage, E2E integration; target ≥80% coverage)
3. **Documentation** (docstrings on public functions + operational README + separate Technical Report)

## Approach: Interleaved

```
Schema JSON → (Tests + Docstrings in parallel) → README → Technical Report
```

Schema is the foundation — defines the formal contract of configuration. Once it exists, tests can validate configs programmatically and docstrings can reference the schema. README and Technical Report come last as consolidation.

---

## Deliverable 1: JSON Schema (`config_schema.json`)

### Location
`src/fastslr/core/config_schema.json`

### Standard
JSON Schema Draft 2020-12, validated via `jsonschema` Python library.

### What it covers
- `global` — all global parameters (thresholds, weights, policies, noise profile, fail-fast, uplift factor, error policy, etc.)
- `t0` — global anti-terms (anti_exclude and anti_flag arrays of strings)
- `_domain_blocks[]` — array of blocks, each with: name, positives (with level, section_scope, is_regex), anti_exclude, anti_flag
- `normalization` — optional rules (abbreviations, compounds, symbols)

### Integration point
`config.py::load_config()` calls `jsonschema.validate()` before any processing. Validation errors produce friendly, translated (i18n) messages indicating the exact field, the error, and the expected value.

### Dependency
Add `jsonschema>=4.20` to `[project.dependencies]` in pyproject.toml.

---

## Deliverable 2: Complete Test Suite

### New test files

| File | Module under test | Focus |
|---|---|---|
| `tests/test_scoring.py` | `scoring.py` (~475 lines) | `evaluate_block`, `make_final_decision`, `find_positive_terms`, `evaluate_t0_conditional`, threshold edge cases, uplift, anti-terms, noise filtering, all 3 decision policies (special/strict/k_of_n), special approval rule |
| `tests/test_config.py` | `config.py` + schema | Validation via jsonschema, invalid configs (wrong types, missing fields, negative ranges), terms CSV parsing, legacy PT field names |
| `tests/test_io.py` | `io.py` + `adapters.py` | Format detection (Zotero/Scopus/WOS), encoding detection, XLSX/CSV export, protocol snapshot generation, varied separators |
| `tests/test_coverage_analysis.py` | `coverage.py` | Dead term detection, broad term detection, section distribution |
| `tests/test_integration.py` | Full pipeline E2E | Multiple synthetic configs simulating different research areas, determinism verification |

### Existing test files (preserved as-is)
- `test_engine.py` (12 tests)
- `test_patterns.py` (16 tests)
- `test_normalization.py` (16 tests)
- `test_compliance.py` (7 tests)

### Integration test mechanics

Each E2E scenario consists of 3 artifacts in `tests/fixtures/`:

1. **Config JSON** — minimal but functional config with 2-3 blocks, ~5-10 terms per block, standard thresholds
2. **Articles CSV** — hand-written synthetic articles (10-15 per scenario) with controlled titles and abstracts, each designed to trigger a specific code path (approval, rejection, flag, fail-fast, uplift, anti-term exclusion, etc.)
3. **Expected results** — asserted within the test code itself, after manual verification by running the pipeline once and confirming each decision makes sense given terms and thresholds

**Important:** These test configs are internal test artifacts only. They are NOT templates or profiles offered to users. The tool remains 100% customizable — researchers define everything from scratch.

**Scenarios:**
- Scenario A: 3 blocks, standard thresholds, mix of approved/rejected/flagged articles
- Scenario B: 2 blocks, strict policy, fail-fast verification
- Scenario C: 3 blocks with T0 anti-terms, k_of_n policy
- Scenario D: Subset of real O&G protocol terms (from v12) for regression

**Determinism test:** Each scenario runs twice and asserts identical output (same input + same config = same result, always).

### Coverage target
- Global: ≥80%
- `scoring.py`: ≥90%
- Reporting via `pytest-cov` (add to dev dependencies)

### Principles
- Every test is deterministic and independent (no shared state)
- Reusable fixtures in `conftest.py` (minimal configs, synthetic articles, example blocks)
- No mocking of core logic — tests exercise real code paths

---

## Deliverable 3: Docstrings

### Scope
All public functions and classes in core + app modules. Private functions (`_prefix`) only get docstrings if logic is non-obvious.

### Format
Google style docstrings:

```python
def evaluate_block(article_text: dict, block: dict, global_params: GlobalParams) -> BlockEvaluation:
    """Evaluate a single domain block against an article.

    Searches for positive and anti terms in title, abstract and manual_tags,
    computes weighted scores per section, and applies threshold-based
    decision logic.

    Args:
        article_text: Normalized text sections {"title": ..., "abstract": ..., "manual_tags": ...}.
        block: Domain block configuration with positives, anti_exclude, anti_flag.
        global_params: Global parameters (thresholds, weights, noise profile).

    Returns:
        BlockEvaluation with status (APPROVED/FLAGGED/REJECTED), scores,
        matched terms and detailed reason.
    """
```

### Priority order
1. `scoring.py` — evaluate_block, make_final_decision, find_positive_terms, evaluate_t0_conditional
2. `engine.py` — process_articles, collect_statistics
3. `config.py` — load_config, parse_terms_csv, load_global_params
4. `models.py` — all dataclasses (BlockEvaluation, TermMatch, GlobalParams, etc.)
5. `patterns.py` — compile_pattern, compile_proximity_pattern, precompile_patterns
6. `io.py` — load_csv_safe, export_results, generate_protocol_snapshot
7. `controller.py` — all public orchestration functions

---

## Deliverable 4: README.md (Operational Guide)

### Mission
A researcher must be able to install, configure, run and interpret results reading ONLY the README.

### Language
English (international audience, PyPI standard).

### Structure

```
# FastSLR — Deterministic SLR Triage Engine

## Overview
  - What it is, who it's for, philosophy (deterministic, transparent, reproducible)
  - Badges: version, Python, license, tests

## Quick Start
  - Installation (pip install)
  - First run in 3 commands (new-project → edit config → run)

## Concepts
  - Domain blocks
  - Relevance levels (1-5) and why they exist
  - Anti-terms (exclusion vs flagging)
  - Sections and weights (title, abstract, keywords)
  - Final decisions (APPROVED/FLAGGED/REJECTED)
  - Fail-fast and why it's core

## Configuration Guide
  - config.json structure (referencing schema)
  - Global parameters (each one explained)
  - How to define blocks, terms and anti-terms
  - Terms CSV as alternative to JSON
  - Difficulty presets (binary/simple/standard)
  - Annotated config examples

## CLI Reference
  - All 10 commands with usage examples
  - Global flags (--lang, --output, --quiet)

## TUI Guide
  - Description of each screen
  - Keyboard shortcuts

## Understanding Results
  - How to read the output XLSX
  - Per-block columns (Score, Status, Highlights)
  - Final decision and reason
  - Protocol snapshot and reproducibility hash

## Academic Use
  - How to cite
  - How to report parameters in a paper's methods section
  - Academic package export (ZIP)

## i18n
  - Supported languages
  - How to switch

## Development
  - Dev setup (clone, install dev deps)
  - Running tests (pytest + coverage)
  - Linting (ruff + pyright)

## License
```

---

## Deliverable 5: Technical Report (`docs/TECHNICAL_REPORT.md`)

### Mission
Complete technical-executive reference describing the system internally — architecture, algorithm, pipeline, modules. Target audience: thesis committee, peer reviewers, developers, anyone who needs to understand "how and why".

### Structure

```
# FastSLR v3.0.0 — Technical Report

## 1. Executive Summary
  - Problem: manual SLR screening is slow, irreproducible and subjective
  - Solution: deterministic engine based on configurable pattern matching
  - Design decision: no AI/ML — conscious trade-off for transparency,
    determinism and full reproducibility
  - Demonstrated results: 505 articles → 38 final corpus (7.5%)

## 2. System Architecture
  ### 2.1 Layer Diagram
    - Mermaid diagram: UI → Controller → Core → I/O
    - Separation principle: core is UI-agnostic, controller is sole bridge
  ### 2.2 Module Map
    - Table: module, file, lines, responsibility
    - Inter-module dependency diagram (Mermaid)
  ### 2.3 Technology Stack
    - Python ≥3.10 and justification
    - Each dependency: what it does, why chosen, alternatives discarded
  ### 2.4 Design Decisions
    - Expanded from existing decision-log with full rationale

## 3. Pipeline
  ### 3.1 End-to-End Flowchart
    - Complete Mermaid flowchart (Input → Output)
    - Annotations showing where each mechanism acts (fail-fast, anti-terms, uplift)
  ### 3.2 Input Stage
    - Accepted formats (CSV, XLSX)
    - Bibliographic format auto-detection (Zotero, Scopus, WOS)
    - Encoding and separator detection
    - Automatic column mapping
  ### 3.3 Pre-processing
    - Deterministic normalization (abbreviations, symbols, compounds)
    - LRU cache and performance
  ### 3.4 Processing Stage
    - Article loop, fail-fast, error policies
  ### 3.5 Output Stage
    - XLSX, CSV, protocol snapshot, academic package
    - SHA-256 hash of config and input

## 4. Algorithm
  ### 4.1 Term Matching Engine
    - Exact matching (word boundaries + regex)
    - Wildcards (industr* → \w*)
    - Proximity detection (compound terms)
    - Compound splitting (and/&/or//)
    - Pattern compilation and caching
  ### 4.2 T0 Global Pre-screening
    - Purpose and when to use
    - Global anti-terms (exclusion vs flagging)
    - Short-circuit logic
  ### 4.3 Block Evaluation
    - Positive term search by section
    - Explicit score formula:
      section_score = Σ(level_scores[l]) for l ∈ unique_levels, capped at 30
      weighted = section_score × section_weight
      raw_score = Σ(weighted) for all sections
    - No-tags uplift (×1.17) — when and why
    - Anti-exclusion → immediate REJECTED
    - Anti-flag → downgrade APPROVED→FLAGGED
    - Noise filtering (3 configurable parameters)
  ### 4.4 Decision Thresholds
    - Complete tables: approval and flagging per level
    - Why level 5 has no approval threshold
    - How thresholds interact with best_level
  ### 4.5 Final Decision Logic
    - Complete decision tree (Mermaid flowchart)
    - "special" policy (default v11): priority rules 1-5
    - "strict" policy: AND logic
    - "k_of_n" policy: parametric logic
    - Special approval rule (1 flagged + others ≥40)
  ### 4.6 Fail-Fast
    - Methodological justification
    - Measured impact: ~49% processing economy (real data)

## 5. Configuration System
  ### 5.1 JSON Schema
    - Formal structure (reference to schema file)
    - Automatic validation and error messages
  ### 5.2 Global Parameters
    - Each parameter: name, type, default, valid range, effect
  ### 5.3 Domain Blocks
    - Block structure (positives, anti_exclude, anti_flag)
    - Levels and section_scope
  ### 5.4 Terms CSV
    - Format, columns, merge behavior with JSON

## 6. Reproducibility & Audit Trail
  ### 6.1 Protocol Snapshot (v2.1)
    - Fields: version, timestamp, execution_id, config_hash, input_hash
    - How to reproduce a run
  ### 6.2 Determinism Guarantees
    - No external state, no randomness, no order dependency
    - Same input + same config = same output, always
  ### 6.3 Academic Package Export
    - ZIP contents: results, config, protocol, metadata

## 7. Quality Assurance
  ### 7.1 Test Suite
    - Organization, coverage, test types
  ### 7.2 Stress Testing
    - 15 scenarios, findings and fixes
  ### 7.3 Type Safety
    - pyright standard mode, zero errors
  ### 7.4 Code Quality
    - ruff (format + lint), hookify rules

## 8. Interfaces
  ### 8.1 CLI
    - Commands, flags, examples
  ### 8.2 TUI
    - 10 screens, workflows, threading model
  ### 8.3 i18n
    - Translation system, fallback chain, supported languages

## Appendix A: Default Configuration Reference
## Appendix B: Complete Module API Reference
## Appendix C: Decision Tree (full-page diagram)
```

---

## Implementation Order

| Phase | Deliverable | Depends on |
|---|---|---|
| **Phase 8** | JSON Schema (`config_schema.json`) + integration in `config.py` | — |
| **Phase 9a** | Test suite (test_scoring, test_config, test_io, test_coverage_analysis, test_integration) + fixtures | Phase 8 (schema needed for test_config) |
| **Phase 9b** | Docstrings on all public functions (parallel with 9a) | — |
| **Phase 10** | README.md (operational guide) | Phases 9a+9b (documents validated tool) |
| **Phase 11** | TECHNICAL_REPORT.md (executive-technical reference) | Phases 9a+9b (references test suite, docstrings) |

## Files Created/Modified

### New files
- `src/fastslr/core/config_schema.json` — JSON Schema definition
- `tests/test_scoring.py` — Scoring module test suite
- `tests/test_config.py` — Config + schema validation tests
- `tests/test_io.py` — I/O and adapter tests
- `tests/test_coverage_analysis.py` — Coverage analysis tests
- `tests/test_integration.py` — E2E pipeline tests
- `tests/fixtures/scenario_a_config.json` — Test fixture
- `tests/fixtures/scenario_a_articles.csv` — Test fixture
- `tests/fixtures/scenario_b_config.json` — Test fixture
- `tests/fixtures/scenario_b_articles.csv` — Test fixture
- `tests/fixtures/scenario_c_config.json` — Test fixture
- `tests/fixtures/scenario_c_articles.csv` — Test fixture
- `tests/fixtures/scenario_d_config.json` — Test fixture (O&G subset)
- `tests/fixtures/scenario_d_articles.csv` — Test fixture (O&G subset)
- `docs/TECHNICAL_REPORT.md` — Executive-technical reference
- `README.md` — Operational guide (rewrite)

### Modified files
- `src/fastslr/core/config.py` — Add jsonschema validation in load_config()
- `pyproject.toml` — Add jsonschema>=4.20 to dependencies, pytest-cov to dev deps
- `tests/conftest.py` — Add shared fixtures for new test files
- All public functions in core/ and app/ — Add Google-style docstrings

## What is NOT in scope
- No ML/NLP components (by design)
- No pre-built term profiles or templates for specific research areas
- No changes to the core algorithm or decision logic
- No changes to fail-fast behavior
- No new CLI/TUI features
