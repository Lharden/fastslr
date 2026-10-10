"""Render the per-record markdown tables of the regression report.

Usage: python render.py <regression_detail.json> <fc505_kw.csv> <out.md>
"""
import ast
import json
import sys
from pathlib import Path

import pandas as pd

detail = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
src = pd.read_csv(sys.argv[2], dtype=str, keep_default_na=False).set_index("Key")
out = Path(sys.argv[3])

STATUS = ["Status_T0", "Status_T1A", "Status_T1B", "Status_T1C", "Final_Decision"]
SHORT = {
    "APPROVED_FINAL": "APPROVED",
    "FLAGGED_FINAL": "FLAGGED",
    "REJECTED_FINAL": "REJECTED",
    "NOT_EVALUATED": "N/E",
}
KIND_ORDER = {"decision_or_status": 0, "score_only": 1, "matches_only": 2, "display_only": 3}


def short(v: str) -> str:
    return SHORT.get(v, v) or "—"


def term_list(items: list[str]) -> list[str]:
    out = []
    for s in items:
        t = ast.literal_eval(s)
        if len(t) == 5:  # positive match: term, sec, L, type, comps
            term, sec, level, mtype, _ = t
            out.append(f"`{term}` ({sec}, L{level}{', prox.' if mtype == 'proximity' else ''})")
        else:  # anti/flag hit: term, sec
            out.append(f"`{t[0]}` ({t[1]})")
    return out


def render(kw: str) -> str:
    recs = sorted(
        detail[kw]["records"],
        key=lambda r: (KIND_ORDER[r["kind"]], r["ID"]),
    )
    lines = [
        "| # | ID | Título (início) | Decisão final | Status por bloco | Escore final | Casamentos | Causa |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(recs, 1):
        ch = r["changed"]
        causes = sorted({c for v in ch.values() for c in v["causes"]})
        fd = ch.get("Final_Decision")
        final = (
            f"**{short(fd['before'])} → {short(fd['after'])}**"
            if fd
            else "igual"
        )
        status = "; ".join(
            f"{c.replace('Status_', '')}: {short(ch[c]['before'])} → {short(ch[c]['after'])}"
            for c in STATUS[:-1]
            if c in ch
        ) or "igual"
        scores = "; ".join(
            f"{c.replace('FinalScore_', '')}: {ch[c]['before'] or '0'} → {ch[c]['after'] or '0'}"
            for c in sorted(ch)
            if c.startswith("FinalScore_")
        ) or "igual"
        matches = []
        for c in sorted(ch):
            if c.startswith(("Highlights_", "AntiHighlights_", "Flags_")):
                block = c.split("_", 1)[1]
                kind = {"Highlights": "", "AntiHighlights": "anti ", "Flags": "flag "}[c.split("_")[0]]
                plus = term_list(ch[c]["added"])
                minus = term_list(ch[c]["removed"])
                if plus:
                    matches.append(f"{block} {kind}+ " + ", ".join(plus))
                if minus:
                    matches.append(f"{block} {kind}− " + ", ".join(minus))
        title = src.loc[r["ID"], "Title"][:60].replace("|", "/").replace("�", "?")
        lines.append(
            f"| {i} | {r['ID']} | {title} | {final} | {status} | {scores} | "
            f"{'<br>'.join(matches) or '—'} | {', '.join(causes)} |"
        )
    return "\n".join(lines)


parts = []
for kw, label in (("kw", "Com palavras-chave"), ("nokw", "Sem palavras-chave")):
    parts.append(f"### {label}\n\n{render(kw)}\n")
out.write_text("\n".join(parts), encoding="utf-8")
print("ok", out)
