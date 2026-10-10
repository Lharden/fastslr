"""Pre-freeze audit of FastSLR v3.0.0: input and audit-trail defects F07-F09.

A Web of Science export read its record id from Keywords Plus (F07), blank or
duplicate ids passed silently (F08), and a missing keywords column applied the
no-keywords uplift to every record without a word (F09).
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from fastslr.app.cli import app
from fastslr.app.controller import inspect_run_setup, run_triage
from fastslr.core.engine import process_articles, resolve_field_columns

from .freeze_audit_support import (
    TERMS_FINAL,
    write_config,
)

runner = CliRunner()


# ── F07: Web of Science 'ID' is Keywords Plus, not the record id ─────────────


class TestF07WebOfScienceId:
    def _wos(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "TI": ["Machine learning for oil and gas procurement"],
                "AB": ["We study supply chain procurement in oil and gas."],
                "DE": ["machine learning; procurement"],
                "ID": ["KEYWORDS PLUS; SUPPLY"],
                "UT": ["WOS:000123456700001"],
            }
        )

    def test_id_field_resolves_to_ut(self):
        mapping = resolve_field_columns(
            self._wos(), {"id": "key", "title": "title", "abstract": "abstract"}
        )
        assert mapping["id"] == "UT"

    def test_result_id_is_the_ut_accession_number(self, hist_config):
        result, _ = process_articles(self._wos(), hist_config)
        assert list(result["ID"]) == ["WOS:000123456700001"]


# ── F08: duplicate or blank record IDs passed silently ───────────────────────


def _articles_csv(path: Path, keys: list[str]) -> Path:
    df = pd.DataFrame(
        {
            "key": keys,
            "title": ["Machine learning for oil and gas procurement"] * len(keys),
            "abstract": ["Supply chain procurement in oil and gas."] * len(keys),
            "manual_tags": ["procurement"] * len(keys),
        }
    )
    df.to_csv(path, sep=";", index=False)
    return path


class TestF08RecordIdsMustBeUniqueAndPresent:
    def test_duplicate_id_raises(self, hist_config):
        df = pd.DataFrame(
            [["A1", "t", "a", "k"], ["A1", "t2", "a2", "k2"]],
            columns=["key", "title", "abstract", "manual_tags"],
        )
        with pytest.raises(ValueError, match="A1"):
            process_articles(df, hist_config)

    @pytest.mark.parametrize("blank", [None, "", "   "])
    def test_blank_id_raises(self, hist_config, blank):
        df = pd.DataFrame(
            [["A1", "t", "a", "k"], [blank, "t2", "a2", "k2"]],
            columns=["key", "title", "abstract", "manual_tags"],
        )
        with pytest.raises(ValueError, match=r"(?i)blank|empty"):
            process_articles(df, hist_config)

    def test_cli_run_exits_non_zero_with_clear_message(self, tmp_path):
        inp = _articles_csv(tmp_path / "in.csv", ["A1", "A1", "B2"])
        result = runner.invoke(
            app,
            [
                "run",
                str(inp),
                "-c",
                str(write_config(tmp_path / "config.json")),
                "-t",
                str(TERMS_FINAL),
                "-o",
                str(tmp_path / "out"),
                "-y",
            ],
        )
        assert result.exit_code != 0
        assert "A1" in result.output
        assert "duplicate" in result.output.lower()
        assert not (tmp_path / "out" / "triage_results.xlsx").exists()

    def test_doctor_reports_duplicates_and_fails(self, tmp_path):
        inp = _articles_csv(tmp_path / "in.csv", ["A1", "A1", ""])
        cfg = write_config(tmp_path / "config.json")
        inspection = inspect_run_setup(inp, cfg, TERMS_FINAL)
        assert not inspection.ok
        assert any("A1" in e for e in inspection.errors)
        assert any("blank" in e.lower() for e in inspection.errors)
        result = runner.invoke(
            app, ["doctor", "-i", str(inp), "-c", str(cfg), "-t", str(TERMS_FINAL)]
        )
        assert result.exit_code != 0


# ── F09: keywords column absent -> uplift applied to every record silently ───


class TestF09MissingKeywordsColumnWarns:
    def _no_kw(self) -> pd.DataFrame:
        return pd.DataFrame(
            [["A1", "Machine learning for oil and gas procurement", "Supply chain."]],
            columns=["key", "title", "abstract"],
        )

    def test_stats_carry_the_warning(self, hist_config):
        _, stats = process_articles(self._no_kw(), hist_config)
        assert any("keyword" in w.lower() for w in stats["input_warnings"])

    def test_no_warning_when_column_present(self, hist_config):
        df = self._no_kw().assign(manual_tags=[""])
        _, stats = process_articles(df, hist_config)
        assert stats["input_warnings"] == []

    def test_audit_outputs_record_the_warning(self, tmp_path):
        inp = tmp_path / "in.csv"
        self._no_kw().to_csv(inp, sep=";", index=False)
        result = run_triage(inp, write_config(tmp_path / "config.json"), TERMS_FINAL)
        protocol = json.loads(result.artifact_paths["protocol"].read_text(encoding="utf-8"))
        assert any("keyword" in w.lower() for w in protocol["processing"]["input_warnings"])
        report = result.artifact_paths["report"].read_text(encoding="utf-8")
        assert "keyword" in report.lower()

    def test_doctor_warns(self, tmp_path):
        inp = tmp_path / "in.csv"
        self._no_kw().to_csv(inp, sep=";", index=False)
        inspection = inspect_run_setup(inp, write_config(tmp_path / "config.json"), TERMS_FINAL)
        assert any("keyword" in w.lower() for w in inspection.warnings)
