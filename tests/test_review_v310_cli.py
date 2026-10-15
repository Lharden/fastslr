"""Revisao v3.1.0, CLI: guarda de sobrescrita em 'profile load' e erros de SO amigaveis.

1. 'fastslr profile load' gravava config.json sem checar se ja existia; dentro de um projeto
   isso apagava a configuracao atual sem volta. Agora exige --force, como create_project.
2. main() so tratava FileNotFoundError, JSONDecodeError e ValueError; PermissionError,
   FileExistsError (OSError) e RuntimeError (taxa de erro) chegavam como traceback cru.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from fastslr.app import cli, profiles
from fastslr.app.cli import app

from .freeze_audit_support import TERMS_FINAL, write_config

runner = CliRunner()


@pytest.fixture
def isolated_profile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "profiles"
    target.mkdir()
    monkeypatch.setattr(profiles, "_profiles_dir", lambda: target)
    profiles.save_profile("meu", {"novo": True})


def _main_with_argv(monkeypatch: pytest.MonkeyPatch, *args: str) -> None:
    monkeypatch.setattr(sys, "argv", ["fastslr", *args])
    cli.main()


# -- 1. profile load nao sobrescreve em silencio ------------------------------


class TestProfileLoadGuard:
    def test_existing_destination_is_refused_and_untouched(
        self, isolated_profile: None, tmp_path: Path
    ) -> None:
        dest = tmp_path / "config.json"
        dest.write_text('{"antigo": true}', encoding="utf-8")

        result = runner.invoke(app, ["profile", "load", "meu", "-o", str(dest)])

        assert result.exit_code == 1
        assert "--force" in result.output
        assert dest.read_text(encoding="utf-8") == '{"antigo": true}'

    def test_force_overwrites(self, isolated_profile: None, tmp_path: Path) -> None:
        dest = tmp_path / "config.json"
        dest.write_text('{"antigo": true}', encoding="utf-8")

        result = runner.invoke(app, ["profile", "load", "meu", "-o", str(dest), "--force"])

        assert result.exit_code == 0
        assert json.loads(dest.read_text(encoding="utf-8")) == {"novo": True}

    def test_new_destination_is_written_without_force(
        self, isolated_profile: None, tmp_path: Path
    ) -> None:
        dest = tmp_path / "novo.json"

        result = runner.invoke(app, ["profile", "load", "meu", "-o", str(dest)])

        assert result.exit_code == 0
        assert json.loads(dest.read_text(encoding="utf-8")) == {"novo": True}


# -- 2. main() traduz OSError e RuntimeError ----------------------------------


class TestMainFriendlyErrors:
    def test_permission_error_tells_to_close_the_file(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def boom() -> None:
            raise PermissionError(13, "Permission denied", "triage_results.xlsx")

        monkeypatch.setattr(cli, "app", boom)
        with pytest.raises(SystemExit) as exc:
            cli.main()

        out = capsys.readouterr().out
        assert exc.value.code == 1
        assert "triage_results.xlsx" in out
        assert "Traceback" not in out

    def test_runtime_error_is_friendly(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def boom() -> None:
            raise RuntimeError("taxa de erro 40% acima do limite")

        monkeypatch.setattr(cli, "app", boom)
        with pytest.raises(SystemExit) as exc:
            cli.main()

        out = capsys.readouterr().out
        assert exc.value.code == 1
        assert "taxa de erro 40% acima do limite" in out

    def test_unrelated_exception_is_not_swallowed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def boom() -> None:
            raise KeyError("x")

        monkeypatch.setattr(cli, "app", boom)
        with pytest.raises(KeyError):
            cli.main()

    def test_run_with_output_dir_pointing_to_a_file(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        articles = tmp_path / "articles.csv"
        pd.DataFrame(
            {
                "key": ["A1", "A2"],
                "title": ["Machine learning", "Supply chain"],
                "abstract": ["machine learning here", "supply chain there"],
                "manual_tags": ["", ""],
            }
        ).to_csv(articles, sep=";", index=False, encoding="utf-8-sig")
        config = write_config(tmp_path / "config.json")
        out_file = tmp_path / "saida"
        out_file.write_text("sou um arquivo", encoding="utf-8")

        with pytest.raises(SystemExit) as exc:
            _main_with_argv(
                monkeypatch,
                "run",
                str(articles),
                "-c",
                str(config),
                "-t",
                str(TERMS_FINAL),
                "-o",
                str(out_file),
                "-y",
                "-q",
            )

        out = capsys.readouterr().out
        assert exc.value.code == 1
        assert "saida" in out
        assert out_file.read_text(encoding="utf-8") == "sou um arquivo"
