"""Data classes and type definitions for the RSL Triage System."""

from __future__ import annotations

from dataclasses import dataclass, field

from .constants import SECTION_NAMES


@dataclass
class TermMatch:
    """A positive term match found in an article section.

    Represents a single occurrence where a configured search term was
    detected in one of the article sections (title, abstract, manual_tags).

    Attributes:
        term: The original search term string that matched.
        level: Relevance level assigned to the term (``None`` if unset).
        section: Name of the section where the match occurred.
        source_row: Row index in the terms CSV (for traceability).
        match_type: Either ``"exact"`` or ``"proximity"``.
        components: For proximity matches, the two sub-terms that were found
            within the allowed gap.
    """

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
    """An anti-term hit (exclusion or flagging) found in an article section.

    Anti-terms cause an article to be either excluded (anti_exclude) or
    downgraded to flagged (anti_flag) when detected.

    Attributes:
        term: The anti-term string that matched.
        section: Name of the section where the match occurred.
        source_row: Row index in the terms CSV (for traceability).
    """

    term: str
    section: str
    source_row: int | None

    def __repr__(self) -> str:
        return f"AntiHit(term={self.term!r}, section={self.section!r})"


@dataclass
class BlockEvaluation:
    """Result of evaluating a single thematic block.

    Captures the full scoring output for one domain block, including
    per-section scores, matched terms, anti-term hits, and the final
    status decision (APPROVED, FLAGGED, or REJECTED).

    Attributes:
        status: Decision outcome for this block.
        reason: Human-readable explanation of the decision.
        raw_score: Score before no-tags uplift.
        final_score: Score after uplift (if applied).
        best_level: Highest-priority (lowest number) matched level.
        matches: Positive term matches grouped by section name.
        anti_exclude: Anti-exclusion hits that triggered rejection.
        anti_flag: Anti-flag hits that downgrade approval to flagged.
        uplift_applied: Whether the no-tags uplift was applied.
        section_scores: Weighted scores per section.
    """

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
    """Result of the global pre-screening evaluation (T0).

    T0 is a cross-block pre-screening gate that can reject or flag
    articles before any domain block is evaluated.

    Attributes:
        status: One of ``"PASSED"``, ``"FLAGGED"``, or ``"REJECTED"``.
        reason: Human-readable explanation of the T0 outcome.
        scope: Always ``"global"`` for T0 evaluations.
        anti_exclude: Global anti-exclusion hits.
        anti_flag: Global anti-flag hits.
    """

    status: str
    reason: str
    scope: str
    anti_exclude: list[AntiHit] = field(default_factory=list)
    anti_flag: list[AntiHit] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"T0Evaluation(status={self.status!r}, scope={self.scope!r})"


@dataclass
class GlobalParams:
    """Global configuration parameters for the triage engine.

    Holds all numeric thresholds, weights, and policy flags that govern
    the scoring and decision logic across every domain block.

    Attributes:
        level_scores: Points awarded per relevance level.
        section_weights: Multiplicative weights for each section.
        approval_thresholds: Minimum score for approval per level.
        flagging_thresholds: Minimum score for flagging per level.
        no_tags_uplift: Multiplier applied when manual tags are absent.
        max_section_score: Cap on raw score per section.
        fail_fast_enabled: Stop evaluating remaining blocks after a rejection.
        special_approval_threshold: Score threshold for the special approval rule.
        max_gap_between_terms: Max token gap for proximity detection.
        token_unit_for_gaps: Regex defining one token unit for gap measurement.
        enable_proximity_detection: Whether compound-term proximity matching is active.
        level_order: Order of relevance levels (lowest = most relevant).
        enable_special_approval_rule: Allow promotion when one block is flagged.
        decision_policy: Policy name (``"special"``, ``"strict"``, or ``"k_of_n"``).
        min_approved_blocks: Minimum approved blocks required under k_of_n.
        max_flagged_blocks_for_approval: Max flagged blocks still allowing approval.
        noise_profile: Noise filter strictness (``"relaxed"`` disables filters).
        min_unique_terms_for_approval: Minimum distinct terms to pass noise filter.
        min_sections_with_hits_for_approval: Minimum sections with hits for approval.
        require_non_weak_term_for_approval: Require at least one non-weak level term.
        weak_levels: Levels considered weak by the noise filter.
        error_policy: How to handle per-article errors (``"flag"`` or ``"fail"``).
        max_error_rate: Maximum tolerated error rate before aborting.
    """

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
    level_order: tuple[int, ...] = (1, 2, 3, 4, 5)
    enable_special_approval_rule: bool = True
    decision_policy: str = "special"
    min_approved_blocks: int | None = None
    max_flagged_blocks_for_approval: int = 0
    noise_profile: str = "relaxed"
    min_unique_terms_for_approval: int = 1
    min_sections_with_hits_for_approval: int = 1
    require_non_weak_term_for_approval: bool = False
    weak_levels: tuple[int, ...] = (5,)
    error_policy: str = "flag"
    max_error_rate: float = 0.05


__all__ = [
    "TermMatch",
    "AntiHit",
    "BlockEvaluation",
    "T0Evaluation",
    "GlobalParams",
]
