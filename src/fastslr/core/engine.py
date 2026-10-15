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
    # 'UT' precedes 'ID': in a Web of Science export 'UT' is the accession
    # number and 'ID' is Keywords Plus, not a record identifier.
    "key": ["Key", "key", "EID", "UT", "Record ID", "Article ID", "ID", "id"],
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


def _is_missing_scalar(value: object) -> bool:
    """Return whether a scalar cell value is missing (NaN/None).

    ``pd.isna`` is typed as possibly returning an array (for array-like inputs),
    which makes it an invalid conditional operand under static typing. The cell
    values here come from ``Series.get`` and are scalars, so the result is a
    plain bool; we coerce defensively for the array-like edge case.
    """
    result = pd.isna(value)
    if isinstance(result, bool):
        return result
    # Array-like input (not expected for scalar cells): treat as missing only if
    # every element is missing.
    return bool(getattr(result, "all", lambda: result)())


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


_MAX_LISTED_IDS = 10


def find_record_id_problems(df: pd.DataFrame, id_col: str) -> list[str]:
    """Return one message per record-ID problem in *df* (empty when IDs are valid).

    Every record must carry a non-blank, unique ID: the result table is keyed
    on it, and a blank or repeated ID makes the decision of one record
    indistinguishable from another's. Records are numbered from 1 in input
    order, header excluded. They are not file lines: a quoted abstract with
    line breaks, common in Scopus and WoS exports, spans several lines.
    """
    if id_col not in df.columns:
        columns = ", ".join(str(c) for c in df.columns)
        return [
            f"Record ID column '{id_col}' not found in the input (columns: {columns}). "
            "Set fields.id in config.json."
        ]

    ids: list[str | None] = [
        None if _is_missing_scalar(value) or not str(value).strip() else str(value).strip()
        for value in df[id_col].tolist()
    ]
    problems: list[str] = []

    blank_records = [pos + 1 for pos, value in enumerate(ids) if value is None]
    if blank_records:
        listed = ", ".join(str(n) for n in blank_records[:_MAX_LISTED_IDS])
        more = " ..." if len(blank_records) > _MAX_LISTED_IDS else ""
        problems.append(
            f"{len(blank_records)} record(s) with a blank ID in column '{id_col}' "
            f"(record(s) {listed}{more}, counted from 1 without the header)."
        )

    records_by_id: dict[str, list[int]] = {}
    for pos, value in enumerate(ids):
        if value is not None:
            records_by_id.setdefault(value, []).append(pos + 1)
    duplicates = [(value, numbers) for value, numbers in records_by_id.items() if len(numbers) > 1]
    if duplicates:
        listed = "; ".join(
            f"'{value}' (records {', '.join(str(n) for n in numbers)})"
            for value, numbers in duplicates[:_MAX_LISTED_IDS]
        )
        more = " ..." if len(duplicates) > _MAX_LISTED_IDS else ""
        problems.append(
            f"{len(duplicates)} duplicate record ID(s) in column '{id_col}': {listed}{more}."
        )

    return problems


def missing_keywords_warning(tags_col: str | None, df: pd.DataFrame, uplift: float) -> str | None:
    """Warning for an input without a keywords column, or ``None`` when it has one.

    Without the column every record counts as having no keywords, so the
    no-keywords uplift applies to all of them and the keywords section never
    scores.
    """
    if tags_col and tags_col in df.columns:
        return None
    source = f"column '{tags_col}' not found in the input" if tags_col else "no column configured"
    effect = (
        f"the no-keywords uplift (x{uplift:g}) is applied to every record"
        if uplift > 1.0
        else "the keywords section never scores"
    )
    return (
        f"Keywords column missing (fields.manual_tags: {source}): every record is treated "
        f"as having no keywords, so {effect}."
    )


def collect_statistics(df_result: pd.DataFrame) -> dict:
    """Compute summary statistics from the result DataFrame.

    Error rows (emitted under ``ERROR_POLICY='flag'``) carry only an id, a
    decision and a reason -- they have no ``Status_*``/``FinalScore_*`` columns.
    They are still counted in ``decision_distribution`` (their total matches
    ``n_total``), but per-block status counts and score aggregates skip their
    ``NaN`` cells. To keep every metric on a coherent, explicit denominator the
    stats expose ``n_total`` (all rows), ``n_error`` (rows that were never
    evaluated) and ``n_valid`` (rows with at least one block status), plus a
    per-block ``n_valid``. Score means therefore have a documented denominator
    instead of an implicit, smaller one.
    """
    n_total = len(df_result)
    stats: dict = {
        "total_articles": n_total,
        "n_total": n_total,
        "n_valid": n_total,
        "n_error": 0,
        "processing_time": 0,
        "articles_per_second": 0,
        "decision_distribution": {},
        "block_performance": {},
        "score_distribution": {},
        "level_distribution": {},
    }

    if df_result.empty:
        return stats

    # A row is "valid" (genuinely evaluated) iff it has a non-NaN value in at
    # least one Status_* column. Error rows lack every Status_* column.
    status_cols = [c for c in df_result.columns if c.startswith("Status_")]
    if status_cols:
        # Per-row "any non-NaN status" computed on the numpy mask to avoid the
        # ambiguous DataFrame.any overload (pyright cannot narrow its bool|Series
        # return). A row is valid if at least one Status_* cell is present.
        present = df_result[status_cols].notna().to_numpy()
        n_valid = int(present.any(axis=1).sum())
    else:
        # No Status_* columns at all: nothing was evaluated successfully.
        n_valid = 0
    stats["n_valid"] = n_valid
    stats["n_error"] = n_total - n_valid

    if "Final_Decision" in df_result.columns:
        stats["decision_distribution"] = df_result["Final_Decision"].value_counts().to_dict()

    for col in status_cols:
        block = col.replace("Status_", "")
        score_col = f"FinalScore_{block}" if block != "T0" else None

        block_valid = int(df_result[col].notna().sum())
        stats["block_performance"][block] = {
            "status_distribution": df_result[col].value_counts().to_dict(),
            "n_valid": block_valid,
        }
        if score_col and score_col in df_result.columns:
            scores = df_result[score_col].dropna()
            stats["block_performance"][block].update(
                {
                    "avg_score": scores.mean(),
                    "max_score": scores.max(),
                }
            )

    for col in df_result.columns:
        if col.startswith("FinalScore_"):
            scores = df_result[col].dropna().astype(float)
            stats["score_distribution"][col] = {
                "mean": scores.mean(),
                "std": scores.std(),
                "min": scores.min(),
                "max": scores.max(),
                "n_valid": int(scores.size),
            }

    return stats


def _create_not_evaluated(reason: str = "Fail-fast") -> BlockEvaluation:
    return BlockEvaluation(status="NOT_EVALUATED", reason=reason)


# Fixed (non per-block) output columns generated for every result row.
_FIXED_OUTPUT_COLUMNS: frozenset[str] = frozenset(
    {
        "Title_Highlighted",
        "Abstract_Highlighted",
        "Tags_Highlighted",
        "Final_Decision",
        "Decision_Reason",
        "triage_version",
        "run_timestamp",
        "Status_T0",
        "Reason_T0",
        "Scope_T0",
        "AntiHighlights_T0",
        "Flags_T0",
    }
)

# Per-block column prefixes generated for each domain block.
_BLOCK_OUTPUT_PREFIXES: tuple[str, ...] = (
    "RawScore_",
    "FinalScore_",
    "BestLevel_",
    "Status_",
    "Highlights_",
    "AntiHighlights_",
    "Flags_",
)


def _validate_id_output(id_output: str, domain_blocks: list[str]) -> None:
    """Reject an ``id_output`` name that collides with a generated column.

    The result row is built as ``{id_output: article_id}`` and then updated with
    every generated column. If ``id_output`` equals one of those names, the
    article id would be silently overwritten. We surface a clear error instead.
    """
    generated: set[str] = set(_FIXED_OUTPUT_COLUMNS)
    for block_name in domain_blocks:
        for prefix in _BLOCK_OUTPUT_PREFIXES:
            generated.add(f"{prefix}{block_name}")

    if id_output in generated:
        raise ValueError(
            f"fields.id_output={id_output!r} collides with a generated output "
            "column and would overwrite the article id. Choose a distinct name "
            "(reserved/generated names include Final_Decision, Decision_Reason, "
            "Status_<block>, FinalScore_<block>, *_Highlighted, etc.)."
        )


def process_articles(
    df: pd.DataFrame,
    config: dict,
    on_progress: Callable[[int, int], None] | None = None,
    *,
    evaluate_all_blocks: bool = False,
) -> tuple[pd.DataFrame, dict]:
    """Process the article DataFrame through the full triage pipeline.

    Args:
        df: Input articles DataFrame.
        config: Loaded triage configuration dict.
        on_progress: Optional callback ``(current, total)`` invoked after
            each article is processed.
        evaluate_all_blocks: evaluate every block of every article, ignoring
            fail-fast and the T0 exclusion. Term coverage needs it: a block
            that is skipped has no matches, and its terms would look dead. The
            final decision does not change, because a rejected block and a T0
            rejection decide REJECTED_FINAL before anything else is read.

    Returns ``(result_df, stats)``.
    """
    start_time = time.time()

    global_params = load_global_params(config.get("global", {}))
    fields = config.get("fields", {})
    domain_blocks = get_domain_blocks(config)

    id_output = fields.get("id_output", "ID")
    _validate_id_output(id_output, domain_blocks)

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

    id_problems = find_record_id_problems(df, id_col)
    if id_problems:
        raise ValueError("Invalid record IDs in the input. " + " ".join(id_problems))

    input_warnings: list[str] = []
    keywords_warning = missing_keywords_warning(tags_col, df, global_params.no_tags_uplift)
    if keywords_warning:
        logger.warning(keywords_warning)
        input_warnings.append(keywords_warning)

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
        article_id = f"ERR_{count}"
        try:
            id_value = row.get(id_col)
            title_value = row.get(title_col)
            abstract_value = row.get(abstract_col)
            tags_value = row.get(tags_col) if tags_col else None

            article_id = "NO_ID" if _is_missing_scalar(id_value) else str(id_value)
            title = "" if _is_missing_scalar(title_value) else str(title_value)
            abstract = "" if _is_missing_scalar(abstract_value) else str(abstract_value)

            manual_tags = ""
            if tags_value is not None and not _is_missing_scalar(tags_value):
                if isinstance(tags_value, (list, tuple)):
                    manual_tags = ", ".join(str(x) for x in tags_value if not _is_missing_scalar(x))
                else:
                    manual_tags = str(tags_value)

            norm_engine = (
                config.get(domain_blocks[0], {}).get("normalization_engine")
                if domain_blocks
                else None
            )

            eval_t0 = evaluate_t0_conditional(title, abstract, manual_tags, config, norm_engine)

            t0_prevents_evaluation = (
                eval_t0 and eval_t0.status == "REJECTED" and not evaluate_all_blocks
            )

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

                    if (
                        fail_fast
                        and not evaluate_all_blocks
                        and evaluations[block_name].status == "REJECTED"
                    ):
                        skip_remaining = True
            else:
                for block_name in domain_blocks:
                    evaluations[block_name] = _create_not_evaluated("Global T0 exclusion")

            final_decision, final_reason = make_final_decision(evaluations, eval_t0, global_params)

            # Build output row
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
            logger.warning("Error processing article %s: %s", article_id, exc, exc_info=True)
            # Under "flag" policy, keep the article as FLAGGED
            row_output = {
                id_output: article_id,
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
    stats["input_warnings"] = input_warnings

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


__all__ = [
    "process_articles",
    "collect_statistics",
    "sample_articles",
    "resolve_field_columns",
    "find_record_id_problems",
    "missing_keywords_warning",
]
