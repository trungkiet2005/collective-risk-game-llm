"""Who earns more at the same table, and which pairs reach the target.

Run from the repository root:
    python paper/AAMAS/analysis/advantage.py

Reuses the loader of selection.py (read-only access to results/exp_mixed, exp_baseline and
exp_evprobe through crsd_data; never Legacy_Results/, never writes under results/). Writes
    paper/AAMAS/figures/fig_advantage.pdf (+ .png preview)
    paper/AAMAS/tables/num_advantage.tex

ONE MATRIX, TWO TRIANGLES. The payoff gap is antisymmetric and group success is symmetric,
so each needs only half a matrix: the payoff gap fills the cells above the diagonal (rust
to blue), group success fills the diagonal and the cells below it (slate).

a  PAYOFF EDGE AT THE SAME TABLE. Cell (row X, column Y) = mean over the 150 mixed games
   of the pair (pooled over k = 1..5 and p in {.1,.5,.9}) of
       mean expected payoff of the X seats - mean expected payoff of the Y seats
   at that table. Expected payoff = 40 - own total if the table reached 120, else
   (1 - p)(40 - own total). Both seat blocks share the pool and the lottery, so the edge
   is the contribution gap scaled by 1 or 1 - p. The matrix is antisymmetric by
   construction; the script asserts it. Diagonal: no edge exists ("self").
b  GROUP SUCCESS. Off-diagonal = share of the pair's 150 mixed games reaching the target
   (symmetric). Diagonal = self-play target rate at the same three p, exp_baseline +
   exp_evprobe pooled (identical game condition), 60 games; drawn italic in a thin box.

Unit = game. Game-level bootstrap CIs are printed, not drawn.

LAYOUT. The matrix is tried at column width first. If any cell label would be wider than
its cell minus a 2 pt margin, or a print gate fails, the figure is built at text width
instead; stdout says which and why.
"""
from __future__ import annotations

import itertools
import math
import sys
from pathlib import Path

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, TwoSlopeNorm
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parent))
import crsd_data as cd      # noqa: E402
import crsd_style as cs     # noqa: E402
import selection as sel     # noqa: E402  (loader only; selection.main() is not run)

M = cd.MODELS
K = len(M)
MI = {m: i for i, m in enumerate(M)}
CELL_MARGIN_PT = 2.0


# ============================================================================ numbers
def matrices(mx, sp):
    edge = np.full((K, K), np.nan)
    reach = np.full((K, K), np.nan)
    count = np.zeros((K, K), int)
    n = np.zeros((K, K), int)
    edge_ci = {}
    contrib_gap = np.full((K, K), np.nan)
    for (a, b), d in mx.groupby(["A", "B"]):
        i, j = MI[a], MI[b]
        if len(d) != 150:
            raise RuntimeError(f"{a}/{b}: {len(d)} games, expected 150")
        gap = (d.eA - d.eB).to_numpy(float)
        edge[i, j], edge[j, i] = gap.mean(), -gap.mean()
        lo, hi = cd.boot_ci(gap, offset=500 + 10 * i + j)
        edge_ci[(i, j)], edge_ci[(j, i)] = (lo, hi), (-hi, -lo)
        cg = (d.cA - d.cB).to_numpy(float).mean()
        contrib_gap[i, j], contrib_gap[j, i] = cg, -cg
        reach[i, j] = reach[j, i] = d.reached.mean()
        count[i, j] = count[j, i] = int(d.reached.sum())
        n[i, j] = n[j, i] = len(d)
    for m, d in sp.groupby("model"):
        i = MI[m]
        if len(d) != 60:
            raise RuntimeError(f"{m}: {len(d)} self-play games, expected 60")
        reach[i, i], count[i, i], n[i, i] = d.reached.mean(), int(d.reached.sum()), len(d)
    off = ~np.eye(K, dtype=bool)
    if not np.allclose(edge[off], -edge.T[off], atol=1e-12):
        raise RuntimeError("payoff-edge matrix is not antisymmetric")
    if not np.allclose(reach, reach.T):
        raise RuntimeError("group-success matrix is not symmetric")
    if np.isnan(edge[off]).any() or np.isnan(reach).any():
        raise RuntimeError("a matrix cell is empty")
    return edge, edge_ci, contrib_gap, reach, count, n


def report(edge, edge_ci, contrib_gap, reach, count, n, sp):
    print("a  payoff edge, row minus column, mean expected payoff per seat [95% game-level CI], "
          "150 games per pair; (row minus column contribution per seat)")
    print("            " + "".join(f"{m:>26}" for m in M))
    for i, m in enumerate(M):
        cells = []
        for j in range(K):
            if i == j:
                cells.append(f"{'self':>26}")
            else:
                lo, hi = edge_ci[(i, j)]
                cells.append(f"{edge[i, j]:+6.2f} [{lo:+5.1f},{hi:+5.1f}] ({contrib_gap[i, j]:+5.1f})")
        print(f"  {m:10}" + "".join(f"{c:>26}" for c in cells))
    print("  row means over partners: " + ", ".join(
        f"{m} {np.nanmean(np.where(np.eye(K, dtype=bool), np.nan, edge)[i]):+.2f}" for i, m in enumerate(M)))
    print("\nb  share of games reaching the target (count/games); diagonal = self-play, 60 games")
    print("            " + "".join(f"{m:>16}" for m in M))
    for i, m in enumerate(M):
        print(f"  {m:10}" + "".join(f"{100 * reach[i, j]:6.1f}% ({count[i, j]:3d}/{n[i, j]:3d})" for j in range(K)))
    print("  self-play target rate by p: " + "; ".join(
        f"{m} " + " ".join(f"{100 * d.reached.mean():.0f}%" for _, d in sp[sp.model == m].groupby("p"))
        for m in M))


# ============================================================================ figure
def signed(v: float) -> str:
    s = f"{v:+.1f}"
    return "0.0" if float(s) == 0 else s.replace("-", "−")


def draw(edge, reach, width):
    cs.use()
    height = 188 if width == "col" else 190
    fig = plt.figure(figsize=cs.figsize(width, height_pt=height))
    fig._crsd_width = width
    grid = fig.add_gridspec(2, 2, width_ratios=[1, 0.045], wspace=0.04, hspace=0.3)
    ax = fig.add_subplot(grid[:, 0])
    cax_gap, cax_reach = fig.add_subplot(grid[0, 1]), fig.add_subplot(grid[1, 1])
    off = ~np.eye(K, dtype=bool)
    vmax = float(math.ceil(np.nanmax(np.abs(edge[off]))))
    norm_gap = TwoSlopeNorm(0.0, -vmax, vmax)
    norm_reach = Normalize(0.0, 100.0)
    cell_texts = []
    for i, j in itertools.product(range(K), range(K)):
        if j > i:     # above the diagonal: payoff of the row model minus the column model
            fc, text = cs.CMAP_DIV(norm_gap(edge[i, j])), signed(edge[i, j])
        else:         # diagonal and below: share of games reaching the target
            fc, text = cs.CMAP_SEQ(norm_reach(100 * reach[i, j])), f"{100 * reach[i, j]:.0f}%"
        ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, fc=fc, ec=cs.WHITE, lw=1.2, zorder=2))
        ink = cs.cell_ink(fc)
        cell_texts.append(ax.text(j, i, text, ha="center", va="center", fontsize=cs.SIZE_SMALL,
                                  color=ink, zorder=3, fontstyle="italic" if i == j else "normal"))
        if i == j:    # self-play: italic in a thin box
            ax.add_patch(Rectangle((i - 0.5 + 0.08, i - 0.5 + 0.08), 0.84, 0.84, fill=False, ec=ink,
                                   lw=0.7, zorder=3))
    ax.set_xlim(-0.5, K - 0.5)
    ax.set_ylim(K - 0.5, -0.5)
    ax.set_aspect("equal")
    cs.row_labels(ax, list(M), wrap=True, colour=False)       # beside crsd_div: no model hues
    cs.row_labels(ax, list(M), axis="x", wrap=True, colour=False)
    ax.xaxis.tick_top()
    cs.style_matrix_axes(ax)

    for cax, cmap, norm, ticks, labels, title in (
            (cax_gap, cs.CMAP_DIV, norm_gap, [-vmax, 0, vmax],
             [f"−{vmax:.0f}", "0", f"+{vmax:.0f}"], "Payoff gap, upper"),
            (cax_reach, cs.CMAP_SEQ, norm_reach, [0, 50, 100], ["0", "50", "100"],
             "Target %, lower")):
        cb = fig.colorbar(mpl.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax)
        cb.outline.set_visible(False)
        cb.set_ticks(ticks)
        cb.set_ticklabels(labels)
        cb.ax.tick_params(length=2.0, width=0.6, labelsize=cs.SIZE_SMALL)
        cb.set_label(title, fontsize=cs.SIZE_SMALL)
    return fig, cell_texts


def fits(fig, texts):
    """Every cell label must sit inside its cell with a CELL_MARGIN_PT margin on both sides,
    and the print gates (text size, collisions) must pass."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    worst = np.inf
    for t in texts:
        ax = t.axes
        x, _ = t.get_position()
        cell_px = abs(ax.transData.transform((x + 0.5, 0))[0] - ax.transData.transform((x - 0.5, 0))[0])
        text_px = t.get_window_extent(renderer=r).width
        worst = min(worst, (cell_px - text_px) / 2 * cs.POINTS_PER_INCH / fig.dpi)
    cell_pt = cell_px * cs.POINTS_PER_INCH / fig.dpi
    try:
        cs.check_text(fig)
        cs.check_overlap(fig)
        gate = "gates pass"
    except RuntimeError as err:
        gate = f"gate fails: {str(err)[:160]}".replace("−", "-")
    ok = worst >= CELL_MARGIN_PT and gate == "gates pass"
    return ok, f"cell {cell_pt:.1f} pt, tightest label margin {worst:.1f} pt per side, {gate}"


# ============================================================================ main
def main():
    mx, sp = sel.load()
    edge, edge_ci, contrib_gap, reach, count, n = matrices(mx, sp)
    report(edge, edge_ci, contrib_gap, reach, count, n, sp)

    fig, texts = draw(edge, reach, "col")
    ok, why = fits(fig, texts)
    print(f"\nlayout at column width: {why} -> {'use it' if ok else 'too crowded'}")
    if not ok:
        plt.close(fig)
        fig, texts = draw(edge, reach, "full")
        ok, why = fits(fig, texts)
        print(f"layout at text width: {why}")
        if not ok:
            raise RuntimeError("cell labels do not fit even at text width")
    pdf = cs.save(fig, cd.FIGURES / "fig_advantage", title="fig_advantage")
    print(f"wrote {pdf.relative_to(cd.REPO)} (+ .png) at {'column' if fig._crsd_width == 'col' else 'text'} width")

    off = ~np.eye(K, dtype=bool)
    g = MI["Grok"]
    grok_row = {M[j]: edge[g, j] for j in range(K) if j != g}
    worst_partner = min(grok_row, key=grok_row.get)
    if grok_row[worst_partner] >= 0:
        raise RuntimeError("Grok is not behind any partner; AdvGrokWorst would not be a loss")
    q = MI["Qwen"]
    qwen_row = {M[j]: edge[q, j] for j in range(K) if j != q}
    best_partner = max(qwen_row, key=qwen_row.get)
    if qwen_row[best_partner] <= 0:
        raise RuntimeError("Qwen has no positive edge")
    pairs = {(i, j): reach[i, j] for i, j in itertools.combinations(range(K), 2)}
    low = min(pairs.values())
    low_pairs = [key for key, v in pairs.items() if np.isclose(v, low)]
    if len(low_pairs) != 1:
        raise RuntimeError(f"lowest target share is tied: {[(M[i], M[j]) for i, j in low_pairs]}")
    li, lj = low_pairs[0]

    mac = cd.Macros("advantage.py")
    mac.add("AdvGrokWorst", cd.fmt(-grok_row[worst_partner], 1))
    mac.add("AdvGrokWorstPartner", cd.show(worst_partner))
    mac.add("AdvQwenBest", cd.fmt(qwen_row[best_partner], 1))
    mac.add("AdvQwenBestPartner", cd.show(best_partner))
    mac.add("AdvMaxAbs", cd.fmt(float(np.max(np.abs(edge[off]))), 1))
    mac.add("AdvPairLowReach", str(count[li, lj]))
    mac.add("AdvPairLowReachName", f"{cd.show(M[li])} and {cd.show(M[lj])}")
    mac.add("AdvPairLowReachPct", cd.pct(low))
    path = mac.write("num_advantage.tex")
    print(f"wrote {path.relative_to(cd.REPO)}")
    for k, v in mac.items.items():
        print(f"  \\{k} = {v}")


if __name__ == "__main__":
    main()
