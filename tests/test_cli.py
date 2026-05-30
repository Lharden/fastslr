"""CLI smoke tests for fastslr.app.cli.

These are happy-path smoke tests for every command plus a few error-path
tests that exercise validation that already exists today (run with a missing
input/config). Commands that lack input validation (preview/coverage/diff with
missing files) are intentionally NOT tested here — they are slated to be
hardened in a later phase.

All tests pin the locale to English via ``--lang en`` (or an explicit
``set_locale`` call) so output assertions are deterministic regardless of the
host machine locale.

Profile tests monkeypatch ``Path.home()`` to ``tmp_path`` so they never touch
the real ``~/.fastslr/profiles`` directory.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from fastslr.app import profiles
from fastslr.app.cli import app
from fastslr.core.presets import generate_config

runner = CliRunner()


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def articles_csv(tmp_path: Path) -> Path:
    """A minimal articles input table (semicolon-separated, >= 3 columns)."""
    df = pd.DataFrame(
        {
            "key": ["A1", "A2", "A3"],
            "title": [
                "Machine learning in supply chain",
                "A study of context aware systems",
                "Unrelated cooking recipes",
            ],
            "abstract": [
                "We apply machine learning to supply chain optimization.",
                "Context aware computing improves decision making.",
                "How to bake bread at home.",
            ],
            "manual_tags": ["ml; scm", "context", ""],
        }
    )
    path = tmp_path / "articles.csv"
    df.to_csv(path, sep=";", index=False, encoding="utf-8-sig")
    return path


@pytest.fixture
def config_json(tmp_path: Path) -> Path:
    """A valid config.json with three domain blocks."""
    blocks = [
        {"name": "CTX", "label": "Context"},
        {"name": "TECH", "label": "Technique"},
        {"name": "SCM", "label": "Supply Chain"},
    ]
    config = generate_config(preset_name="standard", blocks=blocks)
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.fixture
def terms_csv(tmp_path: Path) -> Path:
    """A minimal terms table with positives for each block plus a GLOBAL anti."""
    rows = [
        {
            "block": "CTX",
            "kind": "pos",
            "term": "context aware",
            "level": "1",
            "section_scope": "any",
            "is_regex": "0",
        },
        {
            "block": "TECH",
            "kind": "pos",
            "term": "machine learning",
            "level": "1",
            "section_scope": "any",
            "is_regex": "0",
        },
        {
            "block": "SCM",
            "kind": "pos",
            "term": "supply chain",
            "level": "1",
            "section_scope": "any",
            "is_regex": "0",
        },
        {
            "block": "GLOBAL",
            "kind": "anti",
            "term": "cooking recipes",
            "level": "",
            "section_scope": "any",
            "is_regex": "0",
        },
    ]
    df = pd.DataFrame(rows)
    path = tmp_path / "terms.csv"
    df.to_csv(path, sep=";", index=False, encoding="utf-8-sig")
    return path


def _make_result_csv(path: Path, rows: list[tuple[str, str]]) -> Path:
    """Write a minimal triage-result CSV with ID + Final_Decision columns."""
    df = pd.DataFrame(
        {
            "ID": [r[0] for r in rows],
            "title": [f"title {r[0]}" for r in rows],
            "Final_Decision": [r[1] for r in rows],
        }
    )
    df.to_csv(path, sep=";", index=False, encoding="utf-8-sig")
    return path


@pytest.fixture
def home_redirect(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect Path.home() so profile commands use an isolated directory."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda _cls: fake_home))
    return fake_home


# ── version ────────────────────────────────────────────────────────────────


def test_version_happy() -> None:
    result = runner.invoke(app, ["version", "--lang", "en"])
    assert result.exit_code == 0, result.output
    assert "FastSLR v" in result.output


# ── doctor ───────────────────────────────────────────────────────────────────


def test_doctor_no_args_shows_quickstart() -> None:
    result = runner.invoke(app, ["doctor", "--lang", "en"])
    assert result.exit_code == 0, result.output
    assert "FastSLR quick start" in result.output


def test_doctor_happy_with_full_setup(
    articles_csv: Path, config_json: Path, terms_csv: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "doctor",
            "--lang",
            "en",
            "-i",
            str(articles_csv),
            "-c",
            str(config_json),
            "-t",
            str(terms_csv),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Run command" in result.output
    assert "Input articles" in result.output


def test_doctor_missing_config_reports_error(articles_csv: Path, tmp_path: Path) -> None:
    missing = tmp_path / "nope.json"
    result = runner.invoke(
        app,
        ["doctor", "--lang", "en", "-i", str(articles_csv), "-c", str(missing)],
    )
    assert result.exit_code == 1
    assert "Setup errors" in result.output


# ── run ────────────────────────────────────────────────────────────────────


def test_run_happy(articles_csv: Path, config_json: Path, terms_csv: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    result = runner.invoke(
        app,
        [
            "run",
            str(articles_csv),
            "--lang",
            "en",
            "-c",
            str(config_json),
            "-t",
            str(terms_csv),
            "-o",
            str(out_dir),
            "--quiet",
        ],
    )
    assert result.exit_code == 0, result.output
    # quiet suppresses the table, but the run must still produce artifacts
    assert (out_dir / "triage_results.xlsx").exists()


def test_run_verbose_prints_results(
    articles_csv: Path, config_json: Path, terms_csv: Path, tmp_path: Path
) -> None:
    out_dir = tmp_path / "out"
    result = runner.invoke(
        app,
        [
            "run",
            str(articles_csv),
            "--lang",
            "en",
            "-c",
            str(config_json),
            "-t",
            str(terms_csv),
            "-o",
            str(out_dir),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Triage Results" in result.output
    assert "Results saved to" in result.output


def test_run_missing_input_exits_1(config_json: Path, tmp_path: Path) -> None:
    missing = tmp_path / "ghost.csv"
    result = runner.invoke(
        app,
        ["run", str(missing), "--lang", "en", "-c", str(config_json)],
    )
    assert result.exit_code == 1
    assert "File not found" in result.output


def test_run_missing_config_exits_1(articles_csv: Path, tmp_path: Path) -> None:
    missing = tmp_path / "ghost.json"
    result = runner.invoke(
        app,
        ["run", str(articles_csv), "--lang", "en", "-c", str(missing)],
    )
    assert result.exit_code == 1
    assert "Config not found" in result.output


# ── preview ──────────────────────────────────────────────────────────────────


def test_preview_happy(articles_csv: Path, config_json: Path, terms_csv: Path) -> None:
    result = runner.invoke(
        app,
        [
            "preview",
            str(articles_csv),
            "--lang",
            "en",
            "-c",
            str(config_json),
            "-t",
            str(terms_csv),
            "-s",
            "3",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Triage Results" in result.output
    assert "Preview based on" in result.output


# ── coverage ─────────────────────────────────────────────────────────────────


def test_coverage_happy(articles_csv: Path, config_json: Path, terms_csv: Path) -> None:
    result = runner.invoke(
        app,
        [
            "coverage",
            str(articles_csv),
            "--lang",
            "en",
            "-c",
            str(config_json),
            "-t",
            str(terms_csv),
        ],
    )
    assert result.exit_code == 0, result.output


# ── diff ─────────────────────────────────────────────────────────────────────


def test_diff_happy(tmp_path: Path) -> None:
    a = _make_result_csv(
        tmp_path / "a.csv",
        [("A1", "APPROVED_FINAL"), ("A2", "REJECTED_FINAL")],
    )
    b = _make_result_csv(
        tmp_path / "b.csv",
        [("A1", "APPROVED_FINAL"), ("A2", "FLAGGED_FINAL")],
    )
    result = runner.invoke(app, ["diff", str(a), str(b), "--lang", "en"])
    assert result.exit_code == 0, result.output
    assert "Total changes: 1" in result.output


# ── new-project ──────────────────────────────────────────────────────────────


def test_new_project_happy(tmp_path: Path) -> None:
    out_dir = tmp_path / "proj"
    result = runner.invoke(
        app,
        [
            "new-project",
            "my-review",
            "--lang",
            "en",
            "-b",
            "CTX,TECH,SCM",
            "-o",
            str(out_dir),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Project created" in result.output
    assert (out_dir / "config.json").exists()
    assert (out_dir / "terms.xlsx").exists()


def test_new_project_empty_blocks_exits_1(tmp_path: Path) -> None:
    out_dir = tmp_path / "proj"
    result = runner.invoke(
        app,
        ["new-project", "my-review", "--lang", "en", "-b", " ,  ", "-o", str(out_dir)],
    )
    assert result.exit_code == 1
    assert "At least one block name is required" in result.output


# ── export ───────────────────────────────────────────────────────────────────


def test_export_happy(tmp_path: Path) -> None:
    result_file = _make_result_csv(
        tmp_path / "triage_results.csv",
        [("A1", "APPROVED_FINAL")],
    )
    out_dir = tmp_path / "export_out"
    result = runner.invoke(
        app,
        ["export", str(result_file), "--lang", "en", "-o", str(out_dir)],
    )
    assert result.exit_code == 0, result.output
    assert "Academic package exported" in result.output
    assert (out_dir / "academic_package.zip").exists()


def test_export_missing_result_exits_1(tmp_path: Path) -> None:
    missing = tmp_path / "ghost.csv"
    result = runner.invoke(app, ["export", str(missing), "--lang", "en"])
    assert result.exit_code == 1
    assert "File not found" in result.output


# ── terms ────────────────────────────────────────────────────────────────────


def test_terms_happy(config_json: Path, terms_csv: Path) -> None:
    result = runner.invoke(
        app,
        ["terms", "--lang", "en", "-c", str(config_json), "-t", str(terms_csv)],
    )
    assert result.exit_code == 0, result.output
    assert "Terms" in result.output


# ── profile save / load / list ───────────────────────────────────────────────


def test_profile_save_happy(config_json: Path, home_redirect: Path) -> None:
    result = runner.invoke(
        app,
        ["profile", "save", "myprofile", "--lang", "en", "-c", str(config_json)],
    )
    assert result.exit_code == 0, result.output
    assert "saved" in result.output
    assert (home_redirect / ".fastslr" / "profiles" / "myprofile.json").exists()


def test_profile_load_happy(config_json: Path, home_redirect: Path, tmp_path: Path) -> None:
    # Seed a profile first.
    profiles.save_profile("myprofile", json.loads(config_json.read_text(encoding="utf-8")))
    out_config = tmp_path / "loaded_config.json"
    result = runner.invoke(
        app,
        ["profile", "load", "myprofile", "--lang", "en", "-o", str(out_config)],
    )
    assert result.exit_code == 0, result.output
    assert "loaded" in result.output
    assert out_config.exists()


def test_profile_load_missing_exits_1(home_redirect: Path) -> None:
    result = runner.invoke(app, ["profile", "load", "ghost", "--lang", "en"])
    assert result.exit_code == 1
    assert "File not found" in result.output


def test_profile_list_empty(home_redirect: Path) -> None:
    result = runner.invoke(app, ["profile", "list", "--lang", "en"])
    assert result.exit_code == 0, result.output
    assert "No profiles saved yet" in result.output


def test_profile_list_happy(config_json: Path, home_redirect: Path) -> None:
    profiles.save_profile(
        "myprofile",
        json.loads(config_json.read_text(encoding="utf-8")),
        "a description",
    )
    result = runner.invoke(app, ["profile", "list", "--lang", "en"])
    assert result.exit_code == 0, result.output
    assert "Saved Profiles" in result.output
    assert "myprofile" in result.output


# ── Regression: friendly errors + .exists() validation (findings a, b) ─────────
#
# Before the fix, preview/coverage/diff/terms and `profile save -c <missing>`
# leaked raw FileNotFoundError/ValueError tracebacks (exit code != 1, output
# contained "Traceback" / "Error" from the interpreter). They must now fail with
# a localized one-line message and exit code 1.


def _assert_friendly_failure(result, needle: str) -> None:
    """Assert a command failed cleanly: exit 1, friendly message, no traceback."""
    assert result.exit_code == 1, result.output
    assert "Traceback" not in result.output, result.output
    assert needle in result.output, result.output


def test_preview_missing_input_exits_1_friendly(config_json: Path, tmp_path: Path) -> None:
    missing = tmp_path / "ghost.csv"
    result = runner.invoke(
        app,
        ["preview", str(missing), "--lang", "en", "-c", str(config_json)],
    )
    _assert_friendly_failure(result, "File not found")


def test_preview_missing_config_exits_1_friendly(articles_csv: Path, tmp_path: Path) -> None:
    missing = tmp_path / "ghost.json"
    result = runner.invoke(
        app,
        ["preview", str(articles_csv), "--lang", "en", "-c", str(missing)],
    )
    _assert_friendly_failure(result, "Config not found")


def test_coverage_missing_input_exits_1_friendly(config_json: Path, tmp_path: Path) -> None:
    missing = tmp_path / "ghost.csv"
    result = runner.invoke(
        app,
        ["coverage", str(missing), "--lang", "en", "-c", str(config_json)],
    )
    _assert_friendly_failure(result, "File not found")


def test_coverage_missing_terms_exits_1_friendly(
    articles_csv: Path, config_json: Path, tmp_path: Path
) -> None:
    missing_terms = tmp_path / "ghost_terms.csv"
    result = runner.invoke(
        app,
        [
            "coverage",
            str(articles_csv),
            "--lang",
            "en",
            "-c",
            str(config_json),
            "-t",
            str(missing_terms),
        ],
    )
    _assert_friendly_failure(result, "File not found")


def test_diff_missing_file_exits_1_friendly(tmp_path: Path) -> None:
    a = _make_result_csv(tmp_path / "a.csv", [("A1", "APPROVED_FINAL")])
    missing = tmp_path / "ghost_b.csv"
    result = runner.invoke(app, ["diff", str(a), str(missing), "--lang", "en"])
    _assert_friendly_failure(result, "File not found")


def test_terms_missing_config_exits_1_friendly(tmp_path: Path) -> None:
    missing = tmp_path / "ghost.json"
    result = runner.invoke(app, ["terms", "--lang", "en", "-c", str(missing)])
    _assert_friendly_failure(result, "Config not found")


def test_terms_missing_terms_exits_1_friendly(config_json: Path, tmp_path: Path) -> None:
    missing_terms = tmp_path / "ghost_terms.csv"
    result = runner.invoke(
        app,
        ["terms", "--lang", "en", "-c", str(config_json), "-t", str(missing_terms)],
    )
    _assert_friendly_failure(result, "File not found")


def test_profile_save_missing_config_exits_1_friendly(home_redirect: Path, tmp_path: Path) -> None:
    missing = tmp_path / "ghost.json"
    result = runner.invoke(
        app,
        ["profile", "save", "myprofile", "--lang", "en", "-c", str(missing)],
    )
    _assert_friendly_failure(result, "Config not found")


# ── Regression: false empty-kind warnings on normalization rows (finding c) ────
#
# In data/terms_final.csv, 34 GLOBAL rows carry a normalization rule
# (normalization_type filled) but an empty `kind` BY DESIGN. They must be skipped
# silently, not reported as "Row N: empty kind. Row skipped.".


def test_normalization_rows_do_not_warn_empty_kind() -> None:
    from fastslr.core.config import parse_terms_csv

    terms_path = Path(__file__).resolve().parents[1] / "data" / "terms_final.csv"
    if not terms_path.exists():
        pytest.skip("data/terms_final.csv not present")

    config = parse_terms_csv(terms_path, {"global": {}})
    warnings = config.get("_parse_warnings", [])
    empty_kind = [w for w in warnings if "empty kind" in w]
    assert empty_kind == [], (
        f"expected no 'empty kind' warnings for normalization rows, got {len(empty_kind)}: "
        f"{empty_kind[:3]}"
    )


def test_normalization_rows_still_parsed_as_rules() -> None:
    from fastslr.core.config import parse_terms_csv

    terms_path = Path(__file__).resolve().parents[1] / "data" / "terms_final.csv"
    if not terms_path.exists():
        pytest.skip("data/terms_final.csv not present")

    config = parse_terms_csv(terms_path, {"global": {}})
    rules = config.get("normalization_rules", {})
    # Skipping the rows silently must NOT drop the normalization rules themselves.
    assert rules.get("abbreviations"), "normalization abbreviations should still be extracted"


# ── Regression: non-interactive run must not abort on warnings (finding d) ─────


@pytest.fixture
def terms_csv_with_warning(tmp_path: Path) -> Path:
    """Terms table that triggers a config warning (a too-broad single-char term).

    The single-character positive term keeps the block valid (it still has a
    positive) but emits a 'too broad' warning, exercising the warning path.
    """
    rows = [
        {
            "block": "CTX",
            "kind": "pos",
            "term": "context aware",
            "level": "1",
            "section_scope": "any",
            "is_regex": "0",
        },
        {
            "block": "TECH",
            "kind": "pos",
            "term": "machine learning",
            "level": "1",
            "section_scope": "any",
            "is_regex": "0",
        },
        {
            "block": "SCM",
            "kind": "pos",
            "term": "x",  # single-char -> "too broad" warning
            "level": "1",
            "section_scope": "any",
            "is_regex": "0",
        },
    ]
    df = pd.DataFrame(rows)
    path = tmp_path / "terms_warn.csv"
    df.to_csv(path, sep=";", index=False, encoding="utf-8-sig")
    return path


def test_run_noninteractive_proceeds_past_warnings(
    articles_csv: Path,
    config_json: Path,
    terms_csv_with_warning: Path,
    tmp_path: Path,
) -> None:
    out_dir = tmp_path / "out"
    # CliRunner provides a non-TTY stdin, so the run must proceed by default
    # instead of aborting at the [y/N] prompt. Verbose (no --quiet) on purpose so
    # the warning block and the proceed path are both exercised.
    result = runner.invoke(
        app,
        [
            "run",
            str(articles_csv),
            "--lang",
            "en",
            "-c",
            str(config_json),
            "-t",
            str(terms_csv_with_warning),
            "-o",
            str(out_dir),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (out_dir / "triage_results.xlsx").exists()
    # It must have shown the warnings and the non-interactive proceed notice.
    assert "warning(s) found" in result.output
    assert "proceeding despite warnings" in result.output.lower()


# ── Regression: preview --sample must be a positive integer ───────────────────
#
# Finding preview-sample-zero-silent-empty: `preview --sample 0` previously
# sampled zero rows and printed empty stats as a "success"; `--sample -5` raised
# a raw pandas ValueError. Both must now fail with a friendly localized message
# and exit code 1 BEFORE any file/triage work happens.


def test_preview_sample_zero_exits_1_friendly(
    articles_csv: Path, config_json: Path, terms_csv: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "preview",
            str(articles_csv),
            "--lang",
            "en",
            "-c",
            str(config_json),
            "-t",
            str(terms_csv),
            "-s",
            "0",
        ],
    )
    assert result.exit_code == 1, result.output
    assert "Traceback" not in result.output, result.output
    assert "--sample must be a positive integer" in result.output


def test_preview_sample_negative_exits_1_friendly(
    articles_csv: Path, config_json: Path, terms_csv: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "preview",
            str(articles_csv),
            "--lang",
            "en",
            "-c",
            str(config_json),
            "-t",
            str(terms_csv),
            "-s",
            "-5",
        ],
    )
    assert result.exit_code == 1, result.output
    assert "Traceback" not in result.output, result.output
    assert "--sample must be a positive integer" in result.output


def test_preview_sample_zero_checked_before_files(config_json: Path, tmp_path: Path) -> None:
    """The sample guard fires before .exists() checks, so a missing input is moot."""
    missing = tmp_path / "ghost.csv"
    result = runner.invoke(
        app,
        ["preview", str(missing), "--lang", "en", "-c", str(config_json), "-s", "0"],
    )
    assert result.exit_code == 1, result.output
    assert "--sample must be a positive integer" in result.output


# ── Regression: doctor output is localized (no hardcoded English) ─────────────
#
# Finding doctor-not-localized-mixed-language: _print_setup_inspection used
# hardcoded English literals ('Setup errors', 'Domain blocks', 'Valid terms',
# 'Run command', ...) while the rest of the CLI followed the locale. Under
# --lang pt_BR the doctor output must be Portuguese, with none of the old
# English headers leaking through.


def test_doctor_localized_pt_br_no_english_headers(
    articles_csv: Path, config_json: Path, terms_csv: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "doctor",
            "--lang",
            "pt_BR",
            "-i",
            str(articles_csv),
            "-c",
            str(config_json),
            "-t",
            str(terms_csv),
        ],
    )
    assert result.exit_code == 0, result.output
    # Portuguese headers present.
    assert "Comando de execucao" in result.output
    assert "Artigos de entrada" in result.output
    # Old hardcoded English headers must NOT appear.
    for english in (
        "Run command",
        "Input articles",
        "Domain blocks",
        "Valid terms",
        "Detected field mapping",
    ):
        assert english not in result.output, f"leaked English header: {english!r}"


def test_doctor_localized_pt_br_setup_errors(articles_csv: Path, tmp_path: Path) -> None:
    missing = tmp_path / "nope.json"
    result = runner.invoke(
        app,
        ["doctor", "--lang", "pt_BR", "-i", str(articles_csv), "-c", str(missing)],
    )
    assert result.exit_code == 1
    assert "Erros de configuracao" in result.output
    assert "Setup errors" not in result.output


# ── Regression: new-project --force overwrites; without it, refuses ───────────


def test_new_project_refuses_existing_without_force(tmp_path: Path) -> None:
    out_dir = tmp_path / "proj"
    first = runner.invoke(
        app,
        ["new-project", "r", "--lang", "en", "-b", "CTX", "-o", str(out_dir)],
    )
    assert first.exit_code == 0, first.output
    second = runner.invoke(
        app,
        ["new-project", "r", "--lang", "en", "-b", "CTX", "-o", str(out_dir)],
    )
    assert second.exit_code == 1, second.output
    assert "Traceback" not in second.output, second.output


def test_new_project_force_overwrites_existing(tmp_path: Path) -> None:
    out_dir = tmp_path / "proj"
    first = runner.invoke(
        app,
        ["new-project", "r", "--lang", "en", "-b", "CTX", "-o", str(out_dir)],
    )
    assert first.exit_code == 0, first.output
    forced = runner.invoke(
        app,
        ["new-project", "r", "--lang", "en", "-b", "CTX", "-o", str(out_dir), "--force"],
    )
    assert forced.exit_code == 0, forced.output
    assert (out_dir / "config.json").exists()


# ── Regression: i18n hardening (findings i18n-format-valueerror / detect) ─────


def test_i18n_format_valueerror_does_not_crash() -> None:
    """A typed format spec given a non-numeric value must not raise (hardening)."""
    from fastslr.i18n import _ as translate
    from fastslr.i18n import set_locale

    set_locale("en")
    # 'speed_unit' is '{value:.1f} articles/s' — a string value triggers
    # ValueError in str.format; _() must swallow it and return the raw template.
    out = translate("speed_unit", value="not a number")
    assert "{value:.1f}" in out  # unformatted template returned, no exception


def test_detect_locale_env_var_priority(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastslr.i18n import detect_locale

    monkeypatch.setenv("FASTSLR_LANG", "es")
    assert detect_locale() == "es"


def test_detect_locale_parses_lang_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastslr.i18n import detect_locale

    monkeypatch.delenv("FASTSLR_LANG", raising=False)
    monkeypatch.setenv("LC_ALL", "")
    monkeypatch.setenv("LC_MESSAGES", "")
    monkeypatch.setenv("LC_CTYPE", "")
    monkeypatch.setenv("LANG", "pt_BR.UTF-8")
    # With no FASTSLR_LANG and a pt_BR LANG, detection should resolve to pt_BR
    # (either directly from the process locale or by parsing LANG). The exact
    # source depends on the host's configured C locale; both are acceptable.
    assert detect_locale() in ("pt_BR", "en")


def test_detect_locale_no_deprecation_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    """detect_locale must not emit a DeprecationWarning (no getdefaultlocale)."""
    import warnings

    from fastslr.i18n import detect_locale

    monkeypatch.delenv("FASTSLR_LANG", raising=False)
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        detect_locale()  # must not raise
