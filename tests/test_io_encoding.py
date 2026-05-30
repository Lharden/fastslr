"""Regression tests for deterministic encoding detection/fallback on table reads.

These tests cover the fix for the masked ``UnicodeDecodeError`` bug: when
``chardet`` is absent, ``_detect_encoding`` previously always returned
``"utf-8"`` and a CSV in cp1252/latin-1 with accents failed to load, surfacing
only a generic "Unable to load delimited table" message.

The fix introduces a deterministic fallback chain
(``utf-8-sig`` -> ``utf-8`` -> ``cp1252`` -> ``latin-1``) that works without
chardet, honours a configured encoding first, and reports the attempted
encodings on failure.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fastslr.core import io as io_module
from fastslr.core.io import load_table_safe


def _write_bytes(path: Path, text: str, encoding: str) -> None:
    path.write_bytes(text.encode(encoding))


def test_cp1252_csv_loads_without_chardet(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A cp1252 CSV with accents must load correctly even when chardet is absent."""
    # Force the chardet-less code path (deterministic fallback must be the guarantor).
    monkeypatch.setattr(io_module, "chardet", None)

    csv_path = tmp_path / "accents_cp1252.csv"
    content = "title;abstract;keywords\nCafé;Über;naïve\n"
    _write_bytes(csv_path, content, "cp1252")

    df = load_table_safe(csv_path, min_columns=3)

    assert list(df.columns) == ["title", "abstract", "keywords"]
    assert df.iloc[0]["title"] == "Café"
    assert df.iloc[0]["abstract"] == "Über"
    assert df.iloc[0]["keywords"] == "naïve"


def test_latin1_csv_loads_without_chardet(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """latin-1 content (which never raises on decode) must round-trip via fallback."""
    monkeypatch.setattr(io_module, "chardet", None)

    csv_path = tmp_path / "accents_latin1.csv"
    content = "title;abstract;keywords\nCafé;Über;naïve\n"
    _write_bytes(csv_path, content, "latin-1")

    df = load_table_safe(csv_path, min_columns=3)

    assert df.iloc[0]["title"] == "Café"
    assert df.iloc[0]["keywords"] == "naïve"


def test_utf8_sig_csv_loads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A UTF-8 file with BOM must load without a leading BOM glyph in the first column."""
    monkeypatch.setattr(io_module, "chardet", None)

    csv_path = tmp_path / "bom_utf8sig.csv"
    content = "title;abstract;keywords\nCafé;Über;naïve\n"
    _write_bytes(csv_path, content, "utf-8-sig")

    df = load_table_safe(csv_path, min_columns=3)

    # The BOM must be stripped: first column name is clean "title", not "﻿title".
    assert list(df.columns) == ["title", "abstract", "keywords"]
    assert df.iloc[0]["title"] == "Café"


def test_plain_utf8_csv_loads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Plain UTF-8 with multibyte accents must load correctly."""
    monkeypatch.setattr(io_module, "chardet", None)

    csv_path = tmp_path / "plain_utf8.csv"
    content = "title;abstract;keywords\nCafé;Über;naïve\n"
    _write_bytes(csv_path, content, "utf-8")

    df = load_table_safe(csv_path, min_columns=3)

    assert df.iloc[0]["abstract"] == "Über"


def test_configured_encoding_is_prioritized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the caller supplies an encoding, it must be tried first."""
    monkeypatch.setattr(io_module, "chardet", None)

    csv_path = tmp_path / "configured.csv"
    content = "title;abstract;keywords\nCafé;Über;naïve\n"
    _write_bytes(csv_path, content, "cp1252")

    df = load_table_safe(csv_path, min_columns=3, encoding="cp1252")

    assert df.iloc[0]["title"] == "Café"
