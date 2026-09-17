"""R1/Q7 — the shared lottery schedule cannot induce learning, and does not.

Reviewer Q7: "Could you include an alternative lottery implementation (per-game
independent draws) in a small follow-up to confirm that realized-catastrophe feedback
does not, in fact, induce learning-like adjustments over repetitions?"

A follow-up run is not the right instrument here, because the concern it would test is
excluded by construction, and we can show that on the data already collected. Three
pieces of evidence, from strongest to weakest:

(a) STRUCTURAL. The catastrophe is drawn once, after round 10, in
    crsd/engine/scoring.py::compute_outcome. No agent ever observes the draw: it
    happens strictly after the last decision of the game, and agents carry no state
    between games. There is therefore no channel along which a realised catastrophe in
    repetition k could reach a decision in repetition k+1.

(b) EMPIRICAL DRIFT TEST. If any such channel existed despite (a), contributions would
    drift with repetition index. We regress group contribution on rep within each
    (model, risk, language) cell and test the pooled slope.

(c) FEEDBACK TEST. We regress contribution in repetition k on whether repetition k-1
    of the same cell ended in a catastrophe. Under (a) the coefficient must be zero.

(d) RESAMPLED LOTTERY. The alternative implementation the reviewer asks for is a
    post-hoc recomputation, because the lottery never touches behaviour: we redraw an
    independent uniform per game, 10,000 times, over the OBSERVED contribution vectors,
    and report the resulting distribution of realised payoff. This gives the payoff
    figures the paper quotes a schedule-free interval.

Output: paper/revision/out/r2_lottery_no_learning.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paper.Interface_Focus.revision._data import OUT, baseline_all, label            # noqa: E402

ENDOWMENT = 40.0
N_PLAYERS = 6


def load() -> pd.DataFrame:
    return baseline_all()


def ols(x: np.ndarray, y: np.ndarray) -> dict:
    """Slope, SE and two-sided t-test p-value for y ~ a + b x."""
    n = len(x)
    if n < 3 or np.ptp(x) == 0:
        return {"n": int(n), "slope": None, "p": None}
    X = np.column_stack([np.ones(n), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = n - 2
    s2 = float(resid @ resid) / dof if dof > 0 else np.nan
    xtx_inv = np.linalg.inv(X.T @ X)
    se = float(np.sqrt(s2 * xtx_inv[1, 1])) if dof > 0 else np.nan
    if not np.isfinite(se) or se == 0:
        return {"n": int(n), "slope": float(beta[1]), "se": se, "p": 1.0}
    t = float(beta[1]) / se
    # two-sided p from the t distribution, via the normal approximation refined by
    # an exact incomplete-beta call when scipy is available
    try:
        from scipy import stats
        p = float(2 * stats.t.sf(abs(t), dof))
    except Exception:
        from math import erfc, sqrt
        p = float(erfc(abs(t) / sqrt(2)))
    return {"n": int(n), "slope": float(beta[1]), "se": se, "t": t, "p": p}


def drift_test(df: pd.DataFrame) -> dict:
    """(b) Does contribution drift with repetition index?"""
    out = {}
    for arm, sub in df.groupby("arm"):
        # within-cell centred, so a pooled slope is not contaminated by cell means
        parts = []
        for _, cell in sub.groupby(["model", "language", "risk_probability"]):
            if len(cell) < 3:
                continue
            parts.append(pd.DataFrame({
                "rep": cell["rep"] - cell["rep"].mean(),
                "y": cell["group_total"] - cell["group_total"].mean(),
            }))
        pooled = pd.concat(parts, ignore_index=True)
        res = ols(pooled["rep"].to_numpy(float), pooled["y"].to_numpy(float))
        per_model = {}
        for model, ms in sub.groupby("model"):
            mp = []
            for _, cell in ms.groupby(["language", "risk_probability"]):
                if len(cell) < 3:
                    continue
                mp.append(pd.DataFrame({
                    "rep": cell["rep"] - cell["rep"].mean(),
                    "y": cell["group_total"] - cell["group_total"].mean()}))
            if mp:
                q = pd.concat(mp, ignore_index=True)
                per_model[model] = ols(q["rep"].to_numpy(float), q["y"].to_numpy(float))
        out[arm] = {"pooled": res, "per_model": per_model}
    return out


def feedback_test(df: pd.DataFrame) -> dict:
    """(c) Does a catastrophe in repetition k-1 change contribution in repetition k?"""
    rows = []
    for _, cell in df.groupby(["arm", "model", "language", "risk_probability"]):
        cell = cell.sort_values("rep")
        prev = cell["catastrophe"].shift(1)
        y = cell["group_total"]
        ok = prev.notna()
        if ok.sum() < 3:
            continue
        rows.append(pd.DataFrame({
            "arm": cell["arm"][ok],
            "prev_cat": prev[ok].astype(float),
            # centre within cell so the coefficient is a pure within-cell contrast
            "y": (y[ok] - y[ok].mean()),
        }))
    if not rows:
        return {}
    allrows = pd.concat(rows, ignore_index=True)
    out = {}
    for arm, sub in allrows.groupby("arm"):
        if sub["prev_cat"].nunique() < 2:
            out[arm] = {"n": int(len(sub)), "note": "no variation in prev_cat"}
            continue
        out[arm] = ols(sub["prev_cat"].to_numpy(float), sub["y"].to_numpy(float))
        out[arm]["n_prev_catastrophe"] = int(sub["prev_cat"].sum())
    return out


def resample_lottery(df: pd.DataFrame, n_boot: int = 10_000, seed: int = 20260813) -> dict:
    """(d) Redraw an independent lottery per game over the observed contributions.

    Realised per-agent payoff = (endowment - own contribution) unless the target was
    missed AND the lottery fired, in which case it is 0. We only have the group total,
    so we use the group mean kept = (6*40 - group_total)/6, which is exactly what
    mean_payoff records when no catastrophe occurs.
    """
    rng = np.random.default_rng(seed)
    res = {}
    for (arm, model), sub in df.groupby(["arm", "model"]):
        kept = (N_PLAYERS * ENDOWMENT - sub["group_total"].to_numpy(float)) / N_PLAYERS
        missed = (sub["target_reached"].to_numpy(float) < 1)
        p = sub["risk_probability"].to_numpy(float)
        draws = rng.random((n_boot, len(sub)))
        hit = missed[None, :] & (draws < p[None, :])
        payoff = np.where(hit, 0.0, kept[None, :])
        means = payoff.mean(axis=1)
        res[f"{arm}::{model}"] = {
            "n_games": int(len(sub)),
            "observed_mean_payoff": round(float(sub["mean_payoff"].mean()), 3),
            "resampled_mean": round(float(means.mean()), 3),
            "resampled_ci95": [round(float(np.percentile(means, 2.5)), 3),
                               round(float(np.percentile(means, 97.5)), 3)],
            "expected_no_catastrophe": round(float(kept.mean()), 3),
        }
    # the headline p=0.1 English comparison the paper makes
    sub = df[(df.risk_probability == 0.1) & (df.language == "en")]
    head = {}
    for model, ms in sub.groupby("model"):
        kept = (N_PLAYERS * ENDOWMENT - ms["group_total"].to_numpy(float)) / N_PLAYERS
        missed = (ms["target_reached"].to_numpy(float) < 1)
        draws = rng.random((n_boot, len(ms)))
        hit = missed[None, :] & (draws < 0.1)
        means = np.where(hit, 0.0, kept[None, :]).mean(axis=1)
        head[model] = {
            "observed_mean_payoff": round(float(ms["mean_payoff"].mean()), 3),
            "resampled_mean": round(float(means.mean()), 3),
            "resampled_ci95": [round(float(np.percentile(means, 2.5)), 3),
                               round(float(np.percentile(means, 97.5)), 3)],
        }
    res["__headline_p0.1_en__"] = head
    return res


def main() -> None:
    df = load()
    report = {
        "n_baseline_games": int(len(df)),
        "drift_by_rep": drift_test(df),
        "prev_catastrophe_feedback": feedback_test(df),
        "resampled_lottery": resample_lottery(df),
    }
    (OUT / "r2_lottery_no_learning.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")

    print(f"baseline games: {report['n_baseline_games']}\n")
    print("== (b) drift of group contribution with repetition index ==")
    for arm, d in report["drift_by_rep"].items():
        p = d["pooled"]
        print(f"  {arm:12s} pooled slope = {p['slope']:+.4f} pts/rep "
              f"(SE {p['se']:.4f}, n={p['n']}, P={p['p']:.3f})")
    print("\n== (c) contribution in rep k vs catastrophe in rep k-1 ==")
    for arm, d in report["prev_catastrophe_feedback"].items():
        if "slope" in d and d["slope"] is not None:
            print(f"  {arm:12s} beta = {d['slope']:+.3f} pts (SE {d['se']:.3f}, "
                  f"n={d['n']}, P={d['p']:.3f}, {d['n_prev_catastrophe']} prior catastrophes)")
        else:
            print(f"  {arm:12s} {d}")
    print("\n== (d) independent per-game lottery, 10k redraws, p=0.1 English ==")
    for model, d in report["resampled_lottery"]["__headline_p0.1_en__"].items():
        print(f"  {model:38s} observed {d['observed_mean_payoff']:>6.2f}  "
              f"resampled {d['resampled_mean']:>6.2f} "
              f"CI[{d['resampled_ci95'][0]:.2f}, {d['resampled_ci95'][1]:.2f}]")


if __name__ == "__main__":
    main()
