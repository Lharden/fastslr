"""Regression tests for the approved final-audit G3 changes."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import tomllib
from typer.testing import CliRunner

from fastslr.app import cli, controller, tui
from fastslr.i18n import _ as translate
from fastslr.i18n import set_locale

ROOT = Path(__file__).resolve().parents[1]
runner = CliRunner()


def test_console_script_uses_friendly_main_and_license_is_spdx_string() -> None:
    with (ROOT / "pyproject.toml").open("rb") as file:
        project = tomllib.load(file)["project"]

    assert project["scripts"]["fastslr"] == "fastslr.app.cli:main"
    assert project["license"] == "MIT"


def test_ascii_spinner_frames_are_cp1252_safe() -> None:
    spinner = cli._ascii_spinner_column()

    for frame in spinner.spinner.frames:
        frame.encode("cp1252", errors="strict")


def test_terms_command_displays_propagated_parse_warnings(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    warning = "Row 7: invalid regex was ignored"
    monkeypatch.setattr(
        controller,
        "browse_terms",
        lambda **_kwargs: SimpleNamespace(total=0, terms=[], parse_warnings=[warning]),
    )

    result = runner.invoke(cli.app, ["terms", "--lang", "en", "-c", str(config_path)])

    assert result.exit_code == 0, result.output
    assert warning in result.output
    assert "Parse warnings" in result.output


def test_run_uses_localized_progress_label(monkeypatch, tmp_path: Path) -> None:
    descriptions: list[str] = []
    input_path = tmp_path / "articles.csv"
    config_path = tmp_path / "config.json"
    input_path.write_text("id,title,abstract\n1,A,B\n", encoding="utf-8")
    config_path.write_text("{}", encoding="utf-8")

    class FakeProgress:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def add_task(self, description: str, total=None) -> int:
            descriptions.append(description)
            return 1

        def update(self, *_args, **_kwargs) -> None:
            pass

    monkeypatch.setattr(cli, "Progress", FakeProgress)
    monkeypatch.setattr(controller, "_prepare_config", lambda *_args: {})
    monkeypatch.setattr(controller, "validate_config", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        controller,
        "run_triage",
        lambda **_kwargs: SimpleNamespace(stats={}, output_dir=tmp_path / "out"),
    )

    result = runner.invoke(
        cli.app,
        ["run", str(input_path), "--config", str(config_path), "--lang", "es", "--quiet"],
    )

    assert result.exit_code == 0, result.output
    assert descriptions == ["Triaje"]


def test_edit_config_uses_document_validation_for_validate_and_save(
    monkeypatch, tmp_path: Path
) -> None:
    flags: list[bool] = []

    def fake_validate(_config: dict, *, require_resolved_blocks: bool = True) -> list:
        flags.append(require_resolved_blocks)
        return []

    class Editor:
        text = '{"global": {}}'

    class Status:
        def update(self, _message: str) -> None:
            pass

    class ConfigPath:
        value = str(tmp_path / "config.json")

    class DummyScreen:
        def query_one(self, selector: str, _widget_type):
            return {
                "#config_editor": Editor(),
                "#config_status": Status(),
                "#config_path": ConfigPath(),
            }[selector]

        def notify(self, *_args, **_kwargs) -> None:
            pass

    monkeypatch.setattr(controller, "validate_config", fake_validate)
    screen = cast(Any, DummyScreen())

    tui.EditConfigScreen.validate_config_text(screen)
    tui.EditConfigScreen.save_config(screen)

    assert flags == [False, False]


def test_all_locales_define_g3_user_visible_keys() -> None:
    expected = {
        "progress_triage",
        "terms_parse_warnings",
        "error_empty_corpus",
        "error_no_common_id",
        "error_invalid_result",
    }

    for locale in ("en", "es", "pt_BR"):
        data = json.loads(
            (ROOT / "src" / "fastslr" / "i18n" / "locales" / f"{locale}.json").read_text(
                encoding="utf-8"
            )
        )
        assert expected <= data.keys()

    set_locale("es")
    assert translate("progress_triage") == "Triaje"
    set_locale("en")


def test_sdist_manifest_includes_test_support_files() -> None:
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")

    assert "tests/conftest.py" in manifest
    assert "tests/__init__.py" in manifest


def test_publish_workflow_validates_version_and_guards_manual_publish() -> None:
    workflow = (ROOT / ".github" / "workflows" / "publish-pypi.yml").read_text(encoding="utf-8")

    assert "confirm_publish" in workflow
    assert "github.event.repository.default_branch" in workflow
    assert "github.event.release.tag_name" in workflow
    assert "Validate release tag against package version" in workflow
    assert "needs.build.outputs.version" in workflow
    assert "pypa/gh-action-pypi-publish@release/v1" in workflow
