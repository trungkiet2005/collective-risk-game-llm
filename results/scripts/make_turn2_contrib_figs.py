"""Turn-2 add-on — "Đóng vừa đủ ~120" bar chart cho FULL model set
(7 model mở: Qwen 7/32/72B, Llama 8/70B, Gemma 9/27B + Gemini frontier),
tách theo ngôn ngữ.

Xuất 3 hình vào slides/turn_2/figs/:
  F2_contrib_all.png  — gộp cả EN + VN (bức tổng quát, giống hình gốc)
  F2_contrib_vn.png   — chỉ tiếng Việt
  F2_contrib_en.png   — chỉ tiếng Anh

Màu: mỗi họ một tông (Qwen xanh dương, Llama coral, Gemma teal); trong họ
nhạt = nhỏ, đậm = lớn. Gemini frontier (đóng) = tím. Chạy trong results/.
"""
from pathlib import Path
import os
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
DARK = "#264653"
FRONT_KEY = "__front__"

# thứ tự trục X: theo họ, trong họ nhỏ→lớn; Gemini frontier ở cuối
ORDER = ["qwen25-7b-instruct", "qwen25-32b-instruct", "qwen25-72b-instruct-awq",
         "llama-3-1-8b", "llama-3-1-70b-instruct-awq",
         "gemma2-9b-it", "gemma2-27b-it", FRONT_KEY]
COL = {
    "qwen25-7b-instruct": "#9CC3E0", "qwen25-32b-instruct": "#5B9BD5", "qwen25-72b-instruct-awq": "#2C6E9B",
    "llama-3-1-8b": "#F0987A", "llama-3-1-70b-instruct-awq": "#B23A22",
    "gemma2-9b-it": "#83C5BE", "gemma2-27b-it": "#14746F",
    FRONT_KEY: "#6A4C93",
}
LBL = {
    "qwen25-7b-instruct": "Qwen\n7B", "qwen25-32b-instruct": "Qwen\n32B", "qwen25-72b-instruct-awq": "Qwen\n72B",
    "llama-3-1-8b": "Llama\n8B", "llama-3-1-70b-instruct-awq": "Llama\n70B",
    "gemma2-9b-it": "Gemma\n9B", "gemma2-27b-it": "Gemma\n27B",
    FRONT_KEY: "Gemini\nflash-lite",
}
COLS = [COL[m] for m in ORDER]
LABS = [LBL[m] for m in ORDER]

# ---- data --------------------------------------------------------------------
OS_PATHS = [
    R / "data/baseline/crsd_results/crsd_all_models.csv",          # Qwen-7B, Llama-8B, Gemma-9B
    R / "extracted_large/crsd_results/crsd_all_models.csv",        # Qwen-32B, Gemma-27B, (Llama-70B?)
    R / "extracted_new/llama70/crsd_results/crsd_all_models.csv",  # Llama-70B
    R / "extracted_new/qwen72/crsd_results/crsd_all_models.csv",   # Qwen-72B
]
os_ = pd.concat([pd.read_csv(p) for p in OS_PATHS if os.path.exists(p)], ignore_index=True)
os_ = os_.drop_duplicates(subset=["model", "language", "game_id"])
fr = pd.read_csv(R / "frontier/google-gemini-3.1-flash-lite-preview/exp_baseline/games.csv")

OSM = [m for m in ORDER if m != FRONT_KEY]


def contrib_by(lang):
    """group_total trung bình / model cho một tập ngôn ngữ (None = gộp cả hai)."""
    o, f = os_, fr
    if lang is not None:
        o, f = o[o.language == lang], f[f.language == lang]
    gt = o.groupby("model").group_total.mean()
    return [gt[m] for m in OSM] + [f.group_total.mean()]


def draw(vals, title, fname, subtitle=None):
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    x = np.arange(len(ORDER))
    ax.bar(x, vals, 0.66, color=COLS, edgecolor="white", lw=1.2)
    ax.axhline(120, color=DARK, ls=":", lw=1.8)
    ax.text(-0.55, 126, "mục tiêu 120", color=DARK, fontsize=9.5, ha="left", va="bottom")
    for xi, v in zip(x, vals):
        ax.text(xi, v + 4, f"{v:.0f}", ha="center", fontsize=10.5, fontweight="bold",
                color=COL[FRONT_KEY] if xi == len(x) - 1 else DARK)
    ax.set_xticks(x); ax.set_xticklabels(LABS, fontsize=9.5)
    ax.set_ylabel("Tổng đóng góp / game (trên 240)")
    ax.set_ylim(0, 260)
    # tiêu đề phụ (nhỏ, xám) sát trên khung; tiêu đề chính nằm trên nữa
    ax.set_title(subtitle or "", fontsize=10, color="#52646b", pad=8)
    fig.suptitle(title, fontsize=14, y=1.0, va="bottom", color=DARK)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(OUT / fname, bbox_inches="tight", facecolor="white")
    plt.close(fig)


draw(contrib_by(None), "Đóng “vừa đủ” ~120 — chỉ hai model NHỎ đóng dư",
     "F2_contrib_all.png", subtitle="Gộp cả tiếng Anh + tiếng Việt")
draw(contrib_by("vn"), "Chỉ tiếng Việt (VN)",
     "F2_contrib_vn.png", subtitle="Đóng góp mỗi game")
draw(contrib_by("en"), "Chỉ tiếng Anh (EN)",
     "F2_contrib_en.png", subtitle="Đóng góp mỗi game")

# in số để dán takeaway slide
lab = {m: LBL[m].replace("\n", "-") for m in ORDER}
for tag, lang in [("ALL", None), ("VN", "vn"), ("EN", "en")]:
    vals = contrib_by(lang)
    print(tag, {lab[k]: round(v, 1) for k, v in zip(ORDER, vals)})
print("-> F2_contrib_{all,vn,en}.png saved to", OUT)
