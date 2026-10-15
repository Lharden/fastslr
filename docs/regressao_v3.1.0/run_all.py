"""Run every code tree of prepare_sources.py on every input variant, through the production path.

Usage: python run_all.py <sources_dir> <inputs_dir> <config.json> <terms.csv> <out_dir>
                         [--variant NAME=FILE ...]

Each run is ../regressao_v3.0.1/run_one.py with no revert: <out_dir>/<tree>_<variant>/. The default
variants are kw=fc505_kw.csv and nokw=fc505_nokw.csv, the two inputs of the 505 historical records.
A run that fails is reported and the others go on; compare.py names the tree that did not run.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

RUN_ONE = Path(__file__).resolve().parent.parent / "regressao_v3.0.1" / "run_one.py"


def main() -> None:
    p = argparse.ArgumentParser()
    for name in ("sources", "inputs", "config", "terms", "out"):
        p.add_argument(name, type=Path)
    p.add_argument("--variant", action="append", metavar="NAME=FILE")
    args = p.parse_args()
    sources, inputs, config, terms, out = (
        args.sources,
        args.inputs,
        args.config,
        args.terms,
        args.out,
    )
    variants = dict(
        v.split("=", 1) for v in args.variant or ["kw=fc505_kw.csv", "nokw=fc505_nokw.csv"]
    )
    trees = sorted(d.name for d in sources.iterdir() if (d / "src").is_dir())
    failed = []
    for tree in trees:
        for kw, filename in variants.items():
            dest = out / f"{tree}_{kw}"
            cmd = [
                sys.executable,
                "-I",
                str(RUN_ONE),
                str(sources / tree / "src"),
                str(inputs / filename),
                str(config),
                str(terms),
                str(dest),
            ]
            r = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
            )
            last = (r.stdout.strip().splitlines() or [""])[0]
            print(f"{tree}_{kw}: exit {r.returncode} {last}")
            if r.returncode != 0:
                failed.append(f"{tree}_{kw}")
                print(r.stderr[-2000:])
    print("failed:", failed or "none")
    # The census of what was asked: a run that died before creating its folder is
    # invisible to a glob, and compare.py must name it instead of skipping it.
    out.mkdir(parents=True, exist_ok=True)
    (out / "run_all.json").write_text(
        json.dumps({"trees": trees, "variants": variants, "failed": failed}, indent=1),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
