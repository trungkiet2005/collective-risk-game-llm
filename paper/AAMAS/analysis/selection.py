"""Empirical game-theoretic analysis: the five models as strategies, and what selection picks.

Run from the repository root:
    python paper/AAMAS/analysis/selection.py

Reads results/exp_mixed, results/exp_baseline and results/exp_evprobe through crsd_data
(read-only; never Legacy_Results/, never writes under results/). Writes
    paper/AAMAS/figures/fig_selection.pdf (+ .png preview)
    paper/AAMAS/supplement/figures/fig_invasion.pdf (+ .png preview)
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

FIG_SELECTION. Stationary mass per rule and risk level (bars, with the population's
self-play target rate), and the expected payoff of a Qwen3-235B or Gemini 3.5
Flash-Lite seat as the number of Qwen3-235B seats changes in the same table.

EGTTOOLS. The supplement's invasion diagrams (fig_invasion) are computed and drawn with
EGTTools (Fernandez Domingos, Santos & Lenaerts 2023): egttools.analytical.StochDynamics recomputes every fixation probability
and stationary distribution from the same payoff functions, the script refuses to draw
unless they match its own to 1e-7, and egttools.plotting.draw_invasion_diagram draws the
graphs.
"""
from __future__ import annotations

import itertools
import sys
import warnings
from math import comb
from pathlib import Path

import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from scipy.special import logsumexp
from egttools.analytical import StochDynamics
from egttools.plotting import draw_invasion_diagram

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
NODE_SIZE = 130          # pt^2, draw_invasion_diagram's node_size
ARROW_HEAD = 7.0         # networkx's default head is drawn for a 10-inch figure, not a column
MASS_GAP = 0.24          # mass label: horizontal offset from the node centre (layout units)
EGT_ATOL = 1e-7          # StochDynamics returns 0 once a fixation sum passes 1e7
# circular_layout puts node 0 at angle 0, so the pentagon spans x = -0.81..1; the margins
# hold the mass labels left and right of the nodes and the target line at the bottom left
GRAPH_X, GRAPH_Y = (-1.55, 1.62), (-1.22, 1.14)


def blank(ax):
    ax.axis("off")
    ax.set_xticks([])
    ax.set_yticks([])


def egt_dynamics(Pp, N, beta=BETA):
    """Fixation matrix and stationary distribution from egttools' StochDynamics.

    payoffs[x, y](k, 6) is the payoff of an x seat at a table with k x seats and 6 - k
    y seats, i.e. P[x, y, k]; StochDynamics samples those tables hypergeometrically from a
    population of N. fp[r, i] is the fixation probability of one i newcomer in r."""
    payoffs = np.array([[(lambda k, group, *_, x=x, y=y: Pp[x, y, k]) for y in range(K)]
                        for x in range(K)], dtype=object)
    dyn = StochDynamics(K, payoffs, pop_size=N, group_size=cd.N_PLAYERS)
    with warnings.catch_warnings(), np.errstate(over="ignore"):
        # exp overflow under strong selection, and the near-1 diagonal warning; reducible
        # chains are caught by stationary() in run_rules instead
        warnings.simplefilter("ignore", RuntimeWarning)
        _, fp = dyn.transition_and_fixation_matrix(beta)
        sd = dyn.calculate_stationary_distribution(beta)
    return fp, sd


def invasion_figure(P, point, REACH):
    """Invasion diagrams from egttools.plotting.draw_invasion_diagram, one per risk level
    (row) and rule (column), styled as EGTTools draws them: plain coloured nodes, black
    arrows, the stationary mass printed beside every node. An edge A -> B means one B
    newcomer takes over an A population with more than the neutral probability 1/N
    (draw_invasion_diagram's rule; a neutral pair would be a dashed line). The line at the
    bottom left is the target rate of the selected population."""
    cs.use()
    fig = plt.figure(figsize=cs.figsize("col", height_pt=268))
    fig._crsd_width = "col"
    rules = (("within", N_WITHIN, f"Tablemates, $N={N_WITHIN}$"),
             ("across", N_ACROSS, f"Across tables, $N={N_ACROSS}$"))
    grid = fig.add_gridspec(len(RISKS), len(rules) + 1, hspace=0.0, wspace=0.0,
                            width_ratios=(0.08, *[1] * len(rules)))
    off = ~np.eye(K, dtype=bool)
    for pi, p in enumerate(RISKS):
        lax = fig.add_subplot(grid[pi, 0])
        blank(lax)
        lax.text(0.5, 0.5, f"$p={p:g}$", rotation=90, ha="center", va="center",
                 fontsize=cs.SIZE_LABEL, color=cs.INK, transform=lax.transAxes)
        for ri, (rule, n, label) in enumerate(rules):
            ax = fig.add_subplot(grid[pi, ri + 1])
            o = point[(rule, BETA, n, pi)]
            R = rho_within(P[pi], BETA) if rule == "within" else rho_matrix(P[pi], n, BETA)
            fp, sd = egt_dynamics(P[pi], n)
            if not (np.allclose(fp.T[off], R[off], rtol=0, atol=EGT_ATOL)
                    and np.allclose(sd, o["pi"], rtol=0, atol=EGT_ATOL)):
                raise RuntimeError(f"graph {rule} p={p}: egttools disagrees with this script")
            G = draw_invasion_diagram(list(M), 1 / n, fp, sd, node_size=NODE_SIZE,
                                      display_node_labels=False, display_edge_labels=False,
                                      display_sd_labels=False, edge_width=0.7, node_linewidth=0.0,
                                      colors=[cs.model(m).colour for m in M], ax=ax)
            for arrow in ax.patches:
                arrow.set_mutation_scale(ARROW_HEAD)
            # Masses beside the nodes rather than above and below (egttools' placement), so
            # the row height is the pentagon's and the spare column width holds the labels.
            pos = nx.circular_layout(G)            # the layout draw_invasion_diagram uses
            for i, m in enumerate(M):
                x, y = pos[m]
                right = x > 0
                ax.text(x + (MASS_GAP if right else -MASS_GAP), y, f"{sd[i]:.2f}",
                        ha="left" if right else "right", va="center", fontsize=cs.SIZE_SMALL,
                        color=cs.INK)
            blank(ax)
            ax.set_aspect("equal")
            ax.set_xlim(*GRAPH_X)
            ax.set_ylim(*GRAPH_Y)
            ax.text(GRAPH_X[0], GRAPH_Y[0] + 0.1, f"Target {100 * o['reach']:.0f}%", ha="left",
                    va="bottom", fontsize=cs.SIZE_SMALL, color=cs.INK)
            if pi == 0:
                ax.set_title(label, loc="center", fontsize=cs.SIZE_LABEL, fontweight="normal",
                             pad=2.0)
    handles = [Line2D([], [], ls="none", marker="o", ms=6.0, mfc=cs.model(m).colour, mec="none",
                      label=cd.show(m)) for m in cs.MODEL_ORDER]
    # Three per row: the five versioned names do not fit on one line of a column.
    cs.legend_top(fig, handles, ncols=3, handlelength=0.6, handletextpad=0.3, columnspacing=0.75)
    return fig


COMP_PAIR = ("Qwen", "Flash-Lite")
COMP_RISKS = (0.5, 0.9)
BAR_HATCH = {"Haiku": "....", "Luna": "///", "Grok": "xxx"}
BAR_LABEL_MIN = 0.2      # print the mass inside a bar segment at least this wide
VISIBLE_MASS = 0.005     # narrower segments are invisible at column width; they stay out of the key


def selection_figure(P, point):
    """a, b: stationary mass per risk level for the two rules, with the population's
    self-play target rate at the right of each bar. c, d: expected payoff of a Qwen or
    Flash-Lite seat by the number of Qwen seats at the same table. Returns the figure and
    every number drawn."""
    rules = ((N_WITHIN, "within", f"Tablemates, $N={N_WITHIN}$"),
             (N_ACROSS, "across", f"Across tables, $N={N_ACROSS}$"))
    drawn = dict(mass={}, target={}, composition={})
    shown = [m for m in cs.MODEL_ORDER
             if any(point[(r, BETA, n, pi)]["pi"][MI[m]] >= VISIBLE_MASS
                    for n, r, _ in rules for pi in range(len(RISKS)))]
    cs.use()
    fig = plt.figure(figsize=cs.figsize("col", height_pt=192))
    fig._crsd_width = "col"
    outer = fig.add_gridspec(2, 1, height_ratios=(0.62, 1.0))
    top = outer[0].subgridspec(1, 2, wspace=0.12)
    bars = [fig.add_subplot(top[0, j]) for j in range(2)]
    bottom = outer[1].subgridspec(1, 2, wspace=0.08)
    gax = [fig.add_subplot(bottom[0, j]) for j in range(2)]

    for j, (n, rule, label) in enumerate(rules):
        ax = bars[j]
        for row, p in enumerate(RISKS):
            o = point[(rule, BETA, n, RISKS.index(p))]
            left = 0.0
            for m in cs.MODEL_ORDER:
                w = float(o["pi"][MI[m]])
                drawn["mass"][(rule, p, m)] = w
                if w <= 0:
                    continue
                st = cs.model(m)
                ax.barh(row, w, left=left, height=0.74, color=st.colour, ec=cs.WHITE, lw=0.5,
                        zorder=2, hatch=BAR_HATCH.get(m, ""))
                if w >= BAR_LABEL_MIN:
                    ax.text(left + w / 2, row, f"{w:.2f}", ha="center", va="center",
                            fontsize=cs.SIZE_SMALL, color=cs.cell_ink(st.colour), zorder=3,
                            bbox=dict(fc=st.colour, ec="none", pad=0.0))
                left += w
            drawn["target"][(rule, p)] = cd.pct(o["reach"])
            ax.text(1.04, row, f"{cd.pct(o['reach'])}%", ha="left", va="center",
                    fontsize=cs.SIZE_SMALL, color=cs.INK, clip_on=False)
        ax.set_ylim(2.55, -0.55)
        ax.set_xlim(0, 1.0)
        ax.set_xticks([0, 1], ["0", "1"])
        ax.tick_params(axis="y", length=0)
        ax.spines["left"].set_visible(False)
        ax.grid(False)
        ax.set_yticks(range(len(RISKS)), [f"$p={p:g}$" for p in RISKS] if j == 0 else [])
        cs.panel_title(ax, "ab"[j], label)

    handles = [Patch(fc=cs.model(m).colour, ec=cs.WHITE, lw=0.4, hatch=BAR_HATCH.get(m, ""),
                     label=cd.show(m)) for m in shown]
    q, f = MI[COMP_PAIR[0]], MI[COMP_PAIR[1]]
    x = np.arange(N_WITHIN + 1)
    for j, p in enumerate(COMP_RISKS):
        ax = gax[j]
        pi = RISKS.index(p)
        q_pay = np.array([np.nan if k == 0 else P[pi, q, f, k] for k in x])
        f_pay = np.array([P[pi, f, f, 6] if k == 0 else
                          (np.nan if k == N_WITHIN else P[pi, f, q, 6 - k]) for k in x])
        drawn["composition"][(p, COMP_PAIR[0])] = q_pay
        drawn["composition"][(p, COMP_PAIR[1])] = f_pay
        qm, fm = cs.model(COMP_PAIR[0]), cs.model(COMP_PAIR[1])
        ax.plot(x, q_pay, color=qm.colour, lw=cs.LW_DATA, marker=qm.marker, ms=4.0,
                mfc=qm.colour, mec=cs.WHITE, mew=0.5, label=cd.show(COMP_PAIR[0]), zorder=3)
        ax.plot(x, f_pay, color=fm.colour, lw=cs.LW_DATA, marker=fm.marker, ms=4.0,
                mfc=fm.colour, mec=cs.WHITE, mew=0.5, label=cd.show(COMP_PAIR[1]), zorder=3)
        ax.axhline(cd.FAIR_TOTAL, color=cs.INK, lw=cs.LW_THEORY,
                   ls=(0, (4.5, 2.0)), zorder=2)
        ax.set_xlim(0, N_WITHIN)
        ax.set_ylim(0, 42)
        ax.set_xticks(range(N_WITHIN + 1))
        ax.set_yticks([0, 20, 40] if j == 0 else [])
        ax.grid(axis="y", color=cs.LINE, alpha=0.18, lw=0.6)
        cs.panel_title(ax, "cd"[j], f"$p={p:g}$")
        if j == 0:
            ax.set_ylabel("Expected payoff per seat")
        else:
            ax.tick_params(axis="y", labelleft=False)
    fig.supxlabel(f"Number of {cd.show(COMP_PAIR[0])} seats in the table",
                  fontsize=cs.SIZE_LABEL)
    handles += [Line2D([], [], color=cs.INK, lw=cs.LW_THEORY, ls=(0, (4.5, 2.0)),
                        label="Fair-share payoff")]
    fig.legend(handles=handles, loc="outside upper center", ncols=2, handlelength=1.4,
               handletextpad=0.3, columnspacing=1.2)
    return fig, drawn


def check_drawn(drawn, mac):
    """The bars and target labels must print the numbers the paper's macros state."""
    masses = {("within", 0.1, "Qwen"): "SelWithinQwenMassLow",
              ("within", 0.5, "Qwen"): "SelWithinQwenMassMid",
              ("within", 0.9, "Qwen"): "SelWithinQwenMassHigh",
              ("across", 0.5, "Flash-Lite"): "SelAcrossFlashMassMid",
              ("across", 0.9, "Flash-Lite"): "SelAcrossFlashMassHigh"}
    for key, name in masses.items():
        if cd.fmt(drawn["mass"][key], 2) != mac.items[name]:
            raise RuntimeError(f"fig_selection bar {key} is {drawn['mass'][key]:.4f} "
                               f"but {name} = {mac.items[name]}")
    targets = {("within", 0.5): "SelWithinReachMid", ("within", 0.9): "SelWithinReachHigh",
               ("across", 0.9): "SelAcrossReachHigh"}
    for key, name in targets.items():
        if drawn["target"][key] != mac.items[name]:
            raise RuntimeError(f"fig_selection target {key} is {drawn['target'][key]}% "
                               f"but {name} = {mac.items[name]}")


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

    fig, drawn = selection_figure(P, point)
    check_drawn(drawn, mac)
    print("\nfig_selection: stationary mass drawn (within N=6, across N=30) and target rate")
    for (rule, p), t in drawn["target"].items():
        print(f"  {rule:6} p={p:.1f} " + " ".join(f"{m}={drawn['mass'][(rule, p, m)]:.3f}"
                                                  for m in cs.MODEL_ORDER) + f" | target {t}%")
    for p in COMP_RISKS:
        q_pay = drawn["composition"][(p, COMP_PAIR[0])]
        f_pay = drawn["composition"][(p, COMP_PAIR[1])]
        print(f"  payoff curves Qwen/Flash-Lite p={p:.1f}: "
              f"Qwen {np.round(q_pay, 2).tolist()} | Flash-Lite {np.round(f_pay, 2).tolist()}")
    pdf = cs.save(fig, cd.FIGURES / "fig_selection", title="fig_selection")
    print(f"wrote {pdf.relative_to(cd.REPO)} (+ .png)")
    fig = invasion_figure(P, point, REACH)
    pdf = cs.save(fig, cd.PAPER / "supplement" / "figures" / "fig_invasion", title="fig_invasion")
    print(f"wrote {pdf.relative_to(cd.REPO)} (+ .png)")
    if len(beaten) > 3:
        raise RuntimeError(
            f"Qwen is significantly below its tablemates in {len(beaten)} of {n_qwen_cells} cells; "
            "the paper's reading of Qwen as the table winner needs revisiting")


if __name__ == "__main__":
    main()
