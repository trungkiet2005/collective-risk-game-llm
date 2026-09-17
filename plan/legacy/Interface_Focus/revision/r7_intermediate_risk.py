"""R1/Q8 — where exactly do the two step-function models pivot?

Reviewer Q8: "Have you tested additional intermediate risk levels (e.g. p = 0.3, 0.7) to
probe whether the two step-function models truly pivot at EV = 0.5 or if small
hysteresis/noise exists around the threshold?"

The expected-value indifference point is exactly p = 0.5: paying the target share leaves
20 for certain, withholding leaves (1-p)*40, and the two are equal at p = 0.5. Our
original grid (0.1, 0.5, 0.9) cannot say whether the pivot sits at 0.5 or merely
somewhere between 0.1 and 0.5. Adding p = 0.3 and p = 0.7 brackets it: at 0.3
withholding is still worth more (28 > 20), at 0.7 cooperating already is (12 < 20).

This script reads whatever risk levels are present, so it degrades gracefully before the
new shards land: it reports which cells exist and only draws the figure once at least
one model has more than three.

Output: paper/revision/out/r7_intermediate_risk.json + paper/figures/fig12_pivot.*
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paper.Interface_Focus.revision._data import FRONTIER_LABELS, OUT, frontier_games, label   # noqa: E402

# This is the one analysis that wants the p=0.3/0.7 cells; every other script
# takes the shared three-level grid so its cross-panel means stay comparable.

FIGDIR = Path(__file__).resolve().parents[1] / "figures"
TARGET, ENDOWMENT, N_PLAYERS = 120.0, 40.0, 6

# The four top-tier configurations the follow-up covers, in the order they are drawn.
PANEL = [
    ("google-gemini-3.1-pro-preview", "#0B84A5"),
    ("openai-gpt-5.6-sol", "#F6C85F"),
    ("anthropic-claude-opus-5-default", "#CA472F"),
    ("xai-grok-4.20-0309-reasoning", "#6F4E7C"),
]


def ev_prediction(p: float) -> float:
    """Group contribution a risk-neutral agent would produce at risk p."""
    keep_if_cooperate = ENDOWMENT - TARGET / N_PLAYERS      # 20
    ev_if_defect = (1.0 - p) * ENDOWMENT
    if abs(keep_if_cooperate - ev_if_defect) < 1e-9:
        return float("nan")                                  # indifferent
    return TARGET if keep_if_cooperate > ev_if_defect else 0.0


def summarise(df: pd.DataFrame) -> dict:
    out = {}
    for model, g in df[df.language == "en"].groupby("model"):
        rows = {}
        for p, gp in g.groupby("risk_probability"):
            rows[str(p)] = {
                "n_games": int(len(gp)),
                "contribution_mean": round(float(gp["group_total"].mean()), 2),
                "contribution_sd": round(float(gp["group_total"].std(ddof=0)), 2),
                "reach_rate": round(float(gp["target_reached"].mean()), 3),
                "ev_prediction": ev_prediction(float(p)),
            }
        out[label(model)] = rows
    return out


def pivot_location(rows: dict) -> dict:
    """Between which two tested risk levels does the model cross the target?"""
    ps = sorted(float(p) for p in rows)
    reach = [rows[str(p)]["reach_rate"] for p in ps]
    below = [p for p, r in zip(ps, reach) if r < 0.5]
    above = [p for p, r in zip(ps, reach) if r >= 0.5]
    if not below or not above:
        return {"tested_levels": ps, "crossing": None,
                "note": "reach never crosses 0.5 in the tested range"}
    return {"tested_levels": ps,
            "crossing": [max(below), min(above)],
            "consistent_with_ev_threshold": max(below) < 0.5 <= min(above)}


def make_figure(df: pd.DataFrame, summary: dict) -> bool:
    present = [(m, c) for m, c in PANEL if (df.model == m).any()]
    n_levels = max((df[df.model == m].risk_probability.nunique() for m, _ in present),
                   default=0)
    if n_levels <= 3:
        print(f"only {n_levels} risk levels present -- figure not drawn yet")
        return False

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 7.6, "axes.labelsize": 7.6,
                         "xtick.labelsize": 7, "ytick.labelsize": 7,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(7.1, 2.9))

    for ax in (axA, axB):
        ax.axvline(0.5, color="0.6", lw=0.9, ls="--", zorder=0)
    axA.text(0.508, 236, "EV indifference", fontsize=6.6, color="0.35",
             ha="left", va="top", rotation=90)

    for model, colour in present:
        sub = df[(df.model == model) & (df.language == "en")]
        g = sub.groupby("risk_probability")
        ps = sorted(sub.risk_probability.unique())
        mean = [g.get_group(p)["group_total"].mean() for p in ps]
        reach = [g.get_group(p)["target_reached"].mean() for p in ps]
        new = [p for p in ps if p not in (0.1, 0.5, 0.9)]
        lab = FRONTIER_LABELS[model][0]
        axA.plot(ps, mean, marker="o", ms=3.2, lw=1.3, color=colour, label=lab)
        axB.plot(ps, reach, marker="o", ms=3.2, lw=1.3, color=colour, label=lab)
        # ring the two follow-up levels so the reader sees what is new
        if new:
            axA.plot(new, [mean[ps.index(p)] for p in new], "o", ms=7,
                     mfc="none", mec=colour, mew=1.1, zorder=5)
            axB.plot(new, [reach[ps.index(p)] for p in new], "o", ms=7,
                     mfc="none", mec=colour, mew=1.1, zorder=5)

    axA.axhline(TARGET, color="0.55", lw=0.7, ls=":", zorder=0)
    axA.set_ylim(-14, 258)
    axA.set_ylabel("Group contribution (of 240)")
    axA.set_title("(a)  Contribution across five risk levels", loc="left", fontsize=8)
    axB.set_ylim(-0.07, 1.10)
    axB.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    axB.set_ylabel("Target-reach rate")
    axB.set_title("(b)  The two pivots are not in the same place", loc="left", fontsize=8)
    for ax in (axA, axB):
        ax.set_xlabel("Catastrophe risk $p$")
        ax.set_xticks([0.1, 0.3, 0.5, 0.7, 0.9])
        ax.set_xlim(0.02, 0.98)
    axA.legend(frameon=False, fontsize=6.6, handlelength=1.4, loc="upper left")

    fig.tight_layout()
    FIGDIR.mkdir(exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(FIGDIR / f"fig12_pivot.{ext}", dpi=300)
    plt.close(fig)
    print(f"wrote {FIGDIR / 'fig12_pivot.pdf'}")
    return True


def main() -> None:
    df = frontier_games("exp_baseline", all_risks=True)
    summary = summarise(df)
    pivots = {m: pivot_location(rows) for m, rows in summary.items()}
    report = {"by_model": summary, "pivot": pivots}
    (OUT / "r7_intermediate_risk.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")

    print("== risk levels present, English ==")
    for m, rows in summary.items():
        ps = ", ".join(sorted(rows, key=float))
        print(f"  {m:26s} p in [{ps}]")
    print("\n== contribution and reach by risk ==")
    for m, rows in summary.items():
        if len(rows) <= 3:
            continue
        print(f"  {m}")
        for p in sorted(rows, key=float):
            r = rows[p]
            ev = r["ev_prediction"]
            evs = "tie" if np.isnan(ev) else f"{ev:.0f}"
            print(f"    p={p:<4} n={r['n_games']:<3} contribution "
                  f"{r['contribution_mean']:6.1f} (SD {r['contribution_sd']:5.1f})  "
                  f"reach {r['reach_rate']:.2f}   EV says {evs}")
        pv = pivots[m]
        if pv.get("crossing"):
            lo, hi = pv["crossing"]
            print(f"    -> reach crosses 0.5 between p={lo} and p={hi}; "
                  f"consistent with the EV threshold: "
                  f"{pv['consistent_with_ev_threshold']}")
        else:
            print(f"    -> {pv['note']}")

    make_figure(df, summary)


if __name__ == "__main__":
    main()
