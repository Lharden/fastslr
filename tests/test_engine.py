"""End-to-end tests for the triage engine pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

import fastslr.core.engine as engine_module
from fastslr.core.config import get_domain_blocks, load_global_params, parse_terms_csv
from fastslr.core.engine import collect_statistics, process_articles
from fastslr.core.io import compute_config_hash
from fastslr.core.normalization import NormalizationEngine
from fastslr.core.patterns import precompile_patterns


@pytest.fixture
def sample_config():
    """Minimal configuration for end-to-end testing."""
    config_path = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "fastslr"
        / "core"
        / "default_config.json"
    )
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_articles():
    """Small DataFrame with test articles."""
    return pd.DataFrame(
        {
            "key": ["A001", "A002", "A003", "A004"],
            "title": [
                "Machine learning for oil and gas supply chain optimization",
                "A systematic review of cooking recipes",
                "Neural networks in petroleum logistics management",
                "Blockchain in pharmaceutical supply chain",
            ],
            "abstract": [
                "This paper applies artificial intelligence to supply chain "
                "management in the petroleum industry.",
                "We review 100 recipes using deep learning classification.",
                "Deep learning and predictive analytics for offshore operations "
                "and procurement.",
                "Blockchain technology applied to drug manufacturing and distribution.",
            ],
            "manual_tags": ["", "", "SCM, AI, oil", ""],
        }
    )


@pytest.fixture
def mini_terms_csv(tmp_path):
    """Create a minimal terms CSV for testing."""
    terms = pd.DataFrame(
        {
            "block": [
                "GLOBAL",
                "GLOBAL",
                "CTX",
                "CTX",
                "TECH",
                "TECH",
                "SCM",
                "SCM",
            ],
            "kind": [
                "anti",
                "flag",
                "pos",
                "pos",
                "pos",
                "pos",
                "pos",
                "pos",
            ],
            "term": [
                "systematic review",
                "case study",
                "oil and gas",
                "petroleum",
                "artificial intelligence",
                "machine learning",
                "supply chain management",
                "procurement",
            ],
            "level": [
                "",
                "",
                "1",
                "2",
                "1",
                "2",
                "1",
                "3",
            ],
            "section_scope": ["any"] * 8,
            "is_regex": ["0"] * 8,
        }
    )
    path = tmp_path / "test_terms.csv"
    terms.to_csv(path, sep=";", index=False)
    return path


class TestProcessArticles:
    def test_pipeline_produces_results(
        self, sample_config, sample_articles, mini_terms_csv
    ):
        config = parse_terms_csv(str(mini_terms_csv), sample_config)
        engine = NormalizationEngine(config.get("normalization_rules", {}))
        gp = load_global_params(config.get("global", {}))

        for block_name in get_domain_blocks(config):
            config[block_name] = precompile_patterns(config[block_name], engine, gp)
        if "T0" in config:
            config["T0"] = precompile_patterns(config["T0"], engine, gp)

        result_df, stats = process_articles(
            sample_articles, config, on_progress=None
        )

        assert len(result_df) > 0
        assert "Final_Decision" in result_df.columns
        assert stats["total_articles"] > 0
        assert stats["processing_time"] >= 0

    def test_systematic_review_rejected(
        self, sample_config, sample_articles, mini_terms_csv
    ):
        config = parse_terms_csv(str(mini_terms_csv), sample_config)
        engine = NormalizationEngine(config.get("normalization_rules", {}))
        gp = load_global_params(config.get("global", {}))

        for block_name in get_domain_blocks(config):
            config[block_name] = precompile_patterns(config[block_name], engine, gp)
        if "T0" in config:
            config["T0"] = precompile_patterns(config["T0"], engine, gp)

        result_df, _ = process_articles(sample_articles, config, on_progress=None)

        # Article A002 "A systematic review of cooking recipes" should be rejected
        a002 = result_df[result_df.iloc[:, 0] == "A002"]
        if not a002.empty:
            assert a002.iloc[0]["Final_Decision"] == "REJECTED_FINAL"

    def test_relevant_article_not_rejected(
        self, sample_config, sample_articles, mini_terms_csv
    ):
        config = parse_terms_csv(str(mini_terms_csv), sample_config)
        engine = NormalizationEngine(config.get("normalization_rules", {}))
        gp = load_global_params(config.get("global", {}))

        for block_name in get_domain_blocks(config):
            config[block_name] = precompile_patterns(config[block_name], engine, gp)
        if "T0" in config:
            config["T0"] = precompile_patterns(config["T0"], engine, gp)

        result_df, _ = process_articles(sample_articles, config, on_progress=None)

        # Article A001 is directly relevant (oil+gas, AI, SCM) — should not be rejected
        a001 = result_df[result_df.iloc[:, 0] == "A001"]
        if not a001.empty:
            assert a001.iloc[0]["Final_Decision"] != "REJECTED_FINAL"

    def test_error_policy_flag_keeps_article(
        self, sample_config, mini_terms_csv, monkeypatch
    ):
        cfg = parse_terms_csv(str(mini_terms_csv), sample_config)
        cfg["global"]["ERROR_POLICY"] = "flag"

        engine = NormalizationEngine(cfg.get("normalization_rules", {}))
        gp = load_global_params(cfg.get("global", {}))
        for block_name in get_domain_blocks(cfg):
            cfg[block_name] = precompile_patterns(cfg[block_name], engine, gp)
        if "T0" in cfg:
            cfg["T0"] = precompile_patterns(cfg["T0"], engine, gp)

        def _boom(*_args, **_kwargs):
            raise RuntimeError("forced test failure")

        monkeypatch.setattr(engine_module, "evaluate_block", _boom)

        df = pd.DataFrame(
            {
                "key": ["E001"],
                "title": ["oil and gas"],
                "abstract": ["machine learning"],
                "manual_tags": [""],
            }
        )

        result_df, stats = process_articles(df, cfg, on_progress=None)
        assert len(result_df) == 1
        assert result_df.iloc[0]["Final_Decision"] == "FLAGGED_FINAL"
        assert stats["error_count"] == 1

    def test_error_policy_fail_raises(self, sample_config, mini_terms_csv, monkeypatch):
        cfg = parse_terms_csv(str(mini_terms_csv), sample_config)
        cfg["global"]["ERROR_POLICY"] = "fail"

        engine = NormalizationEngine(cfg.get("normalization_rules", {}))
        gp = load_global_params(cfg.get("global", {}))
        for block_name in get_domain_blocks(cfg):
            cfg[block_name] = precompile_patterns(cfg[block_name], engine, gp)
        if "T0" in cfg:
            cfg["T0"] = precompile_patterns(cfg["T0"], engine, gp)

        def _boom(*_args, **_kwargs):
            raise RuntimeError("forced fail policy")

        monkeypatch.setattr(engine_module, "evaluate_block", _boom)

        df = pd.DataFrame(
            {
                "key": ["E002"],
                "title": ["oil and gas"],
                "abstract": ["machine learning"],
                "manual_tags": [""],
            }
        )

        with pytest.raises(RuntimeError):
            process_articles(df, cfg, on_progress=None)


class TestCollectStatistics:
    def test_basic_statistics(self):
        df = pd.DataFrame(
            {
                "Final_Decision": [
                    "APPROVED_FINAL",
                    "REJECTED_FINAL",
                    "REJECTED_FINAL",
                ],
                "Status_CTX": ["APPROVED", "REJECTED", "REJECTED"],
                "FinalScore_CTX": [25.0, 0.0, 0.0],
            }
        )
        stats = collect_statistics(df)
        assert stats["total_articles"] == 3
        assert "APPROVED_FINAL" in stats["decision_distribution"]
        assert stats["decision_distribution"]["APPROVED_FINAL"] == 1

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        stats = collect_statistics(df)
        assert stats["total_articles"] == 0


class TestConfigHash:
    def test_deterministic_hash(self, sample_config):
        h1 = compute_config_hash(sample_config)
        h2 = compute_config_hash(sample_config)
        assert h1 == h2
        assert len(h1) == 16
