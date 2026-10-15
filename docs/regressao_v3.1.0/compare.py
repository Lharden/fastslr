"""Compare the 3.0.1 base and the merged 3.1.0 on the 505 records and attribute every difference.

Usage: python compare.py <out_dir> <report_dir> [--reference <dir>]

<out_dir> holds the runs of run_all.py: base_<kw>, merged_<kw> and loo_<module>_<kw>.
--reference points to the folder of the 3.0.1 regression runs (with fixed_kw/ and fixed_nokw/):
the base must give exactly the same cells, or the instrument is not the one of 2026-10-10.

Attribution (leave-one-out): for a field that changed between base and merged, module X is a
cause when the merged code with ONLY X put back to its base copy gives the base value again. A
field no single module explains is an interaction, with the modules whose revert moves it at all.
Cells are compared as written, row numbers included: F05 is in both sides.
"""

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

BLOCKS = ["T1A", "T1B", "T1C"]
STATUS = ["Status_T0"] + [f"Status_{b}" for b in BLOCKS] + ["Final_Decision"]
IGNORE = {"run_timestamp", "triage_version"}


def load(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path / "triage_results.xlsx", dtype=str, keep_default_na=False)
    assert df["ID"].is_unique and len(df) == 505, path
    return df.set_index("ID")


def differing_cells(a: pd.DataFrame, b: pd.DataFrame) -> list[tuple[str, str]]:
    cols = [c for c in a.columns if c not in IGNORE]
    assert list(a.index) == list(b.index) and set(cols) <= set(b.columns)
    return [(rid, col) for rid in a.index for col in cols if a.at[rid, col] != b.at[rid, col]]


def kind(changed: dict) -> str:
    if any(k in changed for k in STATUS):
        return "decision_or_status"
    if any(k.startswith(("FinalScore_", "RawScore_", "BestLevel_")) for k in changed):
        return "score_only"
    if any(k.startswith(("Highlights_", "AntiHighlights_", "Flags_")) for k in changed):
        return "matches_only"
    return "display_only"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("out", type=Path)
    p.add_argument("report", type=Path)
    p.add_argument("--reference", type=Path)
    args = p.parse_args()
    modules = sorted(
        {d.name.removeprefix("loo_").rsplit("_", 1)[0] for d in args.out.glob("loo_*_kw")}
    )
    summary: dict[str, Any] = {"modules": modules}
    for kw in ("kw", "nokw"):
        base, merged = load(args.out / f"base_{kw}"), load(args.out / f"merged_{kw}")
        loo = {m: load(args.out / f"loo_{m}_{kw}") for m in modules}
        instrument = None
        if args.reference:
            ref = load(args.reference / f"fixed_{kw}")
            instrument = {"reference_cells_differing": len(differing_cells(ref, base))}
        records: dict[str, dict] = {}
        for rid, col in differing_cells(base, merged):
            b, f = base.at[rid, col], merged.at[rid, col]
            causes = [m for m in modules if loo[m].at[rid, col] == b]
            movers = [m for m in modules if loo[m].at[rid, col] != f]
            records.setdefault(rid, {})[col] = {
                "before": b,
                "after": f,
                "causes": causes,
                "interaction": [] if causes else movers,
            }
        rows = [
            {
                "ID": rid,
                "title": base.at[rid, "Title"] if "Title" in base.columns else "",
                "kind": kind(ch),
                "changed": ch,
            }
            for rid, ch in records.items()
        ]
        summary[kw] = {
            "distribution_before": base["Final_Decision"].value_counts().to_dict(),
            "distribution_after": merged["Final_Decision"].value_counts().to_dict(),
            "instrument_check": instrument,
            "records_changed": len(rows),
            "by_kind": pd.Series([r["kind"] for r in rows]).value_counts().to_dict()
            if rows
            else {},
            "unexplained_fields": [
                (r["ID"], col)
                for r in rows
                for col, d in r["changed"].items()
                if not d["causes"] and not d["interaction"]
            ],
            "records": rows,
        }
    args.report.mkdir(parents=True, exist_ok=True)
    (args.report / "regression_detail.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False, default=str), encoding="utf-8"
    )
    for kw in ("kw", "nokw"):
        s = summary[kw]
        print(f"=== {kw}")
        for key in (
            "distribution_before",
            "distribution_after",
            "instrument_check",
            "records_changed",
            "by_kind",
            "unexplained_fields",
        ):
            print(f"  {key}: {s[key]}")
        for r in s["records"]:
            parts = [
                f"{c}: {d['before'][:60]} -> {d['after'][:60]} "
                f"[{','.join(d['causes']) or 'interaction:' + ','.join(d['interaction'])}]"
                for c, d in r["changed"].items()
            ]
            print("   ", r["ID"], r["kind"], "; ".join(parts))


if __name__ == "__main__":
    main()
