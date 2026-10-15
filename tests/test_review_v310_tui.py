"""Regressions for the v3.1.0 TUI review findings (tui.py).

1. ``input_warnings`` from ``process_articles`` reach the Run Triage summary.
2. The Run worker is exclusive, the button is disabled while it runs (and
   re-enabled on success or error), and widgets are only queried on the UI
   thread.
3. Paths pasted with quotes (Windows "Copy as path") are cleaned in every
   path field.
"""

from __future__ import annotations

import asyncio
import inspect
import threading
from collections.abc import Awaitable
from pathlib import Path
from types import SimpleNamespace
from typing import Any, TypeVar

import pandas as pd
import pytest
from textual.widgets import Button, Input, Static

from fastslr.app import controller, tui

_T = TypeVar("_T")


def _run(coro: Awaitable[_T]) -> _T:
    return asyncio.run(coro)  # type: ignore[arg-type]


def _fake_result(tmp_path: Path, warnings: list[str] | None = None) -> Any:
    stats: dict[str, Any] = {
        "decision_distribution": {"APPROVED_FINAL": 1},
        "total_articles": 1,
        "processing_time": 0.1,
    }
    if warnings is not None:
        stats["input_warnings"] = warnings
    return SimpleNamespace(stats=stats, output_dir=tmp_path)


def _files(tmp_path: Path) -> tuple[Path, Path]:
    articles = tmp_path / "a.csv"
    config = tmp_path / "c.json"
    articles.write_text("x\n", encoding="utf-8")
    config.write_text("{}", encoding="utf-8")
    return articles, config


async def _fill_and_press(app, screen, pilot, articles: str, config: str) -> None:  # noqa: ANN001
    """Fill the Run screen, press Run and wait, up to 2 s, until the press was handled.

    ``press()`` only posts ``Button.Pressed``, and one pause does not always let
    the handler run under the load of the full suite. When it had not run,
    ``wait_for_complete()`` found no worker and returned at once, and the test
    read an empty ``#results`` (about 1 full run in 5). The worker writes
    ``#status`` before anything else, on every path, so a non-empty status
    proves that the handler ran and the worker exists.
    """
    await app.push_screen(screen)
    await pilot.pause()
    screen.query_one("#input_file", Input).value = articles
    screen.query_one("#config_file", Input).value = config
    screen.query_one("#btn_run", Button).press()
    status = screen.query_one("#status", Static)
    for _ in range(200):
        if str(status.render()):
            return
        await pilot.pause(0.01)
    raise AssertionError("the Run press was never handled: #status stayed empty for 2 s")


async def _until_enabled(button: Button, pilot) -> bool:  # noqa: ANN001
    """Wait, up to 2 s, for the worker's call_from_thread to re-enable *button*.

    One pause is not always enough under the load of the full suite, and a test
    that reads the button right after it fails at random.
    """
    for _ in range(200):
        if not button.disabled:
            break
        await pilot.pause(0.01)
    await pilot.pause()  # let the other widgets the worker updated refresh too
    return button.disabled


# -- 3. helper ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('"C:\\x\\a.csv"', "C:\\x\\a.csv"),
        ("'/tmp/a.csv'", "/tmp/a.csv"),
        ('  "C:\\x y\\a.csv"  ', "C:\\x y\\a.csv"),
        ("  plain.csv ", "plain.csv"),
        ("", ""),
        ('"', '"'),
        ("\"mixed'", "\"mixed'"),
    ],
)
def test_clean_path_strips_spaces_and_one_pair_of_quotes(raw: str, expected: str) -> None:
    assert tui._clean_path(raw) == expected


def test_run_screen_passes_unquoted_paths_to_controller(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    articles, config = _files(tmp_path)
    seen: dict[str, Any] = {}

    def fake_run(**kw: Any) -> Any:
        seen.update(kw)
        return _fake_result(tmp_path)

    monkeypatch.setattr(controller, "run_triage", fake_run)

    async def scenario() -> None:
        app = tui.FastSLRApp()
        async with app.run_test() as pilot:
            await _fill_and_press(app, tui.RunTriageScreen(), pilot, f'"{articles}"', f"'{config}'")
            await app.workers.wait_for_complete()

    _run(scenario())
    assert seen["input_path"] == articles
    assert seen["config_path"] == config


def test_coverage_diff_export_results_strip_quotes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: dict[str, Any] = {}
    monkeypatch.setattr(tui.App, "notify", lambda self, *a, **k: None)

    def cov(**kw: Any) -> object:
        calls["coverage"] = kw
        return object()

    monkeypatch.setattr(controller, "analyze_coverage", cov)
    monkeypatch.setattr(controller, "format_coverage", lambda r: "ok")

    def diff(a: Path, b: Path) -> Any:
        calls["diff"] = (a, b)
        return SimpleNamespace(changed=[], total_a=0, total_b=0)

    monkeypatch.setattr(controller, "diff_results", diff)

    def export(**kw: Any) -> Path:
        calls["export"] = kw
        return tmp_path / "p.zip"

    monkeypatch.setattr(controller, "export_academic_package", export)

    def read(p: Path) -> pd.DataFrame:
        calls["results"] = p
        return pd.DataFrame({"Final_Decision": ["APPROVED_FINAL"], "Article_ID": ["1"]})

    monkeypatch.setattr(controller, "read_results_table", read)

    def quoted(name: str) -> str:
        return f'"C:\\q\\{name}"'

    async def scenario() -> None:
        app = tui.FastSLRApp()
        async with app.run_test() as pilot:

            async def go(screen: Any, values: dict[str, str], button: str) -> None:
                await app.push_screen(screen)
                await pilot.pause()
                for wid, val in values.items():
                    screen.query_one(f"#{wid}", Input).value = val
                screen.query_one(f"#{button}", Button).press()
                await pilot.pause()
                await pilot.pause()

            await go(
                tui.CoverageScreen(),
                {
                    "input_file": quoted("a.csv"),
                    "config_file": quoted("c.json"),
                    "terms_file": quoted("t.csv"),
                },
                "btn_analyze",
            )
            await go(
                tui.DiffScreen(),
                {"file_a": quoted("a.xlsx"), "file_b": quoted("b.xlsx")},
                "btn_compare",
            )
            await go(
                tui.ExportScreen(),
                {
                    "result_file": quoted("r.xlsx"),
                    "output_dir": quoted("out"),
                    "config_file": quoted("c.json"),
                },
                "btn_export",
            )
            await go(tui.ResultsScreen(), {"results_path": quoted("r.xlsx")}, "btn_load")

    _run(scenario())
    c = calls["coverage"]
    assert (c["input_path"], c["config_path"], c["terms_path"]) == (
        Path("C:\\q\\a.csv"),
        Path("C:\\q\\c.json"),
        Path("C:\\q\\t.csv"),
    )
    assert calls["diff"] == (Path("C:\\q\\a.xlsx"), Path("C:\\q\\b.xlsx"))
    e = calls["export"]
    assert (e["result_path"], e["output_dir"], e["config_path"]) == (
        Path("C:\\q\\r.xlsx"),
        Path("C:\\q\\out"),
        Path("C:\\q\\c.json"),
    )
    assert calls["results"] == Path("C:\\q\\r.xlsx")


# -- 1. input_warnings -------------------------------------------------------


def test_run_summary_shows_every_input_warning(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    articles, config = _files(tmp_path)
    warnings = ["WARN-ALPHA keywords column missing", "WARN-BETA second"]
    monkeypatch.setattr(controller, "run_triage", lambda **_kw: _fake_result(tmp_path, warnings))

    async def scenario() -> str:
        app = tui.FastSLRApp()
        async with app.run_test() as pilot:
            screen = tui.RunTriageScreen()
            await _fill_and_press(app, screen, pilot, str(articles), str(config))
            await app.workers.wait_for_complete()
            await pilot.pause()
            return str(screen.query_one("#results", Static).render())

    text = _run(scenario())
    assert "WARN-ALPHA keywords column missing" in text
    assert "WARN-BETA second" in text


def test_run_summary_without_warnings_still_renders(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    articles, config = _files(tmp_path)
    monkeypatch.setattr(controller, "run_triage", lambda **_kw: _fake_result(tmp_path, []))

    async def scenario() -> str:
        app = tui.FastSLRApp()
        async with app.run_test() as pilot:
            screen = tui.RunTriageScreen()
            await _fill_and_press(app, screen, pilot, str(articles), str(config))
            await app.workers.wait_for_complete()
            await pilot.pause()
            return str(screen.query_one("#results", Static).render())

    assert "APPROVED: 1" in _run(scenario())


# -- 2. exclusivity, button state, thread safety -----------------------------


def test_double_press_runs_triage_once_and_button_is_reenabled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    articles, config = _files(tmp_path)
    release = threading.Event()
    started = threading.Event()
    count = 0

    def slow_run(**_kw: Any) -> Any:
        nonlocal count
        count += 1
        started.set()
        release.wait(timeout=10)
        return _fake_result(tmp_path)

    monkeypatch.setattr(controller, "run_triage", slow_run)

    async def scenario() -> tuple[bool, bool]:
        app = tui.FastSLRApp()
        async with app.run_test() as pilot:
            screen = tui.RunTriageScreen()
            await _fill_and_press(app, screen, pilot, str(articles), str(config))
            for _ in range(200):
                if started.is_set():
                    break
                await pilot.pause(0.01)
            btn = screen.query_one("#btn_run", Button)
            disabled_while_running = btn.disabled
            screen.start_triage()  # second "click" while the first still runs
            await pilot.pause()
            release.set()
            await app.workers.wait_for_complete()
            return disabled_while_running, await _until_enabled(btn, pilot)

    disabled_while_running, disabled_after = _run(scenario())
    assert disabled_while_running is True
    assert disabled_after is False
    assert count == 1


def test_button_reenabled_after_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    articles, config = _files(tmp_path)

    def boom(**_kw: Any) -> Any:
        raise RuntimeError("boom")

    monkeypatch.setattr(controller, "run_triage", boom)

    async def scenario() -> tuple[bool, str]:
        app = tui.FastSLRApp()
        async with app.run_test() as pilot:
            screen = tui.RunTriageScreen()
            await _fill_and_press(app, screen, pilot, str(articles), str(config))
            await app.workers.wait_for_complete()
            disabled = await _until_enabled(screen.query_one("#btn_run", Button), pilot)
            return disabled, str(screen.query_one("#status", Static).render())

    disabled, status = _run(scenario())
    assert disabled is False
    assert "boom" in status


def test_button_reenabled_after_missing_file(tmp_path: Path) -> None:
    async def scenario() -> bool:
        app = tui.FastSLRApp()
        async with app.run_test() as pilot:
            screen = tui.RunTriageScreen()
            await _fill_and_press(
                app, screen, pilot, str(tmp_path / "no.csv"), str(tmp_path / "no.json")
            )
            await app.workers.wait_for_complete()
            return await _until_enabled(screen.query_one("#btn_run", Button), pilot)

    assert _run(scenario()) is False


def test_worker_never_queries_widgets_off_the_ui_thread(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    articles, config = _files(tmp_path)
    monkeypatch.setattr(controller, "run_triage", lambda **_kw: _fake_result(tmp_path))
    idents: list[int] = []
    original = tui.RunTriageScreen.query_one

    def spy(self: Any, *args: Any, **kwargs: Any) -> Any:
        idents.append(threading.get_ident())
        return original(self, *args, **kwargs)

    monkeypatch.setattr(tui.RunTriageScreen, "query_one", spy)

    async def scenario() -> int:
        app = tui.FastSLRApp()
        async with app.run_test() as pilot:
            screen = tui.RunTriageScreen()
            await _fill_and_press(app, screen, pilot, str(articles), str(config))
            await app.workers.wait_for_complete()
            await pilot.pause()
            return threading.get_ident()

    ui = _run(scenario())
    assert idents
    assert set(idents) == {ui}


def test_run_worker_is_exclusive_thread_worker() -> None:
    # The behavioural guard is the button state above; this pins the decorator.
    assert "@work(thread=True, exclusive=True)" in inspect.getsource(tui.RunTriageScreen)
