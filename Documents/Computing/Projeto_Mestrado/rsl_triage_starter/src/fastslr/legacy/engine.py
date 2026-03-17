"""Core evaluation pipeline.

Processes articles through the multi-block triage system.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime

import pandas as pd

from .cli import ProgressBar
from .config import load_global_params
from .constants import ALL_BLOCKS, DOMAIN_BLOCKS, VERSION
from .io import highlight_text, pack_anti_hits, pack_highlights
from .models import BlockEvaluation
from .scoring import evaluate_block, evaluate_t0_conditional, make_final_decision


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

    if "Final_Decision" in df_result.columns:
        stats["decision_distribution"] = (
            df_result["Final_Decision"].value_counts().to_dict()
        )

    blocks_to_check = list(DOMAIN_BLOCKS)
    if "Status_T0" in df_result.columns:
        blocks_to_check.insert(0, "T0")

    for block in blocks_to_check:
        status_col = f"Status_{block}"
        score_col = f"FinalScore_{block}" if block != "T0" else None

        if status_col in df_result.columns:
            stats["block_performance"][block] = {
                "status_distribution": df_result[status_col].value_counts().to_dict()
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
    df: pd.DataFrame, config: dict, show_progress: bool = True
) -> tuple[pd.DataFrame, dict]:
    """Process the article DataFrame through the full triage pipeline.

    Returns ``(result_df, stats)``.
    """
    start_time = time.time()

    global_params = load_global_params(config.get("global", {}))
    fields = config.get("fields", {})

    id_col = fields.get("id", "key")
    title_col = fields.get("title", "title")
    abstract_col = fields.get("abstract", "abstract")
    tags_col = fields.get("manual_tags")

    fail_fast = global_params.fail_fast_enabled

    # Collect all terms for highlighting
    all_terms = []
    for block_name in ALL_BLOCKS:
        if block_name in config:
            block_config = config[block_name]
            all_terms.extend(block_config.get("positives", []))
            if block_config.get("proximity_positives"):
                all_terms.extend(block_config["proximity_positives"])
            all_terms.extend(block_config.get("anti_exclude", []))
            all_terms.extend(block_config.get("anti_flag", []))

    output_rows = []
    total = len(df)

    progress = ProgressBar(total, prefix="  Triage") if show_progress else None

    # BUG FIX: use enumerate() instead of relying on DataFrame index
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
                    manual_tags = ", ".join(
                        str(x) for x in tags_value if not pd.isna(x)
                    )
                else:
                    manual_tags = str(tags_value)

            norm_engine = config.get("T1A", {}).get("normalization_engine")
            eval_t0 = evaluate_t0_conditional(
                title, abstract, manual_tags, config, norm_engine
            )

            t0_prevents_evaluation = eval_t0 and eval_t0.status == "REJECTED"

            if not t0_prevents_evaluation:
                eval_t1a = evaluate_block(
                    title, abstract, manual_tags, config["T1A"], global_params
                )

                if fail_fast and eval_t1a.status == "REJECTED":
                    eval_t1b = _create_not_evaluated("T1A rejected")
                    eval_t1c = _create_not_evaluated("T1A rejected")
                else:
                    eval_t1b = evaluate_block(
                        title, abstract, manual_tags, config["T1B"], global_params
                    )

                    if fail_fast and eval_t1b.status == "REJECTED":
                        eval_t1c = _create_not_evaluated("T1B rejected")
                    else:
                        eval_t1c = evaluate_block(
                            title, abstract, manual_tags, config["T1C"], global_params
                        )
            else:
                eval_t1a = _create_not_evaluated("Global T0 exclusion")
                eval_t1b = _create_not_evaluated("Global T0 exclusion")
                eval_t1c = _create_not_evaluated("Global T0 exclusion")

            evaluations = {"T1A": eval_t1a, "T1B": eval_t1b, "T1C": eval_t1c}
            final_decision, final_reason = make_final_decision(
                evaluations, eval_t0, global_params
            )

            row_output = {
                config["fields"].get("id_output", "ID"): article_id,
                "Title_Highlighted": highlight_text(title, all_terms, "title"),
                "Abstract_Highlighted": highlight_text(abstract, all_terms, "abstract"),
                "Tags_Highlighted": highlight_text(
                    manual_tags, all_terms, "manual_tags"
                ),
                "RawScore_T1A": round(eval_t1a.raw_score, 2),
                "FinalScore_T1A": round(eval_t1a.final_score, 2),
                "BestLevel_T1A": eval_t1a.best_level,
                "Status_T1A": eval_t1a.status,
                "Highlights_T1A": pack_highlights(eval_t1a),
                "AntiHighlights_T1A": pack_anti_hits(eval_t1a.anti_exclude),
                "Flags_T1A": pack_anti_hits(eval_t1a.anti_flag),
                "RawScore_T1B": round(eval_t1b.raw_score, 2),
                "FinalScore_T1B": round(eval_t1b.final_score, 2),
                "BestLevel_T1B": eval_t1b.best_level,
                "Status_T1B": eval_t1b.status,
                "Highlights_T1B": pack_highlights(eval_t1b),
                "AntiHighlights_T1B": pack_anti_hits(eval_t1b.anti_exclude),
                "Flags_T1B": pack_anti_hits(eval_t1b.anti_flag),
                "RawScore_T1C": round(eval_t1c.raw_score, 2),
                "FinalScore_T1C": round(eval_t1c.final_score, 2),
                "BestLevel_T1C": eval_t1c.best_level,
                "Status_T1C": eval_t1c.status,
                "Highlights_T1C": pack_highlights(eval_t1c),
                "AntiHighlights_T1C": pack_anti_hits(eval_t1c.anti_exclude),
                "Flags_T1C": pack_anti_hits(eval_t1c.anti_flag),
                "Final_Decision": final_decision,
                "Decision_Reason": final_reason,
                "triage_version": VERSION,
                "run_timestamp": datetime.now().isoformat(),
            }

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

            if progress:
                progress.update(count)

        except Exception as exc:
            logging.debug("Error processing article %d: %s", count, exc)
            continue

    if progress:
        progress.finish()

    processing_time = time.time() - start_time
    result_df = pd.DataFrame(output_rows)

    stats = collect_statistics(result_df)
    stats["processing_time"] = processing_time
    stats["articles_per_second"] = (
        len(output_rows) / processing_time if processing_time > 0 else 0
    )

    return result_df, stats


__all__ = ["process_articles", "collect_statistics"]
