"""I/O operations: CSV/XLSX loading, export, report generation, and audit."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from types import ModuleType

import pandas as pd

from .constants import ALL_BLOCKS, DOMAIN_BLOCKS, SECTION_NAMES, VERSION
from .models import AntiHit, BlockEvaluation

chardet: ModuleType | None
try:
    import chardet as _chardet
except ModuleNotFoundError:  # pragma: no cover - optional dependency fallback
    chardet = None
else:
    chardet = _chardet

logger = logging.getLogger(__name__)


# ── hashing ──────────────────────────────────────────────────────────────────


def _sanitize_config_for_serialization(config: dict) -> dict:
    """Remove non-serializable elements from the configuration."""
    config_clean = deepcopy(config)

    for block in ALL_BLOCKS:
        if block not in config_clean:
            continue
        config_clean[block].pop("normalization_engine", None)
        for term_list_key in (
            "positives",
            "proximity_positives",
            "anti_exclude",
            "anti_flag",
        ):
            term_list = config_clean[block].get(term_list_key)
            if isinstance(term_list, list):
                for term in term_list:
                    if isinstance(term, dict):
                        term.pop("pattern", None)

    return config_clean


def compute_config_hash(config: dict) -> str:
    """Generate a SHA-256 hash (truncated to 16 hex chars) of the configuration."""
    config_clean = _sanitize_config_for_serialization(config)
    config_str = json.dumps(config_clean, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(config_str.encode("utf-8")).hexdigest()[:16]


def compute_file_hash(file_path: str) -> str:
    """Compute a SHA-256 hash (truncated to 16 hex chars) of a file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()[:16]


# ── CSV loading ──────────────────────────────────────────────────────────────


def load_csv_safe(path: Path) -> pd.DataFrame:
    """Load a CSV file with automatic encoding and separator detection."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, "rb") as f:
        raw_data = f.read(10000)
        if chardet is None:
            encoding = "utf-8"
        else:
            encoding = chardet.detect(raw_data).get("encoding", "utf-8")

    for sep in (";", ",", "\t"):
        try:
            df = pd.read_csv(
                path, encoding=encoding, sep=sep, dtype=str, keep_default_na=False
            )
            if not df.empty and len(df.columns) >= 3:
                return df
        except Exception:
            continue

    raise ValueError(f"Unable to load CSV: {path}")


# ── export helpers ───────────────────────────────────────────────────────────


def get_export_opts(cfg: dict) -> dict:
    """Extract export options from the configuration dict."""
    root = cfg or {}
    out = root.get("output") or {}
    return {
        "export_csv": bool(out.get("csv", True)),
        "export_xlsx": bool(out.get("xlsx", False)),
        "csv_sep": out.get("csv_sep", root.get("sep", ";")),
        "csv_decimal": out.get("csv_decimal", root.get("decimal", ",")),
        "csv_float_fmt": out.get("csv_float_format", "%.2f"),
        "xlsx_engine": out.get("xlsx_engine", "openpyxl"),
        "xlsx_sheet": out.get("xlsx_sheet_name", "resultados"),
        "encoding": root.get("encoding", "utf-8-sig"),
    }


def export_results(df: pd.DataFrame, output_path: Path, cfg: dict) -> None:
    """Export the result DataFrame to CSV and/or XLSX."""
    opts = get_export_opts(cfg)

    if opts["export_csv"]:
        df.to_csv(
            output_path,
            index=False,
            encoding=opts["encoding"],
            sep=opts["csv_sep"],
            float_format=opts["csv_float_fmt"],
            decimal=opts["csv_decimal"],
        )

    if opts["export_xlsx"]:
        xlsx_path = output_path.with_suffix(".xlsx")
        df.to_excel(
            xlsx_path,
            index=False,
            engine=opts["xlsx_engine"],
            sheet_name=opts["xlsx_sheet"],
        )


# ── highlighting ─────────────────────────────────────────────────────────────


def highlight_text(original_text: str, all_terms: list[dict], section_name: str) -> str:
    """Mark matched terms in the original text with ***TERM*** markers."""
    if not original_text or not all_terms:
        return original_text

    spans = []

    for term in all_terms:
        if term.get("scope", "any") not in ("any", section_name):
            continue

        pattern = term.get("pattern")
        if not pattern:
            continue

        try:
            for match in pattern.finditer(original_text):
                spans.append(match.span())
        except re.error:
            continue

    if not spans:
        return original_text

    spans = sorted(set(spans))
    merged: list[tuple[int, int]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    result = original_text
    for start, end in reversed(merged):
        result = f"{result[:start]}***{result[start:end].upper()}***{result[end:]}"

    return result


def pack_highlights(evaluation: BlockEvaluation) -> str:
    """Serialize all positive matches of a block evaluation to a compact string."""
    items = []
    for sec_name in SECTION_NAMES:
        for m in evaluation.matches.get(sec_name, []):
            comp_str = f" comps={'+'.join(m.components)}" if m.components else ""
            items.append(
                f'term="{m.term}" sec={sec_name} L={m.level} '
                f"row={m.source_row} type={m.match_type}{comp_str}"
            )
    return " | ".join(items)


def pack_anti_hits(hits: list[AntiHit]) -> str:
    """Serialize anti-term hits to a compact string."""
    return "|".join(
        f"{h.term}:{h.section}:{h.source_row}" for h in hits if h.term and h.section
    )


# ── reports ──────────────────────────────────────────────────────────────────


def generate_report(
    df: pd.DataFrame, stats: dict, config: dict, output_path: Path
) -> None:
    """Write a human-readable triage report to a text file."""
    total = len(df)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("=== TRIAGE REPORT ===\n")
        f.write(f"VERSION: {VERSION}\n")
        f.write(f"DATE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"TOTAL ARTICLES: {total}\n")
        f.write(f"PROCESSING TIME: {stats.get('processing_time', 0):.2f}s\n")
        f.write(f"RATE: {stats.get('articles_per_second', 0):.1f} articles/s\n\n")

        f.write(f"CONFIG HASH: {compute_config_hash(config)}\n\n")

        if "Final_Decision" in df.columns:
            f.write("== FINAL DECISIONS ==\n")
            for decision, count in df["Final_Decision"].value_counts().items():
                f.write(f"{decision}: {count} ({(count / total) * 100:.1f}%)\n")
            f.write("\n")

        f.write("== BLOCK PERFORMANCE ==\n")

        blocks_to_report = ["T0"] if "Status_T0" in df.columns else []
        blocks_to_report.extend(DOMAIN_BLOCKS)

        for block in blocks_to_report:
            f.write(f"\n{block}:\n")
            block_stats = stats.get("block_performance", {}).get(block, {})

            for status, count in block_stats.get("status_distribution", {}).items():
                f.write(f"  {status}: {count} ({(count / total) * 100:.1f}%)\n")

            if block != "T0":
                f.write(f"  Avg score: {block_stats.get('avg_score', 0):.2f}\n")
                f.write(f"  Max score: {block_stats.get('max_score', 0):.2f}\n")


def export_config_audit(config: dict, output_path: Path) -> None:
    """Export sanitized configuration for audit trail."""
    config_clean = _sanitize_config_for_serialization(config)

    config_clean["_metadata"] = {
        "export_timestamp": datetime.now().isoformat(),
        "version": VERSION,
        "config_hash": compute_config_hash(config),
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(config_clean, f, indent=2, ensure_ascii=False)


def export_raw_subset(
    original_df: pd.DataFrame,
    result_df: pd.DataFrame,
    config: dict,
    output_path: Path,
) -> None:
    """Export a subset with approved/flagged articles (original text)."""
    fields = config.get("fields", {})
    col_id_input = fields.get("id", "key")
    col_title_input = fields.get("title", "title")
    col_abs_input = fields.get("abstract", "abstract")
    col_id_output = fields.get("id_output", "ID")

    target_decisions = {"APPROVED_FINAL", "FLAGGED_FINAL"}

    if "Final_Decision" not in result_df.columns:
        return

    subset_results = result_df[
        result_df["Final_Decision"].isin(target_decisions)
    ].copy()

    if subset_results.empty:
        return

    decision_map = dict(
        zip(
            subset_results[col_id_output].astype(str),
            subset_results["Final_Decision"],
            strict=True,
        )
    )
    valid_ids = set(subset_results[col_id_output].astype(str))

    df_export = original_df.copy()
    df_export["_temp_id_str"] = df_export[col_id_input].astype(str)
    df_final = df_export[df_export["_temp_id_str"].isin(valid_ids)].copy()
    df_final["Final_Decision"] = df_final["_temp_id_str"].map(decision_map)

    cols_to_keep = [col_id_input, col_title_input, col_abs_input, "Final_Decision"]
    cols_existing = [c for c in cols_to_keep if c in df_final.columns]
    df_final = df_final[cols_existing]

    subset_path = output_path.with_stem(output_path.stem + "_filtered_raw").with_suffix(
        ".xlsx"
    )

    try:
        opts = get_export_opts(config)
        df_final.to_excel(
            subset_path, index=False, engine=opts.get("xlsx_engine", "openpyxl")
        )
    except Exception:
        logger.warning("Failed to export raw subset to %s", subset_path, exc_info=True)


__all__ = [
    "compute_config_hash",
    "compute_file_hash",
    "load_csv_safe",
    "get_export_opts",
    "export_results",
    "highlight_text",
    "pack_highlights",
    "pack_anti_hits",
    "generate_report",
    "export_config_audit",
    "export_raw_subset",
]
