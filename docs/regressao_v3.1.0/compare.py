"""Compare the 3.0.1 base and the merged 3.1.0 on a corpus and attribute every difference.

Usage: python compare.py <out_dir> <report_dir> [--reference <dir>]
                         [--variants kw nokw] [--rows 505]

<out_dir> holds the runs of run_all.py: base_<variant>, merged_<variant> and
loo_<module>_<variant>. The defaults are the two inputs of the 505 historical records of RSL1.
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


ROWS = 505


def load(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path / "triage_results.xlsx", dtype=str, keep_default_na=False)
    assert df["ID"].is_unique and len(df) == ROWS, (path, len(df))
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
    p.add_argument("--variants", nargs="+", default=["kw", "nokw"])
    p.add_argument("--rows", type=int, default=505, help="records expected in every run")
    args = p.parse_args()
    global ROWS
    ROWS = args.rows
    census = args.out / "run_all.json"
    if not census.exists():
        raise SystemExit(f"{census} is missing: run run_all.py, which records what it was asked")
    trees = sorted(
        t.removeprefix("loo_")
        for t in json.loads(census.read_text(encoding="utf-8"))["trees"]
        if t.startswith("loo_")
    )

    def ran(tree: str) -> bool:
        return all(
            (args.out / f"loo_{tree}_{kw}" / "triage_results.xlsx").exists() for kw in args.variants
        )

    # A module whose base copy cannot run with the merged code (it lacks a name another
    # module imports now) cannot be undone alone: it is reported, never silently dropped.
    modules = [m for m in trees if ran(m)]
    summary: dict[str, Any] = {
        "modules": modules,
        "modules_not_run": sorted(set(trees) - set(modules)),
    }
    print("modules undone:", modules, "| could not run alone:", summary["modules_not_run"])
    for kw in args.variants:
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
    for kw in args.variants:
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
