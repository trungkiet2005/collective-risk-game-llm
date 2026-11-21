"""Risk dose-response probe (rebuttal). Gates fixed 2026-11-21 before data: plan/rb-risk-probe-20261121.md.

One decision prompt, only the stated risk changes (p = 0, 0.1, ..., 1.0); histories r1 (round 1) and
fair (round 6 after five fair rounds); base and no-hint wording; 10 calls per cell.
Payoff-driven pivots: r1 at p* = 0.5, fair at p = 1/3 (best response 0 at p <= 0.3, 2 at p >= 0.4).

Outputs followups/rb_risk.csv (one row per model, wording, history, risk) and
followups/rb_risk_step.csv (the pre-registered step test per model, wording, history).

    python paper/AAMAS/analysis/rebuttal_risk.py <download_root>
"""
import csv
import glob
import random
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent / "followups"
BELOW = {"r1": (0.1, 0.2, 0.3, 0.4), "fair": (0.1, 0.2, 0.3)}
ABOVE = {"r1": (0.6, 0.7, 0.8, 0.9, 1.0), "fair": (0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)}
B = 5000


def load(root, task="crg-rb-risk"):
    files = glob.glob(str(Path(root) / "*" / task / "**" / "games.csv"), recursive=True)
    parts = sorted((list(csv.DictReader(open(f, encoding="utf-8"))) for f in files), key=len, reverse=True)
    seen, rows = set(), []
    for part in parts:
        for r in part:
            if (r["model"], r["item"]) not in seen:
                seen.add((r["model"], r["item"]))
                rows.append(r)
    return rows


def boot_diff(a, b, rng):
    d = []
    for _ in range(B):
        x = [a[rng.randrange(len(a))] for _ in a]
        y = [b[rng.randrange(len(b))] for _ in b]
        d.append(sum(x) / len(x) - sum(y) / len(y))
    d.sort()
    return round(d[int(0.025 * B)], 2), round(d[int(0.975 * B)], 2)


def main(root, task="crg-rb-risk", tag=""):
    rows = load(root, task)
    cells = defaultdict(list)
    fails = defaultdict(int)
    for r in rows:
        key = (r["model"], r["template"], r["history"], round(float(r["risk"]), 1))
        if r["parse_failed"] == "0":
            cells[key].append(int(r["value"]))
        else:
            fails[key] += 1
    curve = []
    for (m, t, h, p), v in sorted(cells.items()):
        br = 0 if (h == "fair" and p <= 0.3) or (h == "r1" and p < 0.5) else 2
        curve.append(dict(model=m, wording=t, history=h, risk=p, n=len(v), parse_failed=fails[(m, t, h, p)],
                          mean=round(sum(v) / len(v), 2), share0=round(sum(x == 0 for x in v) / len(v), 2),
                          share2=round(sum(x == 2 for x in v) / len(v), 2),
                          share4=round(sum(x == 4 for x in v) / len(v), 2), best_response=br))
    with open(HERE / ("rb_risk%s.csv" % tag), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(curve[0]))
        w.writeheader()
        w.writerows(curve)
    rng = random.Random(20261121)
    steps = []
    for m, t, h in sorted({k[:3] for k in cells}):
        lo = [x for p in BELOW[h] for x in cells.get((m, t, h, p), [])]
        hi = [x for p in ABOVE[h] for x in cells.get((m, t, h, p), [])]
        z = cells.get((m, t, h, 0.0), [])
        if not lo or not hi:
            continue
        step = sum(hi) / len(hi) - sum(lo) / len(lo)
        ci = boot_diff(hi, lo, rng)
        steps.append(dict(model=m, wording=t, history=h, n_below=len(lo), n_above=len(hi),
                          mean_below=round(sum(lo) / len(lo), 2), mean_above=round(sum(hi) / len(hi), 2),
                          step=round(step, 2), ci_lo=ci[0], ci_hi=ci[1],
                          verdict="risk-responsive" if step >= 1.0 and ci[0] > 0 else "flat",
                          best_response_below=round(sum(x == 0 for x in lo) / len(lo), 2),
                          mean_p0=round(sum(z) / len(z), 2) if z else "", benchmark_step=2))
    with open(HERE / ("rb_risk%s_step.csv" % tag), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(steps[0]))
        w.writeheader()
        w.writerows(steps)
    for s in steps:
        print(s)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--task", default="crg-rb-risk")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    main(a.root, a.task, a.tag)
