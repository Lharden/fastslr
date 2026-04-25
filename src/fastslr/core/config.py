"""Configuration loading, terms table parsing, and parameter construction."""

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
    TERM_KINDS,
    VALID_SCOPES,
)
from .models import GlobalParams
from .normalization import extract_normalization_rules

logger = logging.getLogger(__name__)


def load_config(path: str | Path) -> dict:
    """Load a JSON configuration file."""
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


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
    """Return the list of domain block names from the configuration."""
    configured_blocks = list(config.get("_domain_blocks", []))
    if configured_blocks:
        return configured_blocks

    block_order = config.get("global", {}).get("BLOCK_ORDER", [])
    inline_blocks = [
        block_name
        for block_name in block_order
        if isinstance(config.get(block_name), dict) and "positives" in config[block_name]
    ]
    if inline_blocks:
        return inline_blocks

    return []


def load_global_params(global_cfg: dict) -> GlobalParams:
    """Construct a GlobalParams instance from the global configuration dict."""
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
    """Parse a terms CSV/XLSX table and merge terms into the base configuration.

    The terms table must have columns: block, kind, term, level, section_scope, is_regex.
    The 'block' column determines which thematic block a term belongs to.
    'GLOBAL' block terms become T0 anti-terms.
    """
    from .io import load_table_safe

    terms_path = Path(terms_path)
    df = load_table_safe(terms_path)

    config = dict(base_config)

    required_cols = {"block", "kind", "term"}
    if not required_cols.issubset(set(df.columns)):
        raise ValueError(f"Terms CSV missing required columns: {required_cols - set(df.columns)}")

    # Resolve configured level range for validation
    global_cfg = base_config.get("global", {})
    raw_level_scores = global_cfg.get("PONTUACAO_NIVEIS", {})
    configured_levels: set[int] = set()
    if raw_level_scores:
        configured_levels = {int(k) for k in raw_level_scores}

    _VALID_IS_REGEX = frozenset({"0", "1", "true", "false", "yes", "no", ""})

    parse_warnings: list[str] = []

    normalization_rules = extract_normalization_rules(df, warnings=parse_warnings)
    config["normalization_rules"] = normalization_rules

    block_terms: dict[str, dict] = {}
    valid_count = 0
    # Dedup key: (block, kind, term_lower, scope, level_str, is_regex).
    # Rows that share a term but differ in scope, level, or regex flag are
    # intentionally distinct rules and must all be kept.
    seen_terms: set[tuple[str, str, str, str, str, bool]] = set()

    for idx, row in df.iterrows():
        try:
            block = str(row.get("block", "")).strip()
            kind = str(row.get("kind", "")).strip().lower()
            term = str(row.get("term", "")).strip()
            row_num = int(idx) + 2 if idx is not None else None  # +2: header + 0-indexed

            # ── empty fields ──────────────────────────────────────────
            empty_fields: list[str] = []
            if not block or pd.isna(block):
                empty_fields.append("block")
            if not kind or pd.isna(kind):
                empty_fields.append("kind")
            if not term or pd.isna(term):
                empty_fields.append("term")
            if empty_fields:
                parse_warnings.append(
                    f"Row {row_num}: empty {', '.join(empty_fields)}. Row skipped."
                )
                continue

            # ── kind validation ───────────────────────────────────────
            if kind not in TERM_KINDS:
                parse_warnings.append(
                    f"Row {row_num}, block '{block}', term '{term}': "
                    f"invalid kind '{kind}' (valid: {', '.join(sorted(TERM_KINDS))}). "
                    f"Row skipped."
                )
                continue

            # ── level validation ──────────────────────────────────────
            level = row.get("level", "")
            if pd.isna(level):
                level = ""
            level = str(level).strip()

            if kind == "pos":
                if not level:
                    parse_warnings.append(
                        f"Row {row_num}, block '{block}', term '{term}': "
                        f"positive term without level. Score contribution will be 0."
                    )
                else:
                    try:
                        # Handle Excel float formatting: "1.0" → 1
                        level_float = float(level)
                        if level_float != int(level_float):
                            raise ValueError("fractional level")
                        level_int = int(level_float)
                        level = str(level_int)
                        if configured_levels and level_int not in configured_levels:
                            parse_warnings.append(
                                f"Row {row_num}, block '{block}', term '{term}': "
                                f"level {level_int} not in configured levels "
                                f"({', '.join(str(lv) for lv in sorted(configured_levels))}). "
                                f"Score contribution will be 0."
                            )
                    except (ValueError, TypeError):
                        examples = (
                            ", ".join(str(lv) for lv in sorted(configured_levels))
                            if configured_levels
                            else "1, 2, 3..."
                        )
                        parse_warnings.append(
                            f"Row {row_num}, block '{block}', term '{term}': "
                            f"invalid level '{level}' (must be a whole number, "
                            f"e.g. {examples}). "
                            f"Score contribution will be 0."
                        )
                        level = ""
            elif level:
                # anti/flag with level filled — doesn't make sense
                parse_warnings.append(
                    f"Row {row_num}, block '{block}', term '{term}': "
                    f"level is ignored for '{kind}' terms."
                )

            # ── section_scope validation ──────────────────────────────
            scope = str(row.get("section_scope", "any")).strip().lower()
            if scope not in VALID_SCOPES:
                parse_warnings.append(
                    f"Row {row_num}, block '{block}', term '{term}': "
                    f"invalid section_scope '{scope}' (valid: {', '.join(sorted(VALID_SCOPES))}). "
                    f"Defaulting to 'any'."
                )
                scope = "any"

            # ── is_regex validation ───────────────────────────────────
            is_regex_raw = row.get("is_regex", "0")
            if pd.isna(is_regex_raw):
                is_regex_raw = "0"
            is_regex_str = str(is_regex_raw).strip().lower()
            if is_regex_str not in _VALID_IS_REGEX:
                parse_warnings.append(
                    f"Row {row_num}, block '{block}', term '{term}': "
                    f"invalid is_regex '{is_regex_raw}' (valid: 0, 1). "
                    f"Defaulting to 0 (plain text)."
                )
            is_regex = is_regex_str in ("1", "true", "yes")

            # ── duplicate detection ───────────────────────────────────
            # Key must include scope, level and is_regex so that rows
            # intentionally reusing a term across sections, levels or
            # regex/literal variants are preserved as distinct rules.
            dedup_key = (block, kind, term.lower(), scope, level, is_regex)
            if dedup_key in seen_terms:
                parse_warnings.append(
                    f"Row {row_num}, block '{block}', term '{term}': "
                    f"duplicate term (same block, kind, scope, level and is_regex). "
                    f"Only the first occurrence is used. Row skipped."
                )
                continue
            seen_terms.add(dedup_key)

            # ── build entry ───────────────────────────────────────────
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

    # ── block-level validation ────────────────────────────────────────
    block_order = global_cfg.get("BLOCK_ORDER")

    # Warn about blocks in CSV that are not in BLOCK_ORDER
    if block_order:
        ordered_set = set(block_order)
        for csv_block in sorted(block_terms):
            if csv_block != GLOBAL_BLOCK_NAME and csv_block not in ordered_set:
                term_count = (
                    len(block_terms[csv_block].get("positives", []))
                    + len(block_terms[csv_block].get("anti", {}).get("exclude", []))
                    + len(block_terms[csv_block].get("anti", {}).get("flag", []))
                )
                parse_warnings.append(
                    f"Block '{csv_block}' has {term_count} term(s) in CSV but is not in "
                    f"BLOCK_ORDER ({', '.join(block_order)}). All its terms will be ignored."
                )

    # ── cross-term logical validation ─────────────────────────────────
    parse_errors: list[str] = []

    for blk_name, blk_data in block_terms.items():
        if blk_name == GLOBAL_BLOCK_NAME:
            continue

        pos_terms = {e["term"].lower() for e in blk_data.get("positives", [])}
        anti_excl_terms = {
            e["term"].lower() for e in blk_data.get("anti", {}).get("exclude", [])
        }
        anti_flag_terms = {
            e["term"].lower() for e in blk_data.get("anti", {}).get("flag", [])
        }

        # #15: positive + anti-exclude conflict → BLOCKS RUN
        for conflict in sorted(pos_terms & anti_excl_terms):
            parse_errors.append(
                f"Block '{blk_name}': term '{conflict}' is both 'pos' and 'anti'. "
                f"Logic contradiction — keep it as 'pos' OR 'anti', not both."
            )

        # #18: positive + anti-flag conflict → BLOCKS RUN
        for conflict in sorted(pos_terms & anti_flag_terms):
            parse_errors.append(
                f"Block '{blk_name}': term '{conflict}' is both 'pos' and 'flag'. "
                f"Logic contradiction — keep it as 'pos' OR 'flag', not both."
            )

        # #16: wildcard-only or single-char terms
        for entry in blk_data.get("positives", []):
            t = entry["term"].strip()
            if t in ("*", "?") or (len(t) == 1 and t.isalpha()):
                parse_warnings.append(
                    f"Block '{blk_name}': term '{t}' is too broad — "
                    f"will match nearly everything."
                )

        # #17: block with anti-terms but no positives
        has_positives = len(blk_data.get("positives", [])) > 0
        has_anti = (
            len(blk_data.get("anti", {}).get("exclude", []))
            + len(blk_data.get("anti", {}).get("flag", []))
        ) > 0
        if has_anti and not has_positives:
            parse_warnings.append(
                f"Block '{blk_name}' has anti-terms but no positive terms. "
                f"Score will always be 0 — this block can only reject, never approve."
            )

    config["_parse_warnings"] = parse_warnings
    config["_parse_errors"] = parse_errors

    domain_blocks: list[str] = []
    block_labels: dict[str, str] = {}

    def _is_inline_block(value: object) -> bool:
        """Return True if a base_config entry looks like an inline block definition."""
        return isinstance(value, dict) and "positives" in value

    inline_block_names = {
        name for name, value in base_config.items()
        if name not in {GLOBAL_BLOCK_NAME, T0_BLOCK_NAME} and _is_inline_block(value)
    }

    if block_order:
        ordered = list(block_order)
    else:
        csv_names = {k for k in block_terms if k != GLOBAL_BLOCK_NAME}
        ordered = sorted(csv_names | inline_block_names)

    for block_name in ordered:
        if block_name == GLOBAL_BLOCK_NAME:
            continue
        csv_block = block_terms.get(block_name)
        base_entry = base_config.get(block_name)
        inline = base_entry if _is_inline_block(base_entry) else None

        if csv_block is not None and inline is not None:
            # Merge CSV terms into the existing inline block so both survive.
            inline_anti = inline.get("anti", {}) or {}
            csv_anti = csv_block.get("anti", {})
            config[block_name] = {
                "positives": list(inline.get("positives", []))
                + list(csv_block.get("positives", [])),
                "anti": {
                    "exclude": list(inline_anti.get("exclude", []))
                    + list(csv_anti.get("exclude", [])),
                    "flag": list(inline_anti.get("flag", []))
                    + list(csv_anti.get("flag", [])),
                },
            }
            domain_blocks.append(block_name)
            block_labels[block_name] = block_name
        elif csv_block is not None:
            config[block_name] = csv_block
            domain_blocks.append(block_name)
            block_labels[block_name] = block_name
        elif inline is not None:
            # Block defined only in config.json: preserve it unchanged.
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
