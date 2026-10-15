"""Text normalization engine with LRU-cached transformations."""

from __future__ import annotations

import html
import re
import unicodedata
from collections import OrderedDict

import pandas as pd

_SCIENTIFIC_MARKUP_RE = re.compile(r"</?(?:inf|sub|sup)\s*>", re.IGNORECASE)

# A hyphen joining two word characters ('machine-learning', 'on-time') is read
# as a space, in the text and in the terms alike, so the hyphenated and the
# spaced spellings of a compound match the same term. Hyphens that do not join
# two word characters ('pre- and post-', ' - ') are kept.
_WORD_HYPHEN_RE = re.compile(r"(?<=\w)-(?=\w)")


def _nfkc(value: str) -> str:
    return unicodedata.normalize("NFKC", value)


def _is_word(value: str) -> bool:
    """Return whether *value* (stripped) starts and ends with a word character."""
    stripped = value.strip()
    return bool(stripped) and stripped[0].isalnum() and stripped[-1].isalnum()


def _edge_anchors(key: str) -> tuple[str, str]:
    """Word-boundary anchors for *key*, only on the edges that are word characters.

    ``\\b`` next to a non-word edge never matches where it should: 'C#' at the
    end of a phrase, 'c++' or '.NET'. For a key with word edges on both sides
    the anchors are the same as ``\\b...\\b``.
    """
    prefix = r"(?<!\w)" if re.match(r"\w", key[:1]) else ""
    suffix = r"(?!\w)" if re.match(r"\w", key[-1:]) else ""
    return prefix, suffix


def _abbreviation_pattern(abbr: str) -> re.Pattern:
    """Pattern for an abbreviation key.

    A key with an uppercase letter keeps its case: it matches as written in the
    terms table and in all uppercase, so 'ML' expands but the unit in '5 ml'
    does not, and 'IoT' matches 'IoT' and 'IOT' but not 'iot'. An all-lowercase
    key says nothing about case, so 'iot' matches 'iot', 'IoT' and 'IOT'.
    """
    prefix, suffix = _edge_anchors(abbr)
    if abbr == abbr.lower():
        return re.compile(rf"{prefix}{re.escape(abbr)}{suffix}", re.IGNORECASE)
    forms = sorted({abbr, abbr.upper()}, key=lambda form: (-len(form), form))
    alternation = "|".join(re.escape(form) for form in forms)
    return re.compile(rf"{prefix}(?:{alternation}){suffix}")


def _symbol_substitution(symbol: str, replacement: str) -> str:
    """Return the text that replaces *symbol*.

    A symbol that stands for a word ('&' -> 'and', '/' -> 'or', 'w/' -> 'with')
    is replaced by that word delimited by spaces, so 'oil&gas' becomes
    'oil and gas' and not 'oilandgas'. A symbol that is itself letters (the
    ligature 'ﬁ' -> 'fi') or a target that is punctuation ('–' -> '-') is
    replaced in place.
    """
    if symbol.isalnum() or not _is_word(replacement):
        return replacement
    return f" {replacement} "


class NormalizationEngine:
    """Rule-based text normalization engine with LRU cache.

    Applies abbreviation expansion, symbol replacement, compound-variant
    unification and hyphen-between-words splitting in a deterministic order.
    """

    def __init__(self, rules: dict) -> None:
        self.rules = rules
        self.enabled = rules.get("enabled", False)
        # Abbreviation keys keep their case: expansion is case-sensitive. Every
        # key goes through NFKC, like the text it is matched against: a key
        # written with a compatibility character would otherwise never match.
        self._abbreviations = self._order_by_key_length(
            {_nfkc(k.strip()): v.lower() for k, v in rules.get("abbreviations", {}).items()}
        )
        self._abbreviation_patterns = [
            (_abbreviation_pattern(abbr), expanded)
            for abbr, expanded in self._abbreviations.items()
        ]
        self._compounds = self._order_by_key_length(
            {_nfkc(k).lower(): v.lower() for k, v in rules.get("compound_variants", {}).items()}
        )
        # ``symbol_replacements`` values are lowercased here so casefolding is
        # consistent: the symbol pass runs after the global ``.lower()`` and
        # would otherwise re-inject uppercase characters.
        # Symbol keys go through NFKC too, so a rule keyed on '½' applies to the
        # '1⁄2' the text becomes; a ligature key ('ﬁ' -> 'fi') turns into a no-op.
        self._symbols = self._order_by_key_length(
            {_nfkc(k).lower(): v.lower() for k, v in rules.get("symbol_replacements", {}).items()}
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

        # Entities and scientific markup are cleaned first, on both paths, so
        # 'oil &amp; gas' and 'CO<sub>2</sub>' reach the rules as 'oil & gas'
        # and 'CO2'. NFKC then gives one form to text that only looks the same:
        # decomposed accents ('gestão' exported in NFD), full-width letters
        # ('ＡＩ') and ligatures.
        normalized = html.unescape(str(text).strip())
        normalized = _SCIENTIFIC_MARKUP_RE.sub("", normalized)
        normalized = unicodedata.normalize("NFKC", normalized)

        if not self.enabled:
            return re.sub(r"\s+", " ", _WORD_HYPHEN_RE.sub(" ", normalized.lower())).strip()

        for pattern, expanded in self._abbreviation_patterns:
            normalized = pattern.sub(lambda _m, rep=expanded: rep, normalized)

        normalized = normalized.lower()

        for symbol, replacement in self._symbols.items():
            substitution = _symbol_substitution(symbol, replacement)
            if re.search(r"[A-Za-z]", symbol):
                # ``\b`` only asserts a boundary between a word and non-word
                # char, so anchoring a symbol whose edge is non-word ('c#',
                # 'c++', '.net') breaks. Anchor each edge conditionally.
                prefix = r"(?<!\w)" if symbol[:1].isalnum() or symbol[:1] == "_" else ""
                suffix = r"(?!\w)" if symbol[-1:].isalnum() or symbol[-1:] == "_" else ""
                pattern = rf"{prefix}{re.escape(symbol)}{suffix}"
                normalized = re.sub(
                    pattern, lambda _m, rep=substitution: rep, normalized, flags=re.IGNORECASE
                )
            else:
                normalized = normalized.replace(symbol, substitution)

        for variant, standard in self._compounds.items():
            prefix, suffix = _edge_anchors(variant)
            normalized = re.sub(
                rf"{prefix}{re.escape(variant)}{suffix}",
                lambda _m, rep=standard: rep,
                normalized,
            )

        # Last, so compound variants keyed on a hyphenated form ('e-procurement',
        # 'well-bore') still apply before the hyphen is read as a space.
        normalized = _WORD_HYPHEN_RE.sub(" ", normalized)

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
            raw_target = str(row.get("normalization_target", ""))
            norm_target = raw_target.strip()
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
                existing = rules["abbreviations"].get(term)
            elif norm_type == "compound_variant":
                existing = rules["compound_variants"].get(term.lower())
            elif norm_type == "symbol_replacement":
                # Use the lowercased key + lowercased value for symmetry with
                # abbreviation/compound, so 'C#'/'c#' collapse to one rule and
                # identical rows do not trigger a false-positive warning.
                existing = rules["symbol_replacements"].get(term.lower())

            # A symbol replacement keeps the spaces written around its target
            # (" and "); the engine delimits word targets with spaces anyway.
            stored_target = (
                raw_target.lower() if norm_type == "symbol_replacement" else norm_target.lower()
            )

            if existing is not None and existing != stored_target:
                if warnings is not None:
                    warnings.append(
                        f"Row {row_num}, term '{term}': "
                        f"duplicate normalization rule (already mapped to '{existing}'). "
                        f"Overwriting with '{norm_target}'."
                    )

            # Abbreviation keys keep their case, so 'ML' and 'ml' are two rules,
            # and both claim the text 'ML'. Which one wins would depend on the
            # sort order, so the overlap is reported.
            if norm_type == "abbreviation" and warnings is not None:
                for other, other_target in rules["abbreviations"].items():
                    if other != term and other.lower() == term.lower():
                        if other_target != stored_target:
                            warnings.append(
                                f"Row {row_num}, term '{term}': abbreviation rules '{other}' "
                                f"('{other_target}') and '{term}' ('{stored_target}') differ "
                                f"only in case and overlap on the same text."
                            )

            if norm_type == "abbreviation":
                # Case is kept: abbreviation expansion is case-sensitive.
                rules["abbreviations"][term] = stored_target
            elif norm_type == "compound_variant":
                rules["compound_variants"][term.lower()] = stored_target
            elif norm_type == "symbol_replacement":
                rules["symbol_replacements"][term.lower()] = stored_target

            processed_count += 1
        except (KeyError, TypeError, ValueError):
            continue

    if processed_count > 0:
        rules["enabled"] = True

    return rules


__all__ = ["NormalizationEngine", "extract_normalization_rules"]
