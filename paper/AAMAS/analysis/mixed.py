"""E3b mixed tables: one late defector, and paying less beside an over-contributor.

Run from the repository root:
    python paper/AAMAS/analysis/mixed.py
    python paper/AAMAS/analysis/mixed.py --figure-only  # leaves macros untouched

Reads results/exp_mixed, results/exp_baseline and results/exp_evprobe through crsd_data
(read-only; never Legacy_Results/, never writes under results/). Writes
    paper/AAMAS/figures/fig_mixed.pdf (+ .png preview)
    paper/AAMAS/figures/fig_mixed.csv (plotted estimates and bootstrap provenance)
    paper/AAMAS/tables/num_mixed.tex

DESIGN, CHECKED BEFORE ANYTHING IS COUNTED
    exp_mixed = 10 model pairs x k = 1..5 seats of model A x p in {.1,.5,.9} x 10 reps
    = 1,500 games. Seat truth comes from agent{i}_llm, never from the folder slug.
    Within a (pair, k) cell each model's seats form one contiguous block, and the block
    is identical in every rep and at every p. Nothing below relies on seat rotation,
    because there is none.
    "X alone" = self-play (six X seats) at the same three p. exp_baseline and exp_evprobe
    are the same game condition (probe calls never enter the game history), so they are
    pooled: 20 games per model per p, 60 per model. A baseline-only version is printed.

UNIT = GAME. Rates and means are over games; 95% CIs are game-level percentile
bootstraps (crsd_data.boot_ci). A model's per-seat total in a mixed game is the mean
of the seats it holds in that game.

DEFINITIONS USED BY THE TIMING SPLIT
    Round t is "before the target" when the pot at the START of round t (sum of rounds
    1..t-1, i.e. what the agents have seen) is below 120, and "after" otherwise.
    Shortfall of a seat in a round = max(0, 2 - contribution). Per game: mean over the
    focal model's seats and the rounds of that phase; then the mean over games that
    have at least one round in the phase. Pooled over k = 1..5 Grok seats and all p.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

sys.path.insert(0, str(Path(__file__).resolve().parent))
import crsd_data as cd      # noqa: E402
import crsd_style as cs     # noqa: E402

RISKS = (0.1, 0.5, 0.9)
SELF_EXPS = ("exp_baseline", "exp_evprobe")
PANEL_A = ("Haiku", "Flash-Lite", "Luna", "Grok")     # X alone vs five X + one Qwen
PANEL_B = ("Haiku", "Flash-Lite", "Luna", "Qwen")     # focal model beside Grok seats
POT_BEFORE_LAST = cd.TARGET - cd.N_PLAYERS * cd.FAIR_SHARE   # 108: fair share completes it


def thousands(n: int) -> str:
    return f"{int(n):,}".replace(",", "{,}")


def pct_small(share: float) -> str:
    """Whole percent, but one decimal when a non-zero share would print as 0."""
    return f"{100 * share:.1f}" if 0 < share < 0.005 else cd.pct(share)


# ============================================================================ data
def load():
    games, units, _ = cd.build(("exp_mixed", "exp_baseline", "exp_evprobe"))
    games = games.assign(p=games.p.round(3))
    units = units.assign(p=units.p.round(3))
    mg = games[games.exp == "exp_mixed"].copy()
    mu = units[units.exp == "exp_mixed"].copy()
    su = units[units.exp.isin(SELF_EXPS) & units.p.isin(RISKS)].copy()
    # seat-level model names and the (A, B, kA) cell of every mixed game
    names, cells = [], []
    for g in mg.itertuples():
        ms = [cd.SLUG.get(s) for s in g.llm]
        if None in ms:
            raise ValueError(f"non-LLM seat in mixed game {g.gid}: {g.llm}")
        present = sorted(set(ms), key=cd.MODELS.index)
        if len(present) != 2:
            raise ValueError(f"mixed game {g.gid} holds {present}")
        a, b = present
        names.append(tuple(ms))
        cells.append((a, b, ms.count(a)))
    mg["names"] = names
    mg["A"], mg["B"], mg["kA"] = zip(*cells)
    return mg, mu, su


def check_design(mg, mu, su):
    if len(mg) != 1500:
        raise RuntimeError(f"exp_mixed holds {len(mg)} games, expected 1500")
    pairs = mg.groupby(["A", "B"]).size()
    if len(pairs) != 10 or set(pairs) != {150}:
        raise RuntimeError(f"pair balance broken: {pairs.to_dict()}")
    cell = mg.groupby(["A", "B", "kA", "p"]).rep.apply(lambda s: tuple(sorted(s)))
    if len(cell) != 150 or set(cell) != {tuple(range(10))}:
        raise RuntimeError("a (pair, k, p) cell does not hold reps 0..9 exactly once")
    patterns = {}
    for g in mg.itertuples():
        for m in (g.A, g.B):
            idx = [i for i, n in enumerate(g.names) if n == m]
            if idx != list(range(idx[0], idx[-1] + 1)):
                raise RuntimeError(f"{m} seats not contiguous in {g.gid}: {g.names}")
        patterns.setdefault((g.A, g.B, g.kA), set()).add(g.names)
    if any(len(v) != 1 for v in patterns.values()):
        raise RuntimeError("seat block changes across reps or p within a (pair, k) cell")
    n_self = su.groupby(["model", "p"]).size()
    if len(n_self) != 15 or set(n_self) != {20}:
        raise RuntimeError(f"self-play endpoints unbalanced: {n_self.to_dict()}")
    if set(su.partner) != {"self"}:
        raise RuntimeError("self-play endpoint rows with a partner")
    print(f"design ok: {len(mg)} mixed games, {len(pairs)} pairs, 150 (pair,k,p) cells x 10 reps; "
          f"seat blocks contiguous and fixed within each of {len(patterns)} (pair,k) cells; "
          f"self-play endpoints 20 games per model per p "
          f"({', '.join(f'{e} {int((su.exp == e).sum())}' for e in SELF_EXPS)} rows)")


# ============================================================================ panel a
def panel_a(mg, mu, su):
    rows = []
    for off, x in enumerate(PANEL_A):
        alone = su[su.model == x].reached.to_numpy(float)
        alone_base = su[(su.model == x) & (su.exp == "exp_baseline")].reached.to_numpy(float)
        withq = mu[(mu.model == x) & (mu.partner == "Qwen") & (mu.k == 5)]
        if len(alone) != 60 or len(withq) != 30:
            raise RuntimeError(f"{x}: {len(alone)} alone games, {len(withq)} with-Qwen games")
        w = withq.reached.to_numpy(float)
        rows.append(dict(
            model=x, n_alone=len(alone), alone=alone.mean(), alone_ci=cd.boot_ci(alone, offset=100 + off),
            alone_base=alone_base.mean(), n_base=len(alone_base),
            G_alone=su[su.model == x].G.mean(),
            n_q=len(w), q_hits=int(w.sum()), q=w.mean(), q_ci=cd.boot_ci(w, offset=200 + off),
            G_q=withq.G.mean()))
    A = pd.DataFrame(rows).set_index("model")
    print("\n[a] target reached: X alone (self-play, 20 games x 3 p) vs five X seats + one Qwen seat"
          " (exp_mixed, 10 games x 3 p)")
    for x, r in A.iterrows():
        print(f"  {x:10} alone {100 * r.alone:5.1f}% [{100 * r.alone_ci[0]:.0f},{100 * r.alone_ci[1]:.0f}]"
              f" (n={r.n_alone}, mean group total {r.G_alone:6.1f})"
              f" | +1 Qwen {r.q_hits:2d}/{r.n_q} = {100 * r.q:5.1f}% [{100 * r.q_ci[0]:.0f},{100 * r.q_ci[1]:.0f}]"
              f" (mean group total {r.G_q:6.1f})")
    print("  sensitivity, baseline-only alone: "
          + ", ".join(f"{x} {100 * r.alone_base:.0f}% (n={r.n_base})" for x, r in A.iterrows()))
    return A


# ============================================================================ panel b
def panel_b(mu):
    rows = []
    for mi, m in enumerate(PANEL_B):
        for grok in range(1, 6):
            d = mu[(mu.model == m) & (mu.partner == "Grok") & (mu.k == 6 - grok)]
            if len(d) != 30:
                raise RuntimeError(f"{m} beside {grok} Grok seats: {len(d)} games")
            v = d.own.to_numpy(float)
            lo, hi = cd.boot_ci(v, offset=300 + 10 * mi + grok)
            rows.append(dict(model=m, grok=grok, n=len(v), own=v.mean(), lo=lo, hi=hi))
    B = pd.DataFrame(rows)
    print("\n[b] focal model's mean total per seat by number of Grok seats (pooled p, 30 games per point)")
    for m in PANEL_B:
        d = B[B.model == m]
        print(f"  {m:10} " + "  ".join(f"{g}:{o:5.2f} [{lo:5.2f},{hi:5.2f}]"
                                       for g, o, lo, hi in zip(d.grok, d.own, d.lo, d.hi)))
    return B


def beside(mu):
    out = {}
    print("\nper-seat total holding ONE seat: beside five Grok seats vs beside five seats of each other partner")
    for m in PANEL_B:
        d = mu[(mu.model == m) & (mu.k == 1)]
        five_grok = d[d.partner == "Grok"].own
        others = d[d.partner != "Grok"]
        by = others.groupby("partner").own.mean()
        out[m] = (five_grok.mean(), others.own.mean(), len(five_grok), len(others))
        print(f"  {m:10} five Grok {five_grok.mean():5.2f} (n={len(five_grok)}) | other partners "
              f"{others.own.mean():5.2f} (n={len(others)}; "
              + ", ".join(f"{q} {v:.2f}" for q, v in by.items()) + ")")
    return out


# ============================================================================ timing split
def timing_split(mg):
    rows = []
    for g in mg.itertuples():
        if "Grok" not in (g.A, g.B):
            continue
        m = g.B if g.A == "Grok" else g.A
        idx = [i for i, n in enumerate(g.names) if n == m]
        pot_start = np.r_[0.0, np.cumsum(g.strat.sum(axis=0))[:-1]]
        before = pot_start < cd.TARGET
        sf = np.maximum(0.0, cd.FAIR_SHARE - g.strat[idx])
        rows.append(dict(
            model=m, p=g.p, grok=6 - len(idx),
            early=sf[:, before].mean() if before.any() else np.nan,
            late=sf[:, ~before].mean() if (~before).any() else np.nan,
            tot_early=sf[:, before].sum(axis=1).mean(), tot_late=sf[:, ~before].sum(axis=1).mean(),
            sum_early=sf[:, before].sum(), dec_early=len(idx) * before.sum(),
            sum_late=sf[:, ~before].sum(), dec_late=len(idx) * (~before).sum()))
    T = pd.DataFrame(rows)
    print("\ntiming split beside Grok (k = 1..5 Grok seats, all p; 150 games per model)")
    print("  shortfall below 2 per seat-round: game-level mean BEFORE the pot reached 120 | AFTER"
          " | per-seat game total before + after = share after | decision-pooled before, after")
    out = {}
    for m in PANEL_B:
        d = T[T.model == m]
        e, l = d.early.mean(), d.late.mean()
        e_ci = cd.boot_ci(d.early.dropna(), offset=400 + PANEL_B.index(m))
        te, tl = d.tot_early.mean(), d.tot_late.mean()
        out[m] = dict(early=e, late=l)
        print(f"  {m:10} before {e:.3f} [{e_ci[0]:.3f},{e_ci[1]:.3f}] (n={d.early.count()})"
              f" | after {l:.3f} (n={d.late.count()} games with rounds after)"
              f" | total {te:.2f} + {tl:.2f} = {te + tl:.2f}, share after {tl / (te + tl):.0%}"
              f" | pooled {d.sum_early.sum() / d.dec_early.sum():.3f}, "
              f"{d.sum_late.sum() / max(d.dec_late.sum(), 1):.3f}")
    return out


# ============================================================================ pivotal zeros
def pivotal(mg):
    print(f"\nround-10 decisions when the pot after round 9 is exactly {POT_BEFORE_LAST:.0f}")
    dec = []
    for g in mg.itertuples():
        if abs(g.pot[8] - POT_BEFORE_LAST) > 1e-9:
            continue
        for i, n in enumerate(g.names):
            dec.append(dict(gid=g.gid, model=n, x=g.strat[i, 9]))
    D = pd.DataFrame(dec)
    zero = {}
    for m in cd.MODELS:
        d = D[D.model == m]
        zero[m] = (d.x == 0).mean()
        print(f"  {m:10} {100 * zero[m]:5.1f}% zero of {len(d)} decisions in {d.gid.nunique()} games")
    miss = mg[mg.reached == 0]
    with_q = miss[[("Qwen" in (a, b)) for a, b in zip(miss.A, miss.B)]]
    fixed = 0
    for g in with_q.itertuples():
        nz = sum(1 for i, n in enumerate(g.names) if n == "Qwen" and g.strat[i, 9] == 0)
        fixed += int(g.G + cd.FAIR_SHARE * nz >= cd.TARGET)
    print(f"  missed mixed games {len(miss)}; containing Qwen {len(with_q)}; "
          f"reach the target if Qwen's round-10 zeros were 2: {fixed}/{len(with_q)} "
          f"= {100 * fixed / len(with_q):.1f}%")
    return zero, len(miss), len(with_q), fixed / len(with_q)


# ============================================================================ figure
# Keep the shared model hues, text variants and marker shapes. Filled/open marks
# encode the two independent conditions in A, not a time sequence or causal effect.
# The local 8 pt floor is stricter than the shared style's 7 pt default.
FIGURE_HEIGHT_PT = 159.5
# A PDF point is 1/72 inch; the manuscript's column width is in 1/72.27 inch.
# Compensate for inclusion at columnwidth, with a small rounding margin.
FIGURE_TEXT_PT = cs.SIZE_LABEL * 72.27 / cs.POINTS_PER_INCH + 0.02


def interval(ax, x, y, lo, hi, name, *, filled=True):
    """Draw an existing estimate and its game-level bootstrap CI as a translucent bar,
    without offsets to the measured value. A zero-width interval draws no bar."""
    st = cs.model(name)
    if not lo - 1e-9 <= x <= hi + 1e-9:
        raise ValueError(f"{name}: estimate {x} outside [{lo}, {hi}]")
    if hi > lo:
        ax.plot([lo, hi], [y, y], color=st.colour, lw=5.0, alpha=0.28,
                solid_capstyle="round", zorder=2)
    ax.plot([x], [y], ls="none", marker=st.marker, ms=4.6 * st.marker_scale,
            mfc=st.colour if filled else cs.WHITE, mec=st.colour, mew=0.9, zorder=4,
            clip_on=False)


def figure(A, B):
    cs.use()
    fig = plt.figure(figsize=cs.figsize("col", height_pt=FIGURE_HEIGHT_PT))
    fig._crsd_width = "col"
    ax, bx = fig.subplots(1, 2, gridspec_kw={"width_ratios": [1, 1.25], "wspace": 0.06})

    # ---- a: one row per model, an arrow from self-play (filled) to one Qwen seat
    # (open); both conditions keep their own interval, even at 100%.
    rows_a = list(PANEL_A)
    ax.set_xlim(-6, 106)
    for i, x in enumerate(rows_a):
        r, st = A.loc[x], cs.model(x)
        if abs(r.q - r.alone) > 0.12:
            ax.annotate("", xy=(100 * r.q, i), xytext=(100 * r.alone, i), zorder=3,
                        arrowprops=dict(arrowstyle="-|>", color=st.colour, lw=1.1,
                                        shrinkA=3.2, shrinkB=3.6, mutation_scale=7))
        elif r.q == r.alone:
            ax.annotate("no change", (100 * r.q, i), xytext=(-7, 0), textcoords="offset points",
                        ha="right", va="center", fontsize=FIGURE_TEXT_PT, color=cs.MUTED,
                        fontstyle="italic")
        # Open first, so a filled marker stays visible when the two coincide.
        interval(ax, 100 * r.q, i, *(100 * np.array(r.q_ci)), x, filled=False)
        interval(ax, 100 * r.alone, i, *(100 * np.array(r.alone_ci)), x)
    ax.set_xticks([0, 50, 100])
    ax.set_xlabel("Target reached (%)", fontsize=FIGURE_TEXT_PT)
    cs.row_labels(ax, rows_a, wrap=True)
    ax.set_ylim(len(rows_a) - 0.5, -0.5)
    ax.spines[["left", "right", "top"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.grid(False)
    condition_handles = [
        Line2D([], [], marker="o", ls="none", ms=4.4, mec=cs.INK,
               mfc=cs.INK if filled else cs.WHITE, mew=0.9, label=label)
        for filled, label in ((True, "Self-play"), (False, "+1 Qwen"))
    ]
    fig.legend(handles=condition_handles, loc="outside lower left", ncols=2,
               fontsize=FIGURE_TEXT_PT, handletextpad=0.2)

    # ---- b: every composition has its own x position; the band is its interval.
    # Lines only join measured means; no fit, interpolation of data, or causal arrows.
    for m in PANEL_B:
        d = B[B.model == m].sort_values("grok")
        if list(d.grok) != [1, 2, 3, 4, 5]:
            raise RuntimeError(f"{m}: Grok seat counts {list(d.grok)}")
        if ((d.own < d.lo - 1e-9) | (d.own > d.hi + 1e-9)).any():
            raise ValueError(f"{m}: an estimate lies outside its interval")
        st = cs.model(m)
        bx.fill_between(d.grok, d.lo, d.hi, color=st.colour, alpha=0.18, lw=0, zorder=1.5)
        bx.plot(d.grok, d.own, color=st.colour, lw=cs.LW_DATA, marker=st.marker,
                ms=4.0 * st.marker_scale, mfc=st.colour, mec=cs.WHITE, mew=0.5, zorder=3)
        bx.annotate(m, (5, d.own.iloc[-1]), xytext=(4, 0), textcoords="offset points",
                    ha="left", va="center", fontsize=FIGURE_TEXT_PT, color=st.text,
                    annotation_clip=False)
    bx.axhline(cd.FAIR_TOTAL, **cs.THEORY_SECONDARY)
    bx.set_xlim(0.7, 5.3)
    bx.set_xticks(range(1, 6))
    bx.set_ylim(min(8.0, float(np.floor(B.lo.min())) - 1),
                max(25.5, float(np.ceil(B.hi.max())) + 1))
    bx.set_yticks([10, 15, 20, 25])
    bx.set_xlabel("Grok 4.20 seats", fontsize=FIGURE_TEXT_PT)
    bx.set_ylabel("Units per seat", fontsize=FIGURE_TEXT_PT)

    for axis, letter, title in ((ax, "a", "One replacement"), (bx, "b", "Beside Grok 4.20")):
        cs.panel_title(axis, letter, title)
        axis.tick_params(labelsize=FIGURE_TEXT_PT)
        axis.set_axisbelow(True)
    cs.check_text(fig, min_pt=FIGURE_TEXT_PT)
    return fig


def save_figure(A, B):
    fig = figure(A, B)
    pdf = cs.save(fig, cd.FIGURES / "fig_mixed", proofs=True,
                  title="Mixed groups: target success and contributions by composition")
    rows = []
    for off, m in enumerate(PANEL_A):
        r = A.loc[m]
        for condition, value, ci, n, seed_offset, experiments in (
            ("self_play", r.alone, r.alone_ci, r.n_alone, 100 + off, ";".join(SELF_EXPS)),
            ("one_Qwen_seat", r.q, r.q_ci, r.n_q, 200 + off, "exp_mixed"),
        ):
            rows.append(dict(panel="a", model=cd.show(m), condition=condition,
                             grok_seats=None, estimate=100 * value, ci_low=100 * ci[0],
                             ci_high=100 * ci[1], unit="percent_games_reaching_target",
                             n_games=int(n), bootstrap_seed=cd.SEED + seed_offset,
                             experiments=experiments))
    for r in B.itertuples():
        rows.append(dict(panel="b", model=cd.show(r.model), condition="beside_Grok",
                         grok_seats=r.grok, estimate=r.own, ci_low=r.lo, ci_high=r.hi,
                         unit="mean_units_per_focal_seat_per_game", n_games=r.n,
                         bootstrap_seed=cd.SEED + 300 + 10 * PANEL_B.index(r.model) + r.grok,
                         experiments="exp_mixed"))
    provenance = pd.DataFrame(rows)
    provenance["grok_seats"] = provenance.grok_seats.astype("Int64")
    provenance["risk_levels"] = ";".join(map(str, RISKS))
    provenance["games_per_risk"] = provenance.n_games // len(RISKS)
    provenance["bootstrap_draws"] = cd.N_BOOT
    provenance["ci_method"] = "percentile_2.5_97.5;pooled_games;not_risk_stratified"
    # LF on every platform, so the registered digest does not depend on the OS.
    provenance.to_csv(cd.FIGURES / "fig_mixed.csv", index=False, lineterminator="\n")
    print(f"wrote {pdf.relative_to(cd.REPO)} (+ .png, greyscale/CVD proof, .csv)")
    print(f"figure gates passed: {cs.COL_W_PT:.4f} x {FIGURE_HEIGHT_PT} PDF pt; "
          f"text >= {FIGURE_TEXT_PT:.2f} PDF pt "
          f"({FIGURE_TEXT_PT * cs.POINTS_PER_INCH / 72.27:.3f} after placement); "
          "text overlap, marker bounds, PDF width and fonts; "
          "8 condition estimates and 20 composition estimates, all with 95% bootstrap CIs")


# ============================================================================ main
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--figure-only", action="store_true",
                        help="regenerate the figure and provenance without writing macros")
    args = parser.parse_args()
    mg, mu, su = load()
    check_design(mg, mu, su)
    A = panel_a(mg, mu, su)
    B = panel_b(mu)
    if args.figure_only:
        save_figure(A, B)
        return
    bes = beside(mu)
    split = timing_split(mg)
    zero, n_miss, n_miss_q, fix_share = pivotal(mg)

    mac = cd.Macros("mixed.py")
    mac.add("MixGames", thousands(len(mg)))
    mac.add("MixPairs", str(mg.groupby(["A", "B"]).ngroups))
    mac.add("MixFlashAloneReach", cd.pct(A.loc["Flash-Lite", "alone"]))
    mac.add("MixFlashQwenReach", str(A.loc["Flash-Lite", "q_hits"]))
    mac.add("MixLunaAloneReach", cd.pct(A.loc["Luna", "alone"]))
    mac.add("MixLunaQwenReach", str(A.loc["Luna", "q_hits"]))
    mac.add("MixHaikuQwenReach", str(A.loc["Haiku", "q_hits"]))
    mac.add("MixGrokQwenReach", str(A.loc["Grok", "q_hits"]))
    mac.add("MixQwenPotZeroPct", pct_small(zero["Qwen"]))
    mac.add("MixFlashPotZeroPct", pct_small(zero["Flash-Lite"]))
    mac.add("MixMissWithQwen", str(n_miss_q))
    mac.add("MixMissTotal", str(n_miss))
    mac.add("MixQwenPivotalFix", cd.pct(fix_share))
    mac.add("MixLunaBesideFiveGrok", cd.fmt(bes["Luna"][0], 1))
    mac.add("MixLunaBesideOthers", cd.fmt(bes["Luna"][1], 1))
    mac.add("MixFlashBesideFiveGrok", cd.fmt(bes["Flash-Lite"][0], 1))
    mac.add("MixHaikuBesideFiveGrok", cd.fmt(bes["Haiku"][0], 1))
    mac.add("MixLunaEarlyShort", cd.fmt(split["Luna"]["early"], 2))
    mac.add("MixFlashEarlyShort", cd.fmt(split["Flash-Lite"]["early"], 2))
    mac.add("MixHaikuEarlyShort", cd.fmt(split["Haiku"]["early"], 2))
    # One generous seat among five Qwen seats: does it give the table enough slack?
    for macro, partner in (("MixGrokRescuesQwen", "Grok"), ("MixHaikuRescuesQwen", "Haiku")):
        d = mu[(mu.model == "Qwen") & (mu.partner == partner) & (mu.k == 5)]
        if len(d) != 30:
            raise RuntimeError(f"five Qwen + one {partner}: {len(d)} games")
        print(f"  five Qwen + one {partner}: target {int(d.reached.sum())}/30")
        mac.add(macro, str(int(d.reached.sum())))
    # Qwen does not pay less beside Grok.
    qg = mu[(mu.model == "Qwen") & (mu.partner == "Grok")].own.mean()
    qo = mu[(mu.model == "Qwen") & (mu.partner != "Grok")].own.mean()
    print(f"  Qwen per-seat total beside Grok {qg:.2f} vs beside others {qo:.2f}")
    if qg < qo:
        raise RuntimeError("Qwen now pays less beside Grok; revisit the text")
    mac.add("MixQwenBesideGrok", cd.fmt(qg, 1))
    mac.add("MixQwenBesideOthers", cd.fmt(qo, 1))
    path = mac.write("num_mixed.tex")
    print(f"\nwrote {path.relative_to(cd.REPO)}")
    for k, v in mac.items.items():
        print(f"  \\{k} = {v}")

    save_figure(A, B)


if __name__ == "__main__":
    main()
