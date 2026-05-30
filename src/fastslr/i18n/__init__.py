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

import importlib.resources as resources
import json
import locale
import logging
import os

logger = logging.getLogger(__name__)

LOCALES_SUBDIR = "locales"
SUPPORTED_LOCALES = ("en", "pt_BR", "es")
DEFAULT_LOCALE = "en"

# Anchor package for importlib.resources lookups. ``__package__`` is typed as
# ``str | None``; for this package's ``__init__`` it is always the dotted name.
_PACKAGE = __package__ or "fastslr.i18n"

_current_locale: str = DEFAULT_LOCALE
_strings: dict[str, str] = {}
_fallback: dict[str, str] = {}


def _load_locale_file(locale_name: str) -> dict[str, str]:
    """Load a JSON locale file via importlib.resources and return its dict.

    Uses ``importlib.resources`` so locale data resolves correctly when the
    package is installed (including from a zip/wheel), not just from source.
    Returns an empty dict on any lookup or parse failure (graceful fallback).
    """
    resource = resources.files(_PACKAGE).joinpath(LOCALES_SUBDIR).joinpath(f"{locale_name}.json")
    try:
        if not resource.is_file():
            logger.warning("Locale file not found: %s.json", locale_name)
            return {}
        return json.loads(resource.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Failed to load locale '%s': %s", locale_name, exc)
        return {}


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

    # 2. System locale.
    # ``locale.getdefaultlocale()`` is deprecated and slated for removal in
    # Python 3.15, so we avoid it. ``locale.getlocale()`` returns the locale
    # configured for the process (after any ``setlocale``); when that yields
    # nothing useful (commonly the C/POSIX default), fall back to parsing the
    # standard environment variables, mirroring what getdefaultlocale did.
    sys_locale = ""
    try:
        sys_locale = locale.getlocale(locale.LC_CTYPE)[0] or ""
    except (ValueError, TypeError):
        sys_locale = ""

    if not sys_locale or sys_locale.upper() in ("C", "POSIX"):
        for env_var in ("LC_ALL", "LC_MESSAGES", "LC_CTYPE", "LANG"):
            env_value = os.environ.get(env_var)
            if env_value:
                # Strip encoding/modifier suffixes: "pt_BR.UTF-8@euro" -> "pt_BR"
                sys_locale = env_value.split(".")[0].split("@")[0]
                break

    if sys_locale and sys_locale.upper() not in ("C", "POSIX"):
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
        except (KeyError, IndexError, ValueError) as exc:
            # KeyError/IndexError: placeholder missing from kwargs.
            # ValueError: a typed format spec (e.g. '{value:.2f}') received a
            # non-numeric value. In all cases keep the raw (unformatted) string
            # rather than crashing the UI; log for diagnosis.
            logger.debug("Failed to format i18n key %r with %r: %s", key, kwargs, exc)

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
