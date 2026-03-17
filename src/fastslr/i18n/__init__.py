"""FastSLR i18n — internationalization support via JSON locale files.

Usage:
    from fastslr.i18n import _, set_locale

    set_locale("pt_BR")
    print(_("version_info", version="3.0.0"))  # "FastSLR v3.0.0"

Translation strings support ``{key}`` placeholders for runtime substitution.
If a key is not found in the active locale, the English fallback is used.
If the key is missing everywhere, the key itself is returned.
"""

from __future__ import annotations

import json
import locale
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

LOCALES_DIR = Path(__file__).parent / "locales"
SUPPORTED_LOCALES = ("en", "pt_BR", "es")
DEFAULT_LOCALE = "en"

_current_locale: str = DEFAULT_LOCALE
_strings: dict[str, str] = {}
_fallback: dict[str, str] = {}


def _load_locale_file(locale_name: str) -> dict[str, str]:
    """Load a JSON locale file and return its string dict."""
    path = LOCALES_DIR / f"{locale_name}.json"
    if not path.exists():
        logger.warning("Locale file not found: %s", path)
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def set_locale(locale_name: str) -> None:
    """Set the active locale. Falls back to 'en' if locale not found."""
    global _current_locale, _strings, _fallback

    _fallback = _load_locale_file(DEFAULT_LOCALE)

    if locale_name in SUPPORTED_LOCALES:
        _current_locale = locale_name
        _strings = _load_locale_file(locale_name)
    else:
        # Try matching just the language part (e.g., "pt" → "pt_BR")
        lang = locale_name.split("_")[0].lower()
        matched = None
        for supported in SUPPORTED_LOCALES:
            if supported.lower().startswith(lang):
                matched = supported
                break

        if matched:
            _current_locale = matched
            _strings = _load_locale_file(matched)
        else:
            logger.warning("Unsupported locale '%s', using '%s'", locale_name, DEFAULT_LOCALE)
            _current_locale = DEFAULT_LOCALE
            _strings = _fallback


def get_locale() -> str:
    """Return the current active locale."""
    return _current_locale


def detect_locale() -> str:
    """Detect the best locale from environment.

    Priority: FASTSLR_LANG env var → system locale → 'en'.
    """
    # 1. Explicit env var
    env_lang = os.environ.get("FASTSLR_LANG")
    if env_lang:
        return env_lang

    # 2. System locale
    try:
        sys_locale = locale.getdefaultlocale()[0] or ""
    except (ValueError, AttributeError):
        sys_locale = ""

    if sys_locale:
        # Try exact match first (e.g., "pt_BR")
        if sys_locale in SUPPORTED_LOCALES:
            return sys_locale
        # Try language-only match (e.g., "pt" → "pt_BR")
        lang = sys_locale.split("_")[0].lower()
        for supported in SUPPORTED_LOCALES:
            if supported.lower().startswith(lang):
                return supported

    return DEFAULT_LOCALE


def _(key: str, **kwargs: object) -> str:
    """Translate a message key, with optional placeholder substitution.

    Lookup order: active locale → English fallback → key itself.
    """
    text = _strings.get(key) or _fallback.get(key) or key

    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass

    return text


# Initialize with auto-detected locale on import
set_locale(detect_locale())


__all__ = [
    "set_locale",
    "get_locale",
    "detect_locale",
    "SUPPORTED_LOCALES",
    "_",
]
