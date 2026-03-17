"""Backward-compatibility shim. Use 'fastslr' instead."""

from fastslr import *  # noqa: F401,F403
from fastslr import __version__

__all__ = ["__version__"]
