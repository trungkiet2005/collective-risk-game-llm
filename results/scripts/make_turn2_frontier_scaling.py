"""LF — đặt model frontier ĐÓNG (Gemini-3.1-flash-lite) vào THANG SCALING open-source.
So sánh trực tiếp: 3 họ mở phóng to hội tụ ~120; frontier đóng đáp đúng vùng đó.
Palette/style khớp make_turn2_figs.py. Chạy trong results/.
Xuất slides/turn_2/figs/LF_scaling_frontier.png."""
from pathlib import Path
import os
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

R = Path(__file__).resolve().parent.parent   # results/ (script dưới results/scripts/)
OUT = R.parent / "slides" / "turn_2" / "figs"; OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 150, "font.size": 13,
    "axes.titlesize": 15, "axes.labelsize": 13, "legend.fontsize": 11,
    "xtick.labelsize": 11, "ytick.labelsize": 11, "axes.grid": True,
    "grid.alpha": 0.22, "axes.spines.top": False, "axes.spines.right": False,
    "font.family": "DejaVu Sans", "axes.edgecolor": "#52646b", "text.color": "#264653",
    "axes.labelcolor": "#264653", "xtick.color": "#264653", "ytick.color": "#264653",
})
DARK, ACC, TEAL = "#264653", "#E76F51", "#2A9D8F"
FRONT = "#6A4C93"                                   # frontier đóng (Gemini) — nổi bật
COL = {"qwen25-7b-instruct": "#7FB8DE", "qwen25-32b-instruct": "#2C6E9B", "qwen25-72b-instruct-awq": "#0B3C5D",
       "gemma2-9b-it": "#83C5BE", "gemma2-27b-it": "#14746F",
       "llama-3-1-8b": "#F0987A", "llama-3-1-70b-instruct-awq": "#B23A22"}
LBL = {"qwen25-7b-instruct": "Qwen-7B", "qwen25-32b-instruct": "Qwen-32B", "qwen25-72b-instruct-awq": "Qwen-72B",
       "gemma2-9b-it": "Gemma-9B", "gemma2-27b-it": "Gemma-27B",
       "llama-3-1-8b": "Llama-8B", "llama-3-1-70b-instruct-awq": "Llama-70B"}
PAR = {"qwen25-7b-instruct": 7, "qwen25-32b-instruct": 32, "qwen25-72b-instruct-awq": 72,
       "gemma2-9b-it": 9, "gemma2-27b-it": 27, "llama-3-1-8b": 8, "llama-3-1-70b-instruct-awq": 70}
famcol = {"Qwen": "#2C6E9B", "Gemma": "#14746F", "Llama": "#B23A22"}

# ---- data: open scaling (giống make_turn2_figs) + frontier Gemini --------------
paths = ["data/baseline/crsd_results/crsd_all_models.csv",
         "extracted_large/crsd_results/crsd_all_models.csv",
         "extracted_new/llama70/crsd_results/crsd_all_models.csv",
         "extracted_new/qwen72/crsd_results/crsd_all_models.csv"]
A = pd.concat([pd.read_csv(R / p) for p in paths if os.path.exists(R / p)], ignore_index=True)
gt = A.groupby("model").group_total.mean()
fr = pd.read_csv(R / "frontier/google-gemini-3.1-flash-lite-preview/exp_baseline/games.csv")
gem = fr.group_total.mean()

fig, ax = plt.subplots(figsize=(9.4, 5.0))

# vùng "model LỚN hội tụ" — mọi model >=27B (mở) + frontier đóng rơi vào đây
ax.axhspan(118, 135, color=TEAL, alpha=0.10, zorder=0)

# 3 họ mở phóng to
fams = [("Qwen", ["qwen25-7b-instruct", "qwen25-32b-instruct", "qwen25-72b-instruct-awq"]),
        ("Gemma", ["gemma2-9b-it", "gemma2-27b-it"]),
        ("Llama", ["llama-3-1-8b", "llama-3-1-70b-instruct-awq"])]
for fam, ms in fams:
    xs = [PAR[m] for m in ms]; ys = [gt[m] for m in ms]
    ax.plot(xs, ys, "-", color=famcol[fam], lw=2.4, zorder=2, alpha=.85)
    for m in ms:
        ax.scatter(PAR[m], gt[m], s=140, color=COL[m], zorder=3, edgecolor="white", lw=1.5)
lab = {"qwen25-7b-instruct": (0, 12, "bottom"), "qwen25-32b-instruct": (14, 11, "bottom"),
       "qwen25-72b-instruct-awq": (0, 11, "bottom"), "gemma2-9b-it": (0, 12, "bottom"),
       "gemma2-27b-it": (-13, -16, "top"), "llama-3-1-8b": (0, 11, "bottom"),
       "llama-3-1-70b-instruct-awq": (2, -17, "top")}
for m in PAR:
    dx, dy, va = lab[m]
    ax.annotate(f"{LBL[m]}\n{gt[m]:.0f}", xy=(PAR[m], gt[m]), xytext=(dx, dy),
                textcoords="offset points", ha="center", va=va, fontsize=9, color=COL[m], fontweight="bold")

ax.axhline(120, color=DARK, ls=":", lw=1.8); ax.text(7, 123, "mục tiêu 120", color=DARK, fontsize=10)

# ---- frontier ĐÓNG: khu riêng bên phải (không nằm trên trục #tham số của model mở)
XG = 150
ax.axvline(102, color="#c4ccce", ls="-", lw=1.2, zorder=1)
ax.text(98, 246, "mở / tự host", color="#8a989e", fontsize=9.5, ha="right", va="top")
ax.text(107, 246, "đóng / frontier", color=FRONT, fontsize=9.5, ha="left", va="top", fontweight="bold")
ax.scatter(XG, gem, s=300, marker="D", color=FRONT, zorder=5, edgecolor="white", lw=1.8)
ax.annotate(f"Gemini flash-lite\nĐÓNG · {gem:.0f}", xy=(XG, gem), xytext=(0, 16),
            textcoords="offset points", ha="center", va="bottom", color=FRONT,
            fontsize=10, fontweight="bold")
# mũi tên từ cụm model lớn (mở) sang frontier đóng → cùng một mức "vừa đủ"
ax.annotate("", xy=(XG*0.83, gem), xytext=(74, 121.3),
            arrowprops=dict(arrowstyle="->", color=FRONT, lw=1.7,
                            connectionstyle="arc3,rad=-0.30"), zorder=4)

ax.set_xscale("log")
ax.set_xticks([7, 32, 72, XG]); ax.set_xticklabels(["7-9B", "27-32B", "70-72B", "frontier\nđóng"])
ax.set_xlim(6, 230); ax.set_ylim(105, 250)
ax.set_xlabel("Số tham số (log)  ·  model mở phóng to  →  frontier đóng")
ax.set_ylabel("Tổng đóng góp / game (trên 240)")
ax.set_title("Frontier đóng đáp đúng vùng “vừa đủ” của model lớn mở")
ax.grid(axis="x", visible=False)
fig.tight_layout(); fig.savefig(OUT / "LF_scaling_frontier.png", bbox_inches="tight", facecolor="white")
plt.close(fig)
print("open group_total:", {LBL[m]: round(gt[m], 1) for m in PAR})
print("gemini group_total:", round(gem, 1))
print("-> LF_scaling_frontier.png saved to", OUT)
