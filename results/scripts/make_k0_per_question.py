"""K0 — accuracy từng câu trong bộ 20 câu đọc-hiểu (bản sạch, nhãn tiếng Việt).
Gộp mọi ngôn ngữ / mức rủi ro / show_cumulative → 1 accuracy cho mỗi (câu × model).
Ghép cạnh slide 'Bộ câu hỏi thật — 20 câu'."""
from pathlib import Path
import glob
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

R = Path(__file__).resolve().parent.parent   # results/ (script dưới results/scripts/)
OUT = Path(__file__).resolve().parents[2] / "slides" / "week2" / "figs"; OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 150, "font.size": 13,
    "axes.titlesize": 15, "axes.labelsize": 13, "legend.fontsize": 11,
    "xtick.labelsize": 11, "ytick.labelsize": 11, "axes.grid": True,
    "grid.alpha": 0.22, "axes.spines.top": False, "axes.spines.right": False,
    "font.family": "DejaVu Sans", "axes.edgecolor": "#52646b", "text.color": "#264653",
    "axes.labelcolor": "#264653", "xtick.color": "#264653", "ytick.color": "#264653",
})
DARK, ACC, TEAL = "#264653", "#E76F51", "#2A9D8F"
CMODELS = ["qwen25-7b-instruct", "gemma2-9b-it", "llama-3-1-8b"]
CCOL = {"qwen25-7b-instruct": "#1B4965", "gemma2-9b-it": "#2A9D8F", "llama-3-1-8b": "#E76F51"}
CLBL = {"qwen25-7b-instruct": "Qwen2.5-7B", "gemma2-9b-it": "Gemma-2-9B", "llama-3-1-8b": "Llama-3.1-8B"}

# thứ tự + nhãn tiếng Việt ngắn, khớp slide "Bộ câu hỏi thật"; (r) đọc thẳng, (t) tự tính
QORDER = [
    ("rules", "rules_actions",           "Mức đóng được phép mỗi vòng", "r"),
    ("rules", "rules_endowment",          "Vốn ban đầu mỗi người", "r"),
    ("rules", "rules_target",             "Mục tiêu chung cả game", "r"),
    ("rules", "rules_n_rounds",           "Game dài bao nhiêu vòng", "r"),
    ("rules", "rules_risk_pct",           "Xác suất mất hết nếu trượt", "r"),
    ("rules", "rules_payoff_disaster",    "Còn lại nếu gặp thảm hoạ", "r"),
    ("rules", "rules_max_contrib",        "Mức đóng tối đa / vòng", "r"),
    ("rules", "rules_min_contrib",        "Mức đóng tối thiểu / vòng", "r"),
    ("time",  "time_round",               "Đang ở vòng thứ mấy", "r"),
    ("time",  "time_action_i",            "Vòng i: ghế Px đóng bao nhiêu", "r"),
    ("time",  "time_own_action_i",        "Vòng i: chính bạn đóng bao nhiêu", "r"),
    ("time",  "time_round_total_i",       "Vòng i: cả 6 người đóng tổng", "t"),
    ("state", "state_pool",               "Tổng quỹ chung đến giờ", "t"),
    ("state", "state_remaining_to_target","Còn thiếu bao nhiêu để đạt 120", "t"),
    ("state", "state_X_total",            "Ghế Px đã đóng tổng cộng", "t"),
    ("state", "state_own_total",          "Chính bạn đã đóng tổng cộng", "t"),
    ("state", "state_own_remaining",      "Vốn bạn còn chưa đóng", "r"),
    ("state", "state_count_p",            "Ghế Px đóng đúng mức 4 mấy lần", "t"),
    ("state", "state_rounds_left",        "Còn mấy vòng nữa (kể cả vòng này)", "t"),
    ("state", "state_target_reached",     "Nhóm đã đạt mục tiêu chưa", "t"),
]
CATLBL = {"rules": "RULES · luật tĩnh", "time": "TIME · tra lịch sử", "state": "STATE · cộng dồn"}

frames = [pd.read_csv(f) for f in
          glob.glob(str(R / "extracted_comp/crsd_results/*/exp_comprehension/comprehension_summary.csv"))]
C = pd.concat(frames, ignore_index=True)

def acc(model, qid):
    d = C[(C.model == model) & (C.question_id == qid)]
    return d.n_correct.sum() / d.n.sum() if d.n.sum() else np.nan

n = len(QORDER)
ypos = np.arange(n)[::-1]                       # câu đầu tiên ở trên cùng
w = 0.26
fig, ax = plt.subplots(figsize=(12.2, 8.6))

for j, m in enumerate(CMODELS):
    vals = [acc(m, qid) for _, qid, _, _ in QORDER]
    yy = ypos + (1 - j) * w
    ax.barh(yy, vals, height=w, color=CCOL[m], label=CLBL[m], edgecolor="white", lw=0.6, zorder=3)
    for y, v in zip(yy, vals):
        ax.text(v + 0.012, y, f"{v*100:.0f}", va="center", ha="left", fontsize=8, color=CCOL[m])

# nền theo nhóm category + nhãn nhóm bên phải
cats = [c for c, *_ in QORDER]
band = {"rules": "#2A9D8F", "time": "#E9C46A", "state": "#E76F51"}
i = 0
while i < n:
    c = cats[i]; j = i
    while j < n and cats[j] == c:
        j += 1
    y_hi = ypos[i] + 0.5; y_lo = ypos[j-1] - 0.5
    ax.axhspan(y_lo, y_hi, color=band[c], alpha=0.06, zorder=0)
    ax.text(1.055, (y_hi + y_lo) / 2, CATLBL[c], rotation=90, va="center", ha="center",
            fontsize=10.5, color=DARK, fontweight="bold", alpha=0.85)
    i = j

# nhãn câu (kèm dấu đọc/tính) trên trục y
ylabels = [("● " if tag == "r" else "▲ ") + lbl for _, _, lbl, tag in QORDER]
ax.set_yticks(ypos); ax.set_yticklabels(ylabels, fontsize=10)
ax.set_ylim(-0.7, n - 0.3)
ax.set_xlim(0, 1.13); ax.set_xticks(np.arange(0, 1.01, 0.2))
ax.set_xticklabels([f"{int(t*100)}%" for t in np.arange(0, 1.01, 0.2)])
ax.axvline(0.9, color="#888", ls=":", lw=1.1, zorder=1)
ax.set_xlabel("Tỉ lệ trả lời đúng (gộp EN/VN · 3 mức rủi ro · pool ẩn+hiện)")
ax.set_title("Độ chính xác từng câu trong bộ 20 câu đọc-hiểu — cao ở RULES/TIME, tụt dần ở STATE",
             fontsize=14, pad=40)
ax.grid(axis="y", visible=False)
# chú thích ký hiệu đọc/tính
ax.text(0.0, -0.62, "●  đáp án in sẵn (chỉ cần đọc)      ▲  phải tự cộng dồn từ lịch sử",
        transform=ax.get_yaxis_transform(), fontsize=9.5, color="#52646b")
ax.legend(frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.005))

fig.tight_layout()
fig.savefig(OUT / "K0_comp_per_question.png", bbox_inches="tight", facecolor="white")
plt.close(fig)
print("[OK] ->", OUT / "K0_comp_per_question.png")
