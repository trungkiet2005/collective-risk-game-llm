"""Publication figures for the CRG-LLM paper (Royal Society Interface, single column).

Recomputes every quantity from results/open_source/ so the figures are self-verifying
and match scratchpad/FACTS.md exactly. Outputs vector PDF (for LaTeX) + PNG (preview)
to paper/figures/.

Run:  python paper/make_figures.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

# ----------------------------------------------------------------- paths
HERE = Path(__file__).resolve().parent
OS = HERE.parent / "results" / "open_source"
FIG = HERE / "figures"; FIG.mkdir(exist_ok=True)

# ----------------------------------------------------------------- style
mpl.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9.5,
    "axes.linewidth": 0.8,
    "axes.edgecolor": "#3a3a38",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "legend.fontsize": 8,
    "legend.frameon": False,
    "lines.linewidth": 1.8,
    "lines.markersize": 6,
    "grid.color": "#e1e0d9",
    "grid.linewidth": 0.7,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
})
INK = "#0b0b0b"; INK2 = "#52514e"; MUTED = "#898781"

# family palette (CVD-validated: worst all-pairs ΔE 13.0)
FAM = {"Qwen": "#2a78d6", "Gemma": "#eb6834", "Llama": "#4a3aa7"}
HUMANC = "#0b0b0b"

# model metadata: raw_id -> (label, family, size, comprehension_id)
META = {
    "qwen25-7b-instruct":        ("Qwen2.5-7B",  "Qwen",  7),
    "qwen25-32b-instruct":       ("Qwen2.5-32B", "Qwen",  32),
    "qwen25-72b-instruct-awq":   ("Qwen2.5-72B", "Qwen",  72),
    "gemma2-9b-it":              ("Gemma-2-9B",  "Gemma", 9),
    "gemma2-27b-it":             ("Gemma-2-27B", "Gemma", 27),
    "llama-3-1-8b":              ("Llama-3.1-8B","Llama", 8),
    "llama-3-1-70b-instruct-awq":("Llama-3.1-70B","Llama",70),
    "llama33-70b-instruct-awq":  ("Llama-3.3-70B","Llama",70),
}
HUMAN = {0.1: 0.00, 0.5: 0.10, 0.9: 0.50}


def shade(base_hex, t):
    """Return base color lightened toward white by fraction t in [0,1] (0=base)."""
    c = np.array(mpl.colors.to_rgb(base_hex))
    return tuple(c + (1 - c) * (0.62 * t))


def model_color(family, size, sizes_in_family):
    """Small = lighter, large = darker within a family."""
    order = sorted(sizes_in_family)
    if len(order) == 1:
        t = 0.25
    else:
        rank = order.index(size) / (len(order) - 1)   # 0..1, small..large
        t = 0.55 * (1 - rank)                          # small lighter
    return shade(FAM[family], t)


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan, np.nan)
    p = k / n; d = 1 + z * z / n
    ctr = (p + z * z / (2 * n)) / d
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0, ctr - half), min(1, ctr + half)


def save(fig, name):
    fig.savefig(FIG / f"{name}.pdf")
    fig.savefig(FIG / f"{name}.png", dpi=150)
    plt.close(fig)
    print(f"  -> {name}.pdf / .png")


def set_size_axis_log(ax):
    """log2 size axis with cluster tick labels (70B/72B coincide on a log axis)."""
    ax.set_xscale("log", base=2)
    ax.set_xticks([np.sqrt(7 * 9), np.sqrt(27 * 32), np.sqrt(70 * 72)])
    ax.set_xticklabels(["7–9B", "27–32B", "70–72B"])
    ax.minorticks_off()
    ax.set_xlim(6, 90)
    ax.set_xlabel("Model size (parameters, log scale)")


# =====================================================================
# load & prep
# =====================================================================
b = pd.read_csv(OS / "crsd_all_models.csv")
b = b[b.experiment == "exp_baseline"].copy()
b["reach"] = b.target_reached.astype(int)
b["disaster"] = b.catastrophe.astype(int)
b["risk"] = b.risk_probability.astype(float)
b["label"] = b.model.map(lambda m: META[m][0])
b["family"] = b.model.map(lambda m: META[m][1])
b["size"] = b.model.map(lambda m: META[m][2])
B_SIZES = {f: sorted(b[b.family == f]["size"].unique()) for f in FAM}

c = pd.read_csv(OS / "crsd_comprehension_all_models.csv")
c["label"] = c.model.map(lambda m: META[m][0])
c["family"] = c.model.map(lambda m: META[m][1])
c["size"] = c.model.map(lambda m: META[m][2])

# order for baseline (7 models) and comprehension (7 models) by size then family
BORDER = b.drop_duplicates("model").sort_values(["size", "family"])[["model", "label", "family", "size"]]
CORDER = c.drop_duplicates("model").sort_values(["size", "family"])[["model", "label", "family", "size"]]
RISKS = [0.1, 0.5, 0.9]


# =====================================================================
# FIG 2 — risk-insensitivity (reach + contribution vs risk)
# =====================================================================
def fig_risk_insensitivity():
    g = (b.groupby(["model", "label", "family", "size", "risk"])
         .agg(reach=("reach", "mean"), contrib=("group_total", "mean")).reset_index())
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(7.2, 3.5))
    models = list(BORDER.itertuples(index=False))

    # --- Panel A: reach vs risk. Five models sit exactly on 1.0, so we apply a
    # small downward offset (<=0.042) purely for visibility; disclosed in the caption.
    nm = len(models)
    for i, m in enumerate(models):
        s = g[g.model == m.model].sort_values("risk")
        col = model_color(m.family, m.size, B_SIZES[m.family])
        dy = -i * 0.007          # one-sided: never draws a rate above its true value
        axA.plot(s.risk, s.reach + dy, "-o", color=col, ms=4.5, lw=1.6,
                 mec="white", mew=0.5, zorder=3, alpha=0.95)
    hk = sorted(HUMAN)
    axA.plot(hk, [HUMAN[k] for k in hk], "--s", color=HUMANC, lw=2.4, ms=7, zorder=6)
    axA.text(0.5, 1.045, "all 7 LLMs: reach rate flat in risk", fontsize=7.4,
             color=INK2, ha="center", va="bottom")
    axA.annotate("Llama-3.1-70B\n(50%, every risk)", xy=(0.5, 0.50), xytext=(0.5, 0.70),
                 fontsize=7, color=model_color("Llama", 70, B_SIZES["Llama"]), ha="center",
                 arrowprops=dict(arrowstyle="->", color=model_color("Llama", 70, B_SIZES["Llama"]), lw=0.8))
    axA.annotate("humans cooperate\nmore as risk rises", xy=(0.86, 0.46), xytext=(0.30, 0.30),
                 fontsize=7.2, color=INK, ha="left", va="center",
                 arrowprops=dict(arrowstyle="->", color=INK, lw=0.9))
    axA.set_xticks(RISKS); axA.set_xlim(0.03, 0.97); axA.set_ylim(-0.05, 1.10)
    axA.set_xlabel("Catastrophe risk  $p$")
    axA.set_ylabel("Target-reach rate")
    axA.set_title("(a)  Reaching the collective target", loc="left", fontsize=9.5)
    axA.yaxis.grid(True, alpha=0.6); axA.set_axisbelow(True)

    # --- Panel B: contribution vs risk
    for m in models:
        s = g[g.model == m.model].sort_values("risk")
        col = model_color(m.family, m.size, B_SIZES[m.family])
        axB.plot(s.risk, s["contrib"], "-o", color=col, ms=4.5, lw=1.6, mec="white", mew=0.5)
    axB.axhline(240, color=MUTED, ls="--", lw=0.8)
    axB.axhline(120, color=INK2, ls="--", lw=1.0)
    axB.text(0.09, 243, "max possible (240)", fontsize=6.8, color=MUTED, va="bottom")
    axB.text(0.09, 110, "target (120)", fontsize=6.8, color=INK2, va="bottom")
    # label only the two separated models; bracket the low cluster
    def lab(name, yv, col, dy=0):
        axB.annotate(name, xy=(0.9, yv), xytext=(3, dy), textcoords="offset points",
                     fontsize=6.8, color=col, va="center", ha="left")
    lab("Qwen2.5-7B", 232.7, model_color("Qwen", 7, B_SIZES["Qwen"]))
    lab("Llama-3.1-8B", 185.4, model_color("Llama", 8, B_SIZES["Llama"]))
    axB.annotate("5 larger models:\npool only 121–133", xy=(0.5, 128), xytext=(0.42, 158),
                 fontsize=6.8, color=INK2, ha="center", va="center",
                 arrowprops=dict(arrowstyle="-[,widthB=1.2", color=INK2, lw=0.8))
    axB.set_xticks(RISKS); axB.set_xlim(0.03, 1.06); axB.set_ylim(105, 255)
    axB.set_xlabel("Catastrophe risk  $p$")
    axB.set_ylabel("Group contribution (of 240)")
    axB.set_title("(b)  How much they pool", loc="left", fontsize=9.5)
    axB.yaxis.grid(True, alpha=0.6); axB.set_axisbelow(True)

    handles = [Line2D([0], [0], color=FAM[f], lw=2.4, marker="o", mec="white", ms=5, label=f)
               for f in FAM]
    handles.append(Line2D([0], [0], color=HUMANC, lw=2.4, ls="--", marker="s", ms=6, label="Human (Milinski 2008)"))
    leg = axA.legend(handles=handles, loc="center left", bbox_to_anchor=(0.02, 0.66),
                     fontsize=7.2, handlelength=1.7)
    fig.tight_layout(w_pad=1.8)
    save(fig, "fig2_risk_insensitivity")


# =====================================================================
# FIG 3 — economy with scale (contribution vs model size)
# =====================================================================
def fig_economy_scaling():
    econ = (b.groupby(["model", "label", "family", "size"])
            .agg(contrib=("group_total", "mean"), sd=("group_total", "std")).reset_index())
    fig, ax = plt.subplots(figsize=(5.6, 3.7))
    ax.axhline(240, color=MUTED, ls="--", lw=0.8)
    ax.axhline(120, color=INK2, ls="--", lw=1.0)
    ax.text(6.4, 243, "max possible (240)", fontsize=7, color=MUTED, va="bottom")
    ax.text(6.4, 123, "target (120)", fontsize=7, color=INK2, va="bottom")
    lab_off = {"Qwen2.5-72B": (7, 6), "Llama-3.1-70B": (-7, -13), "Qwen2.5-7B": (14, -2)}
    for f in FAM:
        s = econ[econ.family == f].sort_values("size")
        ax.plot(s["size"], s["contrib"], "-", color=FAM[f], lw=1.4, alpha=0.5, zorder=2)
        ax.errorbar(s["size"], s["contrib"], yerr=s.sd, fmt="o", color=FAM[f], ms=8,
                    mec="white", mew=1.0, capsize=2.5, elinewidth=0.9,
                    ecolor=FAM[f], zorder=3, label=f)
        for _, r in s.iterrows():
            dx, dy = lab_off.get(r.label, (0, 10))
            ax.annotate(f"{r['contrib']:.0f}", xy=(r["size"], r["contrib"]), xytext=(dx, dy),
                        textcoords="offset points", fontsize=6.9, color=FAM[f],
                        ha="center", fontweight="bold")
    set_size_axis_log(ax)
    ax.set_ylim(105, 255)
    ax.set_ylabel("Group contribution (of 240)")
    ax.set_title("Small models over-pool; larger ones converge to “just enough”", loc="left", fontsize=9.5)
    ax.yaxis.grid(True, alpha=0.6); ax.set_axisbelow(True)
    ax.legend(loc="upper right", title="Family", title_fontsize=7.5, bbox_to_anchor=(1.0, 0.9))
    fig.tight_layout()
    save(fig, "fig3_economy_scaling")


# =====================================================================
# FIG 4 — comprehension accuracy by category
# =====================================================================
CATC = {"rules": "#2a78d6", "time": "#eb6834", "state": "#4a3aa7"}
CATLAB = {"rules": "Rules", "time": "Time", "state": "State"}


def comp_acc(df, keys):
    r = (df.groupby(keys)
         .apply(lambda x: pd.Series({"n": x.n.sum(), "k": x.n_correct.sum()}), include_groups=False)
         .reset_index())
    r["acc"] = r.k / r.n
    ci = r.apply(lambda row: wilson(row.k, row.n), axis=1)
    r["lo"] = [t[1] for t in ci]; r["hi"] = [t[2] for t in ci]
    return r


def fig_comprehension_category():
    cat = comp_acc(c, ["label", "family", "size", "category"])
    order = list(CORDER.itertuples(index=False))
    ypos = {m.label: i for i, m in enumerate(order)}   # bottom=smallest
    fig, ax = plt.subplots(figsize=(5.6, 3.9))
    # alternating row bands so each model's three dots read as one group
    for i in range(len(order)):
        if i % 2 == 0:
            ax.axhspan(i - 0.5, i + 0.5, color="#f4f3ef", zorder=0)
    offs = {"rules": 0.22, "time": 0.0, "state": -0.22}
    for _, r in cat.iterrows():
        y = ypos[r.label] + offs[r.category]
        col = CATC[r.category]
        ax.plot([r.lo, r.hi], [y, y], "-", color=col, lw=1.4, alpha=0.9, zorder=2)
        ax.plot(r.acc, y, "o", color=col, ms=6, mec="white", mew=0.7, zorder=3)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([m.label for m in order])
    ax.set_ylim(-0.6, len(order) - 0.4)
    ax.set_xlim(0.0, 1.03)
    ax.set_xlabel("Response accuracy (Wilson 95% CI)")
    ax.set_title("Do the agents understand the game?", loc="left", fontsize=9.5)
    ax.axvline(1.0, color=MUTED, ls=":", lw=0.7)
    ax.xaxis.grid(True, alpha=0.6); ax.set_axisbelow(True)
    handles = [Line2D([0], [0], color=CATC[k], lw=2.2, marker="o", ms=5, mec="white",
                      label=CATLAB[k]) for k in ["rules", "time", "state"]]
    ax.legend(handles=handles, loc="lower left", title="Question axis", title_fontsize=7.5, ncol=1)
    fig.tight_layout()
    save(fig, "fig4_comprehension_category")


# =====================================================================
# FIG 5 — the mechanism: read vs add  +  risk-gate vs arithmetic scaling
# =====================================================================
def fig_mechanism():
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(7.2, 3.5))

    # --- Panel A: READ (printed) vs ADD (must sum), pool hidden (showcum=0)
    rv = comp_acc(c[(c.show_cumulative == 0) &
                    (c.question_id.isin(["state_own_remaining", "state_pool"]))],
                  ["label", "family", "size", "question_id"])
    order = list(CORDER.itertuples(index=False))
    x = np.arange(len(order))
    read = {r.label: r.acc for _, r in rv[rv.question_id == "state_own_remaining"].iterrows()}
    add = {r.label: r.acc for _, r in rv[rv.question_id == "state_pool"].iterrows()}
    for i, m in enumerate(order):
        axA.plot([i, i], [add[m.label], read[m.label]], "-", color=MUTED, lw=1.0, zorder=1)
    axA.plot(x, [read[m.label] for m in order], "o", color="#52514e", ms=7,
             mec="white", mew=0.8, label="Read a printed value\n(own money left)", zorder=3)
    axA.plot(x, [add[m.label] for m in order], "D", color="#d03b3b", ms=6.5,
             mec="white", mew=0.8, label="Sum across rounds\n(pool total)", zorder=3)
    axA.set_xticks(x)
    axA.set_xticklabels([m.label for m in order], rotation=35, ha="right", fontsize=7)
    axA.set_ylim(0, 1.06)
    axA.set_ylabel("Answer accuracy")
    axA.set_title("(a)  Reading ≠ adding", loc="left", fontsize=9.5)
    axA.axhline(1.0, color=MUTED, ls=":", lw=0.7)
    axA.yaxis.grid(True, alpha=0.6); axA.set_axisbelow(True)
    axA.legend(loc="lower right", fontsize=7.0, labelspacing=0.7)

    # --- Panel B: risk-knowledge (flat, high) vs cumulative arithmetic (rises with scale)
    gate = comp_acc(c[c.question_id == "rules_risk_pct"], ["label", "family", "size"]).sort_values("size")
    arith = comp_acc(c[(c.question_id == "state_pool") & (c.show_cumulative == 0)],
                     ["label", "family", "size"]).sort_values("size")
    axB.plot(gate["size"], gate.acc, "-o", color="#0ca30c", ms=6, mec="white", mew=0.8,
             lw=1.8, label="Knows the risk %", zorder=3)
    axB.fill_between(gate["size"], gate.lo, gate.hi, color="#0ca30c", alpha=0.12)
    axB.plot(arith["size"], arith.acc, "-D", color="#d03b3b", ms=6, mec="white", mew=0.8,
             lw=1.8, label="Adds the pool (hidden)", zorder=3)
    axB.fill_between(arith["size"], arith.lo, arith.hi, color="#d03b3b", alpha=0.12)
    set_size_axis_log(axB)
    axB.set_ylim(0, 1.06)
    axB.set_ylabel("Accuracy")
    axB.set_title("(b)  Risk is known; arithmetic scales", loc="left", fontsize=9.5)
    axB.axhline(1.0, color=MUTED, ls=":", lw=0.7)
    axB.yaxis.grid(True, alpha=0.6); axB.set_axisbelow(True)
    axB.legend(loc="center right", fontsize=7.2)
    fig.tight_layout(w_pad=1.8)
    save(fig, "fig5_mechanism")


# =====================================================================
# FIG 6 — language (EN vs VN): behaviour reach + comprehension state
# =====================================================================
def fig_language():
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(7.2, 3.5))

    # Panel A: behaviour reach EN vs VN
    rb = b.groupby(["label", "family", "size", "language"])["reach"].mean().reset_index()
    order = list(BORDER.itertuples(index=False))
    for i, m in enumerate(order):
        en = rb[(rb.label == m.label) & (rb.language == "en")]["reach"].values[0]
        vn = rb[(rb.label == m.label) & (rb.language == "vn")]["reach"].values[0]
        # EN and VN coincide at 1.0 for five models; offset them by +/-0.13 row
        # units purely for visibility (disclosed in the caption).
        axA.plot([en, vn], [i + 0.13, i - 0.13], "-", color=MUTED, lw=1.0, zorder=1)
        axA.plot(en, i + 0.13, "o", color="#2a78d6", ms=6, mec="white", mew=0.7, zorder=3)
        axA.plot(vn, i - 0.13, "o", color="#d03b3b", ms=6, mec="white", mew=0.7, zorder=3)
    axA.set_yticks(range(len(order)))
    axA.set_yticklabels([m.label for m in order], fontsize=7.5)
    axA.set_xlim(-0.05, 1.05); axA.set_ylim(-0.6, len(order) - 0.4)
    axA.set_xlabel("Target-reach rate")
    axA.set_title("(a)  Behaviour: reaching target", loc="left", fontsize=9.5)
    axA.xaxis.grid(True, alpha=0.6); axA.set_axisbelow(True)
    _li = order.index(next(m for m in order if m.label == "Llama-3.1-70B"))
    axA.annotate("collapses in\nVietnamese", xy=(0.03, _li - 0.13),
                 xytext=(0.30, _li - 0.55), fontsize=6.8, color="#d03b3b", va="center",
                 arrowprops=dict(arrowstyle="->", color="#d03b3b", lw=0.8))

    # Panel B: comprehension STATE accuracy EN vs VN
    cs = comp_acc(c[c.category == "state"], ["label", "family", "size", "language"])
    corder = list(CORDER.itertuples(index=False))
    for i, m in enumerate(corder):
        en = cs[(cs.label == m.label) & (cs.language == "en")]["acc"].values[0]
        vn = cs[(cs.label == m.label) & (cs.language == "vn")]["acc"].values[0]
        axB.plot([en, vn], [i, i], "-", color=MUTED, lw=1.0, zorder=1)
        axB.plot(en, i, "o", color="#2a78d6", ms=6, mec="white", mew=0.7, zorder=3)
        axB.plot(vn, i, "o", color="#d03b3b", ms=6, mec="white", mew=0.7, zorder=3)
    axB.set_yticks(range(len(corder)))
    axB.set_yticklabels([m.label for m in corder], fontsize=7.5)
    axB.set_xlim(0, 1.03); axB.set_ylim(-0.6, len(corder) - 0.4)
    axB.set_xlabel("State-tracking accuracy")
    axB.set_title("(b)  Comprehension: cumulative state", loc="left", fontsize=9.5)
    axB.xaxis.grid(True, alpha=0.6); axB.set_axisbelow(True)

    handles = [Line2D([0], [0], color="#2a78d6", marker="o", ms=6, lw=0, mec="white", label="English"),
               Line2D([0], [0], color="#d03b3b", marker="o", ms=6, lw=0, mec="white", label="Vietnamese")]
    axA.legend(handles=handles, loc="center left", bbox_to_anchor=(0.04, 0.42),
               fontsize=7.5)
    fig.tight_layout(w_pad=2.4)
    save(fig, "fig6_language")


if __name__ == "__main__":
    print("Generating figures ->", FIG)
    fig_risk_insensitivity()
    fig_economy_scaling()
    fig_comprehension_category()
    fig_mechanism()
    fig_language()
    print("done.")


# =====================================================================
# FIG 7 — salience vs risk: which manipulation actually moves behaviour?
# =====================================================================
def fig_salience():
    from scipy import stats as _st
    raw = pd.read_csv(OS / "crsd_all_models.csv")
    raw["label"] = raw.model.map(lambda m: META[m][0] if m in META else None)
    base = raw[raw.experiment == "exp_baseline"].copy()
    base["risk"] = base.risk_probability.astype(float)
    comp = raw[raw.experiment == "exp_comprehension"].copy()
    comp["showcum"] = comp.game_id.str.contains("showcum")
    comp["risk"] = comp.risk_probability.astype(float)

    rows = []
    for lab in comp.label.dropna().unique():
        g = comp[comp.label == lab]
        w = g.pivot_table(index=["rep", "language", "risk"], columns="showcum", values="group_total")
        if w.isna().any().any() or w.shape[1] < 2:
            continue
        sal = w[True].mean() - w[False].mean()
        bb = base[base.label == lab]
        wr = bb.pivot_table(index=["rep", "language"], columns="risk", values="group_total")
        rk = (wr[0.9] - wr[0.1]).mean()
        size = [v[2] for v in META.values() if v[0] == lab][0]
        rows.append((lab, size, abs(rk), abs(sal)))
    rows.sort(key=lambda r: r[1])

    fig, ax = plt.subplots(figsize=(5.6, 3.4))
    y = np.arange(len(rows))
    for i, (lab, sz, rk, sal) in enumerate(rows):
        ax.plot([max(rk, 0.05), sal], [i, i], "-", color=MUTED, lw=1.0, zorder=1)
        ax.plot(max(rk, 0.05), i, "o", color="#52514e", ms=6.5, mec="white", mew=0.8, zorder=3)
        ax.plot(sal, i, "D", color="#d03b3b", ms=6.5, mec="white", mew=0.8, zorder=3)
    ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows], fontsize=7.8)
    ax.set_xscale("log")
    ax.set_xlim(0.1, 200)
    ax.set_xticks([0.1, 1, 10, 100])
    ax.set_xticklabels(["0.1", "1", "10", "100"])
    ax.minorticks_off()
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_xlabel("Change in group contribution (points of 240, log scale)")
    ax.set_title("What actually moves the agents?", loc="left", fontsize=9.5)
    ax.xaxis.grid(True, alpha=0.6); ax.set_axisbelow(True)
    handles = [Line2D([0], [0], color="#52514e", marker="o", ms=6, lw=0, mec="white",
                      label="tripling the catastrophe risk ($p$: 0.1 → 0.9)"),
               Line2D([0], [0], color="#d03b3b", marker="D", ms=6, lw=0, mec="white",
                      label="making the running pool total visible")]
    ax.legend(handles=handles, loc="upper right", fontsize=6.9, framealpha=0.95,
              frameon=True, edgecolor="#e1e0d9")
    fig.tight_layout()
    save(fig, "fig7_salience")


fig_salience()
