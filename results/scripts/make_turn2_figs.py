"""Turn-2 figures — scaling (small→large, +Llama-70B/Qwen-72B) + comprehension (+27B/32B).
Xuất thẳng vào slides/turn_2/figs. Palette khớp deck. Chạy trong results/."""
from pathlib import Path
import json, glob
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
DARK, ACC, TEAL, YELL = "#264653", "#E76F51", "#2A9D8F", "#E9C46A"
# nhạt = nhỏ, đậm = lớn (cùng họ); Qwen xanh dương, Gemma teal, Llama coral
COL = {"qwen25-7b-instruct": "#7FB8DE", "qwen25-32b-instruct": "#2C6E9B", "qwen25-72b-instruct-awq": "#0B3C5D",
       "gemma2-9b-it": "#83C5BE", "gemma2-27b-it": "#14746F",
       "llama-3-1-8b": "#F0987A", "llama-3-1-70b-instruct-awq": "#B23A22",
       "llama33-70b-instruct-awq": "#B23A22"}
LBL = {"qwen25-7b-instruct": "Qwen2.5-7B", "qwen25-32b-instruct": "Qwen2.5-32B", "qwen25-72b-instruct-awq": "Qwen2.5-72B",
       "gemma2-9b-it": "Gemma-2-9B", "gemma2-27b-it": "Gemma-2-27B",
       "llama-3-1-8b": "Llama-3.1-8B", "llama-3-1-70b-instruct-awq": "Llama-3.1-70B",
       "llama33-70b-instruct-awq": "Llama-3.3-70B"}
PAR = {"qwen25-7b-instruct": 7, "qwen25-32b-instruct": 32, "qwen25-72b-instruct-awq": 72,
       "gemma2-9b-it": 9, "gemma2-27b-it": 27, "llama-3-1-8b": 8, "llama-3-1-70b-instruct-awq": 70,
       "llama33-70b-instruct-awq": 70}
ALLM = ["qwen25-7b-instruct", "qwen25-32b-instruct", "qwen25-72b-instruct-awq",
        "gemma2-9b-it", "gemma2-27b-it", "llama-3-1-8b", "llama-3-1-70b-instruct-awq"]
LARGEM = ["qwen25-32b-instruct", "qwen25-72b-instruct-awq", "gemma2-27b-it", "llama-3-1-70b-instruct-awq"]
HUMAN = {0.9: 0.50, 0.5: 0.10, 0.1: 0.00}

# Gemini frontier (đóng) — xem như MỘT model thường trong các hình so-sánh model
GEM = "google-gemini-3.1-flash-lite-preview"
COL[GEM] = "#6A4C93"; LBL[GEM] = "Gemini-flash-lite"
ALLMG = ALLM + [GEM]           # 7 model mở + Gemini, dùng cho L2/L3/L4/L5

def save(fig, name):
    fig.tight_layout(); fig.savefig(OUT / name, bbox_inches="tight", facecolor="white"); plt.close(fig)
    print("  ->", name)

# ---------------------------------------------------------------- load behavior
def loadcsv(p): return pd.read_csv(p)
A = pd.concat([
    loadcsv(R / "data/baseline/crsd_results/crsd_all_models.csv"),
    loadcsv(R / "extracted_large/crsd_results/crsd_all_models.csv"),
    loadcsv(R / "extracted_new/llama70/crsd_results/crsd_all_models.csv"),
    loadcsv(R / "extracted_new/qwen72/crsd_results/crsd_all_models.csv"),
    loadcsv(R / "frontier/google-gemini-3.1-flash-lite-preview/exp_baseline/games.csv"),
], ignore_index=True)
A["reach"] = A.target_reached.astype(int); A["risk"] = A.risk_probability.astype(float)

def load_turns(pattern):
    rows = []
    for f in glob.glob(str(R / pattern)):
        m = f.replace("\\", "/").split("/")[-3]
        for line in open(f, encoding="utf-8"):
            d = json.loads(line)
            rows.append((m, d["round"], d["contribution"], d.get("language"),
                         float(d.get("risk_probability", 0))))
    return rows
T = pd.DataFrame(
    load_turns("data/baseline/crsd_results/*/exp_baseline/turns.jsonl")
    + load_turns("extracted_large/crsd_results/*/exp_baseline/turns.jsonl")
    + load_turns("extracted_new/llama70/crsd_results/*/exp_baseline/turns.jsonl")
    + load_turns("extracted_new/qwen72/crsd_results/*/exp_baseline/turns.jsonl")
    + load_turns("frontier/google-gemini-3.1-flash-lite-preview/exp_baseline/turns.jsonl"),
    columns=["model", "round", "c", "lang", "risk"])

# ============================================================================
# L1. SCALING headline — contribution vs #params, 3 họ hội tụ về ~120
# ============================================================================
gt = A.groupby("model").group_total.mean()
fig, ax = plt.subplots(figsize=(8.4, 4.8))
fams = [("Qwen", ["qwen25-7b-instruct", "qwen25-32b-instruct", "qwen25-72b-instruct-awq"]),
        ("Gemma", ["gemma2-9b-it", "gemma2-27b-it"]),
        ("Llama", ["llama-3-1-8b", "llama-3-1-70b-instruct-awq"])]
famcol = {"Qwen": "#2C6E9B", "Gemma": "#14746F", "Llama": "#B23A22"}
for fam, ms in fams:
    xs = [PAR[m] for m in ms]; ys = [gt[m] for m in ms]
    ax.plot(xs, ys, "-", color=famcol[fam], lw=2.4, zorder=1, alpha=.8)
    for m in ms:
        ax.scatter(PAR[m], gt[m], s=140, color=COL[m], zorder=3, edgecolor="white", lw=1.5)
# nhãn từng điểm
lab = {"qwen25-7b-instruct": (0, 12, "bottom"), "qwen25-32b-instruct": (16, 10, "bottom"),
       "qwen25-72b-instruct-awq": (2, 11, "bottom"), "gemma2-9b-it": (0, 12, "bottom"),
       "gemma2-27b-it": (-14, -16, "top"), "llama-3-1-8b": (0, 11, "bottom"),
       "llama-3-1-70b-instruct-awq": (6, -16, "top")}
for m in ALLM:
    dx, dy, va = lab[m]
    ax.annotate(f"{LBL[m]}\n{gt[m]:.0f}", xy=(PAR[m], gt[m]), xytext=(dx, dy),
                textcoords="offset points", ha="center", va=va, fontsize=9, color=COL[m], fontweight="bold")
ax.axhline(120, color=DARK, ls=":", lw=1.8); ax.text(7, 124, "mục tiêu 120", color=DARK, fontsize=10)
ax.set_xscale("log"); ax.set_xticks([7, 9, 32, 72]); ax.set_xticklabels(["7-9B", "", "27-32B", "70-72B"])
ax.set_xlim(6, 90); ax.set_ylim(105, 250)
ax.set_xlabel("Số tham số (log)"); ax.set_ylabel("Tổng đóng góp / game (trên 240)")
ax.set_title("Phóng to → cả ba họ hội tụ về “vừa đủ 120”")
ax.grid(axis="x", visible=False)
save(fig, "L1_scaling_contrib.png")

# ============================================================================
# L2. Reach vs risk — Qwen/Gemma lớn phẳng ~100%; Llama-70B phẳng nhưng 50%
# ============================================================================
risks = [0.9, 0.5, 0.1]
rr = A.groupby(["model", "risk"]).reach.mean()
fig, ax = plt.subplots(figsize=(7.8, 4.7))
for m in ["qwen25-32b-instruct", "qwen25-72b-instruct-awq", "gemma2-27b-it"]:
    ax.plot(risks, [rr[(m, k)] for k in risks], "o-", color=COL[m], lw=2.6, ms=9, label=LBL[m])
ax.plot(risks, [rr[("llama-3-1-70b-instruct-awq", k)] for k in risks], "D--", color=COL["llama-3-1-70b-instruct-awq"],
        lw=2.6, ms=9, label="Llama-3.1-70B")
ax.plot(risks, [rr[(GEM, k)] for k in risks], "P-", color=COL[GEM], lw=2.8, ms=11,
        label="Gemini-flash-lite (đóng)", zorder=6, markeredgecolor="white", markeredgewidth=1.3)
ax.plot(risks, [HUMAN[k] for k in risks], "s--", color=DARK, lw=2.4, ms=8, label="Người (Milinski 2008)")
ax.annotate("mọi model lớn: PHẲNG theo rủi ro", xy=(0.5, 1.0), xytext=(0.5, 0.66),
            ha="center", color=DARK, fontsize=10.5, arrowprops=dict(arrowstyle="->", color=DARK))
ax.annotate("Llama-70B phẳng nhưng ở 50%\n(thất bại, không phải nhạy rủi ro)", xy=(0.5, 0.5),
            xytext=(0.72, 0.30), ha="center", color=COL["llama-3-1-70b-instruct-awq"], fontsize=9.5,
            arrowprops=dict(arrowstyle="->", color=COL["llama-3-1-70b-instruct-awq"]))
ax.set_xlabel("Xác suất thảm hoạ (rủi ro)"); ax.set_ylabel("Tỉ lệ đạt mục tiêu")
ax.set_title("Phóng to KHÔNG phục hồi nhạy-rủi-ro")
ax.set_ylim(-0.05, 1.13); ax.set_xticks(risks); ax.invert_xaxis(); ax.legend(loc="center right", frameon=False, fontsize=9.5)
save(fig, "L2_scaling_reach.png")

# ============================================================================
# L3. Choice fingerprint — 7 model
# ============================================================================
fig, ax = plt.subplots(figsize=(8.6, 5.5))
y = np.arange(len(ALLMG)); choice_c = {0: ACC, 2: YELL, 4: TEAL}
left = np.zeros(len(ALLMG))
for v in [0, 2, 4]:
    frac = np.array([T[T.model == m].c.eq(v).mean() for m in ALLMG])
    ax.barh(y, frac, left=left, color=choice_c[v], label=f"đóng {v}", edgecolor="white", lw=1.2)
    for i, (fr, lf) in enumerate(zip(frac, left)):
        if fr > 0.05:
            ax.text(lf + fr/2, y[i], f"{fr*100:.0f}%", va="center", ha="center",
                    fontsize=10, color="white", fontweight="bold")
    left += frac
ax.set_yticks(y); ax.set_yticklabels([LBL[m] for m in ALLMG]); ax.invert_yaxis()
ax.set_xlim(0, 1); ax.set_xlabel("Tỉ lệ lượt chọn mỗi mức đóng góp")
ax.set_title("“Vân tay” lật: chỉ Qwen-7B & Llama-8B kịch trần (4); model lớn & Gemini về “2”")
ax.legend(ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.13)); ax.grid(False)
save(fig, "L3_choice_flip.png")

# ============================================================================
# L4. Round dynamics — large models phẳng rồi ramp; Llama-70B SỤP vòng 10
# ============================================================================
gr = T.groupby(["model", "round"]).c.mean().reset_index()
fig, ax = plt.subplots(figsize=(8.0, 4.7))
for m in ALLMG:
    s = gr[gr.model == m].sort_values("round")
    big = (m == GEM) or any(k in m for k in ["32b", "27b", "70b", "72b"])
    ax.plot(s["round"], s.c, ("P-" if m == GEM else "o-"), color=COL[m], lw=2.6 if big else 1.5,
            ms=7 if m == GEM else 5, label=LBL[m], alpha=1.0 if big else 0.5,
            zorder=6 if m == GEM else 3)
ax.annotate("Llama-70B sụp vòng cuối\n(bỏ cuộc → trượt mục tiêu)", xy=(10, 1.1), xytext=(7.2, 1.4),
            fontsize=9.5, color=COL["llama-3-1-70b-instruct-awq"], ha="center",
            arrowprops=dict(arrowstyle="->", color=COL["llama-3-1-70b-instruct-awq"]))
ax.annotate("ramp sát deadline", xy=(9.5, 3.0), xytext=(6.4, 3.7), fontsize=9.5, color=DARK, ha="center",
            arrowprops=dict(arrowstyle="->", color=DARK))
ax.set_xlabel("Vòng (trên 10)"); ax.set_ylabel("Đóng góp TB / người")
ax.set_title("Vẫn TĂNG dần — ngược người; riêng Llama-70B bỏ cuộc ở vòng chót")
ax.set_xticks(range(1, 11)); ax.set_ylim(0.8, 4.2); ax.legend(frameon=False, ncol=2, fontsize=8.5, loc="upper left")
save(fig, "L4_scaling_dynamics.png")

# ============================================================================
# L5. EN vs VN — 7 model; Llama vẫn lệch mạnh nhất
# ============================================================================
lb = A.groupby(["model", "language"]).group_total.mean().unstack()
fig, ax = plt.subplots(figsize=(9.8, 4.7))
x = np.arange(len(ALLMG)); w = 0.38
for i, lang in enumerate(["en", "vn"]):
    ax.bar(x + (i-0.5)*w, [lb.loc[m, lang] for m in ALLMG], w,
           label={"en": "Tiếng Anh", "vn": "Tiếng Việt"}[lang], color=[DARK, ACC][i])
ax.axhline(120, color="#888", ls=":", lw=1.5, label="Mục tiêu 120")
for i, m in enumerate(ALLMG):
    d = lb.loc[m, "vn"] - lb.loc[m, "en"]
    ax.text(x[i], max(lb.loc[m, "en"], lb.loc[m, "vn"]) + 5, f"{d:+.0f}", ha="center",
            fontsize=9.5, color=ACC if abs(d) > 8 else DARK, fontweight="bold")
ax.set_xticks(x); ax.set_xticklabels([LBL[m] for m in ALLMG], rotation=16, ha="right", fontsize=9.5)
ax.set_ylabel("Tổng đóng góp (trên 240)"); ax.set_ylim(0, 260)
ax.set_title("Trục ngôn ngữ không biến mất khi phóng to — VN của Llama-70B tụt DƯỚI mốc 120")
ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.20))
save(fig, "L5_scaling_lang.png")

# ============================================================================
# L6. NEW — Llama-70B: sụp theo NGÔN NGỮ (EN đạt / VN thảm hoạ)
# ============================================================================
L = A[A.model == "llama-3-1-70b-instruct-awq"]
g = L.groupby("language").agg(reach=("reach", "mean"), cat=("catastrophe", "mean"),
                              gtot=("group_total", "mean"))
fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.5))
langs = ["en", "vn"]; lcol = [DARK, ACC]; llab = ["Tiếng Anh", "Tiếng Việt"]
# panel 1: tỉ lệ đạt & thảm hoạ
ax = axes[0]; x = np.arange(2); w = 0.36
ax.bar(x - w/2, [g.loc[l, "reach"] for l in langs], w, color=["#2A9D8F", "#8FBFB8"], label="Đạt mục tiêu")
ax.bar(x + w/2, [g.loc[l, "cat"] for l in langs], w, color=["#f0b0a0", "#E76F51"], label="Gặp thảm hoạ")
for i, l in enumerate(langs):
    ax.text(x[i]-w/2, g.loc[l, "reach"]+0.02, f"{g.loc[l,'reach']*100:.0f}%", ha="center", fontsize=11, fontweight="bold", color=DARK)
    ax.text(x[i]+w/2, g.loc[l, "cat"]+0.02, f"{g.loc[l,'cat']*100:.0f}%", ha="center", fontsize=11, fontweight="bold", color=ACC)
ax.set_xticks(x); ax.set_xticklabels(llab); ax.set_ylim(0, 1.1); ax.set_ylabel("Tỉ lệ (trên 60 ván)")
ax.set_title("EN đạt 100% · VN trượt 100% → thảm hoạ 73%", fontsize=12)
ax.legend(frameon=False, loc="upper center", ncol=2, bbox_to_anchor=(0.5, -0.10))
# panel 2: đóng góp EN vs VN quanh mốc 120
ax = axes[1]
ax.bar(x, [g.loc[l, "gtot"] for l in langs], 0.5, color=lcol)
ax.axhline(120, color=DARK, ls=":", lw=1.8); ax.text(1.35, 121, "mục tiêu 120", color=DARK, fontsize=9.5, va="bottom", ha="right")
for i, l in enumerate(langs):
    ax.text(x[i], g.loc[l, "gtot"]+2, f"{g.loc[l,'gtot']:.0f}", ha="center", fontsize=12, fontweight="bold", color=lcol[i])
ax.set_xticks(x); ax.set_xticklabels(llab); ax.set_ylim(100, 140); ax.set_ylabel("Tổng đóng góp / game")
ax.set_title("VN đóng 112 < 120 → hụt vạch", fontsize=12)
fig.suptitle("Llama-3.1-70B: model lớn đầu tiên THẤT BẠI — nhưng do NGÔN NGỮ, không do rủi ro", y=1.03, fontsize=13.5)
save(fig, "L6_llama70_lang_collapse.png")

# ============================================================================
#  COMPREHENSION  — nay có cả model LỚN (Qwen-32B, Gemma-27B)
# ============================================================================
def read_comp(pattern):
    return [pd.read_csv(f) for f in glob.glob(str(R / pattern))]
C = pd.concat(
    read_comp("extracted_comp/crsd_results/*/exp_comprehension/comprehension_summary.csv")
    + read_comp("extracted_new/comp_large/crsd_results/*/exp_comprehension/comprehension_summary.csv")
    + read_comp("extracted_new/comp_xl/crsd_results/*/exp_comprehension/comprehension_summary.csv"),
    ignore_index=True)
# thứ tự ghép cặp nhỏ→lớn theo họ (nay có cả 70–72B; Llama đo bản 3.3)
CMODELS = ["qwen25-7b-instruct", "qwen25-32b-instruct", "qwen25-72b-instruct-awq",
           "gemma2-9b-it", "gemma2-27b-it", "llama-3-1-8b", "llama33-70b-instruct-awq"]
NCM = len(CMODELS)
def coff(j, w): return (j - (NCM - 1) / 2) * w   # offset cột cho nhóm NCM model
CCOL = {m: COL[m] for m in CMODELS}
CLBL = {m: LBL[m] for m in CMODELS}
SMALL3 = ["qwen25-7b-instruct", "gemma2-9b-it", "llama-3-1-8b"]  # cho K0

def acc_by(df, by, col):
    a = df.groupby(by).agg(n=("n", "sum"), nc=("n_correct", "sum"))
    a["acc"] = a.nc / a.n.replace(0, np.nan)
    return a["acc"].unstack(col)

# ---- K0. accuracy từng câu (giữ 3 model nhỏ — bản chi tiết ghép slide bộ câu hỏi)
QORDER = [
    ("rules", "rules_actions", "Mức đóng được phép mỗi vòng", "r"),
    ("rules", "rules_endowment", "Vốn ban đầu mỗi người", "r"),
    ("rules", "rules_target", "Mục tiêu chung cả game", "r"),
    ("rules", "rules_n_rounds", "Game dài bao nhiêu vòng", "r"),
    ("rules", "rules_risk_pct", "Xác suất mất hết nếu trượt", "r"),
    ("rules", "rules_payoff_disaster", "Còn lại nếu gặp thảm hoạ", "r"),
    ("rules", "rules_max_contrib", "Mức đóng tối đa / vòng", "r"),
    ("rules", "rules_min_contrib", "Mức đóng tối thiểu / vòng", "r"),
    ("time", "time_round", "Đang ở vòng thứ mấy", "r"),
    ("time", "time_action_i", "Vòng i: ghế Px đóng bao nhiêu", "r"),
    ("time", "time_own_action_i", "Vòng i: chính bạn đóng bao nhiêu", "r"),
    ("time", "time_round_total_i", "Vòng i: cả 6 người đóng tổng", "t"),
    ("state", "state_pool", "Tổng quỹ chung đến giờ", "t"),
    ("state", "state_remaining_to_target", "Còn thiếu bao nhiêu để đạt 120", "t"),
    ("state", "state_X_total", "Ghế Px đã đóng tổng cộng", "t"),
    ("state", "state_own_total", "Chính bạn đã đóng tổng cộng", "t"),
    ("state", "state_own_remaining", "Vốn bạn còn chưa đóng", "r"),
    ("state", "state_count_p", "Ghế Px đóng đúng mức 4 mấy lần", "t"),
    ("state", "state_rounds_left", "Còn mấy vòng nữa (kể cả vòng này)", "t"),
    ("state", "state_target_reached", "Nhóm đã đạt mục tiêu chưa", "t"),
]
CATLBL = {"rules": "RULES · luật tĩnh", "time": "TIME · tra lịch sử", "state": "STATE · cộng dồn"}
K0COL = {"qwen25-7b-instruct": "#1B4965", "gemma2-9b-it": "#2A9D8F", "llama-3-1-8b": "#E76F51"}

def accq(model, qid):
    d = C[(C.model == model) & (C.question_id == qid)]
    return d.n_correct.sum() / d.n.sum() if d.n.sum() else np.nan
n = len(QORDER); ypos = np.arange(n)[::-1]; w = 0.26
fig, ax = plt.subplots(figsize=(12.2, 8.6))
for j, m in enumerate(SMALL3):
    vals = [accq(m, qid) for _, qid, _, _ in QORDER]
    yy = ypos + (1 - j) * w
    ax.barh(yy, vals, height=w, color=K0COL[m], label=CLBL[m], edgecolor="white", lw=0.6, zorder=3)
    for yv, v in zip(yy, vals):
        ax.text(v + 0.012, yv, f"{v*100:.0f}", va="center", ha="left", fontsize=8, color=K0COL[m])
cats = [c for c, *_ in QORDER]; band = {"rules": "#2A9D8F", "time": "#E9C46A", "state": "#E76F51"}
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
ylabels = [("● " if tag == "r" else "▲ ") + lbl for _, _, lbl, tag in QORDER]
ax.set_yticks(ypos); ax.set_yticklabels(ylabels, fontsize=10); ax.set_ylim(-0.7, n - 0.3)
ax.set_xlim(0, 1.13); ax.set_xticks(np.arange(0, 1.01, 0.2)); ax.set_xticklabels([f"{int(t*100)}%" for t in np.arange(0, 1.01, 0.2)])
ax.axvline(0.9, color="#888", ls=":", lw=1.1, zorder=1)
ax.set_xlabel("Tỉ lệ trả lời đúng (gộp EN/VN · 3 mức rủi ro · pool ẩn+hiện)")
ax.set_title("Độ chính xác từng câu — cao ở RULES/TIME, tụt dần ở STATE (ba model nhỏ)", fontsize=14, pad=40)
ax.grid(axis="y", visible=False)
ax.text(0.0, -0.62, "●  đáp án in sẵn (chỉ cần đọc)      ▲  phải tự cộng dồn từ lịch sử",
        transform=ax.get_yaxis_transform(), fontsize=9.5, color="#52646b")
ax.legend(frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.005))
save(fig, "K0_comp_per_question.png")

# ---- K1. category accuracy — 5 model (nhỏ→lớn), STATE hồi phục theo scale
cat = acc_by(C, ["model", "category"], "category").reindex(CMODELS)
fig, ax = plt.subplots(figsize=(10.6, 4.9))
cats3 = ["rules", "time", "state"]; x = np.arange(len(cats3)); w = 0.12
for j, m in enumerate(CMODELS):
    ax.bar(x + coff(j, w), [cat.loc[m, c] for c in cats3], w, color=CCOL[m], label=CLBL[m])
    for i, c in enumerate(cats3):
        ax.text(x[i]+coff(j, w), cat.loc[m, c]+0.015, f"{cat.loc[m,c]*100:.0f}", ha="center",
                va="bottom", rotation=90, fontsize=6.8, color=DARK)
ax.axhline(0.9, color="#888", ls=":", lw=1.2)
ax.set_xticks(x); ax.set_xticklabels(["RULES\n(luật tĩnh)", "TIME\n(tra lịch sử)", "STATE\n(cộng dồn)"])
ax.set_ylabel("Accuracy đọc-hiểu"); ax.set_ylim(0, 1.18)
ax.set_title("Model càng lớn, cộng dồn (STATE) càng khá — tới 70–72B đạt 82–87%")
ax.legend(frameon=False, ncol=7, loc="upper center", bbox_to_anchor=(0.5, -0.13), fontsize=7.6, columnspacing=1.0)
save(fig, "K1_comp_category.png")

# ---- K2. read vs add — pool ẩn hồi phục theo scale nhưng chưa kín
groups = [("đọc số IN SẴN\n(own_remaining)", "state_own_remaining", None),
          ("CỘNG dồn, pool ẨN\n(state_pool, showcum=0)", "state_pool", 0),
          ("CỘNG dồn, pool HIỆN\n(state_pool, showcum=1)", "state_pool", 1)]
fig, ax = plt.subplots(figsize=(10.2, 4.9))
x = np.arange(len(groups)); w = 0.12
for j, m in enumerate(CMODELS):
    vals = []
    for _, q, sc in groups:
        if q == "state_own_remaining":
            v = C[(C.model == m) & (C.question_id == q)]
        else:
            v = C[(C.model == m) & (C.question_id == q) & (C.show_cumulative == sc)]
        vals.append(v.n_correct.sum()/v.n.sum())
    ax.bar(x + coff(j, w), vals, w, color=CCOL[m], label=CLBL[m])
    for i, vv in enumerate(vals):
        ax.text(x[i]+coff(j, w), vv+0.015, f"{vv*100:.0f}", ha="center", va="bottom",
                rotation=90, fontsize=6.8, color=DARK)
ax.axvspan(0.5, 1.5, color=ACC, alpha=0.06)
ax.set_xticks(x); ax.set_xticklabels([gp[0] for gp in groups], fontsize=10)
ax.set_ylabel("Accuracy"); ax.set_ylim(0, 1.18)
ax.set_title("Đọc được ≠ cộng được — nhưng pool ẩn hồi mạnh theo scale (Qwen 14→44→88, Llama 10→82)")
ax.legend(frameon=False, ncol=7, loc="lower center", bbox_to_anchor=(0.5, -0.26), fontsize=7.6, columnspacing=1.0); ax.grid(axis="x", visible=False)
save(fig, "K2_comp_read_vs_add.png")

# ---- K6. hướng sai khi phải TỰ CỘNG (pool ẩn): thiếu hay vượt, bao nhiêu %?
#      per-probe jsonl (summary CSV không có parsed vs ground_truth).
def load_comp_probes(pattern):
    rows = []
    for f in glob.glob(str(R / pattern)):
        for line in open(f, encoding="utf-8"):
            d = json.loads(line)
            if d["question_id"] != "state_pool" or d["show_cumulative"]:
                continue                                   # chỉ nhóm pool ẨN (phải tự cộng)
            rows.append((d["model"], d["parsed_answer"], d["ground_truth"],
                         bool(d["correct"]), bool(d["parse_failed"])))
    return rows
CP = pd.DataFrame(
    load_comp_probes("extracted_comp/crsd_results/*/exp_comprehension/comprehension.jsonl")
    + load_comp_probes("extracted_new/comp_large/crsd_results/*/exp_comprehension/comprehension.jsonl")
    + load_comp_probes("extracted_new/comp_xl_full/crsd_results/*/exp_comprehension/comprehension.jsonl"),
    columns=["model", "parsed", "truth", "correct", "pfail"])
CP = CP[CP.truth.apply(lambda v: isinstance(v, (int, float)) and v > 0)]  # GT>0: có gì để cộng

def dir_stats(m):
    d = CP[(CP.model == m) & (~CP.pfail) & CP.parsed.notna()]
    p = d.parsed.astype(float); g = d.truth.astype(float)
    under = int((p < g).sum()); over = int((p > g).sum()); wrong = under + over
    signed = ((p - g) / g * 100.0)[p != g]                 # % lệch có dấu, chỉ câu SAI
    return dict(under=under, over=over, wrong=wrong,
                under_pct=100*under/wrong if wrong else 0, over_pct=100*over/wrong if wrong else 0,
                avg=float(np.mean(signed)) if len(signed) else 0.0)  # TRUNG BÌNH % lệch

ST = {m: dir_stats(m) for m in CMODELS}
print("  [K6] TRUNG BÌNH % lệch (câu SAI, pool ẩn, GT>0):")
for m in CMODELS:
    print(f"      {CLBL[m]:<14} TB={ST[m]['avg']:+6.1f}%   thiếu {ST[m]['under_pct']:.0f}% / vượt {ST[m]['over_pct']:.0f}%")
ypos = np.arange(NCM)[::-1]                                 # Qwen-7B trên cùng
UND, OVR = "#E76F51", "#2C6E9B"                             # coral = thiếu, xanh = vượt
fig, (axL, axR) = plt.subplots(1, 2, figsize=(12.2, 5.2), sharey=True)

# Panel trái: HƯỚNG — % câu sai là thiếu (trái) vs vượt (phải)
for y, m in zip(ypos, CMODELS):
    s = ST[m]
    axL.barh(y, -s["under_pct"], color=UND, edgecolor="white", height=0.66, zorder=3)
    axL.barh(y, s["over_pct"], color=OVR, edgecolor="white", height=0.66, zorder=3)
    if s["under_pct"] > 6:
        axL.text(-s["under_pct"]+2, y, f"{s['under_pct']:.0f}", va="center", ha="left",
                 fontsize=8.5, color="white", fontweight="bold")
    if s["over_pct"] > 6:
        axL.text(s["over_pct"]-2, y, f"{s['over_pct']:.0f}", va="center", ha="right",
                 fontsize=8.5, color="white", fontweight="bold")
axL.axvline(0, color=DARK, lw=1.1)
axL.set_yticks(ypos); axL.set_yticklabels([CLBL[m] for m in CMODELS], fontsize=10)
axL.set_xlim(-105, 105); axL.set_xticks([-100, -50, 0, 50, 100])
axL.set_xticklabels(["100", "50", "0", "50", "100"])
axL.set_xlabel("% số câu SAI  ← THIẾU (thấp hơn GT)   |   VƯỢT (cao hơn GT) →")
axL.set_title("Hướng sai khi phải tự cộng", fontsize=13)
axL.grid(axis="y", visible=False)

# Panel phải: ĐỘ LỚN — TRUNG BÌNH % lệch có dấu (âm = báo thiếu)
for y, m in zip(ypos, CMODELS):
    avg = ST[m]["avg"]; c = UND if avg < 0 else OVR
    axR.barh(y, avg, color=c, edgecolor="white", height=0.66, zorder=3)
    axR.text(avg + (2.5 if avg >= 0 else -2.5), y, f"{avg:+.0f}%", va="center",
             ha="left" if avg >= 0 else "right", fontsize=9.5, color=DARK, fontweight="bold")
axR.axvline(0, color=DARK, lw=1.1)
axR.set_xlim(-80, 30); axR.set_xticks([-60, -40, -20, 0, 20])
axR.set_xticklabels([f"{t}%" for t in [-60, -40, -20, 0, 20]])
axR.set_xlabel("Trung bình % lệch trên câu SAI  (âm = báo THIẾU)")
axR.set_title("Sai bao nhiêu (trung bình)", fontsize=13)
axR.grid(axis="y", visible=False)

fig.suptitle("Model nhỏ CỘNG THIẾU một cách hệ thống (~40% pool thật); phóng to → lỗi nhỏ & đối xứng",
             y=1.02, fontsize=13.5)
save(fig, "K6_comp_over_under.png")

# ---- K3. risk gate — model lớn trả đúng ~100% mọi mức rủi ro
rrq = C[C.question_id == "rules_risk_pct"]
acc_rg = acc_by(rrq, ["model", "risk_probability"], "risk_probability").reindex(CMODELS)
fig, ax = plt.subplots(figsize=(9.6, 4.8))
risks3 = [0.9, 0.5, 0.1]; x = np.arange(len(risks3)); w = 0.12
for j, m in enumerate(CMODELS):
    ax.bar(x + coff(j, w), [acc_rg.loc[m, r] for r in risks3], w, color=CCOL[m], label=CLBL[m])
ax.set_xticks(x); ax.set_xticklabels([f"rủi ro {r:g}  (đáp đúng {int(r*100)}%)" for r in risks3])
ax.set_ylabel("Accuracy câu “rủi ro bao nhiêu %”"); ax.set_ylim(0, 1.16)
ax.set_title("BIẾT mức rủi ro ~100% (mọi model lớn: hoàn hảo) → phớt-lờ là LỰA CHỌN", fontsize=14)
ax.legend(frameon=False, ncol=7, loc="lower center", bbox_to_anchor=(0.5, -0.2), fontsize=7.6, columnspacing=1.0)
save(fig, "K3_comp_risk_gate.png")

# ---- K4. EN vs VN — gộp mọi model; State rớt ở tiếng Việt
fig, ax = plt.subplots(figsize=(8.2, 4.6))
cats3 = ["rules", "time", "state"]; x = np.arange(len(cats3)); w = 0.36
def cat_lang(dfl):
    a = dfl.groupby("category").agg(n=("n", "sum"), nc=("n_correct", "sum")); return (a.nc/a.n)
ce, cv = cat_lang(C[C.language == "en"]), cat_lang(C[C.language == "vn"])
ax.bar(x - w/2, [ce[c] for c in cats3], w, label="Tiếng Anh", color=DARK)
ax.bar(x + w/2, [cv[c] for c in cats3], w, label="Tiếng Việt", color=ACC)
for i, c in enumerate(cats3):
    d = cv[c]-ce[c]
    ax.text(x[i], max(ce[c], cv[c])+0.02, f"{d*100:+.0f}pp", ha="center", fontsize=10,
            color=ACC if d < -0.03 else DARK, fontweight="bold")
ax.set_xticks(x); ax.set_xticklabels(["RULES", "TIME", "STATE"]); ax.set_ylim(0, 1.12)
ax.set_ylabel("Accuracy (gộp mọi model)")
ax.set_title("Tiếng Việt đánh đúng vào CỘNG DỒN trạng thái")
ax.legend(frameon=False, ncol=2, loc="lower center", bbox_to_anchor=(0.5, -0.16))
save(fig, "K4_comp_lang.png")

# ---- K5. figure-1 analog — mỗi câu, 2 panel show_cumulative, 5 model
try:
    import sys; sys.path.insert(0, str(R.parent))
    from crsd.engine.comprehension import REGISTRY
    qorder = [q.id for q in REGISTRY]; qcat = {q.id: q.category for q in REGISTRY}
except Exception:
    qorder = [q for _, q, _, _ in QORDER]; qcat = {q: c for c, q, _, _ in QORDER}
present = [q for q in qorder if q in set(C.question_id)]
fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
for ax, sc in zip(axes, [0, 1]):
    d_sc = C[C.show_cumulative == sc]; xq = np.arange(len(present))
    for j, m in enumerate(CMODELS):
        accs = []
        for q in present:
            dd = d_sc[(d_sc.model == m) & (d_sc.question_id == q)]
            accs.append(dd.n_correct.sum()/dd.n.sum() if dd.n.sum() else np.nan)
        ax.plot(xq, accs, "o", ms=5, color=CCOL[m], label=CLBL[m] if sc == 0 else None)
    bounds = {}
    for i, q in enumerate(present):
        bounds.setdefault(qcat[q], []).append(i)
    for c in ["rules", "time", "state"]:
        if c in bounds:
            ax.axvspan(min(bounds[c])-0.5, max(bounds[c])+0.5, alpha=0.06, color="k")
            ax.text((min(bounds[c])+max(bounds[c]))/2, 0.03, c.upper(), ha="center", fontsize=11,
                    color="#52646b", fontweight="bold", alpha=0.7, transform=ax.get_xaxis_transform())
    ax.set_xticks(xq); ax.set_xticklabels(present, rotation=90, fontsize=7)
    ax.set_ylim(0, 1.1); ax.axhline(0.9, ls=":", c="grey", lw=0.8)
    ax.set_title(f"showCumulative = {sc}  ({'pool HIỆN' if sc else 'pool ẨN'})", pad=10)
axes[0].set_ylabel("Response accuracy"); axes[0].legend(frameon=False, fontsize=7.5, loc="lower left", ncol=2)
fig.suptitle("Comprehension theo từng câu (Rules | Time | State) — 7 model, nhỏ→lớn", y=1.0)
save(fig, "K5_comp_figure1.png")

print("\n[OK] figs ->", OUT)
