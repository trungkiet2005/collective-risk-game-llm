"""Figures 8-9 for the paper expansion (composition effect + frontier generalisation).

Recomputes every quantity from raw games.csv:
  - fig8: open-source persona/composition sweep (results/open_source/exp_test/exp_persona/)
  - fig9: frontier model gpt-5.4-nano, baseline + persona
    (results/frontier/openai-gpt-5.4-nano/exp_baseline/, .../exp_persona/)

Kept in a separate module from make_figures.py (which is scoped, by design, to
results/open_source/crsd_all_models.csv only) so that the original figures stay
byte-for-byte reproducible from that single source. Shares its style constants.

Run:  python paper/make_figures_expansion.py
"""
from __future__ import annotations
import glob
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats as _st
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
INK = "#0b0b0b"; INK2 = "#52514e"; MUTED = "#898781"
FAM = {"Qwen": "#2a78d6", "Gemma": "#eb6834", "Llama": "#4a3aa7"}
EN_C, VN_C = "#2a78d6", "#d03b3b"


def save(fig, name):
    fig.savefig(FIG / f"{name}.pdf")
    fig.savefig(FIG / f"{name}.png", dpi=150)
    plt.close(fig)
    print(f"  -> {name}.pdf / .png")


NSEL = {
    "personas_cooperative": 0, "personas_mixed_1sel_5coop": 1,
    "personas_mixed_2sel_4coop": 2, "personas_mixed_3sel_3coop": 3,
    "personas_mixed_4sel_2coop": 4, "personas_mixed_5sel_1coop": 5,
    "personas_selfish": 6,
}
MLAB = {"gemma2-9b-it": "Gemma-2-9B", "llama-3-1-8b": "Llama-3.1-8B",
        "qwen25-7b-instruct": "Qwen2.5-7B"}
MFAM = {"gemma2-9b-it": "Gemma", "llama-3-1-8b": "Llama", "qwen25-7b-instruct": "Qwen"}

# =====================================================================
# load
# =====================================================================
dfs = [pd.read_csv(f) for f in glob.glob(str(ROOT / "open_source/exp_test/exp_persona/*/games.csv"))]
p_os = pd.concat(dfs, ignore_index=True)
p_os["nsel"] = p_os.persona_set.map(NSEL)
p_os["reach"] = p_os.target_reached.astype(int)

fb = pd.read_csv(ROOT / "frontier/openai-gpt-5.4-nano/exp_baseline/games.csv")
fb["reach"] = fb.target_reached.astype(int)

fp = pd.read_csv(ROOT / "frontier/openai-gpt-5.4-nano/exp_persona/games.csv")
fp["nsel"] = fp.persona_set.map(NSEL)
fp["reach"] = fp.target_reached.astype(int)


# =====================================================================
# FIG 8 — open-source composition effect: the linear engine
# =====================================================================
def fig_composition():
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(7.2, 3.5))
    models = ["qwen25-7b-instruct", "llama-3-1-8b", "gemma2-9b-it"]  # legend order: least->most fragile
    xs = np.arange(7)

    for m in models:
        s = p_os[p_os.model == m]
        col = FAM[MFAM[m]]
        means = s.groupby("nsel").group_total.mean().reindex(xs)
        sd = s.groupby("nsel").group_total.std().reindex(xs)
        slope, intercept, r, pval, se = _st.linregress(s.nsel, s.group_total)
        axA.plot(xs, intercept + slope * xs, "-", color=col, lw=1.3, alpha=0.55, zorder=1)
        axA.errorbar(xs, means, yerr=sd, fmt="o", color=col, ms=5.5, mec="white", mew=0.7,
                     capsize=2, elinewidth=0.8, ecolor=col, zorder=3, label=MLAB[m])
    axA.axhline(120, color=INK2, ls="--", lw=1.0)
    axA.text(6.3, 124, "target (120)", fontsize=6.8, color=INK2, va="bottom", ha="right")
    axA.set_xlim(-0.4, 6.4); axA.set_ylim(0, 265)
    axA.set_xticks(xs)
    axA.set_xlabel("Selfish-persona agents in the group (of 6)")
    axA.set_ylabel("Group contribution (of 240)")
    axA.set_title("(a)  Contribution falls linearly with composition", loc="left", fontsize=9.2)
    axA.yaxis.grid(True, alpha=0.6); axA.set_axisbelow(True)
    axA.legend(loc="upper right", fontsize=7.4, handlelength=1.6)

    for m in models:
        s = p_os[p_os.model == m]
        col = FAM[MFAM[m]]
        rr = s.groupby("nsel").reach.mean().reindex(xs)
        axB.plot(xs, rr, "-o", color=col, ms=5.5, lw=1.6, mec="white", mew=0.7, zorder=3)
    axB.set_xlim(-0.4, 6.9); axB.set_ylim(-0.08, 1.30)
    axB.set_xticks(xs)
    axB.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    axB.set_xlabel("Selfish-persona agents in the group (of 6)")
    axB.set_ylabel("Target-reach rate")
    axB.set_title("(b)  Reach = does the line clear 120", loc="left", fontsize=9.2)
    axB.yaxis.grid(True, alpha=0.6); axB.set_axisbelow(True)
    axB.annotate("Gemma-2-9B: tips at\none selfish agent", xy=(1, 0.5), xytext=(0.25, 0.16),
                 fontsize=6.8, color=FAM["Gemma"], ha="left",
                 arrowprops=dict(arrowstyle="->", color=FAM["Gemma"], lw=0.8))
    axB.annotate("Llama-3.1-8B: cliff\nbetween 4 and 6", xy=(5, 0.52), xytext=(2.7, 0.70),
                 fontsize=6.8, color=FAM["Llama"], ha="left",
                 arrowprops=dict(arrowstyle="->", color=FAM["Llama"], lw=0.8))
    axB.annotate("Qwen2.5-7B: never tips", xy=(4.4, 1.0), xytext=(4.4, 1.20),
                 fontsize=6.8, color=FAM["Qwen"], ha="center", va="bottom",
                 arrowprops=dict(arrowstyle="->", color=FAM["Qwen"], lw=0.8))

    fig.tight_layout(w_pad=1.8)
    save(fig, "fig8_composition")


# =====================================================================
# FIG 9 — frontier model (gpt-5.4-nano): risk still null, language + composition dominate
# =====================================================================
def fig_frontier():
    fig = plt.figure(figsize=(7.2, 6.6))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1], hspace=0.42, wspace=0.32)
    axA = fig.add_subplot(gs[0, 0])
    axB = fig.add_subplot(gs[0, 1])
    axC = fig.add_subplot(gs[1, :])

    # --- (a) risk-insensitivity persists: reach & contribution by risk x language
    g = fb.groupby(["language", "risk_probability"]).agg(
        reach=("reach", "mean"), contrib=("group_total", "mean")).reset_index()
    for lang, col, lab in [("en", EN_C, "English"), ("vn", VN_C, "Vietnamese")]:
        s = g[g.language == lang].sort_values("risk_probability")
        axA.plot(s.risk_probability, s.contrib, "-o", color=col, ms=6, lw=1.8,
                 mec="white", mew=0.7, label=lab, zorder=3)
    axA.axhline(120, color=INK2, ls="--", lw=1.0)
    axA.text(0.95, 124, "target (120)", fontsize=6.6, color=INK2, va="bottom", ha="right")
    axA.set_xticks([0.1, 0.5, 0.9]); axA.set_xlim(0.03, 0.97); axA.set_ylim(0, 265)
    axA.set_xlabel("Catastrophe risk  $p$")
    axA.set_ylabel("Group contribution (of 240)")
    axA.set_title("(a)  Risk still does nothing", loc="left", fontsize=9.2)
    axA.yaxis.grid(True, alpha=0.6); axA.set_axisbelow(True)
    axA.legend(loc="upper left", fontsize=7.4, bbox_to_anchor=(0.0, 1.02))
    axA.annotate("reach 100% at\nevery risk level", xy=(0.5, 210), xytext=(0.5, 168),
                 fontsize=6.6, color=EN_C, ha="center",
                 arrowprops=dict(arrowstyle="->", color=EN_C, lw=0.7))
    axA.annotate("reach 0% at\nevery risk level", xy=(0.5, 62), xytext=(0.5, 20),
                 fontsize=6.6, color=VN_C, ha="center",
                 arrowprops=dict(arrowstyle="->", color=VN_C, lw=0.7))

    # --- (b) same linear engine, gated by language
    xs = np.arange(7)
    for lang, col, lab in [("en", EN_C, "English"), ("vn", VN_C, "Vietnamese")]:
        s = fp[fp.language == lang]
        means = s.groupby("nsel").group_total.mean().reindex(xs)
        slope, intercept, r, pval, se = _st.linregress(s.nsel, s.group_total)
        axB.plot(xs, intercept + slope * xs, "-", color=col, lw=1.3, alpha=0.55, zorder=1)
        axB.plot(xs, means, "o", color=col, ms=5.5, mec="white", mew=0.7, zorder=3, label=lab)
    axB.axhline(120, color=INK2, ls="--", lw=1.0)
    axB.text(6.3, 124, "target (120)", fontsize=6.6, color=INK2, va="bottom", ha="right")
    axB.set_xlim(-0.4, 6.4); axB.set_ylim(0, 265)
    axB.set_xticks(xs)
    axB.set_xlabel("Selfish-persona agents in the group (of 6)")
    axB.set_ylabel("Group contribution (of 240)")
    axB.set_title("(b)  Composition: same engine, gated by language", loc="left", fontsize=9.2)
    axB.yaxis.grid(True, alpha=0.6); axB.set_axisbelow(True)
    axB.legend(loc="upper right", fontsize=7.4, bbox_to_anchor=(1.0, 1.02))
    axB.annotate("Vietnamese starts below target\neven with zero selfish agents",
                 xy=(0.15, 76), xytext=(1.6, 74),
                 fontsize=6.6, color=VN_C, ha="left", va="center",
                 arrowprops=dict(arrowstyle="->", color=VN_C, lw=0.7))

    # --- (c) magnitude comparison: what actually moves gpt-5.4-nano?
    risk_en = fb[(fb.language == "en") & (fb.risk_probability == 0.9)].group_total.mean() - \
              fb[(fb.language == "en") & (fb.risk_probability == 0.1)].group_total.mean()
    risk_vn = fb[(fb.language == "vn") & (fb.risk_probability == 0.9)].group_total.mean() - \
              fb[(fb.language == "vn") & (fb.risk_probability == 0.1)].group_total.mean()
    comp_en = fp[(fp.language == "en") & (fp.nsel == 6)].group_total.mean() - \
              fp[(fp.language == "en") & (fp.nsel == 0)].group_total.mean()
    comp_vn = fp[(fp.language == "vn") & (fp.nsel == 6)].group_total.mean() - \
              fp[(fp.language == "vn") & (fp.nsel == 0)].group_total.mean()
    lang_gap = fb[fb.language == "en"].group_total.mean() - fb[fb.language == "vn"].group_total.mean()

    rows = [
        ("Catastrophe risk\n(English, $p$: 0.1$\\to$0.9)", abs(risk_en), MUTED, "o"),
        ("Catastrophe risk\n(Vietnamese, $p$: 0.1$\\to$0.9)", abs(risk_vn), MUTED, "o"),
        ("Group composition\n(English, 0$\\to$6 selfish)", abs(comp_en), "#d08a1e", "D"),
        ("Group composition\n(Vietnamese, 0$\\to$6 selfish)", abs(comp_vn), "#d08a1e", "D"),
        ("Language\n(English vs Vietnamese, baseline)", abs(lang_gap), VN_C, "s"),
    ]
    y = np.arange(len(rows))
    for i, (lab, val, col, mk) in enumerate(rows):
        axC.plot([0.3, max(val, 0.3)], [i, i], "-", color=MUTED, lw=1.0, zorder=1)
        axC.plot(max(val, 0.3), i, mk, color=col, ms=8, mec="white", mew=0.9, zorder=3)
        axC.text(max(val, 0.3) * 1.15, i, f"{val:.1f}", fontsize=7.2, color=col, va="center")
    axC.set_yticks(y); axC.set_yticklabels([r[0] for r in rows], fontsize=7.6)
    axC.set_xscale("log"); axC.set_xlim(0.3, 400)
    axC.set_xticks([1, 10, 100]); axC.set_xticklabels(["1", "10", "100"]); axC.minorticks_off()
    axC.set_xlabel("Change in group contribution (points of 240, log scale)")
    axC.set_title("(c)  What actually moves a frontier model?", loc="left", fontsize=9.2)
    axC.xaxis.grid(True, alpha=0.6); axC.set_axisbelow(True)
    axC.set_ylim(-0.6, len(rows) - 0.4)

    save(fig, "fig9_frontier")


if __name__ == "__main__":
    print("Generating expansion figures ->", FIG)
    fig_composition()
    fig_frontier()
    print("done.")
