"""Empirical game-theoretic analysis: the five models as strategies, and what selection picks.

Run from the repository root:
    python paper/AAMAS/analysis/selection.py

Reads results/exp_mixed, results/exp_baseline and results/exp_evprobe through crsd_data
(read-only; never Legacy_Results/, never writes under results/). Writes
    paper/AAMAS/figures/fig_selection.pdf (+ .png preview)
    paper/AAMAS/tables/num_selection.tex

PAYOFFS ARE EXPECTED PAYOFFS over the catastrophe lottery:
    40 - own total            if the table reached 120
    (1 - p) * (40 - own total) if it missed
At one table every seat shares the pool and the lottery, so for any two seats i, j
    E_i - E_j = (c_j - c_i) * (1 if reached else 1 - p):
the seat that pays less always earns more, at every table. The script checks this against
the engine's own private accounts (agent{i}_scores), not against the formula.

PAYOFF FUNCTIONS. P[p, X, Y, k] = mean (over games) of the mean expected payoff of the X
seats at a table with k X seats and 6 - k Y seats, k = 1..6. k = 1..5 come from exp_mixed
(10 games per cell); k = 6 is X self-play, pooled from exp_baseline and exp_evprobe at the
same p (identical game condition, 20 games). A baseline-only sensitivity is printed.

SELECTION. Pairwise-comparison (Fermi) process in the small-mutation limit (alpha-rank
with a single population): a single mutant X in a resident Y population fixes with
    rho = 1 / (1 + sum_{j=1}^{N-1} prod_{i=1}^{j} exp(-beta (f_X(i) - f_Y(i)))),
and the stationary distribution of the embedded chain over the five monomorphic states is
the "stationary mass". beta = 1 in payoff units (the endowment is 40).
  (i)  WITHIN-TABLE. The population is one table of N = 6. With i X seats, f_X(i) =
       P[X, Y, i] and f_Y(i) = P[Y, X, 6 - i]: a model is compared only with the
       tablemates it plays beside. Uses mixed k = 1..5 only.
  (ii) ACROSS-TABLE. Population of N = 30, tables of 6 drawn without replacement
       (hypergeometric), fitness = expected payoff averaged over the table compositions
       it can land in. Uses the self-play endpoints and the mixed tables.
       N = 60 and 120 and beta = 10 are printed as sensitivities.
Population outcomes weight each model's SELF-PLAY target rate and per-seat expected
payoff by its stationary mass. Uncertainty: 1000 game-level bootstrap replicates
(resample the games of every mixed cell and every self-play cell), reported as the share
of replicates in which the point-estimate winner is still top, and percentile 95% CIs.
"""
from __future__ import annotations

import itertools
import sys
from math import comb
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch
from scipy.special import logsumexp

sys.path.insert(0, str(Path(__file__).resolve().parent))
import crsd_data as cd      # noqa: E402
import crsd_style as cs     # noqa: E402

RISKS = (0.1, 0.5, 0.9)
M = cd.MODELS
K = len(M)
MI = {m: i for i, m in enumerate(M)}
SELF_EXPS = ("exp_baseline", "exp_evprobe")
BETA = 1.0
N_WITHIN = 6
N_ACROSS = 30
N_EXTRA = (60, 120)
BETA_EXTRA = 10.0
BETA_WEAK = 0.1
N_BOOT = 1000
N_SCAN = range(6, 121)
ALPHA_SIG = 0.05


def thousands(n: int) -> str:
    return f"{int(n):,}".replace(",", "{,}")


# ============================================================================ data
def load():
    games, units, _ = cd.build(("exp_mixed", "exp_baseline", "exp_evprobe"))
    games = games.assign(p=games.p.round(3))
    mg = games[games.exp == "exp_mixed"].copy()
    sg = games[games.exp.isin(SELF_EXPS) & games.p.isin(RISKS)].copy()
    if len(mg) != 1500:
        raise RuntimeError(f"exp_mixed holds {len(mg)} games")
    rows = []
    for g in mg.itertuples():
        names = [cd.SLUG.get(s) for s in g.llm]
        if None in names:
            raise ValueError(f"non-LLM seat in {g.gid}")
        a, b = sorted(set(names), key=M.index)
        ia = [i for i, n in enumerate(names) if n == a]
        ib = [i for i, n in enumerate(names) if n == b]
        c = g.strat.sum(axis=1)
        e = cd.expected_payoff(c, g.reached, g.p)
        rows.append(dict(gid=g.gid, p=g.p, rep=g.rep, A=a, B=b, kA=len(ia), reached=g.reached,
                         cA=c[ia].mean(), cB=c[ib].mean(), eA=e[ia].mean(), eB=e[ib].mean(),
                         names=tuple(names), strat=g.strat, G=g.G))
    mx = pd.DataFrame(rows)
    srows = []
    for g in sg.itertuples():
        names = {cd.SLUG.get(s) for s in g.llm}
        if len(names) != 1 or None in names:
            raise ValueError(f"self-play game {g.gid} holds {names}")
        srows.append(dict(gid=g.gid, exp=g.exp, p=g.p, model=names.pop(), reached=g.reached,
                          welfare=g.exp_welfare))
    sp = pd.DataFrame(srows)
    bal = sp.groupby(["model", "p"]).size()
    if len(bal) != 15 or set(bal) != {20}:
        raise RuntimeError(f"self-play endpoints unbalanced: {bal.to_dict()}")
    cells = mx.groupby(["p", "A", "B", "kA"]).size()
    if len(cells) != 150 or set(cells) != {10}:
        raise RuntimeError("mixed cells are not 150 x 10 games")
    return mx, sp


# ============================================================================ identity
def identity_check(mx):
    raw = cd._read_experiment("exp_mixed")
    raw["gid"] = [f"exp_mixed|{fm}|{float(p):g}|{int(r)}"
                  for fm, p, r in zip(raw.folder_model, raw.risk_probability, raw.rep)]
    raw = raw.set_index("gid")
    max_err, max_err_model = 0.0, 0.0
    for g in mx.itertuples():
        row = raw.loc[g.gid]
        left = np.array([cd._parse(row[f"agent{i}_scores"])[-1] for i in range(1, 7)], float)
        factor = 1.0 if g.reached else 1.0 - g.p
        e = factor * left                                  # engine's account, lottery averaged
        c = g.strat.sum(axis=1)                            # contributions from the moves
        for i, j in itertools.combinations(range(6), 2):
            max_err = max(max_err, abs((e[i] - e[j]) - (c[j] - c[i]) * factor))
        max_err_model = max(max_err_model, abs((g.eA - g.eB) - (g.cB - g.cA) * factor))
    sign_ok = int(sum(np.sign(round(ea - eb, 9)) == -np.sign(round(ca - cb, 9))
                      for ea, eb, ca, cb in zip(mx.eA, mx.eB, mx.cA, mx.cB)))
    ties = int(((mx.cA - mx.cB).abs() < 1e-9).sum())
    print(f"identity E_i - E_j = (c_j - c_i) x (1 or 1-p): max abs error over {len(mx)} games x 15 seat "
          f"pairs = {max_err:.2e} (engine private accounts); model-level {max_err_model:.2e}")
    print(f"  games where sign(payoff gap) = -sign(contribution gap): {sign_ok}/{len(mx)} "
          f"(of which equal contributions and equal payoffs: {ties})")
    if max_err >= 1e-12:
        raise RuntimeError(f"identity fails: max error {max_err}")
    return max_err, sign_ok


# ============================================================================ payoff tables
def cell_arrays(mx, sp):
    mixed = {}
    for (p, a, b, k), d in mx.groupby(["p", "A", "B", "kA"]):
        mixed[(RISKS.index(p), MI[a], MI[b], int(k))] = d[["eA", "eB"]].to_numpy(float)
    selfc = {}
    for (p, m), d in sp.groupby(["p", "model"]):
        selfc[(RISKS.index(p), MI[m])] = d[["welfare", "reached"]].to_numpy(float)
    return mixed, selfc


def tables(mixed, selfc, rng=None):
    """P[pi, x, y, k] (k = 1..6), self-play REACH[pi, x] and WEL[pi, x]; bootstrap if rng."""
    def rs(arr):
        return arr if rng is None else arr[rng.integers(0, len(arr), len(arr))]
    P = np.full((len(RISKS), K, K, 7), np.nan)
    REACH = np.full((len(RISKS), K), np.nan)
    WEL = np.full((len(RISKS), K), np.nan)
    for (pi, x), arr in selfc.items():
        m = rs(arr).mean(axis=0)
        P[pi, x, :, 6] = m[0]
        WEL[pi, x], REACH[pi, x] = m[0], m[1]
    for (pi, a, b, k), arr in mixed.items():
        m = rs(arr).mean(axis=0)
        P[pi, a, b, k] = m[0]
        P[pi, b, a, 6 - k] = m[1]
    return P, REACH, WEL


# ============================================================================ dynamics
def hyp(j, N, S, n):
    if j < 0 or j > n or j > S or n - j > N - S:
        return 0.0
    return comb(S, j) * comb(N - S, n - j) / comb(N, n)


_W = {}


def weights(N):
    """WX[i-1, k-1]: X focal with i X in the population sits at a table with k X seats.
    WY[i-1, j]: Y focal sits at a table with j X seats (and 6 - j Y seats)."""
    if N not in _W:
        wx, wy = np.zeros((N - 1, 6)), np.zeros((N - 1, 6))
        for idx, i in enumerate(range(1, N)):
            for k in range(1, 7):
                wx[idx, k - 1] = hyp(k - 1, N - 1, i - 1, 5)
            for j in range(6):
                wy[idx, j] = hyp(j, N - 1, i, 5)
        if not (np.allclose(wx.sum(1), 1) and np.allclose(wy.sum(1), 1)):
            raise RuntimeError(f"hypergeometric weights for N={N} do not sum to 1")
        _W[N] = (wx, wy)
    return _W[N]


def fitness(Pp, x, y, N):
    wx, wy = weights(N)
    return wx @ Pp[x, y, 1:7], wy @ Pp[y, x, 6 - np.arange(6)]


def fixation(fx, fy, beta):
    return float(np.exp(-logsumexp(np.r_[0.0, -beta * np.cumsum(fx - fy)])))


def rho_matrix(Pp, N, beta):
    """R[x, y] = fixation probability of one x mutant in a y population."""
    R = np.full((K, K), 1.0 / N)
    for x, y in itertools.permutations(range(K), 2):
        R[x, y] = fixation(*fitness(Pp, x, y, N), beta)
    return R


def rho_within(Pp, beta):
    """Explicit one-table version: i X seats and 6 - i Y seats at THE table, i = 1..5."""
    R = np.full((K, K), 1.0 / N_WITHIN)
    i = np.arange(1, N_WITHIN)
    for x, y in itertools.permutations(range(K), 2):
        R[x, y] = fixation(Pp[x, y, i], Pp[y, x, N_WITHIN - i], beta)
    return R


def stationary(R):
    C = np.zeros((K, K))
    for s, r in itertools.permutations(range(K), 2):
        C[s, r] = R[r, s] / (K - 1)
    C[np.diag_indices(K)] = 1 - C.sum(axis=1)
    w, v = np.linalg.eig(C.T)
    i = int(np.argmin(np.abs(w - 1)))
    pi = np.abs(np.real(v[:, i]))
    pi = pi / pi.sum()
    n_unit = int(np.sum(np.abs(w - 1) < 1e-9))
    return pi, n_unit


def outcome(Pp, reach, wel, rule, beta=BETA, N=N_ACROSS):
    R = rho_within(Pp, beta) if rule == "within" else rho_matrix(Pp, N, beta)
    pi, n_unit = stationary(R)
    return dict(pi=pi, reach=float(pi @ reach), pay=float(pi @ wel), top=int(np.argmax(pi)),
                n_unit=n_unit)


RULES = [("within", BETA, N_WITHIN), ("across", BETA, N_ACROSS)]
EXTRA = ([("within", BETA_EXTRA, N_WITHIN), ("across", BETA_EXTRA, N_ACROSS)]
         + [("across", b, n) for n in N_EXTRA for b in (BETA, BETA_EXTRA)])


def run_rules(mixed, selfc, label, n_boot=N_BOOT, offset=0, boot_extra=True):
    P, REACH, WEL = tables(mixed, selfc)
    for pi in range(len(RISKS)):
        if not np.allclose(rho_within(P[pi], BETA), rho_matrix(P[pi], N_WITHIN, BETA)):
            raise RuntimeError("within-table rule differs from the N = 6 hypergeometric process")
    specs = RULES + EXTRA
    point = {(r, b, n, pi): outcome(P[pi], REACH[pi], WEL[pi], r, b, n)
             for (r, b, n) in specs for pi in range(len(RISKS))}
    rng = cd.rng(offset)
    boot_keys = [key for key in point if boot_extra or key[:3] in RULES]
    boots = {key: [] for key in boot_keys}
    for _ in range(n_boot):
        Pb, Rb, Wb = tables(mixed, selfc, rng)
        for (r, b, n, pi) in boot_keys:
            boots[(r, b, n, pi)].append(outcome(Pb[pi], Rb[pi], Wb[pi], r, b, n))
    print(f"\n=== {label}: stationary mass, and the population's self-play target rate and "
          f"expected payoff per seat ({n_boot} bootstrap replicates)")
    for (r, b, n) in specs:
        for pi, p in enumerate(RISKS):
            o = point[(r, b, n, pi)]
            flag = "" if o["n_unit"] == 1 else f"  [{o['n_unit']} unit eigenvalues: chain reducible]"
            line = (f"  {r:6} N={n:<3d} beta={b:<4g} p={p:.1f}  "
                    + " ".join(f"{m}={v:.2f}" for m, v in zip(M, o["pi"])))
            if (r, b, n, pi) in boots:
                bs = boots[(r, b, n, pi)]
                share = np.mean([x["top"] == o["top"] for x in bs])
                rlo, rhi = np.percentile([x["reach"] for x in bs], [2.5, 97.5])
                wlo, whi = np.percentile([x["pay"] for x in bs], [2.5, 97.5])
                line += (f" | top {M[o['top']]} in {share:.0%} of reps | target {100 * o['reach']:.0f}% "
                         f"[{100 * rlo:.0f},{100 * rhi:.0f}] | payoff/seat {o['pay']:.2f} [{wlo:.2f},{whi:.2f}]")
            else:
                line += (f" | top {M[o['top']]} (point only) | target {100 * o['reach']:.0f}% "
                         f"| payoff/seat {o['pay']:.2f}")
            print(line + flag)
    for pi, p in enumerate(RISKS):
        print(f"  uniform over models p={p:.1f}: target {100 * REACH[pi].mean():.0f}%, "
              f"payoff/seat {WEL[pi].mean():.2f}; self-play target "
              + ", ".join(f"{m} {100 * v:.0f}%" for m, v in zip(M, REACH[pi])))
    return P, REACH, WEL, point, boots


# ============================================================================ table-level facts
def signflip_lower(d):
    """Exact one-sided sign-flip p value for mean(d) < 0 over all 2^n sign vectors."""
    d = np.asarray(d, float)
    signs = np.array(list(itertools.product((1.0, -1.0), repeat=len(d))))
    null = (signs * d).mean(axis=1)
    return float(np.mean(null <= d.mean() + 1e-12))


def table_facts(mx):
    print("\nsingle seat beside five Grok seats: mean expected payoff per seat (10 games per cell)")
    wins = 0
    for m in M:
        if m == "Grok":
            continue
        for p in RISKS:
            d = mx[(mx.p == p) & (((mx.A == m) & (mx.B == "Grok") & (mx.kA == 1))
                                  | ((mx.B == m) & (mx.A == "Grok") & (mx.kA == 5)))]
            if len(d) != 10:
                raise RuntimeError(f"{m} vs five Grok at p={p}: {len(d)} games")
            em = np.where(d.A == m, d.eA, d.eB).mean()
            eg = np.where(d.A == "Grok", d.eA, d.eB).mean()
            wins += int(em > eg)
            print(f"  p={p:.1f} {m:10} {em:5.2f} vs Grok {eg:5.2f}  -> {'single seat ahead' if em > eg else 'Grok ahead'}")
    print(f"  cells where the single seat earns more: {wins}/12")

    print(f"\nQwen vs its tablemates, every (pair, k, p) cell: exact 2^10 sign-flip test, one-sided "
          f"(Qwen below), alpha = {ALPHA_SIG}")
    below, above, n_cells, min_p = [], 0, 0, 1.0
    for (p, a, b, k), d in mx[(mx.A == "Qwen") | (mx.B == "Qwen")].groupby(["p", "A", "B", "kA"]):
        diff = np.where(d.A == "Qwen", d.eA - d.eB, d.eB - d.eA)
        if len(diff) != 10:
            raise RuntimeError("Qwen cell without 10 games")
        pv = signflip_lower(diff)
        pv_up = signflip_lower(-diff)
        n_cells += 1
        min_p = min(min_p, pv)
        above += int(pv_up < ALPHA_SIG)
        if pv < ALPHA_SIG:
            q_tot = np.where(d.A == "Qwen", d.cA, d.cB)
            o_tot = np.where(d.A == "Qwen", d.cB, d.cA)
            below.append(dict(p=p, A=a, B=b, kA=int(k), qwen_seats=int(k) if a == "Qwen" else 6 - int(k),
                              gap=float(diff.mean()), p_one_sided=pv, diffs=diff.round(2).tolist(),
                              qwen_total=float(q_tot.mean()), other_total=float(o_tot.mean()),
                              reached=int(d.reached.sum())))
    print(f"  cells {n_cells}; Qwen significantly below: {len(below)} (smallest one-sided p {min_p:.4f}); "
          f"significantly above: {above}")
    for c in below:
        other = c["B"] if c["A"] == "Qwen" else c["A"]
        print(f"  BEATEN: p={c['p']:.1f}, {c['qwen_seats']} Qwen seats beside {6 - c['qwen_seats']} {other} seats: "
              f"Qwen minus {other} expected payoff {c['gap']:+.2f}, exact one-sided p = {c['p_one_sided']:.4f}; "
              f"per-seat totals Qwen {c['qwen_total']:.2f} vs {other} {c['other_total']:.2f}; "
              f"target reached {c['reached']}/10; per-game gaps {c['diffs']}")
    return wins, below, n_cells, above


def switch_n(P, pi_idx, target="Flash-Lite", beta=BETA):
    tops = {N: M[int(np.argmax(stationary(rho_matrix(P[pi_idx], N, beta))[0]))] for N in N_SCAN}
    ok = [N for N in N_SCAN if all(tops[n] == target for n in N_SCAN if n >= N)]
    if not ok:
        raise RuntimeError(f"{target} never becomes the stable winner for N <= {max(N_SCAN)}")
    changes = [(N, tops[N]) for i, N in enumerate(N_SCAN) if i == 0 or tops[N] != tops[N - 1]]
    print(f"  across-table winner vs N at p={RISKS[pi_idx]}, beta={beta:g} (N = {min(N_SCAN)}..{max(N_SCAN)}): "
          + ", ".join(f"from N={n}: {t}" for n, t in changes))
    return min(ok)


# ============================================================================ figure
NODE_R = (0.12, 0.42)   # node radius at zero and at full stationary mass (unit pentagon)
ARROW_GAP = 0.08        # clearance between an arrow tip and the node it enters
GRAPH_X, GRAPH_Y = (-1.62, 1.62), (-1.68, 1.46)
GLYPH_FIT = {"o": 1.0, "s": 0.82, "^": 1.0, "v": 1.0, "D": 0.86}   # marker inside the node radius


def figure(P, point, REACH):
    """alpha-Rank response graphs, one per rule (row) and risk level (column). Each node is
    a one-model population; its area grows with the stationary mass. For every pair, one
    arrow points from the model that is taken over to the model that takes over, i.e. the
    direction of the larger fixation probability. The number under a graph is the target
    rate of the selected population."""
    cs.use()
    fig = plt.figure(figsize=cs.figsize("col", height_pt=158))
    fig._crsd_width = "col"
    grid = fig.add_gridspec(2, len(RISKS), hspace=0.0, wspace=0.0)
    angle = np.pi / 2 - 2 * np.pi * np.arange(K) / K          # first model on top, clockwise
    pos = {m: np.array([np.cos(a), np.sin(a)]) for m, a in zip(cs.MODEL_ORDER, angle)}
    span = GRAPH_X[1] - GRAPH_X[0]
    rules = (("within", N_WITHIN, "Tablemates"), ("across", N_ACROSS, "Across tables"))
    for ri, (rule, n, label) in enumerate(rules):
        for pi, p in enumerate(RISKS):
            ax = fig.add_subplot(grid[ri, pi])
            ax.set_aspect("equal")
            ax.set_xlim(*GRAPH_X)
            ax.set_ylim(*GRAPH_Y)
            ax.axis("off")
            ax.set_xticks([])
            ax.set_yticks([])
            R = rho_within(P[pi], BETA) if rule == "within" else rho_matrix(P[pi], n, BETA)
            o = point[(rule, BETA, n, pi)]
            if not np.allclose(stationary(R)[0], o["pi"]):
                raise RuntimeError(f"graph {rule} p={p}: mass differs from the reported point")
            rad = {m: NODE_R[0] + (NODE_R[1] - NODE_R[0]) * np.sqrt(o["pi"][MI[m]]) for m in M}
            for a, b in itertools.combinations(M, 2):
                ia, ib = MI[a], MI[b]
                if np.isclose(R[ia, ib], R[ib, ia], rtol=0, atol=1e-12):
                    continue
                win, lose = (a, b) if R[ia, ib] > R[ib, ia] else (b, a)
                u = (pos[win] - pos[lose]) / np.linalg.norm(pos[win] - pos[lose])
                ax.add_patch(FancyArrowPatch(tuple(pos[lose] + u * (rad[lose] + ARROW_GAP)),
                                             tuple(pos[win] - u * (rad[win] + ARROW_GAP)),
                                             arrowstyle="-|>", mutation_scale=5.5, lw=0.7,
                                             color=cs.LINE, shrinkA=0, shrinkB=0, zorder=1))
            fig.canvas.draw()
            pt_per_unit = ax.get_window_extent().width / fig.dpi * cs.POINTS_PER_INCH / span
            for m in M:
                st = cs.model(m)
                ax.plot(*pos[m], marker=st.marker, ms=2 * rad[m] * pt_per_unit * GLYPH_FIT[st.marker],
                        mfc=st.colour, mec=cs.WHITE, mew=0.7, ls="none", zorder=3)
            ax.text(0, GRAPH_Y[0] + 0.1, f"Target {100 * o['reach']:.0f}%", ha="center", va="center",
                    fontsize=cs.SIZE_SMALL, color=cs.INK)
            if ri == 0:
                ax.set_title(f"$p={p:g}$", loc="center", fontsize=cs.SIZE_LABEL, fontweight="normal",
                             pad=1.0)
            if pi == 0:
                ax.text(GRAPH_X[0] - 0.3, 0, label, rotation=90, ha="center", va="center",
                        fontsize=cs.SIZE_LABEL, color=cs.INK, clip_on=False)
    handles = [Line2D([], [], ls="none", marker=cs.model(m).marker, ms=5.2 * cs.model(m).marker_scale,
                      mfc=cs.model(m).colour, mec=cs.WHITE, mew=0.5, label=cd.show(m))
               for m in cs.MODEL_ORDER]
    cs.legend_top(fig, handles, ncols=len(handles), handlelength=0.6, handletextpad=0.3, columnspacing=0.75)
    return fig


# ============================================================================ main
def main():
    mx, sp = load()
    max_err, sign_ok = identity_check(mx)
    mixed, selfc = cell_arrays(mx, sp)
    P, REACH, WEL, point, boots = run_rules(mixed, selfc, "POOLED self-play (exp_baseline + exp_evprobe)",
                                            offset=1)

    print("\npayoff functions (pooled self-play): P[X seat | k X seats, 6-k Y seats], k = 1..6; "
          "entries at k=6 are X self-play")
    for pi, p in enumerate(RISKS):
        print(f"  p={p:.1f}")
        for x, y in itertools.permutations(range(K), 2):
            print(f"    {M[x]:10} beside {M[y]:10} " + " ".join(f"{P[pi, x, y, k]:6.2f}" for k in range(1, 7)))

    wins, beaten, n_qwen_cells, qwen_above = table_facts(mx)
    print("\npopulation-size scan")
    n_switch = switch_n(P, RISKS.index(0.9))
    switch_n(P, RISKS.index(0.5))
    switch_n(P, RISKS.index(0.1), target="Qwen")

    sp_base = sp[sp.exp == "exp_baseline"]
    _, selfc_base = cell_arrays(mx, sp_base)
    run_rules(mixed, selfc_base, "SENSITIVITY, baseline-only self-play (10 games per model per p)",
              offset=2, boot_extra=False)

    hi, mid, lo = RISKS.index(0.9), RISKS.index(0.5), RISKS.index(0.1)
    w_hi = point[("within", BETA, N_WITHIN, hi)]
    a_hi, a_mid, a_lo = (point[("across", BETA, N_ACROSS, i)] for i in (hi, mid, lo))
    mac = cd.Macros("selection.py")
    mac.add("SelIdentityMaxErr", "$<10^{-12}$")
    mac.add("SelSignAgree", thousands(sign_ok))
    mac.add("SelGrokLosesCells", str(wins))
    # Qwen against its tablemates, cell by cell (exact sign-flip, one-sided, alpha 0.05).
    # The paper reports both directions; with 60 tests a few false positives are expected.
    mac.add("SelQwenCells", str(n_qwen_cells))
    mac.add("SelQwenBelowCells", cd.word(len(beaten)))
    mac.add("SelQwenAboveCells", str(qwen_above))
    for name, i in (("Low", lo), ("Mid", mid), ("High", hi)):
        mac.add(f"SelWithinQwenMass{name}", cd.fmt(point[("within", BETA, N_WITHIN, i)]["pi"][MI["Qwen"]], 2))
    mac.add("SelWithinReachHigh", cd.pct(w_hi["reach"]))
    mac.add("SelWithinPayHigh", cd.fmt(w_hi["pay"], 1))
    mac.add("SelAcrossFlashMassMid", cd.fmt(a_mid["pi"][MI["Flash-Lite"]], 2))
    mac.add("SelAcrossFlashMassHigh", cd.fmt(a_hi["pi"][MI["Flash-Lite"]], 2))
    mac.add("SelAcrossReachHigh", cd.pct(a_hi["reach"]))
    mac.add("SelAcrossPayHigh", cd.fmt(a_hi["pay"], 1))
    mac.add("SelUniformReachHigh", cd.pct(REACH[hi].mean()))
    mac.add("SelAcrossWinnerLow", cd.show(M[a_lo["top"]]))
    mac.add("SelSwitchN", str(n_switch))
    # Robustness of the two reported rules: smallest bootstrap share in which the point
    # winner stays on top, over both rules and all three risk levels (pooled self-play).
    top_shares = [np.mean([b["top"] == point[(r, bt, n, pi)]["top"] for b in boots[(r, bt, n, pi)]])
                  for (r, bt, n) in RULES for pi in range(len(RISKS))]
    mac.add("SelBootMinPct", cd.pct(min(top_shares)))
    mac.add("SelBetaExtra", f"{BETA_EXTRA:g}")
    mac.add("SelNExtra", " and ".join(str(n) for n in N_EXTRA))
    # Strong and weak selection. Strong (beta = BETA_EXTRA): within-table target rates.
    s_mid = point[("within", BETA_EXTRA, N_WITHIN, mid)]
    s_hi = point[("within", BETA_EXTRA, N_WITHIN, hi)]
    mac.add("SelStrongWithinReachMid", cd.pct(s_mid["reach"]))
    mac.add("SelStrongWithinReachHigh", cd.pct(s_hi["reach"]))
    mac.add("SelWithinReachMid", cd.pct(point[("within", BETA, N_WITHIN, mid)]["reach"]))
    mac.add("SelUniformReachMid", cd.pct(REACH[mid].mean()))
    # Weak (beta = BETA_WEAK): not a robustness claim, reported as a boundary.
    weak_within = [outcome(P[pi], REACH[pi], WEL[pi], "within", BETA_WEAK, N_WITHIN) for pi in range(len(RISKS))]
    weak_across = [outcome(P[pi], REACH[pi], WEL[pi], "across", BETA_WEAK, N_ACROSS) for pi in range(len(RISKS))]
    for pi, p in enumerate(RISKS):
        print(f"  weak beta={BETA_WEAK}: within p={p} " + " ".join(f"{m}={v:.2f}" for m, v in zip(M, weak_within[pi]["pi"]))
              + f" | across N={N_ACROSS} top {M[weak_across[pi]['top']]} "
              + " ".join(f"{m}={v:.2f}" for m, v in zip(M, weak_across[pi]["pi"])))
    mac.add("SelWeakBeta", f"{BETA_WEAK:g}")
    mac.add("SelWeakWithinMaxMass", cd.fmt(max(float(o["pi"].max()) for o in weak_within), 2))
    mac.add("SelWeakAcrossTopHigh", cd.show(M[weak_across[hi]["top"]]))
    mac.add("SelWeakAcrossTopMid", cd.show(M[weak_across[mid]["top"]]))
    # The winners must not change with beta, population size, or self-play source.
    for (r, bt, n) in EXTRA:
        for pi in range(len(RISKS)):
            ref = point[(r, BETA, N_WITHIN if r == "within" else N_ACROSS, pi)]["top"]
            if point[(r, bt, n, pi)]["top"] != ref:
                raise RuntimeError(f"winner changes under {(r, bt, n)} at p={RISKS[pi]}")
    path = mac.write("num_selection.tex")
    print(f"\nwrote {path.relative_to(cd.REPO)}")
    for k, v in mac.items.items():
        print(f"  \\{k} = {v}")
    for key, o in point.items():
        if key[:3] in RULES and o["n_unit"] != 1:
            raise RuntimeError(f"reducible chain for a reported rule {key}")

    fig = figure(P, point, REACH)
    pdf = cs.save(fig, cd.FIGURES / "fig_selection", title="fig_selection")
    print(f"wrote {pdf.relative_to(cd.REPO)} (+ .png)")
    if len(beaten) > 3:
        raise RuntimeError(
            f"Qwen is significantly below its tablemates in {len(beaten)} of {n_qwen_cells} cells; "
            "the paper's reading of Qwen as the table winner needs revisiting")


if __name__ == "__main__":
    main()
