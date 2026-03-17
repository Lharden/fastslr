"""Text normalization engine with LRU-cached transformations."""

from __future__ import annotations

import re

import pandas as pd


class NormalizationEngine:
    """Rule-based text normalization engine with LRU cache.

    Applies abbreviation expansion, compound-variant unification,
    and symbol replacement in a deterministic order.
    """

    def __init__(self, rules: dict) -> None:
        self.rules = rules
        self.enabled = rules.get("enabled", False)
        self._abbreviations = {
            k.lower(): v.lower() for k, v in rules.get("abbreviations", {}).items()
        }
        self._compounds = {
            k.lower(): v.lower() for k, v in rules.get("compound_variants", {}).items()
        }
        self._symbols = rules.get("symbol_replacements", {})
        self._cache_maxsize = 2000
        self._cache: dict[str, str] = {}
        self._cache_order: list[str] = []

    def normalize(self, text: str) -> str:
        """Normalize *text* with per-instance LRU caching."""
        if not text:
            return ""

        cache_key = str(text)
        if cache_key in self._cache:
            self._cache_order.remove(cache_key)
            self._cache_order.append(cache_key)
            return self._cache[cache_key]

        normalized = self._normalize_uncached(cache_key)

        if len(self._cache_order) >= self._cache_maxsize:
            oldest_key = self._cache_order.pop(0)
            self._cache.pop(oldest_key, None)

        self._cache[cache_key] = normalized
        self._cache_order.append(cache_key)
        return normalized

    def _normalize_uncached(self, text: str) -> str:
        """Normalize *text* by applying all configured rules.

        Returns the lowercased, whitespace-collapsed result.
        """
        if not text:
            return ""

        if not self.enabled:
            return re.sub(r"\s+", " ", text.lower().strip())

        normalized = str(text).strip()

        for abbr, expanded in self._abbreviations.items():
            pattern = rf"\b{re.escape(abbr)}\b"
            normalized = re.sub(pattern, expanded, normalized, flags=re.IGNORECASE)

        normalized = normalized.lower()

        for symbol, replacement in self._symbols.items():
            if re.search(r"[A-Za-z]", symbol):
                normalized = re.sub(rf"\b{re.escape(symbol)}\b", replacement, normalized)
            else:
                normalized = normalized.replace(symbol, replacement)

        for variant, standard in self._compounds.items():
            normalized = re.sub(rf"\b{re.escape(variant)}\b", standard, normalized)

        return re.sub(r"\s+", " ", normalized).strip()


def extract_normalization_rules(df: pd.DataFrame) -> dict:
    """Extract normalization rules from the terms CSV DataFrame.

    Looks for ``normalization_type`` and ``normalization_target`` columns.
    Returns a dict suitable for :class:`NormalizationEngine`.
    """
    rules: dict = {
        "abbreviations": {},
        "compound_variants": {},
        "symbol_replacements": {},
        "enabled": False,
    }

    required_cols = ["normalization_type", "normalization_target"]
    if not all(col in df.columns for col in required_cols):
        return rules

    processed_count = 0

    for _idx, row in df.iterrows():
        try:
            norm_type = str(row.get("normalization_type", "")).strip().lower()
            norm_target = str(row.get("normalization_target", "")).strip()
            term = str(row.get("term", "")).strip()

            if not norm_type or not term or pd.isna(norm_type) or not norm_target:
                continue

            if norm_type == "abbreviation":
                rules["abbreviations"][term.lower()] = norm_target.lower()
            elif norm_type == "compound_variant":
                rules["compound_variants"][term.lower()] = norm_target.lower()
            elif norm_type == "symbol_replacement":
                rules["symbol_replacements"][term] = norm_target

            processed_count += 1
        except (KeyError, TypeError, ValueError):
            continue

    if processed_count > 0:
        rules["enabled"] = True

    return rules


__all__ = ["NormalizationEngine", "extract_normalization_rules"]
