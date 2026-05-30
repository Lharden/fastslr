"""Text normalization engine with LRU-cached transformations."""

from __future__ import annotations

import re
from collections import OrderedDict

import pandas as pd


class NormalizationEngine:
    """Rule-based text normalization engine with LRU cache.

    Applies abbreviation expansion, compound-variant unification,
    and symbol replacement in a deterministic order.
    """

    def __init__(self, rules: dict) -> None:
        self.rules = rules
        self.enabled = rules.get("enabled", False)
        self._abbreviations = self._order_by_key_length(
            {k.lower(): v.lower() for k, v in rules.get("abbreviations", {}).items()}
        )
        self._compounds = self._order_by_key_length(
            {k.lower(): v.lower() for k, v in rules.get("compound_variants", {}).items()}
        )
        # ``symbol_replacements`` values are lowercased here so casefolding is
        # consistent: the symbol pass runs after the global ``.lower()`` and
        # would otherwise re-inject uppercase characters.
        self._symbols = self._order_by_key_length(
            {k.lower(): v.lower() for k, v in rules.get("symbol_replacements", {}).items()}
        )
        self._cache_maxsize = 2000
        # ``OrderedDict`` gives O(1) LRU bookkeeping via ``move_to_end`` and
        # ``popitem(last=False)`` for eviction.
        self._cache: OrderedDict[str, str] = OrderedDict()

    @staticmethod
    def _order_by_key_length(mapping: dict[str, str]) -> dict[str, str]:
        """Return *mapping* ordered by descending key length.

        Overlapping rules (where one key is a substring of another) must be
        applied most-specific-first so the output is independent of the CSV
        row order. Ties break on the key itself for full determinism.
        """
        return {k: mapping[k] for k in sorted(mapping, key=lambda key: (-len(key), key))}

    def normalize(self, text: str) -> str:
        """Normalize *text* with per-instance LRU caching."""
        if not text:
            return ""

        cache_key = str(text)
        if cache_key in self._cache:
            self._cache.move_to_end(cache_key)
            return self._cache[cache_key]

        normalized = self._normalize_uncached(cache_key)

        if len(self._cache) >= self._cache_maxsize:
            self._cache.popitem(last=False)

        self._cache[cache_key] = normalized
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
                # ``\b`` only asserts a boundary between a word and non-word
                # char, so anchoring a symbol whose edge is non-word ('c#',
                # 'c++', '.net') breaks. Anchor each edge conditionally.
                prefix = r"(?<!\w)" if symbol[:1].isalnum() or symbol[:1] == "_" else ""
                suffix = r"(?!\w)" if symbol[-1:].isalnum() or symbol[-1:] == "_" else ""
                pattern = rf"{prefix}{re.escape(symbol)}{suffix}"
                normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
            else:
                normalized = normalized.replace(symbol, replacement)

        for variant, standard in self._compounds.items():
            normalized = re.sub(rf"\b{re.escape(variant)}\b", standard, normalized)

        return re.sub(r"\s+", " ", normalized).strip()


_VALID_NORM_TYPES = frozenset({"abbreviation", "compound_variant", "symbol_replacement"})


def extract_normalization_rules(
    df: pd.DataFrame,
    warnings: list[str] | None = None,
) -> dict:
    """Extract normalization rules from the terms table DataFrame.

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

            row_num = int(str(_idx)) + 2 if _idx is not None else None

            # #2: normalization_target filled but type empty
            if (not norm_type or pd.isna(norm_type)) and norm_target:
                if warnings is not None:
                    warnings.append(
                        f"Row {row_num}, term '{term}': "
                        f"normalization_target is '{norm_target}' but normalization_type is empty. "
                        f"Normalization rule ignored."
                    )
                continue

            if not norm_type or pd.isna(norm_type):
                continue

            if norm_type not in _VALID_NORM_TYPES:
                if warnings is not None:
                    warnings.append(
                        f"Row {row_num}, term '{term}': "
                        f"invalid normalization_type '{norm_type}' "
                        f"(valid: {', '.join(sorted(_VALID_NORM_TYPES))}). "
                        f"Normalization rule ignored."
                    )
                continue

            if not norm_target:
                if warnings is not None:
                    warnings.append(
                        f"Row {row_num}, term '{term}': "
                        f"normalization_type is '{norm_type}' but normalization_target is empty. "
                        f"Normalization rule ignored."
                    )
                continue

            if not term:
                continue

            # #3: duplicate normalization rules
            existing = None
            if norm_type == "abbreviation":
                existing = rules["abbreviations"].get(term.lower())
            elif norm_type == "compound_variant":
                existing = rules["compound_variants"].get(term.lower())
            elif norm_type == "symbol_replacement":
                # Use the lowercased key + lowercased value for symmetry with
                # abbreviation/compound, so 'C#'/'c#' collapse to one rule and
                # identical rows do not trigger a false-positive warning.
                existing = rules["symbol_replacements"].get(term.lower())

            if existing is not None and existing != norm_target.lower():
                if warnings is not None:
                    warnings.append(
                        f"Row {row_num}, term '{term}': "
                        f"duplicate normalization rule (already mapped to '{existing}'). "
                        f"Overwriting with '{norm_target}'."
                    )

            if norm_type == "abbreviation":
                rules["abbreviations"][term.lower()] = norm_target.lower()
            elif norm_type == "compound_variant":
                rules["compound_variants"][term.lower()] = norm_target.lower()
            elif norm_type == "symbol_replacement":
                rules["symbol_replacements"][term.lower()] = norm_target.lower()

            processed_count += 1
        except (KeyError, TypeError, ValueError):
            continue

    if processed_count > 0:
        rules["enabled"] = True

    return rules


__all__ = ["NormalizationEngine", "extract_normalization_rules"]
