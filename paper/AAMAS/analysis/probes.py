"""E2 comprehension probes: stated answers versus contributions (know-do gap).

Run from the repository root:
    python paper/AAMAS/analysis/probes.py

Data: results/exp_evprobe (150 self-play games, p in {0.1, 0.5, 0.9}, 10 reps per model)
and results/exp_evprobe_probes.csv. Probes go to Player_1 (agent1) at rounds 1, 5 and 10
in separate calls that never enter the game history.

Writes
    paper/AAMAS/figures/fig_knowdo.pdf (+ .png)
    paper/AAMAS/tables/num_probes.tex

The value_compare question offers (A) pay 2 in every round and the group reaches the
target (20 for certain) against (B) pay 0 in every round and the group misses (keep 40
unless the disaster strikes). The answer code is decoded from the question text and
asserted below: 1 = A pays more, 2 = B ("keeping") pays more, 0 = exactly equal.

Unit = game. Answer shares are per-game shares over the three probe rounds, so the mean
over games equals the pooled answer share; CIs are game-level percentile bootstraps.
"""
from __future__ import annotations

import re
import sys

import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.transforms import blended_transform_factory

import crsd_data as cd
import crsd_style as cs

EXP = "exp_evprobe"
RISKS = (0.1, 0.5, 0.9)
ROUNDS = (1, 5, 10)
ANS_EQUAL, ANS_FAIR, ANS_KEEP = 0, 1, 2
THREE = ("Haiku", "Flash-Lite", "Luna")
FIGURE_TEXT_PT = cs.SIZE_LABEL + 0.05  # still at least 8 pt after TeX's 72/72.27 scale


def thousands(n: int) -> str:
    return f"{int(n):,}".replace(",", "{,}")


def pct0(x: float) -> str:
    """Percent with no decimals, rounding half up (never banker's rounding)."""
    return str(int(np.floor(100.0 * x + 0.5 + 1e-9)))


# ------------------------------------------------------------------ decode the question
def decode_value_compare(probes: pd.DataFrame) -> pd.DataFrame:
    vc = probes[probes["question_id"] == "value_compare"].copy()
    texts = vc["question_text"].unique()
    if len(texts) != 1:
        raise AssertionError(f"value_compare has {len(texts)} wordings; decode each one")
    text = texts[0]
    for needle in ("(A) You contribute 2 in every one of the 10 rounds and the group "
                   "reaches the target, so you finish with 20 for certain.",
                   "(B) You contribute 0 in every round and the group does not reach the "
                   "target, so you keep 40 unless the disaster strikes.",
                   "Answer 1 if A is higher, 2 if B is higher, 0 if they are exactly equal."):
        if needle not in text:
            raise AssertionError(f"value_compare wording changed; missing: {needle!r}")
    if vc["parse_failed"].any():
        raise AssertionError("value_compare parse failures present")
    vc["ans"] = vc["parsed_answer"].astype(int)
    vc["gt"] = vc["ground_truth"].astype(int)
    if not set(vc["ans"]) <= {ANS_EQUAL, ANS_FAIR, ANS_KEEP}:
        raise AssertionError(f"unexpected answers {sorted(set(vc['ans']))}")
    # Ground truth from arithmetic: A = 20 for sure, B = (1-p)*40 in expectation.
    for p, gts in vc.groupby("risk_probability")["gt"]:
        ev_a, ev_b = cd.FAIR_TOTAL, (1.0 - p) * cd.ENDOWMENT
        want = ANS_EQUAL if abs(ev_a - ev_b) < 1e-9 else (ANS_KEEP if ev_b > ev_a else ANS_FAIR)
        if set(gts) != {want}:
            raise AssertionError(f"p={p}: ground truth {set(gts)} but arithmetic says {want}")
    if not (vc["correct"] == (vc["ans"] == vc["gt"])).all():
        raise AssertionError("'correct' column disagrees with answer == ground truth")
    return vc


# ------------------------------------------------------------------ data
def load():
    games, _, _ = cd.build([EXP])
    raw = cd._read_experiment(EXP)
    if not (raw["agent1_name"] == "Player_1").all():
        raise AssertionError("agent1 is not Player_1 in every game")
    raw["gid"] = [f"{EXP}|{m}|{float(p):g}|{int(r)}" for m, p, r in
                  zip(raw["folder_model"], raw["risk_probability"], raw["rep"])]
    gid_of = dict(zip(raw["game_id"], raw["gid"]))
    g = games.set_index("gid")
    g["p1_total"] = [float(s[0].sum()) for s in g["strat"]]
    g["p1_llm"] = [cd.SLUG[l[0]] for l in g["llm"]]
    g["model"] = [m[0] if len(m) == 1 else None for m in g["models"]]
    if (g["p1_llm"] != g["model"]).any():
        raise AssertionError("agent1 model differs from the game's model")

    probes = cd.load_probes()
    if not ((probes["player"] == "Player_1") & (probes["player_index"] == 0)).all():
        raise AssertionError("a probe went to a seat other than Player_1")
    if set(probes["round"]) != set(ROUNDS):
        raise AssertionError(f"probe rounds {sorted(set(probes['round']))}")
    probes["gid"] = probes["game_id"].map(gid_of)
    if probes["gid"].isna().any():
        raise AssertionError("probe game_id without a wide row")
    probes["p"] = probes["risk_probability"].astype(float)
    if not np.allclose(probes["p"], g.loc[probes["gid"], "p"].to_numpy()):
        raise AssertionError("probe risk disagrees with game risk")
    if (probes["model"].to_numpy() != g.loc[probes["gid"], "model"].to_numpy()).any():
        raise AssertionError("probe model disagrees with game model")
    return g, probes


# ------------------------------------------------------------------ numbers
def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    g, probes = load()
    vc = decode_value_compare(probes)
    vc["keep"] = (vc["ans"] == ANS_KEEP).astype(float)
    print("value_compare decoded: 0 = equal, 1 = A (pay 2 every round, target reached) "
          "pays more, 2 = B (pay 0, target missed; 'keeping') pays more")
    print("ground truth by p:", vc.groupby("p")["gt"].unique().to_dict())

    n_games = g.shape[0]
    per_game = probes.groupby("gid").size()
    if n_games != 150 or len(per_game) != 150 or not (per_game == 30).all():
        raise AssertionError(f"expected 150 games x 30 probes, got {n_games} / {per_game.describe()}")
    if not (vc.groupby("gid").size() == 3).all():
        raise AssertionError("expected three value_compare answers per game")
    rules = probes[probes["category"] == "rules"]
    value = probes[probes["category"] == "value"]

    M = cd.Macros("probes.py")
    M.add("ProbeGames", str(n_games))
    M.add("ProbeQuestions", thousands(len(probes)))
    M.add("ProbeRuleQuestions", thousands(len(rules)))
    M.add("ProbeRulePct", pct0(rules["correct"].mean()))
    M.add("ProbeValueQuestions", thousands(len(value)))
    print(f"\nprobes {len(probes)}; rules {len(rules)} correct {int(rules['correct'].sum())}; "
          f"value {len(value)}; value_compare {len(vc)}")

    print("\nvalue_compare answer counts by model x p:")
    print(vc.groupby(["model", "p"])["ans"].value_counts().unstack(fill_value=0).to_string())
    for m in cd.MODELS:
        acc = vc.loc[vc["model"] == m, "correct"].mean()
        M.add(f"ProbeCorrect{cd.MACRO[m]}Pct", pct0(acc))
        print(f"  accuracy {m:10} {100 * acc:5.1f}%  (n={int((vc['model'] == m).sum())})")

    qwen_keep = vc.loc[vc["model"] == "Qwen", "keep"].mean()
    M.add("ProbeQwenKeepPct", pct0(qwen_keep))
    grok_r1 = vc[(vc["model"] == "Grok") & (vc["round"] == 1)]
    M.add("ProbeGrokRoundOneKeepPct", pct0(grok_r1["keep"].mean()))
    print(f"\nQwen keep share {qwen_keep:.3f} (n={int((vc['model'] == 'Qwen').sum())}); "
          f"Grok round-1 keep share {grok_r1['keep'].mean():.3f} (n={len(grok_r1)})")

    low15 = vc[vc["model"].isin(THREE) & (vc["p"] == 0.1) & vc["round"].isin([1, 5])]
    M.add("ProbeThreeLowKeepPct", pct0(low15["keep"].mean()))
    print(f"three models p=.1 rounds 1+5 keep: {int(low15['keep'].sum())}/{len(low15)} "
          f"= {100 * low15['keep'].mean():.1f}%")

    three = g[g["model"].isin(THREE)]
    lo_g = three[three["p"] == 0.1]
    hi_g = three[three["p"] == 0.9]
    if set(low15["gid"]) != set(lo_g.index):
        raise AssertionError("the low-risk answer set and game set differ")
    M.add("ProbeThreeLowContrib", cd.fmt(lo_g["p1_total"].mean()))
    M.add("ProbeThreeHighContrib", cd.fmt(hi_g["p1_total"].mean()))
    shift = hi_g["p1_total"].mean() - lo_g["p1_total"].mean()
    # Stratified game bootstrap: resample the ten games of each model within each p.
    rng = cd.rng(11)
    cells = [three[(three["model"] == m) & (three["p"] == p)]["p1_total"].to_numpy()
             for p in (0.1, 0.9) for m in THREE]
    draws = np.empty(cd.N_BOOT)
    for b in range(cd.N_BOOT):
        res = [c[rng.integers(0, c.size, c.size)].mean() for c in cells]
        draws[b] = np.mean(res[3:]) - np.mean(res[:3])
    s_lo, s_hi = np.percentile(draws, [2.5, 97.5])
    p_perm = cd.perm_test(hi_g["p1_total"], lo_g["p1_total"], offset=12)
    M.add("ProbeThreeRiskShift", cd.fmt(shift))
    M.add("ProbeThreeRiskShiftLo", cd.fmt(s_lo))
    M.add("ProbeThreeRiskShiftHi", cd.fmt(s_hi))
    print(f"three models Player_1 total: p=.1 {lo_g['p1_total'].mean():.3f} (n={len(lo_g)}), "
          f"p=.9 {hi_g['p1_total'].mean():.3f} (n={len(hi_g)}); shift {shift:+.3f} "
          f"95% CI [{s_lo:+.2f}, {s_hi:+.2f}] (stratified game bootstrap, {cd.N_BOOT}); "
          f"permutation P={p_perm:.3f}")

    wide = vc.pivot_table(index=["model", "p", "gid"], columns="round", values="ans")
    switched = wide.nunique(axis=1) > 1
    luna_switch = int(switched.loc["Luna"].sum())
    n_luna = int(switched.loc["Luna"].size)
    if n_luna != 30:
        raise AssertionError(f"Luna has {n_luna} probed games")
    M.add("ProbeLunaSwitchGames", str(luna_switch))
    print("games whose value_compare answer changes across rounds 1/5/10:",
          switched.groupby(level="model").sum().to_dict(), "of 30 each")

    # per-model, per-p summaries for the figure
    summ = []
    for m in cs.MODEL_ORDER:
        for i, p in enumerate(RISKS):
            share = vc[(vc["model"] == m) & (vc["p"] == p)].groupby("gid")["keep"].mean()
            tot = g[(g["model"] == m) & (g["p"] == p)]["p1_total"]
            if len(share) != 10 or len(tot) != 10:
                raise AssertionError(f"{m} p={p}: {len(share)} probed / {len(tot)} games")
            k_lo, k_hi = cd.boot_ci(share, offset=100 + 10 * i + cs.MODEL_ORDER.index(m))
            t_lo, t_hi = cd.boot_ci(tot, offset=200 + 10 * i + cs.MODEL_ORDER.index(m))
            summ.append(dict(model=m, p=p, keep=share.mean(), keep_lo=k_lo, keep_hi=k_hi,
                             tot=tot.mean(), tot_lo=t_lo, tot_hi=t_hi))
    S = pd.DataFrame(summ)
    print("\nfigure data (keep share, Player_1 total with 95% CI):")
    print(S.round(3).to_string(index=False))

    path = M.write("num_probes.tex")
    print(f"\nwrote {path}")
    for k, v in M.items.items():
        print(f"  \\{k} = {v}")
    figure(vc, g, S)


# ------------------------------------------------------------------ figure
def shifts(vc: pd.DataFrame, g: pd.DataFrame) -> pd.DataFrame:
    """Per model, from p = 0.1 to p = 0.9: the drop in the share of answers saying that
    keeping pays more (x; a correct answerer moves by +1) and the rise in what the
    questioned seat pays (y). Self-play is not a fixed-partner best-response test.
    95% CIs resample the ten games at each risk level independently."""
    lo_p, hi_p = RISKS[0], RISKS[-1]
    rows = []
    for k, m in enumerate(cs.MODEL_ORDER):
        shares = {p: vc[(vc["model"] == m) & (vc["p"] == p)].groupby("gid")["keep"].mean()
                 for p in (lo_p, hi_p)}
        totals = {p: g[(g["model"] == m) & (g["p"] == p)]["p1_total"]
                  for p in (lo_p, hi_p)}
        for p in (lo_p, hi_p):
            if not totals[p].index.is_unique or set(shares[p].index) != set(totals[p].index):
                raise RuntimeError(f"{m} p={p}: answers and contributions must match by game")
        # Resample the same game for the answer and contribution, regardless of row order.
        share = {p: s.to_numpy(float) for p, s in shares.items()}
        paid = {p: totals[p].reindex(shares[p].index).to_numpy(float) for p in shares}
        if any(len(v) != 10 for v in (*share.values(), *paid.values())):
            raise AssertionError(f"{m}: expected ten games at p={lo_p} and p={hi_p}")
        rng = cd.rng(900 + k)
        bx, by = np.empty(cd.N_BOOT), np.empty(cd.N_BOOT)
        for b in range(cd.N_BOOT):
            i_lo, i_hi = rng.integers(0, 10, 10), rng.integers(0, 10, 10)
            bx[b] = share[lo_p][i_lo].mean() - share[hi_p][i_hi].mean()
            by[b] = paid[hi_p][i_hi].mean() - paid[lo_p][i_lo].mean()
        rows.append(dict(model=m, dx=share[lo_p].mean() - share[hi_p].mean(),
                         dy=paid[hi_p].mean() - paid[lo_p].mean(),
                         x_lo=np.percentile(bx, 2.5), x_hi=np.percentile(bx, 97.5),
                         y_lo=np.percentile(by, 2.5), y_hi=np.percentile(by, 97.5)))
    return pd.DataFrame(rows)


def knowdo_data(vc: pd.DataFrame, S: pd.DataFrame) -> pd.DataFrame:
    """Per model and p: the share of value_compare answers saying A (paying) is higher,
    per-game shares with a game-level bootstrap CI, joined to what Player_1 paid (S)."""
    rows = []
    for k, m in enumerate(cs.MODEL_ORDER):
        for i, p in enumerate(RISKS):
            share = vc[(vc["model"] == m) & (vc["p"] == p)].groupby("gid")["ans"].apply(
                lambda a: (a == ANS_FAIR).mean())
            if len(share) != 10:
                raise AssertionError(f"{m} p={p}: {len(share)} probed games")
            a_lo, a_hi = cd.boot_ci(share, offset=500 + 10 * i + k)
            rows.append(dict(model=m, p=p, pay_ans=share.mean(), a_lo=a_lo, a_hi=a_hi))
    D = pd.DataFrame(rows).merge(S[["model", "p", "tot", "tot_lo", "tot_hi"]], on=["model", "p"])
    if len(D) != len(cs.MODEL_ORDER) * len(RISKS):
        raise AssertionError("figure rows do not cover every model x p")
    return D


def levels(vc: pd.DataFrame, g: pd.DataFrame) -> pd.DataFrame:
    """Per model at p = 0.1 and p = 0.9: the share of value answers saying B (keeping)
    pays more and the units Player_1 pays, each with a game-bootstrap 95% CI. These are
    the same inputs and draws as the supplement's knowdo table (supp_probes.table_knowdo,
    offsets 6000+ and 6100+), so the figure and that table print identical intervals."""
    rows = []
    for k, m in enumerate(cd.MODELS):
        for j, p in enumerate(RISKS):
            if p not in (RISKS[0], RISKS[-1]):
                continue
            share = vc[(vc["model"] == m) & (vc["p"] == p)].groupby("gid")["keep"].mean()
            paid = g[(g["model"] == m) & (g["p"] == p)]["p1_total"].astype(float)
            if len(share) != 10 or len(paid) != 10 or set(share.index) != set(paid.index):
                raise RuntimeError(f"{m} p={p}: answers and contributions must match by game")
            s_lo, s_hi = cd.boot_ci(share.to_numpy(), offset=6000 + 10 * j + k)
            t_lo, t_hi = cd.boot_ci(paid.to_numpy(), offset=6100 + 10 * j + k)
            rows.append(dict(model=m, p=p, keep=share.mean(), keep_lo=s_lo, keep_hi=s_hi,
                             paid=paid.mean(), paid_lo=t_lo, paid_hi=t_hi))
    return pd.DataFrame(rows)


def figure(vc: pd.DataFrame, g: pd.DataFrame, S: pd.DataFrame) -> None:
    D = shifts(vc, g)
    print("\nfigure data (shift from p=0.1 to p=0.9 with 95% CI):")
    print(D.round(2).to_string(index=False))
    # the caption's reading: three models flip their answer and keep their payment
    three = D.set_index("model").loc[list(THREE)]
    if (three["dx"] < 0.8).any() or (three["dy"].abs() > 2.0).any():
        raise AssertionError("an answering model no longer flips its answer with flat play; "
                             "revisit the caption of fig_knowdo")

    K = knowdo_data(vc, S)
    print("\nfigure data (share of answers saying paying wins, Player_1 total; 95% CI):")
    print(K.round(3).to_string(index=False))
    t = K[K["model"].isin(THREE)]
    lo, hi = t[t["p"] == RISKS[0]].set_index("model"), t[t["p"] == RISKS[-1]].set_index("model")
    if (hi["pay_ans"] - lo["pay_ans"]).min() < 0.7:
        raise RuntimeError("the three answering models no longer flip their answer")
    if (hi["tot"] - lo["tot"]).abs().max() > 2.0:
        raise RuntimeError("the three answering models no longer pay the same at both risks")

    # One arrow per model from p = 0.1 (open) to p = 0.9 (filled); the arrow is the
    # shift, the translucent bars are the level intervals (the shift intervals are in
    # the supplement). The answer benchmark applies ONLY to the stated A/B question,
    # not to best responses in self-play.
    L = levels(vc, g)
    print("\nfigure data (share saying B, Player_1 total; 95% CI, supplement draws):")
    print(L.round(3).to_string(index=False))
    lv = L.set_index(["model", "p"])
    cs.use()
    fig, (ax, bx) = cs.subplots("col", height_pt=162, ncols=2, sharey=True)
    fig.get_layout_engine().set(wspace=0.06)

    def point(axis, x, y, m, filled):
        st = cs.model(m) if m in cs.MODELS else None
        colour = st.colour if st else cs.MUTED
        axis.plot([x], [y], ls="none", marker=st.marker if st else "o",
                  ms=4.6 * (st.marker_scale if st else 0.92), mfc=colour if filled else cs.WHITE,
                  mec=colour, mew=0.9, zorder=4, clip_on=False)

    def shift(axis, x0, x1, y, colour, dashed=False):
        if abs(x1 - x0) < 0.12 * np.diff(axis.get_xlim())[0]:   # too short for a head
            axis.plot([x0, x1], [y, y], color=colour, lw=1.1, zorder=3)
            return
        axis.annotate("", xy=(x1, y), xytext=(x0, y), zorder=3, arrowprops=dict(
            arrowstyle="-|>", color=colour, lw=1.1, shrinkA=3.2, shrinkB=3.6, mutation_scale=7,
            ls=(0, (3, 1.6)) if dashed else "solid"))

    ax.set_xlim(-7, 107)
    bx.set_xlim(10, 42)
    shift(ax, 100, 0, 0, cs.MUTED, dashed=True)
    point(ax, 100, 0, "Correct", False)
    point(ax, 0, 0, "Correct", True)
    for row, m in enumerate(cs.MODEL_ORDER, start=1):
        st = cs.model(m)
        lo, hi = lv.loc[(m, RISKS[0])], lv.loc[(m, RISKS[-1])]
        for axis, col, scale in ((ax, "keep", 100), (bx, "paid", 1)):
            for r in (lo, hi):
                if r[f"{col}_hi"] > r[f"{col}_lo"]:
                    axis.plot([scale * r[f"{col}_lo"], scale * r[f"{col}_hi"]], [row, row],
                              color=st.colour, lw=5.0, alpha=0.28, solid_capstyle="round",
                              zorder=2)
            shift(axis, scale * lo[col], scale * hi[col], row, st.colour)
            point(axis, scale * lo[col], row, m, False)
            point(axis, scale * hi[col], row, m, True)
    bx.axvline(cd.FAIR_TOTAL, ymin=0, ymax=0.83, **cs.THEORY_SECONDARY)
    for axis in (ax, bx):
        axis.grid(False)
        axis.spines[["left", "right", "top"]].set_visible(False)
        axis.tick_params(axis="both", labelsize=FIGURE_TEXT_PT)
        axis.set_ylim(len(cs.MODEL_ORDER) + 0.45, -0.6)
    bx.tick_params(axis="y", left=False)
    ax.set_xticks([0, 50, 100])
    bx.set_xticks([10, 20, 30, 40])
    ax.set_xlabel("Answers favouring B (%)", fontsize=FIGURE_TEXT_PT)
    bx.set_xlabel("Units paid (of 40)", fontsize=FIGURE_TEXT_PT)
    cs.panel_title(ax, "a", "Answers")
    cs.panel_title(bx, "b", "Play")
    ax.set_yticks(range(len(cs.MODEL_ORDER) + 1),
                  ["Correct"] + [cd.show(m, wrap=True) for m in cs.MODEL_ORDER])
    ax.tick_params(axis="y", length=0, pad=3)
    for t, m in zip(ax.get_yticklabels(), ["Correct", *cs.MODEL_ORDER]):
        t.set_color(cs.MUTED if m == "Correct" else cs.model(m).text)
        t.set_fontstyle("italic" if m == "Correct" else "normal")
    handles = [Line2D([], [], ls="none", marker="o", ms=4.2, mec=cs.INK, mew=0.9,
                      mfc=cs.INK if filled else cs.WHITE, label=f"$p={p:g}$")
               for filled, p in ((False, RISKS[0]), (True, RISKS[-1]))]
    bx.legend(handles=handles, loc="center", bbox_to_anchor=(0.5, 0.0), ncols=2,
              bbox_transform=blended_transform_factory(bx.transAxes, bx.transData),
              fontsize=FIGURE_TEXT_PT, handletextpad=0.2, columnspacing=0.8)
    # Machine-readable source for the plotted estimates, distinct from rounded tables.
    # LF on every platform, so the registered digest does not depend on the OS.
    L.to_csv(cd.FIGURES / "fig_knowdo.csv", index=False, float_format="%.10g",
             lineterminator="\n")
    cs.check_text(fig, min_pt=FIGURE_TEXT_PT)
    pdf = cs.save(fig, cd.FIGURES / "fig_knowdo", title="fig_knowdo", proofs=True)
    print(f"wrote {pdf} (+ .png)")


if __name__ == "__main__":
    main()
