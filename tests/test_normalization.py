"""Tests for the NormalizationEngine and rule extraction."""

from __future__ import annotations

import pandas as pd

from fastslr.core.normalization import extract_normalization_rules


class TestNormalizationEngine:
    def test_disabled_returns_lowered_collapsed(self, normalization_engine_disabled):
        result = normalization_engine_disabled.normalize("  Hello   WORLD  ")
        assert result == "hello world"

    def test_empty_string(self, normalization_engine_enabled):
        assert normalization_engine_enabled.normalize("") == ""

    def test_abbreviation_expansion(self, normalization_engine_enabled):
        result = normalization_engine_enabled.normalize("AI in supply-chain")
        assert "artificial intelligence" in result

    def test_compound_variant_unification(self, normalization_engine_enabled):
        result = normalization_engine_enabled.normalize("supply-chain management")
        assert "supply chain" in result

    def test_symbol_replacement(self, normalization_engine_enabled):
        result = normalization_engine_enabled.normalize("oil & gas")
        assert "oil and gas" in result

    def test_whitespace_collapse(self, normalization_engine_enabled):
        result = normalization_engine_enabled.normalize("  too   many    spaces  ")
        assert "  " not in result
        assert result == result.strip()

    def test_lru_cache_returns_same_result(self, normalization_engine_enabled):
        text = "AI in oil & gas supply-chain"
        result1 = normalization_engine_enabled.normalize(text)
        result2 = normalization_engine_enabled.normalize(text)
        assert result1 == result2

    def test_case_insensitive_abbreviation(self, normalization_engine_enabled):
        # "AI" should match regardless of case in source
        result = normalization_engine_enabled.normalize("ai applications")
        assert "artificial intelligence" in result


class TestExtractNormalizationRules:
    def test_missing_columns_returns_disabled(self):
        df = pd.DataFrame({"term": ["test"], "kind": ["pos"]})
        rules = extract_normalization_rules(df)
        assert rules["enabled"] is False
        assert rules["abbreviations"] == {}

    def test_extracts_abbreviations(self):
        df = pd.DataFrame(
            {
                "term": ["AI", "ML"],
                "normalization_type": ["abbreviation", "abbreviation"],
                "normalization_target": [
                    "artificial intelligence",
                    "machine learning",
                ],
            }
        )
        rules = extract_normalization_rules(df)
        assert rules["enabled"] is True
        assert "ai" in rules["abbreviations"]
        assert rules["abbreviations"]["ai"] == "artificial intelligence"

    def test_extracts_compound_variants(self):
        df = pd.DataFrame(
            {
                "term": ["supply-chain"],
                "normalization_type": ["compound_variant"],
                "normalization_target": ["supply chain"],
            }
        )
        rules = extract_normalization_rules(df)
        assert "supply-chain" in rules["compound_variants"]

    def test_extracts_symbol_replacements(self):
        df = pd.DataFrame(
            {
                "term": ["&"],
                "normalization_type": ["symbol_replacement"],
                "normalization_target": ["and"],
            }
        )
        rules = extract_normalization_rules(df)
        assert rules["symbol_replacements"]["&"] == "and"

    def test_skips_invalid_rows(self):
        df = pd.DataFrame(
            {
                "term": ["AI", ""],
                "normalization_type": ["abbreviation", "abbreviation"],
                "normalization_target": ["artificial intelligence", "nothing"],
            }
        )
        rules = extract_normalization_rules(df)
        assert len(rules["abbreviations"]) == 1
