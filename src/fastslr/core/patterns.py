"""Pattern compilation: wildcards, proximity, and block precompilation."""

from __future__ import annotations

import logging
import re

from .models import GlobalParams
from .normalization import NormalizationEngine

logger = logging.getLogger(__name__)

# An inner variable quantifier (*, + or an interval WITH a comma such as
# {2,} / {2,4}) inside a repeated group is exponentially ambiguous; an exact
# count like {2} partitions unambiguously and stays allowed.
_UNSAFE_NESTED_QUANTIFIER_RE = re.compile(
    r"\((?:[^()\\]|\\.)*(?:[*+]|\{\d*,\d*\})(?:[^()\\]|\\.)*\)\s*(?:[*+]|\{\d*,?\d*\})"
)


def _conditional_boundaries(term: str, body: str) -> str:
    """Wrap *body* with boundary anchors conditional on *term*'s edge chars.

    ``\\b`` only asserts a boundary between a word char and a non-word char,
    so anchoring a term whose edge is a non-word char (``C++``, ``.NET``)
    either never matches or matches the wrong span. Instead we use
    lookarounds that only constrain the edge when it is a word char:

    * leading edge is a word char  -> prefix ``(?<!\\w)``
    * trailing edge is a word char -> suffix ``(?!\\w)``

    When an edge is a non-word char the constraint is relaxed on that side,
    allowing e.g. ``C++`` to match inside ``C++ language``.
    """
    prefix = r"(?<!\w)" if term[:1].isalnum() or term[:1] == "_" else ""
    suffix = r"(?!\w)" if term[-1:].isalnum() or term[-1:] == "_" else ""
    return f"{prefix}{body}{suffix}"


def compile_pattern(term: str, is_regex: bool = False) -> re.Pattern | None:
    """Compile a search term into a case-insensitive regex pattern.

    Supports wildcard expansion (``*`` -> ``\\w*``) for non-regex terms.
    Returns ``None`` for empty or invalid patterns.
    """
    if not term or not term.strip():
        return None

    term = term.strip()

    if is_regex:
        if _UNSAFE_NESTED_QUANTIFIER_RE.search(term):
            logger.warning("Rejected unsafe regex with nested quantifiers: %r", term)
            return None
        try:
            return re.compile(term, re.IGNORECASE)
        except re.error:
            logger.debug("Invalid regex pattern: %s", term)
            return None

    escaped = re.escape(term)
    # Restore wildcard: re.escape turns '*' into '\\*'
    escaped = escaped.replace(r"\*", r"\w*")
    pattern_str = _conditional_boundaries(term, escaped)

    try:
        return re.compile(pattern_str, re.IGNORECASE)
    except re.error:
        logger.debug("Failed to compile pattern for term: %s", term)
        return None


# Separator allowed between proximity terms: whitespace, hyphen or slash, so
# 'oil and gas', 'oil-and-gas' and 'oil/gas' match. Dot and comma are not
# separators: proximity must not cross a sentence ('engine oil. Gas turbines')
# or a list ('food, oil, natural gas').
_PROXIMITY_SEP = r"[\s\-/]+"

# Default intervening-token unit. Used as fallback when a caller-supplied
# token_unit is not explicitly allowlisted.
_DEFAULT_TOKEN_UNIT = r"\S+"
_ALLOWED_TOKEN_UNITS = frozenset({_DEFAULT_TOKEN_UNIT, r"\w+"})


def _safe_token_unit(token_unit: str) -> str:
    """Allowlist *token_unit*, falling back to ``\\S+``.

    The token unit is interpolated verbatim into the proximity gap. An
    arbitrary fragment can disable proximity, over-match, or introduce
    catastrophic backtracking after composition. Only reviewed exact values
    are accepted; all others fall back to the safe default with a warning.
    """
    if token_unit not in _ALLOWED_TOKEN_UNITS:
        logger.warning(
            "token_unit for proximity gap is not allowlisted: %r; falling back to %r",
            token_unit,
            _DEFAULT_TOKEN_UNIT,
        )
        return _DEFAULT_TOKEN_UNIT
    return token_unit


def compile_proximity_pattern(
    term_a: str,
    term_b: str,
    max_gap: int = 3,
    token_unit: str = _DEFAULT_TOKEN_UNIT,
) -> re.Pattern | None:
    """Create a bidirectional proximity pattern for two terms.

    Matches ``term_a <sep> term_b`` or ``term_b <sep> term_a`` with at most
    *max_gap* intervening tokens, where ``<sep>`` is one or more whitespace,
    hyphen or slash characters (see ``_PROXIMITY_SEP``). A ``*`` in a term is
    a wildcard (``\\w*``), as in :func:`compile_pattern`.

    A negative *max_gap* is clamped to ``0`` (with a warning): the historical
    behaviour produced a regex quantifier ``{0,-1}`` which Python silently
    treats as a literal, so proximity never matched. *token_unit* is validated
    against an allowlist and falls back to ``\\S+`` when rejected.
    """
    if not term_a or not term_a.strip() or not term_b or not term_b.strip():
        return None

    if max_gap < 0:
        logger.warning("max_gap %d is negative; clamping to 0", max_gap)
        max_gap = 0

    token_unit = _safe_token_unit(token_unit)

    term_a_s = term_a.strip()
    term_b_s = term_b.strip()
    a = re.escape(term_a_s).replace(r"\*", r"\w*")
    b = re.escape(term_b_s).replace(r"\*", r"\w*")
    gap = rf"(?:{_PROXIMITY_SEP}{token_unit}){{0,{max_gap}}}{_PROXIMITY_SEP}"

    # Conditional boundary on the outer edges of each alternative; the inner
    # edges are separated by the gap, so they need no anchor.
    a_lead = r"(?<!\w)" if term_a_s[:1].isalnum() or term_a_s[:1] == "_" else ""
    a_tail = r"(?!\w)" if term_a_s[-1:].isalnum() or term_a_s[-1:] == "_" else ""
    b_lead = r"(?<!\w)" if term_b_s[:1].isalnum() or term_b_s[:1] == "_" else ""
    b_tail = r"(?!\w)" if term_b_s[-1:].isalnum() or term_b_s[-1:] == "_" else ""

    pattern_str = rf"{a_lead}{a}{gap}{b}{b_tail}|{b_lead}{b}{gap}{a}{a_tail}"

    try:
        return re.compile(pattern_str, re.IGNORECASE)
    except re.error:
        logger.debug("Failed to compile proximity pattern: %s <-> %s", term_a, term_b)
        return None


# Splits a compound term on every 'and' / '&' / 'or' connector (whitespace
# delimited) or '/' separator, not just the first one. ``and``/``or`` require
# surrounding whitespace so they are not stripped from inside words (e.g.
# 'brand', 'category'); '&' and '/' are recognised with or without spaces.
_COMPOUND_SPLIT_RE = re.compile(
    r"\s+(?:and|or)\s+|\s*&\s*|\s*/\s*",
    re.IGNORECASE,
)


def detect_compound_terms(term: str) -> list[tuple[str, str]]:
    """Detect compound terms connected by 'and', '&', 'or', or '/'.

    Splits on *every* connector (not only the first) and returns sequential
    adjacent ``(part_a, part_b)`` pairs. For two components this yields a
    single pair (``'oil and gas'`` -> ``[('oil', 'gas')]``); for three or more
    it yields one pair per adjacent component (``'A and B and C'`` ->
    ``[('A', 'B'), ('B', 'C')]``) so each part becomes a real proximity term
    instead of an unmatchable literal like ``'B and C'``.
    """
    parts = [p.strip() for p in _COMPOUND_SPLIT_RE.split(term.strip())]
    parts = [p for p in parts if p]
    if len(parts) < 2:
        return []
    return [(parts[i], parts[i + 1]) for i in range(len(parts) - 1)]


# A literal hyphen between two word characters in a regex term, outside a
# character class and not part of an escape such as ``\d-``.
_WORD_HYPHEN_IN_REGEX = re.compile(r"(?<!\\)\w-\w")
_CHAR_CLASS_RE = re.compile(r"\[(?:\\.|[^\]\\])*\]")


def _strip_classes(regex: str) -> str:
    """Remove ``[...]`` character classes, whose ``a-z`` ranges are not hyphens."""
    return _CHAR_CLASS_RE.sub("", regex)


def _entry_is_regex(entry: dict) -> bool:
    """Return the entry's regex flag, accepting the 'regex' and 'is_regex' keys."""
    is_regex = entry.get("regex", entry.get("is_regex", False))
    if isinstance(is_regex, str):
        return is_regex.lower() in ("1", "true", "yes")
    return bool(is_regex)


def _row_label(entry: dict) -> object:
    """Line of the terms file the entry came from (already 1-based), or '?'."""
    row = entry.get("source_row")
    return row if row is not None else "?"


# Proximity is generated only for components of at least two characters. The
# acronyms 'O&G' and 'E&P' normalize to 'o and g' / 'e and p': they match as
# exact phrases, and an 'o'..'g' or 'e'..'p' proximity would match any two
# single letters close together ('p = 0.01 e.g.').
_MIN_PROXIMITY_COMPONENT_LEN = 2


def _compile_term_entry(
    entry: dict,
    is_anti: bool = False,
    normalization_engine: NormalizationEngine | None = None,
    warnings: list[str] | None = None,
    block_name: str = "",
) -> dict | None:
    """Compile a single term entry, adding a 'pattern' key."""
    term = entry.get("term", "").strip()
    if not term:
        return None

    is_regex = _entry_is_regex(entry)

    if is_regex and warnings is not None and _WORD_HYPHEN_IN_REGEX.search(_strip_classes(term)):
        warnings.append(
            f"Row {_row_label(entry)}, block '{block_name}', term '{term}': regex term has "
            f"a hyphen between word characters, but text normalization reads such hyphens "
            f"as spaces, so it can never match. Use '[\\s-]' or a space instead."
        )

    match_term = term
    if normalization_engine is not None and not is_regex:
        normalized_term = normalization_engine.normalize(term)
        if normalized_term:
            match_term = normalized_term

    pattern = compile_pattern(match_term, is_regex=is_regex)
    if pattern is None:
        if warnings is not None and is_regex:
            warnings.append(
                f"Row {_row_label(entry)}, block '{block_name}', term '{term}': "
                f"invalid or unsafe regex pattern. Term excluded from analysis."
            )
        return None

    compiled = dict(entry)
    compiled["pattern"] = pattern
    compiled["original_term"] = term
    compiled["match_term"] = match_term

    highlight_patterns = []
    original_pattern = compile_pattern(term, is_regex=is_regex)
    if original_pattern is not None:
        highlight_patterns.append(original_pattern)
    if match_term != term and not is_regex:
        match_pattern = compile_pattern(match_term)
        if match_pattern is not None:
            highlight_patterns.append(match_pattern)
    compiled["highlight_patterns"] = highlight_patterns

    if not is_anti:
        level = entry.get("level")
        if level is not None and level != "":
            try:
                compiled["level"] = int(level)
            except (ValueError, TypeError):
                compiled["level"] = None
        else:
            compiled["level"] = None

    return compiled


def precompile_patterns(
    block: dict,
    normalization_engine: NormalizationEngine | None = None,
    global_params: GlobalParams | None = None,
    block_name: str = "",
    warnings: list[str] | None = None,
) -> dict:
    """Compile all patterns in a block configuration.

    Returns a new dict with compiled 'positives', 'anti_exclude',
    'anti_flag', and 'proximity_positives' lists.
    """
    compiled_block = dict(block)

    # Compile positives
    compiled_positives = []
    for entry in block.get("positives", []):
        compiled = _compile_term_entry(
            entry,
            normalization_engine=normalization_engine,
            warnings=warnings,
            block_name=block_name,
        )
        if compiled is not None:
            compiled_positives.append(compiled)
    compiled_block["positives"] = compiled_positives

    # Compile anti terms
    anti = block.get("anti", {})
    compiled_exclude = []
    for entry in anti.get("exclude", []):
        compiled = _compile_term_entry(
            entry,
            is_anti=True,
            normalization_engine=normalization_engine,
            warnings=warnings,
            block_name=block_name,
        )
        if compiled is not None:
            compiled_exclude.append(compiled)
    compiled_block["anti_exclude"] = compiled_exclude

    compiled_flag = []
    for entry in anti.get("flag", []):
        compiled = _compile_term_entry(
            entry,
            is_anti=True,
            normalization_engine=normalization_engine,
            warnings=warnings,
            block_name=block_name,
        )
        if compiled is not None:
            compiled_flag.append(compiled)
    compiled_block["anti_flag"] = compiled_flag

    # Generate proximity positives from compound terms
    max_gap = 3
    token_unit = r"\S+"
    enable_proximity = True

    if global_params is not None:
        max_gap = global_params.max_gap_between_terms
        token_unit = global_params.token_unit_for_gaps
        enable_proximity = global_params.enable_proximity_detection

    proximity_positives = []
    if enable_proximity:
        for entry in compiled_positives:
            # A regex term is a pattern, not a phrase: splitting it on 'and'/'/'
            # would produce fragments that are neither regex nor literal.
            if _entry_is_regex(entry):
                continue
            compounds = detect_compound_terms(
                entry.get("match_term") or entry.get("original_term", "")
            )
            for part_a, part_b in compounds:
                if min(len(part_a), len(part_b)) < _MIN_PROXIMITY_COMPONENT_LEN:
                    continue
                prox_pattern = compile_proximity_pattern(
                    part_a, part_b, max_gap=max_gap, token_unit=token_unit
                )
                if prox_pattern is not None:
                    highlight_patterns = []
                    original_pattern = compile_pattern(entry.get("original_term", ""))
                    if original_pattern is not None:
                        highlight_patterns.append(original_pattern)
                    proximity_positives.append(
                        {
                            "term": entry.get("original_term", ""),
                            "original_term": entry.get("original_term", ""),
                            "match_term": entry.get("match_term", ""),
                            "pattern": prox_pattern,
                            "highlight_patterns": highlight_patterns,
                            "level": entry.get("level"),
                            "scope": entry.get("scope", "any"),
                            "source_row": entry.get("source_row"),
                            "is_proximity": True,
                            "components": (part_a, part_b),
                        }
                    )

    compiled_block["proximity_positives"] = proximity_positives

    return compiled_block


__all__ = [
    "compile_pattern",
    "compile_proximity_pattern",
    "detect_compound_terms",
    "precompile_patterns",
]
