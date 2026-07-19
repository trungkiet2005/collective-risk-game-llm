"""Turn-2 add-on figure — FRONTIER closed model (gemini-3.1-flash-lite) vs the
open-source arm + human. Palette/style khớp make_turn2_figs.py. Chạy trong results/.
Xuất slides/turn_2/figs/F1_frontier.png."""
from pathlib import Path
import glob
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

R = Path(__file__).resolve().parent.parent   # results/ (script dưới results/scripts/)
OUT = R.parent / "slides" / "turn_2" / "figs"; OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 150, "font.size": 13,
    "axes.titlesize": 14, "axes.labelsize": 13, "legend.fontsize": 10,
    "xtick.labelsize": 11, "ytick.labelsize": 11, "axes.grid": True,
    "grid.alpha": 0.22, "axes.spines.top": False, "axes.spines.right": False,
    "font.family": "DejaVu Sans", "axes.edgecolor": "#52646b", "text.color": "#264653",
    "axes.labelcolor": "#264653", "xtick.color": "#264653", "ytick.color": "#264653",
})
DARK, ACC, TEAL = "#264653", "#E76F51", "#2A9D8F"
FRONT = "#6A4C93"                                   # frontier closed model (Gemini) — nổi bật
HUMAN = {0.9: 0.50, 0.5: 0.10, 0.1: 0.00}
OSCOL = {"qwen25-7b-instruct": "#7FB8DE", "llama-3-1-8b": "#F0987A", "gemma2-9b-it": "#83C5BE"}
OSLBL = {"qwen25-7b-instruct": "Qwen-7B", "llama-3-1-8b": "Llama-8B", "gemma2-9b-it": "Gemma-9B"}
OSM = list(OSCOL)

# ---- data --------------------------------------------------------------------
FRONT_CSV = R / "frontier/google-gemini-3.1-flash-lite-preview/exp_baseline/games.csv"
fr = pd.read_csv(FRONT_CSV)
os_ = pd.concat([pd.read_csv(f) for f in glob.glob(
    str(R / "data/baseline/crsd_results/*/exp_baseline/games.csv"))], ignore_index=True)
for d in (fr, os_):
    d["reach"] = d.target_reached.astype(int); d["risk"] = d.risk_probability.astype(float)

risks = [0.9, 0.5, 0.1]
fr_reach = fr.groupby("risk").reach.mean()
os_reach = os_.groupby(["model", "risk"]).reach.mean()
fr_gt = fr.group_total.mean()
os_gt = os_.groupby("model").group_total.mean()

fig, (axL, axR) = plt.subplots(1, 2, figsize=(11.4, 4.7))

# ---- Panel A: reach vs risk — Gemini phẳng 100% cùng mọi model mở; người dốc xuống
for m in OSM:
    axL.plot(risks, [os_reach[(m, k)] for k in risks], "-", color=OSCOL[m], lw=1.6,
             ms=6, marker="o", alpha=0.55)
axL.plot(risks, [fr_reach[k] for k in risks], "o-", color=FRONT, lw=3.2, ms=11,
         label="Gemini-3.1-flash-lite  (frontier, đóng)", zorder=5,
         markeredgecolor="white", markeredgewidth=1.4)
axL.plot(risks, [HUMAN[k] for k in risks], "s--", color=DARK, lw=2.4, ms=8,
         label="Người (Milinski 2008)")
axL.plot([], [], "o-", color="#9bb0b8", lw=1.6, label="3 model mở (Qwen/Llama/Gemma)")
axL.text(0.5, 1.05, "mọi LLM (mở + frontier): PHẲNG 100%", ha="center", va="bottom",
         color=DARK, fontsize=10.5, fontweight="bold")
axL.set_xlabel("Xác suất thảm hoạ (rủi ro)"); axL.set_ylabel("Tỉ lệ đạt mục tiêu")
axL.set_title("Frontier đóng cũng PHỚT LỜ rủi ro")
axL.set_ylim(-0.05, 1.16); axL.set_xticks(risks); axL.invert_xaxis()
axL.legend(loc="center right", frameon=False, fontsize=9)

# ---- Panel B: contribution — Gemini ~120 (vừa đủ), như model lớn; không đóng dư
bmods = OSM + ["__front__"]
vals = [os_gt[m] for m in OSM] + [fr_gt]
cols = [OSCOL[m] for m in OSM] + [FRONT]
labs = [OSLBL[m] for m in OSM] + ["Gemini\nflash-lite"]
x = np.arange(len(bmods))
axR.bar(x, vals, 0.62, color=cols, edgecolor="white", lw=1.2)
axR.axhline(120, color=DARK, ls=":", lw=1.8); axR.text(-0.45, 126, "mục tiêu 120",
            color=DARK, fontsize=9.5, ha="left", va="bottom")
for xi, v in zip(x, vals):
    axR.text(xi, v + 5, f"{v:.0f}", ha="center", fontsize=11, fontweight="bold",
             color=FRONT if xi == len(x)-1 else DARK)
axR.set_xticks(x); axR.set_xticklabels(labs, fontsize=10)
axR.set_ylabel("Tổng đóng góp / game (trên 240)"); axR.set_ylim(0, 260)
axR.set_title("Đóng “vừa đủ” ~120 — kinh tế như model lớn")
axR.grid(axis="x", visible=False)

fig.suptitle("Model frontier đóng (Gemini, Google) — cùng baseline: phớt lờ rủi ro, đóng vừa đủ, EN=VN",
             y=1.02, fontsize=13)
fig.tight_layout(); fig.savefig(OUT / "F1_frontier.png", bbox_inches="tight", facecolor="white")
plt.close(fig)

# in số để dán takeaway slide
print("gemini reach by risk:", {k: round(fr_reach[k], 2) for k in risks})
print("gemini group_total:", round(fr_gt, 1))
print("gemini EN vs VN reach:", fr.groupby("language").reach.mean().round(2).to_dict())
print("gemini EN vs VN group_total:", fr.groupby("language").group_total.mean().round(1).to_dict())
print("open-source group_total:", {OSLBL[m]: round(os_gt[m], 1) for m in OSM})
print("-> F1_frontier.png saved to", OUT)
