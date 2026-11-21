"""Within-model risk trend on the self-play grid (rebuttal, Reviewer JJ3F).

Unit = game (mean seat total over its six seats). For each model, over p in (0, 1]:
OLS slope of game mean on p (units per +0.1 risk), 95% percentile bootstrap resampling
games within each risk level, two-sided permutation P shuffling risk labels across games,
and Spearman rho. The welfare benchmark (0 below 1/2, 20 above) gives the reference slope
on the same design. Also the low-vs-high contrast (p<=0.4 vs p>=0.6).

    python paper/AAMAS/analysis/rebuttal_trend.py
"""
import ast
import csv
import glob
import json
import random
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "followups" / "rebuttal_trend.csv"
B, PERM = 5000, 5000


def games():
    rows = []
    for f in glob.glob(str(REPO / "results" / "exp_baseline" / "*" / "*" / "*.csv")):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            tot = [sum(ast.literal_eval(r["agent%d_strategies" % k])) for k in range(1, 7)]
            rows.append((r["agent1_llm"], float(r["risk_probability"]), sum(tot) / 6))
    return rows


def slope(x, y):
    mx, my = sum(x) / len(x), sum(y) / len(y)
    sxx = sum((a - mx) ** 2 for a in x)
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / sxx


def ranks(v):
    o = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and v[o[j + 1]] == v[o[i]]:
            j += 1
        for k in range(i, j + 1):
            r[o[k]] = (i + j) / 2
        i = j + 1
    return r


def spearman(x, y):
    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else 0.0


def main():
    rng = random.Random(20261121)
    data = games()
    out = []
    for model in sorted({m for m, _, _ in data}):
        pts = [(p, y) for m, p, y in data if m == model and p > 0]
        x, y = [p for p, _ in pts], [v for _, v in pts]
        s = slope(x, y) / 10
        by = {}
        for p, v in pts:
            by.setdefault(p, []).append(v)
        boots = []
        for _ in range(B):
            bx, bv = [], []
            for p, vs in by.items():
                for _ in vs:
                    bx.append(p)
                    bv.append(rng.choice(vs))
            boots.append(slope(bx, bv) / 10)
        boots.sort()
        perm = 0
        for _ in range(PERM):
            xs = x[:]
            rng.shuffle(xs)
            if abs(slope(xs, y) / 10) >= abs(s) - 1e-12:
                perm += 1
        lo = [v for p, v in pts if p <= 0.4]
        hi = [v for p, v in pts if p >= 0.6]
        bench = [0.0 if p < 0.5 else (10.0 if p == 0.5 else 20.0) for p in x]
        out.append(dict(model=model, n_games=len(pts), slope_per_0p1=round(s, 3),
                        slope_lo=round(boots[int(0.025 * B)], 3),
                        slope_hi=round(boots[int(0.975 * B) - 1], 3),
                        perm_p=round((perm + 1) / (PERM + 1), 4),
                        spearman=round(spearman(x, y), 3),
                        mean_low=round(sum(lo) / len(lo), 2),
                        mean_high=round(sum(hi) / len(hi), 2),
                        high_minus_low=round(sum(hi) / len(hi) - sum(lo) / len(lo), 2),
                        benchmark_slope_per_0p1=round(slope(x, bench) / 10, 3)))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    for r in out:
        print(json.dumps(r))


if __name__ == "__main__":
    main()
