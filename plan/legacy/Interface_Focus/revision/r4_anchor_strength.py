"""R1/W1/Q1 — how strong is the equal-split anchor, measured on data we already have.

Reviewer W1/Q1: the decision prompt names the equal-split solution ("an average of 2
per player per round"), which supplies a risk-independent focal action and may be what
produces "just-enough" play.

The clean answer is an ablation that removes the hint, and we run one. But the existing
data already bounds how much of the risk null the anchor can possibly explain, and the
bound is what makes the ablation interpretable rather than exploratory. The argument is
one of relative strength:

  If agents were locked onto the focal action, NOTHING in the prompt could move them.
  We can measure that directly: P(contribution = 2) under each manipulation. If the
  anchor were binding, P(2) would be insensitive to persona, to salience and to
  language as well as to risk. It is not: those three move it by tens of points while
  risk does not. An anchor that yields to a one-sentence persona cannot be the reason
  agents ignore a ninefold change in the probability of ruin.

We also report where the anchor is visibly overridden: the two expected-value models
contribute 0 at p = 0.1, which requires refusing the only number the prompt offers.

Output: paper/revision/out/r4_anchor_strength.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _data import OUT, RESULTS, all_turns, label      # noqa: E402

FOCAL = 2


def action_mix(t: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    g = t.groupby(by)["contribution"]
    return pd.DataFrame({
        "p_focal": g.apply(lambda s: float((s == FOCAL).mean())),
        "p_zero": g.apply(lambda s: float((s == 0).mean())),
        "p_max": g.apply(lambda s: float((s == 4).mean())),
        "n": g.size(),
    }).reset_index()


def spread(df: pd.DataFrame, key: str) -> dict:
    """Max-minus-min of P(focal) across the levels of `key`, per model."""
    out = {}
    for model, sub in df.groupby("model"):
        if sub[key].nunique() < 2:
            continue
        v = sub.groupby(key)["p_focal"].mean()
        out[label(model)] = {
            "levels": {str(k): round(float(x), 4) for k, x in v.items()},
            "range_pp": round(float(v.max() - v.min()) * 100, 2),
        }
    return out


def main() -> None:
    base = all_turns("exp_baseline")
    base = base[~base["parse_failed"].fillna(False).astype(bool)]
    per = all_turns("exp_persona")
    per = per[~per["parse_failed"].fillna(False).astype(bool)]

    # --- how often is the focal action taken at all -------------------------
    overall = action_mix(base, ["model"]).assign(
        label=lambda d: d["model"].map(label))

    # --- what moves P(focal): risk, language, persona composition -----------
    by_risk = action_mix(base, ["model", "risk_probability"])
    by_lang = action_mix(base, ["model", "language"])

    per = per.copy()
    per["n_selfish"] = per["persona_set"].str.extract(r"(\d)sel").astype(float)
    per.loc[per["persona_set"] == "personas_cooperative", "n_selfish"] = 0.0
    per.loc[per["persona_set"] == "personas_selfish", "n_selfish"] = 6.0
    by_comp = action_mix(per.dropna(subset=["n_selfish"]), ["model", "n_selfish"])
    by_risk_persona = action_mix(per, ["model", "risk_probability"])

    report = {
        "focal_action": FOCAL,
        "overall_p_focal": {r["label"]: {"p_focal": round(r["p_focal"], 4),
                                         "p_zero": round(r["p_zero"], 4),
                                         "p_max": round(r["p_max"], 4),
                                         "n_turns": int(r["n"])}
                            for _, r in overall.iterrows()},
        "moved_by_risk_baseline": spread(by_risk, "risk_probability"),
        "moved_by_language_baseline": spread(by_lang, "language"),
        "moved_by_composition": spread(by_comp, "n_selfish"),
        "moved_by_risk_in_composition": spread(by_risk_persona, "risk_probability"),
    }

    # --- headline comparison: median range across models, per manipulation --
    def median_range(d: dict) -> float:
        vals = [v["range_pp"] for v in d.values()]
        return round(float(np.median(vals)), 2) if vals else float("nan")

    report["median_range_pp"] = {
        "risk (baseline)": median_range(report["moved_by_risk_baseline"]),
        "risk (composition study)": median_range(report["moved_by_risk_in_composition"]),
        "language (baseline)": median_range(report["moved_by_language_baseline"]),
        "composition 0->6 selfish": median_range(report["moved_by_composition"]),
    }

    # --- where the anchor is demonstrably overridden ------------------------
    ev = base[(base["model"].isin(["google-gemini-3.1-pro-preview",
                                   "openai-gpt-5.6-sol"]))
              & (base["risk_probability"] == 0.1) & (base["language"] == "en")]
    report["anchor_overridden_at_p01_en"] = {
        label(m): {"p_zero": round(float((s["contribution"] == 0).mean()), 4),
                   "p_focal": round(float((s["contribution"] == FOCAL).mean()), 4),
                   "n_turns": int(len(s))}
        for m, s in ev.groupby("model")
    }

    # --- the decisive test: is the risk null confined to anchor-followers? ---
    # If anchoring produced the null, models that rarely take the focal action would
    # be free to respond to risk and should show a larger risk effect. We correlate
    # P(focal) with the absolute English risk effect across the fourteen
    # configurations, and report the null separately for the models at each extreme.
    risk_effect = {}
    for model, sub in base[base.language == "en"].groupby("model"):
        gt = (sub.groupby(["game_id", "risk_probability"])["contribution"].sum()
              .reset_index().groupby("risk_probability")["contribution"].mean())
        if {0.1, 0.9}.issubset(set(gt.index)):
            risk_effect[label(model)] = float(gt.loc[0.9] - gt.loc[0.1])
    pairs = [(report["overall_p_focal"][m]["p_focal"], abs(e), m)
             for m, e in risk_effect.items() if m in report["overall_p_focal"]]
    if len(pairs) >= 3:
        x = np.array([p[0] for p in pairs])
        y = np.array([p[1] for p in pairs])
        r = float(np.corrcoef(x, y)[0, 1])
    else:
        r = float("nan")
    lo = sorted(pairs)[:4]
    hi = sorted(pairs)[-4:]
    report["anchor_vs_risk_effect"] = {
        "pearson_r_p_focal_vs_abs_risk_effect": round(r, 3),
        "weakest_anchor_grip": [{"model": m, "p_focal": round(pf, 3),
                                 "abs_risk_effect": round(ae, 2)} for pf, ae, m in lo],
        "strongest_anchor_grip": [{"model": m, "p_focal": round(pf, 3),
                                   "abs_risk_effect": round(ae, 2)} for pf, ae, m in hi],
    }

    (OUT / "r4_anchor_strength.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")

    print("== P(contribution = 2), the focal action named by the prompt ==")
    for m, d in sorted(report["overall_p_focal"].items(),
                       key=lambda kv: -kv[1]["p_focal"]):
        print(f"  {m:24s} focal {d['p_focal']:.3f}  zero {d['p_zero']:.3f}  "
              f"max {d['p_max']:.3f}  (n={d['n_turns']})")

    print("\n== how far each manipulation moves P(focal), percentage points ==")
    print("   (median over the models run in that arm)")
    for k, v in report["median_range_pp"].items():
        print(f"  {k:28s} {v:>6.2f} pp")

    print("\n== the anchor is overridden where it matters most ==")
    for m, d in report["anchor_overridden_at_p01_en"].items():
        print(f"  {m:22s} contributes 0 in {d['p_zero']*100:.1f}% of turns at "
              f"p=0.1 (focal action taken {d['p_focal']*100:.1f}%)")

    av = report["anchor_vs_risk_effect"]
    print("\n== is the risk null confined to models that follow the anchor? ==")
    print(f"  corr(P(focal), |risk effect|) = "
          f"{av['pearson_r_p_focal_vs_abs_risk_effect']}")
    print("  weakest grip on the focal action:")
    for d in av["weakest_anchor_grip"]:
        print(f"    {d['model']:24s} P(focal)={d['p_focal']:.3f}  "
              f"|risk effect|={d['abs_risk_effect']:.1f}")
    print("  strongest grip on the focal action:")
    for d in av["strongest_anchor_grip"]:
        print(f"    {d['model']:24s} P(focal)={d['p_focal']:.3f}  "
              f"|risk effect|={d['abs_risk_effect']:.1f}")


if __name__ == "__main__":
    main()
