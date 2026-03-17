"""Stable Python entrypoint for triagem.bat fallback mode."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    src_path = (Path.cwd() / "src").resolve()
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    from fastslr.cli import main as cli_main

    return int(cli_main())


if __name__ == "__main__":
    raise SystemExit(main())
