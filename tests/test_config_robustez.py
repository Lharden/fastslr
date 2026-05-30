"""Regression tests for config.py robustness fixes.

Covers three audit findings:

- ``csv-block-case-sensitive-silent-ignore``: a CSV block whose name differs
  only in case/whitespace from a ``BLOCK_ORDER`` entry must be matched
  case-insensitively and its terms preserved (not silently discarded).
- ``required-columns-no-header-normalization``: required-column validation must
  normalize headers (strip + lower) so ``Block;Kind;Term`` style headers are
  accepted, and the error message must list the columns actually found.
- ``proximity-negative-gap-literal-no-match``: ``MAX_GAP_BETWEEN_TERMS`` must be
  clamped to ``>= 0`` at load time so a negative knob cannot silently disable
  proximity matching.
"""

from __future__ import annotations

from pathlib import Path

from fastslr.core.config import load_global_params, parse_terms_csv


def _write_csv(path: Path, header: str, rows: list[str]) -> Path:
    path.write_text(header + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
    return path


# ── csv-block-case-sensitive-silent-ignore ──────────────────────────────


def test_csv_block_matches_block_order_case_insensitive(tmp_path: Path) -> None:
    """CSV block 'ctx' must match BLOCK_ORDER ['CTX'] and keep its terms.

    Before the fix, the case-sensitive comparison produced an empty
    ``_domain_blocks`` and a spurious "not in BLOCK_ORDER" warning.
    """
    csv = _write_csv(
        tmp_path / "terms.csv",
        "block,kind,term,level,section_scope,is_regex",
        ["ctx,pos,quantum,1,any,0"],
    )
    base_config = {"global": {"BLOCK_ORDER": ["CTX"], "PONTUACAO_NIVEIS": {1: 10}}}

    config = parse_terms_csv(csv, base_config)

    # Block must be present under the canonical BLOCK_ORDER name.
    assert config["_domain_blocks"] == ["CTX"]
    assert "CTX" in config
    terms = [e["term"] for e in config["CTX"]["positives"]]
    assert terms == ["quantum"]
    # No "not in BLOCK_ORDER" warning should be emitted.
    assert not any("not in" in w.lower() for w in config["_parse_warnings"])


def test_csv_block_whitespace_matches_block_order(tmp_path: Path) -> None:
    """Leading/trailing whitespace differences must not discard a block."""
    csv = _write_csv(
        tmp_path / "terms.csv",
        "block,kind,term,level,section_scope,is_regex",
        [" Method ,pos,survey,1,any,0"],
    )
    base_config = {"global": {"BLOCK_ORDER": ["METHOD"], "PONTUACAO_NIVEIS": {1: 10}}}

    config = parse_terms_csv(csv, base_config)

    assert config["_domain_blocks"] == ["METHOD"]
    assert [e["term"] for e in config["METHOD"]["positives"]] == ["survey"]


def test_csv_block_truly_absent_still_warns(tmp_path: Path) -> None:
    """A block genuinely absent from BLOCK_ORDER must still warn (no regression)."""
    csv = _write_csv(
        tmp_path / "terms.csv",
        "block,kind,term,level,section_scope,is_regex",
        ["GHOST,pos,quantum,1,any,0"],
    )
    base_config = {"global": {"BLOCK_ORDER": ["CTX"], "PONTUACAO_NIVEIS": {1: 10}}}

    config = parse_terms_csv(csv, base_config)

    assert config["_domain_blocks"] == []
    assert any("GHOST" in w and "BLOCK_ORDER" in w for w in config["_parse_warnings"])


# ── required-columns-no-header-normalization ────────────────────────────


def test_required_columns_accept_titlecase_header(tmp_path: Path) -> None:
    """Header 'Block;Kind;Term' (titlecase) must be accepted after normalization.

    Note: the canonical separator is ';' here only to exercise titlecase; the
    loader reads comma CSV, so we use comma with titlecase names.
    """
    csv = _write_csv(
        tmp_path / "terms.csv",
        "Block,Kind,Term,Level,Section_Scope,Is_Regex",
        ["BLOCK_A,pos,quantum,1,any,0"],
    )
    base_config = {"global": {"BLOCK_ORDER": ["BLOCK_A"], "PONTUACAO_NIVEIS": {1: 10}}}

    config = parse_terms_csv(csv, base_config)

    assert [e["term"] for e in config["BLOCK_A"]["positives"]] == ["quantum"]


def test_required_columns_accept_trailing_space_header(tmp_path: Path) -> None:
    """Header with trailing whitespace ('term ') must be accepted."""
    csv = _write_csv(
        tmp_path / "terms.csv",
        "block ,kind, term ,level,section_scope,is_regex",
        ["BLOCK_A,pos,quantum,1,any,0"],
    )
    base_config = {"global": {"BLOCK_ORDER": ["BLOCK_A"], "PONTUACAO_NIVEIS": {1: 10}}}

    config = parse_terms_csv(csv, base_config)

    assert [e["term"] for e in config["BLOCK_A"]["positives"]] == ["quantum"]


def test_required_columns_error_lists_found_columns(tmp_path: Path) -> None:
    """Missing-columns error must list the columns actually found."""
    csv = _write_csv(
        tmp_path / "terms.csv",
        "foo,bar,baz",
        ["a,b,c"],
    )
    base_config = {"global": {"BLOCK_ORDER": ["BLOCK_A"]}}

    try:
        parse_terms_csv(csv, base_config)
    except ValueError as exc:
        msg = str(exc)
        assert "foo" in msg and "bar" in msg and "baz" in msg
    else:  # pragma: no cover - the call must raise
        raise AssertionError("expected ValueError for missing required columns")


# ── proximity-negative-gap-literal-no-match (config clamp) ───────────────


def test_max_gap_negative_is_clamped_to_zero() -> None:
    """A negative MAX_GAP_BETWEEN_TERMS must be clamped to 0 at load time."""
    params = load_global_params({"MAX_GAP_BETWEEN_TERMS": -1})
    assert params.max_gap_between_terms == 0


def test_max_gap_positive_is_preserved() -> None:
    """A valid positive max_gap must pass through unchanged (no regression)."""
    params = load_global_params({"MAX_GAP_BETWEEN_TERMS": 3})
    assert params.max_gap_between_terms == 3
