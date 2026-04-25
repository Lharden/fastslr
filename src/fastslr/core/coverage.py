"""Term coverage analysis and reporting."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


@dataclass
class TermCoverageReport:
    """Results of a term coverage analysis."""

    dead_terms: list[dict] = field(default_factory=list)
    broad_terms: list[dict] = field(default_factory=list)
    block_discrimination: list[dict] = field(default_factory=list)
    section_distribution: dict[str, int] = field(default_factory=dict)
    suggestions: list[str] = field(default_factory=list)
    total_articles: int = 0
    total_terms: int = 0


_HIGHLIGHT_TERM_RE = re.compile(r'term="([^"]+)"\s+sec=(\w+)')


def _extract_term_hits(
    result_df: pd.DataFrame,
    domain_blocks: list[str],
) -> dict[str, dict[str, int]]:
    """Parse highlight columns to count per-term article and section hits."""
    term_hits: dict[str, dict[str, int]] = {}
    article_term_seen: set[tuple[object, str]] = set()

    for block in domain_blocks:
        col = f"Highlights_{block}"
        if col not in result_df.columns:
            continue

        for article_idx, raw in result_df[col].dropna().items():
            for match in _HIGHLIGHT_TERM_RE.finditer(str(raw)):
                term, section = match.group(1), match.group(2)
                if term not in term_hits:
                    term_hits[term] = {
                        "title": 0,
                        "abstract": 0,
                        "manual_tags": 0,
                        "_total": 0,
                        "_articles": 0,
                    }
                term_hits[term][section] = term_hits[term].get(section, 0) + 1
                term_hits[term]["_total"] += 1

                article_key = (article_idx, term)
                if article_key not in article_term_seen:
                    article_term_seen.add(article_key)
                    term_hits[term]["_articles"] += 1

    return term_hits


def analyze_term_coverage(
    result_df: pd.DataFrame,
    config: dict,
    domain_blocks: list[str] | None = None,
) -> TermCoverageReport:
    """Analyze term coverage after a triage run."""
    if domain_blocks is None:
        domain_blocks = list(config.get("_domain_blocks") or [])

    total_articles = len(result_df)
    report = TermCoverageReport(total_articles=total_articles)

    # Collect all configured term strings
    all_configured_terms: set[str] = set()
    for block in domain_blocks:
        block_cfg = config.get(block, {})
        for entry in block_cfg.get("positives", []):
            t = entry.get("original_term") or entry.get("term", "")
            if t:
                all_configured_terms.add(t)

    report.total_terms = len(all_configured_terms)

    # Parse highlights to find actual hits
    term_hits = _extract_term_hits(result_df, domain_blocks)
    matched_terms = set(term_hits.keys())

    # Dead terms (configured but never matched)
    for term in sorted(all_configured_terms - matched_terms):
        report.dead_terms.append({"term": term})
        report.suggestions.append(f"Term '{term}' had 0 matches - check spelling or remove")

    # Broad terms (matched >80% of articles)
    broad_threshold = total_articles * 0.8 if total_articles > 0 else 0
    for term, hits in sorted(term_hits.items(), key=lambda x: -x[1]["_articles"]):
        article_count = hits["_articles"]
        if article_count > broad_threshold:
            pct = article_count / max(total_articles, 1) * 100
            report.broad_terms.append(
                {
                    "term": term,
                    "article_count": article_count,
                    "hit_count": hits["_total"],
                    "pct": pct,
                }
            )
            report.suggestions.append(
                f"Term '{term}' matched {article_count}/{total_articles}"
                f" articles ({pct:.0f}%) - may add noise"
            )

    # Section distribution
    section_totals: dict[str, int] = {"title": 0, "abstract": 0, "manual_tags": 0}
    for hits in term_hits.values():
        for sec in ("title", "abstract", "manual_tags"):
            section_totals[sec] += hits.get(sec, 0)
    report.section_distribution = section_totals

    # Block discrimination
    for block in domain_blocks:
        status_col = f"Status_{block}"
        if status_col not in result_df.columns:
            continue
        value_counts = result_df[status_col].value_counts()
        if len(value_counts) == 1:
            only_status = value_counts.index[0]
            report.block_discrimination.append(
                {
                    "block": block,
                    "status": only_status,
                    "issue": f"All articles have status '{only_status}'",
                }
            )
            report.suggestions.append(
                f"Block '{block}' has no discrimination - all articles are {only_status}"
            )

    return report


def format_coverage_report(report: TermCoverageReport) -> str:
    """Format a TermCoverageReport as a human-readable string."""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("  TERM COVERAGE REPORT")
    lines.append("=" * 60)
    lines.append(f"  Total articles: {report.total_articles}")
    lines.append(f"  Total configured terms: {report.total_terms}")
    lines.append("")

    if report.dead_terms:
        lines.append(f"  DEAD TERMS ({len(report.dead_terms)} with 0 matches):")
        for dt in report.dead_terms[:20]:
            lines.append(f"    - {dt['term']}")
        if len(report.dead_terms) > 20:
            lines.append(f"    ... and {len(report.dead_terms) - 20} more")
        lines.append("")

    if report.broad_terms:
        lines.append(f"  BROAD TERMS ({len(report.broad_terms)} matching >80% of articles):")
        for bt in report.broad_terms[:10]:
            lines.append(
                f"    - {bt['term']} "
                f"({bt['article_count']} articles, {bt['hit_count']} section hits, "
                f"{bt['pct']:.0f}%)"
            )
        lines.append("")

    if report.block_discrimination:
        lines.append("  LOW DISCRIMINATION BLOCKS:")
        for bd in report.block_discrimination:
            lines.append(f"    - {bd['block']}: {bd['issue']}")
        lines.append("")

    lines.append("  SECTION DISTRIBUTION:")
    for sec, count in sorted(report.section_distribution.items()):
        lines.append(f"    {sec}: {count} hits")
    lines.append("")

    if report.suggestions:
        lines.append(f"  SUGGESTIONS ({len(report.suggestions)}):")
        for i, s in enumerate(report.suggestions[:15], 1):
            lines.append(f"    {i}. {s}")
        if len(report.suggestions) > 15:
            lines.append(f"    ... and {len(report.suggestions) - 15} more")

    lines.append("=" * 60)
    return "\n".join(lines)


def export_coverage_csv(report: TermCoverageReport, output_path: Path) -> None:
    """Export term coverage data to CSV."""
    rows: list[dict] = []
    for dt in report.dead_terms:
        rows.append({"term": dt["term"], "status": "dead", "hits": 0, "pct": 0})
    for bt in report.broad_terms:
        rows.append(
            {
                "term": bt["term"],
                "status": "broad",
                "articles": bt["article_count"],
                "section_hits": bt["hit_count"],
                "pct": bt["pct"],
            }
        )

    df = pd.DataFrame(rows)
    if not df.empty:
        df.to_csv(output_path, index=False)


__all__ = [
    "TermCoverageReport",
    "analyze_term_coverage",
    "format_coverage_report",
    "export_coverage_csv",
]
