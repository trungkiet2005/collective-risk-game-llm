"""Graphical overview of the paper: the game, the four designs, the four findings.

Run from the repository root, AFTER selfplay.py (it reads the game counts that script writes):
    python paper/AAMAS/analysis/overview.py

Writes (and nothing else):
    paper/AAMAS/figures/fig_overview.pdf (+ .png preview)
No longer placed in main.tex: since 19-09-2026 fig:overview is the TikZ figure
paper/AAMAS/tikz_figure_complete/figure_biolinum.pdf (game and designs only).

Every count on the figure is read from tables/num_selfplay.tex, the same macros the prose
prints, and the four design counts must add up to \\CntGames or the figure is not drawn.
Rule constants (six players, ten rounds, 40 units, target 120, moves 0/2/4, p* = 1/2) are
definitions and are typed. Geometry is in printed points on one axes that spans the figure.
The numbered badges tie each design card to the finding it supports.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import crsd_data as cd      # noqa: E402
import crsd_style as cs     # noqa: E402

HEIGHT_PT = 105.0
PROMPT_ARMS = ("CntGamesProbe", "CntGamesNoCue", "CntGamesPara", "CntGamesTempZero",
               "CntGamesWording", "CntGamesNeutral")


# ============================================================================ counts
def counts() -> dict:
    path = cd.TABLES / "num_selfplay.tex"
    text = path.read_text(encoding="utf-8")
    macro = {k: int(v.replace("{,}", "")) for k, v in
             re.findall(r"\\newcommand\{\\(CntGames\w*)\}\{([\d{},]+)\}", text)}
    missing = [k for k in ("CntGames", "CntGamesBaseline", "CntGamesScripted", "CntGamesMixed",
                           *PROMPT_ARMS) if k not in macro]
    if missing:
        raise RuntimeError(f"{path.name} lacks {missing}; run selfplay.py first")
    out = dict(selfplay=macro["CntGamesBaseline"], prompt=sum(macro[k] for k in PROMPT_ARMS),
               scripted=macro["CntGamesScripted"], mixed=macro["CntGamesMixed"])
    if sum(out.values()) != macro["CntGames"]:
        raise RuntimeError(f"design counts {out} add up to {sum(out.values())}, "
                           f"not \\CntGames = {macro['CntGames']}; a design is missing a card")
    return out


# ============================================================================ drawing
class Canvas:
    def __init__(self):
        cs.use()
        self.W, self.H = cs.TEXT_W_PT, HEIGHT_PT
        self.fig = plt.figure(figsize=(self.W / cs.POINTS_PER_INCH, self.H / cs.POINTS_PER_INCH),
                              layout="none")
        self.fig._crsd_width = "full"
        ax = self.fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, self.W)
        ax.set_ylim(0, self.H)
        ax.axis("off")
        ax.set_xticks([])
        ax.set_yticks([])
        self.ax = ax
        self.title_y = self.H - 7.0

    def text(self, x, y, s, *, size=cs.SIZE_SMALL, colour=cs.INK, ha="left", **kw):
        return self.ax.text(x, y, s, ha=ha, va="center", fontsize=size, color=colour, **kw)

    def title(self, x, s):
        self.text(x, self.title_y, s, size=cs.SIZE_TITLE, fontweight="bold")

    def glyph(self, x, y, name, ms=5.2):
        if name is None:    # scripted seat: open LINE circle, never a model shape (palette cost 4)
            self.ax.plot([x], [y], marker="o", ms=ms * 0.82, mfc=cs.WHITE, mec=cs.LINE, mew=1.0,
                         ls="none", zorder=4)
            return
        st = cs.model(name)
        self.ax.plot([x], [y], marker=st.marker, ms=ms * st.marker_scale, mfc=st.colour,
                     mec=cs.WHITE, mew=0.5, ls="none", zorder=4)

    def table(self, cx, cy, seats, r_table=4.8, r_ring=10.0):
        self.ax.add_patch(Circle((cx, cy), r_table, fc=cs.REGION, ec="none", zorder=3))
        for k, seat in enumerate(seats):
            a = np.pi / 2 - 2 * np.pi * k / len(seats)
            self.glyph(cx + r_ring * np.cos(a), cy + r_ring * np.sin(a), seat)

    def badge(self, x, y, n):
        self.ax.add_patch(Circle((x, y), 4.5, fc=cs.INK, ec="none", zorder=5))
        self.text(x, y - 0.2, str(n), colour=cs.WHITE, ha="center", fontweight="bold", zorder=6)

    def flow(self, x0, x1, y):
        self.ax.add_patch(FancyArrowPatch(
            (x0, y), (x1, y), color=cs.LINE, lw=0, zorder=1,
            arrowstyle="simple,head_length=4.5,head_width=6.5,tail_width=2.4"))


def draw(n: dict):
    c = Canvas()
    mid_y = 50.0

    # ---- a  the game: six seats of 40 around the pool, the rules, and the benchmark
    c.title(0, "a   The game")
    tcx, tcy, ring = 25.0, 60.0, 18.0
    c.ax.add_patch(Circle((tcx, tcy), 10.0, fc=cs.REGION, ec="none", zorder=2))
    c.text(tcx, tcy, "Pool", ha="center", zorder=3)
    for k in range(cd.N_PLAYERS):
        a = np.pi / 2 - 2 * np.pi * k / cd.N_PLAYERS
        x, y = tcx + ring * np.cos(a), tcy + ring * np.sin(a)
        c.ax.add_patch(Circle((x, y), 6.1, fc=cs.WHITE, ec=cs.INK, lw=0.8, zorder=3))
        c.text(x, y - 0.2, f"{cd.ENDOWMENT:.0f}", ha="center", zorder=4)
    lx = 54.0
    c.text(lx, 85.0, "Six players, ten rounds")
    c.text(lx, 76.0, "Pay 0, 2 or 4 each round")
    c.text(lx, 64.5, "Pool reaches 120:", fontweight="bold")
    c.text(lx, 55.5, "keep what is left")
    c.text(lx, 44.0, "Pool misses:", fontweight="bold")
    c.text(lx, 35.0, "lose all with prob. $p$")
    # best total per seat against p (Proposition 1)
    bx0, by0, bw, bh = 20.0, 13.0, 140.0, 14.5
    bax = c.fig.add_axes([bx0 / c.W, by0 / c.H, bw / c.W, bh / c.H])
    bax.axvspan(0, cd.PSTAR, color=cs.REGION, lw=0, zorder=0)
    bax.plot([0, cd.PSTAR, cd.PSTAR, 1], [0, 0, cd.FAIR_TOTAL, cd.FAIR_TOTAL], **cs.THEORY)
    bax.set_xlim(0, 1)
    bax.set_ylim(-3, cd.FAIR_TOTAL + 3)
    bax.set_xticks([0, cd.PSTAR, 1], ["0", "0.5", "1"])
    bax.text(1.03, 0.0, "$p$", transform=bax.transAxes, ha="left", va="center",
             fontsize=cs.SIZE_LABEL, color=cs.INK)
    bax.set_yticks([0, cd.FAIR_TOTAL], ["0", f"{cd.FAIR_TOTAL:.0f}"])
    bax.tick_params(axis="x", pad=1.0)
    bax.grid(False)
    bax.text(0.25, cd.FAIR_TOTAL / 2, "best: keep", ha="center", va="center",
             fontsize=cs.SIZE_SMALL, color=cs.MUTED)
    bax.text(0.75, cd.FAIR_TOTAL / 2 - 2, "best: pay 20", ha="center", va="center",
             fontsize=cs.SIZE_SMALL, color=cs.MUTED)
    c.flow(170.0, 180.0, mid_y)

    # ---- b  four designs, one card each; the mini table shows who sits at it
    bx, cw, gap = 184.0, 101.0, 5.0
    c.title(bx, "b   Four designs")
    top, bottom = c.title_y - 8.0, 3.0
    ch = (top - bottom - gap) / 2
    cards = [
        (0, 0, "Self-play", ("Eleven risk levels", "from 0 to 1"), n["selfplay"], ["Haiku"] * 6, (1,)),
        (1, 0, "Prompt tests", ("In-game questions,", "rewordings, temp. 0"), n["prompt"], ["Luna"] * 6, (2,)),
        (0, 1, "Scripted partners", ("Always 0, 2 or 4,", "or copy the group"), n["scripted"],
         ["Grok"] + [None] * 5, (2,)),
        (1, 1, "Two models", ("10 pairs at one table,", "then selection"), n["mixed"],
         ["Qwen"] * 3 + ["Flash-Lite"] * 3, (3, 4)),
    ]
    for col, row, head, lines, count, seats, badges in cards:
        x = bx + col * (cw + gap)
        y = top - (row + 1) * ch - row * gap
        c.ax.add_patch(FancyBboxPatch((x, y), cw, ch, boxstyle="round,pad=0,rounding_size=3.5",
                                      fc=cs.GREY_LIGHT, ec="none", zorder=1))
        c.table(x + 15.0, y + ch / 2, seats)
        tx = x + 30.0
        c.text(tx, y + ch - 8.0, head, size=cs.SIZE_LABEL, fontweight="bold")
        for i, line in enumerate(lines):
            c.text(tx, y + ch - 17.5 - 8.9 * i, line)
        c.text(tx, y + 5.2, f"{count:,} games", colour=cs.MUTED)
        for j, b in enumerate(badges):
            c.badge(x + cw - 6.5 - 10.5 * (len(badges) - 1 - j), y + 6.0, b)
    c.flow(bx + 2 * cw + gap + 2.0, bx + 2 * cw + gap + 12.0, mid_y)

    # ---- c  findings, numbered like the badges on the cards
    fx = bx + 2 * cw + gap + 16.0
    c.title(fx, "c   What we find")
    findings = (("Same pay at every risk,", "even at $p = 0$"),
                ("Answers track the risk,", "payments do not"),
                ("One late dropout breaks", "fair-share tables"),
                ("Tablemate scoring picks", "the smallest payer"))
    fy = top - 6.0
    step = (top - 6.0 - (bottom + 13.0)) / (len(findings) - 1)
    for k, (l1, l2) in enumerate(findings, start=1):
        c.badge(fx + 4.5, fy - 4.4, k)
        c.text(fx + 12.5, fy, l1)
        c.text(fx + 12.5, fy - 9.0, l2)
        fy -= step
    return c.fig


def main():
    n = counts()
    print(f"design counts: {n} (sum {sum(n.values())})")
    fig = draw(n)
    pdf = cs.save(fig, cd.FIGURES / "fig_overview", title="fig_overview")
    print(f"wrote {pdf.relative_to(cd.REPO)} (+ .png)")


if __name__ == "__main__":
    main()
