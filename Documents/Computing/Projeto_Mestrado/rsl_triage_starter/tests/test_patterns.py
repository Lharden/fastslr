"""Tests for pattern compilation, wildcards, and proximity detection."""

from __future__ import annotations

from fastslr.patterns import (
    compile_pattern,
    compile_proximity_pattern,
    detect_compound_terms,
    precompile_patterns,
)


class TestCompilePattern:
    def test_exact_match(self):
        pat = compile_pattern("oil and gas")
        assert pat is not None
        assert pat.search("the oil and gas industry")
        assert not pat.search("oilandgas")

    def test_word_boundary(self):
        pat = compile_pattern("oil")
        assert pat is not None
        assert pat.search("crude oil production")
        assert not pat.search("foiling plans")

    def test_wildcard_expansion(self):
        pat = compile_pattern("industr*")
        assert pat is not None
        assert pat.search("petroleum industry")
        assert pat.search("industrial applications")

    def test_regex_mode(self):
        pat = compile_pattern(r"supply\s+chain", is_regex=True)
        assert pat is not None
        assert pat.search("supply  chain management")

    def test_empty_returns_none(self):
        assert compile_pattern("") is None
        assert compile_pattern("   ") is None

    def test_invalid_regex_returns_none(self):
        assert compile_pattern("[invalid", is_regex=True) is None

    def test_case_insensitive(self):
        pat = compile_pattern("Machine Learning")
        assert pat is not None
        assert pat.search("machine learning")
        assert pat.search("MACHINE LEARNING")


class TestCompileProximityPattern:
    def test_forward_proximity(self):
        pat = compile_proximity_pattern("oil", "gas", max_gap=2)
        assert pat is not None
        assert pat.search("oil and gas industry")

    def test_reverse_proximity(self):
        pat = compile_proximity_pattern("oil", "gas", max_gap=2)
        assert pat is not None
        assert pat.search("gas from oil wells")

    def test_gap_exceeded(self):
        pat = compile_proximity_pattern("oil", "gas", max_gap=1)
        assert pat is not None
        # "oil xxx yyy zzz gas" has 3 tokens between — exceeds max_gap=1
        assert not pat.search("oil xxx yyy zzz gas")

    def test_empty_terms_return_none(self):
        assert compile_proximity_pattern("", "gas") is None
        assert compile_proximity_pattern("oil", "") is None


class TestDetectCompoundTerms:
    def test_and_connector(self):
        result = detect_compound_terms("oil and gas")
        assert len(result) == 1
        assert result[0] == ("oil", "gas")

    def test_ampersand_connector(self):
        result = detect_compound_terms("oil & gas")
        assert len(result) == 1
        assert result[0] == ("oil", "gas")

    def test_or_connector(self):
        result = detect_compound_terms("SCM or SCRM")
        assert len(result) == 1

    def test_slash_connector(self):
        result = detect_compound_terms("supply/demand")
        assert len(result) == 1

    def test_no_compound(self):
        result = detect_compound_terms("machine learning")
        assert len(result) == 0


class TestPrecompilePatterns:
    def test_compiles_positives(self):
        block = {
            "positives": [
                {"term": "oil and gas", "level": 1, "scope": "any", "regex": False}
            ],
            "anti": {"exclude": [], "flag": []},
        }
        compiled = precompile_patterns(block)
        assert len(compiled["positives"]) == 1
        assert "pattern" in compiled["positives"][0]

    def test_generates_proximity_positives(self):
        block = {
            "positives": [
                {"term": "oil and gas", "level": 1, "scope": "any", "regex": False}
            ],
            "anti": {"exclude": [], "flag": []},
        }
        compiled = precompile_patterns(block)
        assert compiled["proximity_positives"] is not None
        assert len(compiled["proximity_positives"]) >= 1

    def test_compiles_anti_terms(self):
        block = {
            "positives": [],
            "anti": {
                "exclude": [{"term": "vegetable oil", "regex": False}],
                "flag": [{"term": "biofuel", "regex": False}],
            },
        }
        compiled = precompile_patterns(block)
        assert len(compiled["anti_exclude"]) == 1
        assert len(compiled["anti_flag"]) == 1

    def test_skips_empty_terms(self):
        block = {
            "positives": [
                {"term": "", "level": 1, "scope": "any", "regex": False}
            ],
            "anti": {"exclude": [], "flag": []},
        }
        compiled = precompile_patterns(block)
        assert len(compiled["positives"]) == 0
