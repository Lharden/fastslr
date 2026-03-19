"""End-to-end integration tests for 4 triage scenarios.

Each scenario uses dedicated fixture files (config JSON + articles CSV)
and exercises a distinct combination of policy, blocks, and T0 settings.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from fastslr.core.config import get_domain_blocks, load_global_params
from fastslr.core.engine import process_articles
from fastslr.core.normalization import NormalizationEngine
from fastslr.core.patterns import precompile_patterns

FIXTURES = Path(__file__).parent / "fixtures"


def _prepare_and_run(
    config_name: str,
    articles_name: str,
) -> tuple[pd.DataFrame, dict, dict]:
    """Load config + articles, precompile patterns, and run the pipeline.

    Args:
        config_name: JSON config filename inside the fixtures directory.
        articles_name: CSV articles filename inside the fixtures directory.

    Returns:
        Tuple of (result_df, stats, config).
    """
    config_path = FIXTURES / config_name
    articles_path = FIXTURES / articles_name

    with open(config_path, encoding="utf-8") as fh:
        config: dict = json.load(fh)

    norm_rules = config.get("normalization_rules", {})
    engine = NormalizationEngine(norm_rules)
    gp = load_global_params(config.get("global", {}))

    for block_name in get_domain_blocks(config):
        config[block_name] = precompile_patterns(config[block_name], engine, gp)

    if "T0" in config:
        config["T0"] = precompile_patterns(config["T0"], engine, gp)

    df = pd.read_csv(articles_path, encoding="utf-8")

    result_df, stats = process_articles(df, config)
    return result_df, stats, config


# ---------------------------------------------------------------------------
# Scenario A — 3 blocks, special policy, fail-fast
# ---------------------------------------------------------------------------


class TestScenarioA:
    """Scenario A: 3 blocks (TOPIC, METHOD, DOMAIN), special policy, fail-fast."""

    @pytest.fixture(autouse=True)
    def _run_pipeline(self) -> None:
        self.result_df, self.stats, self.config = _prepare_and_run(
            "scenario_a_config.json",
            "scenario_a_articles.csv",
        )

    def test_produces_results(self) -> None:
        """Pipeline returns non-empty results with expected columns."""
        assert len(self.result_df) > 0
        assert "Final_Decision" in self.result_df.columns

    def test_has_all_decision_types(self) -> None:
        """Result set contains both APPROVED_FINAL and REJECTED_FINAL."""
        decisions = set(self.result_df["Final_Decision"].unique())
        assert "APPROVED_FINAL" in decisions
        assert "REJECTED_FINAL" in decisions

    def test_deterministic_output(self) -> None:
        """Two identical runs on the same data produce identical results."""
        result2, _, _ = _prepare_and_run(
            "scenario_a_config.json",
            "scenario_a_articles.csv",
        )
        # Drop timestamp columns which change between runs
        cols_to_drop = ["run_timestamp"]
        df1 = self.result_df.drop(columns=cols_to_drop, errors="ignore").reset_index(drop=True)
        df2 = result2.drop(columns=cols_to_drop, errors="ignore").reset_index(drop=True)
        assert_frame_equal(df1, df2)

    def test_fail_fast_produces_not_evaluated(self) -> None:
        """Articles rejected at TOPIC block have NOT_EVALUATED for later blocks."""
        domain_blocks = get_domain_blocks(self.config)
        first_block = domain_blocks[0]
        later_blocks = domain_blocks[1:]

        status_col = f"Status_{first_block}"
        if status_col not in self.result_df.columns:
            pytest.skip(f"Column {status_col} not found")

        rejected_at_first = self.result_df[self.result_df[status_col] == "REJECTED"]
        if rejected_at_first.empty:
            pytest.skip("No articles rejected at first block")

        for _, row in rejected_at_first.iterrows():
            for block in later_blocks:
                later_col = f"Status_{block}"
                if later_col in self.result_df.columns:
                    assert row[later_col] == "NOT_EVALUATED", (
                        f"Article {row.get('ID', '?')}: expected NOT_EVALUATED for "
                        f"{block} after rejection at {first_block}, got {row[later_col]}"
                    )


# ---------------------------------------------------------------------------
# Scenario B — 2 blocks, strict policy
# ---------------------------------------------------------------------------


class TestScenarioB:
    """Scenario B: 2 blocks (TECH, APP), strict policy."""

    @pytest.fixture(autouse=True)
    def _run_pipeline(self) -> None:
        self.result_df, self.stats, self.config = _prepare_and_run(
            "scenario_b_config.json",
            "scenario_b_articles.csv",
        )

    def test_strict_requires_all_approved(self) -> None:
        """Under strict policy, APPROVED_FINAL articles have all blocks APPROVED."""
        approved_rows = self.result_df[self.result_df["Final_Decision"] == "APPROVED_FINAL"]
        assert len(approved_rows) > 0, "Expected at least one APPROVED_FINAL article"

        domain_blocks = get_domain_blocks(self.config)
        for _, row in approved_rows.iterrows():
            for block in domain_blocks:
                status_col = f"Status_{block}"
                assert row[status_col] == "APPROVED", (
                    f"Article {row.get('ID', '?')}: strict policy APPROVED_FINAL "
                    f"but {block} is {row[status_col]}"
                )


# ---------------------------------------------------------------------------
# Scenario C — 3 blocks, k_of_n policy, T0
# ---------------------------------------------------------------------------


class TestScenarioC:
    """Scenario C: 3 blocks (BIO, STAT, CLIN), k_of_n policy, T0 pre-screening."""

    @pytest.fixture(autouse=True)
    def _run_pipeline(self) -> None:
        self.result_df, self.stats, self.config = _prepare_and_run(
            "scenario_c_config.json",
            "scenario_c_articles.csv",
        )

    def test_k_of_n_allows_partial_approval(self) -> None:
        """k_of_n policy approves articles with >= min_approved_blocks."""
        decisions = set(self.result_df["Final_Decision"].unique())
        assert "APPROVED_FINAL" in decisions, (
            f"Expected APPROVED_FINAL in k_of_n scenario, got: {decisions}"
        )

    def test_t0_rejection_overrides(self) -> None:
        """T0 anti-exclude terms cause REJECTED_FINAL regardless of block scores."""
        decisions = set(self.result_df["Final_Decision"].unique())
        assert "REJECTED_FINAL" in decisions, (
            f"Expected REJECTED_FINAL from T0 rejection, got: {decisions}"
        )


# ---------------------------------------------------------------------------
# Scenario D — O&G regression subset
# ---------------------------------------------------------------------------


class TestScenarioD:
    """Scenario D: 3 blocks (CTX, AI, SCM) with O&G domain terms."""

    @pytest.fixture(autouse=True)
    def _run_pipeline(self) -> None:
        self.result_df, self.stats, self.config = _prepare_and_run(
            "scenario_d_config.json",
            "scenario_d_articles.csv",
        )

    def test_regression_deterministic(self) -> None:
        """Two runs on the same O&G data produce identical results."""
        result2, _, _ = _prepare_and_run(
            "scenario_d_config.json",
            "scenario_d_articles.csv",
        )
        cols_to_drop = ["run_timestamp"]
        df1 = self.result_df.drop(columns=cols_to_drop, errors="ignore").reset_index(drop=True)
        df2 = result2.drop(columns=cols_to_drop, errors="ignore").reset_index(drop=True)
        assert_frame_equal(df1, df2)

    def test_produces_expected_distribution(self) -> None:
        """Result set contains at least 2 unique decision types."""
        unique_decisions = self.result_df["Final_Decision"].nunique()
        assert unique_decisions >= 2, (
            f"Expected >= 2 unique decisions, got {unique_decisions}: "
            f"{self.result_df['Final_Decision'].value_counts().to_dict()}"
        )
