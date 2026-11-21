"""Generalisation wave: base self-play of six newer or open models (rebuttal, mTF6 Q3).

Per (model, risk): games, mean seat total (benchmark: 0 below p* = 1/2, 20 above), share of
seats paying anything, games reaching 120, units paid after the pool reached 120. Only games
with 60 parsed turns; duplicate game_ids dropped. Tasks crg-gen-selfplay-p0/-p01/-p09 under
the download root. The five-model panel (results/exp_baseline) is printed for the same risks.

    python paper/AAMAS/analysis/rebuttal_gen_selfplay.py <download_root>
"""
import ast
import csv
import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "followups" / "gen_selfplay.csv"
RISK_OF_TASK = {"crg-gen-selfplay-p0": 0.0, "crg-gen-selfplay-p01": 0.1, "crg-gen-selfplay-p09": 0.9}


def stats(moves):
    pool, after = 0, 0
    for r in range(10):
        rnd = [moves[s][r] for s in range(6)]
        if pool >= 120:
            after += sum(rnd)
        pool += sum(rnd)
    totals = [sum(m) for m in moves]
    return sum(totals) / 6, sum(t > 0 for t in totals) / 6, int(pool >= 120), after


def load_gen(root):
    games = {}
    for task, risk in RISK_OF_TASK.items():
        for f in glob.glob(str(Path(root) / "*" / task / "**" / "turns.jsonl"), recursive=True):
            per, bad = defaultdict(dict), set()
            for line in open(f, encoding="utf-8"):
                t = json.loads(line)
                if t.get("parse_failed"):
                    bad.add(t["game_id"])
                per[t["game_id"]][(int(t["player"].split("_")[1]) - 1, t["round"] - 1)] = int(t["contribution"])
            for gid, d in per.items():
                if gid in games or gid in bad or len(d) != 60:
                    continue
                games[gid] = (gid.split("__")[1], risk, stats([[d[(s, r)] for r in range(10)] for s in range(6)]))
    return games


def load_panel():
    out = defaultdict(list)
    for p in ("0", "0.1", "0.9"):
        for f in glob.glob(str(REPO / "results" / "exp_baseline" / p / "*" / "*.csv")):
            for r in csv.DictReader(open(f, encoding="utf-8")):
                moves = [ast.literal_eval(r["agent%d_strategies" % k]) for k in range(1, 7)]
                out[(r["agent1_llm"], float(p))].append(stats(moves))
    return out


def row(model, risk, s, source):
    n = len(s)
    return dict(source=source, model=model, risk=risk, games=n,
                seat_total=round(sum(x[0] for x in s) / n, 2),
                share_seats_paying=round(sum(x[1] for x in s) / n, 2),
                games_reaching_120=sum(x[2] for x in s),
                units_after_120=round(sum(x[3] for x in s) / n, 2))


def main(root):
    cells = defaultdict(list)
    for model, risk, st in load_gen(root).values():
        cells[(model, risk)].append(st)
    rows = [row(m, r, s, "new") for (m, r), s in sorted(cells.items())]
    rows += [row(m, r, s, "panel") for (m, r), s in sorted(load_panel().items())]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(json.dumps(r))


if __name__ == "__main__":
    main(sys.argv[1])
