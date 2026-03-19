# FastSLR -- Deterministic SLR Triage Engine

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-3.0.0-brightgreen.svg)](https://pypi.org/project/fastslr/)

**FastSLR** is a deterministic, rule-based triage engine for Systematic Literature Reviews (SLR). It scores and classifies articles based on researcher-defined search terms, thematic blocks, and configurable decision policies -- with zero AI/ML involved.

---

## Overview

FastSLR automates the title-and-abstract screening stage of a systematic review. Given a corpus of articles (CSV or XLSX) and a configuration file describing your review protocol, it deterministically classifies every article as **APPROVED**, **FLAGGED**, or **REJECTED**.

**Who it is for:** Researchers conducting systematic or scoping literature reviews who need transparent, reproducible screening that can be fully described in a methods section.

**Design philosophy:**

- **Deterministic** -- same input + same config = same output, always.
- **Transparent** -- every decision includes the exact terms matched, scores computed, and reason for the verdict.
- **Reproducible** -- output includes config hashes and input hashes for audit trails.
- **No AI/ML** -- all decisions are rule-based. No black boxes, no model drift, no training data needed.

**Key features:**

- Configurable domain blocks (researcher-defined thematic areas)
- 5 relevance levels (customizable via presets: 1, 3, or 5 levels)
- 3 decision policies (`special`, `strict`, `k_of_n`)
- Fail-fast evaluation (rejects early, skips unnecessary computation)
- Anti-term system (exclusion and flagging)
- Section-aware scoring with configurable weights
- Internationalization (English, Portuguese, Spanish)
- CLI and interactive TUI interfaces
- Academic export package for publication

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

Edit `terms.csv` with your search terms. Each row defines one term:

```csv
block,kind,term,level,section_scope,is_regex
CTX,pos,machine learning,1,any,0
CTX,pos,deep learning,1,any,0
CTX,pos,neural network,2,any,0
CTX,anti,survey,,,0
TECH,pos,convolutional,1,any,0
TECH,pos,transformer,2,any,0
METHOD,pos,cross-validation,1,any,0
```

### 4. Run triage

```bash
fastslr run articles.csv --config my_review/config.json --terms my_review/terms.csv
```

Results are saved as an XLSX file in the output directory.

---

## Concepts

### Domain Blocks

Domain blocks are researcher-defined thematic areas that an article must satisfy. For example, a review about "AI in Healthcare" might define two blocks: `AI` and `HEALTH`. **All blocks are mandatory** -- an article must pass every block to be approved.

### Relevance Levels

Terms are assigned a priority level from 1 (most relevant) to 5 (least relevant). Higher-priority terms contribute more points. The number of levels depends on the preset:

| Preset     | Levels | Use case                                    |
|------------|--------|---------------------------------------------|
| `binary`   | 1      | Quick include/exclude screening             |
| `simple`   | 3      | Moderate granularity                        |
| `standard` | 5      | Full granularity (recommended)              |

### Anti-terms

Anti-terms trigger negative actions when found in an article:

- **Exclusion anti-terms** (`anti_exclude` / kind=`anti`): Immediately reject the article from that block. No further evaluation is needed.
- **Flagging anti-terms** (`anti_flag` / kind=`flag`): Downgrade the article to FLAGGED status for manual review.

### Sections and Weights

FastSLR evaluates three article sections, each with a configurable weight multiplier:

| Section       | Default Weight | Description                              |
|---------------|----------------|------------------------------------------|
| `title`       | 2.0x           | Article title (highest signal)           |
| `abstract`    | 1.0x           | Article abstract (baseline)              |
| `manual_tags` | 1.5x           | Author keywords or manual tags           |

A term found in the title contributes 2x its base score; in the abstract, 1x.

### Final Decisions

Each article receives one of three final decisions:

| Decision          | Meaning                                         |
|-------------------|------------------------------------------------|
| `APPROVED_FINAL`  | Passed all blocks -- include in full-text review |
| `FLAGGED_FINAL`   | Needs manual review (anti-flag hit or borderline)|
| `REJECTED_FINAL`  | Failed one or more blocks -- exclude             |

### Fail-Fast

When `FAIL_FAST_GLOBAL` is enabled (default: `true`), if any block rejects an article, the remaining blocks are marked as `NOT_EVALUATED` and the article is immediately rejected. This is a core methodology choice, not a limitation -- it reflects the logical AND requirement across all domain blocks and significantly speeds up processing.

---

## Configuration Guide

### Config File Structure

The `config.json` file has four main sections:

```json
{
  "global": { ... },
  "fields": { ... },
  "output": { ... },
  "encoding": "utf-8-sig",
  "sep": ";"
}
```

### Global Parameters

All global parameters live under the `"global"` key. The table below documents every parameter:

#### Decision & Policy

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `DECISION_POLICY` | string | `"special"` | How the final decision is derived from block statuses. Options: `"special"` (default rule + high-score override), `"strict"` (all blocks must approve), `"k_of_n"` (at least K blocks must approve). |
| `ENABLE_SPECIAL_APPROVAL_RULE` | bool | `true` | When `true` and policy is `"special"`, articles with a very high score in any block can be approved even if other blocks are only flagged. |
| `SPECIAL_APPROVAL_THRESHOLD` | number | `40.0` | Score threshold that triggers the special approval rule. |
| `FAIL_FAST_GLOBAL` | bool | `true` | Stop evaluating remaining blocks after the first exclusion. |
| `MIN_APPROVED_BLOCKS` | int or null | `null` | For `k_of_n` policy: minimum number of blocks that must be approved. |
| `MAX_FLAGGED_BLOCKS_FOR_APPROVAL` | int | `0` | Maximum number of flagged blocks still allowing article approval. |

#### Scoring

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `PONTUACAO_NIVEIS` | object | `{"1":10,"2":8,"3":6,"4":4,"5":2}` | Points awarded per relevance level. Key = level number (string), value = integer score. |
| `LIMITES_APROVADO` | object | `{"1":10,"2":12,"3":18,"4":22,"5":null}` | Minimum score for APPROVED status at each level. `null` means that level alone cannot approve. |
| `LIMITES_SINALIZADO` | object | `{"1":6,"2":6,"3":6,"4":7,"5":12}` | Minimum score for FLAGGED status at each level. Below this = REJECTED. |
| `WEIGHTS` | object | `{"title":2.0,"abstract":1.0,"manual_tags":1.5}` | Multiplier applied to raw scores per section. |
| `MAX_SECTION_SCORE` | number | `30` | Cap on the raw score a single section can contribute. Prevents one section from dominating. |
| `NO_TAGS_UPLIFT` | number | `1.17` | Multiplier applied to scores when the `manual_tags` column is empty. Compensates for missing keyword data. Must be >= 1.0. |

#### Matching

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ENABLE_PROXIMITY_DETECTION` | bool | `true` | Enable multi-word proximity matching. When `true`, multi-word terms can match even if words are not adjacent. |
| `MAX_GAP_BETWEEN_TERMS` | int | `2` | Maximum number of tokens allowed between words in a multi-word term for proximity matching. |
| `TOKEN_UNIT_FOR_GAPS` | string | `"\\S+"` | Regex pattern defining what counts as a token for gap measurement. |
| `NOISE_PROFILE` | string | `"relaxed"` | Noise-tolerance profile: `"relaxed"` (most permissive), `"balanced"`, `"strict"` (least permissive). |

#### Quality Gates

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `MIN_UNIQUE_TERMS_FOR_APPROVAL` | int | `1` | Minimum number of distinct terms that must match for a block to be approved. |
| `MIN_SECTIONS_WITH_HITS_FOR_APPROVAL` | int | `1` | Minimum number of sections (title, abstract, tags) with at least one hit for approval. |
| `REQUIRE_NON_WEAK_TERM_FOR_APPROVAL` | bool | `false` | When `true`, at least one non-weak-level term must match for approval. |
| `WEAK_LEVELS` | array | `[5]` | Which levels are considered "weak" (low priority). |
| `LEVEL_ORDER` | array | `[1,2,3,4,5]` | Explicit evaluation order of priority levels. |
| `BLOCK_ORDER` | array | *(from terms)* | Explicit evaluation order of domain blocks. |

#### Error Handling

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ERROR_POLICY` | string | `"flag"` | How processing errors are handled: `"flag"` (mark article and continue) or `"fail"` (halt immediately). |
| `MAX_ERROR_RATE` | number | `0.05` | Maximum acceptable error rate (0.0-1.0) before halting the run. |

### Field Mappings

The `"fields"` section maps your CSV column names to FastSLR's expected fields:

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

| Field | Description |
|-------|-------------|
| `id` | Column name in your input CSV that contains the article identifier. |
| `id_output` | Column name used in the output file for the article ID. |
| `title` | Column name containing article titles. |
| `abstract` | Column name containing article abstracts. |
| `manual_tags` | Column name containing author keywords or manual tags. |

### Output Settings

```json
{
  "output": {
    "csv": false,
    "xlsx": true,
    "csv_sep": ";",
    "csv_decimal": ",",
    "csv_float_format": "%.2f",
    "xlsx_engine": "openpyxl",
    "xlsx_sheet_name": "resultados",
    "academic_package": true
  }
}
```

### Defining Domain Blocks with Positive Terms

Terms can be defined in the `config.json` directly or in a separate `terms.csv` file (recommended for larger term sets). Each positive term has:

- **`term`**: The search string (case-insensitive matching).
- **`level`**: Relevance level (1 = highest priority, 5 = lowest).
- **`section_scope`**: Where to look -- `"title"`, `"abstract"`, `"manual_tags"`, or `"any"` (all sections).
- **`is_regex`**: Set to `true` to interpret the term as a regular expression.

### Anti-terms

Anti-terms are defined per block. There are two types:

- **`anti_exclude`** (kind=`anti` in CSV): If found, the article is immediately **rejected** from that block.
- **`anti_flag`** (kind=`flag` in CSV): If found, the article is **flagged** for manual review.

### Terms CSV Format

The terms CSV is the recommended way to manage terms. Required columns:

| Column | Required | Description |
|--------|----------|-------------|
| `block` | Yes | Block name (e.g., `CTX`, `TECH`). Use `GLOBAL` for cross-block anti-terms. |
| `kind` | Yes | Term type: `pos` (positive), `anti` (exclusion), `flag` (flagging). |
| `term` | Yes | The search term string. |
| `level` | No | Relevance level (1-5). Required for `pos` terms. |
| `section_scope` | No | Section scope: `title`, `abstract`, `manual_tags`, or `any` (default). |
| `is_regex` | No | `1`/`true` for regex terms, `0`/`false` otherwise (default). |

Example:

```csv
block,kind,term,level,section_scope,is_regex
CTX,pos,machine learning,1,any,0
CTX,pos,artificial intelligence,1,any,0
CTX,pos,deep learning,2,any,0
CTX,pos,neural network,2,title,0
CTX,pos,classification,3,any,0
CTX,anti,review paper,,,0
CTX,flag,meta-analysis,,,0
TECH,pos,image recognition,1,any,0
TECH,pos,computer vision,1,any,0
GLOBAL,anti,retracted,,,0
GLOBAL,flag,preprint,,,0
```

The `GLOBAL` block defines anti-terms that apply to all articles before block evaluation (T0 pre-screening).

### Presets

Presets configure the level scores and thresholds:

#### Binary (1 level)

```
Level scores:         {1: 10}
Approval thresholds:  {1: 5}
Flagging thresholds:  {1: 3}
```

#### Simple (3 levels)

```
Level scores:         {1: 10, 2: 6, 3: 2}
Approval thresholds:  {1: 8, 2: 10, 3: 14}
Flagging thresholds:  {1: 4, 2: 6, 3: 8}
```

#### Standard (5 levels -- recommended)

```
Level scores:         {1: 10, 2: 8, 3: 6, 4: 4, 5: 2}
Approval thresholds:  {1: 10, 2: 12, 3: 18, 4: 22, 5: null}
Flagging thresholds:  {1: 6, 2: 6, 3: 6, 4: 7, 5: 12}
```

Note: `null` in approval thresholds means that level alone cannot trigger approval.

### Full Annotated Config Example

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
    "TOKEN_UNIT_FOR_GAPS": "\\S+",
    "ENABLE_PROXIMITY_DETECTION": true,
    "NOISE_PROFILE": "relaxed",
    "MIN_UNIQUE_TERMS_FOR_APPROVAL": 1,
    "MIN_SECTIONS_WITH_HITS_FOR_APPROVAL": 1,
    "REQUIRE_NON_WEAK_TERM_FOR_APPROVAL": false,
    "ERROR_POLICY": "flag",
    "MAX_ERROR_RATE": 0.05,
    "PONTUACAO_NIVEIS": {
      "1": 10, "2": 8, "3": 6, "4": 4, "5": 2
    },
    "LIMITES_APROVADO": {
      "1": 10, "2": 12, "3": 18, "4": 22, "5": null
    },
    "LIMITES_SINALIZADO": {
      "1": 6, "2": 6, "3": 6, "4": 7, "5": 12
    },
    "WEIGHTS": {
      "title": 2.0,
      "abstract": 1.0,
      "manual_tags": 1.5
    },
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

## CLI Reference

All commands support the `--lang` / `-l` flag to set the interface language and `--help` for detailed usage.

### 1. `fastslr run`

Run the full triage on an articles file.

```bash
fastslr run articles.csv --config config.json --terms terms.csv
fastslr run articles.csv -c config.json -t terms.csv -o results/ -q
```

| Flag | Short | Description |
|------|-------|-------------|
| `--config` | `-c` | Path to config.json (required). |
| `--terms` | `-t` | Path to terms CSV (optional). |
| `--output` | `-o` | Output directory (optional, defaults to current dir). |
| `--quiet` | `-q` | Suppress progress and statistics output. |
| `--lang` | `-l` | Interface language (`en`, `pt_BR`, `es`). |

### 2. `fastslr preview`

Preview triage results on a random sample of articles without writing output files.

```bash
fastslr preview articles.csv --config config.json --sample 100
fastslr preview articles.csv -c config.json -t terms.csv -s 50
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--config` | `-c` | -- | Path to config.json (required). |
| `--terms` | `-t` | -- | Path to terms CSV (optional). |
| `--sample` | `-s` | `50` | Number of articles to sample. |
| `--lang` | `-l` | -- | Interface language. |

### 3. `fastslr coverage`

Analyze term coverage across all articles. Shows which terms matched and how often.

```bash
fastslr coverage articles.csv --config config.json
fastslr coverage articles.csv -c config.json -t terms.csv -o coverage_report.csv
```

| Flag | Short | Description |
|------|-------|-------------|
| `--config` | `-c` | Path to config.json (required). |
| `--terms` | `-t` | Path to terms CSV (optional). |
| `--output` | `-o` | Export coverage report as CSV. |
| `--lang` | `-l` | Interface language. |

### 4. `fastslr diff`

Compare two triage result files to see which articles changed decisions.

```bash
fastslr diff results_v1.xlsx results_v2.xlsx
```

| Flag | Short | Description |
|------|-------|-------------|
| `--lang` | `-l` | Interface language. |

Shows a table of articles with changed decisions and a summary of all transitions (e.g., APPROVED -> REJECTED).

### 5. `fastslr new-project`

Create a new triage project with scaffolded config and terms template.

```bash
fastslr new-project my_review --blocks "CTX,TECH,METHOD"
fastslr new-project my_review -b "AI,HEALTH" -p simple -o projects/
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--blocks` | `-b` | -- | Comma-separated block names (required). |
| `--preset` | `-p` | `standard` | Level preset: `binary`, `simple`, `standard`. |
| `--output` | `-o` | current dir | Output directory. |
| `--lang` | `-l` | -- | Interface language. |

### 6. `fastslr export`

Export an academic package (ZIP) from triage results for publication or archiving.

```bash
fastslr export results.xlsx
fastslr export results.xlsx -o exports/ -c config.json
```

| Flag | Short | Description |
|------|-------|-------------|
| `--output` | `-o` | Output directory for the ZIP file. |
| `--config` | `-c` | Config file to include in the package. |
| `--lang` | `-l` | Interface language. |

### 7. `fastslr terms`

Browse and inspect all configured terms (positive, anti-exclude, anti-flag).

```bash
fastslr terms --config config.json
fastslr terms -c config.json -t terms.csv --block CTX --kind pos
```

| Flag | Short | Description |
|------|-------|-------------|
| `--config` | `-c` | Path to config.json (required). |
| `--terms` | `-t` | Path to terms CSV (optional). |
| `--block` | `-b` | Filter by block name. |
| `--kind` | `-k` | Filter by kind: `pos`, `anti`, or `flag`. |
| `--lang` | `-l` | Interface language. |

### 8. `fastslr profile`

Manage reusable configuration profiles.

```bash
# Save a config as a named profile
fastslr profile save my_protocol --config config.json --desc "Initial protocol"

# List all saved profiles
fastslr profile list

# Load a profile back to a config file
fastslr profile load my_protocol --output config.json
```

| Subcommand | Description |
|------------|-------------|
| `save <name> -c <config>` | Save a config as a named profile. `--desc` for description. |
| `load <name>` | Load a profile to `config.json` (or use `-o` for a different path). |
| `list` | List all saved profiles with name, description, and path. |

### 9. `fastslr tui`

Launch the interactive terminal user interface.

```bash
fastslr tui
```

No additional flags. See [TUI Guide](#tui-guide) below.

### 10. `fastslr version`

Show the installed FastSLR version.

```bash
fastslr version
```

---

## TUI Guide

The interactive TUI provides a menu-driven interface for all FastSLR operations. Launch it with `fastslr tui`.

### Screens

| Key | Screen | Description |
|-----|--------|-------------|
| `1` | New Project | Guided project creation wizard with preset selection. |
| `2` | Load Profile | Browse and load saved configuration profiles. |
| `3` | Edit Configuration | View and edit config.json with a built-in JSON editor. |
| `4` | Browse Terms | View all search terms in a filterable table (block, kind, scope). |
| `5` | Run Triage | Execute triage with a progress bar and live statistics. |
| `6` | Results Explorer | Browse triage results with decision filtering (Approved/Flagged/Rejected). |
| `7` | Coverage Analysis | Check which terms matched and which had zero hits. |
| `8` | Compare Runs | Diff two result files to see changed decisions. |
| `9` | Export Academic Package | Generate a publication-ready ZIP archive. |
| `0` | Settings & Language | Change interface language (English, Portuguese, Spanish). |

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1`-`9`, `0` | Navigate directly to the corresponding screen. |
| `Escape` | Go back to the previous screen. |
| `Q` | Quit the application. |

---

## Understanding Results

### Output XLSX Structure

The output spreadsheet contains one row per article with the following column groups:

#### Identification

- **`ID`** -- Article identifier (mapped from your input's ID column).

#### Per-Block Columns

For each domain block (e.g., `CTX`, `TECH`), the output includes:

| Column | Description |
|--------|-------------|
| `RawScore_{block}` | Unweighted sum of term match scores for this block. |
| `FinalScore_{block}` | Weighted score after applying section weights and uplift. |
| `BestLevel_{block}` | Highest (lowest-numbered) relevance level matched. |
| `Status_{block}` | Block verdict: `APPROVED`, `FLAGGED`, `REJECTED`, or `NOT_EVALUATED`. |
| `Highlights_{block}` | Positive terms that matched, with section and level info. |
| `AntiHighlights_{block}` | Anti-terms that matched (exclusion or flagging). |
| `Flags_{block}` | Warning flags (e.g., anti-flag hits, quality gate notes). |

#### Final Columns

| Column | Description |
|--------|-------------|
| `Final_Decision` | Overall article verdict: `APPROVED_FINAL`, `FLAGGED_FINAL`, or `REJECTED_FINAL`. |
| `Final_Reason` | Human-readable explanation of why the decision was made. |

### Protocol Snapshot

Each triage run generates a protocol snapshot JSON file containing:

- **`config_hash`** -- SHA-256 hash of the configuration used.
- **`input_hash`** -- SHA-256 hash of the input file.
- Timestamps, version info, and full parameter dump.

This enables exact reproducibility: if two runs share the same `config_hash` and `input_hash`, they are guaranteed to produce identical results.

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

### Reporting Parameters in a Methods Section

When describing FastSLR usage in a paper, include at minimum:

1. **FastSLR version** (e.g., 3.0.0)
2. **Preset used** (binary / simple / standard) or custom level configuration
3. **Number and names of domain blocks** (e.g., 3 blocks: CTX, TECH, METHOD)
4. **Decision policy** (`special`, `strict`, or `k_of_n`)
5. **Fail-fast setting** (enabled/disabled)
6. **Number of positive terms per block** and **number of anti-terms**
7. **Section weights** (title, abstract, keywords)
8. **Config hash and input hash** from the protocol snapshot (for exact reproducibility)

Example methods paragraph:

> *Title-and-abstract screening was performed using FastSLR v3.0.0 with the standard preset (5 relevance levels). Three domain blocks were defined: Context (CTX, 45 terms), Technology (TECH, 32 terms), and Methods (METHOD, 28 terms), with 12 global anti-terms. The `special` decision policy was used with fail-fast enabled. Section weights were: title 2.0x, abstract 1.0x, keywords 1.5x. The protocol snapshot hash is `abc123...` for full reproducibility.*

### Academic Package Export

The `fastslr export` command generates a ZIP archive containing:

- Triage results (XLSX)
- Configuration snapshot (JSON)
- Protocol metadata (hashes, version, timestamps)

This package is designed to be uploaded as supplementary material alongside your publication.

---

## i18n

FastSLR supports three interface languages:

| Language | Code | Example |
|----------|------|---------|
| English | `en` | Default |
| Portuguese (Brazil) | `pt_BR` | `--lang pt_BR` |
| Spanish | `es` | `--lang es` |

### How to Switch Language

**1. Per-command flag** (highest priority):

```bash
fastslr run articles.csv -c config.json --lang pt_BR
```

**2. Environment variable** (persistent):

```bash
export FASTSLR_LANG=pt_BR
fastslr run articles.csv -c config.json
```

On Windows:

```powershell
$env:FASTSLR_LANG = "pt_BR"
fastslr run articles.csv -c config.json
```

**3. System locale auto-detection** (automatic fallback):

If neither the flag nor the environment variable is set, FastSLR detects the system locale. For example, a system with locale `pt_BR.UTF-8` will automatically use Portuguese.

Language priority: `--lang` flag > `FASTSLR_LANG` env var > system locale > English (default).

---

## Development

### Setup

```bash
git clone https://github.com/Lharden/fastslr.git
cd fastslr
pip install -e ".[dev]"
```

### Testing

```bash
pytest --cov
```

### Linting and Type Checking

```bash
ruff check src/
ruff format src/
pyright src/
```

### Dependencies

Runtime:

- Python >= 3.10
- pandas >= 2.0
- openpyxl >= 3.1
- typer >= 0.12
- rich >= 13.0
- textual >= 0.80
- jsonschema >= 4.20

Optional:

- chardet >= 5.0 (auto-detect CSV encoding: `pip install fastslr[chardet]`)

Dev:

- pytest >= 7.0
- pytest-cov >= 4.0
- ruff >= 0.1
- pyright >= 1.1
- coverage >= 7.0

---

## License

FastSLR is licensed under the [MIT License](LICENSE).

Copyright (c) 2026 Leonardo Harden.
