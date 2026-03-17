"""Import adapters for bibliographic reference formats."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ColumnMapping:
    """Maps bibliographic format columns to internal standard names."""

    id: str
    title: str
    abstract: str
    manual_tags: str | None = None


ZOTERO_MAPPING = ColumnMapping(
    id="Key",
    title="Title",
    abstract="Abstract Note",
    manual_tags="Manual Tags",
)

SCOPUS_MAPPING = ColumnMapping(
    id="EID",
    title="Title",
    abstract="Abstract",
    manual_tags="Author Keywords",
)

WOS_MAPPING = ColumnMapping(
    id="UT",
    title="TI",
    abstract="AB",
    manual_tags="DE",
)

KNOWN_FORMATS: dict[str, ColumnMapping] = {
    "zotero": ZOTERO_MAPPING,
    "scopus": SCOPUS_MAPPING,
    "wos": WOS_MAPPING,
}

# Signature columns used for auto-detection
_FORMAT_SIGNATURES: dict[str, set[str]] = {
    "zotero": {"Key", "Item Type", "Abstract Note", "Manual Tags"},
    "scopus": {"EID", "Source title", "Cited by", "Abstract"},
    "wos": {"UT", "TI", "AB", "SO"},
}


def detect_format(df: pd.DataFrame) -> str | None:
    """Auto-detect bibliographic format from DataFrame column names."""
    columns = set(df.columns)
    best_match = None
    best_score = 0

    for fmt, signature in _FORMAT_SIGNATURES.items():
        overlap = len(columns & signature)
        if overlap > best_score:
            best_score = overlap
            best_match = fmt

    if best_score >= 2:
        logger.info(
            "Auto-detected format: %s (matched %d signature columns)",
            best_match,
            best_score,
        )
        return best_match

    return None


def apply_mapping(
    df: pd.DataFrame,
    mapping: ColumnMapping,
    target_fields: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Rename columns from source format to target field names.

    *target_fields* maps internal names to desired output column names.
    Defaults to lowercase: id, title, abstract, manual_tags.
    """
    if target_fields is None:
        target_fields = {
            "id": "key",
            "title": "title",
            "abstract": "abstract",
            "manual_tags": "manual_tags",
        }

    rename_map: dict[str, str] = {}
    for internal, target in target_fields.items():
        source_col = getattr(mapping, internal, None)
        if source_col and source_col in df.columns:
            rename_map[source_col] = target

    return df.rename(columns=rename_map)


def normalize_import(
    df: pd.DataFrame,
    format_hint: str | None = None,
    target_fields: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Detect format and normalize column names for the triage engine."""
    fmt = format_hint or detect_format(df)
    if fmt is None:
        logger.info("Could not detect format; returning DataFrame as-is")
        return df

    mapping = KNOWN_FORMATS.get(fmt)
    if mapping is None:
        logger.warning("Unknown format '%s'; returning DataFrame as-is", fmt)
        return df

    return apply_mapping(df, mapping, target_fields)


__all__ = [
    "ColumnMapping",
    "ZOTERO_MAPPING",
    "SCOPUS_MAPPING",
    "WOS_MAPPING",
    "KNOWN_FORMATS",
    "detect_format",
    "apply_mapping",
    "normalize_import",
]
