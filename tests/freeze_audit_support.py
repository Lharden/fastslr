"""Shared helpers for the pre-freeze audit regression tests (findings F01-F10).

The integration cases run the historical configuration of the review
(``fixtures/historical/config_v8.json`` + ``terms_final.csv``, byte-identical
copies of the files in RSL_Project ``data/revision/historical/
engine_reconstruction``) through the production path (``_prepare_config`` +
``process_articles``). The ``hist_config`` / ``hist_engine`` fixtures live in
``conftest.py``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from fastslr.core.engine import process_articles

HIST = Path(__file__).parent / "fixtures" / "historical"
CONFIG_V8 = HIST / "config_v8.json"
TERMS_FINAL = HIST / "terms_final.csv"


def run_rows(config: dict, rows: list[list[str]]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["key", "title", "abstract", "manual_tags"])
    result, _ = process_articles(df, config)
    return result.set_index("ID")


def highlighted_terms(cell: str) -> set[str]:
    return set(re.findall(r'term="([^"]*)"', cell or ""))


def write_terms(path: Path, rows: list[str]) -> Path:
    header = "block;kind;term;level;section_scope;is_regex;normalization_type;normalization_target"
    path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")
    return path


def write_config(path: Path) -> Path:
    """The historical config, writing xlsx with openpyxl."""
    cfg = json.loads(CONFIG_V8.read_text(encoding="utf-8"))
    cfg["output"]["xlsx_engine"] = "openpyxl"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    return path
