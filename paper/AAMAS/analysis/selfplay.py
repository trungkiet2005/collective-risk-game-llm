"""Self-play on the risk grid, the no-cue control and the robustness arms.

Run from the repository root:
    python paper/AAMAS/analysis/selfplay.py

Writes (and nothing else):
    paper/AAMAS/figures/fig_selfplay.pdf (+ .png preview)
    paper/AAMAS/tables/tab_models.tex     one-column tabular, five models on the grid
    paper/AAMAS/tables/tab_robust.tex     one-column tabular, level per arm at p in {.1,.9}
    paper/AAMAS/tables/num_selfplay.tex   \\newcommand macros quoted in the prose

Conventions (crsd_data): unit of analysis = game; payoffs are EXPECTED over the
catastrophe lottery; CIs are percentile bootstraps over games, stratified by risk cell
whenever a quantity pools several p; permutation tests shuffle game labels, within risk
cell when pooling. Reads results/ read-only; never touches Legacy_Results/.
"""
from __future__ import annotations

import math
import os
import pathlib
import sys
from decimal import ROUND_HALF_UP, Decimal

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import crsd_data as cd  # noqa: E402
import crsd_style as cs  # noqa: E402

pd.set_option("display.width", 220)
MODELS = cd.MODELS
BASE = "exp_baseline"
ENDPOINTS = (0.1, 0.9)
_OFFSET = [100]          # distinct RNG stream per resampling call, deterministic order


def next_offset() -> int:
    _OFFSET[0] += 1
    return _OFFSET[0]


# ------------------------------------------------------------------ formatting
def rnd(x: float, digits: int = 1) -> str:
    """Half-up rounding (not banker's), true minus for LaTeX, no '-0.0'."""
    q = Decimal(1).scaleb(-digits)
    s = str(Decimal(repr(float(x))).quantize(q, rounding=ROUND_HALF_UP))
    if s.startswith("-") and float(s) == 0:
        s = s[1:]
    return "$-$" + s[1:] if s.startswith("-") else s


def pct(x: float, digits: int = 0) -> str:
    """Percent; a value that is not exactly 0 or 100 never prints as 0 or 100."""
    s = rnd(100.0 * x, digits)
    if s in ("0", "100") and not np.isclose(100.0 * x, float(s)):
        s = rnd(100.0 * x, digits + 1)
    return s


def thousands(n: int) -> str:
    return f"{int(n):,}".replace(",", "{,}")


# ------------------------------------------------------------------ statistics
def strat_boot_ci(values, strata, stat="mean", denom=None, n=cd.N_BOOT):
    """Percentile bootstrap over games, resampling within each stratum.

    stat="mean": CI of the pooled mean.  stat="ratio": CI of 100*(1 - sum(values)/sum(denom)).
    """
    v = np.asarray(values, float)
    s = np.asarray(strata)
    d = None if denom is None else np.asarray(denom, float)
    g = cd.rng(next_offset())
    num = np.zeros(n)
    den = np.zeros(n)
    for key in np.unique(s):
        idx_all = np.flatnonzero(s == key)
        pick = idx_all[g.integers(0, idx_all.size, (n, idx_all.size))]
        num += v[pick].sum(1)
        den += (d[pick].sum(1) if d is not None else np.full(n, idx_all.size))
    draws = 100.0 * (1.0 - num / den) if stat == "ratio" else num / den
    return float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))


def strat_boot_diff_ci(x, sx, y, sy, n=cd.N_BOOT):
    """CI of mean(y) - mean(x); each arm resampled within its own risk cells."""
    g = cd.rng(next_offset())

    def draws(v, s):
        v, s = np.asarray(v, float), np.asarray(s)
        tot = np.zeros(n)
        for key in np.unique(s):
            a = v[s == key]
            tot += a[g.integers(0, a.size, (n, a.size))].sum(1)
        return tot / v.size

    dd = draws(y, sy) - draws(x, sx)
    return float(np.percentile(dd, 2.5)), float(np.percentile(dd, 97.5))


def strat_perm(x, sx, y, sy, n=cd.N_PERM):
    """Two-sided permutation p for mean(y) - mean(x), arm labels shuffled within risk cell."""
    x, y, sx, sy = (np.asarray(a) for a in (x, y, sx, sy))
    x, y = x.astype(float), y.astype(float)
    obs = y.mean() - x.mean()
    g = cd.rng(next_offset())
    pools = []
    for key in np.unique(np.concatenate([sx, sy])):
        pools.append((np.concatenate([x[sx == key], y[sy == key]]), int((sx == key).sum())))
    hits = 0
    for _ in range(n):
        sum_x = sum_y = 0.0
        for pool, k in pools:
            perm = g.permutation(pool)
            sum_x += perm[:k].sum()
            sum_y += perm[k:].sum()
        if abs(sum_y / y.size - sum_x / x.size) >= abs(obs) - 1e-12:
            hits += 1
    return float(obs), (hits + 1) / (n + 1)


# ------------------------------------------------------------------ data
def load():
    games, units, seats = cd.build()
    for frame in (games, units, seats):
        frame["p"] = frame["p"].round(1)
    return games, units, seats


def e7_analytic_check():
    """Risk-neutral EV maximiser, symmetric seats: group total 0 below p*, 120 at/above."""
    per_seat = np.arange(0, 41, 2, dtype=float)       # feasible per-seat totals
    for p in np.round(np.arange(0.0, 1.0001, 0.05), 2):
        pay = np.where(cd.N_PLAYERS * per_seat >= cd.TARGET, cd.ENDOWMENT - per_seat,
                       (1 - p) * (cd.ENDOWMENT - per_seat))
        best = set(cd.N_PLAYERS * per_seat[np.isclose(pay, pay.max())])
        want = 0.0 if p < cd.PSTAR else cd.TARGET
        if want not in best:
            raise RuntimeError(f"E7 check: at p={p} the EV maximiser total {best} excludes {want}")
        if p != cd.PSTAR and best != {want}:
            raise RuntimeError(f"E7 check: at p={p} the EV maximiser is not unique: {best}")
        if not np.isclose(pay.max(), float(cd.opt_payoff(p))):
            raise RuntimeError(f"E7 check: opt_payoff({p}) disagrees with the brute force")
    print("E7 analytic check: EV-maximiser group total is 0 for p<0.5 and 120 for p>=0.5 "
          "(both optimal at p=0.5); opt_payoff matches the brute force.")


# ------------------------------------------------------------------ figure
LOSS_PARTS = (("B", "Below $p^*$", "////"), ("A", "Past 120", "xxxx"), ("C", "Missed", "...."))


def figure(units, games):
    """Three panels that share one row per model (plus a reference row on top).
    a  mean units a seat pays at each p; the top row is the optimum of Proposition 1.
    b  which move (0, 2 or 4) seats make in each round, pooled over p > 0.
    c  the share of the attainable payoff opt(p) that is kept, and how the rest is lost:
       paying toward the target below p* (B), paying past 120 (A), missing at p >= p* (C).
       The parts are the ones behind the Main loss column of the model table."""
    base_u = units[units.exp == BASE].copy()
    base_g = games[games.exp == BASE]
    risks = np.sort(base_u.p.unique())
    rows = ["Optimum", *cs.MODEL_ORDER]
    ylim = (len(rows) - 0.5, -0.5)

    cs.use()
    fig = plt.figure(figsize=cs.figsize("full", height_pt=126))
    fig._crsd_width = "full"
    grid = fig.add_gridspec(1, 3, width_ratios=[1.62, 1.0, 0.78])
    ax_a, ax_b, ax_c = (fig.add_subplot(grid[0, i]) for i in range(3))

    # ---- a: mean total per seat, rows x risk; hue = model, lightness = amount (0..40)
    M_ = np.full((len(rows), len(risks)), np.nan)
    M_[0] = np.where(risks < cd.PSTAR, 0.0, cd.FAIR_TOTAL)
    for i, m in enumerate(cs.MODEL_ORDER, start=1):
        d = base_u[base_u.model == m]
        M_[i] = [d[d.p == p].own.mean() for p in risks]
    print("\nFigure panel a: mean total per seat by p")
    for r, vals in zip(rows, M_):
        print(f"  {r:10s} " + " ".join(f"{v:5.1f}" for v in vals))
    for (i, j), v in np.ndenumerate(M_):
        c = cs.MUTED if i == 0 else cs.model(rows[i]).text
        if i == 0 and np.isclose(risks[j], cd.PSTAR):     # both 0 and 20 are optimal at p*
            lo_fc, hi_fc = cs.ramp(c, 0.04), cs.ramp(c, 0.52)
            ax_a.add_patch(Polygon([(j - .5, -.5), (j + .5, -.5), (j - .5, .5)], fc=lo_fc, ec="none",
                                   zorder=2))
            ax_a.add_patch(Polygon([(j + .5, -.5), (j + .5, .5), (j - .5, .5)], fc=hi_fc, ec="none",
                                   zorder=2))
            ax_a.text(j - .22, -.2, "0", ha="center", va="center", fontsize=cs.SIZE_SMALL,
                      color=cs.cell_ink(lo_fc), fontstyle="italic", zorder=3)
            ax_a.text(j + .2, .2, "20", ha="center", va="center", fontsize=cs.SIZE_SMALL,
                      color=cs.cell_ink(hi_fc), fontstyle="italic", zorder=3)
            continue
        fc = cs.ramp(c, 0.04 + 0.96 * v / cd.ENDOWMENT)
        ax_a.add_patch(Rectangle((j - .5, i - .5), 1, 1, fc=fc, ec="none", zorder=2))
        ax_a.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=cs.SIZE_SMALL,
                  color=cs.cell_ink(fc), fontstyle="italic" if i == 0 else "normal", zorder=3)
    for x in np.arange(0.5, len(risks) - 0.5):
        ax_a.axvline(x, color=cs.WHITE, lw=1.0, zorder=2.5)
    for y in np.arange(0.5, len(rows) - 0.5):
        ax_a.axhline(y, color=cs.WHITE, lw=3.0 if y < 1 else 1.0, zorder=2.5)
    ax_a.set_xlim(-0.5, len(risks) - 0.5)
    ax_a.set_xticks(range(len(risks)), [f"{p:g}" for p in risks])
    ax_a.set_xlabel("Catastrophe probability $p$")
    cs.panel_title(ax_a, "a", "Units a seat pays, out of 40")

    # ---- b: share of seats making each move, per round, pooled over p > 0
    pos = base_g[base_g.p > 0]
    height = 0.80
    print(f"\nFigure panel b: share of moves 0/2/4 by round, p>0 ({len(pos)} games)")
    for i, m in enumerate(cs.MODEL_ORDER, start=1):
        d = pos[pos.models.map(lambda t: t == (m,))]
        if len(d) != 100:
            raise RuntimeError(f"panel b expects 100 games for {m}, found {len(d)}")
        S = np.concatenate(d.strat.to_list(), axis=0)                  # seats x rounds
        shares = np.array([[np.mean(S[:, t] == a) for t in range(cd.N_ROUNDS)] for a in (0, 2, 4)])
        if not np.allclose(shares.sum(axis=0), 1.0):
            raise RuntimeError(f"{m}: a move outside 0, 2, 4")
        print(f"  {m:10s} pay 0: " + " ".join(f"{v:4.2f}" for v in shares[0])
              + " | pay 4: " + " ".join(f"{v:4.2f}" for v in shares[2]))
        for t in range(cd.N_ROUNDS):
            top = i + height / 2
            for a, sh in zip((0, 2, 4), shares[:, t]):
                if sh > 0:
                    ax_b.add_patch(Rectangle((t + 1 - 0.43, top - height * sh), 0.86, height * sh,
                                             fc=cs.PAY_COLOURS[a], ec="none", zorder=2))
                top -= height * sh
    key_x = 1 - 0.43
    for a in (0, 2, 4):                          # key in the empty reference row
        ax_b.add_patch(Rectangle((key_x, -0.22), 0.55, 0.44, fc=cs.PAY_COLOURS[a], ec="none", zorder=2))
        ax_b.text(key_x + 0.75, 0, f"Pay {a}", ha="left", va="center", fontsize=cs.SIZE_SMALL,
                  color=cs.INK)
        key_x += 3.1
    ax_b.set_xlim(0.45, cd.N_ROUNDS + 0.55)
    ax_b.set_xticks(range(1, cd.N_ROUNDS + 1))
    ax_b.set_xlabel("Round")
    cs.panel_title(ax_b, "b", "Moves by round")

    # ---- c: payoff kept and lost, as shares of the attainable payoff
    base_u["opt"] = cd.opt_payoff(base_u.p)
    loss = base_u.opt - base_u.exp_pay
    reached = base_u.reached.values == 1
    below = base_u.p.values < cd.PSTAR
    base_u["A"] = np.where(reached, (base_u.G.values - cd.TARGET) / cd.N_PLAYERS, 0.0)
    base_u["B"] = (np.where(below & reached, base_u.opt.values - cd.FAIR_TOTAL, 0.0)
                   + np.where(below & ~reached, loss.values, 0.0))
    base_u["C"] = np.where(~below & ~reached, loss.values, 0.0)
    if not np.allclose(base_u.A + base_u.B + base_u.C, loss):
        raise RuntimeError("panel c: loss parts do not add up")
    print("\nFigure panel c: share of attainable payoff kept | lost below p*, past 120, missed")
    for i, m in enumerate(cs.MODEL_ORDER, start=1):
        d = base_u[base_u.model == m]
        opt = d.opt.sum()
        st = cs.model(m)
        kept = d.exp_pay.sum() / opt
        ax_c.barh(i, 100 * kept, height=0.62, color=st.colour, lw=0, zorder=2)
        left, parts = kept, []
        for key, _, hatch in LOSS_PARTS:
            w = d[key].sum() / opt
            parts.append(w)
            if w > 1e-9:
                ax_c.barh(i, 100 * w, left=100 * left, height=0.62, facecolor=st.tint,
                          edgecolor=st.colour, hatch=hatch, lw=0.6, zorder=2)
            left += w
        if not np.isclose(left, 1.0):
            raise RuntimeError(f"panel c: {m} parts sum to {left}")
        print(f"  {m:10s} kept {100 * kept:5.1f}% | " + " ".join(f"{100 * w:5.1f}%" for w in parts))
        inside = kept > 0.3
        ax_c.text(100 * kept + (-1.5 if inside else 1.5), i, f"{100 * kept:.0f}",
                  ha="right" if inside else "left", va="center", fontsize=cs.SIZE_SMALL,
                  color=cs.cell_ink(st.colour) if inside else cs.INK, zorder=5,
                  bbox=None if inside else dict(fc=cs.WHITE, ec="none", pad=0.4, alpha=0.85))
    key_x = 0.0
    fig.canvas.draw()
    for _, label, hatch in LOSS_PARTS:            # key in the empty reference row
        ax_c.add_patch(Rectangle((key_x, -0.22), 9, 0.44, facecolor=cs.WHITE, edgecolor=cs.MUTED,
                                 hatch=hatch, lw=0.6, zorder=2, clip_on=False))
        t = ax_c.text(key_x + 12, 0, label, ha="left", va="center", fontsize=cs.SIZE_SMALL,
                      color=cs.INK)
        box = t.get_window_extent(renderer=fig.canvas.get_renderer())
        key_x = ax_c.transData.inverted().transform((box.x1, box.y0))[0] + 6
    ax_c.set_xlim(0, 100)
    ax_c.set_xticks([0, 50, 100])
    ax_c.set_xlabel("Share of best payoff (%)")
    cs.panel_title(ax_c, "c", "Payoff kept and lost")

    cs.style_matrix_axes(ax_a)
    cs.row_labels(ax_a, rows)
    for ax in (ax_a, ax_b, ax_c):
        ax.set_ylim(*ylim)
    for ax in (ax_b, ax_c):
        ax.set_yticks([])
        ax.grid(False)
        ax.spines["left"].set_visible(False)
    ax_b.tick_params(axis="x", length=0)
    out = cs.save(fig, cd.FIGURES / "fig_selfplay", width="full")
    print(f"wrote {out}")


# ------------------------------------------------------------------ main
def main():
    games, units, seats = load()
    M = cd.Macros("selfplay.py")
    e7_analytic_check()

    # ---------------------------------------------------------------- counts
    n_exp = games.groupby("exp").size()
    print("\nGames per experiment:\n" + n_exp.to_string())
    if (games.groupby(["exp", "folder_model"]).rep.nunique() != 10).any():
        raise RuntimeError("a folder does not hold exactly ten repetitions")
    scripted = sum(int(n_exp[e]) for e in cd.SCRIPTED.values())
    llm_seats = len(seats)
    # sanity: every seat outside E3a is an LLM, E3a has exactly one LLM seat
    expect_seats = 6 * (len(games) - scripted) + scripted
    if llm_seats != expect_seats:
        raise RuntimeError(f"LLM seat count {llm_seats} != expected {expect_seats}")
    M.add("CntGames", thousands(len(games)))
    M.add("CntGamesBaseline", thousands(n_exp[BASE]))
    M.add("CntGamesNoCue", thousands(n_exp["exp_nohint"]))
    M.add("CntGamesProbe", thousands(n_exp["exp_evprobe"]))
    M.add("CntGamesScripted", thousands(scripted))
    M.add("CntGamesMixed", thousands(n_exp["exp_mixed"]))
    M.add("CntGamesPara", thousands(n_exp["exp_para1"] + n_exp["exp_para2"]))
    M.add("CntGamesTempZero", thousands(n_exp["exp_baseline_temp0"]))
    M.add("CntGamesNeutral", thousands(n_exp["exp_neutral"]))
    M.add("CntGamesWording", thousands(n_exp["exp_wording"]))
    M.add("CntDecisions", thousands(llm_seats * cd.N_ROUNDS))
    M.add("CntParseFail", str(int(games.n_parse.sum())))
    M.add("CntReps", str(int(games.rep.nunique())))

    # ---------------------------------------------------------------- lottery
    base_g = games[games.exp == BASE].copy()
    base_u = units[units.exp == BASE].copy()
    base_s = seats[seats.exp == BASE].copy()
    draws = cd.lottery_draws()
    missed = base_g[base_g.reached == 0]
    # Printed as an upper bound ("all ten draws lie below X"), so round UP.
    upper = math.ceil(max(draws) * 100) / 100
    if not all(u < upper for u in draws):
        raise RuntimeError("LotMaxDraw must be a strict upper bound on every draw")
    M.add("LotMaxDraw", f"{upper:.2f}")
    M.add("LotRealCat", str(int(base_g.catastrophe.sum())))
    M.add("LotExpCat", str(int(Decimal(repr(float(missed.p.sum()))).quantize(
        Decimal(1), rounding=ROUND_HALF_UP))))
    print(f"\nLottery draws {[round(u, 3) for u in draws]}; baseline misses {len(missed)}, "
          f"realised catastrophes {int(base_g.catastrophe.sum())}, expected {missed.p.sum():.2f}")

    # ---------------------------------------------------------------- model table
    base_u["opt"] = cd.opt_payoff(base_u.p)
    base_u["loss"] = base_u.opt - base_u.exp_pay
    reached = base_u.reached.values == 1
    below = base_u.p.values < cd.PSTAR
    A = np.where(reached, (base_u.G.values - cd.TARGET) / cd.N_PLAYERS, 0.0)
    B = np.where(below & reached, base_u.opt.values - cd.FAIR_TOTAL, 0.0) \
        + np.where(below & ~reached, base_u.loss.values, 0.0)
    C = np.where(~below & ~reached, base_u.loss.values, 0.0)
    if not np.allclose(A + B + C, base_u.loss.values):
        raise RuntimeError("loss decomposition does not add up")
    if (A < -1e-9).any() or (B < -1e-9).any() or (C < -1e-9).any():
        raise RuntimeError("negative loss component")
    base_u["A"], base_u["B"], base_u["C"] = A, B, C
    labels = {"A": "overshoot", "B": "below $p^*$", "C": "last round"}
    expected_main = {"Haiku": "B", "Flash-Lite": "B", "Luna": "B", "Qwen": "C", "Grok": "A"}

    print("\nModel table (exp_baseline, 110 games per model)")
    print("  loss decomposition, share of each model's expected loss: "
          "A overshoot | B paying below p* | C missing at p>=p*")
    rows = []
    loss_pct = {}
    for m in MODELS:
        d = base_u[base_u.model == m]
        s = base_s[base_s.model == m]
        t = d.loss.sum()
        shares = {k: d[k].sum() / t for k in "ABC"}
        top = max(shares, key=shares.get)
        if top != expected_main[m]:
            raise RuntimeError(f"{m}: computed main loss {top} ({labels[top]}) disagrees with the "
                               f"label {expected_main[m]} ({labels[expected_main[m]]}); shares {shares}")
        lost = 100.0 * (1.0 - d.exp_pay.mean() / d.opt.mean())
        loss_pct[m] = lost
        lost_ci = strat_boot_ci(d.exp_pay, d.p, stat="ratio", denom=d.opt)
        own0 = d[d.p == 0].own.mean()
        exact = s.traj.map(lambda tr: all(a == 2 for a in tr)).mean()
        print(f"  {m:10s} A {100 * shares['A']:5.1f}%  B {100 * shares['B']:5.1f}%  "
              f"C {100 * shares['C']:5.1f}%  -> {labels[top]:12s} | loss/seat {d.loss.mean():5.2f} | "
              f"pays@0 {own0:5.2f} exact2 {100 * exact:5.1f}% target {100 * d.reached.mean():5.1f}% "
              f"payoff {d.exp_pay.mean():5.2f} lost {lost:5.1f}% [{lost_ci[0]:.1f}, {lost_ci[1]:.1f}]")
        rows.append((cd.show(m), rnd(own0, 1), pct(exact), pct(d.reached.mean()), rnd(d.exp_pay.mean(), 1),
                     rnd(lost, 0), labels[top]))
    tot = base_u.loss.sum()
    print(f"  panel shares: A {100 * base_u.A.sum() / tot:.1f}%  B {100 * base_u.B.sum() / tot:.1f}%  "
          f"C {100 * base_u.C.sum() / tot:.1f}%")

    tab = [
        "% Generated by paper/AAMAS/analysis/selfplay.py. Do not edit by hand.",
        r"\begin{tabular}{@{}l@{\hspace{3pt}}r@{\hspace{3pt}}r@{\hspace{3pt}}r"
        r"@{\hspace{3pt}}r@{\hspace{3pt}}r@{\hspace{3pt}}l@{}}",
        r"\toprule",
        r" & Pays at & Exact & Target & Payoff & Lost & Main \\",
        r"Model & $p{=}0$ & split (\%) & (\%) & & (\%) & loss \\",
        r"\midrule",
    ]
    tab += [" & ".join(r) + r" \\" for r in rows]
    tab += [r"\bottomrule", r"\end{tabular}"]
    (cd.TABLES / "tab_models.tex").write_text("\n".join(tab) + "\n", encoding="utf-8")

    # ---------------------------------------------------------------- grid macros
    zero = base_s[base_s.p == 0]
    M.add("GridZeroSeats", str(len(zero)))
    M.add("GridZeroPaying", str(int((zero.own > 0).sum())))
    M.add("GridZeroPayingPct", pct((zero.own > 0).mean()))
    zero_means = base_u[base_u.p == 0].groupby("model").own.mean()
    M.add("GridZeroModelsPaying", cd.word(int((zero_means > 10).sum())))
    M.add("GridZeroModelsPayingCap", cd.word(int((zero_means > 10).sum()), cap=True))
    print("\nMean seat total at p=0:", zero_means.round(2).to_dict(),
          f"| paying seats {int((zero.own > 0).sum())}/{len(zero)}")
    panel_lost = 100.0 * (1.0 - base_u.exp_pay.mean() / base_u.opt.mean())
    panel_ci = strat_boot_ci(base_u.exp_pay, base_u.p, stat="ratio", denom=base_u.opt)
    print(f"Panel lost {panel_lost:.2f}% [{panel_ci[0]:.1f}, {panel_ci[1]:.1f}]")
    M.add("GridLossPanelPct", rnd(panel_lost, 0))
    M.add("GridGrokLossPct", rnd(loss_pct["Grok"], 0))
    M.add("GridFlashLossPct", rnd(loss_pct["Flash-Lite"], 0))
    M.add("GridQwenLossPct", rnd(loss_pct["Qwen"], 0))

    bg = {m: base_g[base_g.models.map(lambda t, m=m: t == (m,))] for m in MODELS}
    q = bg["Qwen"]
    Xq = np.stack(q.strat.to_list())                            # games x 6 x 10
    M.add("GridQwenReach", str(int(q.reached.sum())))
    M.add("GridQwenLastZeroPct", pct((Xq[:, :, 9] == 0).mean()))
    M.add("GridQwenRoundsOneNinePct", pct((Xq[:, :, :9] == 2).mean()))
    Xcf = Xq.copy()
    Xcf[:, :, 9] = Xcf[:, :, 8]
    cf_reach = (Xcf.sum(axis=(1, 2)) >= cd.TARGET).mean()
    M.add("GridQwenFixReachPct", pct(cf_reach))
    print(f"Qwen: reach {int(q.reached.sum())}/{len(q)} at p={q[q.reached == 1].p.tolist()}; "
          f"round-10 zero {100 * (Xq[:, :, 9] == 0).mean():.1f}% of {Xq[:, :, 9].size} seats; rounds 1-9 "
          f"equal to 2 {100 * (Xq[:, :, :9] == 2).mean():.1f}%; repeat-round-9 counterfactual "
          f"target {100 * cf_reach:.1f}%")

    gk = bg["Grok"]
    Xg = np.stack(gk.strat.to_list())
    pot = np.cumsum(Xg.sum(1), axis=1)                          # pot after round t
    pot_start = np.concatenate([np.zeros((len(gk), 1)), pot[:, :-1]], axis=1)
    waste = (Xg.sum(1) * (pot_start >= cd.TARGET)).sum(1) / cd.N_PLAYERS
    secured = np.array([np.argmax(r >= cd.TARGET) + 1 for r in pot[pot[:, -1] >= cd.TARGET]])
    M.add("GridGrokWaste", rnd(waste.mean(), 1))
    M.add("GridGrokSecuredRound", rnd(secured.mean(), 1))
    print(f"Grok: reach {int(gk.reached.sum())}/{len(gk)}; units per seat after the pot reached 120 "
          f"{waste.mean():.2f} (games with any {int((waste > 0).sum())}); secured round mean "
          f"{secured.mean():.2f} dist {dict(zip(*np.unique(secured, return_counts=True)))}")

    hk = bg["Haiku"]
    Xh = np.stack(hk.strat.to_list())
    p9 = Xh.sum(1)[:, :9].sum(1)
    z10 = Xh[:, :, 9] == 0
    sec9, piv9 = p9 >= cd.TARGET, (p9 >= 96) & (p9 < cd.TARGET)
    M.add("GridHaikuStopPct", pct(z10[sec9].mean()))
    M.add("GridHaikuStopOtherPct", pct(z10[piv9].mean()))
    pos_h = hk.p.values > 0
    print(f"Haiku round-10 zero share: pot9>=120 {100 * z10[sec9].mean():.1f}% ({int(sec9.sum())} games); "
          f"96<=pot9<120 {100 * z10[piv9].mean():.1f}% ({int(piv9.sum())} games); "
          f"p>0 only: {100 * z10[sec9 & pos_h].mean():.1f}% / {100 * z10[piv9 & pos_h].mean():.1f}%")

    fl = base_s[base_s.model == "Flash-Lite"]
    M.add("GridFlashExactPct", pct(fl.traj.map(lambda tr: all(a == 2 for a in tr)).mean()))

    steps = {}
    for m in MODELS:
        d = base_u[base_u.model == m]
        steps[m] = d[d.p >= 0.5].own.mean() - d[(d.p > 0) & (d.p < 0.5)].own.mean()
    print("Step own(p>=.5) - own(0<p<.5):", {k: round(v, 2) for k, v in steps.items()})
    M.add("GridStepGrok", rnd(steps["Grok"], 1))
    M.add("GridStepMaxOther", rnd(max(abs(v) for k, v in steps.items() if k != "Grok"), 1))

    pos = base_g[base_g.p > 0]
    miss = pos[pos.reached == 0]
    on_pace = miss.pot.map(lambda pt: all(pt[t - 1] >= 12 * t for t in range(1, 10)))
    M.add("GridMissOnPace", str(int(on_pace.sum())))
    M.add("GridMissTotal", str(len(miss)))
    luna_miss = miss[miss.models.map(lambda t: t[0]) == "Luna"]
    luna_on_pace = on_pace[luna_miss.index]
    if not luna_on_pace.all():
        raise RuntimeError("a Luna miss at p>0 was behind the fair pace; revisit the text")
    M.add("GridLunaMiss", str(len(luna_miss)))
    M.add("GridLunaGames", str(int((pos.models.map(lambda t: t[0]) == "Luna").sum())))
    # Reference for the Payoff column of Table 2: mean attainable payoff over the grid.
    M.add("GridOptMean", rnd(float(np.mean([float(cd.opt_payoff(p)) for p in sorted(base_g.p.unique())])), 1))
    # Closed form: a CRRA player u(x)=x^(1-g)/(1-g) prefers a certain fair-share payoff of 20
    # to keeping 40 with probability 1-p only if g >= 1 - log2(1/(1-p)). Printed at p = 0.1.
    crra_low = 1.0 - math.log2(1.0 / (1.0 - 0.1))
    M.add("GridCrraLow", f"{math.floor(crra_low * 100) / 100:.2f}")
    print(f"CRRA coefficient needed to prefer a certain 20 at p=0.1: {crra_low:.3f}")
    print(f"Misses at p>0: {len(miss)}; on fair pace through round 9: {int(on_pace.sum())}; by model "
          f"{miss.models.map(lambda t: t[0]).value_counts().to_dict()}")

    # ---------------------------------------------------------------- no cue
    print("\nNo cue (exp_nohint) vs rerun (exp_evprobe), p in {.1,.5,.9}")
    arm_u = {e: units[(units.exp == e) & units.p.isin([0.1, 0.5, 0.9])] for e in ("exp_evprobe", "exp_nohint")}
    arm_s = {e: seats[(seats.exp == e) & seats.p.isin([0.1, 0.5, 0.9])] for e in arm_u}
    for e, d in arm_u.items():
        if len(d) != 150 or (d.groupby("model").size() != 30).any():
            raise RuntimeError(f"{e}: expected 30 games per model")
    ev, nh = arm_u["exp_evprobe"], arm_u["exp_nohint"]
    for m in MODELS:
        a, b = ev[ev.model == m], nh[nh.model == m]
        line = f"  {m:10s}"
        for col in ("reached", "exp_pay", "own", "exact2", "exact4"):
            diff, pv = strat_perm(a[col], a.p, b[col], b.p)
            line += f" | {col} {a[col].mean():6.2f}->{b[col].mean():6.2f} (P={pv:.4f})"
        print(line)
    q_ev, q_nh = ev[ev.model == "Qwen"], nh[nh.model == "Qwen"]
    M.add("NoCueQwenReachBase", pct(q_ev.reached.mean()))
    M.add("NoCueQwenReach", pct(q_nh.reached.mean()))
    M.add("NoCueQwenPayBase", rnd(q_ev.exp_pay.mean(), 1))
    M.add("NoCueQwenPay", rnd(q_nh.exp_pay.mean(), 1))
    for p in (0.1, 0.5, 0.9):
        print(f"  Qwen p={p}: reach {q_ev[q_ev.p == p].reached.mean():.2f}->{q_nh[q_nh.p == p].reached.mean():.2f}"
              f" pay {q_ev[q_ev.p == p].exp_pay.mean():.2f}->{q_nh[q_nh.p == p].exp_pay.mean():.2f}"
              f" own {q_ev[q_ev.p == p].own.mean():.2f}->{q_nh[q_nh.p == p].own.mean():.2f}")
    s_nh, s_ev = arm_s["exp_nohint"], arm_s["exp_evprobe"]

    def seat_share(s, m, value):
        return s[s.model == m].traj.map(lambda tr: all(a == value for a in tr)).mean()

    M.add("NoCueGrokAllFourPct", pct(seat_share(s_nh, "Grok", 4)))
    M.add("NoCueFlashExactPct", pct(seat_share(s_nh, "Flash-Lite", 2)))
    M.add("NoCueLunaExactBasePct", pct(seat_share(s_ev, "Luna", 2)))
    M.add("NoCueLunaExactPct", pct(seat_share(s_nh, "Luna", 2)))
    M.add("NoCuePanelReachBase", pct(ev.reached.mean()))
    M.add("NoCuePanelReach", pct(nh.reached.mean()))
    M.add("NoCuePanelPayBase", rnd(ev.exp_pay.mean(), 1))
    M.add("NoCuePanelPay", rnd(nh.exp_pay.mean(), 1))
    strata_ev = ev.model + "|" + ev.p.astype(str)
    strata_nh = nh.model + "|" + nh.p.astype(str)
    dpay, ppay = strat_perm(ev.exp_pay, strata_ev, nh.exp_pay, strata_nh)
    dci = strat_boot_diff_ci(ev.exp_pay, strata_ev, nh.exp_pay, strata_nh)
    print(f"  panel: reach {100 * ev.reached.mean():.1f}% -> {100 * nh.reached.mean():.1f}%; expected pay "
          f"{ev.exp_pay.mean():.2f} -> {nh.exp_pay.mean():.2f} (diff {dpay:+.2f} [{dci[0]:+.2f}, {dci[1]:+.2f}], "
          f"P={ppay:.4f}, stratified by model x p)")
    print(f"  seats: Grok all-4 {100 * seat_share(s_ev, 'Grok', 4):.1f}% -> {100 * seat_share(s_nh, 'Grok', 4):.1f}%; "
          f"Flash exact-2 {100 * seat_share(s_ev, 'Flash-Lite', 2):.1f}% -> "
          f"{100 * seat_share(s_nh, 'Flash-Lite', 2):.1f}%; Luna exact-2 "
          f"{100 * seat_share(s_ev, 'Luna', 2):.1f}% -> {100 * seat_share(s_nh, 'Luna', 2):.1f}%")

    # ---------------------------------------------------------------- robustness
    arms = [("Base", BASE), ("Rerun", "exp_evprobe"), ("No hint", "exp_nohint"),
            ("Para.\\,1", "exp_para1"), ("Para.\\,2", "exp_para2"), ("Temp.\\,0", "exp_baseline_temp0"),
            ("Wording", "exp_wording"), ("Neutral", "exp_neutral")]
    ru = {e: units[(units.exp == e) & units.p.isin(ENDPOINTS)] for _, e in arms}
    rg = {e: games[(games.exp == e) & games.p.isin(ENDPOINTS)] for _, e in arms}
    for e, d in ru.items():
        cnt = d.groupby(["model", "p"]).size()
        if len(cnt) != 10 or (cnt != 10).any():
            raise RuntimeError(f"{e}: expected 10 games per model per endpoint risk")
    print("\nRobustness: mean seat total pooled over p in {.1,.9} (20 games per cell); "
          "shift vs Base, stratified permutation P, stratified bootstrap 95% CI")
    rob_rows, flat_shifts = [], []
    for m in MODELS:
        b = ru[BASE][ru[BASE].model == m]
        cells = []
        for name, e in arms:
            d = ru[e][ru[e].model == m]
            val = d.own.mean()
            bold = False
            if e != BASE:
                diff, pv = strat_perm(b.own, b.p, d.own, d.p)
                lo, hi = strat_boot_diff_ci(b.own, b.p, d.own, d.p)
                p_unstrat = cd.perm_test(b.own, d.own, offset=next_offset())
                bold = pv < 0.01 and abs(diff) >= 2.0
                print(f"  {m:10s} {name.replace(chr(92) + ',', ' '):8s} {b.own.mean():5.2f} -> {val:5.2f} "
                      f"shift {diff:+6.2f} [{lo:+.2f}, {hi:+.2f}] P={pv:.4f} (unstratified {p_unstrat:.4f})"
                      f"{'  BOLD' if bold else ''}")
                if m != "Grok" and e not in ("exp_nohint", "exp_neutral", "exp_wording"):
                    flat_shifts.append((abs(diff), m, e))
            cells.append(f"\\textbf{{{rnd(val, 1)}}}" if bold else rnd(val, 1))
        rob_rows.append(cells)
    # Conditions as rows, models as columns: with eight conditions and the models' full
    # family names, the model-per-row layout ran 52 pt past the column.
    family = [cd.LINES[m][0] for m in MODELS]
    member = [cd.LINES[m][1] for m in MODELS]
    tab = [
        "% Generated by paper/AAMAS/analysis/selfplay.py. Do not edit by hand.",
        r"\begin{tabular}{@{}l" + "r" * len(MODELS) + "@{}}",
        r"\toprule",
        " & " + " & ".join(family) + r" \\",
        "Condition & " + " & ".join(member) + r" \\",
        r"\midrule",
    ]
    for j, (name, _) in enumerate(arms):
        tab.append(name + " & " + " & ".join(row[j] for row in rob_rows) + r" \\")
    tab += [r"\bottomrule", r"\end{tabular}"]
    (cd.TABLES / "tab_robust.tex").write_text("\n".join(tab) + "\n", encoding="utf-8")

    gb = lambda e, m: ru[e][ru[e].model == m]  # noqa: E731
    M.add("RobGrokBase", rnd(gb(BASE, "Grok").own.mean(), 1))
    M.add("RobGrokParaTwo", rnd(gb("exp_para2", "Grok").own.mean(), 1))
    M.add("RobGrokParaTwoExactGames", str(int((gb("exp_para2", "Grok").exact2 == 1).sum())))
    worst = max(flat_shifts)
    print(f"  largest |shift| among the four flat models (arms other than No cue): {worst[0]:.2f} "
          f"({worst[1]}, {worst[2]})")
    M.add("RobFlatMaxShift", rnd(worst[0], 1))

    def distinct(e):
        g = rg[e]
        per_cell = g.groupby(["folder_model", "p"]).strat.apply(
            lambda col: len({tuple(map(tuple, s.astype(int))) for s in col}))
        per_cell_sorted = g.groupby(["folder_model", "p"]).strat.apply(
            lambda col: len({tuple(sorted(map(tuple, s.astype(int)))) for s in col}))
        return per_cell, per_cell_sorted

    t0, t0_sorted = distinct("exp_baseline_temp0")
    b0, b0_sorted = distinct(BASE)
    print(f"  distinct 6x10 trajectories per cell (of 10): temp0 mean {t0.mean():.2f} "
          f"(seat-order-free {t0_sorted.mean():.2f}), values {sorted(t0.tolist())}; baseline mean "
          f"{b0.mean():.2f} (seat-order-free {b0_sorted.mean():.2f}), values {sorted(b0.tolist())}")
    M.add("RobTempZeroDistinct", rnd(t0.mean(), 1))
    M.add("RobTempZeroBaseDistinct", rnd(b0.mean(), 1))

    for macro, e in (("RobGrokRiskBase", BASE), ("RobGrokRiskParaTwo", "exp_para2"),
                     ("RobGrokRiskRerun", "exp_evprobe")):
        d = gb(e, "Grok")
        delta = d[d.p == 0.9].own.mean() - d[d.p == 0.1].own.mean()
        _, pv = strat_perm(d[d.p == 0.1].own, np.zeros(10), d[d.p == 0.9].own, np.zeros(10))
        print(f"  Grok risk delta p=.9 - p=.1 in {e}: {delta:+.2f} (P={pv:.4f})")
        M.add(macro, rnd(delta, 1))

    # Qwen's last-round zero depends on the wording: share of Qwen seats paying 0 in round 10,
    # at the two endpoint risks, per condition.
    for macro, e in (("RobQwenLastZeroBase", BASE), ("RobQwenLastZeroNoHint", "exp_nohint"),
                     ("RobQwenLastZeroParaOne", "exp_para1"), ("RobQwenLastZeroParaTwo", "exp_para2"),
                     ("RobQwenLastZeroNeutral", "exp_neutral"), ("RobQwenLastZeroWording", "exp_wording")):
        s = seats[(seats.exp == e) & (seats.model == "Qwen") & seats.p.isin(ENDPOINTS)]
        if len(s) != 120:
            raise RuntimeError(f"{e}: expected 120 Qwen seats at the endpoints, found {len(s)}")
        share = s.traj.map(lambda tr: tr[-1] == 0).mean()
        print(f"  Qwen round-10 zero share in {e} (p=.1,.9): {100 * share:.1f}%")
        M.add(macro, pct(share))

    # ---------------------------------------------------------------- framing arms
    # Two demand-effect controls on the same three risks. Both replace "climate",
    # "must", "disaster" and the game's name; "neutral" also states that only the
    # player's own cash matters, "wording" does not. Their decisive cell is p=0, where
    # paying is dominated whatever the player believes.
    #   baseline -> wording : effect of the words
    #   wording  -> neutral : effect of stating the objective
    arm_units = {}
    for exp, prefix, title in (("exp_neutral", "Neu", "neutral prompt"),
                               ("exp_wording", "Wor", "neutral wording, no objective")):
        au = units[units.exp == exp]
        a_s = seats[seats.exp == exp]
        cnt = au.groupby(["model", "p"]).size()
        if len(cnt) != 15 or (cnt != 10).any():
            raise RuntimeError(f"{exp}: expected 10 games per model at p in {{0,.1,.9}}, got {cnt.to_dict()}")
        arm_units[exp] = au
        nz = a_s[a_s.p == 0]
        nz_means = au[au.p == 0].groupby("model").own.mean()
        M.add(prefix + "ZeroSeats", str(len(nz)))
        M.add(prefix + "ZeroPaying", str(int((nz.own > 0).sum())))
        M.add(prefix + "ZeroModelsPaying", cd.word(int((nz_means > 10).sum())))
        M.add(prefix + "ZeroModelsPayingCap", cd.word(int((nz_means > 10).sum()), cap=True))
        print(f"\n{title} ({exp}): mean seat total, grid -> arm, by p")
        for m in MODELS:
            line = f"  {m:10s}"
            for pp in (0.0, 0.1, 0.9):
                b = base_u[(base_u.model == m) & (base_u.p == pp)]
                d = au[(au.model == m) & (au.p == pp)]
                pv = cd.perm_test(b.own, d.own, offset=next_offset())
                line += (f" | p={pp:g}: {b.own.mean():5.2f} -> {d.own.mean():5.2f} (P={pv:.4f}; "
                         f"reach {100 * d.reached.mean():3.0f}%)")
            d1 = au[(au.model == m) & (au.p == 0.1)].own
            d9 = au[(au.model == m) & (au.p == 0.9)].own
            pr = cd.perm_test(d1, d9, offset=next_offset())
            s0 = nz[nz.model == m]
            line += (f" | step .9-.1 {d9.mean() - d1.mean():+5.2f} (P={pr:.4f})"
                     f" | p=0 paying seats {int((s0.own > 0).sum())}/{len(s0)}")
            print(line)
            key = m.replace("-", "")
            M.add(prefix + "Zero" + key, rnd(nz_means[m], 1))
            M.add(prefix + "Step" + key, rnd(d9.mean() - d1.mean(), 1))
            M.add(prefix + "Low" + key, rnd(d1.mean(), 1))
            M.add(prefix + "High" + key, rnd(d9.mean(), 1))
            M.add(prefix + "Reach" + key, str(int(au[au.model == m].reached.sum())))
            M.add(prefix + "Games" + key, str(int((au.model == m).sum())))
        print(f"  p=0 paying seats {int((nz.own > 0).sum())}/{len(nz)}; models with mean > 10: "
              f"{int((nz_means > 10).sum())}")
    for m in MODELS:
        key = m.replace("-", "")
        M.add("GridZero" + key, rnd(base_u[(base_u.model == m) & (base_u.p == 0)].own.mean(), 1))
    print("\nObjective effect, wording -> neutral (same words, objective added):")
    for m in MODELS:
        line = f"  {m:10s}"
        for pp in (0.0, 0.1, 0.9):
            w = arm_units["exp_wording"]; n = arm_units["exp_neutral"]
            w = w[(w.model == m) & (w.p == pp)].own; n = n[(n.model == m) & (n.p == pp)].own
            pv = cd.perm_test(w, n, offset=next_offset())
            line += f" | p={pp:g}: {w.mean():5.2f} -> {n.mean():5.2f} (P={pv:.4f})"
        print(line)

    path = M.write("num_selfplay.tex")
    print(f"\nwrote {path}")
    print("\nMacros:")
    for k, v in M.items.items():
        print(f"  {k:28s} = {v}")

    # Numbers and tables above never depend on the figure; CRSD_SKIP_FIGURES=1 rewrites them
    # without touching figures/ (used while the figures are being redesigned separately).
    if os.environ.get("CRSD_SKIP_FIGURES") != "1":
        figure(units, games)


if __name__ == "__main__":
    main()
