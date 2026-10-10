"""Compare v3.0.0 vs fixed runs on the 505 records and attribute every difference.

Usage: python compare.py <out_root> <audit_run_original.csv> <report_dir>

Attribution (leave-one-out): for a field that changed between v3.0.0 and the
fixed run, fix X is a cause when the fixed code with ONLY X reverted gives the
v3.0.0 value back. A field no single revert explains is reported as an
interaction, with the fixes whose revert moves it at all.
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd

OUT, AUDIT_BASE, REPORT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
FIXES = ["F01", "F02", "F03", "F04", "F06"]
BLOCKS = ["T1A", "T1B", "T1C"]
STATUS = ["Status_T0"] + [f"Status_{b}" for b in BLOCKS] + ["Final_Decision"]
IGNORE = {"run_timestamp", "triage_version"}
ROW_RE = re.compile(r"(row=|:)(\d+|None)(?=( type=|\||$))")


def load(name: str) -> pd.DataFrame:
    df = pd.read_excel(OUT / name / "triage_results.xlsx", dtype=str, keep_default_na=False)
    assert df["ID"].is_unique and len(df) == 505, name
    return df.set_index("ID")


def parse_hl(cell: str) -> dict:
    """Highlights cell -> {(term, sec, L, type, comps): row}."""
    out = {}
    for item in filter(None, (s.strip() for s in cell.split(" | "))):
        m = re.match(r'term=(".*?") sec=(\S+) L=(\S+) row=(\S+) type=(\S+)(?: comps=(.*))?$', item)
        assert m, item
        out[(json.loads(m[1]), m[2], m[3], m[5], m[6] or "")] = m[4]
    return out


def parse_anti(cell: str) -> dict:
    """AntiHighlights/Flags cell 'term:sec:row|...' -> {(term, sec): row}."""
    out = {}
    for item in filter(None, cell.split("|")):
        term, sec, row = item.rsplit(":", 2)
        out[(term, sec)] = row
    return out


def shift_check(old: dict, new: dict, bad: list, rid: str, col: str) -> int:
    n = 0
    for key in old.keys() & new.keys():
        o, w = old[key], new[key]
        n += 1
        if o == "None" and w == "None":
            continue
        if o == "None" or w == "None" or int(w) != int(o) + 2:
            bad.append((rid, col, key, o, w))
    return n


def norm_field(col: str, val: str):
    """Comparable form of a cell with the row numbers taken out."""
    if col.startswith("Highlights_"):
        return frozenset(parse_hl(val))
    if col.startswith(("AntiHighlights_", "Flags_")):
        return frozenset(parse_anti(val))
    return val


summary = {}
for kw in ("kw", "nokw"):
    base, fixed = load(f"v300_{kw}"), load(f"fixed_{kw}")
    loo = {x: load(f"loo_{x}_{kw}") for x in FIXES}
    assert list(base.index) == list(fixed.index)
    cols = [c for c in base.columns if c not in IGNORE]
    assert set(cols) <= set(fixed.columns), set(cols) - set(fixed.columns)

    # instrument check against the audit's own v3.0.0 baseline (with keywords)
    instrument = None
    if kw == "kw":
        aud = pd.read_csv(AUDIT_BASE, sep=";", dtype=str, keep_default_na=False).set_index("ID")
        common = [c for c in STATUS if c in aud.columns]
        mism = int((aud.loc[base.index, common] != base[common]).any(axis=1).sum())
        instrument = {"audit_rows": len(aud), "compared_cols": common, "mismatched_records": mism}

    # F05: every matched term keeps its identity and its row moves by +2
    bad_rows: list = []
    n_rows_checked = 0
    for rid in base.index:
        for col in cols:
            if col.startswith("Highlights_"):
                n_rows_checked += shift_check(
                    parse_hl(base.at[rid, col]), parse_hl(fixed.at[rid, col]), bad_rows, rid, col
                )
            elif col.startswith(("AntiHighlights_", "Flags_")):
                n_rows_checked += shift_check(
                    parse_anti(base.at[rid, col]), parse_anti(fixed.at[rid, col]), bad_rows, rid, col
                )

    records = []
    for rid in base.index:
        changed = {}
        for col in cols:
            b, f = norm_field(col, base.at[rid, col]), norm_field(col, fixed.at[rid, col])
            if b != f:
                causes = [x for x in FIXES if norm_field(col, loo[x].at[rid, col]) == b]
                movers = [x for x in FIXES if norm_field(col, loo[x].at[rid, col]) != f]
                if isinstance(b, frozenset):
                    detail = {
                        "removed": sorted(map(str, b - f)),
                        "added": sorted(map(str, f - b)),
                    }
                else:
                    detail = {"before": b, "after": f}
                changed[col] = {
                    **detail,
                    "causes": causes,
                    "interaction": [] if causes else movers,
                }
        if changed:
            records.append({"ID": rid, "changed": changed})

    def kind(rec):
        c = rec["changed"]
        if any(k in c for k in STATUS):
            return "decision_or_status"
        if any(k.startswith(("FinalScore_", "RawScore_", "BestLevel_")) for k in c):
            return "score_only"
        if any(k.startswith(("Highlights_", "AntiHighlights_", "Flags_")) for k in c):
            return "matches_only"
        return "display_only"

    for r in records:
        r["kind"] = kind(r)
        r["title"] = ""
    unexplained = [
        (r["ID"], col)
        for r in records
        for col, d in r["changed"].items()
        if not d["causes"] and not d["interaction"]
    ]
    summary[kw] = {
        "distribution_before": base["Final_Decision"].value_counts().to_dict(),
        "distribution_after": fixed["Final_Decision"].value_counts().to_dict(),
        "instrument_check": instrument,
        "f05_rows_checked": n_rows_checked,
        "f05_row_violations": bad_rows[:20],
        "f05_row_violation_count": len(bad_rows),
        "records_changed": len(records),
        "by_kind": pd.Series([r["kind"] for r in records]).value_counts().to_dict()
        if records
        else {},
        "unexplained_fields": unexplained,
        "records": records,
    }

REPORT.mkdir(parents=True, exist_ok=True)
(REPORT / "regression_detail.json").write_text(
    json.dumps(summary, indent=1, ensure_ascii=False, default=str), encoding="utf-8"
)
for kw, s in summary.items():
    print(f"=== {kw}")
    for k in (
        "distribution_before",
        "distribution_after",
        "instrument_check",
        "f05_rows_checked",
        "f05_row_violation_count",
        "records_changed",
        "by_kind",
        "unexplained_fields",
    ):
        print(f"  {k}: {s[k]}")
    for r in s["records"]:
        if r["kind"] == "decision_or_status":
            parts = [
                f"{c}: {d['before']} -> {d['after']} [{','.join(d['causes']) or 'interaction:' + ','.join(d['interaction'])}]"
                for c, d in r["changed"].items()
                if c in STATUS
            ]
            print("   ", r["ID"], "; ".join(parts))
