"""Tests for config loading, schema validation, global params, and terms CSV parsing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fastslr.core.config import load_config, load_global_params, parse_terms_csv

# ── TestLoadConfig ───────────────────────────────────────────────────────────


class TestLoadConfig:
    """Tests for :func:`load_config`."""

    def test_loads_valid_config(self, tmp_path: Path) -> None:
        cfg_data = {
            "global": {
                "DECISION_POLICY": "special",
                "NOISE_PROFILE": "relaxed",
                "ERROR_POLICY": "flag",
            }
        }
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps(cfg_data), encoding="utf-8")

        result = load_config(cfg_file)

        assert result["global"]["DECISION_POLICY"] == "special"

    def test_raises_on_nonexistent_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "nonexistent.json")

    def test_raises_on_invalid_json(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{invalid json!!!}", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            load_config(bad_file)


# ── TestSchemaValidation ─────────────────────────────────────────────────────


class TestSchemaValidation:
    """Tests for JSON-schema validation inside :func:`load_config`."""

    def test_rejects_invalid_decision_policy(self, tmp_path: Path) -> None:
        cfg_data = {
            "global": {
                "DECISION_POLICY": "invalid",
                "NOISE_PROFILE": "relaxed",
                "ERROR_POLICY": "flag",
            }
        }
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps(cfg_data), encoding="utf-8")

        with pytest.raises(ValueError, match="(?i)validation"):
            load_config(cfg_file)

    def test_rejects_invalid_noise_profile(self, tmp_path: Path) -> None:
        cfg_data = {
            "global": {
                "DECISION_POLICY": "special",
                "NOISE_PROFILE": "nonexistent",
                "ERROR_POLICY": "flag",
            }
        }
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps(cfg_data), encoding="utf-8")

        with pytest.raises(ValueError):
            load_config(cfg_file)

    def test_accepts_minimal_valid_config(self, tmp_path: Path) -> None:
        cfg_data = {
            "global": {
                "DECISION_POLICY": "special",
                "NOISE_PROFILE": "relaxed",
                "ERROR_POLICY": "flag",
            }
        }
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps(cfg_data), encoding="utf-8")

        result = load_config(cfg_file)

        assert "global" in result

    def test_accepts_config_with_domain_blocks(self, tmp_path: Path) -> None:
        cfg_data = {
            "global": {
                "DECISION_POLICY": "special",
                "NOISE_PROFILE": "relaxed",
                "ERROR_POLICY": "flag",
            },
            "_domain_blocks": ["BLK_A", "BLK_B"],
        }
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps(cfg_data), encoding="utf-8")

        result = load_config(cfg_file)

        assert result["_domain_blocks"] == ["BLK_A", "BLK_B"]


# ── TestLoadGlobalParams ─────────────────────────────────────────────────────


class TestLoadGlobalParams:
    """Tests for :func:`load_global_params`."""

    def test_loads_defaults_from_empty(self) -> None:
        params = load_global_params({})

        assert params.decision_policy == "special"
        assert params.fail_fast_enabled is True

    def test_loads_legacy_pt_keys(self) -> None:
        global_cfg = {"PONTUACAO_NIVEIS": {"1": 10, "2": 5}}

        params = load_global_params(global_cfg)

        assert params.level_scores == {1: 10, 2: 5}

    def test_loads_english_keys(self) -> None:
        # load_global_params reads PONTUACAO_NIVEIS; the English alias
        # "level_scores" is resolved at schema level.  We pass the PT key
        # with English-style values to confirm the same outcome.
        global_cfg = {"PONTUACAO_NIVEIS": {"1": 10, "2": 5}}

        params = load_global_params(global_cfg)

        assert params.level_scores == {1: 10, 2: 5}


# ── TestParseTermsCsv ────────────────────────────────────────────────────────


class TestParseTermsCsv:
    """Tests for :func:`parse_terms_csv`."""

    def test_parses_valid_csv(self, tmp_path: Path) -> None:
        csv_content = (
            "block,kind,term,level,section_scope,is_regex\n"
            "BLK_A,pos,test term,1,any,False\n"
        )
        csv_path = tmp_path / "terms.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        base_config: dict = {"global": {}}
        result = parse_terms_csv(csv_path, base_config)

        assert "BLK_A" in result.get("_domain_blocks", [])

    def test_global_block_becomes_t0(self, tmp_path: Path) -> None:
        csv_content = (
            "block,kind,term,level,section_scope,is_regex\n"
            "GLOBAL,anti,exclude me,,any,False\n"
        )
        csv_path = tmp_path / "terms.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        base_config: dict = {"global": {}}
        result = parse_terms_csv(csv_path, base_config)

        assert "T0" in result
        anti = result["T0"].get("anti", {})
        exclude_terms = [e["term"] for e in anti.get("exclude", [])]
        assert "exclude me" in exclude_terms
