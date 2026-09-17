"""E3b mixed tables: one late defector, and paying less beside an over-contributor.

Run from the repository root:
    python paper/AAMAS/analysis/mixed.py

Reads results/exp_mixed, results/exp_baseline and results/exp_evprobe through crsd_data
(read-only; never Legacy_Results/, never writes under results/). Writes
    paper/AAMAS/figures/fig_mixed.pdf (+ .png preview)
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

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

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
SAME_X = 1.0      # a shift smaller than this draws a dot inside a ring instead of an arrow


def dumbbell(ax, y, x_from, x_to, name, ci_to=None, mids=()):
    """Filled marker = before, open marker = after, arrow = the change. `mids` are the
    intermediate steps, drawn as small dots on the shaft."""
    st = cs.model(name)
    if ci_to is not None and ci_to[1] - ci_to[0] > 1e-9:
        ax.plot(ci_to, [y, y], color=st.colour, lw=0.8, alpha=0.55, zorder=2, solid_capstyle="butt")
    same = abs(x_to - x_from) < SAME_X
    if not same:
        ax.add_patch(FancyArrowPatch((x_from, y), (x_to, y), arrowstyle="-|>", mutation_scale=7,
                                     lw=1.1, color=st.colour, shrinkA=4.2, shrinkB=4.6, zorder=2.5))
    for xm in mids:
        ax.plot([xm], [y], marker="o", ms=2.2, color=st.colour, mec="none", ls="none", zorder=2.6)
    ms = 5.4 * st.marker_scale
    ax.plot([x_from], [y], marker=st.marker, ms=ms * (0.55 if same else 1.0), mfc=st.colour,
            mec=cs.WHITE, mew=0.0 if same else 0.6, ls="none", zorder=3.1 if same else 3)
    ax.plot([x_to], [y], marker=st.marker, ms=ms, mfc="none" if same else cs.WHITE, mec=st.colour,
            mew=1.1, ls="none", zorder=3)


def key(ax, x, y, filled, text):
    ax.plot([x], [y], marker="o", ms=4.6, mfc=cs.INK if filled else cs.WHITE, mec=cs.INK, mew=0.9,
            ls="none", zorder=3, clip_on=False)
    ax.annotate(text, (x, y), xytext=(4, 0), textcoords="offset points", ha="left", va="center",
                fontsize=cs.SIZE_SMALL, color=cs.INK)


def figure(A, B):
    cs.use()
    fig = plt.figure(figsize=cs.figsize("col", height_pt=118))
    fig._crsd_width = "col"
    ax, bx = fig.subplots(1, 2)
    key_y = -0.95          # the empty row above the first model holds the key

    # ---- a: target reached, six seats of X (filled) -> five X seats + one Qwen seat (open)
    rows_a = list(PANEL_A)
    for i, x in enumerate(rows_a):
        r = A.loc[x]
        dumbbell(ax, i, 100 * r.alone, 100 * r.q, x, ci_to=(100 * r.q_ci[0], 100 * r.q_ci[1]))
    ax.set_xlim(-6, 106)
    ax.set_xticks([0, 50, 100])
    ax.set_xlabel("Target reached (%)")
    key(ax, -2, key_y, False, f"+1 {cd.show('Qwen')}")
    key(ax, 74, key_y, True, "Alone")   # right of "+1 Qwen3-235B", which is longer than it was
    cs.panel_title(ax, "a", "One late dropout")

    # ---- b: per-seat total beside 1 Grok seat (filled) -> 5 Grok seats (open), 2-4 as dots
    rows_b = list(PANEL_B)
    for i, m in enumerate(rows_b):
        d = B[B.model == m].sort_values("grok")
        if list(d.grok) != [1, 2, 3, 4, 5]:
            raise RuntimeError(f"{m}: Grok seat counts {list(d.grok)}")
        v = d.own.to_numpy(float)
        dumbbell(bx, i, v[0], v[-1], m, ci_to=(d.lo.iloc[-1], d.hi.iloc[-1]), mids=v[1:-1])
    bx.axvline(cd.FAIR_TOTAL, **{k: w for k, w in cs.THEORY_SECONDARY.items() if k != "marker"})
    lo = min(8.0, float(np.floor(B.lo.min())))
    hi = max(26.0, float(np.ceil(B.hi.max())))
    bx.set_xlim(lo, hi)
    bx.set_xticks([10, 15, 20, 25])
    bx.set_xlabel("Units per seat")
    key(bx, lo + 0.6, key_y, False, "5 seats")
    key(bx, 21.2, key_y, True, "1 seat")
    cs.panel_title(bx, "b", f"Beside {cd.show('Grok')}")

    for axis, rows in ((ax, rows_a), (bx, rows_b)):
        cs.row_labels(axis, rows, wrap=True)
        axis.set_ylim(len(rows) - 0.5, -1.3)
        axis.grid(False)
        axis.xaxis.grid(True)
        axis.spines["left"].set_visible(False)
        axis.tick_params(axis="y", length=0)
    return fig


# ============================================================================ main
def main():
    mg, mu, su = load()
    check_design(mg, mu, su)
    A = panel_a(mg, mu, su)
    B = panel_b(mu)
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

    fig = figure(A, B)
    pdf = cs.save(fig, cd.FIGURES / "fig_mixed", title="fig_mixed")
    print(f"wrote {pdf.relative_to(cd.REPO)} (+ .png)")


if __name__ == "__main__":
    main()
