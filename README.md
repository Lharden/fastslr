# FastSLR -- Deterministic SLR Triage Engine

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-3.0.0-brightgreen.svg)](https://pypi.org/project/fastslr/)

**FastSLR** automates the title-and-abstract screening stage of Systematic Literature Reviews. Given a corpus of articles (CSV or XLSX) and a configuration file, it deterministically classifies every article as **APPROVED**, **FLAGGED**, or **REJECTED** -- with zero AI/ML involved.

**Who it is for:** Researchers conducting systematic or scoping reviews who need transparent, reproducible screening.

**Key properties:**

- **Deterministic** -- same input + same config = same output, always.
- **Transparent** -- every decision traced to specific term matches and scores.
- **Reproducible** -- SHA-256 hashes for full audit trails.
- **No AI/ML** -- all decisions are rule-based. No black boxes.

---

## Quick Start

### 1. Install

```bash
pip install fastslr
```

### 2. Create a project

```bash
fastslr new-project my_review --blocks "CTX,TECH,METHOD" --preset standard
```

This creates a `my_review/` directory with:
- `config.json` -- triage parameters (edit this)
- `terms.csv` -- term definitions template (fill this in)

### 3. Add your terms

Edit `terms.csv` with your search terms:

```csv
block,kind,term,level,section_scope,is_regex
CTX,pos,machine learning,1,any,0
CTX,pos,deep learning,1,any,0
CTX,pos,neural network,2,any,0
CTX,anti,survey,,,0
TECH,pos,convolutional,1,any,0
TECH,pos,transformer,2,any,0
METHOD,pos,cross-validation,1,any,0
GLOBAL,anti,retracted,,,0
```

| Column | Required | Description |
|--------|----------|-------------|
| `block` | Yes | Block name (e.g., `CTX`, `TECH`). Use `GLOBAL` for cross-block anti-terms. |
| `kind` | Yes | `pos` (positive), `anti` (exclusion), `flag` (flagging). |
| `term` | Yes | The search term string. |
| `level` | For `pos` | Relevance level (1-5). |
| `section_scope` | No | `title`, `abstract`, `manual_tags`, or `any` (default). |
| `is_regex` | No | `1` for regex, `0` for literal (default). |

### 4. Run triage

```bash
fastslr run articles.csv --config my_review/config.json --terms my_review/terms.csv
```

Results are saved as an XLSX file in the output directory.

### 5. Or use the interactive TUI

```bash
fastslr tui
```

The TUI provides a guided menu-driven interface for all operations -- no command-line knowledge required.

---

## Core Concepts

### Domain Blocks

Domain blocks are researcher-defined thematic areas. For example, a review about "AI in Healthcare" might define two blocks: `AI` and `HEALTH`. **All blocks are mandatory** -- an article must pass every block to be approved.

### Relevance Levels

Terms are assigned a priority level from 1 (most relevant) to 5 (least relevant). Higher-priority terms contribute more points.

| Preset     | Levels | Use case                                    |
|------------|--------|---------------------------------------------|
| `binary`   | 1      | Quick include/exclude screening             |
| `simple`   | 3      | Moderate granularity                        |
| `standard` | 5      | Full granularity (recommended)              |

### Anti-terms

- **Exclusion** (`anti`): Immediately reject the article from that block.
- **Flagging** (`flag`): Downgrade to FLAGGED for manual review.

### Sections and Weights

| Section       | Default Weight | Description                              |
|---------------|----------------|------------------------------------------|
| `title`       | 2.0x           | Article title (highest signal)           |
| `abstract`    | 1.0x           | Article abstract (baseline)              |
| `manual_tags` | 1.5x           | Author keywords or manual tags           |

### Final Decisions

| Decision          | Meaning                                         |
|-------------------|------------------------------------------------|
| `APPROVED_FINAL`  | Passed all blocks -- include in full-text review |
| `FLAGGED_FINAL`   | Needs manual review                             |
| `REJECTED_FINAL`  | Failed one or more blocks -- exclude             |

### Fail-Fast

When enabled (default), if any block rejects an article, remaining blocks are skipped. This reflects the logical AND requirement and significantly speeds up processing.

---

## CLI Reference

All commands support `--lang` / `-l` for language and `--help` for usage details.

### `fastslr run`

Run the full triage on an articles file.

```bash
fastslr run articles.csv --config config.json --terms terms.csv
fastslr run articles.csv -c config.json -t terms.csv -o results/ -q
```

| Flag | Short | Description |
|------|-------|-------------|
| `--config` | `-c` | Path to config.json (required). |
| `--terms` | `-t` | Path to terms CSV (optional). |
| `--output` | `-o` | Output directory (default: current dir). |
| `--quiet` | `-q` | Suppress progress output. |
| `--lang` | `-l` | Interface language (`en`, `pt_BR`, `es`). |

### `fastslr preview`

Preview results on a random sample without writing files.

```bash
fastslr preview articles.csv -c config.json -s 50
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--config` | `-c` | -- | Config file (required). |
| `--terms` | `-t` | -- | Terms CSV (optional). |
| `--sample` | `-s` | `50` | Number of articles to sample. |

### `fastslr coverage`

Analyze which terms matched and how often.

```bash
fastslr coverage articles.csv -c config.json -o coverage_report.csv
```

### `fastslr diff`

Compare two result files to see changed decisions.

```bash
fastslr diff results_v1.xlsx results_v2.xlsx
```

### `fastslr new-project`

Scaffold a new project with config and terms templates.

```bash
fastslr new-project my_review --blocks "CTX,TECH,METHOD" --preset standard
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--blocks` | `-b` | -- | Comma-separated block names (required). |
| `--preset` | `-p` | `standard` | `binary`, `simple`, or `standard`. |
| `--output` | `-o` | current dir | Output directory. |

### `fastslr export`

Generate an academic package (ZIP) for publication.

```bash
fastslr export results.xlsx -c config.json
```

### `fastslr terms`

Browse configured terms with optional filtering.

```bash
fastslr terms -c config.json -t terms.csv --block CTX --kind pos
```

### `fastslr profile`

Manage reusable configuration profiles.

```bash
fastslr profile save my_protocol -c config.json --desc "Initial protocol"
fastslr profile list
fastslr profile load my_protocol -o config.json
```

### `fastslr tui`

Launch the interactive terminal interface.

```bash
fastslr tui
```

### `fastslr version`

Show the installed version.

---

## TUI Guide

Launch with `fastslr tui`. Navigate with number keys:

| Key | Screen | Description |
|-----|--------|-------------|
| `1` | New Project | Guided creation wizard with preset selection. |
| `2` | Load Profile | Browse saved configuration profiles. |
| `3` | Edit Configuration | Built-in JSON editor for config.json. |
| `4` | Browse Terms | Filterable table of all search terms. |
| `5` | Run Triage | Execute with progress bar and live stats. |
| `6` | Results Explorer | Browse results filtered by decision. |
| `7` | Coverage Analysis | Check which terms matched. |
| `8` | Compare Runs | Diff two result files. |
| `9` | Export Package | Generate publication-ready ZIP. |
| `0` | Settings & Language | Change interface language. |

Press `Escape` to go back, `Q` to quit.

---

## Configuration Guide

### Config File Structure

```json
{
  "global": { ... },
  "fields": { ... },
  "output": { ... },
  "encoding": "utf-8-sig",
  "sep": ";"
}
```

### Key Global Parameters

#### Decision & Policy

| Parameter | Default | Description |
|-----------|---------|-------------|
| `DECISION_POLICY` | `"special"` | `"special"`, `"strict"`, or `"k_of_n"`. |
| `FAIL_FAST_GLOBAL` | `true` | Stop after first block rejection. |
| `ENABLE_SPECIAL_APPROVAL_RULE` | `true` | Allow high-score override when 1 block is flagged. |
| `SPECIAL_APPROVAL_THRESHOLD` | `40.0` | Score for the special approval rule. |

#### Scoring

| Parameter | Default | Description |
|-----------|---------|-------------|
| `PONTUACAO_NIVEIS` | `{1:10, 2:8, 3:6, 4:4, 5:2}` | Points per relevance level. |
| `LIMITES_APROVADO` | `{1:10, 2:12, 3:18, 4:22, 5:null}` | Minimum score for approval. `null` = cannot approve alone. |
| `LIMITES_SINALIZADO` | `{1:6, 2:6, 3:6, 4:7, 5:12}` | Minimum score for flagging. |
| `WEIGHTS` | `{title:2.0, abstract:1.0, manual_tags:1.5}` | Section weight multipliers. |
| `MAX_SECTION_SCORE` | `30` | Score cap per section. |
| `NO_TAGS_UPLIFT` | `1.17` | Multiplier when tags are empty (>= 1.0). |

#### Matching

| Parameter | Default | Description |
|-----------|---------|-------------|
| `ENABLE_PROXIMITY_DETECTION` | `true` | Multi-word proximity matching. |
| `MAX_GAP_BETWEEN_TERMS` | `2` | Max tokens between words in proximity match. |
| `NOISE_PROFILE` | `"relaxed"` | `"relaxed"`, `"balanced"`, or `"strict"`. |

### Field Mappings

Map your CSV columns to FastSLR's expected fields:

```json
{
  "fields": {
    "id": "key",
    "id_output": "ID",
    "title": "title",
    "abstract": "abstract",
    "manual_tags": "manual_tags"
  }
}
```

FastSLR also auto-detects Zotero, Scopus, and Web of Science column layouts.

### Output Settings

```json
{
  "output": {
    "csv": false,
    "xlsx": true,
    "xlsx_sheet_name": "resultados",
    "academic_package": true
  }
}
```

### Full Config Example

```json
{
  "global": {
    "DECISION_POLICY": "special",
    "ENABLE_SPECIAL_APPROVAL_RULE": true,
    "SPECIAL_APPROVAL_THRESHOLD": 40.0,
    "FAIL_FAST_GLOBAL": true,
    "NO_TAGS_UPLIFT": 1.17,
    "MAX_SECTION_SCORE": 30,
    "MAX_GAP_BETWEEN_TERMS": 2,
    "ENABLE_PROXIMITY_DETECTION": true,
    "NOISE_PROFILE": "relaxed",
    "MIN_UNIQUE_TERMS_FOR_APPROVAL": 1,
    "ERROR_POLICY": "flag",
    "MAX_ERROR_RATE": 0.05,
    "PONTUACAO_NIVEIS": { "1": 10, "2": 8, "3": 6, "4": 4, "5": 2 },
    "LIMITES_APROVADO": { "1": 10, "2": 12, "3": 18, "4": 22, "5": null },
    "LIMITES_SINALIZADO": { "1": 6, "2": 6, "3": 6, "4": 7, "5": 12 },
    "WEIGHTS": { "title": 2.0, "abstract": 1.0, "manual_tags": 1.5 },
    "BLOCK_ORDER": ["CTX", "TECH", "METHOD"]
  },
  "fields": {
    "id": "key",
    "id_output": "ID",
    "title": "title",
    "abstract": "abstract",
    "manual_tags": "manual_tags"
  },
  "output": {
    "csv": false,
    "xlsx": true,
    "xlsx_sheet_name": "resultados",
    "academic_package": true
  },
  "encoding": "utf-8-sig",
  "sep": ";"
}
```

---

## Understanding Results

### Output XLSX

Each article row contains:

- **Per-block columns** (`RawScore`, `FinalScore`, `BestLevel`, `Status`, `Highlights`, `AntiHighlights`, `Flags`)
- **`Final_Decision`** -- `APPROVED_FINAL`, `FLAGGED_FINAL`, or `REJECTED_FINAL`
- **`Final_Reason`** -- Human-readable explanation

### Protocol Snapshot

Each run generates a `protocol.json` with SHA-256 hashes of the config and input file. Two runs with the same hashes are guaranteed to produce identical results.

---

## Language Support

| Language | Code | Usage |
|----------|------|-------|
| English | `en` | Default |
| Portuguese (Brazil) | `pt_BR` | `--lang pt_BR` or `FASTSLR_LANG=pt_BR` |
| Spanish | `es` | `--lang es` or `FASTSLR_LANG=es` |

Priority: `--lang` flag > `FASTSLR_LANG` env var > system locale > English.

---

## Academic Use

### How to Cite

> Harden, L. (2026). *FastSLR: A deterministic triage engine for systematic literature reviews* (Version 3.0.0) [Computer software]. https://github.com/Lharden/fastslr

```bibtex
@software{harden2026fastslr,
  author  = {Harden, Leonardo},
  title   = {FastSLR: A Deterministic Triage Engine for Systematic Literature Reviews},
  year    = {2026},
  version = {3.0.0},
  url     = {https://github.com/Lharden/fastslr}
}
```

### Reporting in a Methods Section

When describing FastSLR in a paper, include:

1. FastSLR version
2. Preset used (binary / simple / standard)
3. Number and names of domain blocks
4. Decision policy
5. Fail-fast setting
6. Number of terms per block and anti-terms
7. Section weights
8. Config hash and input hash from the protocol snapshot

Example:

> *Title-and-abstract screening was performed using FastSLR v3.0.0 with the standard preset (5 relevance levels). Three domain blocks were defined: Context (CTX, 45 terms), Technology (TECH, 32 terms), and Methods (METHOD, 28 terms), with 12 global anti-terms. The `special` decision policy was used with fail-fast enabled. Section weights were: title 2.0x, abstract 1.0x, keywords 1.5x. The protocol snapshot hash is `abc123...` for full reproducibility.*

### Academic Package

`fastslr export` generates a ZIP archive with results, config, and protocol metadata -- ready to upload as supplementary material.

---

## Development

```bash
git clone https://github.com/Lharden/fastslr.git
cd fastslr
pip install -e ".[dev]"
pytest --cov
ruff check src/ && ruff format src/ && pyright src/
```

For architecture details and algorithm specifications, see [`docs/TECHNICAL_REPORT.md`](docs/TECHNICAL_REPORT.md) and [`docs/DESCRITIVO_TECNICO.md`](docs/DESCRITIVO_TECNICO.md).

---

## License

FastSLR is licensed under the [MIT License](LICENSE).

Copyright (c) 2026 Leonardo Harden.
