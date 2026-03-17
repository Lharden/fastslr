"""Run comparison: diff two triage result sets."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


@dataclass
class ArticleDelta:
    """A single article whose decision changed between runs."""

    article_id: str
    old_decision: str
    new_decision: str
    changed_blocks: list[str] = field(default_factory=list)
    score_deltas: dict[str, float] = field(default_factory=dict)


@dataclass
class RunComparison:
    """Result of comparing two triage runs."""

    total_old: int = 0
    total_new: int = 0
    matched: int = 0
    only_in_old: int = 0
    only_in_new: int = 0
    changed: list[ArticleDelta] = field(default_factory=list)
    unchanged_count: int = 0
    transition_summary: dict[str, int] = field(default_factory=dict)


def compare_runs(
    old_df: pd.DataFrame,
    new_df: pd.DataFrame,
    id_column: str = "ID",
) -> RunComparison:
    """Compare two triage result DataFrames."""
    result = RunComparison(total_old=len(old_df), total_new=len(new_df))

    if id_column not in old_df.columns or id_column not in new_df.columns:
        return result

    old_ids = set(old_df[id_column].astype(str))
    new_ids = set(new_df[id_column].astype(str))

    result.only_in_old = len(old_ids - new_ids)
    result.only_in_new = len(new_ids - old_ids)

    common_ids = old_ids & new_ids
    result.matched = len(common_ids)

    old_indexed = old_df.set_index(old_df[id_column].astype(str))
    new_indexed = new_df.set_index(new_df[id_column].astype(str))

    for aid in sorted(common_ids):
        old_row = old_indexed.loc[aid]
        new_row = new_indexed.loc[aid]

        old_dec = str(old_row.get("Final_Decision", ""))
        new_dec = str(new_row.get("Final_Decision", ""))

        if old_dec == new_dec:
            result.unchanged_count += 1
            continue

        # Find changed blocks
        changed_blocks: list[str] = []
        score_deltas: dict[str, float] = {}

        for col in old_indexed.columns:
            if col.startswith("Status_"):
                block = col.replace("Status_", "")
                old_status = str(old_row.get(col, ""))
                new_status = str(new_row.get(col, ""))
                if old_status != new_status:
                    changed_blocks.append(block)

            if col.startswith("FinalScore_"):
                block = col.replace("FinalScore_", "")
                try:
                    old_score = float(old_row.get(col, 0) or 0)
                    new_score = float(new_row.get(col, 0) or 0)
                    delta = new_score - old_score
                    if abs(delta) > 0.01:
                        score_deltas[block] = round(delta, 2)
                except (ValueError, TypeError):
                    pass

        delta = ArticleDelta(
            article_id=aid,
            old_decision=old_dec,
            new_decision=new_dec,
            changed_blocks=changed_blocks,
            score_deltas=score_deltas,
        )
        result.changed.append(delta)

        transition = f"{old_dec} -> {new_dec}"
        result.transition_summary[transition] = result.transition_summary.get(transition, 0) + 1

    return result


def format_diff_table(comparison: RunComparison, max_rows: int = 50) -> str:
    """Format a RunComparison as an ASCII table."""
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("  RUN COMPARISON")
    lines.append("=" * 70)
    lines.append(f"  Old: {comparison.total_old} articles | New: {comparison.total_new} articles")
    lines.append(f"  Matched: {comparison.matched} | Only old: {comparison.only_in_old} | Only new: {comparison.only_in_new}")
    lines.append(f"  Changed: {len(comparison.changed)} | Unchanged: {comparison.unchanged_count}")
    lines.append("")

    if comparison.transition_summary:
        lines.append("  TRANSITION SUMMARY:")
        for transition, count in sorted(comparison.transition_summary.items()):
            lines.append(f"    {transition}: {count}")
        lines.append("")

    if comparison.changed:
        lines.append(f"  CHANGED ARTICLES (showing up to {max_rows}):")
        lines.append(f"  {'ID':<15} {'Old':<20} {'New':<20} {'Blocks':<15}")
        lines.append("  " + "-" * 66)
        for delta in comparison.changed[:max_rows]:
            blocks_str = ",".join(delta.changed_blocks) if delta.changed_blocks else "-"
            lines.append(
                f"  {delta.article_id:<15} {delta.old_decision:<20} {delta.new_decision:<20} {blocks_str:<15}"
            )
        if len(comparison.changed) > max_rows:
            lines.append(f"  ... and {len(comparison.changed) - max_rows} more")

    lines.append("=" * 70)
    return "\n".join(lines)


def export_diff_csv(comparison: RunComparison, output_path: Path) -> None:
    """Export comparison results to CSV."""
    rows: list[dict] = []
    for d in comparison.changed:
        rows.append({
            "ID": d.article_id,
            "old_decision": d.old_decision,
            "new_decision": d.new_decision,
            "changed_blocks": ";".join(d.changed_blocks),
            "score_deltas": ";".join(f"{k}:{v:+.2f}" for k, v in d.score_deltas.items()),
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df.to_csv(output_path, index=False)


__all__ = [
    "ArticleDelta",
    "RunComparison",
    "compare_runs",
    "format_diff_table",
    "export_diff_csv",
]
