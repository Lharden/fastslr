# FastSLR v3.0.0 — Stress Test Log

Date: 2026-03-17
Tester: Automated (Claude Opus 4.6)

## Summary

15 scenarios tested. 12 passed initially, 3 failures found and fixed.

| # | Scenario | Initial | After Fix |
|---|----------|---------|-----------|
| 1 | Empty CSV (headers only, 0 rows) | FAIL | RESOLVED |
| 2 | CSV with missing columns | PASS | — |
| 3 | Single article | PASS | — |
| 4 | Very long abstract (51k chars) | PASS | — |
| 5 | Invalid JSON config | PASS | — |
| 6 | Terms CSV with empty terms | PASS | — |
| 7 | Negative thresholds | PASS* | IMPROVED |
| 8 | Non-existent file paths | PASS | — |
| 9 | Invalid regex in terms | PASS | — |
| 10 | Unicode/special chars (emoji, CJK, Arabic, HTML) | PASS | — |
| 11 | Non-existent profile load | FAIL | RESOLVED |
| 12 | Diff with mismatched files | FAIL | RESOLVED |
| 13 | New project with empty blocks | PASS | — |
| 14 | Sample size larger than dataset | PASS | — |
| 15 | Unknown decision policy | PASS | — |

## Findings and Fixes

### Finding #1 — Empty CSV causes ValueError traceback
- **Scenario**: CSV with headers but zero data rows
- **Expected**: Process 0 articles, show empty results
- **Actual**: `ValueError: Unable to load CSV` — `load_csv_safe()` rejected empty DataFrames
- **Root cause**: `io.py` line 111 checked `not df.empty`, which is True for 0-row DataFrames
- **Fix**: Changed condition to `len(df.columns) >= 3` (valid structure regardless of row count)
- **File**: `src/fastslr/core/io.py`
- **Status**: RESOLVED

### Finding #2 — Non-existent profile shows raw Python traceback
- **Scenario**: `fastslr profile load "nonexistent"`
- **Expected**: Friendly error message
- **Actual**: `FileNotFoundError` with full Python traceback
- **Root cause**: CLI `profile_load` command did not catch `FileNotFoundError`
- **Fix**: Added try/except around `profiles.load_profile()` with translated error message
- **File**: `src/fastslr/app/cli.py`
- **Status**: RESOLVED

### Finding #3 — Diff crashes on files without Final_Decision column
- **Scenario**: Compare two non-triage CSV files
- **Expected**: Clear error about missing column
- **Actual**: `KeyError: "['Final_Decision'] not in index"`
- **Root cause**: `diff_results()` assumed both files had `Final_Decision` column
- **Fix**: Added column validation before merge, raises `ValueError` with descriptive message
- **File**: `src/fastslr/app/controller.py`
- **Status**: RESOLVED

### Finding #4 — Negative thresholds accepted silently
- **Scenario**: Config with negative approval thresholds
- **Expected**: At least a warning
- **Actual**: Processed silently (no crash, but semantically nonsensical)
- **Fix**: Added validation warning for negative threshold values in `validate_config()`
- **File**: `src/fastslr/app/controller.py`
- **Status**: IMPROVED (now warns)

## Scenarios That Passed Without Issues

- **Missing columns**: Auto-mapped via `_auto_map_column()`, no crash
- **Single article**: Full pipeline works for n=1
- **Long abstract (51k chars)**: Regex engine handles it, ~2 art/s (proportional slowdown)
- **Invalid JSON**: Standard `JSONDecodeError` raised, clear message
- **Empty terms**: Silently skipped during parsing, only valid terms loaded
- **Non-existent files**: CLI checks `exists()` before processing
- **Invalid regex**: `compile_pattern()` catches `re.error`, returns None, term skipped
- **Unicode/special chars**: Encoding detection + regex handle multibyte correctly
- **Empty blocks**: CLI validates block list before creating project
- **Sample > dataset**: `sample_articles()` returns full dataset if n >= len(df)
- **Unknown policy**: `validate_config()` catches and reports error-level issue
