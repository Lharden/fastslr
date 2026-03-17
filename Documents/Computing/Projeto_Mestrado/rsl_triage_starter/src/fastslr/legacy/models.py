"""Data classes and type definitions for the RSL Triage System."""

from __future__ import annotations

from dataclasses import dataclass, field

from .constants import SECTION_NAMES


@dataclass
class TermMatch:
    """A positive term match found in an article section."""

    term: str
    level: int | None
    section: str
    source_row: int | None
    match_type: str = "exact"
    components: tuple[str, ...] = ()

    def __repr__(self) -> str:
        return (
            f"TermMatch(term={self.term!r}, level={self.level}, "
            f"section={self.section!r}, type={self.match_type!r})"
        )


@dataclass
class AntiHit:
    """An anti-term hit (exclusion or flagging) found in an article section."""

    term: str
    section: str
    source_row: int | None

    def __repr__(self) -> str:
        return f"AntiHit(term={self.term!r}, section={self.section!r})"


@dataclass
class BlockEvaluation:
    """Result of evaluating a single thematic block (T1A/T1B/T1C)."""

    status: str
    reason: str
    raw_score: float = 0.0
    final_score: float = 0.0
    best_level: int | None = None
    matches: dict[str, list[TermMatch]] = field(
        default_factory=lambda: {s: [] for s in SECTION_NAMES}
    )
    anti_exclude: list[AntiHit] = field(default_factory=list)
    anti_flag: list[AntiHit] = field(default_factory=list)
    uplift_applied: bool = False
    section_scores: dict[str, float] = field(
        default_factory=lambda: {s: 0.0 for s in SECTION_NAMES}
    )

    def __repr__(self) -> str:
        return (
            f"BlockEvaluation(status={self.status!r}, "
            f"score={self.final_score:.2f}, level={self.best_level})"
        )


@dataclass
class T0Evaluation:
    """Result of the global pre-screening evaluation (T0)."""

    status: str
    reason: str
    scope: str
    anti_exclude: list[AntiHit] = field(default_factory=list)
    anti_flag: list[AntiHit] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"T0Evaluation(status={self.status!r}, scope={self.scope!r})"


@dataclass
class GlobalParams:
    """Global configuration parameters for the triage engine."""

    level_scores: dict[int, int]
    section_weights: dict[str, float]
    approval_thresholds: dict[int, float | None]
    flagging_thresholds: dict[int, float]
    no_tags_uplift: float
    max_section_score: float
    fail_fast_enabled: bool
    special_approval_threshold: float
    max_gap_between_terms: int
    token_unit_for_gaps: str
    enable_proximity_detection: bool


__all__ = [
    "TermMatch",
    "AntiHit",
    "BlockEvaluation",
    "T0Evaluation",
    "GlobalParams",
]
