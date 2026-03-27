"""Tests for the presets module: get_preset, build_custom_preset, generate_config."""

from __future__ import annotations

import pytest

from fastslr.core.presets import (
    LEVEL_PRESETS,
    build_custom_preset,
    generate_config,
    get_preset,
)

REQUIRED_PRESET_KEYS = {
    "description",
    "level_count",
    "level_scores",
    "approval_thresholds",
    "flagging_thresholds",
}


# ── TestGetPreset ────────────────────────────────────────────────────────────


class TestGetPreset:
    """Tests for :func:`get_preset`."""

    def test_returns_binary_preset(self) -> None:
        preset = get_preset("binary")

        assert preset["level_count"] == 1

    def test_returns_simple_preset(self) -> None:
        preset = get_preset("simple")

        assert preset["level_count"] == 3

    def test_returns_standard_preset(self) -> None:
        preset = get_preset("standard")

        assert preset["level_count"] == 5

    def test_raises_on_unknown(self) -> None:
        with pytest.raises(ValueError):
            get_preset("nonexistent_preset")

    def test_all_presets_have_required_keys(self) -> None:
        assert "binary" in LEVEL_PRESETS
        assert "simple" in LEVEL_PRESETS
        assert "standard" in LEVEL_PRESETS

        for name, preset in LEVEL_PRESETS.items():
            missing = REQUIRED_PRESET_KEYS - set(preset.keys())
            assert not missing, f"Preset '{name}' missing keys: {missing}"


# ── TestBuildCustomPreset ────────────────────────────────────────────────────


class TestBuildCustomPreset:
    """Tests for :func:`build_custom_preset`."""

    def test_valid_custom(self) -> None:
        result = build_custom_preset(
            n_levels=2,
            scores={1: 10, 2: 5},
            approval={1: 8, 2: 10},
            flagging={1: 4, 2: 6},
        )

        assert result["level_count"] == 2

    def test_raises_on_zero_levels(self) -> None:
        with pytest.raises(ValueError):
            build_custom_preset(
                n_levels=0,
                scores={},
                approval={},
                flagging={},
            )


# ── TestGenerateConfig ───────────────────────────────────────────────────────


class TestGenerateConfig:
    """Tests for :func:`generate_config`."""

    def test_generates_config(self) -> None:
        blocks = [{"name": "BLK_A"}]

        result = generate_config(preset_name="standard", blocks=blocks)

        assert "global" in result
        assert result["global"]["DECISION_POLICY"] == "special"
