"""Tests for the scoring module: term matching, block evaluation, and final decision."""

from __future__ import annotations

from fastslr.core.models import BlockEvaluation, GlobalParams
from fastslr.core.patterns import precompile_patterns
from fastslr.core.scoring import (
    evaluate_block,
    evaluate_t0_conditional,
    find_anti_terms,
    find_positive_terms,
    make_final_decision,
)


def _compile_block(block: dict) -> dict:
    """Compile a raw block config via precompile_patterns."""
    return precompile_patterns(block)


def _make_compiled_block_for_evaluate(
    positives: list[dict] | None = None,
    anti_exclude: list[dict] | None = None,
    anti_flag: list[dict] | None = None,
) -> dict:
    """Build a block in raw format, run precompile_patterns, return compiled block.

    Anti terms must be provided at the top level; this helper restructures them
    into the ``anti: {exclude: [...], flag: [...]}`` layout that
    ``precompile_patterns`` expects, then returns the compiled output suitable
    for ``evaluate_block``.
    """
    raw: dict = {
        "name": "TEST_BLOCK",
        "positives": positives or [],
        "anti": {
            "exclude": anti_exclude or [],
            "flag": anti_flag or [],
        },
        "proximity_positives": [],
    }
    return precompile_patterns(raw)


# ── helpers for make_final_decision tests ──────────────────────────────────


def _make_eval(
    status: str,
    score: float = 20.0,
    best_level: int = 1,
    anti_flag: list | None = None,
) -> BlockEvaluation:
    """Build a BlockEvaluation instance for testing."""
    return BlockEvaluation(
        status=status,
        reason=f"Test {status}",
        raw_score=score,
        final_score=score,
        best_level=best_level,
        matches={"title": [], "abstract": [], "manual_tags": []},
        anti_exclude=[],
        anti_flag=anti_flag or [],
        uplift_applied=False,
        section_scores={
            "title": score * 0.5,
            "abstract": score * 0.3,
            "manual_tags": score * 0.2,
        },
    )


# ═════════════════════════════════════════════════════════════════════════════
# TestFindPositiveTerms (6 tests)
# ═════════════════════════════════════════════════════════════════════════════


class TestFindPositiveTerms:
    """Tests for find_positive_terms."""

    @staticmethod
    def _compiled_terms() -> list[dict]:
        """Compile a minimal set of positive terms."""
        raw_block = {
            "positives": [
                {"term": "artificial intelligence", "level": 1, "is_regex": False},
                {"term": "machine learning", "level": 1, "is_regex": False},
                {"term": "data mining", "level": 3, "is_regex": False},
            ],
            "anti": {"exclude": [], "flag": []},
        }
        compiled = precompile_patterns(raw_block)
        return compiled["positives"]

    def test_finds_exact_match_in_title(self) -> None:
        terms = self._compiled_terms()
        levels, matches = find_positive_terms(
            title="Artificial Intelligence in Healthcare",
            abstract="",
            manual_tags="",
            terms=terms,
        )
        assert 1 in levels
        assert len(matches["title"]) >= 1
        assert any(m.term == "artificial intelligence" for m in matches["title"])

    def test_finds_match_in_abstract(self) -> None:
        terms = self._compiled_terms()
        levels, matches = find_positive_terms(
            title="",
            abstract="We use data mining to extract patterns from large datasets.",
            manual_tags="",
            terms=terms,
        )
        assert 3 in levels
        assert len(matches["abstract"]) >= 1
        assert any(m.term == "data mining" for m in matches["abstract"])

    def test_finds_match_in_manual_tags(self) -> None:
        terms = self._compiled_terms()
        levels, matches = find_positive_terms(
            title="",
            abstract="",
            manual_tags="machine learning, neural networks",
            terms=terms,
        )
        assert 1 in levels
        assert len(matches["manual_tags"]) >= 1

    def test_no_match_returns_empty(self) -> None:
        terms = self._compiled_terms()
        levels, matches = find_positive_terms(
            title="Cooking Recipes for Modern Kitchens",
            abstract="A guide to contemporary cooking methods.",
            manual_tags="",
            terms=terms,
        )
        assert len(levels) == 0
        assert all(len(v) == 0 for v in matches.values())

    def test_multiple_levels_detected(self) -> None:
        terms = self._compiled_terms()
        levels, matches = find_positive_terms(
            title="Artificial Intelligence and Data Mining",
            abstract="",
            manual_tags="",
            terms=terms,
        )
        assert 1 in levels
        assert 3 in levels

    def test_case_insensitive(self) -> None:
        terms = self._compiled_terms()
        levels, matches = find_positive_terms(
            title="MACHINE LEARNING Applications",
            abstract="",
            manual_tags="",
            terms=terms,
        )
        assert 1 in levels
        assert len(matches["title"]) >= 1


# ═════════════════════════════════════════════════════════════════════════════
# TestFindAntiTerms (3 tests)
# ═════════════════════════════════════════════════════════════════════════════


class TestFindAntiTerms:
    """Tests for find_anti_terms."""

    @staticmethod
    def _compiled_anti_exclude() -> list[dict]:
        raw_block = {
            "positives": [],
            "anti": {
                "exclude": [{"term": "cooking oil", "section_scope": "any"}],
                "flag": [],
            },
        }
        compiled = precompile_patterns(raw_block)
        return compiled["anti_exclude"]

    @staticmethod
    def _compiled_anti_flag() -> list[dict]:
        raw_block = {
            "positives": [],
            "anti": {
                "exclude": [],
                "flag": [{"term": "preliminary results", "section_scope": "any"}],
            },
        }
        compiled = precompile_patterns(raw_block)
        return compiled["anti_flag"]

    def test_detects_anti_exclude_term(self) -> None:
        anti_terms = self._compiled_anti_exclude()
        hits = find_anti_terms(
            title="Analysis of Cooking Oil Production",
            abstract="",
            manual_tags="",
            anti_terms=anti_terms,
        )
        assert len(hits) >= 1
        assert hits[0].term == "cooking oil"

    def test_detects_anti_flag_term(self) -> None:
        anti_terms = self._compiled_anti_flag()
        hits = find_anti_terms(
            title="",
            abstract="These are preliminary results of the study.",
            manual_tags="",
            anti_terms=anti_terms,
        )
        assert len(hits) >= 1
        assert hits[0].term == "preliminary results"

    def test_no_anti_terms_returns_empty(self) -> None:
        anti_terms = self._compiled_anti_exclude()
        hits = find_anti_terms(
            title="Artificial Intelligence in Healthcare",
            abstract="A study of machine learning methods.",
            manual_tags="",
            anti_terms=anti_terms,
        )
        assert len(hits) == 0


# ═════════════════════════════════════════════════════════════════════════════
# TestEvaluateBlock (7 tests)
# ═════════════════════════════════════════════════════════════════════════════


class TestEvaluateBlock:
    """Tests for evaluate_block."""

    def test_approved_when_strong_terms(self, default_global_params: GlobalParams) -> None:
        block = _make_compiled_block_for_evaluate(
            positives=[
                {"term": "artificial intelligence", "level": 1, "is_regex": False},
                {"term": "machine learning", "level": 1, "is_regex": False},
            ],
        )
        result = evaluate_block(
            title="Artificial Intelligence and Machine Learning",
            abstract="This paper covers artificial intelligence.",
            manual_tags="",
            block_config=block,
            global_params=default_global_params,
        )
        assert result.status == "APPROVED"

    def test_rejected_when_no_terms(self, default_global_params: GlobalParams) -> None:
        block = _make_compiled_block_for_evaluate(
            positives=[
                {"term": "artificial intelligence", "level": 1, "is_regex": False},
            ],
        )
        result = evaluate_block(
            title="Cooking Recipes for Modern Kitchens",
            abstract="A guide to contemporary cooking methods.",
            manual_tags="",
            block_config=block,
            global_params=default_global_params,
        )
        assert result.status == "REJECTED"
        assert "No positive terms found" in result.reason

    def test_rejected_by_anti_exclude(self, default_global_params: GlobalParams) -> None:
        block = _make_compiled_block_for_evaluate(
            positives=[
                {"term": "artificial intelligence", "level": 1, "is_regex": False},
            ],
            anti_exclude=[{"term": "cooking oil"}],
        )
        result = evaluate_block(
            title="Artificial Intelligence for Cooking Oil Analysis",
            abstract="We apply AI to cooking oil production.",
            manual_tags="",
            block_config=block,
            global_params=default_global_params,
        )
        assert result.status == "REJECTED"
        assert "Anti-exclusion" in result.reason

    def test_flagged_by_anti_flag(self, default_global_params: GlobalParams) -> None:
        block = _make_compiled_block_for_evaluate(
            positives=[
                {"term": "artificial intelligence", "level": 1, "is_regex": False},
                {"term": "machine learning", "level": 1, "is_regex": False},
            ],
            anti_flag=[{"term": "preliminary results"}],
        )
        result = evaluate_block(
            title="Artificial Intelligence and Machine Learning",
            abstract="These are preliminary results of the AI study.",
            manual_tags="",
            block_config=block,
            global_params=default_global_params,
        )
        assert result.status == "FLAGGED"

    def test_uplift_applied_when_no_tags(self, default_global_params: GlobalParams) -> None:
        block = _make_compiled_block_for_evaluate(
            positives=[
                {"term": "artificial intelligence", "level": 1, "is_regex": False},
            ],
        )
        result = evaluate_block(
            title="Artificial Intelligence Advances",
            abstract="",
            manual_tags="",
            block_config=block,
            global_params=default_global_params,
        )
        assert result.uplift_applied is True
        assert result.final_score > result.raw_score

    def test_no_uplift_when_tags_present(self, default_global_params: GlobalParams) -> None:
        block = _make_compiled_block_for_evaluate(
            positives=[
                {"term": "artificial intelligence", "level": 1, "is_regex": False},
            ],
        )
        result = evaluate_block(
            title="Artificial Intelligence Advances",
            abstract="",
            manual_tags="AI, deep learning",
            block_config=block,
            global_params=default_global_params,
        )
        assert result.uplift_applied is False
        assert result.final_score == result.raw_score

    def test_section_scores_populated(self, default_global_params: GlobalParams) -> None:
        block = _make_compiled_block_for_evaluate(
            positives=[
                {"term": "artificial intelligence", "level": 1, "is_regex": False},
            ],
        )
        result = evaluate_block(
            title="Artificial Intelligence Advances",
            abstract="Artificial intelligence is transforming the world.",
            manual_tags="",
            block_config=block,
            global_params=default_global_params,
        )
        assert "title" in result.section_scores
        assert "abstract" in result.section_scores
        assert "manual_tags" in result.section_scores
        assert result.section_scores["title"] > 0
        assert result.section_scores["abstract"] > 0


# ═════════════════════════════════════════════════════════════════════════════
# TestMakeFinalDecision (9 tests)
# ═════════════════════════════════════════════════════════════════════════════


class TestMakeFinalDecision:
    """Tests for make_final_decision."""

    def test_all_approved_returns_approved_final(
        self, default_global_params: GlobalParams
    ) -> None:
        evals = {
            "BLOCK_A": _make_eval("APPROVED", score=50.0),
            "BLOCK_B": _make_eval("APPROVED", score=45.0),
        }
        decision, reason = make_final_decision(evals, None, default_global_params)
        assert decision == "APPROVED_FINAL"

    def test_any_rejected_returns_rejected_final(
        self, default_global_params: GlobalParams
    ) -> None:
        evals = {
            "BLOCK_A": _make_eval("APPROVED", score=50.0),
            "BLOCK_B": _make_eval("REJECTED", score=0.0),
        }
        decision, reason = make_final_decision(evals, None, default_global_params)
        assert decision == "REJECTED_FINAL"

    def test_flagged_block_behavior(self, default_global_params: GlobalParams) -> None:
        evals = {
            "BLOCK_A": _make_eval("APPROVED", score=50.0),
            "BLOCK_B": _make_eval("FLAGGED", score=8.0),
        }
        decision, reason = make_final_decision(evals, None, default_global_params)
        assert decision == "FLAGGED_FINAL" or decision == "APPROVED_FINAL"

    def test_special_approval_rule(self, default_global_params: GlobalParams) -> None:
        """1 flagged + others >= threshold -> APPROVED_FINAL."""
        evals = {
            "BLOCK_A": _make_eval("APPROVED", score=50.0),
            "BLOCK_B": _make_eval("FLAGGED", score=8.0),
        }
        decision, reason = make_final_decision(evals, None, default_global_params)
        assert decision == "APPROVED_FINAL"
        assert "Special rule" in reason

    def test_special_approval_fails_when_scores_low(
        self, default_global_params: GlobalParams
    ) -> None:
        """1 flagged + others below threshold -> FLAGGED_FINAL."""
        evals = {
            "BLOCK_A": _make_eval("APPROVED", score=15.0),
            "BLOCK_B": _make_eval("FLAGGED", score=8.0),
        }
        decision, reason = make_final_decision(evals, None, default_global_params)
        assert decision == "FLAGGED_FINAL"

    def test_t0_flagged_returns_flagged_final(
        self, default_global_params: GlobalParams
    ) -> None:
        from fastslr.core.models import T0Evaluation

        evals = {
            "BLOCK_A": _make_eval("APPROVED", score=50.0),
        }
        t0 = T0Evaluation(
            status="FLAGGED",
            reason="Global flag: some term",
            scope="global",
        )
        decision, reason = make_final_decision(evals, t0, default_global_params)
        assert decision == "FLAGGED_FINAL"

    def test_strict_policy_requires_all_approved(self) -> None:
        params = GlobalParams(
            level_scores={1: 10, 2: 8, 3: 6, 4: 4, 5: 2},
            section_weights={"title": 2.0, "abstract": 1.0, "manual_tags": 1.5},
            approval_thresholds={1: 10, 2: 12, 3: 18, 4: 22, 5: None},
            flagging_thresholds={1: 6, 2: 6, 3: 6, 4: 8, 5: 12},
            no_tags_uplift=1.17,
            max_section_score=30,
            fail_fast_enabled=True,
            special_approval_threshold=40.0,
            max_gap_between_terms=3,
            token_unit_for_gaps=r"\S+",
            enable_proximity_detection=True,
            decision_policy="strict",
        )
        evals = {
            "BLOCK_A": _make_eval("APPROVED", score=50.0),
            "BLOCK_B": _make_eval("FLAGGED", score=8.0),
        }
        decision, reason = make_final_decision(evals, None, params)
        assert decision == "FLAGGED_FINAL"

    def test_k_of_n_policy_approves(self) -> None:
        params = GlobalParams(
            level_scores={1: 10, 2: 8, 3: 6, 4: 4, 5: 2},
            section_weights={"title": 2.0, "abstract": 1.0, "manual_tags": 1.5},
            approval_thresholds={1: 10, 2: 12, 3: 18, 4: 22, 5: None},
            flagging_thresholds={1: 6, 2: 6, 3: 6, 4: 8, 5: 12},
            no_tags_uplift=1.17,
            max_section_score=30,
            fail_fast_enabled=True,
            special_approval_threshold=40.0,
            max_gap_between_terms=3,
            token_unit_for_gaps=r"\S+",
            enable_proximity_detection=True,
            decision_policy="k_of_n",
            min_approved_blocks=2,
            max_flagged_blocks_for_approval=1,
        )
        evals = {
            "BLOCK_A": _make_eval("APPROVED", score=50.0),
            "BLOCK_B": _make_eval("APPROVED", score=45.0),
            "BLOCK_C": _make_eval("FLAGGED", score=8.0),
        }
        decision, reason = make_final_decision(evals, None, params)
        assert decision == "APPROVED_FINAL"

    def test_k_of_n_policy_rejects_too_many_flagged(self) -> None:
        params = GlobalParams(
            level_scores={1: 10, 2: 8, 3: 6, 4: 4, 5: 2},
            section_weights={"title": 2.0, "abstract": 1.0, "manual_tags": 1.5},
            approval_thresholds={1: 10, 2: 12, 3: 18, 4: 22, 5: None},
            flagging_thresholds={1: 6, 2: 6, 3: 6, 4: 8, 5: 12},
            no_tags_uplift=1.17,
            max_section_score=30,
            fail_fast_enabled=True,
            special_approval_threshold=40.0,
            max_gap_between_terms=3,
            token_unit_for_gaps=r"\S+",
            enable_proximity_detection=True,
            decision_policy="k_of_n",
            min_approved_blocks=2,
            max_flagged_blocks_for_approval=0,
        )
        evals = {
            "BLOCK_A": _make_eval("APPROVED", score=50.0),
            "BLOCK_B": _make_eval("APPROVED", score=45.0),
            "BLOCK_C": _make_eval("FLAGGED", score=8.0),
        }
        decision, reason = make_final_decision(evals, None, params)
        assert decision == "FLAGGED_FINAL"


# ═════════════════════════════════════════════════════════════════════════════
# TestNoiseFiltering (4 tests)
# ═════════════════════════════════════════════════════════════════════════════


class TestNoiseFiltering:
    """Tests for noise filtering in evaluate_block via GlobalParams."""

    @staticmethod
    def _noise_params(**overrides: object) -> GlobalParams:
        """Create GlobalParams with balanced noise profile and custom overrides."""
        defaults: dict = {
            "level_scores": {1: 10, 2: 8, 3: 6, 4: 4, 5: 2},
            "section_weights": {"title": 2.0, "abstract": 1.0, "manual_tags": 1.5},
            "approval_thresholds": {1: 10, 2: 12, 3: 18, 4: 22, 5: None},
            "flagging_thresholds": {1: 6, 2: 6, 3: 6, 4: 8, 5: 12},
            "no_tags_uplift": 1.0,
            "max_section_score": 30,
            "fail_fast_enabled": True,
            "special_approval_threshold": 40.0,
            "max_gap_between_terms": 3,
            "token_unit_for_gaps": r"\S+",
            "enable_proximity_detection": True,
            "noise_profile": "balanced",
        }
        defaults.update(overrides)
        return GlobalParams(**defaults)

    def test_rejected_when_few_unique_terms(self) -> None:
        params = self._noise_params(min_unique_terms_for_approval=3)
        block = _make_compiled_block_for_evaluate(
            positives=[
                {"term": "artificial intelligence", "level": 1, "is_regex": False},
            ],
        )
        result = evaluate_block(
            title="Artificial Intelligence Overview",
            abstract="",
            manual_tags="",
            block_config=block,
            global_params=params,
        )
        assert result.status == "REJECTED"
        assert "unique term" in result.reason

    def test_rejected_when_few_sections(self) -> None:
        params = self._noise_params(min_sections_with_hits_for_approval=2)
        block = _make_compiled_block_for_evaluate(
            positives=[
                {"term": "artificial intelligence", "level": 1, "is_regex": False},
            ],
        )
        result = evaluate_block(
            title="Artificial Intelligence Overview",
            abstract="",
            manual_tags="",
            block_config=block,
            global_params=params,
        )
        assert result.status == "REJECTED"
        assert "section" in result.reason

    def test_rejected_when_only_weak_terms(self) -> None:
        params = self._noise_params(
            require_non_weak_term_for_approval=True,
            weak_levels=(5,),
        )
        block = _make_compiled_block_for_evaluate(
            positives=[
                {"term": "data visualization", "level": 5, "is_regex": False},
            ],
        )
        result = evaluate_block(
            title="Data Visualization Techniques",
            abstract="",
            manual_tags="",
            block_config=block,
            global_params=params,
        )
        assert result.status == "REJECTED"
        assert "weak" in result.reason

    def test_passes_when_thresholds_met(self) -> None:
        params = self._noise_params(
            min_unique_terms_for_approval=1,
            min_sections_with_hits_for_approval=1,
            require_non_weak_term_for_approval=False,
        )
        block = _make_compiled_block_for_evaluate(
            positives=[
                {"term": "artificial intelligence", "level": 1, "is_regex": False},
            ],
        )
        result = evaluate_block(
            title="Artificial Intelligence Advances",
            abstract="",
            manual_tags="",
            block_config=block,
            global_params=params,
        )
        assert result.status != "REJECTED" or "Noise filter" not in result.reason


# ═════════════════════════════════════════════════════════════════════════════
# TestEvaluateT0 (4 tests)
# ═════════════════════════════════════════════════════════════════════════════


class TestEvaluateT0:
    """Tests for evaluate_t0_conditional."""

    @staticmethod
    def _t0_config_with_anti(
        exclude_terms: list[dict] | None = None,
        flag_terms: list[dict] | None = None,
    ) -> dict:
        """Build a config dict with a T0 block containing compiled anti terms."""
        raw_t0: dict = {
            "positives": [],
            "anti": {
                "exclude": exclude_terms or [],
                "flag": flag_terms or [],
            },
        }
        compiled_t0 = precompile_patterns(raw_t0)
        return {
            "T0": {
                "anti_exclude": compiled_t0["anti_exclude"],
                "anti_flag": compiled_t0["anti_flag"],
            },
        }

    def test_returns_none_when_no_t0_config(self) -> None:
        result = evaluate_t0_conditional(
            title="Some Title",
            abstract="Some abstract.",
            manual_tags="",
            config={},
        )
        assert result is None

    def test_rejects_on_anti_exclude(self) -> None:
        config = self._t0_config_with_anti(
            exclude_terms=[{"term": "retracted study"}],
        )
        result = evaluate_t0_conditional(
            title="Retracted Study of AI Methods",
            abstract="",
            manual_tags="",
            config=config,
        )
        assert result is not None
        assert result.status == "REJECTED"
        assert "retracted study" in result.reason.lower()

    def test_flags_on_anti_flag(self) -> None:
        config = self._t0_config_with_anti(
            flag_terms=[{"term": "preliminary results"}],
        )
        result = evaluate_t0_conditional(
            title="",
            abstract="These are preliminary results from our research.",
            manual_tags="",
            config=config,
        )
        assert result is not None
        assert result.status == "FLAGGED"

    def test_passes_when_no_anti_terms_match(self) -> None:
        config = self._t0_config_with_anti(
            exclude_terms=[{"term": "retracted study"}],
            flag_terms=[{"term": "preliminary results"}],
        )
        result = evaluate_t0_conditional(
            title="Artificial Intelligence in Healthcare",
            abstract="A comprehensive study of AI applications.",
            manual_tags="",
            config=config,
        )
        assert result is not None
        assert result.status == "PASSED"
