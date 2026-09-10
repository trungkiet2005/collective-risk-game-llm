"""Figure 10 for the paper: the top-tier frontier panel.

Recomputes every quantity from raw games.csv under results/frontier/*/exp_baseline/
plus results/open_source/crsd_all_models.csv for the open-weight comparison bars.

  fig10: (a) contribution vs risk, English, six API models
         (b) target-reach vs risk against the human benchmark
         (c) risk effect across the whole 13-model panel, with the two
             controlled contrasts (capability, reasoning) bracketed

Kept separate from make_figures.py / make_figures_expansion.py so that the
earlier figures stay byte-for-byte reproducible from their own sources.

Run:  python paper/make_figures_toptier.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent / "results"
FIG = HERE / "figures"; FIG.mkdir(exist_ok=True)

mpl.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 300,
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9.5,
    "axes.linewidth": 0.8, "axes.edgecolor": "#3a3a38",
    "axes.spines.top": False, "axes.spines.right": False,
    "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
    "legend.fontsize": 8, "legend.frameon": False,
    "lines.linewidth": 1.8, "lines.markersize": 6,
    "grid.color": "#e1e0d9", "grid.linewidth": 0.7,
    "figure.facecolor": "white", "axes.facecolor": "white",
    "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
})
INK, INK2 = "#26251f", "#6f6d63"

# provider palette
PROV = {"Google": "#3b7dd8", "OpenAI": "#0f9d76",
        "Anthropic": "#d1663c", "xAI": "#7a4fbf"}
GREY = "#9a9891"

FRONT = {
    "google-gemini-3.1-pro-preview":        ("Gemini-3.1-Pro",  "Google",    "top"),
    "openai-gpt-5.6-sol":                   ("GPT-5.6-sol",     "OpenAI",    "top"),
    "anthropic-claude-opus-5-default":      ("Claude-Opus-5",   "Anthropic", "top"),
    "xai-grok-4.20-0309-reasoning":         ("Grok-4.20 (R)",   "xAI",       "top"),
    "xai-grok-4.20-0309-non-reasoning":     ("Grok-4.20 (no R)", "xAI",      "top"),
    "google-gemini-3.1-flash-lite-preview": ("Gemini-3.1-Flash-Lite", "Google", "cheap"),
    "OpenAIGPT5Nano":                       ("GPT-5.4-nano",    "OpenAI",    "cheap"),
}
OPEN = {
    "qwen25-7b-instruct": "Qwen2.5-7B", "llama-3-1-8b": "Llama-3.1-8B",
    "gemma2-9b-it": "Gemma-2-9B", "gemma2-27b-it": "Gemma-2-27B",
    "qwen25-32b-instruct": "Qwen2.5-32B",
    "llama-3-1-70b-instruct-awq": "Llama-3.1-70B",
    "qwen25-72b-instruct-awq": "Qwen2.5-72B",
}
RISKS = [0.1, 0.5, 0.9]
HUMAN = [0.0, 0.10, 0.50]           # Milinski et al. 2008 target-reach rates


def save(fig, name):
    fig.savefig(FIG / f"{name}.pdf")
    fig.savefig(FIG / f"{name}.png", dpi=150)
    plt.close(fig)
    print(f"  -> {name}.pdf / .png")


# ---------------------------------------------------------------- load
fr = pd.concat([pd.read_csv(p) for p in
                sorted((ROOT / "frontier").glob("*/exp_baseline/games.csv"))],
               ignore_index=True)
fr["reach"] = fr.target_reached.astype(int)

ow = pd.read_csv(ROOT / "open_source/crsd_all_models.csv")
ow = ow[ow.experiment == "exp_baseline"].copy()
ow["reach"] = ow.target_reached.astype(int)


def cell(df, model, lang, risk, col="group_total"):
    s = df[(df.model == model) & (df.language == lang) & (df.risk_probability == risk)]
    return s[col].mean()


def risk_effect(df, model, lang="en"):
    return cell(df, model, lang, 0.9) - cell(df, model, lang, 0.1)


# ---------------------------------------------------------------- figure
def fig_toptier():
    fig = plt.figure(figsize=(7.2, 6.4))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.15], hspace=0.46, wspace=0.30)
    axA = fig.add_subplot(gs[0, 0])
    axB = fig.add_subplot(gs[0, 1])
    axC = fig.add_subplot(gs[1, :])

    # ---- (a) contribution vs risk, English
    order = ["google-gemini-3.1-pro-preview", "openai-gpt-5.6-sol",
             "xai-grok-4.20-0309-non-reasoning", "anthropic-claude-opus-5-default",
             "xai-grok-4.20-0309-reasoning", "google-gemini-3.1-flash-lite-preview"]
    # Gemini-3.1-Pro and GPT-5.6-sol are all but coincident (0.0/120.0/120.0 versus
    # 1.6/120.0/119.8); Pro is drawn 3 points high purely so both stay visible.
    OFF_A = {"google-gemini-3.1-pro-preview": 3.0}
    for m in order:
        lab, prov, tier = FRONT[m]
        y = [cell(fr, m, "en", r) + OFF_A.get(m, 0.0) for r in RISKS]
        ls = "-" if tier == "top" else "--"
        axA.plot(RISKS, y, ls, marker="o", color=PROV[prov], ms=5.2,
                 mec="white", mew=0.7, lw=1.7, zorder=3)
    axA.axhline(120, color=INK2, ls=":", lw=1.0, zorder=1)
    axA.text(0.905, 126, "target", fontsize=6.8, color=INK2, ha="right", va="bottom")
    axA.annotate("Gemini-3.1-Pro\nGPT-5.6-sol", xy=(0.13, 8), xytext=(0.28, 44),
                 fontsize=7.0, color=INK, ha="left",
                 arrowprops=dict(arrowstyle="->", color=INK2, lw=0.8))
    axA.annotate("Grok-4.20\n(reasoning off)", xy=(0.9, 220.8), xytext=(0.44, 232),
                 fontsize=7.0, color=PROV["xAI"], ha="left", va="top",
                 arrowprops=dict(arrowstyle="->", color=PROV["xAI"], lw=0.8))
    axA.set_xticks(RISKS); axA.set_xlim(0.02, 0.98); axA.set_ylim(-14, 258)
    axA.set_xlabel("Catastrophe risk $p$")
    axA.set_ylabel("Group contribution (of 240)")
    axA.set_title("(a)  Two models withhold everything at low risk",
                  loc="left", fontsize=9.2)
    axA.yaxis.grid(True, alpha=0.6); axA.set_axisbelow(True)

    # ---- (b) reach vs risk, against humans
    OFF_B = {"google-gemini-3.1-pro-preview": 0.035,
             "anthropic-claude-opus-5-default": -0.035,
             "xai-grok-4.20-0309-non-reasoning": 0.035}
    for m in order:
        lab, prov, tier = FRONT[m]
        y = [fr[(fr.model == m) & (fr.language == "en") &
                (fr.risk_probability == r)].reach.mean() for r in RISKS]
        ls = "-" if tier == "top" else "--"
        axB.plot(RISKS, np.array(y) + OFF_B.get(m, 0.0), ls, marker="o",
                 color=PROV[prov], ms=5.2, mec="white", mew=0.7, lw=1.7, zorder=3)
    axB.plot(RISKS, HUMAN, "-", marker="s", color=INK, ms=5.0, lw=1.8,
             dashes=(4, 2), zorder=4)
    axB.annotate("humans\n(Milinski 2008)", xy=(0.9, 0.50), xytext=(0.60, 0.62),
                 fontsize=7.0, color=INK, ha="left",
                 arrowprops=dict(arrowstyle="->", color=INK, lw=0.8))
    axB.annotate("step at the EV threshold", xy=(0.5, 0.97), xytext=(0.30, 0.30),
                 fontsize=7.0, color=INK2, ha="left",
                 arrowprops=dict(arrowstyle="->", color=INK2, lw=0.8))
    axB.set_xticks(RISKS); axB.set_xlim(0.02, 0.98); axB.set_ylim(-0.07, 1.10)
    axB.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    axB.set_xlabel("Catastrophe risk $p$")
    axB.set_ylabel("Target-reach rate")
    axB.set_title("(b)  Risk-responsive, but not human-like", loc="left", fontsize=9.2)
    axB.yaxis.grid(True, alpha=0.6); axB.set_axisbelow(True)

    hand = [Line2D([], [], color=PROV[p], lw=1.7, marker="o", ms=4.6, mec="white",
                   label=p) for p in ["Google", "OpenAI", "Anthropic", "xAI"]]
    hand += [Line2D([], [], color=INK2, lw=1.5, ls="--", label="cheap tier")]
    axB.legend(handles=hand, loc="lower right", fontsize=6.6, handlelength=1.7,
               ncol=1, labelspacing=0.25, borderpad=0.2)

    # ---- (c) risk effect across the whole panel
    bars = []
    for m, lab in OPEN.items():
        bars.append((lab, risk_effect(ow, m), GREY, "open"))
    for m, (lab, prov, tier) in FRONT.items():
        bars.append((lab, risk_effect(fr, m), PROV[prov], tier))
    bars.sort(key=lambda t: t[1])
    ypos = np.arange(len(bars))
    for i, b in enumerate(bars):
        if b[3] == "cheap":
            axC.barh(i, b[1], height=0.62, zorder=3, facecolor="white",
                     edgecolor=b[2], lw=1.0, hatch="////")
        else:
            axC.barh(i, b[1], height=0.62, zorder=3, facecolor=b[2],
                     edgecolor="none")
    axC.axvline(0, color=INK2, lw=0.9, zorder=2)
    axC.set_yticks(ypos)
    axC.set_yticklabels([b[0] for b in bars], fontsize=7.4)
    axC.set_xlim(-14, 152)
    axC.set_xlabel("Risk effect on group contribution, $p=0.1\\to0.9$ "
                   "(points of 240, English)")
    axC.set_title("(c)  Two configurations of fourteen respond to risk; the rest barely move",
                  loc="left", fontsize=9.2)
    axC.xaxis.grid(True, alpha=0.6); axC.set_axisbelow(True)

    idx = {b[0]: i for i, b in enumerate(bars)}

    def bracket(x, i1, i2, colour, text):
        cap = 2.6
        axC.plot([x, x], [i1, i2], color=colour, lw=1.1, zorder=5,
                 solid_capstyle="butt")
        for i in (i1, i2):
            axC.plot([x - cap, x], [i, i], color=colour, lw=1.1, zorder=5)
        axC.text(x + 3.5, (i1 + i2) / 2, text, fontsize=6.9, color=colour,
                 va="center", ha="left")

    bracket(131, idx["Gemini-3.1-Flash-Lite"], idx["Gemini-3.1-Pro"],
            PROV["Google"], "same family,\ndifferent tier")
    bracket(52, idx["Grok-4.20 (R)"], idx["Grok-4.20 (no R)"],
            PROV["xAI"], "same model,\nreasoning off / on")

    axC.text(1.0, -0.235, "open-weight 7–72B in grey; hatched = cheap API tier",
             transform=axC.transAxes, fontsize=6.6, color=INK2,
             ha="right", va="top")

    save(fig, "fig10_toptier")


if __name__ == "__main__":
    fig_toptier()
