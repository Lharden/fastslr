"""Shared fixtures for the RSL Triage test suite."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure the src directory is on the path for editable-install-free testing
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fastslr.core.models import GlobalParams  # noqa: E402
from fastslr.core.normalization import NormalizationEngine  # noqa: E402


@pytest.fixture
def default_global_params() -> GlobalParams:
    """GlobalParams with the standard v11 defaults."""
    return GlobalParams(
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
        level_order=(1, 2, 3, 4, 5),
        enable_special_approval_rule=True,
        decision_policy="special",
        min_approved_blocks=None,
        max_flagged_blocks_for_approval=0,
        noise_profile="relaxed",
        min_unique_terms_for_approval=1,
        min_sections_with_hits_for_approval=1,
        require_non_weak_term_for_approval=False,
        weak_levels=(5,),
        error_policy="flag",
        max_error_rate=0.05,
    )


@pytest.fixture
def normalization_engine_disabled() -> NormalizationEngine:
    """A NormalizationEngine with rules disabled."""
    return NormalizationEngine({"enabled": False})


@pytest.fixture
def normalization_engine_enabled() -> NormalizationEngine:
    """A NormalizationEngine with some test rules."""
    return NormalizationEngine(
        {
            "enabled": True,
            "abbreviations": {
                "AI": "artificial intelligence",
                "ML": "machine learning",
            },
            "compound_variants": {"supply-chain": "supply chain"},
            "symbol_replacements": {"&": "and"},
        }
    )
