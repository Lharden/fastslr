"""Level preset definitions for project scaffolding."""

from __future__ import annotations


LEVEL_PRESETS: dict[str, dict] = {
    "binary": {
        "description": "Binary: relevant or not relevant (1 level)",
        "level_count": 1,
        "level_scores": {1: 10},
        "approval_thresholds": {1: 5},
        "flagging_thresholds": {1: 3},
    },
    "simple": {
        "description": "Simple: 3 relevance levels",
        "level_count": 3,
        "level_scores": {1: 10, 2: 6, 3: 2},
        "approval_thresholds": {1: 8, 2: 10, 3: 14},
        "flagging_thresholds": {1: 4, 2: 6, 3: 8},
    },
    "standard": {
        "description": "Standard: 5 relevance levels (recommended)",
        "level_count": 5,
        "level_scores": {1: 10, 2: 8, 3: 6, 4: 4, 5: 2},
        "approval_thresholds": {1: 10, 2: 12, 3: 18, 4: 22, 5: None},
        "flagging_thresholds": {1: 6, 2: 6, 3: 6, 4: 7, 5: 12},
    },
}


def get_preset(name: str) -> dict:
    """Return a preset by name, or raise ValueError if not found."""
    if name not in LEVEL_PRESETS:
        available = ", ".join(sorted(LEVEL_PRESETS))
        raise ValueError(f"Unknown preset '{name}'. Available: {available}")
    return dict(LEVEL_PRESETS[name])


def build_custom_preset(
    n_levels: int,
    scores: dict[int, int],
    approval: dict[int, float | None],
    flagging: dict[int, float],
) -> dict:
    """Build a custom level preset from user-provided values."""
    if n_levels < 1:
        raise ValueError("Must have at least 1 level")
    return {
        "description": f"Custom: {n_levels} level(s)",
        "level_count": n_levels,
        "level_scores": dict(scores),
        "approval_thresholds": dict(approval),
        "flagging_thresholds": dict(flagging),
    }


def generate_config(
    preset_name: str,
    blocks: list[dict],
    fields: dict | None = None,
    custom_preset: dict | None = None,
) -> dict:
    """Generate a complete config dict from a preset and block definitions.

    *blocks* is a list of dicts like: [{"name": "CTX", "label": "Context"}]
    """
    if preset_name == "custom" and custom_preset:
        preset = custom_preset
    else:
        preset = get_preset(preset_name)

    if fields is None:
        fields = {
            "id": "key",
            "id_output": "ID",
            "title": "title",
            "abstract": "abstract",
            "manual_tags": "manual_tags",
        }

    scores = {str(k): v for k, v in preset["level_scores"].items()}
    approval = {str(k): v for k, v in preset["approval_thresholds"].items()}
    flagging = {str(k): v for k, v in preset["flagging_thresholds"].items()}

    config = {
        "global": {
            "DECISION_POLICY": "special",
            "ENABLE_SPECIAL_APPROVAL_RULE": True,
            "SPECIAL_APPROVAL_THRESHOLD": 40.0,
            "FAIL_FAST_GLOBAL": True,
            "NO_TAGS_UPLIFT": 1.17,
            "MAX_SECTION_SCORE": 30,
            "MAX_GAP_BETWEEN_TERMS": 2,
            "TOKEN_UNIT_FOR_GAPS": "\\S+",
            "ENABLE_PROXIMITY_DETECTION": True,
            "NOISE_PROFILE": "relaxed",
            "ERROR_POLICY": "flag",
            "PONTUACAO_NIVEIS": scores,
            "LIMITES_APROVADO": approval,
            "LIMITES_SINALIZADO": flagging,
            "WEIGHTS": {"title": 2.0, "abstract": 1.0, "manual_tags": 1.5},
            "BLOCK_ORDER": [b["name"] for b in blocks],
        },
        "fields": fields,
        "output": {
            "csv": False,
            "xlsx": True,
            "xlsx_engine": "openpyxl",
            "xlsx_sheet_name": "resultados",
            "academic_package": True,
        },
        "encoding": "utf-8-sig",
        "sep": ";",
    }

    return config


__all__ = [
    "LEVEL_PRESETS",
    "get_preset",
    "build_custom_preset",
    "generate_config",
]
