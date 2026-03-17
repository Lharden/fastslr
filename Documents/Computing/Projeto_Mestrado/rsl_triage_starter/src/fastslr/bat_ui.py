"""Interactive menu UI for triagem.bat launcher."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    """Entry point called by triagem.bat."""
    # Ensure src is on path
    src_path = (Path(__file__).resolve().parent.parent).resolve()
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    from fastslr.cli import main as cli_main

    return int(cli_main())


if __name__ == "__main__":
    raise SystemExit(main())
