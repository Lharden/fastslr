"""The installed ``fastslr`` console script must route through ``main()``.

``[project.scripts]`` used to point at the Typer ``app`` directly, so commands
that let ``ValueError`` / ``FileNotFoundError`` / ``json.JSONDecodeError``
escape (``preview``, ``coverage``) printed a raw traceback instead of the
one-line message that ``fastslr.app.cli.main`` produces. These tests resolve
the console-script target from the installed package metadata and run exactly
that callable in a subprocess.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from importlib.metadata import entry_points
from pathlib import Path

import pandas as pd
import pytest

from fastslr.core.presets import generate_config


def _console_script_target() -> str:
    eps = [ep for ep in entry_points(group="console_scripts") if ep.name == "fastslr"]
    assert eps, "console script 'fastslr' is not installed"
    return eps[0].value  # e.g. "fastslr.app.cli:main"


def _run_entrypoint(*args: str) -> subprocess.CompletedProcess[str]:
    module, _, attr = _console_script_target().partition(":")
    code = f"import sys; from {module} import {attr} as f; sys.argv[0]='fastslr'; f()"
    return subprocess.run(
        [sys.executable, "-c", code, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


@pytest.fixture
def inputs_with_broken_config(tmp_path: Path) -> tuple[Path, Path]:
    """Valid articles table plus a config.json that is not valid JSON."""
    articles = tmp_path / "articles.csv"
    pd.DataFrame(
        {
            "key": ["A1", "A2"],
            "title": ["Machine learning", "Supply chain"],
            "abstract": ["machine learning here", "supply chain there"],
            "manual_tags": ["", ""],
        }
    ).to_csv(articles, sep=";", index=False, encoding="utf-8-sig")
    config = tmp_path / "config.json"
    config.write_text("{bad", encoding="utf-8")
    return articles, config


def test_console_script_targets_main() -> None:
    assert _console_script_target() == "fastslr.app.cli:main"


@pytest.mark.parametrize("command", ["preview", "coverage"])
def test_decode_error_is_one_line_exit_1(
    command: str, inputs_with_broken_config: tuple[Path, Path]
) -> None:
    articles, config = inputs_with_broken_config
    proc = _run_entrypoint(command, str(articles), "-c", str(config), "--lang", "en")
    out = proc.stdout + proc.stderr
    assert proc.returncode == 1
    assert "Traceback" not in out
    assert "Expecting property name" in out
    assert len(out.strip().splitlines()) <= 3  # one message, allowing for wrapping


def test_help_and_exit_codes_unchanged() -> None:
    assert _run_entrypoint("--help").returncode == 0
    assert _run_entrypoint("version").returncode == 0
    # typer.Exit(1) from _require_input stays exit 1 with no traceback
    proc = _run_entrypoint("preview", "nope.csv", "-c", "nope.json", "--lang", "en")
    assert proc.returncode == 1
    assert "Traceback" not in proc.stderr


@pytest.fixture
def setup_files(tmp_path: Path) -> tuple[Path, Path]:
    """Valid config.json and terms.csv shared by the record-ID tests."""
    config = tmp_path / "config.json"
    cfg = generate_config(preset_name="standard", blocks=[{"name": "TECH", "label": "Technique"}])
    config.write_text(json.dumps(cfg), encoding="utf-8")
    terms = tmp_path / "terms.csv"
    pd.DataFrame(
        [
            {
                "block": "TECH",
                "kind": "pos",
                "term": "machine learning",
                "level": "1",
                "section_scope": "any",
                "is_regex": "0",
            }
        ]
    ).to_csv(terms, sep=";", index=False, encoding="utf-8-sig")
    return config, terms


def _articles(path: Path, keys: list[str]) -> Path:
    pd.DataFrame(
        {
            "key": keys,
            "title": [f"Machine learning {i}" for i in range(len(keys))],
            "abstract": ["machine learning here"] * len(keys),
            "manual_tags": [""] * len(keys),
        }
    ).to_csv(path, sep=";", index=False, encoding="utf-8-sig")
    return path


@pytest.mark.parametrize("command", ["run", "doctor", "preview", "coverage"])
@pytest.mark.parametrize(
    ("keys", "fragment"),
    [(["A1", "A1"], "duplicate record ID"), (["A1", ""], "blank ID")],
    ids=["duplicate-id", "empty-id"],
)
def test_invalid_record_ids_are_one_line_exit_1(
    command: str,
    keys: list[str],
    fragment: str,
    tmp_path: Path,
    setup_files: tuple[Path, Path],
) -> None:
    config, terms = setup_files
    articles = _articles(tmp_path / "articles.csv", keys)
    if command == "doctor":
        args = ["doctor", "-i", str(articles), "-c", str(config), "-t", str(terms)]
    elif command == "run":
        args = [
            "run",
            str(articles),
            "-c",
            str(config),
            "-t",
            str(terms),
            "-o",
            str(tmp_path / "out"),
            "--yes",
            "--quiet",
        ]
    else:
        args = [command, str(articles), "-c", str(config), "-t", str(terms)]
    proc = _run_entrypoint(*args, "--lang", "en")
    out = proc.stdout + proc.stderr
    assert proc.returncode == 1, out
    assert "Traceback" not in out
    assert fragment in out
