"""Regression tests for io.py and coverage.py audit findings.

Covers three confirmed findings:

* ``migrate-protocol-snapshot-incompleto`` — ``migrate_protocol_snapshot`` used to
  only re-tag ``protocol_version``/``schema_id`` and inject ``methodology``,
  without gating on the source version nor backfilling required root keys. A
  minimal v1.0 snapshot therefore presented itself as a valid ``2.1`` snapshot
  while still failing ``validate_protocol_snapshot``. It must now refuse unknown
  versions and produce a snapshot that validates.
* ``default-config-csv-false-vs-codigo-true`` — ``get_export_opts`` defaulted to
  ``csv:true``/``xlsx:false``, the opposite of the shipped template
  (``csv:false``/``xlsx:true``). A minimal config without an ``output`` block
  must now follow the documented default.
* ``broad-terms-strict-gt-corpus-pequeno`` — broad-term detection used a strict
  ``> total*0.8`` with no minimum corpus floor, so a 1-2 article corpus marked
  every matched term as "broad". It must now skip broad-term detection below the
  corpus floor.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
import pytest

from fastslr.core import io
from fastslr.core.coverage import analyze_term_coverage
from fastslr.core.io import (
    PROTOCOL_SCHEMA_ID,
    PROTOCOL_VERSION_CURRENT,
    get_export_opts,
    migrate_protocol_snapshot,
    validate_protocol_snapshot,
)

# ── migrate_protocol_snapshot ─────────────────────────────────────────────────


def test_migrate_incomplete_v10_snapshot_produces_valid_snapshot() -> None:
    """A minimal v1.0 snapshot must migrate to a snapshot that passes validation.

    Regression: previously the migrated snapshot was tagged ``2.1`` but
    ``validate_protocol_snapshot`` still reported missing-root-key errors.
    """
    incomplete = {"protocol_version": "1.0", "inputs": {}}

    migrated = migrate_protocol_snapshot(incomplete)

    assert migrated["protocol_version"] == PROTOCOL_VERSION_CURRENT
    assert migrated["schema_id"] == PROTOCOL_SCHEMA_ID
    # The whole point of the fix: the result must validate cleanly.
    assert validate_protocol_snapshot(migrated) == []


def test_migrate_rejects_unknown_source_version() -> None:
    """An unknown/future source version must be refused, not silently re-tagged."""
    with pytest.raises(ValueError, match="unknown source version"):
        migrate_protocol_snapshot({"protocol_version": "99.0", "inputs": {}})


def test_migrate_rejects_missing_source_version() -> None:
    """A snapshot without ``protocol_version`` is an unknown source and refused."""
    with pytest.raises(ValueError, match="unknown source version"):
        migrate_protocol_snapshot({"inputs": {}})


def test_migrate_complete_v20_snapshot_still_works() -> None:
    """The original happy-path (complete v2.0 snapshot) keeps migrating cleanly."""
    v20 = {
        "protocol_version": "2.0",
        "execution_id": "run_test",
        "generated_at": "2026-02-19T00:00:00",
        "triage_version": "1.1.0",
        "inputs": {
            "input_file": "a.csv",
            "input_hash": "aa",
            "terms_file": "b.csv",
            "terms_hash": "bb",
            "config_hash": "cc",
        },
        "configuration": {
            "decision_policy": "special",
            "domain_blocks": [{"id": "CTX", "label": "Context"}],
        },
        "processing": {
            "total_articles": 1,
            "processing_time_seconds": 0.1,
            "articles_per_second": 10,
        },
        "artifacts": {"results_path": "out.xlsx"},
        "reproducibility": {"deterministic_engine": True},
    }

    migrated = migrate_protocol_snapshot(v20)

    assert migrated["protocol_version"] == PROTOCOL_VERSION_CURRENT
    assert isinstance(migrated.get("methodology"), dict)
    # Original payload preserved (not clobbered by backfill defaults).
    assert migrated["execution_id"] == "run_test"
    assert migrated["triage_version"] == "1.1.0"
    assert validate_protocol_snapshot(migrated) == []


# ── get_export_opts default alignment ─────────────────────────────────────────


def test_export_opts_default_matches_template() -> None:
    """Without an ``output`` block, defaults follow the template: csv off, xlsx on.

    Regression: ``get_export_opts`` previously defaulted csv:true/xlsx:false,
    contradicting default_config.json / generate_config (csv:false/xlsx:true).
    """
    opts = get_export_opts({})

    assert opts["export_csv"] is False
    assert opts["export_xlsx"] is True


def test_export_opts_explicit_output_block_still_honored() -> None:
    """Explicit output flags override the defaults in both directions."""
    csv_only = get_export_opts({"output": {"csv": True, "xlsx": False}})
    assert csv_only["export_csv"] is True
    assert csv_only["export_xlsx"] is False


def test_export_results_minimal_config_writes_xlsx_not_csv(tmp_path) -> None:
    """A minimal config (no output block) exports XLSX, not CSV."""
    df = pd.DataFrame({"ID": ["1"], "Final_Decision": ["APPROVED_FINAL"]})

    exported = io.export_results(df, tmp_path / "triage_results", {})

    assert "xlsx" in exported
    assert "csv" not in exported
    assert exported["xlsx"].exists()


# ── broad-terms corpus floor ──────────────────────────────────────────────────


@dataclass
class _FakeMatch:
    term: str
    level: str = "L1"
    source_row: int = 0
    match_type: str = "exact"
    components: list[str] = field(default_factory=list)


@dataclass
class _FakeEvaluation:
    matches: dict[str, list[_FakeMatch]]


def _result_df_for_terms(rows: list[list[str]]) -> pd.DataFrame:
    """Build a result_df with one ``Highlights_domain`` cell per article.

    ``rows`` is a list (one entry per article) of term strings that matched in
    that article's title section.
    """
    cells: list[str] = []
    for terms in rows:
        evaluation = _FakeEvaluation(matches={"title": [_FakeMatch(term=t) for t in terms]})
        cells.append(io.pack_highlights(evaluation))
    return pd.DataFrame({"Highlights_domain": cells})


def test_broad_terms_not_flagged_for_tiny_corpus() -> None:
    """A 2-article corpus must NOT mark a universally-matched term as broad.

    Regression: ``article_count > total*0.8`` with total=2 → threshold 1.6, so a
    term in both articles (count 2 > 1.6) was wrongly reported broad at 100%.
    """
    term = "machine learning"
    result_df = _result_df_for_terms([[term], [term]])
    config = {
        "_domain_blocks": ["domain"],
        "domain": {"positives": [{"original_term": term}]},
    }

    report = analyze_term_coverage(result_df, config, domain_blocks=["domain"])

    assert report.broad_terms == []
    # And no broad-term suggestion leaks through either.
    assert not any("may add noise" in s for s in report.suggestions)


def test_broad_terms_flagged_for_large_corpus() -> None:
    """At/above the corpus floor, a near-universal term is still flagged broad."""
    term = "ubiquitous"
    # 12 articles, all contain the term -> 100% > 80% and total >= floor (10).
    result_df = _result_df_for_terms([[term]] * 12)
    config = {
        "_domain_blocks": ["domain"],
        "domain": {"positives": [{"original_term": term}]},
    }

    report = analyze_term_coverage(result_df, config, domain_blocks=["domain"])

    broad = {b["term"] for b in report.broad_terms}
    assert term in broad
