"""Smoke tests for the FastSLR TUI (src/fastslr/app/tui.py).

These tests raise coverage of the TUI by exercising the happy paths that the
findings regression suite (``test_tui_findings.py``) leaves untouched: mounting
every screen, navigating from the dashboard, and driving each screen's primary
button handler with the ``controller`` layer mocked out (no real file/network
I/O).

They follow the exact mechanism used by ``test_tui_findings.py``:

- Textual's headless ``app.run_test()`` pilot drives the app (never ``app.run()``).
- Because ``pytest-asyncio`` is not a dependency, each async scenario is wrapped
  in ``asyncio.run`` via the ``_run`` helper.

Every controller call that would otherwise touch disk is monkeypatched, so the
tests stay deterministic and fast.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable
from pathlib import Path
from typing import Any, TypeVar

import pandas as pd
import pytest
from textual.widgets import Button, DataTable, Input, Select, Static, TextArea

from fastslr import i18n
from fastslr.app import controller, tui

_T = TypeVar("_T")


def _run(coro: Awaitable[_T]) -> _T:
    """Run an async pilot interaction without pytest-asyncio."""
    return asyncio.run(coro)  # type: ignore[arg-type]


@pytest.fixture(autouse=True)
def _reset_locale():
    """Keep the global locale isolated between tests."""
    original = i18n.get_locale()
    yield
    i18n.set_locale(original)


def _silence_notify(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Patch App.notify to capture (and silence) notification text."""
    captured: list[str] = []

    def _notify(self, message, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        captured.append(str(message))

    monkeypatch.setattr(tui.App, "notify", _notify)
    return captured


# ── App boot & dashboard ──────────────────────────────────────────────────────


def test_app_boots_with_dashboard():
    """The app mounts and pushes the DashboardScreen with one menu button per item."""

    async def scenario() -> tuple[bool, int]:
        app = tui.FastSLRApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            buttons = screen.query(".menu-btn")
            return isinstance(screen, tui.DashboardScreen), len(buttons)

    is_dashboard, button_count = _run(scenario())
    assert is_dashboard
    assert button_count == len(tui.MENU_ITEMS)


def test_app_title_includes_version():
    """The App TITLE is derived from the controller version."""
    assert tui.APP_VERSION in (tui.FastSLRApp.TITLE or "")


def test_dashboard_navigates_to_every_screen():
    """Each menu action pushes the matching screen class onto the stack."""
    expected = {
        "new_project": tui.NewProjectScreen,
        "load_profile": tui.ProfilesScreen,
        "edit_config": tui.EditConfigScreen,
        "browse_terms": tui.BrowseTermsScreen,
        "run_triage": tui.RunTriageScreen,
        "results": tui.ResultsScreen,
        "coverage": tui.CoverageScreen,
        "diff_runs": tui.DiffScreen,
        "export": tui.ExportScreen,
        "settings": tui.SettingsScreen,
    }

    async def scenario(action_id: str) -> type:
        app = tui.FastSLRApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            dashboard = app.screen
            assert isinstance(dashboard, tui.DashboardScreen)
            dashboard._navigate(action_id)
            await pilot.pause()
            return type(app.screen)

    for action_id, screen_cls in expected.items():
        assert _run(scenario(action_id)) is screen_cls


def test_dashboard_unknown_action_is_noop():
    """Navigating with an unmapped id keeps the dashboard on top."""

    async def scenario() -> bool:
        app = tui.FastSLRApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            app.screen._navigate("does_not_exist")  # type: ignore[attr-defined]
            await pilot.pause()
            return isinstance(app.screen, tui.DashboardScreen)

    assert _run(scenario())


def test_dashboard_menu_action_methods_navigate():
    """The numbered ``action_menu_*`` handlers route to their screens."""
    cases = [
        ("action_menu_1", tui.NewProjectScreen),
        ("action_menu_5", tui.RunTriageScreen),
        ("action_menu_6", tui.ResultsScreen),
        ("action_menu_0", tui.SettingsScreen),
    ]

    async def scenario(method_name: str) -> type:
        app = tui.FastSLRApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            getattr(app.screen, method_name)()
            await pilot.pause()
            return type(app.screen)

    for method_name, screen_cls in cases:
        assert _run(scenario(method_name)) is screen_cls


def test_dashboard_button_press_navigates():
    """Pressing a menu button triggers navigation via the Button.Pressed handler."""

    async def scenario() -> bool:
        app = tui.FastSLRApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            app.screen.query_one("#run_triage", Button).press()
            await pilot.pause()
            return isinstance(app.screen, tui.RunTriageScreen)

    assert _run(scenario())


def test_dashboard_quit_exits_app():
    """``action_quit_app`` exits the running app."""

    async def scenario() -> None:
        app = tui.FastSLRApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            app.screen.action_quit_app()  # type: ignore[attr-defined]
            await pilot.pause()

    _run(scenario())  # should return cleanly, not hang


# ── Generic helper: mount a screen and run a callback ──────────────────────────


async def _drive(app, screen, fn) -> Any:  # noqa: ANN001
    """Push ``screen``, run ``fn(screen, pilot)``, pause, then read widgets.

    ``fn`` performs interactions (set Input values, press Buttons). It may
    return a *reader* callable ``reader(screen) -> value`` which is invoked
    while the app is still live (after a final pause) so that widget state is
    captured before the headless app tears the DOM down.
    """
    async with app.run_test() as pilot:
        await app.push_screen(screen)
        await pilot.pause()
        await pilot.pause()
        reader = fn(screen, pilot)
        await pilot.pause()
        if callable(reader):
            return reader(screen)
        return reader


def test_every_screen_composes_without_error():
    """Each screen mounts and renders its declared widgets."""
    screens = [
        tui.RunTriageScreen,
        tui.NewProjectScreen,
        tui.BrowseTermsScreen,
        tui.ResultsScreen,
        tui.CoverageScreen,
        tui.DiffScreen,
        tui.ExportScreen,
        tui.EditConfigScreen,
        tui.ProfilesScreen,
        tui.SettingsScreen,
    ]

    async def scenario(screen_cls: type) -> bool:
        app = tui.FastSLRApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = screen_cls()
            await app.push_screen(screen)
            await pilot.pause()
            await pilot.pause()
            # Every screen has at least one Static and is the active screen.
            return bool(screen.query(Static)) and app.screen is screen

    for screen_cls in screens:
        assert _run(scenario(screen_cls)), screen_cls.__name__


def test_screens_go_back_pops_to_dashboard():
    """``action_go_back`` pops a pushed screen, returning to the dashboard."""
    screens = [
        tui.RunTriageScreen,
        tui.BrowseTermsScreen,
        tui.ResultsScreen,
        tui.CoverageScreen,
        tui.DiffScreen,
        tui.ExportScreen,
        tui.EditConfigScreen,
        tui.ProfilesScreen,
        tui.SettingsScreen,
        tui.NewProjectScreen,
    ]

    async def scenario(screen_cls: type) -> bool:
        app = tui.FastSLRApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = screen_cls()
            await app.push_screen(screen)
            await pilot.pause()
            screen.action_go_back()
            await pilot.pause()
            return isinstance(app.screen, tui.DashboardScreen)

    for screen_cls in screens:
        assert _run(scenario(screen_cls)), screen_cls.__name__


# ── Browse Terms ───────────────────────────────────────────────────────────────


def test_browse_terms_loads_table(monkeypatch, tmp_path):
    """A valid config path populates the terms DataTable."""
    _silence_notify(monkeypatch)
    view = controller.TermsView(
        terms=[
            {"block": "AI", "kind": "core", "term": "neural", "level": 1, "scope": "title"},
            {"block": "AI", "kind": "core", "term": "network", "level": 2, "scope": "abstract"},
        ],
        total=2,
        blocks=["AI"],
    )
    monkeypatch.setattr(controller, "browse_terms", lambda **_kw: view)

    async def scenario() -> int:
        app = tui.FastSLRApp()
        screen = tui.BrowseTermsScreen()

        def act(s, _pilot):  # noqa: ANN001
            s.query_one("#config_path", Input).value = str(tmp_path / "config.json")
            s.query_one("#btn_load", Button).press()
            return lambda sc: sc.query_one("#terms_table", DataTable).row_count

        return await _drive(app, screen, act)

    assert _run(scenario()) == 2


def test_browse_terms_handles_controller_error(monkeypatch, tmp_path):
    """A controller failure is reported via notify, not a crash."""
    captured = _silence_notify(monkeypatch)

    def _boom(**_kw):
        raise ValueError("bad terms")

    monkeypatch.setattr(controller, "browse_terms", _boom)

    async def scenario() -> None:
        app = tui.FastSLRApp()
        screen = tui.BrowseTermsScreen()

        def act(s, _pilot):  # noqa: ANN001
            s.query_one("#config_path", Input).value = str(tmp_path / "config.json")
            s.query_one("#btn_load", Button).press()

        await _drive(app, screen, act)

    _run(scenario())
    assert any("bad terms" in m for m in captured)


# ── Results Explorer ───────────────────────────────────────────────────────────


def _results_frame(rows: int = 120) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ID": list(range(rows)),
            "Final_Decision": ["APPROVED_FINAL"] * rows,
            "Decision_Reason": ["ok"] * rows,
            "Status_AI": ["hit"] * rows,
            "FinalScore_AI": [10] * rows,
        }
    )


def test_results_load_paginate_and_detail(monkeypatch, tmp_path):
    """Load results, page next/previous, and show a row detail."""
    _silence_notify(monkeypatch)
    monkeypatch.setattr(controller, "read_results_table", lambda _p: _results_frame(120))

    async def scenario() -> dict:
        app = tui.FastSLRApp()
        screen = tui.ResultsScreen()
        async with app.run_test() as pilot:
            await app.push_screen(screen)
            await pilot.pause()
            await pilot.pause()
            screen.query_one("#results_path", Input).value = str(tmp_path / "r.csv")
            screen.query_one("#btn_load", Button).press()
            await pilot.pause()
            first_page_rows = screen.query_one("#results_table", DataTable).row_count
            page_after_load = screen._results_page

            screen.query_one("#btn_next", Button).press()
            await pilot.pause()
            page_after_next = screen._results_page
            screen.query_one("#btn_prev", Button).press()
            await pilot.pause()
            page_after_prev = screen._results_page
            screen.query_one("#btn_detail", Button).press()
            await pilot.pause()
            detail = str(screen.query_one("#article_detail", Static).render())

        return {
            "first_page_rows": first_page_rows,
            "page_after_load": page_after_load,
            "page_after_next": page_after_next,
            "page_after_prev": page_after_prev,
            "detail": detail,
        }

    res = _run(scenario())
    assert res["first_page_rows"] == tui.ResultsScreen.PAGE_SIZE
    assert res["page_after_load"] == 0
    assert res["page_after_next"] == 1
    assert res["page_after_prev"] == 0
    assert "Article detail" in res["detail"]


def test_results_paging_buttons_noop_before_load(monkeypatch):
    """Paging/detail buttons are safe no-ops when no data is loaded."""
    _silence_notify(monkeypatch)

    async def scenario() -> bool:
        app = tui.FastSLRApp()
        screen = tui.ResultsScreen()

        def act(s, _pilot):  # noqa: ANN001
            s.query_one("#btn_next", Button).press()
            s.query_one("#btn_prev", Button).press()
            s.query_one("#btn_detail", Button).press()

        await _drive(app, screen, act)
        # No _results_df attribute should have been created.
        return not hasattr(screen, "_results_df")

    assert _run(scenario())


# ── Coverage ───────────────────────────────────────────────────────────────────


def test_coverage_analyze_renders_report(monkeypatch, tmp_path):
    """A successful analysis writes the formatted report into the output Static."""
    _silence_notify(monkeypatch)
    sentinel = object()
    monkeypatch.setattr(controller, "analyze_coverage", lambda **_kw: sentinel)
    monkeypatch.setattr(controller, "format_coverage", lambda r: "COVERAGE-REPORT-OK")

    async def scenario() -> str:
        app = tui.FastSLRApp()
        screen = tui.CoverageScreen()

        def act(s, _pilot):  # noqa: ANN001
            s.query_one("#input_file", Input).value = str(tmp_path / "articles.csv")
            s.query_one("#config_file", Input).value = str(tmp_path / "config.json")
            s.query_one("#btn_analyze", Button).press()
            return lambda sc: str(sc.query_one("#report_output", Static).render())

        return await _drive(app, screen, act)

    assert "COVERAGE-REPORT-OK" in _run(scenario())


def test_coverage_empty_inputs_notify(monkeypatch):
    """Analyzing with empty inputs warns instead of calling the controller."""
    captured = _silence_notify(monkeypatch)

    def _should_not_run(**_kw):
        raise AssertionError("controller should not be called")

    monkeypatch.setattr(controller, "analyze_coverage", _should_not_run)

    async def scenario() -> None:
        app = tui.FastSLRApp()
        screen = tui.CoverageScreen()

        def act(s, _pilot):  # noqa: ANN001
            s.query_one("#btn_analyze", Button).press()

        await _drive(app, screen, act)

    _run(scenario())
    assert any("articles file" in m.lower() for m in captured)


# ── Diff ─────────────────────────────────────────────────────────────────────--


def test_diff_compare_populates_table(monkeypatch, tmp_path):
    """Comparing two files renders the summary and the changes table."""
    _silence_notify(monkeypatch)
    report = controller.DiffReport(
        changed=[
            controller.DiffEntry("1", "REJECTED_FINAL", "APPROVED_FINAL"),
            controller.DiffEntry("2", "FLAGGED_FINAL", "REJECTED_FINAL"),
        ],
        total_a=10,
        total_b=11,
    )
    monkeypatch.setattr(controller, "diff_results", lambda _a, _b: report)

    async def scenario() -> int:
        app = tui.FastSLRApp()
        screen = tui.DiffScreen()

        def act(s, _pilot):  # noqa: ANN001
            s.query_one("#file_a", Input).value = str(tmp_path / "a.csv")
            s.query_one("#file_b", Input).value = str(tmp_path / "b.csv")
            s.query_one("#btn_compare", Button).press()
            return lambda sc: sc.query_one("#diff_table", DataTable).row_count

        return await _drive(app, screen, act)

    assert _run(scenario()) == 2


def test_diff_empty_inputs_notify(monkeypatch):
    """Comparing without both files warns the user."""
    captured = _silence_notify(monkeypatch)

    async def scenario() -> None:
        app = tui.FastSLRApp()
        screen = tui.DiffScreen()

        def act(s, _pilot):  # noqa: ANN001
            s.query_one("#btn_compare", Button).press()

        await _drive(app, screen, act)

    _run(scenario())
    assert any("result files" in m.lower() for m in captured)


# ── Export ─────────────────────────────────────────────────────────────────────


def test_export_writes_success_message(monkeypatch, tmp_path):
    """A successful export updates the message Static with the zip path."""
    _silence_notify(monkeypatch)
    zip_path = tmp_path / "academic_package.zip"
    monkeypatch.setattr(controller, "export_academic_package", lambda **_kw: zip_path)

    async def scenario() -> str:
        app = tui.FastSLRApp()
        screen = tui.ExportScreen()

        def act(s, _pilot):  # noqa: ANN001
            s.query_one("#result_file", Input).value = str(tmp_path / "results.xlsx")
            s.query_one("#btn_export", Button).press()
            return lambda sc: str(sc.query_one("#export_msg", Static).render())

        return await _drive(app, screen, act)

    assert "academic_package.zip" in _run(scenario())


def test_export_empty_path_notify(monkeypatch):
    """Exporting without a results file warns the user."""
    captured = _silence_notify(monkeypatch)

    async def scenario() -> None:
        app = tui.FastSLRApp()
        screen = tui.ExportScreen()

        def act(s, _pilot):  # noqa: ANN001
            s.query_one("#btn_export", Button).press()

        await _drive(app, screen, act)

    _run(scenario())
    assert any("results file" in m.lower() for m in captured)


# ── Edit Config ────────────────────────────────────────────────────────────────


def test_edit_config_load_validate_save(monkeypatch, tmp_path):
    """Load a config file, validate it (no issues), then save it back."""
    captured = _silence_notify(monkeypatch)
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({"blocks": []}), encoding="utf-8")
    monkeypatch.setattr(controller, "validate_config", lambda _cfg: [])

    async def scenario() -> dict:
        app = tui.FastSLRApp()
        screen = tui.EditConfigScreen()
        async with app.run_test() as pilot:
            await app.push_screen(screen)
            await pilot.pause()
            await pilot.pause()
            screen.query_one("#config_path", Input).value = str(cfg_file)
            screen.query_one("#btn_load", Button).press()
            await pilot.pause()
            loaded_text = screen.query_one("#config_editor", TextArea).text

            screen.query_one("#btn_validate", Button).press()
            await pilot.pause()
            validate_status = str(screen.query_one("#config_status", Static).render())
            screen.query_one("#btn_save", Button).press()
            await pilot.pause()
            save_status = str(screen.query_one("#config_status", Static).render())

        return {
            "loaded_text": loaded_text,
            "validate_status": validate_status,
            "save_status": save_status,
        }

    res = _run(scenario())
    assert "blocks" in res["loaded_text"]
    assert "valid" in res["validate_status"].lower()
    assert "saved" in res["save_status"].lower()
    assert any("saved" in m.lower() for m in captured)


def test_edit_config_validate_reports_issues(monkeypatch):
    """Validation issues from the controller are surfaced in the status line."""
    _silence_notify(monkeypatch)
    issues = [
        controller.ValidationIssue("error", "missing field"),
        controller.ValidationIssue("warning", "odd value"),
    ]
    monkeypatch.setattr(controller, "validate_config", lambda _cfg: issues)

    async def scenario() -> str:
        app = tui.FastSLRApp()
        screen = tui.EditConfigScreen()

        def act(s, _pilot):  # noqa: ANN001
            s.query_one("#config_editor", TextArea).load_text('{"a": 1}')
            s.query_one("#btn_validate", Button).press()
            return lambda sc: str(sc.query_one("#config_status", Static).render())

        return await _drive(app, screen, act)

    status = _run(scenario())
    assert "missing field" in status


# ── New Project Wizard ─────────────────────────────────────────────────────────


# ── Profiles ───────────────────────────────────────────────────────────────────


def test_profiles_lists_saved_profiles(monkeypatch):
    """on_mount populates the table with one row per saved profile."""
    from fastslr.app import profiles as profiles_mod

    monkeypatch.setattr(
        profiles_mod,
        "list_profiles",
        lambda: [
            controller.ProfileInfo("alpha", Path("/tmp/alpha.json"), "first"),
            controller.ProfileInfo("beta", Path("/tmp/beta.json"), "second"),
        ],
    )

    async def scenario() -> int:
        app = tui.FastSLRApp()
        screen = tui.ProfilesScreen()
        async with app.run_test() as pilot:
            await app.push_screen(screen)
            await pilot.pause()
            await pilot.pause()
            return screen.query_one("#profiles_table", DataTable).row_count

    assert _run(scenario()) == 2


def test_profiles_empty_shows_placeholder_row(monkeypatch):
    """With no profiles, a single placeholder row is added."""
    from fastslr.app import profiles as profiles_mod

    monkeypatch.setattr(profiles_mod, "list_profiles", lambda: [])

    async def scenario() -> int:
        app = tui.FastSLRApp()
        screen = tui.ProfilesScreen()
        async with app.run_test() as pilot:
            await app.push_screen(screen)
            await pilot.pause()
            await pilot.pause()
            # Refresh exercises the reload handler too.
            screen.query_one("#btn_refresh", Button).press()
            await pilot.pause()
            return screen.query_one("#profiles_table", DataTable).row_count

    assert _run(scenario()) == 1


# ── Settings ───────────────────────────────────────────────────────────────────


def test_settings_apply_valid_locale_changes_locale():
    """Applying a real locale updates the global locale and shows feedback."""

    async def scenario() -> tuple[str, str]:
        i18n.set_locale("en")
        app = tui.FastSLRApp()
        screen = tui.SettingsScreen()
        async with app.run_test() as pilot:
            await app.push_screen(screen)
            await pilot.pause()
            await pilot.pause()
            screen.query_one("#lang_select", Select).value = "es"
            screen.query_one("#btn_apply", Button).press()
            await pilot.pause()
            msg = str(screen.query_one("#settings_msg", Static).render())
        return i18n.get_locale(), msg

    locale, msg = _run(scenario())
    assert locale == "es"
    assert "es" in msg


# ── Run Triage (check setup, non-threaded happy path) ──────────────────────────
