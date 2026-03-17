"""Save triagem.bat launcher profile from environment variables."""

from __future__ import annotations

import datetime
import json
import os
from pathlib import Path


PROFILE_TARGET_ENV = "RSL_PROFILE_TARGET"

PROFILE_KEYS = (
    "INPUT_PATH",
    "TERMS_PATH",
    "CONFIG_PATH",
    "OUTPUT_PATH",
    "RUN_LOG_PATH",
    "EXTRA_ARGS",
    "MODE_INTERACTIVE",
    "MODE_NO_PROGRESS",
    "MODE_NO_ACADEMIC",
    "MODE_NO_APPENDIX",
    "MODE_QUIET",
    "FORCE_UTF8",
    "SAMPLE_SIZE",
    "SAMPLE_SEED",
    "LOG_LEVEL",
)


def main() -> int:
    target = os.environ.get(PROFILE_TARGET_ENV, "").strip()
    if not target:
        return 2

    settings = {key: os.environ.get(key, "") for key in PROFILE_KEYS}
    profile = {
        "profile_version": 1,
        "launcher": "triagem.bat",
        "saved_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "settings": settings,
    }

    out_path = Path(target)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(profile, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
