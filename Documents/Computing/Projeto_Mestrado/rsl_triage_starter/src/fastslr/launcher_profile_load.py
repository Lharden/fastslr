"""Load triagem.bat launcher profile from a JSON file."""

from __future__ import annotations

import json
import os
from pathlib import Path


PROFILE_SOURCE_ENV = "RSL_PROFILE_SOURCE"


def main() -> int:
    """Load a saved profile and set environment variables."""
    source = os.environ.get(PROFILE_SOURCE_ENV, "").strip()
    if not source:
        return 2

    source_path = Path(source)
    if not source_path.exists():
        return 1

    try:
        profile = json.loads(source_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return 1

    settings = profile.get("settings", {})
    for key, value in settings.items():
        if value:
            os.environ[key] = str(value)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
