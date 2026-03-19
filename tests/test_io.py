"""Tests for I/O operations, adapters, export, and protocol snapshot."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from fastslr.core.adapters import detect_format, normalize_import
from fastslr.core.io import (
    compute_config_hash,
    export_results,
    load_csv_safe,
    validate_protocol_snapshot,
)


# ── TestLoadCsvSafe ──────────────────────────────────────────────────────────


class TestLoadCsvSafe:
    """Tests for :func:`load_csv_safe`."""

    def test_loads_valid_csv(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("ID,Title,Abstract\n1,T,A\n", encoding="utf-8")

        df = load_csv_safe(csv_path)

        assert len(df) == 1

    def test_loads_semicolon_separated(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("ID;Title;Abstract\n1;T;A\n", encoding="utf-8")

        df = load_csv_safe(csv_path)

        assert len(df) == 1

    def test_handles_empty_csv(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "empty.csv"
        csv_path.write_text("ID,Title,Abstract\n", encoding="utf-8")

        df = load_csv_safe(csv_path)

        assert len(df) == 0
        assert len(df.columns) >= 3

    def test_detects_encoding(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "bom.csv"
        # Write UTF-8 BOM file
        content = "\ufeffID,Title,Abstract\n1,Titulo,Resumo\n"
        csv_path.write_bytes(content.encode("utf-8-sig"))

        df = load_csv_safe(csv_path)

        assert len(df) == 1


# ── TestDetectFormat ─────────────────────────────────────────────────────────


class TestDetectFormat:
    """Tests for :func:`detect_format`."""

    def test_detects_scopus(self) -> None:
        df = pd.DataFrame(
            columns=["EID", "Title", "Abstract", "Author Keywords", "Source title"]
        )

        assert detect_format(df) == "scopus"

    def test_detects_wos(self) -> None:
        df = pd.DataFrame(columns=["UT", "TI", "AB", "DE", "SO"])

        assert detect_format(df) == "wos"

    def test_detects_zotero(self) -> None:
        df = pd.DataFrame(columns=["Key", "Title", "Abstract Note", "Manual Tags"])

        assert detect_format(df) == "zotero"

    def test_returns_none_for_unknown(self) -> None:
        df = pd.DataFrame(columns=["Col1", "Col2", "Col3"])

        assert detect_format(df) is None


# ── TestNormalizeImport ──────────────────────────────────────────────────────


class TestNormalizeImport:
    """Tests for :func:`normalize_import`."""

    def test_normalizes_zotero(self) -> None:
        df = pd.DataFrame(
            {
                "Key": ["Z001"],
                "Title": ["Test Title"],
                "Abstract Note": ["Test abstract"],
                "Manual Tags": ["tag1"],
                "Item Type": ["journalArticle"],
            }
        )

        result = normalize_import(df)

        assert "abstract" in result.columns

    def test_normalizes_scopus(self) -> None:
        df = pd.DataFrame(
            {
                "EID": ["S001"],
                "Title": ["Scopus Title"],
                "Abstract": ["Scopus abstract"],
                "Author Keywords": ["kw1"],
                "Source title": ["Journal X"],
                "Cited by": ["5"],
            }
        )

        result = normalize_import(df)

        assert len(result) == 1


# ── TestComputeConfigHash ────────────────────────────────────────────────────


class TestComputeConfigHash:
    """Tests for :func:`compute_config_hash`."""

    def test_deterministic(self) -> None:
        config = {"global": {"DECISION_POLICY": "special"}}

        h1 = compute_config_hash(config)
        h2 = compute_config_hash(config)

        assert h1 == h2

    def test_different_configs(self) -> None:
        config_a = {"global": {"DECISION_POLICY": "special"}}
        config_b = {"global": {"DECISION_POLICY": "strict"}}

        assert compute_config_hash(config_a) != compute_config_hash(config_b)


# ── TestProtocolSnapshot ─────────────────────────────────────────────────────


class TestProtocolSnapshot:
    """Tests for :func:`validate_protocol_snapshot`."""

    def test_validates_valid_snapshot(self) -> None:
        snapshot = {
            "protocol_version": "2.1",
            "schema_id": "rsl-triage-protocol-v2.1",
            "execution_id": "run_abc123",
            "generated_at": "2025-01-01T00:00:00",
            "triage_version": "3.0.0",
            "inputs": {
                "input_file": "articles.csv",
                "input_hash": "abc123",
                "terms_file": "terms.csv",
                "terms_hash": "def456",
                "config_hash": "ghi789",
            },
            "configuration": {},
            "processing": {"total_articles": 100},
            "artifacts": {"results_path": "results.csv"},
            "reproducibility": {"deterministic_engine": True},
        }

        issues = validate_protocol_snapshot(snapshot)

        assert len(issues) == 0


# ── TestExportResults ────────────────────────────────────────────────────────


class TestExportResults:
    """Tests for :func:`export_results`."""

    def test_export_creates_xlsx(self, tmp_path: Path) -> None:
        df = pd.DataFrame(
            {
                "ID": ["A001"],
                "Final_Decision": ["APPROVED_FINAL"],
            }
        )
        output_path = tmp_path / "results.csv"
        cfg = {
            "output": {"csv": False, "xlsx": True, "xlsx_engine": "openpyxl"},
        }

        export_results(df, output_path, cfg)

        xlsx_path = output_path.with_suffix(".xlsx")
        assert xlsx_path.exists()

    def test_export_creates_csv(self, tmp_path: Path) -> None:
        df = pd.DataFrame(
            {
                "ID": ["A001"],
                "Final_Decision": ["APPROVED_FINAL"],
            }
        )
        output_path = tmp_path / "results.csv"
        cfg = {
            "output": {"csv": True, "xlsx": False},
        }

        export_results(df, output_path, cfg)

        assert output_path.exists()
