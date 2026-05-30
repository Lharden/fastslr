"""Regression tests: highlight parsing must survive terms containing double quotes.

Bug: ``pack_highlights`` serialized ``term="{m.term}"`` without escaping embedded
double quotes. A term such as ``5"`` produced ``term="5"" sec=title ...`` which the
coverage regex ``term="([^"]+)"\\s+sec=(\\w+)`` could not parse, so the hit was lost
and the term was wrongly reported as a dead-term (0 matches) and suggested for removal.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from fastslr.core import io
from fastslr.core.coverage import _iter_term_sections, analyze_term_coverage


@dataclass
class _FakeMatch:
    term: str
    level: str = "L1"
    source_row: int = 0
    match_type: str = "exact"
    components: list[str] = field(default_factory=list)


@dataclass
class _FakeEvaluation:
    matches: dict[str, list[_FakeMatch]]


def test_pack_highlights_roundtrip_recovers_term_with_quote() -> None:
    """A term containing a double quote round-trips through pack/regex intact."""
    term = 'pipe 5" diameter'
    evaluation = _FakeEvaluation(matches={"title": [_FakeMatch(term=term)]})

    packed = io.pack_highlights(evaluation)

    matches = list(_iter_term_sections(packed))
    assert len(matches) == 1, f"failed to parse packed highlight: {packed!r}"
    parsed_term, parsed_sec = matches[0]
    assert parsed_term == term
    assert parsed_sec == "title"


def test_pack_highlights_roundtrip_plain_term() -> None:
    """A plain term (no quotes) still round-trips, preserving backward behavior."""
    evaluation = _FakeEvaluation(matches={"abstract": [_FakeMatch(term="machine learning")]})

    packed = io.pack_highlights(evaluation)

    matches = list(_iter_term_sections(packed))
    assert len(matches) == 1
    assert matches[0][0] == "machine learning"
    assert matches[0][1] == "abstract"


def test_term_with_quote_not_reported_as_dead() -> None:
    """A quoted term that matched an article must NOT be classified as a dead-term."""
    term = 'pipe 5" diameter'
    evaluation = _FakeEvaluation(matches={"title": [_FakeMatch(term=term)]})
    packed = io.pack_highlights(evaluation)

    result_df = pd.DataFrame({"Highlights_domain": [packed]})
    config = {
        "_domain_blocks": ["domain"],
        "domain": {"positives": [{"original_term": term}]},
    }

    report = analyze_term_coverage(result_df, config, domain_blocks=["domain"])

    dead = {d["term"] for d in report.dead_terms}
    assert term not in dead, f"quoted term wrongly flagged dead: {report.dead_terms}"


def test_multiple_highlights_with_quotes_in_one_cell() -> None:
    """Multiple ' | '-joined highlights, some with quotes, parse independently."""
    evaluation = _FakeEvaluation(
        matches={
            "title": [_FakeMatch(term='a "quoted" term')],
            "abstract": [_FakeMatch(term="plain term")],
        }
    )
    packed = io.pack_highlights(evaluation)

    found = set(_iter_term_sections(packed))
    assert ('a "quoted" term', "title") in found
    assert ("plain term", "abstract") in found
