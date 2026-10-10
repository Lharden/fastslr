"""Build the 505-record inputs (with and without keywords) from the Zotero export.

Usage: python prepare_inputs.py <Final_Corpus.csv> <out_dir>
"""
import hashlib
import sys
from pathlib import Path

import pandas as pd

src, out = Path(sys.argv[1]), Path(sys.argv[2])
df = pd.read_csv(src, dtype=str, keep_default_na=False, encoding="utf-8-sig")
assert len(df) == 506, len(df)
assert (df["Key"] == "BJ4PZ49E").sum() == 1
df = df[df["Key"] != "BJ4PZ49E"].reset_index(drop=True)
assert len(df) == 505 and df["Key"].is_unique

kw = out / "fc505_kw.csv"
df.to_csv(kw, index=False, encoding="utf-8")
nokw = df.copy()
nokw["Manual Tags"] = ""
nokw_path = out / "fc505_nokw.csv"
nokw.to_csv(nokw_path, index=False, encoding="utf-8")

print("source sha256", hashlib.sha256(src.read_bytes()).hexdigest())
print("records with Manual Tags:", int((df["Manual Tags"].str.strip() != "").sum()))
for p in (kw, nokw_path):
    print(p.name, len(pd.read_csv(p, dtype=str)), hashlib.sha256(p.read_bytes()).hexdigest())
