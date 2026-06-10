"""Regression tests for the execution-quality audit fixes (G4).

Findings from the post-implementation review of commit a6499dc:

- C1: controller raised user-facing errors hardcoded in Portuguese even
  though the G3 fix created the locale keys (``error_empty_corpus``,
  ``error_no_common_id``, ``error_invalid_result``) in all three locales.
- I2: the ReDoS detector missed interval quantifiers nested inside repeated
  groups -- ``(a{2,})+`` and ``(a{2,4})+`` are exponentially ambiguous but
  were accepted, while ``(a{2})+`` (exact count) is safe.
- I3: the empty-corpus guard protected ``run_triage`` only; ``preview_triage``
  and ``analyze_coverage`` silently processed a 0-row corpus.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from fastslr.app.controller import (
    analyze_coverage,
    create_project,
    diff_results,
    export_academic_package,
    preview_triage,
    run_triage,
)
from fastslr.core.patterns import compile_pattern
from fastslr.i18n import set_locale


def _inline_config() -> dict:
    return {
        "global": {
            "BLOCK_ORDER": ["TECH"],
            "PONTUACAO_NIVEIS": {"1": 10},
            "LIMITES_APROVADO": {"1": 10},
            "LIMITES_SINALIZADO": {"1": 6},
            "DECISION_POLICY": "special",
            "ERROR_POLICY": "flag",
            "MAX_ERROR_RATE": 1.0,
        },
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


def _write_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(_inline_config()), encoding="utf-8")
    return config_path


def _write_empty_corpus(tmp_path: Path) -> Path:
    input_path = tmp_path / "articles.csv"
    frame = pd.DataFrame({"key": [], "title": [], "abstract": []})
    input_path.write_text(frame.to_csv(index=False), encoding="utf-8")
    return input_path


@pytest.mark.parametrize("operation", [run_triage, preview_triage, analyze_coverage])
def test_empty_corpus_rejected_in_all_execution_flows(tmp_path: Path, operation) -> None:
    """A 0-row corpus must abort run, preview AND coverage before processing."""
    config_path = _write_config(tmp_path)
    input_path = _write_empty_corpus(tmp_path)
    output_dir = tmp_path / "out"

    kwargs = {"output_dir": output_dir} if operation is run_triage else {}
    with pytest.raises(ValueError, match="(?i)corpus"):
        operation(input_path, config_path, **kwargs)

    assert not output_dir.exists()


def test_empty_corpus_error_respects_active_locale(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    input_path = _write_empty_corpus(tmp_path)

    set_locale("en")
    with pytest.raises(ValueError) as exc:
        run_triage(input_path, config_path, output_dir=tmp_path / "out")
    assert "contains no articles" in str(exc.value)
    assert "nao contem" not in str(exc.value)


def test_diff_no_common_id_error_respects_active_locale(tmp_path: Path) -> None:
    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    pd.DataFrame({"col_x": ["1"], "Final_Decision": ["APPROVED_FINAL"]}).to_csv(a, index=False)
    pd.DataFrame({"col_y": ["1"], "Final_Decision": ["APPROVED_FINAL"]}).to_csv(b, index=False)

    set_locale("en")
    with pytest.raises(ValueError) as exc:
        diff_results(a, b)
    assert "No common ID column" in str(exc.value)
    assert "Nenhuma coluna" not in str(exc.value)


def test_export_invalid_result_error_respects_active_locale(tmp_path: Path) -> None:
    bogus = tmp_path / "raw.csv"
    pd.DataFrame({"key": ["A1"], "title": ["Anything"]}).to_csv(bogus, index=False)

    set_locale("en")
    with pytest.raises(ValueError) as exc:
        export_academic_package(bogus, tmp_path / "out")
    assert "does not appear to be a FastSLR result" in str(exc.value)
    assert "nao parece" not in str(exc.value)


def test_create_project_exists_error_respects_active_locale(tmp_path: Path) -> None:
    target = tmp_path / "proj"
    target.mkdir()
    (target / "config.json").write_text("{}", encoding="utf-8")

    set_locale("en")
    with pytest.raises(FileExistsError) as exc:
        create_project("proj", blocks=[], output_dir=target)
    assert "already contains project files" in str(exc.value)
    assert "ja contem" not in str(exc.value)


@pytest.mark.parametrize("pattern", [r"(a{2,})+", r"(a{2,4})+", r"(\d{1,9})*x"])
def test_redos_detector_rejects_interval_quantifier_nesting(pattern: str) -> None:
    """Interval quantifiers nested in a repeated group are exponentially
    ambiguous and must be rejected like ``(a+)+``."""
    assert compile_pattern(pattern, is_regex=True) is None


@pytest.mark.parametrize(
    "pattern",
    [r"(a{2})+", r"\d{2,4}", r"(abc)+", r"colou?r", r"(machine learning)"],
)
def test_redos_detector_keeps_accepting_benign_patterns(pattern: str) -> None:
    compiled = compile_pattern(pattern, is_regex=True)
    assert compiled is not None
