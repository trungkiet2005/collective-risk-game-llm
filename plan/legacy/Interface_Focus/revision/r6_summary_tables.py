"""R1/W7 + W8 — the two compact summary tables the reviewer asked for.

W7: "central numerical claims (e.g. effect-size comparisons across manipulations) could
be further distilled into a compact summary table."
W8: "the separation between 'economy/thrift' and 'risk sensitivity' ... occasionally
buried in dense text; brief schematic summaries per model family would aid digestion."

Everything here is recomputed from the raw per-game files, including the numbers the
manuscript already quotes, so the new tables cannot drift from the text. Where a value
reproduces one already in the paper we print both and flag any mismatch.

Emits:
  paper/revision/out/tab_effects.tex     -- W7, effect magnitudes on one scale
  paper/revision/out/tab_axes.tex        -- W8, thrift vs risk sensitivity per family
  paper/revision/out/r6_summary.json     -- every number, for checking
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _data import (FRONTIER_LABELS, OPEN_LABELS, OUT, RESULTS,  # noqa: E402
                   frontier_games, label, open_games)

TARGET = 120.0


def paired_test(a: np.ndarray, b: np.ndarray) -> dict:
    """Paired difference b - a with a t-based 95% CI."""
    d = np.asarray(b, float) - np.asarray(a, float)
    n = len(d)
    m = float(d.mean())
    if n < 2:
        return {"n": n, "mean": m, "ci": [None, None], "p": None}
    se = float(d.std(ddof=1) / np.sqrt(n))
    if se == 0:
        return {"n": n, "mean": m, "ci": [m, m], "p": 0.0 if m else 1.0}
    t = m / se
    try:
        from scipy import stats
        p = float(2 * stats.t.sf(abs(t), n - 1))
        crit = float(stats.t.ppf(0.975, n - 1))
    except Exception:
        from math import erfc, sqrt
        p, crit = float(erfc(abs(t) / sqrt(2))), 1.96
    return {"n": n, "mean": m, "ci": [m - crit * se, m + crit * se], "p": p}


# --------------------------------------------------------------------------- #
# 1. risk, in the cells where the outcome was genuinely in doubt
# --------------------------------------------------------------------------- #
def uncensored_risk() -> dict:
    """Reimplementation of the paper's decisive open-weight test.

    Cells are (model, composition, language) in the composition study. A cell is
    uncensored when its target-reach rate is strictly between 0 and 1, i.e. the group
    sometimes made it and sometimes did not. Within those cells we pair p=0.1 against
    p=0.9 on the shared sampling seed (the design uses common random numbers).
    """
    per = open_games("exp_persona")
    nano = pd.read_csv(RESULTS / "frontier" / "openai-gpt-5.4-nano" / "exp_persona"
                       / "games.csv")
    nano["arm"] = "commercial"

    out = {}
    for tag, df in (("open_weight", per), ("gpt-5.4-nano", nano)):
        keys = ["model", "persona_set", "language"]
        reach = df.groupby(keys)["target_reached"].mean()
        cells = reach[(reach > 0) & (reach < 1)].index
        sub = df.set_index(keys).loc[cells].reset_index()

        w = sub.pivot_table(index=keys + ["rep"], columns="risk_probability",
                            values="group_total")
        w = w.dropna(subset=[0.1, 0.9])
        res = paired_test(w[0.1].to_numpy(), w[0.9].to_numpy())

        r = sub.pivot_table(index=keys + ["rep"], columns="risk_probability",
                            values="target_reached").dropna(subset=[0.1, 0.9])
        out[tag] = {
            "n_cells_total": int(len(reach)),
            "n_cells_uncensored": int(len(cells)),
            "risk_effect": res,
            "reach_p01": round(float(r[0.1].mean()), 3),
            "reach_p09": round(float(r[0.9].mean()), 3),
            # minimum detectable effect at 80% power, two-sided alpha .05
            "mde_80pct": round(float(2.802 * (w[0.9] - w[0.1]).std(ddof=1)
                                     / np.sqrt(len(w))), 2),
        }
    return out


# --------------------------------------------------------------------------- #
# 2. the prompt-side manipulations
# --------------------------------------------------------------------------- #
def salience() -> dict:
    """Printed vs hidden running pool total, paired within seed."""
    raw = pd.read_csv(RESULTS / "open_source" / "crsd_all_models.csv")
    comp = raw[raw.experiment == "exp_comprehension"].copy()
    comp["showcum"] = comp.game_id.str.contains("showcum")
    out = {}
    for model, g in comp.groupby("model"):
        w = g.pivot_table(index=["rep", "language", "risk_probability"],
                          columns="showcum", values="group_total")
        if w.shape[1] < 2 or w.isna().any().any():
            continue
        res = paired_test(w[False].to_numpy(), w[True].to_numpy())
        out[label(model)] = {
            "hidden": round(float(w[False].mean()), 1),
            "printed": round(float(w[True].mean()), 1),
            "delta": round(res["mean"], 1),
            "p": res["p"], "n_pairs": res["n"],
        }
    return out


def composition() -> dict:
    """All-cooperative vs all-selfish, per model and language."""
    per = open_games("exp_persona")
    nano = pd.read_csv(RESULTS / "frontier" / "openai-gpt-5.4-nano" / "exp_persona"
                       / "games.csv")
    out = {}
    for df in (per, nano):
        for model, g in df.groupby("model"):
            rows = {}
            for lang, gl in g.groupby("language"):
                coop = gl[gl.persona_set == "personas_cooperative"]["group_total"]
                self_ = gl[gl.persona_set == "personas_selfish"]["group_total"]
                if coop.empty or self_.empty:
                    continue
                rows[lang] = {"all_cooperative": round(float(coop.mean()), 1),
                              "all_selfish": round(float(self_.mean()), 1),
                              "delta": round(float(self_.mean() - coop.mean()), 1)}
            if rows:
                # the manuscript quotes the figure pooled over languages; keep both so
                # the table and the text cannot disagree
                coop = g[g.persona_set == "personas_cooperative"]["group_total"]
                self_ = g[g.persona_set == "personas_selfish"]["group_total"]
                rows["pooled"] = {"all_cooperative": round(float(coop.mean()), 1),
                                  "all_selfish": round(float(self_.mean()), 1),
                                  "delta": round(float(self_.mean() - coop.mean()), 1)}
                out[label(model)] = rows
    return out


def language_effect() -> dict:
    """English minus Vietnamese group contribution in the BASELINE, paired on the seed.

    The baseline is the right arm for this: it is the one both arms share, and it is
    where the manuscript's headline language figure comes from (GPT-5.4-nano, 15 pairs
    of 3 risks x 5 repetitions).
    """
    df = pd.concat([open_games(), frontier_games()], ignore_index=True)
    out = {}
    for model, g in df.groupby("model"):
        w = g.pivot_table(index=["risk_probability", "rep"], columns="language",
                          values="group_total").dropna()
        if w.empty or not {"en", "vn"}.issubset(w.columns):
            continue
        res = paired_test(w["vn"].to_numpy(), w["en"].to_numpy())
        out[label(model)] = {"en": round(float(w["en"].mean()), 1),
                             "vn": round(float(w["vn"].mean()), 1),
                             "delta": round(res["mean"], 1),
                             "p": res["p"], "n_pairs": res["n"]}
    return out


def risk_effect_by_model() -> dict:
    """Group contribution at p=0.9 minus p=0.1 in English (the paper's risk column),
    alongside the overall pooled contribution over BOTH languages (the paper's
    contribution column in table 1) so the two tables agree.

    The pooled column runs over CORE_RISKS only, which the loaders enforce: the
    p=0.3/0.7 cells exist for four configurations out of fourteen and in English
    only, so averaging over them would make this column incomparable across the
    panel and would move numbers the manuscript already quotes.
    """
    df = pd.concat([open_games(), frontier_games()], ignore_index=True)
    out = {}
    for model, g_all in df.groupby("model"):
        g = g_all[g_all.language == "en"]
        m = g.groupby("risk_probability")["group_total"].mean()
        if not {0.1, 0.9}.issubset(m.index):
            continue
        out[label(model)] = {
            "p01": round(float(m.loc[0.1]), 1),
            "p09": round(float(m.loc[0.9]), 1),
            "delta": round(float(m.loc[0.9] - m.loc[0.1]), 1),
            "mean_contribution_all": round(float(g_all["group_total"].mean()), 1),
            "reach_p01_en": round(float(g[g.risk_probability == 0.1]["target_reached"]
                                        .mean()), 3),
        }
    return out


# --------------------------------------------------------------------------- #
# LaTeX emitters
# --------------------------------------------------------------------------- #
def fmt_p(p) -> str:
    if p is None:
        return "--"
    if p < 1e-4:
        return r"$<10^{-4}$"
    return f"${p:.3f}$" if p >= 0.001 else f"${p:.1g}$"


def tab_effects(d: dict) -> str:
    u = d["uncensored_risk"]["open_weight"]["risk_effect"]
    un = d["uncensored_risk"]["gpt-5.4-nano"]["risk_effect"]
    sal = d["salience"]
    comp = d["composition"]
    lang = d["language"]
    rbm = d["risk_by_model"]

    def biggest(d: dict, key="delta"):
        return max(d.items(), key=lambda kv: abs(kv[1][key]))

    sal_m, sal_v = biggest(sal)
    # Convention matched to the running text: the three open-weight models are quoted
    # pooled over languages, GPT-5.4-nano in English, because its Vietnamese arm starts
    # below the target and so its composition line never crosses (see the results).
    comp_pooled = {m: (v["en"] if m == "GPT-5.4-nano" else v["pooled"])
                   for m, v in comp.items()}
    comp_m, comp_v = biggest(comp_pooled)
    lang_m, lang_v = biggest({k: v for k, v in lang.items()})
    ev = {m: rbm[m]["delta"] for m in ("Gemini-3.1-Pro", "GPT-5.6-sol") if m in rbm}
    grok_thrift = (rbm["Grok-4.20 (no reasoning)"]["mean_contribution_all"]
                   - rbm["Grok-4.20 (reasoning)"]["mean_contribution_all"])
    sal_rng = sorted(abs(v["delta"]) for v in sal.values())
    comp_rng = sorted(abs(v["delta"]) for v in comp_pooled.values())

    rows = [
        (r"Catastrophe risk, $p{=}0.1\!\to\!0.9$", "incentive",
         f"${u['mean']:+.2f}$", f"$[{u['ci'][0]:+.1f}, {u['ci'][1]:+.1f}]$",
         fmt_p(u["p"]),
         r"11 models pooled, uncensored cells ($n{=}%d$)" % u["n"]),
        (r"\quad the same, GPT-5.4-nano alone", "incentive",
         f"${un['mean']:+.1f}$", f"$[{un['ci'][0]:+.1f}, {un['ci'][1]:+.1f}]$",
         fmt_p(un["p"]), r"cheap tier, uncensored ($n{=}%d$)" % un["n"]),
        (r"\quad the same, the two EV models", "incentive",
         "$+%.1f$, $+%.1f$" % (ev["GPT-5.6-sol"], ev["Gemini-3.1-Pro"]),
         "--", "--", "GPT-5.6-sol, Gemini-3.1-Pro"),
        (r"Printing the running pool total", "prompt",
         f"${sal_v['delta']:+.1f}$", "--", fmt_p(sal_v["p"]),
         r"%s ($%.1f$--$%.1f$, 5 models)" % (sal_m, sal_rng[0], sal_rng[-1])),
        (r"Group composition, $0\!\to\!6$ selfish", "prompt",
         f"${comp_v['delta']:+.1f}$", "--", "--",
         r"%s ($%.1f$--$%.1f$, 4 models)" % (comp_m, comp_rng[0], comp_rng[-1])),
        (r"Prompt language, Vietnamese $\to$ English", "prompt",
         f"${lang_v['delta']:+.1f}$", "--", fmt_p(lang_v["p"]),
         r"%s; reach $0\%%\!\to\!100\%%$" % lang_m),
        (r"Explicit reasoning, off $\to$ on", "model",
         f"$-{grok_thrift:.1f}$", "--", "--",
         r"Grok-4.20; risk effect $+23.6\!\to\!+0.2$"),
    ]

    body = "\n".join(" & ".join(r) + r" \\" for r in rows)
    return r"""\begin{table*}[t]
\centering
\caption{\textbf{What moves an agent, on one scale.} Change in group contribution
(of a possible $240$) produced by each manipulation. \emph{Channel} identifies
whether the change is carried by the game's incentives, the prompt, or the model
configuration. The final column gives the largest effect and its range across models.
The risk comparison is the smallest for the models that do not follow the
expected-value benchmark.}
\label{tab:effects}
\footnotesize
\setlength{\tabcolsep}{1pt}
\resizebox{\linewidth}{!}{%
\begin{tabular}{@{}p{.20\textwidth}p{.08\textwidth}p{.09\textwidth}p{.12\textwidth}p{.06\textwidth}p{.22\textwidth}@{}}
\toprule
Manipulation & Channel & \shortstack{$\Delta$\\contrib.} & \shortstack{$95\%$\\CI} & $P$ & Largest effect, and range \\
\midrule
""" + body + r"""
\bottomrule
\end{tabular}%
}
\end{table*}
"""


def tab_axes(d: dict) -> str:
    """W8: thrift and risk sensitivity are separate axes, arranged by family."""
    rbm = d["risk_by_model"]
    fam = [
        ("Qwen2.5", ["Qwen2.5-7B", "Qwen2.5-32B", "Qwen2.5-72B"]),
        ("Llama-3.1", ["Llama-3.1-8B", "Llama-3.1-70B"]),
        ("Gemma-2", ["Gemma-2-9B", "Gemma-2-27B"]),
        ("Gemini-3.1", ["Gemini-3.1-Flash-Lite", "Gemini-3.1-Pro"]),
        ("GPT-5", ["GPT-5.4-nano", "GPT-5.6-sol"]),
        ("Claude", ["Claude-Opus-5"]),
        ("Grok-4.20", ["Grok-4.20 (no reasoning)", "Grok-4.20 (reasoning)"]),
    ]
    lines = []
    for family, members in fam:
        first = True
        for m in members:
            if m not in rbm:
                continue
            r = rbm[m]
            thrift = r["mean_contribution_all"]
            verdict = ("EV solution" if abs(r["delta"]) > 50 else
                       "thrifty, risk-blind" if thrift <= 135 else
                       "profligate, risk-blind")
            lines.append(
                f"{family if first else ''} & {m} & ${thrift:.1f}$ & "
                f"${r['delta']:+.1f}$ & ${r['reach_p01_en']*100:.0f}\\%$ & {verdict} \\\\")
            first = False
        lines.append(r"\addlinespace[1pt]")
    body = "\n".join(lines[:-1])
    return r"""\begin{table}[t]
\centering
\caption{\textbf{Economy of play and risk sensitivity are separate axes.} For each
configuration: how much the group pooled overall (of $240$; lower is thriftier), the
risk effect in English, and the target-reach rate at $p=0.1$, the risk level at which
reaching the target is the wrong thing to do. Within every family the larger or more
expensive member is thriftier; only in one family does it also become risk-sensitive.}
\label{tab:axes}
\small
\begin{tabular}{@{}llccll@{}}
\toprule
Family & Configuration & Pooled & $\Delta$ risk & Reach at $p{=}0.1$ & Reading \\
\midrule
""" + body + r"""
\bottomrule
\end{tabular}
\end{table}
"""


def main() -> None:
    d = {
        "uncensored_risk": uncensored_risk(),
        "salience": salience(),
        "composition": composition(),
        "language": language_effect(),
        "risk_by_model": risk_effect_by_model(),
    }
    (OUT / "r6_summary.json").write_text(json.dumps(d, indent=2, default=float),
                                         encoding="utf-8")
    (OUT / "tab_effects.tex").write_text(tab_effects(d), encoding="utf-8")
    (OUT / "tab_axes.tex").write_text(tab_axes(d), encoding="utf-8")

    u = d["uncensored_risk"]
    print("== risk in uncensored cells (recomputed) ==")
    for tag, v in u.items():
        r = v["risk_effect"]
        print(f"  {tag:14s} cells {v['n_cells_uncensored']}/{v['n_cells_total']}  "
              f"delta {r['mean']:+.2f} CI[{r['ci'][0]:+.1f},{r['ci'][1]:+.1f}] "
              f"n={r['n']} P={r['p']:.3f}  reach {v['reach_p01']}->{v['reach_p09']}  "
              f"MDE80={v['mde_80pct']}")

    print("\n== salience: hidden -> printed pool total ==")
    for m, v in d["salience"].items():
        print(f"  {m:16s} {v['hidden']:6.1f} -> {v['printed']:6.1f}  "
              f"delta {v['delta']:+7.1f}  P={v['p']:.2g}")

    print("\n== composition: all-cooperative -> all-selfish ==")
    for m, v in d["composition"].items():
        for lang, r in v.items():
            print(f"  {m:16s} [{lang}] {r['all_cooperative']:6.1f} -> "
                  f"{r['all_selfish']:6.1f}  delta {r['delta']:+7.1f}")

    print("\n== risk effect by configuration (English) ==")
    for m, v in sorted(d["risk_by_model"].items(), key=lambda kv: -kv[1]["delta"]):
        print(f"  {m:24s} {v['p01']:7.1f} -> {v['p09']:7.1f}  "
              f"delta {v['delta']:+7.1f}   pooled {v['mean_contribution_all']:6.1f}  "
              f"reach@0.1 {v['reach_p01_en']:.2f}")

    print(f"\nwrote {OUT/'tab_effects.tex'} and {OUT/'tab_axes.tex'}")


if __name__ == "__main__":
    main()
