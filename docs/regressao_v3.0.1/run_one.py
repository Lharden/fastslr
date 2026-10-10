"""Run one FastSLR triage through the production path (controller.run_triage).

Usage: python -I run_one.py <src_dir> <input> <config> <terms> <out_dir> [revert]

<src_dir> selects the code (v3.0.0 extract or the fixed worktree). [revert]
names ONE fix to undo in memory on the fixed code (leave-one-out attribution):
  F01  symbol targets glued again and 1-char proximity allowed
  F02  hyphen between words kept
  F03  proximity separator back to [\\s\\-/.,]+
  F04  abbreviations case-insensitive again
  F06  proximity for regex terms and escaped wildcard
"""
import re
import sys
from pathlib import Path

src_dir, inp, cfg, terms, out = (Path(a) for a in sys.argv[1:6])
revert = sys.argv[6] if len(sys.argv) > 6 else ""
sys.path.insert(0, str(src_dir))

import fastslr  # noqa: E402

assert Path(fastslr.__file__).resolve().is_relative_to(src_dir.resolve()), fastslr.__file__

import fastslr.core.normalization as normmod  # noqa: E402
import fastslr.core.patterns as patmod  # noqa: E402

if revert == "F01":
    normmod._symbol_substitution = lambda symbol, replacement: replacement
    patmod._MIN_PROXIMITY_COMPONENT_LEN = 0
elif revert == "F02":
    normmod._WORD_HYPHEN_RE = re.compile(r"(?!x)x")
elif revert == "F03":
    patmod._PROXIMITY_SEP = r"[\s\-/.,]+"
elif revert == "F04":
    normmod._abbreviation_pattern = lambda abbr: re.compile(
        rf"\b{re.escape(abbr)}\b", re.IGNORECASE
    )
elif revert == "F06":
    patmod._entry_is_regex = lambda entry: False
    _orig = patmod.compile_proximity_pattern

    def _escaped(term_a, term_b, **kw):
        # old behaviour: '*' stays a literal
        return _orig(term_a.replace("*", "\x00"), term_b.replace("*", "\x00"), **kw)

    patmod.compile_proximity_pattern = _escaped
elif revert:
    raise SystemExit(f"unknown revert {revert}")

from fastslr.app.controller import run_triage  # noqa: E402
from fastslr.core.constants import VERSION  # noqa: E402

res = run_triage(inp, cfg, terms, out)
print(VERSION, revert or "-", res.result_path, res.stats.get("decision_distribution"))
print("input_warnings:", res.stats.get("input_warnings"))
