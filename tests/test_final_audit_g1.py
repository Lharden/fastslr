"""Regression tests for the approved final-audit G1 fixes."""

from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path

import pytest

from fastslr.core.config import parse_terms_csv
from fastslr.core.models import BlockEvaluation, GlobalParams, T0Evaluation
from fastslr.core.normalization import NormalizationEngine
from fastslr.core.patterns import compile_pattern, compile_proximity_pattern, precompile_patterns
from fastslr.core.scoring import make_final_decision


def _evaluation(status: str) -> BlockEvaluation:
    return BlockEvaluation(status=status, reason="test")


def _t0_flagged() -> T0Evaluation:
    return T0Evaluation(status="FLAGGED", reason="global review term", scope="global")


@pytest.mark.parametrize("policy", ["strict", "k_of_n"])
def test_t0_flagged_prevents_approval_for_all_policies(
    default_global_params: GlobalParams,
    policy: str,
) -> None:
    params = replace(default_global_params, decision_policy=policy, min_approved_blocks=1)

    decision, reason = make_final_decision({"A": _evaluation("APPROVED")}, _t0_flagged(), params)

    assert decision == "FLAGGED_FINAL"
    assert reason == "T0: global review term"


@pytest.mark.parametrize("policy", ["strict", "k_of_n"])
def test_rejected_block_keeps_precedence_over_t0_flagged(
    default_global_params: GlobalParams,
    policy: str,
) -> None:
    params = replace(default_global_params, decision_policy=policy, min_approved_blocks=1)

    decision, reason = make_final_decision({"A": _evaluation("REJECTED")}, _t0_flagged(), params)

    assert decision == "REJECTED_FINAL"
    assert reason == "Rejected blocks: A"


def test_global_positive_term_is_warned_and_ignored(tmp_path: Path) -> None:
    terms = tmp_path / "terms.csv"
    terms.write_text(
        "block,kind,term,level,section_scope,is_regex\n"
        "GLOBAL,pos,misleading,1,any,0\n"
        "GLOBAL,anti,exclude-me,,any,0\n",
        encoding="utf-8",
    )

    config = parse_terms_csv(terms, {"global": {}})

    assert config["T0"]["positives"] == []
    assert [entry["term"] for entry in config["T0"]["anti"]["exclude"]] == ["exclude-me"]
    assert any(
        "GLOBAL" in warning and "positive" in warning for warning in config["_parse_warnings"]
    )


def test_default_level_scores_validate_and_neutralize_out_of_range_level(tmp_path: Path) -> None:
    terms = tmp_path / "terms.csv"
    terms.write_text(
        "block,kind,term,level,section_scope,is_regex\nA,pos,invalid-level,0,any,0\n",
        encoding="utf-8",
    )

    config = parse_terms_csv(terms, {"global": {"BLOCK_ORDER": ["A"]}})

    assert config["A"]["positives"][0]["level"] is None
    assert any(
        "level 0 not in configured levels (1, 2, 3, 4, 5)" in warning
        for warning in config["_parse_warnings"]
    )


def test_normalization_unescapes_entities_and_removes_scientific_markup() -> None:
    engine = NormalizationEngine({"enabled": False})
    raw = "CO<sub>2</sub> &amp; H<sup>+</sup> with 10<inf>-3</inf>"

    normalized = engine.normalize(raw)

    assert normalized == "co2 & h+ with 10-3"
    assert raw == "CO<sub>2</sub> &amp; H<sup>+</sup> with 10<inf>-3</inf>"


def test_unsafe_free_regex_is_rejected_with_warning(caplog: pytest.LogCaptureFixture) -> None:
    block = {
        "positives": [
            {"term": r"(a+)+$", "level": 1, "scope": "any", "regex": True, "source_row": 0}
        ],
        "anti": {"exclude": [], "flag": []},
    }
    warnings: list[str] = []

    with caplog.at_level(logging.WARNING):
        compiled = precompile_patterns(block, block_name="A", warnings=warnings)

    assert compiled["positives"] == []
    assert any("unsafe regex" in warning for warning in warnings)
    assert "unsafe regex" in caplog.text.lower()


def test_benign_free_regex_remains_supported() -> None:
    pattern = compile_pattern(r"supply\s+chain", is_regex=True)

    assert pattern is not None
    assert pattern.search("supply   chain")


def test_unsafe_token_unit_falls_back_to_allowlisted_default(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        pattern = compile_proximity_pattern("oil", "gas", max_gap=2, token_unit=r"(\w+)+")

    assert pattern is not None
    assert r"(\w+)+" not in pattern.pattern
    assert pattern.search("oil from gas")
    assert "not allowlisted" in caplog.text
