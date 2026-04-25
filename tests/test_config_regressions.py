"""Regression tests for parse_terms_csv fixes.

Covers two Codex-review findings:

- Dedup key must include section_scope / level / is_regex so that rows
  reusing a term across scopes or variants are not silently collapsed.
- parse_terms_csv must merge CSV terms into an existing base_config
  without dropping blocks that are defined only inline in config.json.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fastslr.core.config import parse_terms_csv


def _write_terms_csv(path: Path, rows: list[str]) -> Path:
    header = "block,kind,term,level,section_scope,is_regex"
    path.write_text(header + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
    return path


def test_same_term_different_scope_is_preserved(tmp_path: Path) -> None:
    """Same term in two different section_scopes must generate two rules."""
    csv = _write_terms_csv(
        tmp_path / "terms.csv",
        [
            "BLOCK_A,pos,machine learning,1,title,0",
            "BLOCK_A,pos,machine learning,1,abstract,0",
        ],
    )

    base_config = {"global": {"BLOCK_ORDER": ["BLOCK_A"]}}
    config = parse_terms_csv(csv, base_config)

    assert config["_valid_terms_count"] == 2
    scopes = sorted(e["scope"] for e in config["BLOCK_A"]["positives"])
    assert scopes == ["abstract", "title"]
    assert config["_parse_warnings"] == []


def test_same_term_different_level_is_preserved(tmp_path: Path) -> None:
    """Same term with different levels must generate two rules."""
    csv = _write_terms_csv(
        tmp_path / "terms.csv",
        [
            "BLOCK_A,pos,deep learning,1,any,0",
            "BLOCK_A,pos,deep learning,2,any,0",
        ],
    )

    base_config = {
        "global": {
            "BLOCK_ORDER": ["BLOCK_A"],
            "PONTUACAO_NIVEIS": {1: 10, 2: 8},
        }
    }
    config = parse_terms_csv(csv, base_config)

    assert config["_valid_terms_count"] == 2
    levels = sorted(e["level"] for e in config["BLOCK_A"]["positives"])
    assert levels == ["1", "2"]


def test_same_term_different_is_regex_is_preserved(tmp_path: Path) -> None:
    """Exact and regex variants of the same term must both survive."""
    csv = _write_terms_csv(
        tmp_path / "terms.csv",
        [
            "BLOCK_A,pos,supply chain,1,any,0",
            "BLOCK_A,pos,supply chain,1,any,1",
        ],
    )

    base_config = {"global": {"BLOCK_ORDER": ["BLOCK_A"]}}
    config = parse_terms_csv(csv, base_config)

    assert config["_valid_terms_count"] == 2
    regex_flags = sorted(bool(e["regex"]) for e in config["BLOCK_A"]["positives"])
    assert regex_flags == [False, True]


def test_true_duplicate_is_still_deduplicated(tmp_path: Path) -> None:
    """Rows identical on (block, kind, term, scope, level, is_regex) are still deduped."""
    csv = _write_terms_csv(
        tmp_path / "terms.csv",
        [
            "BLOCK_A,pos,ai,1,title,0",
            "BLOCK_A,pos,ai,1,title,0",
        ],
    )

    base_config = {"global": {"BLOCK_ORDER": ["BLOCK_A"]}}
    config = parse_terms_csv(csv, base_config)

    assert config["_valid_terms_count"] == 1
    assert any("duplicate term" in w for w in config["_parse_warnings"])


def test_inline_block_survives_when_csv_has_subset(tmp_path: Path) -> None:
    """Blocks defined inline in config.json must remain in _domain_blocks
    even when the CSV only supplies a subset of the configured blocks."""
    csv = _write_terms_csv(
        tmp_path / "terms.csv",
        ["BLOCK_A,pos,neural network,1,any,0"],
    )

    base_config = {
        "global": {"BLOCK_ORDER": ["BLOCK_A", "BLOCK_B"]},
        "BLOCK_B": {
            "positives": [{"term": "robotics", "level": 1, "scope": "any"}],
            "anti": {"exclude": [], "flag": []},
        },
    }
    config = parse_terms_csv(csv, base_config)

    assert "BLOCK_A" in config["_domain_blocks"]
    assert "BLOCK_B" in config["_domain_blocks"]
    # BLOCK_B content preserved unchanged
    assert config["BLOCK_B"]["positives"][0]["term"] == "robotics"


def test_inline_block_survives_when_csv_only_has_global(tmp_path: Path) -> None:
    """Blocks defined inline must remain when CSV only supplies GLOBAL terms."""
    csv = _write_terms_csv(
        tmp_path / "terms.csv",
        ["GLOBAL,anti,review,,any,0"],
    )

    base_config = {
        "global": {"BLOCK_ORDER": ["BLOCK_A"]},
        "BLOCK_A": {
            "positives": [{"term": "optimization", "level": 1, "scope": "any"}],
            "anti": {"exclude": [], "flag": []},
        },
    }
    config = parse_terms_csv(csv, base_config)

    assert config["_domain_blocks"] == ["BLOCK_A"]
    assert config["BLOCK_A"]["positives"][0]["term"] == "optimization"


def test_inline_block_survives_without_block_order(tmp_path: Path) -> None:
    """Without BLOCK_ORDER, inline blocks must still be discovered."""
    csv = _write_terms_csv(
        tmp_path / "terms.csv",
        ["BLOCK_CSV,pos,kubernetes,1,any,0"],
    )

    base_config = {
        "global": {},
        "BLOCK_JSON": {
            "positives": [{"term": "docker", "level": 1, "scope": "any"}],
            "anti": {"exclude": [], "flag": []},
        },
    }
    config = parse_terms_csv(csv, base_config)

    assert set(config["_domain_blocks"]) == {"BLOCK_CSV", "BLOCK_JSON"}


def test_csv_and_inline_block_are_merged(tmp_path: Path) -> None:
    """When the same block exists inline AND in CSV, terms are merged."""
    csv = _write_terms_csv(
        tmp_path / "terms.csv",
        ["BLOCK_A,pos,csv-term,1,any,0"],
    )

    base_config = {
        "global": {"BLOCK_ORDER": ["BLOCK_A"]},
        "BLOCK_A": {
            "positives": [{"term": "json-term", "level": 1, "scope": "any"}],
            "anti": {"exclude": [], "flag": []},
        },
    }
    config = parse_terms_csv(csv, base_config)

    terms = sorted(e["term"] for e in config["BLOCK_A"]["positives"])
    assert terms == ["csv-term", "json-term"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
