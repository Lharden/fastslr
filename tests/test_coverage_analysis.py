"""Tests for term coverage analysis and reporting."""

from __future__ import annotations

import pandas as pd

from fastslr.core.coverage import (
    analyze_term_coverage,
    format_coverage_report,
)

# ── TestAnalyzeTermCoverage ──────────────────────────────────────────────────


class TestAnalyzeTermCoverage:
    """Tests for :func:`analyze_term_coverage`."""

    def test_detects_dead_terms(self) -> None:
        # Two articles where only "artificial intelligence" is highlighted
        result_df = pd.DataFrame(
            {
                "ID": ["A001", "A002"],
                "Final_Decision": ["APPROVED_FINAL", "APPROVED_FINAL"],
                "Highlights_BLK_A": [
                    'term="artificial intelligence" sec=title L=1 row=0 type=exact',
                    'term="artificial intelligence" sec=abstract L=1 row=0 type=exact',
                ],
            }
        )
        config = {
            "_domain_blocks": ["BLK_A"],
            "BLK_A": {
                "positives": [
                    {"term": "artificial intelligence", "level": 1},
                    {"term": "dead term xyz", "level": 2},
                ],
            },
        }

        report = analyze_term_coverage(result_df, config)

        dead_term_names = [d["term"] for d in report.dead_terms]
        assert "dead term xyz" in dead_term_names

    def test_detects_broad_terms(self) -> None:
        # Create 10 articles where "broad term" appears in all of them
        highlights = [
            'term="broad term" sec=title L=1 row=0 type=exact'
        ] * 10
        result_df = pd.DataFrame(
            {
                "ID": [f"A{i:03d}" for i in range(10)],
                "Final_Decision": ["APPROVED_FINAL"] * 10,
                "Highlights_BLK_A": highlights,
            }
        )
        config = {
            "_domain_blocks": ["BLK_A"],
            "BLK_A": {
                "positives": [
                    {"term": "broad term", "level": 1},
                ],
            },
        }

        report = analyze_term_coverage(result_df, config)

        broad_term_names = [b["term"] for b in report.broad_terms]
        assert "broad term" in broad_term_names

    def test_section_distribution_populated(self) -> None:
        result_df = pd.DataFrame(
            {
                "ID": ["A001"],
                "Final_Decision": ["APPROVED_FINAL"],
                "Highlights_BLK_A": [
                    'term="test term" sec=title L=1 row=0 type=exact',
                ],
            }
        )
        config = {
            "_domain_blocks": ["BLK_A"],
            "BLK_A": {
                "positives": [{"term": "test term", "level": 1}],
            },
        }

        report = analyze_term_coverage(result_df, config)

        assert report.section_distribution is not None
        assert len(report.section_distribution) > 0

    def test_report_has_required_fields(self) -> None:
        result_df = pd.DataFrame(
            {
                "ID": ["A001"],
                "Final_Decision": ["APPROVED_FINAL"],
                "Highlights_BLK_A": [
                    'term="test" sec=title L=1 row=0 type=exact',
                ],
            }
        )
        config = {
            "_domain_blocks": ["BLK_A"],
            "BLK_A": {
                "positives": [{"term": "test", "level": 1}],
            },
        }

        report = analyze_term_coverage(result_df, config)

        assert hasattr(report, "dead_terms")
        assert hasattr(report, "broad_terms")
        assert hasattr(report, "total_articles")


# ── TestFormatCoverageReport ─────────────────────────────────────────────────


class TestFormatCoverageReport:
    """Tests for :func:`format_coverage_report`."""

    def test_produces_string_output(self) -> None:
        result_df = pd.DataFrame(
            {
                "ID": ["A001"],
                "Final_Decision": ["APPROVED_FINAL"],
                "Highlights_BLK_A": [
                    'term="test" sec=title L=1 row=0 type=exact',
                ],
            }
        )
        config = {
            "_domain_blocks": ["BLK_A"],
            "BLK_A": {
                "positives": [{"term": "test", "level": 1}],
            },
        }

        report = analyze_term_coverage(result_df, config)
        result = format_coverage_report(report)

        assert isinstance(result, str)
        assert len(result) > 0
