"""Regression and behaviour tests for score-based decision logic.

Covers three findings in ``fastslr.core.scoring`` / ``fastslr.core.config``:

(a) ``make_final_decision`` special rule must not approve when there are
    zero approved blocks (vacuous ``all([])`` over an empty approved set).
(b) ``evaluate_block`` must not FLAG a block whose final score is exactly 0
    just because the default flagging threshold is 0.
(c) ``parse_terms_csv`` must neutralise a positive term whose numeric level
    falls outside the configured levels (warning alone is not enough).

It also exercises the happy paths of ``evaluate_block`` /
``_compute_section_scores`` and the *legitimate* special-approval rule.
"""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

import pytest

from fastslr.core.config import parse_terms_csv
from fastslr.core.models import BlockEvaluation, GlobalParams
from fastslr.core.scoring import (
    _compute_section_scores,
    evaluate_block,
    find_positive_terms,
    make_final_decision,
)

# ── helpers ──────────────────────────────────────────────────────────────────


def _positive(term: str, level: int, scope: str = "any") -> dict:
    """Build a positive-term entry with a pre-compiled pattern.

    ``find_positive_terms`` only requires a ``pattern`` object exposing
    ``.search`` plus ``level``/``scope`` keys, so a plain ``re.compile`` of
    the term is sufficient for these unit tests.
    """
    return {
        "term": term,
        "original_term": term,
        "level": level,
        "scope": scope,
        "pattern": re.compile(re.escape(term), re.IGNORECASE),
        "source_row": None,
    }


def _block(*positives: dict) -> dict:
    """Build a minimal block_config consumable by ``evaluate_block``."""
    return {
        "normalization_engine": None,
        "positives": list(positives),
        "proximity_positives": [],
        "anti_exclude": [],
        "anti_flag": [],
    }


def _eval(status: str, final_score: float, best_level: int | None = 1) -> BlockEvaluation:
    """Build a BlockEvaluation stub for make_final_decision tests."""
    return BlockEvaluation(
        status=status,
        reason="stub",
        raw_score=final_score,
        final_score=final_score,
        best_level=best_level,
    )


# ── (a) make_final_decision: lone FLAGGED block must not be approved ──────────


def test_single_flagged_block_alone_is_flagged_not_approved(
    default_global_params: GlobalParams,
) -> None:
    """Regression (a): 1 FLAGGED block + ZERO approved must be FLAGGED_FINAL.

    Previously the special rule matched because ``len(score_flagged) == 1``
    and ``len(approved_blocks) == total_blocks - 1 == 0`` were both True, and
    ``all([])`` over the empty approved-scores list is vacuously True, so the
    article was wrongly APPROVED_FINAL.
    """
    evaluations = {"B1": _eval("FLAGGED", 6.0)}

    decision, reason = make_final_decision(evaluations, None, default_global_params)

    assert decision == "FLAGGED_FINAL", reason
    assert "approved" not in reason.lower() or "0 approved" not in reason.lower()


# ── (a') legitimate special rule: 1 flagged + others approved >= threshold ────


def test_special_rule_approves_when_others_approved_above_threshold(
    default_global_params: GlobalParams,
) -> None:
    """The legitimate special rule still fires with >=1 approved block."""
    params = replace(default_global_params, special_approval_threshold=40.0)
    evaluations = {
        "B1": _eval("APPROVED", 50.0),
        "B2": _eval("APPROVED", 45.0),
        "B3": _eval("FLAGGED", 7.0),
    }

    decision, reason = make_final_decision(evaluations, None, params)

    assert decision == "APPROVED_FINAL", reason
    assert "Special rule" in reason


def test_special_rule_does_not_apply_when_approved_below_threshold(
    default_global_params: GlobalParams,
) -> None:
    """If an approved block is below the special threshold, fall through to FLAGGED."""
    params = replace(default_global_params, special_approval_threshold=40.0)
    evaluations = {
        "B1": _eval("APPROVED", 30.0),  # below 40 threshold
        "B2": _eval("FLAGGED", 7.0),
    }

    decision, reason = make_final_decision(evaluations, None, params)

    assert decision == "FLAGGED_FINAL", reason


def test_all_blocks_approved_is_approved_final(
    default_global_params: GlobalParams,
) -> None:
    """Sanity: when every block is approved the result is APPROVED_FINAL."""
    evaluations = {
        "B1": _eval("APPROVED", 50.0),
        "B2": _eval("APPROVED", 60.0),
    }

    decision, reason = make_final_decision(evaluations, None, default_global_params)

    assert decision == "APPROVED_FINAL", reason


# ── (b) evaluate_block: zero score must not FLAG ──────────────────────────────


def test_zero_score_block_is_rejected_not_flagged(
    default_global_params: GlobalParams,
) -> None:
    """Regression (b): a block whose final score is 0 must be REJECTED.

    The default flagging threshold for an unconfigured level is 0, and the
    old condition ``final_score >= flagging_threshold`` turned a 0.0 score
    into FLAGGED. A zero score means no scoring evidence and must reject.
    """
    # Level 9 is not in approval/flagging thresholds → flagging_threshold
    # defaults to 0; level 9 is not in level_scores → contributes score 0.
    block_config = _block(_positive("widget", level=9, scope="title"))

    result = evaluate_block(
        title="a widget paper",
        abstract="",
        manual_tags="",
        block_config=block_config,
        global_params=default_global_params,
    )

    assert result.final_score == 0.0
    assert result.status == "REJECTED", result.reason


def test_positive_score_at_flag_threshold_still_flags(
    default_global_params: GlobalParams,
) -> None:
    """A genuinely positive score at/above the flag threshold still FLAGS."""
    # Level 1 → score 10 in title with weight 2.0 → 20 raw; approval is 10,
    # so it would APPROVE. Use level 5 (weak) where approval is None and
    # flagging threshold is 12: title weight 2.0 * level-5 score 2 = 4 < 12
    # → REJECTED, so instead craft a score that lands in the flag band.
    # Level 4: score 4, title weight 2.0 → 8 == flagging_threshold(4)=8,
    # approval(4)=22 not met → FLAGGED.
    block_config = _block(_positive("gadget", level=4, scope="title"))

    result = evaluate_block(
        title="gadget study",
        abstract="",
        manual_tags="",
        block_config=block_config,
        global_params=default_global_params,
    )

    assert result.final_score > 0
    assert result.status == "FLAGGED", result.reason


# ── evaluate_block / _compute_section_scores happy path ───────────────────────


def test_evaluate_block_happy_path_approved(
    default_global_params: GlobalParams,
) -> None:
    """A strong level-1 title hit clears the approval threshold."""
    block_config = _block(_positive("blockchain", level=1, scope="title"))

    result = evaluate_block(
        title="a blockchain survey",
        abstract="",
        manual_tags="",
        block_config=block_config,
        global_params=default_global_params,
    )

    # level 1 score 10 * title weight 2.0 = 20 raw; no manual_tags so the
    # no-tags uplift (1.17) applies → 20 * 1.17 = 23.4 final.
    assert result.best_level == 1
    assert result.raw_score == pytest.approx(20.0)
    assert result.uplift_applied is True
    assert result.final_score == pytest.approx(23.4)
    assert result.status == "APPROVED", result.reason


def test_compute_section_scores_dedups_levels_and_weights(
    default_global_params: GlobalParams,
) -> None:
    """_compute_section_scores counts each level once per section and weights it."""
    from fastslr.core.models import TermMatch

    matches = {
        "title": [
            TermMatch(term="alpha", level=1, section="title", source_row=None),
            TermMatch(term="beta", level=1, section="title", source_row=None),
        ],
        "abstract": [],
        "manual_tags": [],
    }

    section_scores, raw_score = _compute_section_scores(matches, default_global_params)

    # Two level-1 hits in title collapse to a single level-1 score (10) * 2.0.
    assert section_scores["title"] == pytest.approx(20.0)
    assert section_scores["abstract"] == pytest.approx(0.0)
    assert raw_score == pytest.approx(20.0)


# ── find-positive-terms-int-level-crash: non-numeric level must not crash ─────


def test_non_numeric_level_is_ignored_not_crashing() -> None:
    """Regression (find-positive-terms-int-level-crash): a term whose ``level``
    is non-numeric must not raise ``ValueError``/``TypeError``.

    ``find_positive_terms`` calls ``int(level)`` to register the found level.
    The surrounding ``try/except`` only caught ``re.error``, so a non-numeric
    level (reachable via the public API) crashed instead of being ignored. The
    term should still be recorded as a match, but its invalid level must not be
    added to ``found_levels``.
    """
    term = {
        "term": "foo",
        "original_term": "foo",
        "level": "notanumber",
        "scope": "any",
        "pattern": re.compile("foo"),
        "source_row": None,
    }

    found_levels, matches = find_positive_terms("foo", "", "", [term])

    # Invalid level is silently ignored: it never reaches found_levels.
    assert found_levels == set()
    # The match itself is still recorded (with its raw level preserved).
    title_terms = matches["title"]
    assert len(title_terms) == 1
    assert title_terms[0].term == "foo"


def test_numeric_string_level_is_coerced() -> None:
    """A numeric-string level is still coerced to int and registered."""
    term = {
        "term": "bar",
        "original_term": "bar",
        "level": "2",
        "scope": "any",
        "pattern": re.compile("bar"),
        "source_row": None,
    }

    found_levels, _ = find_positive_terms("bar", "", "", [term])

    assert found_levels == {2}


# ── (c) parse_terms_csv: out-of-range level neutralised ───────────────────────


def test_out_of_range_level_makes_block_rejected(tmp_path: Path) -> None:
    """Regression (c): a positive term at a level outside configured levels
    must be neutralised (level cleared) so the block scores 0 and REJECTS.

    Previously the parser only emitted a warning but kept ``level='6'``,
    yielding best_level=6, score 0 and a spurious FLAGGED block.
    """
    terms_csv = tmp_path / "terms.csv"
    terms_csv.write_text(
        "block,kind,term,level,section_scope,is_regex\nB1,pos,quantum,6,title,0\n",
        encoding="utf-8",
    )

    base_config = {
        "global": {
            "PONTUACAO_NIVEIS": {1: 10, 2: 8, 3: 6, 4: 4, 5: 2},
        }
    }

    config = parse_terms_csv(terms_csv, base_config)

    # parse_terms_csv stores each block directly under its name in config.
    positives = config["B1"]["positives"]
    assert len(positives) == 1
    # Level must be cleared (None) so the term contributes no score.
    assert positives[0]["level"] is None
