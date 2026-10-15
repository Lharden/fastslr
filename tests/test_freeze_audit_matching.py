"""Pre-freeze audit of FastSLR v3.0.0: matching defects F01-F06.

The audit (RSL_Project ``docs/nova_rsl/auditoria_fastslr_v3.0.0``, 2026-10-10)
found text-normalization defects that REJECT eligible records. In the review
that will use the frozen version, rejected records are removed with no human
re-check, so each defect is pinned here by a test that failed on v3.0.0.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from fastslr.app.controller import _prepare_config
from fastslr.core.config import parse_terms_csv
from fastslr.core.normalization import NormalizationEngine, extract_normalization_rules
from fastslr.core.patterns import compile_proximity_pattern, precompile_patterns

from .freeze_audit_support import (
    CONFIG_V8,
    TERMS_FINAL,
    highlighted_terms,
    run_rows,
    write_config,
    write_terms,
)

# ── F01: symbol replacement glued words together ─────────────────────────────


class TestF01SymbolReplacementIsAWord:
    """'/', '&' and '+' became glued text ('intelligenceormachine', 'oilandgas')."""

    def test_slash_between_abbreviations_becomes_or(self, hist_engine):
        assert (
            hist_engine.normalize("AI/ML for procurement")
            == "artificial intelligence or machine learning for procurement"
        )

    def test_glued_ampersand_becomes_and(self, hist_engine):
        assert hist_engine.normalize("oil&gas") == "oil and gas"

    def test_target_spaces_in_terms_file_are_kept(self):
        df = pd.DataFrame(
            {
                "term": ["&"],
                "normalization_type": ["symbol_replacement"],
                "normalization_target": [" and "],
            }
        )
        rules = extract_normalization_rules(df)
        assert rules["symbol_replacements"]["&"] == " and "

    def test_letter_symbol_replacement_stays_glued(self, hist_engine):
        # A ligature stands for letters inside a word, not for a word.
        assert hist_engine.normalize("ﬁnance") == "finance"

    def test_audit_title_is_approved(self, hist_config):
        res = run_rows(
            hist_config,
            [["583", "AI/ML for procurement in the oil and gas industry", "", ""]],
        )
        assert res.loc["583", "Final_Decision"] == "APPROVED_FINAL"

    def test_glued_oil_and_gas_matches_term(self, hist_config):
        res = run_rows(hist_config, [["k", "Machine learning for procurement in oil&gas", "", ""]])
        assert "oil and gas" in highlighted_terms(res.loc["k", "Highlights_T1A"])

    @pytest.mark.parametrize("text", ["O&G", "O & G"])
    def test_og_acronym_matches_as_exact_phrase(self, hist_config, text):
        res = run_rows(hist_config, [["k", f"Machine learning for {text} procurement", "", ""]])
        assert "O&G" in highlighted_terms(res.loc["k", "Highlights_T1A"])

    def test_no_proximity_for_single_character_components(self, hist_config):
        prox = hist_config["T1A"]["proximity_positives"]
        components = {p["components"] for p in prox}
        assert ("o", "g") not in components
        assert ("e", "p") not in components
        assert ("oil", "gas") in components

    def test_single_letters_near_each_other_do_not_match_e_and_p(self, hist_config):
        res = run_rows(
            hist_config,
            [
                [
                    "k",
                    "Machine learning for procurement in hospitals",
                    "The effect was significant, p = 0.01 e.g. in table 2.",
                    "",
                ]
            ],
        )
        assert "E&P" not in highlighted_terms(res.loc["k", "Highlights_T1A"])


# ── F02: hyphenated compounds did not match the spaced term ─────────────────


class TestF02HyphenBetweenWordsIsASpace:
    def test_text_hyphen_becomes_space(self, hist_engine):
        assert hist_engine.normalize("A machine-learning model") == "a machine learning model"

    def test_disabled_engine_also_treats_hyphen_as_space(self, normalization_engine_disabled):
        assert normalization_engine_disabled.normalize("Deep-Learning") == "deep learning"

    def test_hyphenated_text_matches_spaced_term(self, hist_config):
        res = run_rows(
            hist_config,
            [["k", "A machine-learning model for oil and gas procurement", "", ""]],
        )
        assert "machine learning" in highlighted_terms(res.loc["k", "Highlights_T1B"])

    def test_hyphenated_term_matches_spaced_and_hyphenated_text(self, hist_config):
        rows = [
            ["a", "Oil and gas procurement with machine learning", "On-time delivery rose.", ""],
            ["b", "Oil and gas procurement with machine learning", "On time delivery rose.", ""],
        ]
        res = run_rows(hist_config, rows)
        for key in ("a", "b"):
            assert "on-time deliver*" in highlighted_terms(res.loc[key, "Highlights_T1C"])

    def test_compound_variants_with_hyphen_still_apply(self, hist_engine):
        assert hist_engine.normalize("e-procurement") == "procurement"
        assert hist_engine.normalize("well-bore") == "wellbore"
        assert hist_engine.normalize("supply-chain") == "supply chain"

    def test_hyphen_outside_words_is_kept(self, hist_engine):
        assert hist_engine.normalize("pre- and post-processing") == "pre- and post processing"

    def test_regex_term_with_word_hyphen_word_warns(self, tmp_path):
        terms = write_terms(
            tmp_path / "terms.csv",
            [
                "T1;pos;covid-19;1;any;1;;",
                "T1;pos;supply chain;1;any;0;;",
            ],
        )
        cfg = _prepare_config(write_config(tmp_path / "config.json"), terms)
        warnings = cfg["_parse_warnings"]
        assert any("covid-19" in w and "hyphen" in w for w in warnings)


# ── F03: proximity crossed sentence and list punctuation ─────────────────────


class TestF03ProximitySeparator:
    @pytest.mark.parametrize("text", ["engine oil. Gas turbines", "food, oil, natural gas"])
    def test_does_not_cross_period_or_comma(self, text):
        pat = compile_proximity_pattern("oil", "gas", max_gap=2)
        assert pat is not None
        assert not pat.search(text.lower())

    @pytest.mark.parametrize("text", ["oil-and-gas", "oil and natural gas", "oil/gas", "gas-oil"])
    def test_space_hyphen_slash_still_match(self, text):
        pat = compile_proximity_pattern("oil", "gas", max_gap=2)
        assert pat is not None
        assert pat.search(text)


# ── F04: abbreviations expanded regardless of case ───────────────────────────


class TestF04AbbreviationsAreCaseSensitive:
    @pytest.mark.parametrize(
        ("text", "forbidden"),
        [
            ("each 5 ml sample", "machine learning"),
            ("Ann Arbor plant", "neural network"),
            ("the cv of the series", "computer vision"),
            ("step size dt", "digital twin"),
        ],
    )
    def test_lowercase_or_titlecase_does_not_expand(self, hist_engine, text, forbidden):
        assert forbidden not in hist_engine.normalize(text)

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("We apply ML", "machine learning"),
            ("an ANN model", "neural network"),
            ("CV pipeline", "computer vision"),
            ("a DT of the plant", "digital twin"),
        ],
    )
    def test_uppercase_acronym_expands(self, hist_engine, text, expected):
        assert expected in hist_engine.normalize(text)

    def test_abbreviation_key_keeps_its_case(self):
        df = pd.DataFrame(
            {
                "term": ["IoT"],
                "normalization_type": ["abbreviation"],
                "normalization_target": ["Internet of Things"],
            }
        )
        rules = extract_normalization_rules(df)
        engine = NormalizationEngine(rules)
        assert engine.normalize("IoT sensors") == "internet of things sensors"
        assert engine.normalize("IOT sensors") == "internet of things sensors"
        assert engine.normalize("iot sensors") == "iot sensors"

    def test_ml_volume_does_not_create_ai_evidence(self, hist_config):
        res = run_rows(
            hist_config,
            [
                [
                    "k",
                    "Procurement in the oil and gas supply chain",
                    "Each 5 ml sample was analysed.",
                    "",
                ]
            ],
        )
        assert "machine learning" not in highlighted_terms(res.loc["k", "Highlights_T1B"])


# ── F05: source row was the internal index, 2 less than the file line ────────


class TestF05SourceRowIsTheFileLine:
    def test_oil_and_gas_reports_line_53(self, hist_config):
        entry = next(e for e in hist_config["T1A"]["positives"] if e["term"] == "oil and gas")
        assert entry["source_row"] == 53

    def test_highlight_cell_carries_the_file_line(self, hist_config):
        res = run_rows(
            hist_config, [["k", "Oil and gas procurement with machine learning", "", ""]]
        )
        assert 'term="oil and gas" sec=title L=1 row=53 ' in res.loc["k", "Highlights_T1A"]

    def test_invalid_regex_warning_reports_the_file_line(self, tmp_path):
        terms = write_terms(
            tmp_path / "terms.csv",
            [
                "T1;pos;supply chain;1;any;0;;",
                "T1;pos;([bad;1;any;1;;",
            ],
        )
        cfg = _prepare_config(write_config(tmp_path / "config.json"), terms)
        assert any(w.startswith("Row 3,") and "([bad" in w for w in cfg["_parse_warnings"])


# ── F06: proximity generated for regex terms; wildcard escaped ───────────────


class TestF06ProximityForRegexAndWildcards:
    def _block(self, term: str, is_regex: bool) -> dict:
        return {
            "positives": [
                {"term": term, "level": "1", "scope": "any", "regex": is_regex, "source_row": 2}
            ],
            "anti": {"exclude": [], "flag": []},
        }

    def test_no_proximity_for_regex_terms(self):
        compiled = precompile_patterns(self._block(r"oil (and|&) gas", True))
        assert compiled["proximity_positives"] == []

    def test_wildcard_in_proximity_component_is_a_wildcard(self):
        compiled = precompile_patterns(self._block("petroleum refiner* and gas plant*", False))
        prox = compiled["proximity_positives"]
        assert prox
        assert any(p["pattern"].search("petroleum refineries and natural gas plants") for p in prox)

    def test_compile_proximity_pattern_expands_wildcard(self):
        pat = compile_proximity_pattern("refiner*", "gas", max_gap=2)
        assert pat is not None
        assert pat.search("refineries and gas")
        assert pat.search("gas from the refinery")


def test_historical_fixture_terms_parse_without_warnings():
    cfg = parse_terms_csv(TERMS_FINAL, json.loads(CONFIG_V8.read_text(encoding="utf-8")))
    assert cfg["_parse_warnings"] == []
    assert cfg["_valid_terms_count"] == 143
