"""Tests for protocol snapshot and academic compliance outputs."""

from __future__ import annotations

import zipfile
from pathlib import Path

from fastslr.io import (
    PROTOCOL_SCHEMA_ID,
    PROTOCOL_VERSION_CURRENT,
    build_protocol_snapshot,
    export_appendix_pack,
    export_compliance_manifest,
    export_protocol_snapshot,
    generate_academic_report,
    get_export_opts,
    migrate_protocol_snapshot,
    validate_protocol_snapshot,
)


def _sample_config() -> dict:
    return {
        "global": {
            "DECISION_POLICY": "special",
            "ENABLE_SPECIAL_APPROVAL_RULE": True,
            "BLOCK_ORDER": ["CTX", "TECH"],
            "PONTUACAO_NIVEIS": {"1": 10, "2": 8},
            "LIMITES_APROVADO": {"1": 10, "2": None},
            "LIMITES_SINALIZADO": {"1": 6, "2": 8},
            "WEIGHTS": {"title": 2.0, "abstract": 1.0, "manual_tags": 1.5},
            "FAIL_FAST_GLOBAL": True,
            "MAX_GAP_BETWEEN_TERMS": 2,
            "ENABLE_PROXIMITY_DETECTION": True,
        },
        "fields": {
            "id": "key",
            "id_output": "ID",
            "title": "title",
            "abstract": "abstract",
            "manual_tags": "manual_tags",
        },
        "_domain_blocks": ["CTX", "TECH"],
        "_block_labels": {"CTX": "Context", "TECH": "Technology"},
        "CTX": {"positives": [], "anti": {"exclude": [], "flag": []}},
        "TECH": {"positives": [], "anti": {"exclude": [], "flag": []}},
    }


def test_protocol_snapshot_generation_and_exports(tmp_path: Path):
    config = _sample_config()
    stats = {
        "total_articles": 10,
        "processing_time": 2.5,
        "articles_per_second": 4.0,
        "decision_distribution": {
            "APPROVED_FINAL": 3,
            "FLAGGED_FINAL": 2,
            "REJECTED_FINAL": 5,
        },
        "block_performance": {
            "CTX": {"status_distribution": {"APPROVED": 4, "REJECTED": 6}},
            "TECH": {"status_distribution": {"APPROVED": 5, "FLAGGED": 5}},
        },
    }

    snapshot = build_protocol_snapshot(
        config=config,
        stats=stats,
        input_path=Path("data/input.csv"),
        terms_path=Path("data/terms.csv"),
        result_path=Path("output/results.xlsx"),
        input_hash="abcd1234",
        terms_hash="efgh5678",
        config_hash="cfg9012",
    )

    assert snapshot["protocol_version"] == PROTOCOL_VERSION_CURRENT
    assert snapshot["schema_id"] == PROTOCOL_SCHEMA_ID
    assert snapshot["configuration"]["decision_policy"] == "special"
    assert len(snapshot["configuration"]["domain_blocks"]) == 2
    assert validate_protocol_snapshot(snapshot) == []

    protocol_path = tmp_path / "protocol.json"
    academic_path = tmp_path / "academic.md"
    bundle_path = tmp_path / "bundle.json"

    export_protocol_snapshot(snapshot, protocol_path)
    generate_academic_report(snapshot, academic_path)
    export_compliance_manifest(
        {
            "results": Path("output/results.xlsx"),
            "protocol": protocol_path,
            "academic": academic_path,
        },
        bundle_path,
        snapshot["execution_id"],
    )

    assert protocol_path.exists()
    assert academic_path.exists()
    assert bundle_path.exists()

    academic_text = academic_path.read_text(encoding="utf-8")
    assert "Academic Compliance Report" in academic_text
    assert "Decision policy" in academic_text
    assert "Scoring Criteria" in academic_text


def test_validate_protocol_snapshot_fails_for_missing_keys():
    invalid = {"protocol_version": PROTOCOL_VERSION_CURRENT}
    errors = validate_protocol_snapshot(invalid)
    assert errors
    assert any("Missing root key" in err for err in errors)


def test_migrate_protocol_snapshot_from_v20():
    v20_snapshot = {
        "protocol_version": "2.0",
        "execution_id": "run_test",
        "generated_at": "2026-02-19T00:00:00",
        "triage_version": "1.1.0",
        "inputs": {
            "input_file": "a.csv",
            "input_hash": "aa",
            "terms_file": "b.csv",
            "terms_hash": "bb",
            "config_hash": "cc",
        },
        "configuration": {
            "decision_policy": "special",
            "domain_blocks": [{"id": "CTX", "label": "Context"}],
        },
        "processing": {
            "total_articles": 1,
            "processing_time_seconds": 0.1,
            "articles_per_second": 10,
        },
        "artifacts": {"results_path": "out.xlsx"},
        "reproducibility": {"deterministic_engine": True},
    }

    migrated = migrate_protocol_snapshot(v20_snapshot)
    assert migrated["protocol_version"] == PROTOCOL_VERSION_CURRENT
    assert migrated["schema_id"] == PROTOCOL_SCHEMA_ID
    assert isinstance(migrated.get("methodology"), dict)


def test_export_opts_supports_academic_package_flag():
    opts = get_export_opts({"output": {"academic_package": False}})
    assert opts["academic_package"] is False


def test_export_appendix_pack_creates_zip_with_index(tmp_path: Path):
    report = tmp_path / "run_report.txt"
    protocol = tmp_path / "run_protocol.json"
    report.write_text("report", encoding="utf-8")
    protocol.write_text("{}", encoding="utf-8")

    zip_path = tmp_path / "appendix.zip"
    export_appendix_pack(
        {
            "report": report,
            "protocol": protocol,
            "missing": tmp_path / "does_not_exist.txt",
        },
        zip_path,
        "run_abc",
    )

    assert zip_path.exists()
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = set(zf.namelist())
        assert "run_report.txt" in names
        assert "run_protocol.json" in names
        assert "APPENDIX_INDEX.md" in names
        assert "appendix_manifest.json" in names


def test_export_appendix_pack_deduplicates_same_file(tmp_path: Path):
    result_file = tmp_path / "same_result.xlsx"
    result_file.write_text("dummy", encoding="utf-8")

    zip_path = tmp_path / "appendix_dedup.zip"
    export_appendix_pack(
        {
            "results_primary": result_file,
            "results_xlsx": result_file,
        },
        zip_path,
        "run_same",
    )

    assert zip_path.exists()
    with zipfile.ZipFile(zip_path, "r") as zf:
        file_entries = [
            name
            for name in zf.namelist()
            if name not in {"APPENDIX_INDEX.md", "appendix_manifest.json"}
        ]
        assert file_entries.count("same_result.xlsx") == 1


def test_protocol_snapshot_keeps_sampling_metadata():
    snapshot = build_protocol_snapshot(
        config=_sample_config(),
        stats={
            "total_articles": 10,
            "processing_time": 1.0,
            "articles_per_second": 10.0,
            "sample_mode": True,
            "sample_size": 4,
            "population_size": 10,
            "sample_seed": 99,
        },
        input_path=Path("data/input.csv"),
        terms_path=Path("data/terms.csv"),
        result_path=Path("output/results.xlsx"),
        input_hash="h1",
        terms_hash="h2",
        config_hash="h3",
    )

    processing = snapshot["processing"]
    assert processing["sample_mode"] is True
    assert processing["sample_size"] == 4
    assert processing["population_size"] == 10
    assert processing["sample_seed"] == 99
