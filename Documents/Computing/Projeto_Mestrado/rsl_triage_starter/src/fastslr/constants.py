"""Global constants and default configuration values for the RSL Triage System."""

from __future__ import annotations

VERSION = "2.0.0"

TERM_KINDS: frozenset[str] = frozenset({"pos", "anti", "flag"})
VALID_SCOPES: frozenset[str] = frozenset({"title", "abstract", "manual_tags", "any"})
SECTION_NAMES: tuple[str, ...] = ("title", "abstract", "manual_tags")

GLOBAL_BLOCK_NAME = "GLOBAL"
T0_BLOCK_NAME = "T0"

# Backward-compatibility aliases for legacy nomenclature.
LEGACY_DOMAIN_BLOCKS: tuple[str, ...] = ("T1A", "T1B", "T1C")

CONFIG_RESERVED_KEYS: frozenset[str] = frozenset(
    {
        "global",
        "fields",
        "encoding",
        "sep",
        "output",
        "normalization_rules",
        "_domain_blocks",
        "_block_labels",
        "_valid_terms_count",
    }
)

DEFAULT_MIN_LEVELS = 2
DEFAULT_MAX_LEVELS = 5

DEFAULT_LEVEL_SCORES: dict[int, int] = {1: 10, 2: 8, 3: 6, 4: 4, 5: 2}
DEFAULT_SECTION_WEIGHTS: dict[str, float] = {
    "title": 2.0,
    "abstract": 1.0,
    "manual_tags": 1.5,
}
DEFAULT_APPROVAL_THRESHOLDS: dict[int, float | None] = {
    1: 10,
    2: 12,
    3: 18,
    4: 22,
    5: None,
}
DEFAULT_FLAGGING_THRESHOLDS: dict[int, float] = {1: 6, 2: 6, 3: 6, 4: 8, 5: 12}

__all__ = [
    "VERSION",
    "TERM_KINDS",
    "VALID_SCOPES",
    "SECTION_NAMES",
    "GLOBAL_BLOCK_NAME",
    "T0_BLOCK_NAME",
    "LEGACY_DOMAIN_BLOCKS",
    "CONFIG_RESERVED_KEYS",
    "DEFAULT_MIN_LEVELS",
    "DEFAULT_MAX_LEVELS",
    "DEFAULT_LEVEL_SCORES",
    "DEFAULT_SECTION_WEIGHTS",
    "DEFAULT_APPROVAL_THRESHOLDS",
    "DEFAULT_FLAGGING_THRESHOLDS",
]
