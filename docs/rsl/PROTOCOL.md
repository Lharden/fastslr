# RSL Triage Protocol (Universal Engine)

## Purpose

This protocol defines the **current universal workflow** for deterministic,
rule-based article triage.

The engine supports:

- Dynamic thematic blocks (N blocks, user-defined)
- Configurable relevance levels (2 to 5)
- Configurable decision policies (`special`, `strict`, `k_of_n`)
- Optional anti-noise profiles (`relaxed`, `balanced`, `strict`)
- Optional pilot sampling mode
- Full run reproducibility with hashed inputs/config and protocol snapshot export

## Legacy Protocol

The original dissertation-specific protocol (fixed `T1A/T1B/T1C`) is preserved at:

- `src/rsl_triage/legacy/PROTOCOL.md`

Use that legacy protocol only for historical reproduction of old runs.

For a practical regression checklist (baseline vs replay), see:

- `docs/LEGACY_REGRESSION_PROTOCOL.md`

For a presentation-oriented live demo script of the Windows launcher, see:

- `docs/LIVE_DEMO_TRIAGEM_BAT.md`
- `docs/LIVE_DEMO_TRIAGEM_BAT_VARIACOES.md`

## Current Method (High Level)

1. Load corpus CSV, config JSON, terms CSV.
2. Parse terms and infer dynamic block structure.
3. Compile deterministic matching patterns.
4. Evaluate each article through configured blocks and decision policy.
5. Export results, statistics, protocol snapshot, and optional academic artifacts.

## Reproducibility Artifacts

Each run can generate:

- `*_protocol.json`
- `*_stats.json`
- `*_config.json`
- optional `*_academic.md`, `*_bundle.json`, `*_appendix_pack.zip`

These artifacts are the source of truth for auditing and replication.
