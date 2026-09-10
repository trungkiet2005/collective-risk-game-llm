"""R1/Q5 — round-by-round trajectories and within-game adaptation.

Reviewer Q5: "Can you report round-by-round trajectories (especially near the
threshold) to see whether models adapt contributions with accumulating evidence of
(not) reaching the target, and whether this adaptation interacts with risk?"

Three quantities, all from turns.jsonl, none requiring a new run:

1. TRAJECTORY. Mean per-agent contribution by round, split by catastrophe risk.
   If risk is ignored, the three curves lie on top of one another for the whole game.

2. PACE ADAPTATION. At the start of round r the group has pooled S and has
   (11-r) rounds left, so the per-agent contribution needed to still finish on target
   is  need(r) = (120 - S) / (6 * (11 - r)).  A group that tracks its own progress
   contributes more when need is high. We regress the agent's contribution on need,
   within model, and call the slope the *pace-tracking coefficient*: 1.0 would be an
   agent that exactly covers the remaining shortfall, 0.0 an agent that ignores it.

3. THE INTERACTION THE REVIEWER ASKS FOR. Adding risk and need x risk to that
   regression asks whether an agent that is falling behind pushes harder when the
   catastrophe is more likely. That is the within-game analogue of the paper's
   between-game risk null, and it is the sharper test: it holds the agent's own
   evidence of impending failure fixed and varies only what failure costs.

Also emits fig11_trajectories.pdf/.png for the manuscript.

Output: paper/revision/out/r3_round_trajectories.json + paper/figures/fig11_*.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paper.Interface_Focus.revision._data import OUT, RESULTS, all_turns, label     # noqa: E402

FIGDIR = Path(__file__).resolve().parents[1] / "figures"
TARGET, N_PLAYERS, N_ROUNDS = 120.0, 6, 10

# the panel shown in the figure: the two expected-value models, two flat top-tier
# models, and three open-weight models spanning the size range
FIG_MODELS = [
    ("google-gemini-3.1-pro-preview", "Gemini-3.1-Pro"),
    ("openai-gpt-5.6-sol", "GPT-5.6-sol"),
    ("anthropic-claude-opus-5-default", "Claude-Opus-5"),
    ("xai-grok-4.20-0309-reasoning", "Grok-4.20 (reasoning)"),
    ("qwen25-7b-instruct", "Qwen2.5-7B"),
    ("gemma2-9b-it", "Gemma-2-9B"),
    ("qwen25-72b-instruct-awq", "Qwen2.5-72B"),
    ("llama-3-1-70b-instruct-awq", "Llama-3.1-70B"),
]


def with_pace(t: pd.DataFrame) -> pd.DataFrame:
    """Add the pool before each round and the per-agent contribution still needed."""
    t = t.sort_values(["model", "game_id", "round", "player"]).copy()
    per_round = (t.groupby(["model", "game_id", "round"])["contribution"]
                 .sum().rename("round_total").reset_index())
    per_round["pool_before"] = (per_round.groupby(["model", "game_id"])["round_total"]
                                .cumsum() - per_round["round_total"])
    t = t.merge(per_round[["model", "game_id", "round", "pool_before"]],
                on=["model", "game_id", "round"], how="left")
    rounds_left = (N_ROUNDS + 1) - t["round"]
    t["need"] = (TARGET - t["pool_before"]) / (N_PLAYERS * rounds_left)
    t["need"] = t["need"].clip(lower=0.0)               # already past the target
    return t


def ols(X: np.ndarray, y: np.ndarray, names: list[str]) -> dict:
    n, k = X.shape
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = n - k
    s2 = float(resid @ resid) / dof
    cov = s2 * np.linalg.pinv(X.T @ X)
    se = np.sqrt(np.diag(cov))
    out = {}
    for i, nm in enumerate(names):
        t = beta[i] / se[i] if se[i] > 0 else 0.0
        try:
            from scipy import stats
            p = float(2 * stats.t.sf(abs(t), dof))
        except Exception:
            from math import erfc, sqrt
            p = float(erfc(abs(t) / sqrt(2)))
        out[nm] = {"coef": round(float(beta[i]), 4),
                   "se": round(float(se[i]), 4),
                   "p": float(f"{p:.4g}")}
    out["n"] = int(n)
    return out


def add_own_style(t: pd.DataFrame) -> pd.DataFrame:
    """The agent's own mean contribution in the rounds before this one.

    Needed as a control: `need` is mechanically depressed by the focal agent's own past
    generosity, so a raw regression of contribution on need partly regresses an agent's
    strategy on itself. Holding own style fixed, the remaining variation in need comes
    from the other five agents, which is exactly the "accumulating evidence" the
    reviewer asks about.
    """
    t = t.sort_values(["model", "game_id", "player", "round"]).copy()
    g = t.groupby(["model", "game_id", "player"])["contribution"]
    t["own_prior_mean"] = (g.cumsum() - t["contribution"]) / (t["round"] - 1)
    return t


def pace_models(t: pd.DataFrame) -> dict:
    """Per-model pace-tracking coefficient.

    Two nuisance sources have to be held out or the coefficient is uninterpretable.
    `own_prior_mean` removes the mechanical path by which an agent's own past
    generosity lowers `need`. Round dummies remove the fact that both `need` and the
    typical contribution move with the round number; with them in, the identifying
    variation in `need` is across games *within* a round, i.e. exactly how far ahead or
    behind this particular group is at this point in the game.
    """
    res = {}
    for model, sub in t.groupby("model"):
        sub = sub.dropna(subset=["need", "contribution", "risk_probability",
                                 "own_prior_mean"])
        # rounds 2..10 only: at round 1 `need` is a constant and own style is undefined
        sub = sub[sub["round"] >= 2]
        if len(sub) < 50 or sub["contribution"].nunique() < 2:
            res[label(model)] = {"n": int(len(sub)), "note": "degenerate"}
            continue
        need = sub["need"].to_numpy(float)
        risk = sub["risk_probability"].to_numpy(float)
        own = sub["own_prior_mean"].to_numpy(float)
        y = sub["contribution"].to_numpy(float)
        one = np.ones(len(sub))
        rd = pd.get_dummies(sub["round"], prefix="r", drop_first=True).to_numpy(float)
        rd_names = [f"round_{c}" for c in
                    pd.get_dummies(sub["round"], prefix="r", drop_first=True).columns]
        base = [one, need, own, rd]
        simple = ols(np.column_stack(base), y,
                     ["intercept", "need", "own_prior_mean"] + rd_names)
        inter = ols(np.column_stack([one, need, own, risk, need * risk, rd]), y,
                    ["intercept", "need", "own_prior_mean", "risk", "need_x_risk"]
                    + rd_names)
        res[label(model)] = {
            "pace_only": {k: simple[k] for k in ("intercept", "need",
                                                 "own_prior_mean", "n")},
            "with_risk": {k: inter[k] for k in ("need", "risk", "need_x_risk", "n")},
        }
    return res


def near_threshold(experiment: str = "exp_persona", t: pd.DataFrame | None = None) -> dict:
    """The reviewer's question asked where it actually bites: mixed-persona groups.

    In the baseline almost every group clears the target with rounds to spare, so
    "accumulating evidence of not reaching the target" barely exists. The composition
    study is where groups genuinely fail. We take the games that are behind pace at the
    start of round 8 and ask two things: do they push harder in the last two rounds,
    and does the size of that push grow with the catastrophe risk?
    """
    if t is None:
        try:
            t = all_turns(experiment)
        except FileNotFoundError:
            return {"note": f"no turns for {experiment}"}
        t = t[~t["parse_failed"].fillna(False).astype(bool)]
        t = with_pace(t)

    behind = t[(t["round"] == 8) & (t["need"] > 2.0)][["model", "game_id"]].drop_duplicates()
    sub = t.merge(behind, on=["model", "game_id"])
    if sub.empty:
        return {"note": "no game behind pace at round 8"}

    keys = ["model", "game_id", "risk_probability"]
    early = sub[sub["round"].between(5, 7)].groupby(keys)["contribution"].mean()
    late = sub[sub["round"].between(9, 10)].groupby(keys)["contribution"].mean()
    j = pd.concat([early.rename("early"), late.rename("late")], axis=1).dropna().reset_index()
    j["push"] = j["late"] - j["early"]

    by_risk = j.groupby("risk_probability")["push"].agg(["mean", "std", "count"])
    fit = {}
    if j["risk_probability"].nunique() > 1:
        fit = ols(np.column_stack([np.ones(len(j)), j["risk_probability"].to_numpy(float)]),
                  j["push"].to_numpy(float), ["intercept", "risk"])
    per_model = {}
    for model, ms in j.groupby("model"):
        if ms["risk_probability"].nunique() < 2 or len(ms) < 10:
            continue
        f = ols(np.column_stack([np.ones(len(ms)), ms["risk_probability"].to_numpy(float)]),
                ms["push"].to_numpy(float), ["intercept", "risk"])
        per_model[label(model)] = {"n": int(len(ms)),
                                   "push_mean": round(float(ms["push"].mean()), 3),
                                   "risk_slope": f["risk"]}
    return {
        "experiment": experiment,
        "n_games_behind_at_round8": int(len(j)),
        "overall_push_mean": round(float(j["push"].mean()), 3),
        "push_by_risk": {str(k): {"mean": round(float(v["mean"]), 3),
                                  "sd": round(float(v["std"]), 3) if pd.notna(v["std"]) else None,
                                  "n": int(v["count"])}
                         for k, v in by_risk.iterrows()},
        "push_on_risk": fit,
        "per_model": per_model,
    }


def trajectories(t: pd.DataFrame) -> dict:
    g = (t.groupby(["model", "risk_probability", "round"])["contribution"]
         .mean().reset_index())
    out = {}
    for model, sub in g.groupby("model"):
        out[label(model)] = {
            str(r): sub[sub.risk_probability == r].sort_values("round")["contribution"]
                       .round(3).tolist()
            for r in sorted(sub.risk_probability.unique())
        }
    return out


def make_figure(t: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 7.6, "axes.labelsize": 7.6,
                         "xtick.labelsize": 7, "ytick.labelsize": 7,
                         "axes.spines.top": False, "axes.spines.right": False})
    colours = {0.1: "#4477AA", 0.5: "#CCBB44", 0.9: "#CC3311"}

    present = [(m, lab) for m, lab in FIG_MODELS if (t["model"] == m).any()]
    ncol = 4
    nrow = int(np.ceil(len(present) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(7.1, 1.85 * nrow),
                             sharex=True, sharey=True)
    axes = np.atleast_1d(axes).ravel()

    for ax, (model, lab) in zip(axes, present):
        sub = t[(t["model"] == model) & (t["language"] == "en")]
        for r in (0.1, 0.5, 0.9):
            s = sub[sub["risk_probability"] == r]
            if s.empty:
                continue
            m = s.groupby("round")["contribution"].mean()
            ax.plot(m.index, m.values, marker="o", ms=2.4, lw=1.15,
                    color=colours[r], label=f"$p={r}$")
        ax.axhline(2.0, color="0.55", lw=0.7, ls=":", zorder=0)
        ax.set_title(lab, fontsize=7.4, loc="left")
        ax.set_xticks([1, 4, 7, 10])
        ax.set_ylim(-0.2, 4.2)
    for ax in axes[len(present):]:
        ax.set_visible(False)
    for ax in axes[:len(present)]:
        if ax.get_subplotspec().is_last_row() or len(present) - ncol < 0:
            ax.set_xlabel("round")
    axes[0].set_ylabel("mean contribution")
    if nrow > 1:
        axes[ncol].set_ylabel("mean contribution")
    axes[0].legend(frameon=False, fontsize=6.4, handlelength=1.2, loc="lower left")

    fig.suptitle("Contribution trajectories are flat in $p$ for every model except the two "
                 "that solve the game", fontsize=8, y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    FIGDIR.mkdir(exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(FIGDIR / f"fig11_trajectories.{ext}", dpi=300)
    plt.close(fig)
    print(f"wrote {FIGDIR / 'fig11_trajectories.pdf'}")


def main() -> None:
    t = all_turns("exp_baseline")
    t = t[~t["parse_failed"].fillna(False).astype(bool)]
    t = add_own_style(with_pace(t))

    # the composition study is where `need` actually varies: in the baseline nearly
    # every group is on pace at every round, so the pace coefficient there is estimated
    # off almost no signal and is not interpretable. We report both and lead with the
    # composition one.
    tp = all_turns("exp_persona")
    tp = tp[~tp["parse_failed"].fillna(False).astype(bool)]
    tp = add_own_style(with_pace(tp))

    report = {
        "n_turns_baseline": int(len(t)),
        "n_turns_persona": int(len(tp)),
        "need_spread": {
            "baseline_sd": round(float(t.loc[t["round"] >= 2, "need"].std()), 3),
            "persona_sd": round(float(tp.loc[tp["round"] >= 2, "need"].std()), 3),
        },
        "trajectories_en": trajectories(t[t.language == "en"]),
        "pace_tracking_persona": pace_models(tp),
        "pace_tracking_baseline": pace_models(t),
        "endgame_push_baseline": near_threshold("exp_baseline", t),
        "endgame_push_persona": near_threshold("exp_persona", tp),
    }
    (OUT / "r3_round_trajectories.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")

    print(f"turns: baseline {report['n_turns_baseline']}, "
          f"persona {report['n_turns_persona']}")
    print(f"SD of `need` (rounds 2-10): baseline "
          f"{report['need_spread']['baseline_sd']}, "
          f"persona {report['need_spread']['persona_sd']}\n")
    for tag in ("pace_tracking_persona", "pace_tracking_baseline"):
        print(f"== pace tracking [{tag.split('_')[-1]}]: "
              f"contribution ~ need(r) + own style + round FE ==")
        print(f"  {'model':26s} {'need':>8s} {'P':>9s}   {'need x risk':>12s} {'P':>9s}")
        for m, d in report[tag].items():
            if "pace_only" not in d:
                print(f"  {m:26s} {d.get('note')}")
                continue
            a, b = d["pace_only"]["need"], d["with_risk"]["need_x_risk"]
            print(f"  {m:26s} {a['coef']:>8.3f} {a['p']:>9.3g}   "
                  f"{b['coef']:>12.3f} {b['p']:>9.3g}")
        print()
    for tag in ("endgame_push_baseline", "endgame_push_persona"):
        eg = report[tag]
        print(f"\n== endgame push, groups behind pace at round 8 [{tag}] ==")
        if eg.get("note"):
            print(f"  {eg['note']}")
            continue
        print(f"  games behind pace: {eg.get('n_games_behind_at_round8')}, "
              f"mean push {eg.get('overall_push_mean'):+.3f}")
        for r, v in eg.get("push_by_risk", {}).items():
            print(f"    p={r}: push {v['mean']:+.3f} (sd {v['sd']}, n={v['n']})")
        if eg.get("push_on_risk"):
            pr = eg["push_on_risk"]["risk"]
            print(f"  push ~ risk: {pr['coef']:+.3f} (SE {pr['se']:.3f}, P={pr['p']:.3g})")
        for m, d in eg.get("per_model", {}).items():
            s = d["risk_slope"]
            print(f"    {m:22s} n={d['n']:<4d} push {d['push_mean']:+.3f}  "
                  f"risk slope {s['coef']:+.3f} (P={s['p']:.3g})")

    make_figure(t)


if __name__ == "__main__":
    main()
