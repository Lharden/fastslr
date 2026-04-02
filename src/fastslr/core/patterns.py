"""Pattern compilation: wildcards, proximity, and block precompilation."""

from __future__ import annotations

import logging
import re

from .models import GlobalParams
from .normalization import NormalizationEngine

logger = logging.getLogger(__name__)


def compile_pattern(term: str, is_regex: bool = False) -> re.Pattern | None:
    """Compile a search term into a case-insensitive regex pattern.

    Supports wildcard expansion (``*`` -> ``\\w*``) for non-regex terms.
    Returns ``None`` for empty or invalid patterns.
    """
    if not term or not term.strip():
        return None

    term = term.strip()

    if is_regex:
        try:
            return re.compile(term, re.IGNORECASE)
        except re.error:
            logger.debug("Invalid regex pattern: %s", term)
            return None

    escaped = re.escape(term)
    # Restore wildcard: re.escape turns '*' into '\\*'
    escaped = escaped.replace(r"\*", r"\w*")
    pattern_str = rf"\b{escaped}\b"

    try:
        return re.compile(pattern_str, re.IGNORECASE)
    except re.error:
        logger.debug("Failed to compile pattern for term: %s", term)
        return None


def compile_proximity_pattern(
    term_a: str,
    term_b: str,
    max_gap: int = 3,
    token_unit: str = r"\S+",
) -> re.Pattern | None:
    """Create a bidirectional proximity pattern for two terms.

    Matches ``term_a ... term_b`` or ``term_b ... term_a`` with at most
    *max_gap* intervening tokens.
    """
    if not term_a or not term_a.strip() or not term_b or not term_b.strip():
        return None

    a = re.escape(term_a.strip())
    b = re.escape(term_b.strip())
    gap = rf"(?:\s+{token_unit}){{0,{max_gap}}}\s+"

    pattern_str = rf"\b{a}{gap}{b}\b|\b{b}{gap}{a}\b"

    try:
        return re.compile(pattern_str, re.IGNORECASE)
    except re.error:
        logger.debug("Failed to compile proximity pattern: %s <-> %s", term_a, term_b)
        return None


_COMPOUND_RE = re.compile(
    r"^(.+?)\s+(?:and|&|or)\s+(.+)$|^(.+?)\s*/\s*(.+)$",
    re.IGNORECASE,
)


def detect_compound_terms(term: str) -> list[tuple[str, str]]:
    """Detect compound terms connected by 'and', '&', 'or', or '/'.

    Returns a list of ``(part_a, part_b)`` tuples.
    """
    results: list[tuple[str, str]] = []
    m = _COMPOUND_RE.match(term.strip())
    if m:
        a = (m.group(1) or m.group(3) or "").strip()
        b = (m.group(2) or m.group(4) or "").strip()
        if a and b:
            results.append((a, b))
    return results


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

    is_regex = entry.get("regex", entry.get("is_regex", False))
    if isinstance(is_regex, str):
        is_regex = is_regex.lower() in ("1", "true", "yes")

    pattern = compile_pattern(term, is_regex=is_regex)
    if pattern is None:
        if warnings is not None and is_regex:
            row = entry.get("source_row")
            row_num = int(row) + 2 if row is not None else "?"
            warnings.append(
                f"Row {row_num}, block '{block_name}', term '{term}': "
                f"invalid regex pattern. Term excluded from analysis."
            )
        return None

    compiled = dict(entry)
    compiled["pattern"] = pattern
    compiled["original_term"] = term

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
            entry, normalization_engine=normalization_engine,
            warnings=warnings, block_name=block_name,
        )
        if compiled is not None:
            compiled_positives.append(compiled)
    compiled_block["positives"] = compiled_positives

    # Compile anti terms
    anti = block.get("anti", {})
    compiled_exclude = []
    for entry in anti.get("exclude", []):
        compiled = _compile_term_entry(
            entry, is_anti=True, normalization_engine=normalization_engine,
            warnings=warnings, block_name=block_name,
        )
        if compiled is not None:
            compiled_exclude.append(compiled)
    compiled_block["anti_exclude"] = compiled_exclude

    compiled_flag = []
    for entry in anti.get("flag", []):
        compiled = _compile_term_entry(
            entry, is_anti=True, normalization_engine=normalization_engine,
            warnings=warnings, block_name=block_name,
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
            compounds = detect_compound_terms(entry.get("original_term", ""))
            for part_a, part_b in compounds:
                prox_pattern = compile_proximity_pattern(
                    part_a, part_b, max_gap=max_gap, token_unit=token_unit
                )
                if prox_pattern is not None:
                    proximity_positives.append(
                        {
                            "term": entry.get("original_term", ""),
                            "original_term": entry.get("original_term", ""),
                            "pattern": prox_pattern,
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
