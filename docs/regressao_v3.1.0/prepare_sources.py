"""Build the code trees for the 3.0.1 -> 3.1.0 regression on the 505 historical records.

Usage: python prepare_sources.py <repo> <out_dir> --base <ref> --merged <ref>

- <out_dir>/base/src: the src of the base (for 3.1.0: 4a66697, the 3.0.1 side of the merge);
- <out_dir>/merged/src: the src of the merged code;
- <out_dir>/loo_<module>/src: the merged src with ONE module put back to its base copy
  (leave-one-out attribution of the pre-IP audit changes).

A module the merge did not change is skipped and reported: undoing it would be a no-op.
"""

import argparse
import hashlib
import io
import shutil
import subprocess
import tarfile
from pathlib import Path

MODULES = [
    "core/normalization.py",
    "core/scoring.py",
    "core/config.py",
    "core/patterns.py",
    "core/io.py",
    "core/engine.py",
    "app/controller.py",
]


def extract(repo: Path, ref: str, dest: Path) -> str:
    sha = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", ref], capture_output=True, text=True, check=True
    ).stdout.strip()
    tar = subprocess.run(
        ["git", "-C", str(repo), "archive", sha, "src"], capture_output=True, check=True
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(tar)) as t:
        t.extractall(dest, filter="data")
    return sha


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("repo", type=Path)
    p.add_argument("out", type=Path)
    # Explicit refs: a default like HEAD^2 only means the 3.0.1 side while HEAD is the merge.
    p.add_argument("--base", required=True)
    p.add_argument("--merged", required=True)
    args = p.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} already exists")
    base_sha = extract(args.repo, args.base, args.out / "base")
    merged_sha = extract(args.repo, args.merged, args.out / "merged")
    print("base", args.base, base_sha)
    print("merged", args.merged, merged_sha)
    pkg = Path("src") / "fastslr"
    for module in MODULES:
        base_file = args.out / "base" / pkg / module
        merged_file = args.out / "merged" / pkg / module
        if digest(base_file) == digest(merged_file):
            print(f"skip {module}: unchanged by the merge")
            continue
        name = "loo_" + Path(module).stem
        shutil.copytree(args.out / "merged", args.out / name)
        shutil.copy2(base_file, args.out / name / pkg / module)
        print(f"{name}: {module} {digest(merged_file)} -> {digest(base_file)}")


if __name__ == "__main__":
    main()
