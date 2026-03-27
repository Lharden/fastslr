"""Configuration loading, terms CSV parsing, and parameter construction."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

from .constants import (
    DEFAULT_APPROVAL_THRESHOLDS,
    DEFAULT_FLAGGING_THRESHOLDS,
    DEFAULT_LEVEL_SCORES,
    DEFAULT_SECTION_WEIGHTS,
    GLOBAL_BLOCK_NAME,
    T0_BLOCK_NAME,
    VALID_SCOPES,
)
from .models import GlobalParams
from .normalization import extract_normalization_rules

logger = logging.getLogger(__name__)

_SCHEMA_DIR = Path(__file__).resolve().parent


def _validate_config_schema(config: dict) -> None:
    """Validate *config* against the bundled JSON Schema.

    Raises :class:`ValueError` with a user-friendly message on validation
    failure.  If the schema file is missing or ``jsonschema`` is not installed
    the function logs a warning and returns silently (graceful degradation).

    Args:
        config: Configuration dictionary to validate.

    Raises:
        ValueError: If the configuration violates the JSON Schema.
    """
    schema_path = _SCHEMA_DIR / "config_schema.json"
    if not schema_path.exists():
        logger.warning("Config schema file not found at %s — skipping validation.", schema_path)
        return

    try:
        import jsonschema  # noqa: WPS433 (local import for optional dep)
    except ImportError:  # pragma: no cover
        logger.warning("jsonschema package not installed — skipping config validation.")
        return

    with open(schema_path, encoding="utf-8") as fh:
        schema = json.load(fh)

    try:
        jsonschema.validate(instance=config, schema=schema)
    except jsonschema.ValidationError as exc:
        field_path = ".".join(str(p) for p in exc.absolute_path) if exc.absolute_path else "(root)"
        raise ValueError(
            f"Config schema validation error at '{field_path}': {exc.message}"
        ) from exc


def load_config(path: str | Path) -> dict:
    """Load a JSON configuration file and validate its schema.

    Args:
        path: Filesystem path to the JSON configuration file.

    Returns:
        Parsed configuration dictionary.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        ValueError: If the file fails JSON-schema validation.
    """
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        config: dict = json.load(f)

    _validate_config_schema(config)
    return config


def auto_detect_input(input_dir: Path) -> Path | None:
    """Auto-detect a CSV input file in the given directory."""
    if not input_dir.exists():
        return None

    csv_files = sorted(input_dir.glob("*.csv"))
    if len(csv_files) == 1:
        return csv_files[0]

    for pattern in ("*corpus*", "*input*", "*articles*"):
        matches = sorted(input_dir.glob(f"{pattern}.csv"))
        if matches:
            return matches[0]

    return csv_files[0] if csv_files else None


def get_domain_blocks(config: dict) -> list[str]:
    """Return the list of domain block names from the configuration.

    Args:
        config: Loaded triage configuration dict.

    Returns:
        Ordered list of domain block name strings (excludes T0/GLOBAL).
    """
    return list(config.get("_domain_blocks", []))


def load_global_params(global_cfg: dict) -> GlobalParams:
    """Construct a :class:`GlobalParams` instance from the global configuration dict.

    Reads scoring weights, thresholds, policy flags, and noise-filter
    settings from the ``global`` section, falling back to built-in defaults
    for any missing key.

    Args:
        global_cfg: The ``config["global"]`` sub-dictionary.

    Returns:
        A fully populated :class:`GlobalParams` dataclass.
    """
    raw_levels = global_cfg.get("PONTUACAO_NIVEIS", {})
    level_scores = (
        {int(k): int(v) for k, v in raw_levels.items()}
        if raw_levels
        else dict(DEFAULT_LEVEL_SCORES)
    )

    raw_weights = global_cfg.get("WEIGHTS", {})
    section_weights = (
        {k: float(v) for k, v in raw_weights.items()}
        if raw_weights
        else dict(DEFAULT_SECTION_WEIGHTS)
    )

    raw_approval = global_cfg.get("LIMITES_APROVADO", {})
    if raw_approval:
        approval_thresholds = {
            int(k): (float(v) if v is not None else None) for k, v in raw_approval.items()
        }
    else:
        approval_thresholds = dict(DEFAULT_APPROVAL_THRESHOLDS)

    raw_flagging = global_cfg.get("LIMITES_SINALIZADO", {})
    flagging_thresholds = (
        {int(k): float(v) for k, v in raw_flagging.items()}
        if raw_flagging
        else dict(DEFAULT_FLAGGING_THRESHOLDS)
    )

    level_order_raw = global_cfg.get("LEVEL_ORDER")
    if level_order_raw:
        level_order = tuple(int(x) for x in level_order_raw)
    else:
        level_order = tuple(sorted(level_scores.keys()))

    weak_raw = global_cfg.get("WEAK_LEVELS")
    if weak_raw:
        weak_levels = tuple(int(x) for x in weak_raw)
    else:
        weak_levels = (max(level_scores.keys()),) if level_scores else (5,)

    return GlobalParams(
        level_scores=level_scores,
        section_weights=section_weights,
        approval_thresholds=approval_thresholds,
        flagging_thresholds=flagging_thresholds,
        no_tags_uplift=float(
            global_cfg.get("NO_TAGS_UPLIFT", global_cfg.get("UPLIFT_NO_MANUAL_TAGS", 1.17))
        ),
        max_section_score=float(
            global_cfg.get("MAX_SECTION_SCORE", global_cfg.get("MAX_SCORE_POR_SECAO", 30))
        ),
        fail_fast_enabled=bool(global_cfg.get("FAIL_FAST_GLOBAL", True)),
        special_approval_threshold=float(
            global_cfg.get(
                "SPECIAL_APPROVAL_THRESHOLD", global_cfg.get("THRESHOLD_APROVACAO_ESPECIAL", 40.0)
            )
        ),
        max_gap_between_terms=int(global_cfg.get("MAX_GAP_BETWEEN_TERMS", 2)),
        token_unit_for_gaps=str(global_cfg.get("TOKEN_UNIT_FOR_GAPS", r"\S+")),
        enable_proximity_detection=bool(global_cfg.get("ENABLE_PROXIMITY_DETECTION", True)),
        level_order=level_order,
        enable_special_approval_rule=bool(global_cfg.get("ENABLE_SPECIAL_APPROVAL_RULE", True)),
        decision_policy=str(global_cfg.get("DECISION_POLICY", "special")),
        min_approved_blocks=global_cfg.get("MIN_APPROVED_BLOCKS"),
        max_flagged_blocks_for_approval=int(global_cfg.get("MAX_FLAGGED_BLOCKS_FOR_APPROVAL", 0)),
        noise_profile=str(global_cfg.get("NOISE_PROFILE", "relaxed")),
        min_unique_terms_for_approval=int(global_cfg.get("MIN_UNIQUE_TERMS_FOR_APPROVAL", 1)),
        min_sections_with_hits_for_approval=int(
            global_cfg.get("MIN_SECTIONS_WITH_HITS_FOR_APPROVAL", 1)
        ),
        require_non_weak_term_for_approval=bool(
            global_cfg.get("REQUIRE_NON_WEAK_TERM_FOR_APPROVAL", False)
        ),
        weak_levels=weak_levels,
        error_policy=str(global_cfg.get("ERROR_POLICY", "flag")),
        max_error_rate=float(global_cfg.get("MAX_ERROR_RATE", 0.05)),
    )


def parse_terms_csv(terms_path: str | Path, base_config: dict) -> dict:
    """Parse a terms CSV and merge term definitions into the base configuration.

    The terms CSV must have columns: ``block``, ``kind``, ``term``, ``level``,
    ``section_scope``, ``is_regex``.  The ``block`` column determines which
    thematic block a term belongs to.  ``GLOBAL`` block terms become T0
    anti-terms.

    Args:
        terms_path: Path to the terms CSV file.
        base_config: Base configuration dict (typically from :func:`load_config`).

    Returns:
        A new configuration dict with term entries merged under their
        respective block keys and ``_domain_blocks`` populated.

    Raises:
        ValueError: If required columns are missing from the CSV.
    """
    from .io import load_csv_safe

    terms_path = Path(terms_path)
    df = load_csv_safe(terms_path)

    config = dict(base_config)

    normalization_rules = extract_normalization_rules(df)
    config["normalization_rules"] = normalization_rules

    required_cols = {"block", "kind", "term"}
    if not required_cols.issubset(set(df.columns)):
        raise ValueError(f"Terms CSV missing required columns: {required_cols - set(df.columns)}")

    block_terms: dict[str, dict] = {}
    valid_count = 0

    for idx, row in df.iterrows():
        try:
            block = str(row.get("block", "")).strip()
            kind = str(row.get("kind", "")).strip().lower()
            term = str(row.get("term", "")).strip()

            if not block or not kind or not term or pd.isna(block) or pd.isna(term):
                continue

            level = row.get("level", "")
            if pd.isna(level):
                level = ""
            level = str(level).strip()

            scope = str(row.get("section_scope", "any")).strip().lower()
            if scope not in VALID_SCOPES:
                scope = "any"

            is_regex_raw = row.get("is_regex", "0")
            if pd.isna(is_regex_raw):
                is_regex_raw = "0"
            is_regex = str(is_regex_raw).strip().lower() in ("1", "true", "yes")

            if block not in block_terms:
                block_terms[block] = {
                    "positives": [],
                    "anti": {"exclude": [], "flag": []},
                }

            entry = {
                "term": term,
                "level": level if level else None,
                "scope": scope,
                "regex": is_regex,
                "source_row": int(idx) if idx is not None else None,
            }

            if kind == "pos":
                block_terms[block]["positives"].append(entry)
            elif kind == "anti":
                block_terms[block]["anti"]["exclude"].append(entry)
            elif kind == "flag":
                block_terms[block]["anti"]["flag"].append(entry)

            valid_count += 1
        except (KeyError, TypeError, ValueError) as exc:
            logger.debug("Skipping row %s: %s", idx, exc)
            continue

    config["_valid_terms_count"] = valid_count

    domain_blocks: list[str] = []
    block_labels: dict[str, str] = {}

    block_order = config.get("global", {}).get("BLOCK_ORDER")
    if block_order:
        ordered = list(block_order)
    else:
        ordered = sorted(k for k in block_terms if k != GLOBAL_BLOCK_NAME)

    for block_name in ordered:
        if block_name == GLOBAL_BLOCK_NAME:
            continue
        if block_name in block_terms:
            config[block_name] = block_terms[block_name]
            domain_blocks.append(block_name)
            block_labels[block_name] = block_name

    config["_domain_blocks"] = domain_blocks
    config["_block_labels"] = block_labels

    if GLOBAL_BLOCK_NAME in block_terms:
        global_terms = block_terms[GLOBAL_BLOCK_NAME]
        config[T0_BLOCK_NAME] = {
            "positives": global_terms.get("positives", []),
            "anti": global_terms.get("anti", {"exclude": [], "flag": []}),
        }

    return config


__all__ = [
    "load_config",
    "auto_detect_input",
    "get_domain_blocks",
    "load_global_params",
    "parse_terms_csv",
]
