# FastSLR v3.0.0 — Design Document

## Overview

FastSLR v3.0.0 is a deterministic, rule-based Systematic Literature Review (SLR)
triage engine. 100% mechanical — zero AI dependencies. Designed for international
researchers to automate the screening phase of SLRs.

## Architecture: Hybrid (Motor v2.0 + New Shell)

The v2.0 engine (scoring, patterns, normalization) is preserved intact as an internal
library (`core/`). A new application layer is built on top (CLI + TUI + i18n).

```
src/fastslr/
├── core/                  ← Engine v2.0 (untouched)
│   ├── engine.py
│   ├── scoring.py
│   ├── models.py
│   ├── config.py
│   ├── patterns.py
│   ├── normalization.py
│   ├── io.py
│   ├── adapters.py
│   ├── coverage.py
│   ├── presets.py
│   ├── constants.py
│   └── default_config.json
├── app/                   ← New shell
│   ├── cli.py             ← CLI entry point (typer)
│   ├── tui.py             ← TUI entry point (textual)
│   ├── controller.py      ← Orchestration logic
│   ├── project.py         ← Project wizard
│   ├── explorer.py        ← Results explorer
│   ├── diff.py            ← Run comparison
│   └── profiles.py        ← Profile save/load
├── i18n/                  ← Internationalization
│   ├── __init__.py
│   └── locales/
│       ├── en/
│       ├── pt_BR/
│       └── es/
├── __init__.py
└── __main__.py
```

## Key Decisions

### Interaction Model
Both batch CLI and interactive TUI. Researcher chooses.

### Language
English with i18n support (gettext). en + pt_BR complete, es structure-ready.

### UX Principle
TUI designed for non-programmers: no jargon, contextual help, breadcrumbs,
friendly errors, smart defaults, visible options.

### Dependencies
- pandas >=2.0 (data manipulation)
- openpyxl >=3.1 (XLSX I/O)
- typer >=0.12 (CLI)
- rich >=13.0 (formatted output)
- textual >=0.80 (TUI framework)
- Optional: chardet >=5.0 (encoding detection)

### Distribution
Cross-platform via `pip install fastslr`. Python >=3.10. License: MIT.

### What is NOT translated (for reproducibility)
- Output column names (Final_Decision, Status_T1A)
- Config JSON keys (approval_thresholds, level_scores)
- Decision values (APPROVED_FINAL, REJECTED_FINAL)

## CLI Commands

```
fastslr run <input> --config <config.json>
fastslr new-project
fastslr coverage <input> --config <config.json>
fastslr diff <result1> <result2>
fastslr preview <input> --config <config.json> --sample 50
fastslr export <result> --format academic
fastslr profile save <name>
fastslr profile load <name>
fastslr profile list
fastslr version
fastslr tui
```

Global flags: --lang, --verbose, --quiet, --output, --format

## TUI Features (10 screens)

1. New Project (wizard, 5 steps, contextual help)
2. Load Profile
3. Edit Configuration (tree navigation, inline edit, live validation)
4. Browse Terms (filterable table)
5. Run Triage (file selection, progress bar, summary)
6. Results Explorer (paginated table, filters, article detail)
7. Coverage Analysis (unmatched terms, distribution)
8. Compare Runs / Diff
9. Export Academic Package (ZIP: protocol, config hash, stats, results)
10. Settings & Language

## Controller API

```python
create_project(name, description, blocks, preset) → ProjectConfig
load_project(path) → ProjectConfig
save_profile(name, config) → Path
load_profile(name) → ProjectConfig
list_profiles() → list[ProfileInfo]
validate_config(config) → list[ValidationIssue]
preview_triage(input_path, config, sample_size) → PreviewResult
run_triage(input_path, config, on_progress) → TriageResult
browse_terms(config, filters) → TermsView
analyze_coverage(result, config) → CoverageReport
diff_results(result_a, result_b) → DiffReport
explore_results(result, filters) → ResultsView
export_academic(result, config) → AcademicPackage
```

## Implementation Phases

| Phase | Focus | Deliverable |
|-------|-------|-------------|
| 1 | Cleanup & restructure | Engine in new structure, AI-free |
| 2 | CLI (typer) | `fastslr run` works |
| 3 | i18n (gettext) | Messages in en/pt_BR/es |
| 4 | TUI (textual) | `fastslr tui` complete |
| 5 | Publication polish | Publishable pip package |
| 6 | Quality & typing | Pyright strict + ruff clean |
| 7 | Stress test & hardening | Resilient + auditable log |

## Files Removed (AI)

- ai_pipeline.py
- ai_pipeline_tui.py
- .pipeline/ (entire directory)
- docs/plans/2026-02-27-stress-test-*.md

## Files Removed (legacy/obsolete)

- legacy/ (entire directory)
- bat_ui.py
- launcher_entrypoint.py
- launcher_profile_load.py
- launcher_profile_save.py
- diff.py (replaced by app/diff.py)

## Only Engine Change

engine.py: replace ProgressBar import with on_progress callback.
