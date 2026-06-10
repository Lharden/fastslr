"""Regression tests for the approved final-audit G2 fixes."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd
import pytest

from fastslr.app.controller import (
    analyze_coverage,
    inspect_run_setup,
    preview_triage,
    run_triage,
    validate_config,
)
from fastslr.core import engine as engine_module
from fastslr.core import io as io_module
from fastslr.core.coverage import TermCoverageReport, analyze_term_coverage, export_coverage_csv
from fastslr.core.engine import process_articles
from fastslr.core.io import load_table_safe


def _inline_config(**global_overrides: object) -> dict:
    global_config = {
        "BLOCK_ORDER": ["TECH"],
        "PONTUACAO_NIVEIS": {"1": 10},
        "LIMITES_APROVADO": {"1": 10},
        "LIMITES_SINALIZADO": {"1": 6},
        "DECISION_POLICY": "special",
        "ERROR_POLICY": "flag",
        "MAX_ERROR_RATE": 1.0,
        **global_overrides,
    }
    return {
        "global": global_config,
        "fields": {
            "id": "key",
            "id_output": "ID",
            "title": "title",
            "abstract": "abstract",
        },
        "output": {"csv": True, "xlsx": False, "academic_package": False},
        "TECH": {
            "positives": [{"term": "AI", "level": 1, "scope": "any", "regex": False}],
            "anti": {"exclude": [], "flag": []},
        },
    }


def _write_config(tmp_path: Path, config: dict) -> Path:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return config_path


def _write_articles(
    tmp_path: Path,
    *,
    columns: dict[str, list[str]] | None = None,
    encoding: str = "utf-8",
) -> Path:
    input_path = tmp_path / "articles.csv"
    frame = pd.DataFrame(
        columns
        or {
            "key": ["A1"],
            "title": ["AI systems"],
            "abstract": ["Relevant abstract"],
        }
    )
    input_path.write_bytes(frame.to_csv(index=False).encode(encoding))
    return input_path


@pytest.mark.parametrize("operation", [run_triage, preview_triage, analyze_coverage])
def test_execution_flows_reject_invalid_prepared_config(
    tmp_path: Path,
    operation,
) -> None:
    config_path = _write_config(tmp_path, _inline_config(DECISION_POLICY="invalid"))
    input_path = _write_articles(tmp_path)
    output_dir = tmp_path / "out"

    kwargs = {"output_dir": output_dir} if operation is run_triage else {}
    with pytest.raises(ValueError, match="decision policy"):
        operation(input_path, config_path, **kwargs)

    assert not output_dir.exists()


def test_documentary_validation_accepts_template_but_execution_rejects_unresolved_blocks(
    tmp_path: Path,
) -> None:
    template = {"global": {"BLOCK_ORDER": ["TECH"]}}
    config_path = _write_config(tmp_path, template)
    input_path = _write_articles(tmp_path)

    assert not [
        issue
        for issue in validate_config(template, require_resolved_blocks=False)
        if issue.level == "error"
    ]
    with pytest.raises(ValueError, match="domain blocks"):
        preview_triage(input_path, config_path)


@pytest.mark.parametrize("operation", [run_triage, preview_triage, analyze_coverage])
def test_execution_flows_reject_unresolved_required_columns(
    tmp_path: Path,
    operation,
) -> None:
    config_path = _write_config(tmp_path, _inline_config())
    input_path = _write_articles(
        tmp_path,
        columns={"unknown_id": ["A1"], "unknown_title": ["AI"], "unknown_text": ["Relevant"]},
    )
    output_dir = tmp_path / "out"

    kwargs = {"output_dir": output_dir} if operation is run_triage else {}
    with pytest.raises(ValueError, match="id.*title.*abstract"):
        operation(input_path, config_path, **kwargs)

    assert not output_dir.exists()


def test_configured_alias_matching_is_case_and_accent_insensitive(tmp_path: Path) -> None:
    config = _inline_config()
    config["fields"] = {"id": "KEY", "title": "TITLE", "abstract": "resumo"}
    config_path = _write_config(tmp_path, config)
    input_path = _write_articles(
        tmp_path,
        columns={"Key": ["A1"], "Title": ["AI systems"], "Resumo": ["Relevant abstract"]},
    )

    result = preview_triage(input_path, config_path)

    assert result.result_df.loc[0, "ID"] == "A1"


def test_utf16_bom_is_detected_without_chardet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(io_module, "chardet", None)
    input_path = _write_articles(tmp_path, encoding="utf-16")

    loaded = load_table_safe(input_path)

    assert list(loaded.columns) == ["key", "title", "abstract"]
    assert loaded.loc[0, "key"] == "A1"


def test_utf16_without_bom_is_detected_from_nuls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(io_module, "chardet", None)
    input_path = _write_articles(tmp_path, encoding="utf-16-le")

    loaded = load_table_safe(input_path)

    assert list(loaded.columns) == ["key", "title", "abstract"]
    assert loaded.loc[0, "key"] == "A1"


def test_run_respects_configured_input_encoding(tmp_path: Path) -> None:
    config = _inline_config()
    config["encoding"] = "utf-16-le"
    config_path = _write_config(tmp_path, config)
    input_path = _write_articles(tmp_path, encoding="utf-16-le")

    result = run_triage(input_path, config_path, output_dir=tmp_path / "out")

    assert result.result_df.loc[0, "ID"] == "A1"


def test_duplicate_ids_are_surfaceable_in_inspection_and_run(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, _inline_config())
    input_path = _write_articles(
        tmp_path,
        columns={
            "key": ["A1", "A1"],
            "title": ["AI systems", "AI planning"],
            "abstract": ["Relevant", "Relevant"],
        },
    )

    inspection = inspect_run_setup(input_path=input_path, config_path=config_path)
    result = run_triage(input_path, config_path, output_dir=tmp_path / "out")

    assert any(
        "duplicate" in warning.lower() and "A1" in warning for warning in inspection.warnings
    )
    assert any(
        "duplicate" in warning.lower() and "A1" in warning
        for warning in result.config["_parse_warnings"]
    )


def test_inline_config_coverage_uses_canonical_domain_blocks() -> None:
    config = _inline_config()
    result_df = pd.DataFrame({"Highlights_TECH": [""]})

    report = analyze_term_coverage(result_df, config)

    assert report.total_terms == 1
    assert report.dead_terms == [{"term": "AI"}]


def test_empty_coverage_export_creates_csv_with_headers(tmp_path: Path) -> None:
    output_path = tmp_path / "coverage.csv"

    export_coverage_csv(TermCoverageReport(), output_path)

    assert output_path.exists()
    assert list(pd.read_csv(output_path).columns) == [
        "term",
        "status",
        "articles",
        "section_hits",
        "hits",
        "pct",
    ]


def test_loader_preserves_oserror_for_unreadable_path(tmp_path: Path) -> None:
    directory_named_csv = tmp_path / "directory.csv"
    directory_named_csv.mkdir()

    with pytest.raises(OSError):
        load_table_safe(directory_named_csv)


def test_error_row_preserves_article_id_and_logs_warning_with_traceback(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    config = _inline_config()
    df = pd.DataFrame({"key": ["REAL-ID"], "title": ["AI"], "abstract": ["Relevant"]})

    def _boom(*args, **kwargs):
        raise RuntimeError("evaluation exploded")

    monkeypatch.setattr(engine_module, "evaluate_block", _boom)

    with caplog.at_level(logging.WARNING, logger="fastslr.core.engine"):
        result_df, stats = process_articles(df, config)

    assert result_df.loc[0, "ID"] == "REAL-ID"
    assert stats["error_count"] == 1
    record = next(record for record in caplog.records if "REAL-ID" in record.message)
    assert record.levelno == logging.WARNING
    assert record.exc_info is not None
