"""Figure 1 — study-design schematic for the CRG-LLM paper.

Two bands: (a) the collective-risk game played by an LLM-agent loop; (b) the two studies.
Pure matplotlib vector schematic -> paper/figures/fig1_pipeline.pdf/.png

Every text element is registered against its container box and checked for overflow
after rendering (see `validate()`), so the figure cannot silently regress.
"""
from pathlib import Path
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
import numpy as np

HERE = Path(__file__).resolve().parent
FIG = HERE / "figures"; FIG.mkdir(exist_ok=True)

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "savefig.dpi": 300, "savefig.bbox": "tight", "savefig.pad_inches": 0.03,
})

INK = "#0b0b0b"; INK2 = "#4c4b48"; MUTED = "#8a887f"
SURF = "#f5f4f0"; EDGE = "#c9c8c1"
BLUE = "#2a78d6"; BLUEF = "#e8f0fc"
ORANGE = "#eb6834"; VIOLET = "#4a3aa7"
GREEN = "#0f9d58"; GREENF = "#e7f4ec"
RED = "#d03b3b"; REDF = "#fbeaea"

FW, FH = 7.2, 5.0
fig, ax = plt.subplots(figsize=(FW, FH))
ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")

# --- overflow bookkeeping -------------------------------------------------
_checks = []          # (text_artist, (x0,y0,x1,y1), label)

def box(x, y, w, h, fc=SURF, ec=EDGE, lw=1.1, r=0.16, z=2):
    rs = min(r * min(w, h), 0.47 * min(w, h))
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                 boxstyle=f"round,pad=0,rounding_size={rs}",
                 fc=fc, ec=ec, lw=lw, zorder=z))
    return (x, y, x + w, y + h)

def txt(x, y, s, size=6, color=INK, weight="normal", ha="center", va="center",
        z=5, style="normal", box_rect=None, label=""):
    t = ax.text(x, y, s, fontsize=size, color=color, weight=weight, ha=ha, va=va,
                zorder=z, style=style)
    if box_rect is not None:
        _checks.append((t, box_rect, label or s[:26]))
    return t

def arrow(x1, y1, x2, y2, color=INK2, lw=1.5, mut=10, rad=0.0, z=3):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                 mutation_scale=mut, color=color, lw=lw, zorder=z,
                 connectionstyle=f"arc3,rad={rad}", shrinkA=1, shrinkB=1))

def band_title(x, y, tag, s):
    txt(x, y, tag, size=10, weight="bold", ha="left", color=INK)
    txt(x + 5.0, y, s, size=9.4, weight="bold", ha="left", color=INK)

# =====================================================================
# BAND (a) — the game            boxes y = 58..92
# =====================================================================
band_title(2, 96.5, "(a)", "A collective-risk dilemma, played by six LLM agents")

BY, BH = 58, 34

# ---------- box 1: the game ----------
b1 = box(2, BY, 29, BH, fc="white", ec=EDGE, lw=1.2)
txt(16.5, BY + 30.5, "The game", size=8.2, weight="bold", box_rect=b1, label="t:game")
for i, xc in enumerate(np.linspace(5.8, 27.2, 6)):
    ax.add_patch(Circle((xc, BY + 24.5), 1.65, fc=BLUEF, ec=BLUE, lw=1.0, zorder=4))
    txt(xc, BY + 24.5, f"A{i+1}", size=4.9, color=BLUE, weight="bold",
        box_rect=b1, label=f"agent{i+1}")
    arrow(xc, BY + 22.2, xc, BY + 19.6, color=MUTED, lw=0.8, mut=6)
# pool bar
p1 = box(5.5, BY + 13.0, 22, 6.4, fc=SURF, ec=INK2, lw=1.0, r=0.18, z=3)
txt(16.5, BY + 17.6, "common pool", size=6.0, color=INK2, box_rect=p1, label="pool")
txt(16.5, BY + 15.1, "target  €120", size=6.6, color=INK, weight="bold",
    box_rect=p1, label="target")
txt(16.5, BY + 9.6, "6 agents · €40 each", size=6.0, color=INK2,
    box_rect=b1, label="cap1")
txt(16.5, BY + 6.6, "contribute 0, 2 or 4 each round", size=6.0, color=INK2,
    box_rect=b1, label="cap2")
txt(16.5, BY + 3.6, "10 rounds", size=6.0, color=INK2, box_rect=b1, label="cap3")

# ---------- box 2: one agent's turn ----------
b2 = box(35.5, BY, 29, BH, fc="white", ec=EDGE, lw=1.2)
txt(50, BY + 30.5, "One agent's turn", size=8.2, weight="bold", box_rect=b2, label="t:turn")
pc = box(38, BY + 18.5, 23, 9.2, fc=SURF, ec=EDGE, lw=1.0, r=0.12, z=3)
txt(50, BY + 25.8, "PROMPT", size=5.4, color=MUTED, weight="bold", box_rect=pc, label="prompt")
for k, s in enumerate(["· the rules", "· every past round",
                       "· CONTRIBUTION: __"]):
    txt(39.6, BY + 23.9 - k * 1.9, s, size=5.3, color=INK2, ha="left",
        box_rect=pc, label=f"pl{k}")
arrow(50, BY + 18.3, 50, BY + 15.6, color=INK2, lw=1.3, mut=9)
lc = box(44, BY + 10.2, 12, 5.2, fc=BLUEF, ec=BLUE, lw=1.2, r=0.2, z=3)
txt(50, BY + 12.8, "LLM", size=7.6, color=BLUE, weight="bold", box_rect=lc, label="llm")
arrow(50, BY + 10.0, 50, BY + 7.4, color=BLUE, lw=1.3, mut=9)
txt(50, BY + 5.6, "contributes 0, 2 or 4", size=6.5, color=INK, weight="bold",
    box_rect=b2, label="dec")
txt(50, BY + 2.4, "repeated for 10 rounds", size=5.9, color=MUTED,
    style="italic", box_rect=b2, label="loop")

# ---------- box 3: end of game ----------
b3 = box(69, BY, 29, BH, fc="white", ec=EDGE, lw=1.2)
txt(83.5, BY + 30.5, "End of the game", size=8.2, weight="bold", box_rect=b3, label="t:end")
txt(83.5, BY + 26.2, "pool ≥ €120 ?", size=7.4, weight="bold", color=INK,
    box_rect=b3, label="q")
arrow(83.5, BY + 24.3, 77, BY + 21.9, color=GREEN, lw=1.1, mut=8)
arrow(83.5, BY + 24.3, 90, BY + 21.9, color=RED, lw=1.1, mut=8)
gb = box(71, BY + 11.5, 12, 10.0, fc=GREENF, ec=GREEN, lw=1.1, r=0.16, z=3)
txt(77, BY + 18.2, "REACHED", size=6.0, color=GREEN, weight="bold", box_rect=gb, label="reach")
txt(77, BY + 15.0, "keep the rest", size=5.6, color=INK2, box_rect=gb, label="k1")
rb = box(84, BY + 11.5, 12, 10.0, fc=REDF, ec=RED, lw=1.1, r=0.16, z=3)
txt(90, BY + 18.2, "MISSED", size=6.0, color=RED, weight="bold", box_rect=rb, label="miss")
txt(90, BY + 15.4, "lose it all", size=5.6, color=INK2, box_rect=rb, label="m1")
txt(90, BY + 13.6, "with prob. $p$", size=5.6, color=RED, box_rect=rb, label="m2")
txt(83.5, BY + 8.2, "catastrophe risk", size=6.0, color=INK2, box_rect=b3, label="cr")
txt(83.5, BY + 4.6, "$p \\in \\{0.1,\\ 0.5,\\ 0.9\\}$", size=7.0, color=INK,
    weight="bold", box_rect=b3, label="pvals")

# flow arrows between the three boxes
arrow(31.2, BY + BH / 2, 35.3, BY + BH / 2, color=INK2, lw=1.7, mut=12)
arrow(64.7, BY + BH / 2, 68.8, BY + BH / 2, color=INK2, lw=1.7, mut=12)

# =====================================================================
# BAND (b) — the two studies     boxes y = 6..46
# =====================================================================
ax.plot([2, 98], [52.5, 52.5], color="#e6e5df", lw=1.0, zorder=1)
band_title(2, 49.5, "(b)", "Two studies on the same games")

SY, SH = 6, 40

# ---------- study 1 ----------
s1 = box(2, SY, 46.5, SH, fc="white", ec=EDGE, lw=1.2)
txt(4.6, SY + 36.2, "Study 1 · Behaviour", size=8.4, weight="bold", ha="left",
    box_rect=s1, label="t:s1")
txt(4.6, SY + 32.3, "Do the agents cooperate more when the risk is", size=6.3,
    color=INK2, ha="left", box_rect=s1, label="q1a")
txt(4.6, SY + 29.6, "higher, as humans do (Milinski et al. 2008)?", size=6.3,
    color=INK2, ha="left", box_rect=s1, label="q1b")
txt(4.6, SY + 26.4, "full factorial", size=5.9, color=MUTED, style="italic",
    ha="left", box_rect=s1, label="ff")

def chip(x, y, w, s, fc, ec, tc, size=6.1, h=4.6, label=""):
    r = box(x, y, w, h, fc=fc, ec=ec, lw=1.0, r=0.3, z=3)
    txt(x + w / 2, y + h / 2, s, size=size, color=tc, weight="bold",
        box_rect=r, label=label)

CY = SY + 20.8
chip(4.6, CY, 17.0, "7 models · 7B–72B", BLUEF, BLUE, BLUE, label="c1")
txt(22.9, CY + 2.3, "×", size=7.5, color=MUTED)
chip(24.6, CY, 12.2, "$p$ = .1 / .5 / .9", SURF, EDGE, INK, label="c2")
txt(38.0, CY + 2.3, "×", size=7.5, color=MUTED)
chip(39.4, CY, 7.4, "EN · VN", SURF, EDGE, INK, label="c3")
txt(25.25, SY + 17.4, "= 60 games per model", size=6.3, color=INK2,
    box_rect=s1, label="ng")
txt(25.25, SY + 12.6, "human benchmark: 0% · 10% · 50% reach", size=6.1,
    color=MUTED, box_rect=s1, label="hb")
mb1 = box(4.6, SY + 4.0, 41.5, 5.4, fc=SURF, ec=EDGE, lw=1.0, r=0.12, z=3)
txt(25.35, SY + 6.7, "measures:   target-reach rate  ·  how much they pool",
    size=6.2, color=INK, box_rect=mb1, label="m:v1")

# ---------- study 2 ----------
s2 = box(51.5, SY, 46.5, SH, fc="white", ec=EDGE, lw=1.2)
txt(54.1, SY + 36.2, "Study 2 · Comprehension", size=8.4, weight="bold", ha="left",
    box_rect=s2, label="t:s2")
txt(54.1, SY + 32.3, "Is the deviation a real choice — or do they", size=6.3,
    color=INK2, ha="left", box_rect=s2, label="q2a")
txt(54.1, SY + 29.6, "simply misunderstand the game?", size=6.3,
    color=INK2, ha="left", box_rect=s2, label="q2b")

pb = box(54.1, SY + 20.6, 19.5, 6.2, fc=BLUEF, ec=BLUE, lw=1.0, r=0.14, z=3)
txt(63.85, SY + 24.8, "the same prompt", size=5.8, color=BLUE, weight="bold",
    box_rect=pb, label="p1")
txt(63.85, SY + 22.4, "+ one probe question", size=5.6, color=INK2,
    box_rect=pb, label="p2")
arrow(73.9, SY + 23.7, 77.3, SY + 23.7, color=INK2, lw=1.2, mut=9)
gb2 = box(77.6, SY + 20.6, 18.4, 6.2, fc=SURF, ec=EDGE, lw=1.0, r=0.14, z=3)
txt(86.8, SY + 24.8, "graded against the", size=5.6, color=INK2, box_rect=gb2, label="g1")
txt(86.8, SY + 22.4, "engine's ground truth", size=5.6, color=INK, weight="bold",
    box_rect=gb2, label="g2")

AXC = {"Rules": (BLUE, "the fixed rules"), "Time": (ORANGE, "read the history"),
       "State": (VIOLET, "sum the pool")}
for k, (name, (col, sub)) in enumerate(AXC.items()):
    xx = 54.1 + k * 14.35
    r = box(xx, SY + 12.6, 12.8, 6.2, fc="white", ec=col, lw=1.3, r=0.14, z=3)
    txt(xx + 6.4, SY + 16.8, name, size=6.6, color=col, weight="bold",
        box_rect=r, label=f"ax{k}")
    txt(xx + 6.4, SY + 14.3, sub, size=5.3, color=INK2, box_rect=r, label=f"axs{k}")
txt(74.75, SY + 10.6, "20 questions · 3 axes · ground truth from the engine",
    size=5.7, color=MUTED, box_rect=s2, label="qn")
mb2 = box(54.1, SY + 4.0, 41.9, 5.4, fc=SURF, ec=EDGE, lw=1.0, r=0.12, z=3)
txt(75.05, SY + 6.7, "measure:   answer accuracy (does it understand?)",
    size=6.2, color=INK, box_rect=mb2, label="m:v2")

# =====================================================================
# validation: no text may overflow its container
# =====================================================================
def validate():
    fig.canvas.draw()
    inv = ax.transData.inverted()
    bad = []
    for t, (x0, y0, x1, y1), label in _checks:
        bb = t.get_window_extent(fig.canvas.get_renderer())
        (dx0, dy0) = inv.transform((bb.x0, bb.y0))
        (dx1, dy1) = inv.transform((bb.x1, bb.y1))
        pad = 0.35                       # required clearance inside the box
        if dx0 < x0 + pad or dx1 > x1 - pad or dy0 < y0 + pad or dy1 > y1 - pad:
            bad.append((label, round(dx0, 2), round(dx1, 2), round(dy0, 2),
                        round(dy1, 2), (x0, y0, x1, y1)))
    if bad:
        print(f"  !! {len(bad)} TEXT OVERFLOW(S):")
        for b in bad:
            print(f"     {b[0]:<12} text x[{b[1]},{b[2]}] y[{b[3]},{b[4]}]  box {b[5]}")
    else:
        print(f"  all {len(_checks)} text elements fit inside their boxes")
    return bad

bad = validate()
fig.savefig(FIG / "fig1_pipeline.pdf")
fig.savefig(FIG / "fig1_pipeline.png", dpi=170)
plt.close(fig)
print("-> fig1_pipeline.pdf / .png")
