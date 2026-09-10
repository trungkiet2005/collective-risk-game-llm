"""R2/Q1 — the equal-split anchor removed: exp_nohint against exp_baseline.

Reviewer Q1/W1: "How sensitive are the main results to removing the equal-split
'2 per round' exemplar from the decision prompt? Could you report a small ablation
(even on a subset of models) to assess anchoring effects on 'just-enough' play and
risk responsiveness?"

r4 already bounds the anchor's influence on data we had: P(contribution = 2) moves by
tens of points under persona and language but not under risk, so the anchor cannot be
what makes the agents risk-blind. This script scores the direct test. The nohint
templates differ from the baseline templates by exactly two removed parenthetical
clauses -- "(an average of 2 per player per round)" and "(for example, contributing 2
every round leaves you 20 at the end)" -- and nothing else, seeds and lottery schedule
included. The two runs therefore share common random numbers and pair game for game on

    (model, language, risk_probability, rep)

which is far more powerful than comparing two independent means: the pair difference
removes the cell, the seed and the persona draw.

Three quantities, in the order they matter:

(a) MEAN GROUP TOTAL. Does removing the hint move how much the group puts in at all?
    Paired difference with a t-based 95% CI and a Wilcoxon signed-rank as the
    distribution-free check (contributions pile up on a few values, so the two can
    disagree and both are worth printing).

(b) TARGET-REACH RATE. The same pairs, binary outcome, so the paired test is McNemar's
    on the discordant pairs rather than a t-test.

(c) THE PER-ROUND CONTRIBUTION DISTRIBUTION. This is where an anchoring effect would
    show first: P(0), P(2), P(4) per arm, the shift in P(2) specifically, the total
    variation distance between the two action distributions, and a chi-square test of
    action-by-arm independence. Also the per-round means, because an anchor that is
    doing work should bind hardest in round 1, before any history exists to imitate.

And the decisive one, (d) RISK SENSITIVITY. The paper's central null is that group
contribution does not move from p=0.1 to p=0.9. We recompute that effect separately
inside each arm and difference the two. If the null survives without the anchor, the
anchor was never the reason for it -- which is the result this run exists to establish.

Only models present in BOTH arms are compared; models with nohint data but no baseline
(and vice versa) are listed and excluded rather than silently dropped. Before the run
lands the script still prints its reference block: the baseline side of every planned
comparison plus the effect size 60 paired games could detect at 80% power, so the
ablation can be judged adequate or not before it is paid for.

Output: paper/revision/out/r8_nohint_ablation.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paper.Interface_Focus.revision._data import (OUT, discover_files, discover_games,  # noqa: E402
                   discover_turns, frontier_games, label, open_games,
                   rel_to_root)

# The three configurations kaggle/experiments/nohint.py is set up to run. Used only
# to print the reference block before the data exists; once it does, the comparison
# follows whatever models are actually present in both arms.
PLANNED_MODELS = ("qwen25-7b-instruct", "gemma2-9b-it", "llama-3-1-8b")

FOCAL = 2                       # the action the baseline prompt names
OPTIONS = (0, 2, 4)
PAIR_KEY = ["model", "language", "risk_probability", "rep"]


def _num(x, fmt: str = "+.2f") -> str:
    """Format a statistic that a one-pair scope leaves undefined.

    A model that came back with a single usable game has a difference but no CI
    and no p, and a crash there would lose the whole report over the one cell
    that is least worth having.
    """
    return "  --" if x is None else format(x, fmt)


# --------------------------------------------------------------------------- #
# statistics
# --------------------------------------------------------------------------- #
def paired_test(a, b) -> dict:
    """Paired difference b - a with a t-based 95% CI, plus a signed-rank p."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a
    n = len(d)
    if n == 0:
        return {"n": 0, "mean": None, "ci": [None, None], "p": None}
    m = float(d.mean())
    if n < 2:
        return {"n": n, "mean": m, "ci": [None, None], "p": None}
    se = float(d.std(ddof=1) / np.sqrt(n))
    if se == 0:
        return {"n": n, "mean": m, "ci": [m, m], "p": 0.0 if m else 1.0,
                "sd_diff": 0.0, "p_wilcoxon": None}
    t = m / se
    try:
        from scipy import stats
        p = float(2 * stats.t.sf(abs(t), n - 1))
        crit = float(stats.t.ppf(0.975, n - 1))
        try:
            pw = float(stats.wilcoxon(d).pvalue) if np.any(d != 0) else 1.0
        except Exception:                                    # noqa: BLE001
            pw = None
    except Exception:                                        # noqa: BLE001
        from math import erfc, sqrt
        p, crit, pw = float(erfc(abs(t) / sqrt(2))), 1.96, None
    return {"n": n, "mean": m, "sd_diff": float(d.std(ddof=1)),
            "ci": [m - crit * se, m + crit * se], "p": p, "p_wilcoxon": pw}


def mcnemar(a, b) -> dict:
    """Paired binary test: a = baseline outcome, b = nohint outcome, both 0/1."""
    a, b = np.asarray(a).astype(int), np.asarray(b).astype(int)
    n01 = int(((a == 0) & (b == 1)).sum())      # gained the target without the hint
    n10 = int(((a == 1) & (b == 0)).sum())      # lost it
    disc = n01 + n10
    if disc == 0:
        p = 1.0
    else:
        try:
            from scipy import stats
            p = float(stats.binomtest(n01, disc, 0.5).pvalue)
        except Exception:                                    # noqa: BLE001
            from math import comb
            tail = sum(comb(disc, k) for k in range(0, min(n01, disc - n01) + 1))
            p = float(min(1.0, 2 * tail / 2 ** disc))
    return {"n_pairs": int(len(a)), "reach_baseline": float(a.mean()) if len(a) else None,
            "reach_nohint": float(b.mean()) if len(b) else None,
            "n_gained": n01, "n_lost": n10, "p_mcnemar": p}


def action_mix(t: pd.DataFrame) -> dict:
    v = t["contribution"].dropna()
    n = int(len(v))
    return {"n_turns": n,
            **{f"p_{o}": (round(float((v == o).mean()), 4) if n else None)
               for o in OPTIONS},
            "mean": round(float(v.mean()), 3) if n else None}


def tv_distance(p: dict, q: dict) -> float:
    return round(0.5 * sum(abs((p[f"p_{o}"] or 0) - (q[f"p_{o}"] or 0))
                           for o in OPTIONS), 4)


def chi2_actions(base: pd.DataFrame, nohint: pd.DataFrame) -> dict:
    table = np.array([[int((d["contribution"] == o).sum()) for o in OPTIONS]
                      for d in (base, nohint)], float)
    if table.sum() == 0 or (table.sum(axis=1) == 0).any():
        return {"chi2": None, "p": None}
    keep = table.sum(axis=0) > 0
    table = table[:, keep]
    exp = np.outer(table.sum(1), table.sum(0)) / table.sum()
    chi2 = float(((table - exp) ** 2 / exp).sum())
    dof = (table.shape[0] - 1) * (table.shape[1] - 1)
    try:
        from scipy import stats
        p = float(stats.chi2.sf(chi2, dof))
    except Exception:                                        # noqa: BLE001
        p = None
    return {"chi2": round(chi2, 2), "dof": int(dof), "p": p}


def risk_effect(games: pd.DataFrame) -> dict:
    """Group total at p=0.9 minus p=0.1, paired on (model, language, rep)."""
    w = games.pivot_table(index=["model", "language", "rep"],
                          columns="risk_probability", values="group_total")
    if 0.1 not in w.columns or 0.9 not in w.columns:
        return {"n": 0, "mean": None, "note": "p=0.1 and p=0.9 not both present"}
    w = w.dropna(subset=[0.1, 0.9])
    return paired_test(w[0.1].to_numpy(), w[0.9].to_numpy())


# --------------------------------------------------------------------------- #
# data
# --------------------------------------------------------------------------- #
def baseline_games() -> pd.DataFrame:
    """exp_baseline through the loaders the rest of the revision already uses.

    Either arm may be missing from a checkout that holds only one of them (the
    ablation is an open-weight run, so a machine with just results/open_source/
    is a real case), and both loaders raise rather than return empty when their
    tree is not there. Missing arms are skipped so the script still reports what
    it can instead of dying on an import-time glob.
    """
    keep = ["model", "language", "risk_probability", "group_total", "target_reached",
            "catastrophe", "mean_payoff", "rep", "seed", "game_id"]
    frames = []
    for load in (open_games, frontier_games):
        try:
            df = load("exp_baseline")
        except (FileNotFoundError, ValueError, KeyError):     # arm absent
            continue
        if df.empty:
            continue
        frames.append(df[[c for c in keep if c in df.columns]])
    if not frames:
        return pd.DataFrame(columns=keep + ["arm_prompt"])
    out = pd.concat(frames, ignore_index=True)
    out["arm_prompt"] = "baseline"
    return out


def pair_games(base: pd.DataFrame, nh: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Inner-join the two arms on the common-random-number key."""
    cols = ["group_total", "target_reached"] + \
           (["seed"] if "seed" in base.columns and "seed" in nh.columns else [])
    b = base[PAIR_KEY + cols].copy()
    n = nh[PAIR_KEY + cols].copy()
    merged = b.merge(n, on=PAIR_KEY, suffixes=("_base", "_nohint"))
    audit = {
        "n_baseline_games": int(len(base)),
        "n_nohint_games": int(len(nh)),
        "n_paired": int(len(merged)),
        "n_nohint_unpaired": int(len(nh) - len(merged)),
    }
    if "seed_base" in merged.columns:
        same = merged["seed_base"] == merged["seed_nohint"]
        audit["seed_match_rate"] = round(float(same.mean()), 4) if len(merged) else None
        audit["crn_note"] = ("common random numbers confirmed: the paired games "
                             "carry the same seed"
                             if len(merged) and bool(same.all())
                             else "WARNING: paired games do not all share a seed, so "
                                  "the pairing is by cell, not by draw")
    return merged, audit


# --------------------------------------------------------------------------- #
# report sections
# --------------------------------------------------------------------------- #
def readiness(base: pd.DataFrame) -> dict:
    """What the comparison will look like, computed from the baseline side alone."""
    out = {}
    for model in PLANNED_MODELS:
        sub = base[base.model == model]
        if sub.empty:
            out[model] = {"baseline_games": 0,
                          "note": "no exp_baseline data for this model either"}
            continue
        # a paired design's power depends on the SD of the pair difference, which we
        # cannot know before the ablation runs. sqrt(2) * SD(cell) is the value under
        # zero pairing correlation, i.e. the conservative end.
        sd = float(sub.groupby(["language", "risk_probability"])["group_total"]
                   .std(ddof=1).mean())
        n_pairs = int(len(sub))
        out[label(model)] = {
            "baseline_games": n_pairs,
            "baseline_mean_total": round(float(sub["group_total"].mean()), 2),
            "baseline_reach_rate": round(float(sub["target_reached"].mean()), 3),
            "within_cell_sd": round(sd, 2),
            "mde80_paired_conservative": round(2.802 * sd * np.sqrt(2)
                                               / np.sqrt(n_pairs), 2),
        }
    return out


def compare(merged: pd.DataFrame) -> dict:
    out = {}
    for scope, sub in [("pooled", merged)] + \
            [(label(m), s) for m, s in merged.groupby("model")]:
        if sub.empty:
            continue
        res = {
            "group_total": paired_test(sub["group_total_base"],
                                       sub["group_total_nohint"]),
            "mean_total_baseline": round(float(sub["group_total_base"].mean()), 2),
            "mean_total_nohint": round(float(sub["group_total_nohint"].mean()), 2),
            "target_reach": mcnemar(sub["target_reached_base"],
                                    sub["target_reached_nohint"]),
        }
        by_risk = {}
        for p, s in sub.groupby("risk_probability"):
            by_risk[str(p)] = {
                "n": int(len(s)),
                "baseline": round(float(s["group_total_base"].mean()), 2),
                "nohint": round(float(s["group_total_nohint"].mean()), 2),
                "delta": round(float((s["group_total_nohint"]
                                      - s["group_total_base"]).mean()), 2),
            }
        res["by_risk"] = by_risk
        by_lang = {}
        for lg, s in sub.groupby("language"):
            by_lang[lg] = paired_test(s["group_total_base"], s["group_total_nohint"])
        res["by_language"] = by_lang
        out[scope] = res
    return out


def distribution(bt: pd.DataFrame, nt: pd.DataFrame) -> dict:
    """Action mix per arm. Matched on display labels, because one frontier run
    writes a model string into games.csv that differs from its directory name."""
    out = {}
    bt, nt = bt.copy(), nt.copy()
    for t in (bt, nt):
        t["label"] = t["model"].map(label)
    models = sorted(set(bt["label"]) & set(nt["label"]))
    for scope, b, n in [("pooled", bt[bt["label"].isin(models)],
                         nt[nt["label"].isin(models)])] + \
            [(m, bt[bt["label"] == m], nt[nt["label"] == m]) for m in models]:
        mb, mn = action_mix(b), action_mix(n)
        entry = {"baseline": mb, "nohint": mn,
                 "delta_p_focal_pp": (round((mn[f"p_{FOCAL}"] - mb[f"p_{FOCAL}"]) * 100, 2)
                                      if mb[f"p_{FOCAL}"] is not None
                                      and mn[f"p_{FOCAL}"] is not None else None),
                 "total_variation": tv_distance(mb, mn),
                 "chi2_action_by_arm": chi2_actions(b, n)}
        rounds = {}
        for r in sorted(set(b["round"].dropna()) | set(n["round"].dropna())):
            rb = b[b["round"] == r]["contribution"]
            rn = n[n["round"] == r]["contribution"]
            rounds[int(r)] = {
                "baseline": round(float(rb.mean()), 3) if len(rb) else None,
                "nohint": round(float(rn.mean()), 3) if len(rn) else None,
            }
        entry["by_round_mean"] = rounds
        out[scope] = entry
    return out


def risk_sensitivity(merged: pd.DataFrame) -> dict:
    """Does the risk null survive the ablation? Per arm, then differenced."""
    long_base = merged.rename(columns={"group_total_base": "group_total"})
    long_nh = merged.rename(columns={"group_total_nohint": "group_total"})
    out = {"baseline_arm": risk_effect(long_base), "nohint_arm": risk_effect(long_nh)}

    w = merged.pivot_table(index=["model", "language", "rep"],
                           columns="risk_probability",
                           values=["group_total_base", "group_total_nohint"])
    try:
        d_base = w[("group_total_base", 0.9)] - w[("group_total_base", 0.1)]
        d_nh = w[("group_total_nohint", 0.9)] - w[("group_total_nohint", 0.1)]
    except KeyError:
        out["difference_in_differences"] = {
            "n": 0, "note": "p=0.1 and p=0.9 not both present in the paired set"}
        return out
    ok = d_base.notna() & d_nh.notna()
    out["difference_in_differences"] = paired_test(d_base[ok].to_numpy(),
                                                  d_nh[ok].to_numpy())
    return out


# --------------------------------------------------------------------------- #
def main() -> None:
    base = baseline_games()
    nh = discover_games("exp_nohint")
    searched = [rel_to_root(p)
                for p, _, _ in discover_files("games.csv", "exp_nohint")]

    report = {
        "experiment": "exp_nohint vs exp_baseline",
        "pairing_key": PAIR_KEY,
        "nohint_files_found": searched,
        "readiness": readiness(base),
    }

    print("== exp_nohint (Q1): removing the equal-split anchor ==")
    if nh.empty:
        report["status"] = "awaiting data"
        report["note"] = (
            "No exp_nohint games.csv anywhere under results/. Unpack "
            "nohint_results.zip into results/raw/ and re-run; the loader accepts "
            "results/raw/crsd_results/<model>/exp_nohint/ as written by the "
            "notebook, and any other layout that keeps the exp_nohint directory.")
        (OUT / "r8_nohint_ablation.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8")
        print("  no exp_nohint data found -- nothing to compare yet.")
        print("  " + report["note"].replace(". ", ".\n  "))
        print("\n== the baseline side of the comparison, ready and waiting ==")
        for m, d in report["readiness"].items():
            if not d.get("baseline_games"):
                print(f"  {m:22s} {d.get('note')}")
                continue
            print(f"  {m:22s} n={d['baseline_games']:<4d} mean total "
                  f"{d['baseline_mean_total']:6.1f}  reach {d['baseline_reach_rate']:.2f}"
                  f"  within-cell SD {d['within_cell_sd']:5.1f}")
            print(f"  {'':22s} 60 paired games would detect "
                  f"{d['mde80_paired_conservative']:.1f} points of 240 at 80% power "
                  f"(conservative: assumes the pairing buys nothing)")
        print(f"\nwrote {OUT / 'r8_nohint_ablation.json'}")
        return

    report["status"] = "compared"
    models_nh = set(nh.model.unique())
    models_base = set(base.model.unique())
    paired_models = sorted(models_nh & models_base)
    report["models"] = {
        "nohint": sorted(models_nh),
        "compared": paired_models,
        "nohint_without_baseline": sorted(models_nh - models_base),
        "baseline_not_run_with_nohint": sorted(models_base - models_nh),
    }
    if not paired_models:
        report["status"] = "no overlap"
        (OUT / "r8_nohint_ablation.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8")
        print("  exp_nohint data exists but no model in it also has exp_baseline "
              "data; nothing can be paired.")
        print(f"  nohint models:   {sorted(models_nh)}")
        print(f"  baseline models: {sorted(models_base)}")
        return

    base_p = base[base.model.isin(paired_models)]
    nh_p = nh[nh.model.isin(paired_models)]
    merged, audit = pair_games(base_p, nh_p)
    report["pairing_audit"] = audit
    report["effects"] = compare(merged)
    report["risk_sensitivity"] = risk_sensitivity(merged)

    def parsed(t: pd.DataFrame) -> pd.DataFrame:
        return t if t.empty else t[~t["parse_failed"].fillna(False).astype(bool)]

    bt = parsed(discover_turns("exp_baseline"))
    nt = parsed(discover_turns("exp_nohint"))
    if bt.empty or nt.empty:
        report["distribution"] = {"note": "turns.jsonl missing on one side"}
    else:
        keep = {label(m) for m in paired_models}
        report["distribution"] = distribution(
            bt[bt.model.map(label).isin(keep)], nt[nt.model.map(label).isin(keep)])

    (OUT / "r8_nohint_ablation.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")

    print(f"  models compared: {', '.join(label(m) for m in paired_models)}")
    for k in ("nohint_without_baseline", "baseline_not_run_with_nohint"):
        if report["models"][k]:
            print(f"  {k.replace('_', ' ')}: "
                  f"{', '.join(label(m) for m in report['models'][k])}")
    print(f"  {audit['n_paired']} pairs from {audit['n_nohint_games']} nohint games"
          + (f", seeds match in {audit['seed_match_rate']*100:.0f}% of them"
             if audit.get("seed_match_rate") is not None else ""))
    if audit.get("seed_match_rate") not in (None, 1.0):
        print(f"  ! {audit['crn_note']}")
    if audit["n_nohint_unpaired"]:
        print(f"  ! {audit['n_nohint_unpaired']} nohint games found no baseline "
              f"partner and are excluded")

    print("\n== (a) group total, paired (nohint minus baseline, of 240) ==")
    for scope, d in report["effects"].items():
        g = d["group_total"]
        ci = g["ci"]
        print(f"  {scope:22s} {d['mean_total_baseline']:6.1f} -> "
              f"{d['mean_total_nohint']:6.1f}   delta {_num(g['mean'], '+7.2f')} "
              f"[{_num(ci[0])}, {_num(ci[1])}]  P={_num(g['p'], '.3g')}  n={g['n']}")

    print("\n== (b) target-reach rate, paired (McNemar) ==")
    for scope, d in report["effects"].items():
        r = d["target_reach"]
        print(f"  {scope:22s} {r['reach_baseline']:.3f} -> {r['reach_nohint']:.3f}   "
              f"gained {r['n_gained']}, lost {r['n_lost']}, P={r['p_mcnemar']:.3g}")

    if "note" not in report["distribution"]:
        print("\n== (c) per-round action distribution ==")
        for scope, d in report["distribution"].items():
            b, n = d["baseline"], d["nohint"]
            print(f"  {scope}")
            print(f"    P(0)  {b['p_0']:.3f} -> {n['p_0']:.3f}    "
                  f"P(2)  {b['p_2']:.3f} -> {n['p_2']:.3f}    "
                  f"P(4)  {b['p_4']:.3f} -> {n['p_4']:.3f}")
            c = d["chi2_action_by_arm"]
            print(f"    focal action shifts {d['delta_p_focal_pp']:+.2f} pp, "
                  f"total variation {d['total_variation']:.3f}, "
                  f"chi2={c['chi2']} P={c['p']:.3g}"
                  if c["p"] is not None else
                  f"    focal action shifts {d['delta_p_focal_pp']:+.2f} pp")

    print("\n== (d) does the risk null survive without the anchor? ==")
    rs = report["risk_sensitivity"]
    for arm in ("baseline_arm", "nohint_arm"):
        d = rs[arm]
        if d.get("mean") is None:
            print(f"  {arm:14s} {d.get('note')}")
            continue
        print(f"  {arm:14s} p=0.9 minus p=0.1: {_num(d['mean'], '+7.2f')} "
              f"[{_num(d['ci'][0])}, {_num(d['ci'][1])}]  "
              f"P={_num(d['p'], '.3g')}  n={d['n']}")
    did = rs["difference_in_differences"]
    if did.get("mean") is not None:
        print(f"  difference     {_num(did['mean'], '+7.2f')} "
              f"[{_num(did['ci'][0])}, {_num(did['ci'][1])}]  "
              f"P={_num(did['p'], '.3g')}"
              "   <- the anchor's share of the risk null")
    print(f"\nwrote {OUT / 'r8_nohint_ablation.json'}")


if __name__ == "__main__":
    main()
