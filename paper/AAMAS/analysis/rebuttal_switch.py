"""Dynamic partners (rebuttal, R1 JJ3F). One llm seat, five scripted partners.

Arms, all with the llm in seat P1 and the base prompt:
    coop      five always_2 partners                  (control, exp_bestresponse_coop)
    switch0   partners pay 2 in rounds 1-5, then 0    (target out of reach from round 6)
    switch4   partners pay 2 in rounds 1-5, then 4    (target certain from round 6)
The best response from round 6 is 0 in both switch arms; in coop it is 2 at p=0.9
(the llm seat is pivotal) and 0 at p=0.1 (a share costs 20 for certain, keeping 30 is
worth 27 on average).

Per (model, risk, arm), over games: the llm seat's mean contribution per round in rounds
1-5 and in rounds 6-10, the change late - early, the share of rounds 6-10 in which it
paid 0, the share of games reaching 120, and its mean EXPECTED payoff ((40 - paid) if the
target is reached, else (40 - paid)(1 - p)), as the paper reports. Each switch arm's change is
compared with the coop change at the same (model, risk): a difference in differences with
a 95% percentile bootstrap over games (5,000, fixed seed).

    python paper/AAMAS/analysis/rebuttal_switch.py
"""
import ast
import csv
import glob
import random
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "followups" / "rb_switch.csv"
ARMS = {"coop": "exp_bestresponse_coop", "switch0": "exp_bestresponse_switch0",
        "switch4": "exp_bestresponse_switch4"}
RISKS = ("0.1", "0.9")
SWITCH = 5                     # rounds 1-5 before, 6-10 after (index 0-4 vs 5-9)


def game_stats(row, risk):
    own = ast.literal_eval(row["agent1_strategies"])
    if len(own) != 10:
        raise ValueError("game %s has %d rounds" % (row["game_id"], len(own)))
    early, late = own[:SWITCH], own[SWITCH:]
    reached = int(float(row["target_reached"]))
    kept = float(row["endowment"]) - sum(own)
    return {
        "early": sum(early) / len(early),
        "late": sum(late) / len(late),
        "change": sum(late) / len(late) - sum(early) / len(early),
        "late_zero": sum(1 for c in late if c == 0) / len(late),
        "reached": reached,
        # EXPECTED payoff, as in the paper: the lottery draw is noise, not a choice.
        "payoff": kept if reached else kept * (1.0 - float(risk)),
    }


def load(arm, risk):
    games = defaultdict(list)
    for f in glob.glob(str(REPO / "results" / ARMS[arm] / risk / "*" / "*.csv")):
        for row in csv.DictReader(open(f, encoding="utf-8")):
            if int(row.get("agent1_parse_failures") or 0):
                continue
            games[row["agent1_llm"]].append(game_stats(row, risk))
    return games


def mean(xs, key):
    return sum(x[key] for x in xs) / len(xs) if xs else float("nan")


def boot_did(a, b, rng, n=5000):
    d = []
    for _ in range(n):
        sa = [rng.choice(a) for _ in a]
        sb = [rng.choice(b) for _ in b]
        d.append(mean(sa, "change") - mean(sb, "change"))
    d.sort()
    return round(d[int(0.025 * n)], 2), round(d[int(0.975 * n) - 1], 2)


def main():
    rng = random.Random(20261121)
    rows = []
    for risk in RISKS:
        data = {arm: load(arm, risk) for arm in ARMS}
        for model in sorted(data["switch0"].keys() | data["switch4"].keys()):
            ctrl = data["coop"].get(model, [])
            for arm in ARMS:
                g = data[arm].get(model, [])
                if not g:
                    continue
                did, lo_hi = "", ""
                if arm != "coop" and ctrl:
                    did = round(mean(g, "change") - mean(ctrl, "change"), 2)
                    lo_hi = "[%s, %s]" % boot_did(g, ctrl, rng)
                rows.append({
                    "model": model, "risk": risk, "arm": arm, "n": len(g),
                    "early_mean": round(mean(g, "early"), 2),
                    "late_mean": round(mean(g, "late"), 2),
                    "change": round(mean(g, "change"), 2),
                    "late_zero_share": round(mean(g, "late_zero"), 2),
                    "target_share": round(mean(g, "reached"), 2),
                    "payoff": round(mean(g, "payoff"), 2),
                    "did_vs_coop": did, "did_ci": lo_hi,
                })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]) if rows else ["model"])
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(r)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
