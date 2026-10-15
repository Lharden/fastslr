"""Regressions from the 3.1.0 merge review, second batch.

- The published academic package and the protocol carry file names and hashes, never paths.
- Term coverage evaluates every block, so a term skipped by fail-fast is not called dead.
- Record-ID problems are numbered by record, not by file line.
- doctor names a bad global value as a config problem.
- A table that is too narrow says so, instead of blaming the encoding.
- diff refuses repeated IDs instead of pairing every copy with every copy.
- A failing article logs one warning, with its real ID.
"""

from __future__ import annotations

import json
import logging
import re
import zipfile
from pathlib import Path

import pandas as pd
import pytest

import fastslr.core.engine as engine_module
from fastslr.app.controller import (
    _prepare_config,
    analyze_coverage,
    diff_results,
    inspect_run_setup,
    run_triage,
)
from fastslr.core.engine import find_record_id_problems, process_articles
from fastslr.core.io import export_compliance_manifest, load_table_safe

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _config(tmp_path: Path, global_cfg: dict | None = None, blocks: dict | None = None) -> Path:
    blocks = blocks or {"T1A": ["oil"]}
    data: dict = {
        "global": {"BLOCK_ORDER": list(blocks), **(global_cfg or {})},
        "fields": {"id": "key", "title": "title", "abstract": "abstract"},
    }
    for name, terms in blocks.items():
        data[name] = {"positives": [{"term": t, "level": 1} for t in terms]}
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _articles(tmp_path: Path, rows: list[tuple[str, str]], name: str = "articles.csv") -> Path:
    path = tmp_path / name
    pd.DataFrame(
        {
            "key": [k for k, _ in rows],
            "title": [t for _, t in rows],
            "abstract": [t for _, t in rows],
        }
    ).to_csv(path, sep=";", index=False)
    return path


# ── no paths in what is published ────────────────────────────────────────────


def test_published_package_and_protocol_carry_names_and_hashes(tmp_path: Path) -> None:
    input_path = _articles(tmp_path, [("A1", "Oil fields"), ("A2", "Gas fields")])

    result = run_triage(input_path, _config(tmp_path), output_dir=tmp_path / "out")

    protocol = json.loads((tmp_path / "out" / "protocol.json").read_text(encoding="utf-8"))
    assert result.result_path is not None
    assert protocol["inputs"]["input_file"] == "articles.csv"
    assert protocol["artifacts"]["results_path"] == result.result_path.name
    with zipfile.ZipFile(result.artifact_paths["academic_package"]) as zf:
        manifest = json.loads(zf.read("appendix_manifest.json"))
        packed = {name: zf.read(name).decode("utf-8", "replace") for name in zf.namelist()}
    assert manifest["files"] and all(_SHA256.match(v) for v in manifest["files"].values())
    assert not any(str(tmp_path) in text for text in packed.values())


def test_compliance_manifest_paths_are_relative_to_its_folder(tmp_path: Path) -> None:
    inside = tmp_path / "run" / "report.txt"
    inside.parent.mkdir()
    inside.write_text("x", encoding="utf-8")
    outside = tmp_path / "elsewhere" / "terms.csv"

    export_compliance_manifest(
        {"report": inside, "terms": outside}, tmp_path / "run" / "manifest.json", "run_x"
    )

    manifest = json.loads((tmp_path / "run" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["artifacts"] == {"report": "report.txt", "terms": "terms.csv"}


# ── coverage sees every block ────────────────────────────────────────────────


def test_coverage_does_not_call_a_term_dead_because_fail_fast_skipped_its_block(
    tmp_path: Path,
) -> None:
    config_path = _config(tmp_path, blocks={"T1A": ["oil"], "T1B": ["ledger"]})
    # 'ledger' only appears where T1A rejects, so fail-fast never evaluates T1B there.
    input_path = _articles(tmp_path, [("A1", "Ledger systems"), ("A2", "Oil fields")])

    report = analyze_coverage(input_path, config_path)

    assert "ledger" not in {d["term"] for d in report.dead_terms}


def test_evaluating_every_block_does_not_change_any_decision(tmp_path: Path) -> None:
    config = _prepare_config(_config(tmp_path, blocks={"T1A": ["oil"], "T1B": ["ledger"]}), None)
    df = pd.DataFrame(
        {
            "key": ["A1", "A2", "A3"],
            "title": ["Ledger systems", "Oil fields", "Oil ledger"],
            "abstract": ["Ledger", "Oil", "Oil and ledger"],
        }
    )

    normal, _ = process_articles(df, config)
    every, _ = process_articles(df, config, evaluate_all_blocks=True)

    assert list(normal["Final_Decision"]) == list(every["Final_Decision"])
    assert "NOT_EVALUATED" in set(normal["Status_T1B"])
    assert "NOT_EVALUATED" not in set(every["Status_T1B"])


# ── messages that point to the right place ───────────────────────────────────


def test_record_id_problems_are_numbered_by_record() -> None:
    df = pd.DataFrame({"key": ["A1", "B2", "A1", ""]})

    problems = " ".join(find_record_id_problems(df, "key"))

    assert "'A1' (records 1, 3)" in problems
    assert "record(s) 4" in problems
    assert "line" not in problems


def test_doctor_names_a_bad_global_value_as_a_config_problem(tmp_path: Path) -> None:
    config_path = _config(tmp_path, global_cfg={"NO_TAGS_UPLIFT": "high"})
    input_path = _articles(tmp_path, [("A1", "Oil fields")])

    inspection = inspect_run_setup(input_path=input_path, config_path=config_path)

    # The config is loaded through load_global_params first, so a bad global value
    # is named there and the input section never sees it (review finding #12 refuted).
    assert any("Could not load config/terms" in e for e in inspection.errors)
    assert not any("Could not load input table" in e for e in inspection.errors)
    assert inspection.input_rows == 1


def test_narrow_table_says_it_lacks_columns(tmp_path: Path) -> None:
    path = tmp_path / "two.csv"
    path.write_text("title;abstract\nOil;Gas\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"at most 2 column\(s\).*at least 3"):
        load_table_safe(path)


def test_diff_refuses_repeated_ids(tmp_path: Path) -> None:
    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    pd.DataFrame({"ID": ["A1", "A1"], "Final_Decision": ["APPROVED_FINAL"] * 2}).to_csv(
        a, sep=";", index=False
    )
    pd.DataFrame({"ID": ["A1"], "Final_Decision": ["REJECTED_FINAL"]}).to_csv(
        b, sep=";", index=False
    )

    with pytest.raises(ValueError, match="repeated IDs.*A1"):
        diff_results(a, b)


def test_failing_article_logs_one_warning_with_its_real_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # The traceback stays at WARNING: a decision of the pre-IP audit (G2), kept.
    config = _prepare_config(_config(tmp_path, global_cfg={"MAX_ERROR_RATE": 1.0}), None)
    real = engine_module.evaluate_block

    def failing(title, *args, **kwargs):
        if "boom" in title.lower():
            raise RuntimeError("boom")
        return real(title, *args, **kwargs)

    monkeypatch.setattr(engine_module, "evaluate_block", failing)
    df = pd.DataFrame({"key": ["A1", "B2"], "title": ["Boom", "Oil"], "abstract": ["x", "Oil"]})

    with caplog.at_level(logging.DEBUG, logger="fastslr.core.engine"):
        result, _ = process_articles(df, config)

    warnings = [
        r
        for r in caplog.records
        if r.levelno == logging.WARNING and "Error processing" in r.getMessage()
    ]
    assert len(warnings) == 1 and "A1" in warnings[0].getMessage()
    assert result.loc[result["ID"] == "A1", "Final_Decision"].item() == "FLAGGED_FINAL"
