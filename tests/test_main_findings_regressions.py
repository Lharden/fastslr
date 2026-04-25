"""Regression tests for the main conceptual review findings."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from fastslr.app.controller import diff_results, inspect_run_setup, run_triage, validate_config
from fastslr.core.config import load_global_params
from fastslr.core.coverage import analyze_term_coverage
from fastslr.core.io import export_results, load_table_safe
from fastslr.core.models import BlockEvaluation
from fastslr.core.normalization import NormalizationEngine
from fastslr.core.patterns import precompile_patterns
from fastslr.core.scoring import evaluate_block, make_final_decision


def test_normalized_abbreviation_term_matches_normalized_article_text() -> None:
    norm = NormalizationEngine(
        {
            "enabled": True,
            "abbreviations": {"AI": "artificial intelligence"},
            "compound_variants": {},
            "symbol_replacements": {},
        }
    )
    gp = load_global_params({})
    block = {
        "positives": [{"term": "AI", "level": 1, "scope": "any", "regex": False}],
        "anti": {"exclude": [], "flag": []},
    }

    compiled = precompile_patterns(block, norm, gp)
    compiled["normalization_engine"] = norm

    evaluation = evaluate_block("AI for well planning", "", "", compiled, gp)

    assert evaluation.status == "APPROVED"
    assert evaluation.matches["title"][0].term == "AI"


def test_k_of_n_rejects_when_any_block_is_rejected_under_fail_fast_policy() -> None:
    gp = load_global_params(
        {
            "DECISION_POLICY": "k_of_n",
            "MIN_APPROVED_BLOCKS": 1,
            "MAX_FLAGGED_BLOCKS_FOR_APPROVAL": 0,
        }
    )
    evaluations = {
        "CTX": BlockEvaluation(status="APPROVED", reason="ok", final_score=50),
        "TECH": BlockEvaluation(status="REJECTED", reason="below threshold", final_score=0),
        "SCM": BlockEvaluation(status="NOT_EVALUATED", reason="Previous block rejected"),
    }

    decision, reason = make_final_decision(evaluations, None, gp)

    assert decision == "REJECTED_FINAL"
    assert "TECH" in reason


def test_no_domain_blocks_is_rejected_by_engine_and_validation() -> None:
    gp = load_global_params({"DECISION_POLICY": "special"})

    decision, reason = make_final_decision({}, None, gp)
    issues = validate_config({"global": {}})

    assert decision == "REJECTED_FINAL"
    assert reason == "No domain blocks configured"
    assert any(issue.level == "error" and "No domain blocks" in issue.message for issue in issues)


def test_load_table_safe_accepts_xlsx_terms(tmp_path: Path) -> None:
    terms_path = tmp_path / "terms.xlsx"
    pd.DataFrame(
        {
            "block": ["TECH"],
            "kind": ["pos"],
            "term": ["AI"],
            "level": ["1"],
            "section_scope": ["any"],
            "is_regex": ["0"],
        }
    ).to_excel(terms_path, index=False, engine="openpyxl")

    loaded = load_table_safe(terms_path)

    assert list(loaded.columns[:3]) == ["block", "kind", "term"]


def test_load_table_safe_prefers_separator_with_known_headers(tmp_path: Path) -> None:
    input_path = tmp_path / "zotero.csv"
    input_path.write_text(
        "Key,Title,Abstract Note\n"
        'A1,"AI in drilling","Uses sensors; optimization; and planning"\n',
        encoding="utf-8",
    )

    loaded = load_table_safe(input_path)

    assert list(loaded.columns) == ["Key", "Title", "Abstract Note"]
    assert loaded.loc[0, "Abstract Note"] == "Uses sensors; optimization; and planning"


def test_run_triage_accepts_xlsx_terms_and_exports_academic_package(tmp_path: Path) -> None:
    input_path = tmp_path / "articles.csv"
    pd.DataFrame(
        {
            "key": ["A1"],
            "title": ["AI for production planning"],
            "abstract": ["A deterministic artificial intelligence workflow."],
            "manual_tags": [""],
        }
    ).to_csv(input_path, index=False)

    config = {
        "global": {
            "BLOCK_ORDER": ["TECH"],
            "PONTUACAO_NIVEIS": {"1": 10},
            "LIMITES_APROVADO": {"1": 10},
            "LIMITES_SINALIZADO": {"1": 6},
            "WEIGHTS": {"title": 2.0, "abstract": 1.0, "manual_tags": 1.5},
            "DECISION_POLICY": "special",
        },
        "fields": {
            "id": "key",
            "id_output": "ID",
            "title": "title",
            "abstract": "abstract",
            "manual_tags": "manual_tags",
        },
        "output": {"csv": False, "xlsx": True, "academic_package": True},
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    terms_path = tmp_path / "terms.xlsx"
    pd.DataFrame(
        {
            "block": ["TECH"],
            "kind": ["pos"],
            "term": ["AI"],
            "level": ["1"],
            "section_scope": ["any"],
            "is_regex": ["0"],
            "normalization_type": ["abbreviation"],
            "normalization_target": ["artificial intelligence"],
        }
    ).to_excel(terms_path, index=False, engine="openpyxl")

    result = run_triage(input_path, config_path, terms_path, output_dir=tmp_path / "out")

    assert result.result_path == tmp_path / "out" / "triage_results.xlsx"
    assert result.academic_package_path == tmp_path / "out" / "academic_package.zip"
    assert result.academic_package_path is not None
    assert result.academic_package_path.exists()
    assert result.result_df.loc[0, "Final_Decision"] == "APPROVED_FINAL"


def test_export_results_uses_csv_extension_when_only_csv_enabled(tmp_path: Path) -> None:
    exported = export_results(
        pd.DataFrame({"ID": ["A1"], "Final_Decision": ["APPROVED_FINAL"]}),
        tmp_path / "triage_results.xlsx",
        {"output": {"csv": True, "xlsx": False}},
    )

    assert exported == {"csv": tmp_path / "triage_results.csv"}
    assert (tmp_path / "triage_results.csv").exists()
    assert not (tmp_path / "triage_results.xlsx").exists()


def test_coverage_broad_terms_count_articles_not_section_hits() -> None:
    result_df = pd.DataFrame(
        {
            "Highlights_TECH": [
                'term="AI" sec=title L=1 row=0 type=exact | '
                'term="AI" sec=abstract L=1 row=0 type=exact | '
                'term="AI" sec=manual_tags L=1 row=0 type=exact',
                "",
            ]
        }
    )
    config = {
        "_domain_blocks": ["TECH"],
        "TECH": {"positives": [{"term": "AI"}]},
    }

    report = analyze_term_coverage(result_df, config)

    assert report.broad_terms == []
    assert report.section_distribution == {"title": 1, "abstract": 1, "manual_tags": 1}


def test_diff_reads_semicolon_csv_export(tmp_path: Path) -> None:
    path_a = tmp_path / "a.csv"
    path_b = tmp_path / "b.csv"
    pd.DataFrame({"ID": ["A1"], "Final_Decision": ["APPROVED_FINAL"]}).to_csv(
        path_a, sep=";", index=False
    )
    pd.DataFrame({"ID": ["A1"], "Final_Decision": ["REJECTED_FINAL"]}).to_csv(
        path_b, sep=";", index=False
    )

    report = diff_results(path_a, path_b)

    assert len(report.changed) == 1
    assert report.changed[0].old_decision == "APPROVED_FINAL"
    assert report.changed[0].new_decision == "REJECTED_FINAL"


def test_inspect_run_setup_reports_detected_columns(tmp_path: Path) -> None:
    input_path = tmp_path / "articles.xlsx"
    pd.DataFrame(
        {
            "Key": ["A1"],
            "Article Title": ["AI systems"],
            "Abstract Note": ["Relevant abstract"],
            "Manual Tags": [""],
        }
    ).to_excel(input_path, index=False, engine="openpyxl")

    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "global": {"BLOCK_ORDER": ["TECH"]},
                "TECH": {
                    "positives": [{"term": "AI", "level": 1, "scope": "any"}],
                    "anti": {"exclude": [], "flag": []},
                },
            }
        ),
        encoding="utf-8",
    )

    inspection = inspect_run_setup(input_path=input_path, config_path=config_path)

    assert inspection.ok
    assert inspection.field_mapping["id"] == "Key"
    assert inspection.field_mapping["title"] == "Article Title"
    assert inspection.field_mapping["abstract"] == "Abstract Note"
    assert inspection.run_command is not None
