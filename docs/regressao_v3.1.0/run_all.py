"""Run every code tree of prepare_sources.py on both 505-record inputs, through the production path.

Usage: python run_all.py <sources_dir> <inputs_dir> <config_v8.json> <terms_final.csv> <out_dir>

Each run is ../regressao_v3.0.1/run_one.py with no revert: <out_dir>/<tree>_<kw|nokw>/. A run that
fails is reported and the others go on; compare.py then refuses to attribute without it.
"""

import subprocess
import sys
from pathlib import Path

RUN_ONE = Path(__file__).resolve().parent.parent / "regressao_v3.0.1" / "run_one.py"


def main() -> None:
    sources, inputs, config, terms, out = (Path(a) for a in sys.argv[1:6])
    trees = sorted(d.name for d in sources.iterdir() if (d / "src").is_dir())
    failed = []
    for tree in trees:
        for kw in ("kw", "nokw"):
            dest = out / f"{tree}_{kw}"
            cmd = [
                sys.executable,
                "-I",
                str(RUN_ONE),
                str(sources / tree / "src"),
                str(inputs / f"fc505_{kw}.csv"),
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


if __name__ == "__main__":
    main()
