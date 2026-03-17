"""FastSLR core engine — deterministic SLR triage."""

from .constants import VERSION
from .engine import collect_statistics, process_articles, sample_articles
from .models import AntiHit, BlockEvaluation, GlobalParams, T0Evaluation, TermMatch

__all__ = [
    "VERSION",
    "process_articles",
    "collect_statistics",
    "sample_articles",
    "TermMatch",
    "AntiHit",
    "BlockEvaluation",
    "T0Evaluation",
    "GlobalParams",
]
