"""Regression tests for normalization determinism findings.

Covers:
- rule-order-dependent-output: overlapping symbol rules must produce the
  same output regardless of CSV row order (longest key first).
- symbol-replacement-value-not-lowercased: symbol replacement values must
  be lowercased so casefolding is consistent.
- dup-detection-symbol-case-asymmetry: symbol_replacement dedup key must be
  lowercased and compared symmetrically (no false-positive warnings).
- lru-cache-on-n: the per-instance LRU cache must evict the least-recently
  used key correctly (true LRU semantics).
"""

from __future__ import annotations

import pandas as pd

from fastslr.core.normalization import (
    NormalizationEngine,
    extract_normalization_rules,
)


class TestRuleOrderDeterminism:
    """rule-order-dependent-output: order of overlapping symbol keys."""

    def test_overlapping_symbol_order_independent(self) -> None:
        # '&' is a substring concern relative to 'r&d'. The two insertion
        # orders below must yield identical output for the same input.
        rules_a = {
            "enabled": True,
            "symbol_replacements": {"&": "and", "r&d": "research and development"},
        }
        rules_b = {
            "enabled": True,
            "symbol_replacements": {"r&d": "research and development", "&": "and"},
        }
        engine_a = NormalizationEngine(rules_a)
        engine_b = NormalizationEngine(rules_b)

        out_a = engine_a.normalize("r&d lab")
        out_b = engine_b.normalize("r&d lab")

        assert out_a == out_b
        # Longest key first => 'r&d' wins, not the bare '&'.
        assert out_a == "research and development lab"


class TestSymbolValueLowercased:
    """symbol-replacement-value-not-lowercased."""

    def test_symbol_value_is_lowercased(self) -> None:
        engine = NormalizationEngine({"enabled": True, "symbol_replacements": {"+": "Plus"}})
        result = engine.normalize("c++")
        # Must not leak uppercase from the replacement value.
        assert result == result.lower()
        assert result == "cplusplus"


class TestDupDetectionSymmetry:
    """dup-detection-symbol-case-asymmetry."""

    def test_identical_symbol_rows_no_spurious_warning(self) -> None:
        df = pd.DataFrame(
            {
                "term": ["+", "+"],
                "normalization_type": ["symbol_replacement", "symbol_replacement"],
                "normalization_target": ["Plus", "Plus"],
            }
        )
        warnings: list[str] = []
        rules = extract_normalization_rules(df, warnings)
        # No false-positive duplicate warning for identical rows.
        assert warnings == []
        # Key stored lowercased, value stored lowercased.
        assert rules["symbol_replacements"]["+"] == "plus"

    def test_symbol_key_case_collision_warns(self) -> None:
        df = pd.DataFrame(
            {
                "term": ["C#", "c#"],
                "normalization_type": ["symbol_replacement", "symbol_replacement"],
                "normalization_target": ["csharp", "different"],
            }
        )
        warnings: list[str] = []
        rules = extract_normalization_rules(df, warnings)
        # 'C#' and 'c#' collapse to one key; differing targets => warning.
        assert len(rules["symbol_replacements"]) == 1
        assert "c#" in rules["symbol_replacements"]
        assert len(warnings) == 1


class TestLruCacheCorrectness:
    """lru-cache-on-n: true LRU eviction semantics."""

    def test_lru_evicts_least_recently_used(self) -> None:
        engine = NormalizationEngine({"enabled": False})
        engine._cache_maxsize = 2

        engine.normalize("a")  # cache: [a]
        engine.normalize("b")  # cache: [a, b]
        engine.normalize("a")  # touch a -> cache: [b, a]
        engine.normalize("c")  # evicts b (LRU) -> cache: [a, c]

        assert "a" in engine._cache
        assert "c" in engine._cache
        assert "b" not in engine._cache

    def test_cache_returns_consistent_result(self) -> None:
        engine = NormalizationEngine({"enabled": True, "symbol_replacements": {"&": "and"}})
        first = engine.normalize("oil & gas")
        second = engine.normalize("oil & gas")
        assert first == second == "oil and gas"
