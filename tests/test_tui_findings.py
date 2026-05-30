"""Regression tests for TUI findings (src/fastslr/app/tui.py).

These tests are deliberately lightweight: Textual TUIs are hard to test end
to end, so we drive the app with Textual's built-in ``run_test`` pilot and
assert on observable widget state plus emitted ``Notification`` messages.

We avoid the ``pytest-asyncio`` dependency (not installed) by wrapping each
async pilot interaction in ``asyncio.run``.

Findings covered:
- tui-worker-ui-access-from-thread: ``_run_triage`` now takes the 4 input
  values as arguments (read on the UI thread by ``start_triage``).
- tui-settings-locale-empty-no-feedback: ``apply_settings`` gives feedback
  when no language is selected.
- tui-settings-locale-not-applied-current-screen: the language ``Select`` is
  initialized from ``get_locale()`` instead of a hardcoded ``"en"``.
- tui-empty-input-silent-return: load handlers notify instead of returning
  silently on an empty path.
- tui-results-detail-cursor-row-empty: filtering by decision on a file
  without a ``Final_Decision`` column notifies the user.
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable
from typing import TypeVar

import pandas as pd
import pytest
from textual.widgets import Button, Input, Select, Static

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


def test_run_triage_signature_reads_inputs_as_arguments():
    """tui-worker-ui-access-from-thread.

    The thread worker must receive the input values as arguments so that the
    DOM is only queried on the UI thread (in ``start_triage``), not inside the
    worker thread.
    """
    params = list(inspect.signature(tui.RunTriageScreen._run_triage).parameters)
    assert params == ["self", "input_path", "config_path", "terms_path", "output_dir"]


def test_settings_select_uses_current_locale():
    """tui-settings-locale-not-applied-current-screen.

    The language Select must be initialized with the active locale instead of
    a hardcoded value.
    """
    i18n.set_locale("pt_BR")

    async def scenario() -> str | None:
        app = tui.FastSLRApp()
        async with app.run_test() as pilot:
            screen = tui.SettingsScreen()
            await app.push_screen(screen)
            await pilot.pause()
            await pilot.pause()
            select = screen.query_one("#lang_select", Select)
            return str(select.value)

    assert _run(scenario()) == "pt_BR"


def test_settings_apply_empty_gives_feedback():
    """tui-settings-locale-empty-no-feedback.

    Clicking Apply with a blank selection must update the message widget
    instead of doing nothing silently.
    """

    async def scenario() -> object:
        app = tui.FastSLRApp()
        async with app.run_test() as pilot:
            screen = tui.SettingsScreen()
            await app.push_screen(screen)
            await pilot.pause()
            await pilot.pause()
            select = screen.query_one("#lang_select", Select)
            select.clear()
            screen.query_one("#btn_apply", Button).press()
            await pilot.pause()
            return screen.query_one("#settings_msg", Static).render()

    text = str(_run(scenario()))
    assert "valid language" in text.lower()


def _captured_notifications(messages: list[str]):
    """Patch App.notify to capture notification text."""

    def _notify(self, message, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        messages.append(str(message))

    return _notify


def test_browse_terms_empty_path_notifies(monkeypatch):
    """tui-empty-input-silent-return (BrowseTermsScreen)."""
    captured: list[str] = []
    monkeypatch.setattr(tui.App, "notify", _captured_notifications(captured))

    async def scenario() -> None:
        app = tui.FastSLRApp()
        async with app.run_test() as pilot:
            screen = tui.BrowseTermsScreen()
            await app.push_screen(screen)
            await pilot.pause()
            await pilot.pause()
            screen.query_one("#btn_load", Button).press()
            await pilot.pause()

    _run(scenario())
    assert captured, "expected a warning notification for empty config path"
    assert any("config file" in m.lower() for m in captured)


def test_edit_config_empty_path_notifies(monkeypatch):
    """tui-empty-input-silent-return (EditConfigScreen)."""
    captured: list[str] = []
    monkeypatch.setattr(tui.App, "notify", _captured_notifications(captured))

    async def scenario() -> None:
        app = tui.FastSLRApp()
        async with app.run_test() as pilot:
            screen = tui.EditConfigScreen()
            await app.push_screen(screen)
            await pilot.pause()
            await pilot.pause()
            screen.query_one("#btn_load", Button).press()
            await pilot.pause()

    _run(scenario())
    assert any("config file" in m.lower() for m in captured)


def test_results_empty_path_notifies(monkeypatch):
    """tui-empty-input-silent-return (ResultsScreen)."""
    captured: list[str] = []
    monkeypatch.setattr(tui.App, "notify", _captured_notifications(captured))

    async def scenario() -> None:
        app = tui.FastSLRApp()
        async with app.run_test() as pilot:
            screen = tui.ResultsScreen()
            await app.push_screen(screen)
            await pilot.pause()
            await pilot.pause()
            screen.query_one("#btn_load", Button).press()
            await pilot.pause()

    _run(scenario())
    assert any("results file" in m.lower() for m in captured)


def test_results_filter_without_final_decision_notifies(monkeypatch, tmp_path):
    """tui-results-detail-cursor-row-empty.

    Selecting a decision filter on a file that has no ``Final_Decision``
    column must warn the user instead of silently showing every row.
    """
    captured: list[str] = []
    monkeypatch.setattr(tui.App, "notify", _captured_notifications(captured))

    df = pd.DataFrame({"ID": [1, 2], "Title": ["a", "b"]})
    monkeypatch.setattr(controller, "read_results_table", lambda _path: df)

    async def scenario() -> None:
        app = tui.FastSLRApp()
        async with app.run_test() as pilot:
            screen = tui.ResultsScreen()
            await app.push_screen(screen)
            await pilot.pause()
            await pilot.pause()
            screen.query_one("#results_path", Input).value = str(tmp_path / "x.csv")
            screen.query_one("#filter_decision", Select).value = "APPROVED_FINAL"
            screen.query_one("#btn_load", Button).press()
            await pilot.pause()

    _run(scenario())
    assert any("final_decision" in m.lower() for m in captured)
