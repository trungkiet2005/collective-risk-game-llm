"""Reasons Claude Haiku 4.5 writes in the SUBMITTED risk grid (rebuttal, R2 mTF6).

Haiku is the only model of the panel that writes free text before its CONTRIBUTION line.
This codes that text with the same regexes as the explained-decision probe (CODES in
rebuttal_probes.py), so the two are comparable.

Source: the dense-grid transcripts in Legacy_Results/ (read-only; read on the user's
request of 2026-11-21), English, reps 0-9 = exactly the 110 games of
results/exp_baseline. Every move is checked against results/ first; any mismatch aborts.

Per risk level and round scope (round 1 only, and all rounds): seats or turns, how many
pay (> 0), and how many replies match each code.

    python paper/AAMAS/analysis/rebuttal_grid_reasons.py
"""
import ast
import csv
import glob
import importlib.util
import json
import re
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / "followups" / "rb_grid_reasons.csv"
TAG = "anthropic-claude-haiku-4-5-20251001"
TURNS = REPO / "Legacy_Results" / "results" / "frontier" / "dense_grid" / TAG / "exp_baseline" / "turns.jsonl"


def load_codes():
    spec = importlib.util.spec_from_file_location("rbp", HERE / "rebuttal_probes.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CODES


def risk_dir(p):
    return "0" if p == 0 else ("1" if p == 1 else repr(p))


def main():
    codes = load_codes()
    turns = defaultdict(dict)
    for line in open(TURNS, encoding="utf-8"):
        t = json.loads(line)
        if t.get("language") != "en" or int(t["rep"]) > 9:
            continue
        p = round(float(t["risk_probability"]), 2)
        seat = int(t["player"].split("_")[1]) - 1
        turns[(p, int(t["rep"]))][(seat, t["round"])] = t

    # the transcripts must be the paper's games, move for move
    checked = 0
    for p in sorted({k[0] for k in turns}):
        f = glob.glob(str(REPO / "results" / "exp_baseline" / risk_dir(p) / TAG / "*.csv"))[0]
        for r in csv.DictReader(open(f, encoding="utf-8")):
            g = turns[(p, int(r["rep"]))]
            for k in range(6):
                moves = ast.literal_eval(r["agent%d_strategies" % (k + 1)])
                for rd, mv in enumerate(moves, 1):
                    if int(g[(k, rd)]["contribution"]) != mv:
                        raise SystemExit("move mismatch %s rep %s seat %d round %d" % (p, r["rep"], k, rd))
                    checked += 1

    rows = []
    for p in sorted({k[0] for k in turns}):
        for scope in ("round1", "all"):
            sel = [t for (pp, _), g in turns.items() if pp == p for (s, rd), t in g.items()
                   if scope == "all" or rd == 1]
            rec = {"risk": p, "scope": scope, "n": len(sel),
                   "pays": sum(int(t["contribution"]) > 0 for t in sel)}
            for c, rx in codes.items():
                rec[c] = sum(bool(re.search(rx, t.get("raw_response") or "", re.I)) for t in sel)
            rec["zero_risk_and_pays"] = sum(
                bool(re.search(codes["zero_risk"], t.get("raw_response") or "", re.I))
                and int(t["contribution"]) > 0 for t in sel)
            rows.append(rec)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("moves verified:", checked)
    for r in rows:
        if r["scope"] == "round1" and r["risk"] in (0.0, 0.1, 0.5, 0.9):
            print(r)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
