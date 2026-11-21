"""Target probe (rebuttal): is the payment rebuilt from the target? Fixed 2026-11-21 before data.

Round-1 decision, no history. T = 240: fair share 4 per round, pivot p* = 1, so paying is never
worth it at p < 1. Per model, wording (base / no hint), target, risk: mean payment, share paying 4,
share paying 0, n. Explained decisions at T = 240, p = 0.9 are listed verbatim (first 300 chars).

    python paper/AAMAS/analysis/rebuttal_target.py <download_root>
"""
import csv
import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent / "followups" / "rb_target.csv"


def main(root):
    files = glob.glob(str(Path(root) / "*" / "crg-rb-target" / "**" / "games.csv"), recursive=True)
    parts = sorted((list(csv.DictReader(open(f, encoding="utf-8"))) for f in files), key=len, reverse=True)
    seen, rows = set(), []
    for part in parts:
        for r in part:
            if (r["model"], r["item"]) not in seen:
                seen.add((r["model"], r["item"]))
                rows.append(r)
    cells = defaultdict(list)
    for r in rows:
        if r["kind"] == "cf" and r["parse_failed"] == "0":
            cells[(r["model"], r["template"], int(r["target"]), float(r["risk"]))].append(int(r["value"]))
    out = []
    for (m, t, T, p), v in sorted(cells.items()):
        out.append(dict(model=m, wording=t, target=T, risk=p, n=len(v), mean=round(sum(v) / len(v), 2),
                        share_pay4=round(sum(x == 4 for x in v) / len(v), 2),
                        share_pay0=round(sum(x == 0 for x in v) / len(v), 2)))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    for r in out:
        print(json.dumps(r))
    for r in rows:
        if r["kind"] == "explain":
            print(r["model"], r["value"], "|", (r["raw_response"] or "")[:300].replace("\n", " "))


if __name__ == "__main__":
    main(sys.argv[1])
