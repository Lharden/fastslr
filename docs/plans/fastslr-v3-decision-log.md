# FastSLR v3.0.0 — Decision Log

## Decision 1: Remove AI completely
- **Decided**: Remove all AI dependencies (ai_pipeline, .pipeline/, prompts, schemas)
- **Alternatives**: Keep as optional tools, move to separate repo
- **Reason**: System must be 100% mechanical for academic publication. Git preserves history.

## Decision 2: Interaction model — Batch + TUI
- **Decided**: Both CLI batch mode and interactive TUI
- **Alternatives**: Batch only (like legacy), TUI only
- **Reason**: Researchers have different preferences. Batch for reproducibility/scripting, TUI for guided use.

## Decision 3: Hybrid architecture (Motor v2.0 + New Shell)
- **Decided**: Preserve v2.0 engine untouched in core/, build new app layer
- **Alternatives**: Incremental refactor, full rewrite
- **Reason**: Engine is tested and correct. Risk is in the shell, not the algorithm. Clear separation enables independent evolution.

## Decision 4: English with i18n (gettext)
- **Decided**: Interface in English with gettext i18n. Output data stays English.
- **Alternatives**: English only, full i18n including output
- **Reason**: International audience needs translated interface. Output in English ensures reproducibility across locales.

## Decision 5: All 10 TUI features
- **Decided**: Implement all 10 proposed TUI screens
- **Alternatives**: Subset / phased feature release
- **Reason**: Complete tool for publication. Each feature serves a distinct research workflow need.

## Decision 6: Cross-platform via pip
- **Decided**: pip install fastslr, Python >=3.10, Windows/macOS/Linux
- **Alternatives**: Windows-only (like legacy .bat), conda, Docker
- **Reason**: Maximum accessibility for researchers. pip is universal in academia.

## Decision 7: Pragmatic dependencies
- **Decided**: pandas, openpyxl, typer, rich, textual
- **Alternatives**: Minimal (stdlib only), heavy (Django/Flask-based)
- **Reason**: Established libraries, reasonable install size, good cross-platform support.

## Decision 8: MIT License
- **Decided**: MIT
- **Alternatives**: Apache 2.0, GPL v3
- **Reason**: Most permissive, standard in academic tools, minimizes adoption barriers.

## Decision 9: UX for non-programmers
- **Decided**: TUI designed for researchers, not developers. No jargon, contextual help, friendly errors.
- **Alternatives**: Developer-focused CLI
- **Reason**: Target users are researchers from diverse fields, most are not programmers.

## Decision 10: Version 3.0.0
- **Decided**: New major version (v3.0.0)
- **Alternatives**: v2.1, v2.5
- **Reason**: Breaking changes in structure, removed AI layer, new shell. Warrants major bump.

## Decision 11: Pyright strict + ruff + stress tests
- **Decided**: Full type checking, code quality enforcement, and adversarial testing with auditable log
- **Alternatives**: Basic testing only
- **Reason**: Academic publication demands robustness. Stress test log documents resilience.

## Decision 12: Remove legacy/ directory
- **Decided**: Delete frozen v1.0.x legacy code
- **Alternatives**: Keep as reference
- **Reason**: Superseded by universal v2.0→v3.0 engine. Git history preserves it.
