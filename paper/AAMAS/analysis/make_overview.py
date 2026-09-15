"""Create the graphical overview for the AAMAS manuscript.

The figure is deliberately code-native: every label and relationship is
editable, selectable in the PDF, and consistent with the publication figures.
It is a graphical abstract / supplementary overview, not a replacement for the
quantitative result figures in the eight-page submission.
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "figures" / "graphical_overview.pdf"

COLORS = {
    "blue": "#0072B2",      # measurement
    "orange": "#E69F00",    # intervention
    "green": "#009E73",     # result
    "ink": "#263238",
    "muted": "#64748B",
    "pale_blue": "#E8F2F8",
    "pale_orange": "#FFF4D6",
    "pale_green": "#E7F4ED",
}


def box(ax, x, y, w, h, title, body, face, edge):
    patch = FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.015,rounding_size=0.025",
        facecolor=face, edgecolor=edge, linewidth=1.35,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h * 0.68, title, ha="center", va="center",
            fontsize=10.5, fontweight="bold", color=COLORS["ink"])
    ax.text(x + w / 2, y + h * 0.34, body, ha="center", va="center",
            fontsize=8.2, color=COLORS["ink"], linespacing=1.35)


def arrow(ax, x0, y0, x1, y1, label=None):
    a = FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>",
                        mutation_scale=13, linewidth=1.25,
                        color=COLORS["muted"], shrinkA=2, shrinkB=2)
    ax.add_patch(a)
    if label:
        ax.text((x0 + x1) / 2, (y0 + y1) / 2 + 0.035, label, ha="center",
                va="bottom", fontsize=7.3, color=COLORS["muted"])


def main():
    plt.rcParams.update({"font.family": "DejaVu Sans", "pdf.fonttype": 42})
    fig, ax = plt.subplots(figsize=(11.0, 4.3), constrained_layout=True)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.5, 0.96, "When does apparent cooperation reflect a response to others?",
            ha="center", va="top", fontsize=15, fontweight="bold", color=COLORS["ink"])
    ax.text(0.5, 0.90, "Collective-risk dilemma: six agents choose 0, 2, or 4 across ten rounds",
            ha="center", va="top", fontsize=9.3, color=COLORS["muted"])

    box(ax, 0.035, 0.36, 0.20, 0.34, "Collective-risk game",
        "Private endowment: 40\nTarget: 120\nMiss target → catastrophe with risk p",
        COLORS["pale_blue"], COLORS["blue"])

    box(ax, 0.30, 0.61, 0.21, 0.22, "Risk grid",
        "Self-play; p = 0…1\nDoes play move when incentives move?",
        COLORS["pale_orange"], COLORS["orange"])
    box(ax, 0.30, 0.35, 0.21, 0.22, "Focal-point & knowledge controls",
        "Remove equal-split hint\nAsk rules and EV mid-game",
        COLORS["pale_orange"], COLORS["orange"])
    box(ax, 0.30, 0.09, 0.21, 0.22, "Best-response profiling",
        "One LLM + five scripted opponents\nKnown policies make the best response exact",
        COLORS["pale_orange"], COLORS["orange"])

    box(ax, 0.60, 0.35, 0.18, 0.34, "Observed pattern",
        "Risk, wording, and known\nopponents barely change play\n\nKnowledge ≠ action",
        COLORS["pale_green"], COLORS["green"])
    box(ax, 0.83, 0.35, 0.14, 0.34, "Deployment lesson",
        "A fixed schedule\ncan meet a group goal\nwithout protecting\nits own resources",
        COLORS["pale_green"], COLORS["green"])

    arrow(ax, 0.235, 0.53, 0.30, 0.72)
    arrow(ax, 0.235, 0.53, 0.30, 0.46)
    arrow(ax, 0.235, 0.53, 0.30, 0.20)
    arrow(ax, 0.51, 0.72, 0.60, 0.58)
    arrow(ax, 0.51, 0.46, 0.60, 0.52)
    arrow(ax, 0.51, 0.20, 0.60, 0.46)
    arrow(ax, 0.78, 0.52, 0.83, 0.52)

    ax.text(0.5, 0.025,
            "Evidence base: 550 risk-grid games, 150 focal-point-control games, 250 scripted-opponent games.",
            ha="center", va="bottom", fontsize=7.8, color=COLORS["muted"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, bbox_inches="tight")
    fig.savefig(OUT.with_suffix(".png"), dpi=300, bbox_inches="tight", facecolor="white")
    print(OUT)


if __name__ == "__main__":
    main()
