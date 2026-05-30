"""Regression tests for proximity-pattern and compound-term findings.

Covers four audit findings (see vault/Validação - Auditoria Completa.md):

* proximity-negative-gap-literal-no-match
* proximity-requires-adjacent-space
* compound-splits-only-first-separator
* proximity-token-unit-injection
"""

from __future__ import annotations

import logging

from fastslr.core.patterns import (
    _safe_token_unit,
    compile_proximity_pattern,
    detect_compound_terms,
)


class TestNegativeGapClamp:
    """proximity-negative-gap-literal-no-match.

    ``max_gap=-1`` used to produce the quantifier ``{0,-1}`` which Python
    silently treats as literal text, so the pattern never matched. It must be
    clamped to 0 and still match an adjacent occurrence.
    """

    def test_negative_gap_clamped_matches_adjacent(self):
        pat = compile_proximity_pattern("machine", "learning", max_gap=-1)
        assert pat is not None
        assert pat.search("machine learning")

    def test_negative_gap_does_not_match_with_gap_token(self):
        # Clamped to 0: no intervening tokens allowed.
        pat = compile_proximity_pattern("machine", "learning", max_gap=-1)
        assert pat is not None
        assert not pat.search("machine of learning")

    def test_negative_gap_emits_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            compile_proximity_pattern("machine", "learning", max_gap=-5)
        assert any("clamp" in r.message.lower() for r in caplog.records)


class TestNonSpaceSeparators:
    """proximity-requires-adjacent-space.

    Hyphen / slash / comma separated compounds must match, not only the
    space-separated form.
    """

    def test_hyphenated_compound_matches(self):
        pat = compile_proximity_pattern("machine", "learning", max_gap=0)
        assert pat is not None
        assert pat.search("machine-learning")

    def test_slash_compound_matches(self):
        pat = compile_proximity_pattern("input", "output", max_gap=0)
        assert pat is not None
        assert pat.search("input/output")

    def test_comma_compound_matches(self):
        pat = compile_proximity_pattern("machine", "learning", max_gap=0)
        assert pat is not None
        assert pat.search("machine,learning")

    def test_plain_space_still_matches(self):
        pat = compile_proximity_pattern("machine", "learning", max_gap=0)
        assert pat is not None
        assert pat.search("machine learning")

    def test_reverse_order_hyphen_matches(self):
        pat = compile_proximity_pattern("machine", "learning", max_gap=0)
        assert pat is not None
        assert pat.search("learning-machine")


class TestRecursiveCompoundSplit:
    """compound-splits-only-first-separator.

    A 3+ component compound must split on every connector, producing sequential
    adjacent pairs instead of one pair whose second member is an unmatchable
    literal like ``'B and C'``.
    """

    def test_three_part_and(self):
        result = detect_compound_terms("A and B and C")
        assert result == [("A", "B"), ("B", "C")]

    def test_three_part_slash(self):
        result = detect_compound_terms("A/B/C")
        assert result == [("A", "B"), ("B", "C")]

    def test_mixed_connectors(self):
        result = detect_compound_terms("oil and gas / petroleum")
        assert result == [("oil", "gas"), ("gas", "petroleum")]

    def test_two_part_unchanged(self):
        # Backward-compatible with the original 2-part contract.
        assert detect_compound_terms("oil and gas") == [("oil", "gas")]
        assert detect_compound_terms("oil & gas") == [("oil", "gas")]
        assert detect_compound_terms("supply/demand") == [("supply", "demand")]

    def test_no_compound(self):
        assert detect_compound_terms("machine learning") == []

    def test_connector_not_split_inside_word(self):
        # 'and'/'or' need surrounding whitespace; 'brand' must not split.
        assert detect_compound_terms("brand") == []
        assert detect_compound_terms("category") == []

    def test_three_part_pairs_compile_individually(self):
        # Each emitted pair must be a usable proximity pattern (not a literal
        # 'B and C' that almost never matches).
        for part_a, part_b in detect_compound_terms("A and B and C"):
            pat = compile_proximity_pattern(part_a, part_b, max_gap=0)
            assert pat is not None
        # The pair ('B', 'C') matches the adjacent text directly.
        pat_bc = compile_proximity_pattern("B", "C", max_gap=0)
        assert pat_bc is not None
        assert pat_bc.search("B C")


class TestTokenUnitInjection:
    """proximity-token-unit-injection.

    An invalid token_unit fragment must fall back to ``\\S+`` (with warning)
    instead of silently disabling proximity or over-matching.
    """

    def test_invalid_token_unit_falls_back(self):
        pat = compile_proximity_pattern("oil", "gas", max_gap=2, token_unit="([")
        assert pat is not None
        assert pat.search("oil and gas")

    def test_invalid_token_unit_emits_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            _safe_token_unit("([")
        assert any("token_unit" in r.message.lower() for r in caplog.records)

    def test_valid_token_unit_preserved(self):
        assert _safe_token_unit(r"\w+") == r"\w+"

    def test_default_token_unit_valid(self):
        assert _safe_token_unit(r"\S+") == r"\S+"
