"""Core evaluation pipeline.

Processes articles through the multi-block triage system.
"""

from __future__ import annotations

import logging
import re
import time
import unicodedata
from collections.abc import Callable
from datetime import datetime

import pandas as pd

from .config import get_domain_blocks, load_global_params
from .constants import VERSION
from .io import highlight_text, pack_anti_hits, pack_highlights
from .models import BlockEvaluation
from .scoring import evaluate_block, evaluate_t0_conditional, make_final_decision

logger = logging.getLogger(__name__)

_COLUMN_ALIASES: dict[str, list[str]] = {
    "key": ["Key", "key", "ID", "id", "EID", "UT", "Record ID", "Article ID"],
    "title": ["Title", "title", "TI", "Article Title", "Document Title", "Titulo", "Título"],
    "abstract": [
        "Abstract Note",
        "abstract",
        "Abstract",
        "AB",
        "Resumo",
        "Resumen",
        "Description",
    ],
    "manual_tags": [
        "Manual Tags",
        "manual_tags",
        "Tags",
        "Author Keywords",
        "Keywords",
        "DE",
        "Palavras-chave",
        "Palavras chave",
        "Palabras clave",
    ],
}


def _normalize_column_label(label: str) -> str:
    """Normalize a column label for tolerant matching."""
    no_accents = unicodedata.normalize("NFKD", str(label))
    ascii_label = "".join(ch for ch in no_accents if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", ascii_label.lower())


def _auto_map_column(df: pd.DataFrame, col_name: str) -> str:
    """Map a configured column name to an actual DataFrame column.

    Tries exact match first, then case-insensitive, then known aliases.
    """
    if col_name in df.columns:
        return col_name

    col_lower = col_name.lower()
    for actual_col in df.columns:
        if actual_col.lower() == col_lower:
            return actual_col

    normalized_configured = _normalize_column_label(col_name)
    for actual_col in df.columns:
        if _normalize_column_label(actual_col) == normalized_configured:
            return actual_col

    for alias_key, aliases in _COLUMN_ALIASES.items():
        if col_lower == alias_key or col_name in aliases:
            for alias in aliases:
                if alias in df.columns:
                    return alias
                normalized_alias = _normalize_column_label(alias)
                for actual_col in df.columns:
                    if _normalize_column_label(actual_col) == normalized_alias:
                        return actual_col

    return col_name


def resolve_field_columns(df: pd.DataFrame, fields: dict) -> dict[str, str | None]:
    """Resolve configured field names to actual DataFrame columns."""
    resolved: dict[str, str | None] = {}
    configured = {
        "id": fields.get("id", "key"),
        "title": fields.get("title", "title"),
        "abstract": fields.get("abstract", "abstract"),
        "manual_tags": fields.get("manual_tags"),
    }

    for field_name, configured_col in configured.items():
        if not configured_col:
            resolved[field_name] = None
            continue
        actual_col = _auto_map_column(df, str(configured_col))
        resolved[field_name] = actual_col if actual_col in df.columns else None

    return resolved


def collect_statistics(df_result: pd.DataFrame) -> dict:
    """Compute summary statistics from the result DataFrame."""
    stats: dict = {
        "total_articles": len(df_result),
        "processing_time": 0,
        "articles_per_second": 0,
        "decision_distribution": {},
        "block_performance": {},
        "score_distribution": {},
        "level_distribution": {},
    }

    if df_result.empty:
        return stats

    if "Final_Decision" in df_result.columns:
        stats["decision_distribution"] = df_result["Final_Decision"].value_counts().to_dict()

    for col in df_result.columns:
        if col.startswith("Status_"):
            block = col.replace("Status_", "")
            score_col = f"FinalScore_{block}" if block != "T0" else None

            stats["block_performance"][block] = {
                "status_distribution": df_result[col].value_counts().to_dict()
            }
            if score_col and score_col in df_result.columns:
                stats["block_performance"][block].update(
                    {
                        "avg_score": df_result[score_col].mean(),
                        "max_score": df_result[score_col].max(),
                    }
                )

    for col in df_result.columns:
        if col.startswith("FinalScore_"):
            scores = df_result[col].astype(float)
            stats["score_distribution"][col] = {
                "mean": scores.mean(),
                "std": scores.std(),
                "min": scores.min(),
                "max": scores.max(),
            }

    return stats


def _create_not_evaluated(reason: str = "Fail-fast") -> BlockEvaluation:
    return BlockEvaluation(status="NOT_EVALUATED", reason=reason)


def process_articles(
    df: pd.DataFrame,
    config: dict,
    on_progress: Callable[[int, int], None] | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Process the article DataFrame through the full triage pipeline.

    Args:
        df: Input articles DataFrame.
        config: Loaded triage configuration dict.
        on_progress: Optional callback ``(current, total)`` invoked after
            each article is processed.

    Returns ``(result_df, stats)``.
    """
    start_time = time.time()

    global_params = load_global_params(config.get("global", {}))
    fields = config.get("fields", {})
    domain_blocks = get_domain_blocks(config)

    id_col = fields.get("id", "key")
    title_col = fields.get("title", "title")
    abstract_col = fields.get("abstract", "abstract")
    tags_col = fields.get("manual_tags")

    # Auto-map columns if configured names don't exist in DataFrame
    id_col = _auto_map_column(df, id_col)
    title_col = _auto_map_column(df, title_col)
    abstract_col = _auto_map_column(df, abstract_col)
    if tags_col:
        tags_col = _auto_map_column(df, tags_col)

    fail_fast = global_params.fail_fast_enabled
    error_policy = global_params.error_policy

    # Collect all terms for highlighting
    all_terms: list[dict] = []
    all_block_names = list(domain_blocks)
    if "T0" in config:
        all_block_names.append("T0")

    for block_name in all_block_names:
        if block_name in config:
            block_config = config[block_name]
            all_terms.extend(block_config.get("positives", []))
            if block_config.get("proximity_positives"):
                all_terms.extend(block_config["proximity_positives"])
            all_terms.extend(block_config.get("anti_exclude", []))
            all_terms.extend(block_config.get("anti_flag", []))

    output_rows: list[dict] = []
    error_count = 0
    total = len(df)

    for count, (_idx, row) in enumerate(df.iterrows(), start=1):
        try:
            id_value = row.get(id_col)
            title_value = row.get(title_col)
            abstract_value = row.get(abstract_col)
            tags_value = row.get(tags_col) if tags_col else None

            article_id = "NO_ID" if pd.isna(id_value) else str(id_value)
            title = "" if pd.isna(title_value) else str(title_value)
            abstract = "" if pd.isna(abstract_value) else str(abstract_value)

            manual_tags = ""
            if tags_value is not None and not pd.isna(tags_value):
                if isinstance(tags_value, (list, tuple)):
                    manual_tags = ", ".join(str(x) for x in tags_value if not pd.isna(x))
                else:
                    manual_tags = str(tags_value)

            norm_engine = (
                config.get(domain_blocks[0], {}).get("normalization_engine")
                if domain_blocks
                else None
            )

            eval_t0 = evaluate_t0_conditional(title, abstract, manual_tags, config, norm_engine)

            t0_prevents_evaluation = eval_t0 and eval_t0.status == "REJECTED"

            evaluations: dict[str, BlockEvaluation] = {}

            if not t0_prevents_evaluation:
                skip_remaining = False
                for block_name in domain_blocks:
                    if skip_remaining:
                        evaluations[block_name] = _create_not_evaluated("Previous block rejected")
                        continue

                    evaluations[block_name] = evaluate_block(
                        title,
                        abstract,
                        manual_tags,
                        config[block_name],
                        global_params,
                    )

                    if fail_fast and evaluations[block_name].status == "REJECTED":
                        skip_remaining = True
            else:
                for block_name in domain_blocks:
                    evaluations[block_name] = _create_not_evaluated("Global T0 exclusion")

            final_decision, final_reason = make_final_decision(evaluations, eval_t0, global_params)

            # Build output row
            id_output = fields.get("id_output", "ID")
            row_output: dict = {
                id_output: article_id,
                "Title_Highlighted": highlight_text(title, all_terms, "title"),
                "Abstract_Highlighted": highlight_text(abstract, all_terms, "abstract"),
                "Tags_Highlighted": highlight_text(manual_tags, all_terms, "manual_tags"),
            }

            for block_name in domain_blocks:
                ev = evaluations[block_name]
                row_output.update(
                    {
                        f"RawScore_{block_name}": round(ev.raw_score, 2),
                        f"FinalScore_{block_name}": round(ev.final_score, 2),
                        f"BestLevel_{block_name}": ev.best_level,
                        f"Status_{block_name}": ev.status,
                        f"Highlights_{block_name}": pack_highlights(ev),
                        f"AntiHighlights_{block_name}": pack_anti_hits(ev.anti_exclude),
                        f"Flags_{block_name}": pack_anti_hits(ev.anti_flag),
                    }
                )

            row_output.update(
                {
                    "Final_Decision": final_decision,
                    "Decision_Reason": final_reason,
                    "triage_version": VERSION,
                    "run_timestamp": datetime.now().isoformat(),
                }
            )

            if eval_t0 is not None:
                row_output.update(
                    {
                        "Status_T0": eval_t0.status,
                        "Reason_T0": eval_t0.reason,
                        "Scope_T0": eval_t0.scope,
                        "AntiHighlights_T0": pack_anti_hits(eval_t0.anti_exclude),
                        "Flags_T0": pack_anti_hits(eval_t0.anti_flag),
                    }
                )

            output_rows.append(row_output)

        except Exception as exc:
            error_count += 1
            if error_policy == "fail":
                raise
            logger.debug("Error processing article %d: %s", count, exc)
            # Under "flag" policy, keep the article as FLAGGED
            id_output = fields.get("id_output", "ID")
            row_output = {
                id_output: f"ERR_{count}",
                "Final_Decision": "FLAGGED_FINAL",
                "Decision_Reason": f"Processing error: {exc}",
                "triage_version": VERSION,
                "run_timestamp": datetime.now().isoformat(),
            }
            output_rows.append(row_output)

        if on_progress is not None:
            on_progress(count, total)

    processing_time = time.time() - start_time
    result_df = pd.DataFrame(output_rows)

    stats = collect_statistics(result_df)
    stats["processing_time"] = processing_time
    stats["articles_per_second"] = len(output_rows) / processing_time if processing_time > 0 else 0
    stats["error_count"] = error_count
    stats["error_rate"] = error_count / total if total > 0 else 0

    if (
        error_policy == "flag"
        and total > 0
        and global_params.max_error_rate >= 0
        and stats["error_rate"] > global_params.max_error_rate
    ):
        raise RuntimeError(
            "Processing error rate exceeded MAX_ERROR_RATE: "
            f"{stats['error_rate']:.1%} > {global_params.max_error_rate:.1%} "
            f"({error_count}/{total} article(s))"
        )

    return result_df, stats


def sample_articles(df: pd.DataFrame, n: int, seed: int | None = None) -> pd.DataFrame:
    """Return a random sample of *n* articles from *df*.

    If *n* >= len(df) the full DataFrame is returned (copied).
    """
    if n >= len(df):
        return df.copy()
    return df.sample(n=n, random_state=seed).reset_index(drop=True)


__all__ = ["process_articles", "collect_statistics", "sample_articles", "resolve_field_columns"]
