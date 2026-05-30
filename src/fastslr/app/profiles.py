"""Profile management — save, load, and list configuration profiles."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

PROFILES_DIR_NAME = "profiles"

_UNSAFE_NAME_CHARS = re.compile(r"[^a-z0-9_-]+")


def _profiles_dir() -> Path:
    """Return the cross-platform profiles directory (~/.fastslr/profiles/)."""
    base = Path.home() / ".fastslr" / PROFILES_DIR_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def _safe_profile_path(name: str, profiles_dir: Path) -> Path:
    """Sanitize ``name`` into a profile path confined to ``profiles_dir``.

    Strips path separators and unsafe characters, rejects names that sanitize
    to empty, and verifies the resolved path stays inside ``profiles_dir`` to
    prevent path-traversal escapes.
    """
    safe_name = _UNSAFE_NAME_CHARS.sub("_", name.strip().lower()).strip("_")
    if not safe_name:
        raise ValueError(f"Invalid profile name: {name!r}")

    profile_path = profiles_dir / f"{safe_name}.json"
    if not profile_path.resolve().is_relative_to(profiles_dir.resolve()):
        raise ValueError(f"Invalid profile name (path escape): {name!r}")

    return profile_path


@dataclass
class ProfileInfo:
    """Metadata about a saved profile."""

    name: str
    path: Path
    description: str = ""


def save_profile(name: str, config: dict, description: str = "") -> Path:
    """Save a configuration as a named profile."""
    profiles_dir = _profiles_dir()
    profile_path = _safe_profile_path(name, profiles_dir)

    payload = {
        "_profile_name": name,
        "_profile_description": description,
        **config,
    }

    profile_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    logger.info("Profile saved: %s", profile_path)
    return profile_path


def load_profile(name: str) -> dict:
    """Load a named profile and return the configuration dict."""
    profiles_dir = _profiles_dir()
    profile_path = _safe_profile_path(name, profiles_dir)

    if not profile_path.exists():
        raise FileNotFoundError(f"Profile not found: '{name}' (looked at {profile_path})")

    with open(profile_path, encoding="utf-8") as f:
        data = json.load(f)

    # Strip profile metadata before returning config
    data.pop("_profile_name", None)
    data.pop("_profile_description", None)
    return data


def list_profiles() -> list[ProfileInfo]:
    """List all saved profiles."""
    profiles_dir = _profiles_dir()
    profiles: list[ProfileInfo] = []

    for path in sorted(profiles_dir.glob("*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            profiles.append(
                ProfileInfo(
                    name=data.get("_profile_name", path.stem),
                    path=path,
                    description=data.get("_profile_description", ""),
                )
            )
        except (json.JSONDecodeError, OSError):
            profiles.append(ProfileInfo(name=path.stem, path=path))

    return profiles


def delete_profile(name: str) -> bool:
    """Delete a named profile. Returns True if deleted."""
    profiles_dir = _profiles_dir()
    profile_path = _safe_profile_path(name, profiles_dir)

    if profile_path.exists():
        profile_path.unlink()
        return True
    return False


__all__ = [
    "ProfileInfo",
    "save_profile",
    "load_profile",
    "list_profiles",
    "delete_profile",
]
