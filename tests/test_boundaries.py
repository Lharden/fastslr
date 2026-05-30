"""Regression tests for conditional word-boundary anchoring.

Terms ending/starting in non-word characters (``C++``, ``C#``, ``.NET``,
``F#``) must still match because ``\\b`` only asserts a boundary between a
word char and a non-word char. Wrapping such terms in ``\\b...\\b`` either
never matches (``\\bC\\+\\+\\b``) or matches the wrong thing
(``\\b\\.NET\\b`` matching ``X.NET``).
"""

from __future__ import annotations

from fastslr.core.normalization import NormalizationEngine
from fastslr.core.patterns import compile_pattern


class TestConditionalBoundaries:
    """compile_pattern must anchor boundaries conditionally on edge chars."""

    def test_cpp_matches_in_text(self) -> None:
        pattern = compile_pattern("C++")
        assert pattern is not None
        assert pattern.search("C++ language") is not None

    def test_csharp_matches_in_text(self) -> None:
        pattern = compile_pattern("C#")
        assert pattern is not None
        assert pattern.search("using C# today") is not None

    def test_dotnet_matches_isolated(self) -> None:
        pattern = compile_pattern(".NET")
        assert pattern is not None
        assert pattern.search("the .NET framework") is not None

    def test_fsharp_matches_in_text(self) -> None:
        pattern = compile_pattern("F#")
        assert pattern is not None
        assert pattern.search("F# code") is not None

    def test_dotnet_leading_edge_relaxed(self) -> None:
        # Per the conditional-boundary rule, the leading anchor is only added
        # when term[0] is a word char. '.NET' starts with a non-word char,
        # so the left side is relaxed (no (?<!\w)) and 'X.NET' may match the
        # '.NET' span. Trailing 'T' is a word char, so 'X.NETabc' must NOT
        # match (suffix (?!\w) is enforced).
        pattern = compile_pattern(".NET")
        assert pattern is not None
        assert pattern.search("X.NET") is not None
        assert pattern.search("the .NETcore lib") is None

    def test_word_term_still_requires_boundary(self) -> None:
        # Normal word-char terms keep full boundary anchoring.
        pattern = compile_pattern("cat")
        assert pattern is not None
        assert pattern.search("the cat sat") is not None
        assert pattern.search("category") is None
        assert pattern.search("scatter") is None

    def test_wildcard_still_works(self) -> None:
        pattern = compile_pattern("comput*")
        assert pattern is not None
        assert pattern.search("computing") is not None
        assert pattern.search("computer") is not None


class TestSymbolReplacementBoundaries:
    """NormalizationEngine symbol_replacements must match symbol keys."""

    def test_csharp_and_cpp_symbol_replacement(self) -> None:
        rules = {
            "enabled": True,
            "abbreviations": {},
            "compound_variants": {},
            "symbol_replacements": {"c#": "csharp", "c++": "cpp"},
        }
        engine = NormalizationEngine(rules)
        result = engine.normalize("using C# and C++")
        assert "csharp" in result
        assert "cpp" in result
        assert "c#" not in result
        assert "c++" not in result

    def test_symbol_keys_lowercased_on_construction(self) -> None:
        # Keys provided with uppercase / mixed case must still match
        # because the text is lowercased before the symbol loop.
        rules = {
            "enabled": True,
            "abbreviations": {},
            "compound_variants": {},
            "symbol_replacements": {"C#": "csharp", ".NET": "dotnet"},
        }
        engine = NormalizationEngine(rules)
        result = engine.normalize("the C# and .NET stack")
        assert "csharp" in result
        assert "dotnet" in result
