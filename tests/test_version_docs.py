"""The docs that state the version a user installs or cites name ``VERSION``.

The 3.1.0 release reached PyPI with the README, which is the long description,
still titled "FastSLR v3.0.1", and the user guide's methods-section template
still citing v3.0.1. Nothing checked version strings in the docs, so they
drifted on the bump. CITATION.cff must also carry the CHANGELOG release date.

The sdist ships README.md but not CHANGELOG.md, CITATION.cff or docs/, so a
file that is absent is skipped: from the sdist the README is still checked.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from fastslr.core.constants import VERSION

ROOT = Path(__file__).resolve().parents[1]

# Every way the docs state the version a user installs or cites.
_VERSION_PATTERNS = (
    re.compile(r"FastSLR v(\d+\.\d+\.\d+)"),
    re.compile(r"fastslr==(\d+\.\d+\.\d+)"),
    re.compile(r"fastslr\.git@v(\d+\.\d+\.\d+)"),
)
_CURRENT_DOCS = ("README.md", "docs/GUIA_DO_USUARIO.md", "docs/TECHNICAL.md")


def _read(rel: str) -> str:
    path = ROOT / rel
    if not path.is_file():
        pytest.skip(f"{rel} is not shipped here (sdist)")
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize("rel", _CURRENT_DOCS)
def test_docs_name_the_current_version(rel: str) -> None:
    text = _read(rel)
    found = {m.group(1) for pattern in _VERSION_PATTERNS for m in pattern.finditer(text)}
    assert found, f"{rel} states no version"
    assert found == {VERSION}, f"{rel} states {sorted(found)}, VERSION is {VERSION}"


def test_citation_matches_version_and_changelog_date() -> None:
    cff = _read("CITATION.cff")
    changelog = _read("CHANGELOG.md")
    version = re.search(r"^version: (\S+)$", cff, re.MULTILINE)
    released = re.search(r"^date-released: (\S+)$", cff, re.MULTILINE)
    entry = re.search(
        rf"^## \[{re.escape(VERSION)}\] - (\d{{4}}-\d{{2}}-\d{{2}})$", changelog, re.MULTILINE
    )
    assert version is not None and version.group(1) == VERSION
    assert entry is not None, f"CHANGELOG.md has no entry for {VERSION}"
    assert released is not None and released.group(1) == entry.group(1)
