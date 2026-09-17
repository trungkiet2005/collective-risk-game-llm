"""E3a: one LLM (agent1) against five scripted partners.

Run from the repository root:
    python paper/AAMAS/analysis/scripted.py

Data: results/exp_bestresponse_{defect,coop,carry,cond}: five always-0, always-2,
always-4 or conditional-cooperator seats; 4 profiles x 5 models x 5 risks
{.1,.3,.5,.7,.9} x 10 reps = 1,000 games.

Writes
    paper/AAMAS/figures/fig_scripted.pdf (+ .png)
    paper/AAMAS/tables/num_scripted.tex

Checks (raise on violation)
  * seats 2-6 carry the scripted policy of the folder; seat 1 is the folder's model;
  * an independent replay of the scripted seats reproduces every observed game;
  * brute force over all 3^10 LLM trajectories: the best-response total is 0 at every p
    against always-0 and always-4; against always-2 and the conditional cooperator it is
    0 for p < 0.5, 20 for p > 0.5, and both at p = 0.5; the conditional cooperator never
    moves off 2 whatever the LLM does.

SETTLED ROUND (per game): the first round t after which the history shown to the LLM
proves further payment useless. Against always-4: pot after round t >= 120. Against
always-0: pot after round t + 24 * (10 - t) < 120 (all six paying 4 in every remaining
round cannot reach the target). Waste = units the LLM pays in rounds t+1..10.

Payoffs are EXPECTED over the catastrophe lottery. Unit = game.
"""
from __future__ import annotations

import itertools
import sys
from collections import Counter

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

import crsd_data as cd
import crsd_style as cs

PROFILES = {"all0": "scripted:always_0", "all2": "scripted:always_2",
            "all4": "scripted:always_4", "cond": "scripted:conditional_cooperator"}
RISKS = (0.1, 0.3, 0.5, 0.7, 0.9)
OPTIONS = (0, 2, 4)
N, R, E, T = cd.N_PLAYERS, cd.N_ROUNDS, int(cd.ENDOWMENT), int(cd.TARGET)
MAX_STEP = N * max(OPTIONS)          # 24: all six pay 4


def thousands(n: int) -> str:
    return f"{int(n):,}".replace(",", "{,}")


def pct0(x: float) -> str:
    return str(int(np.floor(100.0 * x + 0.5 + 1e-9)))


# ------------------------------------------------------------------ scripted seats
def nearest(v: float) -> int:
    """Engine rule (_nearest_option): nearest legal option, ties keep the LOWER one."""
    best, best_d = OPTIONS[0], abs(v - OPTIONS[0])
    for o in OPTIONS[1:]:
        d = abs(v - o)
        if d < best_d:
            best, best_d = o, d
    return best


def replay(profile: str, llm_moves) -> np.ndarray:
    """(6, 10) contributions with seat 0 = LLM, scripted seats 1-5 per the engine."""
    hist = []
    for own in llm_moves:
        if profile == "cond":
            if not hist:
                others = [nearest(cd.FAIR_SHARE)] * 5
            else:
                last = hist[-1]
                others = [nearest(sum(last[j] for j in range(N) if j != s) / (N - 1))
                          for s in range(1, N)]
        else:
            others = [{"all0": 0, "all2": 2, "all4": 4}[profile]] * 5
        hist.append([int(own)] + others)
    return np.array(hist).T


def brute_force():
    """Enumerate all 3^10 LLM trajectories per profile; return reachable (own, group)."""
    reach = {}
    for prof in PROFILES:
        pairs = set()
        cond_moves = set()
        for seq in itertools.product(OPTIONS, repeat=R):
            h = replay(prof, seq)
            pairs.add((int(h[0].sum()), int(h.sum())))
            if prof == "cond":
                cond_moves.update(np.unique(h[1:]).tolist())
        if prof == "cond" and cond_moves != {2}:
            raise AssertionError(f"conditional cooperator moves to {sorted(cond_moves)}")
        reach[prof] = sorted(pairs)
    return reach


def best_totals(pairs, p):
    ev = {(own, G): (E - own) * (1.0 if G >= T else 1.0 - p) for own, G in pairs}
    top = max(ev.values())
    return sorted({own for (own, G), v in ev.items() if abs(v - top) < 1e-9}), top


def verify_best_response(reach):
    grid = sorted(set(RISKS) | set(np.round(np.arange(0.01, 1.0, 0.01), 2)))
    for prof, pairs in reach.items():
        for p in grid:
            opt, _ = best_totals(pairs, p)
            if prof in ("all0", "all4"):
                want = [0]
            elif p < 0.5:
                want = [0]
            elif p > 0.5:
                want = [20]
            else:
                want = [0, 20]
            if opt != want:
                raise AssertionError(f"{prof} p={p}: best-response totals {opt}, expected {want}")
    print("brute force over 3^10 LLM trajectories per profile: best response verified "
          "(all0/all4: 0 at every p; all2/cond: 0 below .5, 20 above, both at .5); "
          "conditional cooperator only ever plays 2")


# ------------------------------------------------------------------ data
def load(reach) -> pd.DataFrame:
    exps = [cd.SCRIPTED[k] for k in PROFILES]
    games, _, _ = cd.build(exps)
    rows = []
    for g in games.to_dict("records"):
        prof = g["ctx"]
        llm = g["llm"]
        if cd.SLUG.get(llm[0]) is None or llm[0] != g["folder_model"]:
            raise AssertionError(f"seat 1 is {llm[0]} in folder {g['folder_model']}")
        if any(s != PROFILES[prof] for s in llm[1:]):
            raise AssertionError(f"{g['gid']}: scripted seats {llm[1:]}")
        strat = g["strat"].astype(int)
        if not np.array_equal(replay(prof, strat[0]), strat):
            raise AssertionError(f"{g['gid']}: replay of scripted seats disagrees")
        if g["n_parse"] != 0:
            raise AssertionError(f"{g['gid']}: parse failures")
        x = strat[0]
        own, G, p = int(x.sum()), int(strat.sum()), g["p"]
        pot = np.cumsum(strat.sum(axis=0))
        if prof == "all4":
            settled = next(t + 1 for t in range(R) if pot[t] >= T)
        elif prof == "all0":
            settled = next(t + 1 for t in range(R) if pot[t] + MAX_STEP * (R - (t + 1)) < T)
        else:
            settled = None
        opt, top = best_totals(reach[prof], p)
        exp_pay = float(cd.expected_payoff(own, G >= T, p))
        free_rider = float(cd.expected_payoff(0, G >= T, p))   # an always-0 seat, same table
        rows.append(dict(gid=g["gid"], profile=prof, model=cd.SLUG[llm[0]], p=p, rep=g["rep"],
                         x=x, total=own, G=G, reached=int(G >= T), exp_pay=exp_pay,
                         br_pay=top, gap=top - exp_pay, settled=settled,
                         waste=None if settled is None else int(x[settled:].sum()),
                         free_rider_gap=free_rider - exp_pay))
    d = pd.DataFrame(rows)
    cells = d.groupby(["profile", "model", "p"]).size()
    if len(d) != 1000 or len(cells) != 100 or not (cells == 10).all():
        raise AssertionError(f"design not balanced: {len(d)} games, {len(cells)} cells")
    return d


def two_way_shares(df: pd.DataFrame, y: str = "total"):
    """Balanced two-way sums of squares: profile, risk, profile x risk, residual."""
    gm = df[y].mean()
    sst = ((df[y] - gm) ** 2).sum()
    ma = df.groupby("profile")[y].transform("mean")
    mb = df.groupby("p")[y].transform("mean")
    mab = df.groupby(["profile", "p"])[y].transform("mean")
    ss_a = ((ma - gm) ** 2).sum()
    ss_b = ((mb - gm) ** 2).sum()
    ss_ab = ((mab - ma - mb + gm) ** 2).sum()
    ss_r = ((df[y] - mab) ** 2).sum()
    if abs(ss_a + ss_b + ss_ab + ss_r - sst) > 1e-6 * max(sst, 1):
        raise AssertionError("sums of squares do not add up (design unbalanced?)")
    return dict(profile=ss_a / sst, risk=ss_b / sst, inter=ss_ab / sst, resid=ss_r / sst)


# ------------------------------------------------------------------ numbers
def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    reach = brute_force()
    verify_best_response(reach)
    d = load(reach)
    print(f"games {len(d)}; independent replay matched all; no parse failures")

    M = cd.Macros("scripted.py")
    M.add("ScrGames", thousands(len(d)))

    dom = d[d["profile"].isin(["all0", "all4"])]
    M.add("ScrDominatedGames", str(len(dom)))
    n_br_dom = int((dom["total"] == 0).sum())
    M.add("ScrBestResponseDominated", str(n_br_dom))
    M.add("ScrMinTotalDominated", str(int(dom["total"].min())))
    print(f"dominated games {len(dom)}; LLM total 0 in {n_br_dom}; min total {dom['total'].min()}"
          f" (all0 min {d[d.profile == 'all0'].total.min()}, all4 min {d[d.profile == 'all4'].total.min()})")

    optimal = d[d["gap"].abs() < 1e-9]
    M.add("ScrOptimalGames", str(len(optimal)))
    if not (optimal["total"] == 20).all():
        raise AssertionError(f"optimal games with totals {sorted(optimal['total'].unique())}")
    M.add("ScrOptimalAllTwenty", "every")
    print(f"zero expected-payoff gap: {len(optimal)} games; totals {sorted(optimal.total.unique())}; "
          f"profiles {optimal.profile.value_counts().to_dict()}; min p {optimal.p.min()}")
    print("  by model:", optimal.groupby("model").size().reindex(cd.MODELS).to_dict())

    # variance decomposition on the three constant profiles
    three = d[d["profile"].isin(["all0", "all2", "all4"])]
    shares = {m: two_way_shares(three[three["model"] == m]) for m in cd.MODELS}
    print("\nvariance of LLM total (3 profiles x 5 risks x 10 reps = 150 games per model):")
    for m, s in shares.items():
        print(f"  {m:10} profile {100 * s['profile']:5.1f}%  risk {100 * s['risk']:4.1f}%  "
              f"profile x risk {100 * s['inter']:4.1f}%  risk+interaction "
              f"{100 * (s['risk'] + s['inter']):4.1f}%  residual {100 * s['resid']:5.1f}%")
    four = ["Haiku", "Flash-Lite", "Luna", "Qwen"]
    M.add("ScrOpponentShareMin", pct0(min(shares[m]["profile"] for m in four)))
    M.add("ScrOpponentShareMax", pct0(max(shares[m]["profile"] for m in four)))
    M.add("ScrRiskShareMax", pct0(max(shares[m]["risk"] + shares[m]["inter"] for m in four)))
    M.add("ScrGrokOpponentShare", pct0(shares["Grok"]["profile"]))
    ref = three[three["model"] == "Luna"][["profile", "p"]].copy()
    ref["total"] = [20 if (pr == "all2" and p >= 0.5) else 0 for pr, p in zip(ref.profile, ref.p)]
    s_ref = two_way_shares(ref)
    M.add("ScrBestResponderRiskShare", pct0(s_ref["risk"] + s_ref["inter"]))
    print(f"  exact best responder (tie at .5 -> 20): profile {100 * s_ref['profile']:.1f}%  "
          f"risk {100 * s_ref['risk']:.1f}%  interaction {100 * s_ref['inter']:.1f}%")

    # settled round and waste
    sett = dom.groupby("profile")["settled"].agg(lambda s: dict(sorted(Counter(s).items())))
    print("\nsettled-round distribution:", sett.to_dict())
    modal = {prof: Counter(dom[dom.profile == prof]["settled"]).most_common(1)[0][0]
             for prof in ("all0", "all4")}
    if set(modal.values()) != {6}:
        raise AssertionError(f"modal settled round is {modal}, not 6")
    print("waste after the settled round (pooled all0 + all4, 100 games per model):")
    for m in cd.MODELS:
        w = dom[dom["model"] == m]
        lo, hi = cd.boot_ci(w["waste"], offset=300 + list(cd.MODELS).index(m))
        clean = (w["waste"] == 0).mean()
        by = w.groupby("profile")["waste"].mean().to_dict()
        print(f"  {m:10} waste/game {w['waste'].mean():6.2f} [{lo:.2f}, {hi:.2f}]  "
              f"clean {int((w['waste'] == 0).sum())}/{len(w)}  by profile {by}")
        M.add(f"ScrWaste{cd.MACRO[m]}", cd.fmt(w["waste"].mean()))
        if m in ("Luna", "Qwen", "Grok"):
            if len(w) != 100:
                raise AssertionError(f"{m}: {len(w)} dominated games")
            M.add(f"ScrClean{cd.MACRO[m]}", pct0(clean))

    M.add("ScrGrokRiskShare", pct0(shares["Grok"]["risk"] + shares["Grok"]["inter"]))
    M.add("ScrGrokResidShare", pct0(shares["Grok"]["resid"]))

    # Payments before and after the settled round, per model and profile (units per game).
    # This separates stopping once the outcome is settled from responding to partners earlier.
    tab = ["% Generated by paper/AAMAS/analysis/scripted.py. Do not edit by hand.",
           r"\begin{tabular}{@{}lrrrr@{}}",
           r"\toprule",
           r" & \multicolumn{2}{c}{Always 0} & \multicolumn{2}{c}{Always 4} \\",
           r"\cmidrule(lr){2-3}\cmidrule(l){4-5}",
           r"Model & Before & After & Before & After \\",
           r"\midrule"]
    print("\npayment before / after the settled round (units per game, 50 games per cell):")
    for m in cd.MODELS:
        cells = []
        for prof in ("all0", "all4"):
            w = dom[(dom["model"] == m) & (dom["profile"] == prof)]
            before = float(np.mean([int(x[: int(s)].sum()) for x, s in zip(w["x"], w["settled"])]))
            after = w["waste"].mean()
            cells += [cd.fmt(before), cd.fmt(after)]
            print(f"  {m:10} {prof}: before {before:5.2f}  after {after:5.2f}")
        tab.append(f"{cd.show(m)} & " + " & ".join(cells) + r" \\")
    tab += [r"\bottomrule", r"\end{tabular}"]
    (cd.TABLES / "tab_settled.tex").write_text("\n".join(tab) + "\n", encoding="utf-8")

    # fair-share partners
    q2 = d[(d["model"] == "Qwen") & (d["profile"] == "all2")]
    miss = q2[q2["reached"] == 0]
    short = Counter(T - miss["G"])
    M.add("ScrQwenFairMiss", str(len(miss)))
    M.add("ScrQwenFairShort", str(int(short.most_common(1)[0][0])))
    f2 = d[(d["model"] == "Flash-Lite") & (d["profile"] == "all2")]
    M.add("ScrFlashFairReach", str(int(f2["reached"].sum())))
    print(f"\nQwen vs always-2: missed {len(miss)}/{len(q2)}; shortfalls {dict(short)}; "
          f"trajectories {Counter(map(tuple, q2['x'])).most_common(3)}")
    print(f"Flash-Lite vs always-2: reached {int(f2['reached'].sum())}/{len(f2)}")
    print("target reached vs always-2 by model:",
          d[d.profile == "all2"].groupby("model")["reached"].sum().reindex(cd.MODELS).to_dict())

    q0 = d[(d["model"] == "Qwen") & (d["profile"] == "all0")]
    M.add("ScrQwenDefectPay", cd.fmt(q0["total"].mean()))
    M.add("ScrQwenFairPay", cd.fmt(q2["total"].mean()))
    print(f"Qwen mean total: vs always-0 {q0['total'].mean():.3f}; vs always-2 {q2['total'].mean():.3f}")

    a0 = d[d["profile"] == "all0"]
    if a0["reached"].any():
        raise AssertionError("a game against always-0 reached the target")
    fr = a0.groupby("model")["free_rider_gap"].mean().reindex(cd.MODELS)
    print("vs always-0: always-0 seat expected payoff minus LLM expected payoff:",
          fr.round(3).to_dict())
    M.add("ScrFreeRiderGapMin", cd.fmt(fr.min()))
    M.add("ScrFreeRiderGapMax", cd.fmt(fr.max()))

    # Grok: round 1 has no history, so every profile sees the same prompt. How much of
    # Grok's ten-round total does its own sampled round-1 move explain, compared with the
    # partner profile and the risk? One-way sums of squares over all 200 Grok games.
    gk = d[d["model"] == "Grok"].copy()
    gk["r1"] = [int(x[0]) for x in gk["x"]]
    gm = gk["total"].mean()
    sst = ((gk["total"] - gm) ** 2).sum()

    def share(col):
        return float(((gk.groupby(col)["total"].transform("mean") - gm) ** 2).sum() / sst)

    s_r1, s_prof, s_p = share("r1"), share("profile"), share("p")
    open4 = int((gk["r1"] == 4).sum())
    print(f"\nGrok (200 games): opens with 4 in {open4}; variance explained by round-1 move "
          f"{100 * s_r1:.1f}%, by profile {100 * s_prof:.1f}%, by risk {100 * s_p:.1f}%")
    if not s_r1 > max(s_prof, s_p):
        raise AssertionError("Grok's round-1 move no longer dominates profile and risk")
    M.add("ScrGrokOpenFour", str(open4))
    M.add("ScrGrokFirstMoveShare", pct0(s_r1))
    M.add("ScrGrokProfileShareFour", pct0(s_prof))

    path = M.write("num_scripted.tex")
    print(f"\nwrote {path}")
    for k, v in M.items.items():
        print(f"  \\{k} = {v}")
    figure(d, modal=6)


# ------------------------------------------------------------------ figure
def figure(d: pd.DataFrame, modal: int) -> None:
    """Mean units paid in each round, one row per model, beside always-0 and always-4
    partners. The top row is the best response (0 in every round). The dashed rule marks
    the end of the modal settled round."""
    rows = ["Best response", *cs.MODEL_ORDER]
    cs.use()
    fig = plt.figure(figsize=cs.figsize("col", height_pt=100))
    fig._crsd_width = "col"
    axes = fig.subplots(1, 2, sharey=True)
    norm = mpl.colors.Normalize(0, max(OPTIONS))
    titles = {"all0": ("a", "Partners pay 0"), "all4": ("b", "Partners pay 4")}
    for ax, prof in zip(axes, ("all0", "all4")):
        X = np.zeros((len(rows), R))              # best-response row stays 0
        for i, m in enumerate(cs.MODEL_ORDER, start=1):
            S = np.stack(d[(d["profile"] == prof) & (d["model"] == m)]["x"].to_list())
            if S.shape != (50, R):
                raise AssertionError(f"{prof} {m}: {S.shape}")
            X[i] = S.mean(axis=0)
        for (i, t), v in np.ndenumerate(X):
            ax.add_patch(Rectangle((t + 0.5, i - 0.5), 1, 1, fc=cs.CMAP_PAY(norm(v)), ec=cs.WHITE,
                                   lw=0.8, zorder=2))
        ax.axhline(0.5, color=cs.WHITE, lw=2.5, zorder=3)
        ax.plot([modal + 0.5] * 2, [-0.5, len(rows) - 0.5], color=cs.INK, lw=1.0,
                ls=(0, (3.0, 1.6)), zorder=4)
        ax.set_xlim(0.5, R + 0.5)
        ax.set_ylim(len(rows) - 0.5, -0.5)
        cs.style_matrix_axes(ax)
        ax.set_xticks([1, 4, 7, 10])
        ax.set_xlabel("Round")
        cs.panel_title(ax, *titles[prof])
    cs.row_labels(axes[0], rows)
    sm = mpl.cm.ScalarMappable(norm=norm, cmap=cs.CMAP_PAY)
    cb = fig.colorbar(sm, ax=list(axes), location="right", fraction=0.05, pad=0.03, aspect=14)
    cb.outline.set_visible(False)
    cb.set_ticks(list(OPTIONS))
    cb.ax.tick_params(length=2.0, width=0.6, labelsize=cs.SIZE_SMALL)
    cb.set_label("Units paid per round", fontsize=cs.SIZE_SMALL)
    pdf = cs.save(fig, cd.FIGURES / "fig_scripted", title="fig_scripted")
    print(f"wrote {pdf} (+ .png)")


if __name__ == "__main__":
    main()
