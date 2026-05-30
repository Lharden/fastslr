"""Regression tests for single-source-of-truth invariants.

Covers two audit findings:

* ``flagging-threshold-l4-divergence`` -- the level-4 flagging threshold must be
  identical across all three configuration sources (``constants.py`` defaults,
  the ``standard`` preset and the bundled ``default_config.json``). They diverged
  only at level 4 (8 vs 7), producing non-deterministic triage depending on the
  config path that was loaded.
* ``versao-duplicada-mao`` -- the package version must come from a single source.
  ``fastslr.__version__`` (re-exported from ``constants.VERSION``) must equal the
  metadata version resolved by ``importlib.metadata`` (fed by ``pyproject.toml``).
"""

from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path

import fastslr
from fastslr.core.constants import DEFAULT_FLAGGING_THRESHOLDS, VERSION
from fastslr.core.presets import LEVEL_PRESETS

_DEFAULT_CONFIG_PATH = Path(fastslr.__file__).resolve().parent / "core" / "default_config.json"


def _load_json_flagging_thresholds() -> dict[int, float]:
    """Return ``LIMITES_SINALIZADO`` from the bundled default config, int-keyed."""
    with _DEFAULT_CONFIG_PATH.open(encoding="utf-8") as fh:
        config = json.load(fh)
    raw: dict[str, float] = config["global"]["LIMITES_SINALIZADO"]
    return {int(level): value for level, value in raw.items()}


def test_flagging_threshold_l4_aligned_across_sources() -> None:
    """Level-4 flagging threshold is 7 in all three sources of truth."""
    json_thresholds = _load_json_flagging_thresholds()
    preset_thresholds = LEVEL_PRESETS["standard"]["flagging_thresholds"]

    assert DEFAULT_FLAGGING_THRESHOLDS[4] == 7
    assert preset_thresholds[4] == 7
    assert json_thresholds[4] == 7

    # All three must agree on the same value for level 4.
    assert DEFAULT_FLAGGING_THRESHOLDS[4] == preset_thresholds[4] == json_thresholds[4]


def test_flagging_thresholds_fully_consistent_across_sources() -> None:
    """The complete standard flagging-threshold mapping matches all sources."""
    json_thresholds = _load_json_flagging_thresholds()
    preset_thresholds = LEVEL_PRESETS["standard"]["flagging_thresholds"]

    assert DEFAULT_FLAGGING_THRESHOLDS == preset_thresholds
    assert DEFAULT_FLAGGING_THRESHOLDS == json_thresholds


def test_version_single_source_of_truth() -> None:
    """``__version__`` equals the installed package metadata version."""
    metadata_version = importlib.metadata.version("fastslr")
    assert fastslr.__version__ == metadata_version
    assert VERSION == metadata_version
