"""Dynamic partners (rebuttal, JJ3F w2): does the model stop paying when the target becomes
certain, or only once the pool has passed it?

In exp_bestresponse_switch4 the five scripted partners pay 2 in rounds 1-5 and 4 from round 6,
so the target is certain from round 6 but the pool passes 120 only around round 8. Rounds 6-10
are split by the pool BEFORE the round: below 120 (target certain, not yet reached) or at least
120 (reached). Seat 1 is the model (seat layout LFFFFF / LZZZZZ, checked below).
exp_bestresponse_switch0 is printed for comparison (the pool never reaches 120 there).

    python paper/AAMAS/analysis/rebuttal_switch_settled.py
writes paper/AAMAS/analysis/followups/rb_switch_settled.csv
"""
import ast
import csv
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "followups" / "rb_switch_settled.csv"
rows = []
for exp in ("exp_bestresponse_switch4", "exp_bestresponse_switch0"):
    for f in sorted((REPO / "results" / exp).glob("*/*/*.csv")):
        p, model = f.parts[-3], f.parts[-2]
        cells = {}
        for r in csv.DictReader(open(f, encoding="utf-8")):
            assert r["game_id"].split("seats-")[1][0] == "L", r["game_id"]
            own = ast.literal_eval(r["agent1_strategies"])
            pot = ast.literal_eval(r["pot_cumulative"])
            for t in range(5, 10):  # rounds 6-10
                state = "reached" if pot[t - 1] >= 120 else "not_reached"
                c = cells.setdefault(state, [0, 0, 0])
                c[0] += 1
                c[1] += own[t] > 0
                c[2] += own[t]
        for state, (n, paid, units) in sorted(cells.items()):
            rows.append(dict(experiment=exp, p=p, model=model, pool_before_round=state,
                             rounds=n, rounds_paying=paid, mean_units=round(units / n, 3)))

with open(OUT, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)

for r in rows:
    print("%-25s %-4s %-38s %-12s %3d rounds, %3d paying, mean %.2f" % (
        r["experiment"], r["p"], r["model"], r["pool_before_round"],
        r["rounds"], r["rounds_paying"], r["mean_units"]))
s4 = [r for r in rows if r["experiment"] == "exp_bestresponse_switch4"]
for state in ("not_reached", "reached"):
    n = sum(r["rounds"] for r in s4 if r["pool_before_round"] == state)
    k = sum(r["rounds_paying"] for r in s4 if r["pool_before_round"] == state)
    print("switch to 4, all models and risks, pool %s: %d of %d rounds paying" % (state, k, n))
