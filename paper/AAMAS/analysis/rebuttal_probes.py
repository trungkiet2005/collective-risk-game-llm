"""Analyse the rebuttal probe wave (crg-rb-probe). Rules fixed 2026-11-21 before any data.

Counterfactual (cf): the exact base decision prompt, focal seat contributed 2 in every past
round, only partners' past moves differ. Per model and risk: mean contribution per history,
share of contributions > 0, and the best response if partners keep their pattern:
    fair      p=0.1 -> 0, p=0.9 -> 2      generous, settled, defect, drop -> 0
    r1 (round 1, no history) has no best response without beliefs; reported only.
"Responds to partners" = contribution differs across fair/generous/defect/drop
(permutation test of the between-history variance, 5000 shuffles).
"settled" is the dominated case: any positive contribution lowers own payoff, p < 1.

Explain: keyword coding of the free-text reasons, coded categories fixed here:
    fair_share  equal split / share / average of 2 / 2 per round
    target      reaching the target / 120 / threshold
    mentions_risk  disaster / risk / lottery / probability
    own_payoff  own payoff / expected value / maximise / keep more
    norm        cooperation / fairness / altruism / responsibility / help the group
    zero_risk   says there is no risk (only meaningful at p=0); amended 2026-11-21 after the
                first shard: the fixed pattern missed "probability is 0%", widened, "100%" excluded
    settled     says the target is already reached / secured
Recognition: names a known game (collective-risk / Milinski / climate game / threshold
public goods / public goods / social dilemma / commons / volunteer's dilemma).

    python paper/AAMAS/analysis/rebuttal_probes.py <download_root>
"""
import csv
import glob
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent / "followups"
BR = {("fair", 0.1): 0, ("fair", 0.9): 2, ("generous", 0.1): 0, ("generous", 0.9): 0,
      ("settled", 0.1): 0, ("settled", 0.9): 0, ("defect", 0.1): 0, ("defect", 0.9): 0,
      ("drop", 0.1): 0, ("drop", 0.9): 0}
CODES = {
    "fair_share": r"fair share|equal (split|share)|my (fair )?share|average of 2|2 per (player per )?round|equal(ly)? divid|split (the burden|equally)|evenly",
    "target": r"target|120|threshold|reach the goal",
    "mentions_risk": r"disaster|risk|lottery|probabilit|\d+% chance",
    "own_payoff": r"(my|own) (final )?(cash )?payoff|expected (value|payoff)|maximi[sz]|keep more|self-interest|my earnings|free.?rid",
    "norm": r"cooperat|fair(ness)?\b|altruis|responsib|help the group|collective (good|interest)|do my part|contribute my part|good faith|trust",
    "zero_risk": r"(?<![\d.])0 ?%|no risk|zero risk|no (chance of )?disaster|never (be )?hit|risk is 0|probability (is |of )?0\b|without (any )?risk",
    "settled": r"already (reached|met|exceeded|secured|surpassed)|target (is|has been) (already )?(reached|met|secured)|no (further|more) contributions? (are|is) needed|no need to contribute",
}
RECOG = r"collective.?risk|milinski|climate (game|dilemma|change game)|threshold public goods|public goods|social dilemma|tragedy of the commons|commons|volunteer"


def load(root):
    rows = []
    for f in glob.glob(str(Path(root) / "*" / "crg-rb-probe" / "**" / "games.csv"), recursive=True):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            r["risk"] = float(r["risk"])
            rows.append(r)
    seen, out = set(), []
    for r in rows:
        key = (r["model"], r["item"])
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def perm_between(groups, rng, n=5000):
    allv = [v for g in groups for v in g]
    sizes = [len(g) for g in groups]
    m = sum(allv) / len(allv)

    def stat(gs):
        return sum(len(g) * (sum(g) / len(g) - m) ** 2 for g in gs if g)
    obs = stat(groups)
    hit = 0
    for _ in range(n):
        s = allv[:]
        rng.shuffle(s)
        gs, i = [], 0
        for k in sizes:
            gs.append(s[i:i + k])
            i += k
        if stat(gs) >= obs - 1e-12:
            hit += 1
    return (hit + 1) / (n + 1)


def main(root):
    rng = random.Random(20261121)
    rows = load(root)
    if not rows:
        raise SystemExit("no probe rows under %s" % root)
    cf_out, ex_out, rc_out = [], [], []
    models = sorted({r["model"] for r in rows})
    for m in models:
        for p in (0.1, 0.9):
            groups = []
            for h in ("r1", "fair", "generous", "settled", "defect", "drop"):
                vals = [int(r["value"]) for r in rows if r["model"] == m and r["kind"] == "cf"
                        and r["history"] == h and r["risk"] == p and r["parse_failed"] == "0"]
                if not vals:
                    continue
                br = BR.get((h, p))
                cf_out.append(dict(model=m, risk=p, history=h, n=len(vals),
                                   mean=round(sum(vals) / len(vals), 2),
                                   share_pos=round(sum(v > 0 for v in vals) / len(vals), 2),
                                   best_response=("" if br is None else br),
                                   share_br=("" if br is None else
                                             round(sum(v == br for v in vals) / len(vals), 2))))
                if h in ("fair", "generous", "defect", "drop"):
                    groups.append(vals)
            if len(groups) == 4:
                cf_out.append(dict(model=m, risk=p, history="PERM_between_partner_histories",
                                   n=sum(len(g) for g in groups), mean="", share_pos="",
                                   best_response="", share_br=round(perm_between(groups, rng), 4)))
        for p in (0.0, 0.1, 0.9):
            for h in ("r1", "fair", "settled"):
                sub = [r for r in rows if r["model"] == m and r["kind"] == "explain"
                       and r["history"] == h and r["risk"] == p]
                if not sub:
                    continue
                rec = dict(model=m, risk=p, history=h, n=len(sub),
                           mean_contrib=round(sum(int(r["value"]) for r in sub) / len(sub), 2))
                for c, rx in CODES.items():
                    rec[c] = sum(bool(re.search(rx, r["raw_response"] or "", re.I)) for r in sub)
                ex_out.append(rec)
        for t in ("wording", "baseline"):
            sub = [r for r in rows if r["model"] == m and r["kind"] == "recog" and r["template"] == t]
            if sub:
                hits = [bool(re.search(RECOG, (r["raw_response"] or ""), re.I)) for r in sub]
                rc_out.append(dict(model=m, template=t, n=len(sub), names_known_game=sum(hits),
                                   examples=" || ".join((r["value"] or "")[:120] for r in sub[:2])))
    OUT.mkdir(parents=True, exist_ok=True)
    for name, data in (("rb_counterfactual.csv", cf_out), ("rb_explain.csv", ex_out),
                       ("rb_recognition.csv", rc_out)):
        with open(OUT / name, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(data[0]))
            w.writeheader()
            w.writerows(data)
        print("wrote", OUT / name, len(data))
    pf = sum(r["parse_failed"] == "1" for r in rows if r["kind"] != "recog")
    print(json.dumps({"rows": len(rows), "models": models, "decision_parse_failed": pf}))


if __name__ == "__main__":
    main(sys.argv[1])
