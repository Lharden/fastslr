"""Regression tests for package-data packaging and importlib.resources loading.

These tests guard against a packaging bug where the wheel shipped only ``.py``
files: ``i18n/locales/*.json`` and ``core/*.json`` were missing after
``pip install``, so the UI rendered raw translation keys instead of text.

The fix is twofold:
1. ``pyproject.toml`` declares ``[tool.setuptools.package-data]`` so the data
   files are bundled into the wheel.
2. ``fastslr.i18n`` loads locale files via ``importlib.resources`` (which works
   from inside a zip/installed package) instead of a ``__file__``-relative path.
"""

from __future__ import annotations

import importlib.resources as resources

import pytest

from fastslr import i18n


@pytest.mark.parametrize("locale_name", ["en", "pt_BR", "es"])
def test_locale_files_resolvable_via_importlib_resources(locale_name: str) -> None:
    """Each shipped locale JSON must resolve as a package resource."""
    res = resources.files("fastslr.i18n").joinpath("locales").joinpath(f"{locale_name}.json")
    assert res.is_file(), f"locale resource missing via importlib.resources: {locale_name}.json"


def test_core_default_config_resolvable_via_importlib_resources() -> None:
    """The core default_config.json must be bundled as a package resource."""
    res = resources.files("fastslr.core").joinpath("default_config.json")
    assert res.is_file(), "core/default_config.json missing via importlib.resources"


def test_py_typed_marker_present() -> None:
    """The py.typed marker must ship with the package."""
    res = resources.files("fastslr").joinpath("py.typed")
    assert res.is_file(), "py.typed marker missing via importlib.resources"


def test_translation_returns_text_not_key() -> None:
    """A known key must translate to real text (not echo the key back)."""
    i18n.set_locale("en")
    # "version_info" maps to "FastSLR v{version}" in en.json
    translated = i18n._("version_info", version="3.0.0")
    assert translated == "FastSLR v3.0.0"
    assert translated != "version_info"


def test_translation_localized_pt_br() -> None:
    """Switching to pt_BR must load that locale's strings, not echo the key."""
    i18n.set_locale("pt_BR")
    try:
        translated = i18n._("table_metric")
        # Whatever pt_BR maps it to, it must not be the raw key.
        assert translated != "table_metric"
    finally:
        i18n.set_locale("en")


def test_locale_loader_uses_importlib_resources(monkeypatch: pytest.MonkeyPatch) -> None:
    """The locale loader must source data through importlib.resources.

    We patch ``importlib.resources.files`` for the i18n package; if the loader
    relies on it, the strings come from our stub instead of the real file.
    This fails against the old ``__file__``-relative implementation.
    """
    import json

    sentinel = {"version_info": "STUBBED {version}"}

    class _FakeTraversable:
        def joinpath(self, *parts: str) -> _FakeTraversable:
            return self

        def read_text(self, encoding: str = "utf-8") -> str:
            return json.dumps(sentinel)

        def is_file(self) -> bool:
            return True

    real_files = resources.files

    def fake_files(pkg: str):
        if pkg == "fastslr.i18n":
            return _FakeTraversable()
        return real_files(pkg)

    monkeypatch.setattr(i18n.resources, "files", fake_files)
    loaded = i18n._load_locale_file("en")
    assert loaded == sentinel
