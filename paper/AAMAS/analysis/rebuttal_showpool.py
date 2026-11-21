"""Running-pool control, self-play (rebuttal). Pool shown vs base prompt at the same risk.

Per (model, risk): mean seat total, games reaching 120, units per game paid after the pool
had already reached 120 before that round (wasted for every belief), and units paid in the
final round. Base = results/exp_baseline at the same risk (10 games). Intervals: 95%
percentile bootstrap over games of the difference (5,000). Duplicate game_ids across
download folders are dropped (first kept); only games with 60 parsed turns count.

    python paper/AAMAS/analysis/rebuttal_showpool.py <download_root>
"""
import ast
import csv
import glob
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "followups" / "rb_showpool.csv"


def game_stats(moves):
    """moves[seat][round] -> (mean seat total, reached, units after 120, units in round 10)."""
    pool, after, last = 0, 0, 0
    for r in range(10):
        rnd = [moves[s][r] for s in range(6)]
        if pool >= 120:
            after += sum(rnd)
        if r == 9:
            last = sum(rnd)
        pool += sum(rnd)
    return sum(map(sum, moves)) / 6, int(pool >= 120), after, last


def load_showpool(root):
    games = {}
    for f in glob.glob(str(Path(root) / "*" / "crg-rb-showpool" / "**" / "turns.jsonl"), recursive=True):
        per = defaultdict(dict)
        bad = set()
        for line in open(f, encoding="utf-8"):
            t = json.loads(line)
            if t.get("parse_failed"):
                bad.add(t["game_id"])
            seat = int(t["player"].split("_")[1]) - 1
            per[t["game_id"]][(seat, t["round"] - 1)] = int(t["contribution"])
        for gid, d in per.items():
            if gid in games or gid in bad or len(d) != 60:
                continue
            model = gid.split("__")[1]
            risk = 0.9 if "high_risk" in gid else (0.1 if "low_risk" in gid else None)
            moves = [[d[(s, r)] for r in range(10)] for s in range(6)]
            games[gid] = (model, risk, game_stats(moves))
    return games


def load_base():
    base = defaultdict(list)
    for p in ("0.1", "0.9"):
        for f in glob.glob(str(REPO / "results" / "exp_baseline" / p / "*" / "*.csv")):
            for r in csv.DictReader(open(f, encoding="utf-8")):
                moves = [ast.literal_eval(r["agent%d_strategies" % k]) for k in range(1, 7)]
                base[(r["agent1_llm"], float(p))].append(game_stats(moves))
    return base


def boot_diff(a, b, i, rng, n=5000):
    d = []
    for _ in range(n):
        sa = [rng.choice(a)[i] for _ in a]
        sb = [rng.choice(b)[i] for _ in b]
        d.append(sum(sa) / len(sa) - sum(sb) / len(sb))
    d.sort()
    return round(d[int(0.025 * n)], 2), round(d[int(0.975 * n) - 1], 2)


def main(root):
    rng = random.Random(20261121)
    sp = load_showpool(root)
    base = load_base()
    cells = defaultdict(list)
    for model, risk, st in sp.values():
        cells[(model, risk)].append(st)
    out = []
    names = ("seat_total", "target", "after120", "last_round")
    for (model, risk), s in sorted(cells.items()):
        b = base.get((model, risk), [])
        row = dict(model=model, risk=risk, n_pool=len(s), n_base=len(b))
        for i, nm in enumerate(names):
            mp = sum(x[i] for x in s) / len(s)
            mb = sum(x[i] for x in b) / len(b) if b else float("nan")
            row[nm + "_base"] = round(mb, 2)
            row[nm + "_pool"] = round(mp, 2)
            if b and nm != "target":
                lo, hi = boot_diff(s, b, i, rng)
                row[nm + "_diff_ci"] = "[%s, %s]" % (lo, hi)
        out.append(row)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        keys = []
        for r in out:
            keys += [k for k in r if k not in keys]
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(out)
    for r in out:
        print(json.dumps(r))


if __name__ == "__main__":
    main(sys.argv[1])
