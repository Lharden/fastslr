"""Scoring logic: term matching, block evaluation, and final decision tree."""

from __future__ import annotations

import re

from .constants import SECTION_NAMES
from .models import (
    AntiHit,
    BlockEvaluation,
    GlobalParams,
    T0Evaluation,
    TermMatch,
)
from .normalization import NormalizationEngine

# ── helpers ──────────────────────────────────────────────────────────────────


def _normalize_sections(
    sections: dict[str, str],
    engine: NormalizationEngine | None,
) -> dict[str, str]:
    """Return a dict of lowercased / normalized section texts."""
    normalized: dict[str, str] = {}
    for sec_name, sec_text in sections.items():
        if sec_text.strip():
            if engine:
                normalized[sec_name] = engine.normalize(sec_text)
            else:
                normalized[sec_name] = re.sub(r"\s+", " ", sec_text.lower().strip())
        else:
            normalized[sec_name] = ""
    return normalized


# ── positive / anti term finders ─────────────────────────────────────────────


def find_positive_terms(
    title: str,
    abstract: str,
    manual_tags: str,
    terms: list[dict],
    proximity_terms: list[dict] | None = None,
    normalization_engine: NormalizationEngine | None = None,
) -> tuple[set, dict[str, list[TermMatch]]]:
    """Search for positive terms across all article sections.

    Returns a tuple of ``(found_levels, matches_by_section)``.
    """
    sections = {
        "title": title or "",
        "abstract": abstract or "",
        "manual_tags": manual_tags or "",
    }
    normalized = _normalize_sections(sections, normalization_engine)

    found_levels: set = set()
    matches: dict[str, list[TermMatch]] = {s: [] for s in SECTION_NAMES}

    all_terms = list(terms or [])
    if proximity_terms:
        all_terms.extend(proximity_terms)

    for term in all_terms:
        scope = term.get("scope", "any")
        pattern = term.get("pattern")

        if not pattern:
            continue

        target_sections = SECTION_NAMES if scope == "any" else (scope,)

        for sec_name in target_sections:
            sec_norm = normalized.get(sec_name, "")
            if not sec_norm:
                continue

            try:
                if pattern.search(sec_norm):
                    level = term.get("level")
                    if level is not None:
                        found_levels.add(int(level))

                    match_type = "proximity" if term.get("is_proximity") else "exact"
                    components = term.get("components", ())

                    matches[sec_name].append(
                        TermMatch(
                            term=term.get("original_term", term.get("term", "")),
                            level=level,
                            section=sec_name,
                            source_row=term.get("source_row"),
                            match_type=match_type,
                            components=components,
                        )
                    )
            except re.error:
                continue

    return found_levels, matches


def find_anti_terms(
    title: str,
    abstract: str,
    manual_tags: str,
    anti_terms: list[dict],
    normalization_engine: NormalizationEngine | None = None,
) -> list[AntiHit]:
    """Search for anti-terms (exclusion or flagging) across article sections."""
    sections = {
        "title": title or "",
        "abstract": abstract or "",
        "manual_tags": manual_tags or "",
    }
    normalized = _normalize_sections(sections, normalization_engine)

    hits: list[AntiHit] = []

    for term in anti_terms or []:
        scope = term.get("scope", "any")
        pattern = term.get("pattern")

        if not pattern:
            continue

        target_sections = SECTION_NAMES if scope == "any" else (scope,)

        for sec_name in target_sections:
            sec_norm = normalized.get(sec_name, "")
            if not sec_norm:
                continue

            try:
                if pattern.search(sec_norm):
                    hits.append(
                        AntiHit(
                            term=term.get("original_term", term.get("term", "")),
                            section=sec_name,
                            source_row=term.get("source_row"),
                        )
                    )
            except re.error:
                continue

    return hits


# ── block evaluation ─────────────────────────────────────────────────────────


def _compute_section_scores(
    matches: dict[str, list[TermMatch]],
    global_params: GlobalParams,
) -> tuple[dict[str, float], float]:
    """Compute weighted scores per section and total raw score.

    Scoring is based on **unique levels found** per section, not
    individual match count.  If multiple terms match at the same level,
    that level's score is counted only once.
    """
    section_scores: dict[str, float] = {}
    raw_score = 0.0

    for sec_name in SECTION_NAMES:
        sec_matches = matches.get(sec_name, [])
        found_levels_in_section: set[int] = set()
        for m in sec_matches:
            if m.level is not None:
                found_levels_in_section.add(int(m.level))

        sec_raw = sum(global_params.level_scores.get(lvl, 0) for lvl in found_levels_in_section)
        sec_raw = min(sec_raw, global_params.max_section_score)
        weight = global_params.section_weights.get(sec_name, 1.0)
        section_scores[sec_name] = sec_raw * weight
        raw_score += section_scores[sec_name]

    return section_scores, raw_score


def evaluate_block(
    title: str,
    abstract: str,
    manual_tags: str,
    block_config: dict,
    global_params: GlobalParams,
) -> BlockEvaluation:
    """Evaluate an article against a single thematic block."""
    norm_engine = block_config.get("normalization_engine")

    positives = block_config.get("positives", [])
    proximity = block_config.get("proximity_positives", [])
    anti_exclude_terms = block_config.get("anti_exclude", [])
    anti_flag_terms = block_config.get("anti_flag", [])

    # Find positive matches
    found_levels, matches = find_positive_terms(
        title, abstract, manual_tags, positives, proximity, norm_engine
    )

    # Find anti terms
    anti_exclude = find_anti_terms(title, abstract, manual_tags, anti_exclude_terms, norm_engine)
    anti_flag = find_anti_terms(title, abstract, manual_tags, anti_flag_terms, norm_engine)

    # Compute scores
    section_scores, raw_score = _compute_section_scores(matches, global_params)

    # Apply no-tags uplift
    uplift_applied = False
    final_score = raw_score
    has_tags = bool(
        manual_tags
        and manual_tags.strip()
        and manual_tags.strip().lower() not in {"nan", "none", "null"}
    )
    if not has_tags and global_params.no_tags_uplift > 1.0 and raw_score > 0:
        final_score = raw_score * global_params.no_tags_uplift
        uplift_applied = True

    # If anti-exclude triggered, reject immediately
    if anti_exclude:
        return BlockEvaluation(
            status="REJECTED",
            reason=f"Anti-exclusion: {anti_exclude[0].term}",
            raw_score=raw_score,
            final_score=final_score,
            best_level=min(found_levels) if found_levels else None,
            matches=matches,
            anti_exclude=anti_exclude,
            anti_flag=anti_flag,
            uplift_applied=uplift_applied,
            section_scores=section_scores,
        )

    # Determine best level
    best_level = min(found_levels) if found_levels else None

    # Apply noise filters
    if global_params.noise_profile != "relaxed" and best_level is not None:
        unique_terms = len({m.term for sec in matches.values() for m in sec})
        sections_with_hits = sum(1 for v in matches.values() if v)

        if unique_terms < global_params.min_unique_terms_for_approval:
            return BlockEvaluation(
                status="REJECTED",
                reason=f"Noise filter: only {unique_terms} unique term(s)",
                raw_score=raw_score,
                final_score=final_score,
                best_level=best_level,
                matches=matches,
                anti_exclude=anti_exclude,
                anti_flag=anti_flag,
                uplift_applied=uplift_applied,
                section_scores=section_scores,
            )

        if sections_with_hits < global_params.min_sections_with_hits_for_approval:
            return BlockEvaluation(
                status="REJECTED",
                reason=f"Noise filter: hits in only {sections_with_hits} section(s)",
                raw_score=raw_score,
                final_score=final_score,
                best_level=best_level,
                matches=matches,
                anti_exclude=anti_exclude,
                anti_flag=anti_flag,
                uplift_applied=uplift_applied,
                section_scores=section_scores,
            )

        if global_params.require_non_weak_term_for_approval:
            non_weak = found_levels - set(global_params.weak_levels)
            if not non_weak:
                return BlockEvaluation(
                    status="REJECTED",
                    reason="Noise filter: only weak-level terms found",
                    raw_score=raw_score,
                    final_score=final_score,
                    best_level=best_level,
                    matches=matches,
                    anti_exclude=anti_exclude,
                    anti_flag=anti_flag,
                    uplift_applied=uplift_applied,
                    section_scores=section_scores,
                )

    # Decision based on thresholds
    if best_level is not None:
        approval_threshold = global_params.approval_thresholds.get(best_level)
        flagging_threshold = global_params.flagging_thresholds.get(best_level, 0)

        if approval_threshold is not None and final_score >= approval_threshold:
            status = "APPROVED"
            reason = f"Score {final_score:.2f} >= threshold {approval_threshold} (L{best_level})"
        elif final_score >= flagging_threshold:
            status = "FLAGGED"
            reason = (
                f"Score {final_score:.2f} >= flag threshold {flagging_threshold} (L{best_level})"
            )
        else:
            status = "REJECTED"
            reason = f"Score {final_score:.2f} below thresholds (L{best_level})"
    else:
        status = "REJECTED"
        reason = "No positive terms found"

    # Anti-flag modifies status to FLAGGED if currently APPROVED
    if anti_flag and status == "APPROVED":
        status = "FLAGGED"
        reason = f"Downgraded to flagged: anti-flag term '{anti_flag[0].term}'"

    return BlockEvaluation(
        status=status,
        reason=reason,
        raw_score=raw_score,
        final_score=final_score,
        best_level=best_level,
        matches=matches,
        anti_exclude=anti_exclude,
        anti_flag=anti_flag,
        uplift_applied=uplift_applied,
        section_scores=section_scores,
    )


# ── T0 global pre-screening ─────────────────────────────────────────────────


def evaluate_t0_conditional(
    title: str,
    abstract: str,
    manual_tags: str,
    config: dict,
    normalization_engine: NormalizationEngine | None = None,
) -> T0Evaluation | None:
    """Evaluate the global T0 pre-screening block, if configured."""
    t0_config = config.get("T0")
    if not t0_config:
        return None

    anti_exclude_terms = t0_config.get("anti_exclude", [])
    anti_flag_terms = t0_config.get("anti_flag", [])

    anti_exclude = find_anti_terms(
        title, abstract, manual_tags, anti_exclude_terms, normalization_engine
    )
    anti_flag = find_anti_terms(title, abstract, manual_tags, anti_flag_terms, normalization_engine)

    if anti_exclude:
        return T0Evaluation(
            status="REJECTED",
            reason=f"Global exclusion: {anti_exclude[0].term}",
            scope="global",
            anti_exclude=anti_exclude,
            anti_flag=anti_flag,
        )

    if anti_flag:
        return T0Evaluation(
            status="FLAGGED",
            reason=f"Global flag: {anti_flag[0].term}",
            scope="global",
            anti_exclude=anti_exclude,
            anti_flag=anti_flag,
        )

    return T0Evaluation(
        status="PASSED",
        reason="No global anti-terms triggered",
        scope="global",
        anti_exclude=anti_exclude,
        anti_flag=anti_flag,
    )


# ── final decision ───────────────────────────────────────────────────────────


def make_final_decision(
    evaluations: dict[str, BlockEvaluation],
    eval_t0: T0Evaluation | None,
    global_params: GlobalParams,
) -> tuple[str, str]:
    """Combine block evaluations and T0 into a final triage decision.

    Returns ``(decision, reason)`` where decision is one of
    ``APPROVED_FINAL``, ``FLAGGED_FINAL``, ``REJECTED_FINAL``.
    """
    # T0 rejection overrides everything
    if eval_t0 and eval_t0.status == "REJECTED":
        return "REJECTED_FINAL", f"T0: {eval_t0.reason}"

    block_statuses = {name: ev.status for name, ev in evaluations.items()}
    block_scores = {name: ev.final_score for name, ev in evaluations.items()}

    approved_blocks = [n for n, s in block_statuses.items() if s == "APPROVED"]
    flagged_blocks = [n for n, s in block_statuses.items() if s == "FLAGGED"]
    rejected_blocks = [n for n, s in block_statuses.items() if s == "REJECTED"]

    total_blocks = len(evaluations)

    policy = global_params.decision_policy

    if policy == "strict":
        if len(approved_blocks) == total_blocks:
            return "APPROVED_FINAL", "All blocks approved (strict policy)"
        elif flagged_blocks:
            return "FLAGGED_FINAL", f"Flagged blocks: {', '.join(flagged_blocks)}"
        else:
            return "REJECTED_FINAL", f"Rejected blocks: {', '.join(rejected_blocks)}"

    elif policy == "k_of_n":
        min_approved = global_params.min_approved_blocks or 1
        max_flagged = global_params.max_flagged_blocks_for_approval

        if len(approved_blocks) >= min_approved and len(flagged_blocks) <= max_flagged:
            return "APPROVED_FINAL", (f"{len(approved_blocks)}/{total_blocks} approved (k_of_n)")
        elif flagged_blocks or approved_blocks:
            return "FLAGGED_FINAL", (
                f"{len(approved_blocks)} approved, {len(flagged_blocks)} flagged"
            )
        else:
            return "REJECTED_FINAL", "No blocks approved or flagged"

    # ── "special" policy (default — v11 original logic) ──────────────

    # 1. Any domain block rejected → REJECTED_FINAL
    if rejected_blocks:
        return "REJECTED_FINAL", f"Rejected blocks: {', '.join(rejected_blocks)}"

    # 2. T0 flagged → FLAGGED_FINAL
    if eval_t0 and eval_t0.status == "FLAGGED":
        return "FLAGGED_FINAL", f"T0: {eval_t0.reason}"

    # 3. Any block has anti-flag hits → FLAGGED_FINAL
    anti_flagged_blocks = [n for n, ev in evaluations.items() if ev.anti_flag]
    if anti_flagged_blocks:
        return "FLAGGED_FINAL", (f"Anti-flag in blocks: {', '.join(anti_flagged_blocks)}")

    # 4. Special approval rule: 1 flagged + rest approved, approved scores ≥ threshold
    score_flagged = [
        n for n, s in block_statuses.items() if s == "FLAGGED" and not evaluations[n].anti_flag
    ]
    if (
        global_params.enable_special_approval_rule
        and len(score_flagged) == 1
        and len(approved_blocks) == total_blocks - 1
    ):
        approved_scores = [block_scores[b] for b in approved_blocks]
        if all(s >= global_params.special_approval_threshold for s in approved_scores):
            return "APPROVED_FINAL", (
                f"Special rule: {len(approved_blocks)} approved "
                f"(scores >= {global_params.special_approval_threshold})"
            )

    # 5. Any score-based flagged → FLAGGED_FINAL
    if score_flagged:
        return "FLAGGED_FINAL", f"Flagged blocks: {', '.join(score_flagged)}"

    # 6. All approved → APPROVED_FINAL
    if len(approved_blocks) == total_blocks:
        return "APPROVED_FINAL", "All blocks approved"

    return "FLAGGED_FINAL", "Inconclusive evaluation"


__all__ = [
    "find_positive_terms",
    "find_anti_terms",
    "evaluate_block",
    "evaluate_t0_conditional",
    "make_final_decision",
]
