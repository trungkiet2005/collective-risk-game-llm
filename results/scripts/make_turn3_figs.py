"""Turn-3 figures — exp_riskframing (plain wording + computed totals) vs exp_baseline.
Xuất thẳng vào slides/turn_3/figs. Palette khớp deck Turn 1/2. Chạy trong results/."""
from pathlib import Path
import json, glob
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

R = Path(__file__).resolve().parent.parent
OUT = R.parent / "slides" / "turn_3" / "figs"; OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 150, "font.size": 13,
    "axes.titlesize": 15, "axes.labelsize": 13, "legend.fontsize": 11,
    "xtick.labelsize": 11, "ytick.labelsize": 11, "axes.grid": True,
    "grid.alpha": 0.22, "axes.spines.top": False, "axes.spines.right": False,
    "font.family": "DejaVu Sans", "axes.edgecolor": "#52646b", "text.color": "#264653",
    "axes.labelcolor": "#264653", "xtick.color": "#264653", "ytick.color": "#264653",
})
DARK, ACC, TEAL, YELL = "#264653", "#E76F51", "#2A9D8F", "#E9C46A"
COL = {"qwen25-7b-instruct": "#7FB8DE", "qwen25-32b-instruct": "#2C6E9B",
       "qwen25-72b-instruct-awq": "#0B3C5D", "gemma2-9b-it": "#83C5BE",
       "gemma2-27b-it": "#14746F", "llama-3-1-8b": "#F0987A",
       "llama-3-1-70b-instruct-awq": "#B23A22", "llama-3-3-70b-instruct-awq": "#B23A22"}
LBL = {"qwen25-7b-instruct": "Qwen-7B", "qwen25-32b-instruct": "Qwen-32B",
       "qwen25-72b-instruct-awq": "Qwen-72B", "gemma2-9b-it": "Gemma-9B",
       "gemma2-27b-it": "Gemma-27B", "llama-3-1-8b": "Llama-8B",
       "llama-3-1-70b-instruct-awq": "Llama-3.1-70B", "llama-3-3-70b-instruct-awq": "Llama-3.3-70B*"}
# 6 model so cặp SẠCH (cùng checkpoint ở cả hai arm)
PAIR = ["qwen25-7b-instruct", "llama-3-1-8b", "gemma2-9b-it",
        "qwen25-32b-instruct", "gemma2-27b-it", "qwen25-72b-instruct-awq"]
RF_ALL = PAIR + ["llama-3-3-70b-instruct-awq"]
HUMAN = {0.9: 0.50, 0.5: 0.10, 0.1: 0.00}
BASE_C, RF_C = "#B9C6CC", "#E76F51"          # xám = baseline, cam = nhánh can thiệp
# Tên hai nhánh — đổi Ở ĐÂY là toàn bộ 9 hình đổi theo.
N_BASE = "Baseline"                     # kể chuyện xổ số/thảm hoạ, KHÔNG in tổng
N_RF = "framing + computed totals"      # nêu thẳng xác suất, in sẵn tổng quỹ
N_RF_SHORT = "framing+totals"           # bản ngắn cho nhãn hàng ở R8


def save(fig, name):
    fig.tight_layout(); fig.savefig(OUT / name, bbox_inches="tight", facecolor="white"); plt.close(fig)
    print("  ->", name)


def caption(fig, text, color=DARK, y=-0.015, size=10.5):
    """Chú thích đặt DƯỚI figure — không bao giờ đè lên line/cột."""
    fig.text(0.5, y, text, ha="center", va="top", fontsize=size, color=color, style="italic")


# ------------------------------------------------------------------ load games
A = pd.read_csv(R / "open_source/crsd_all_models.csv")
BL = A[A.experiment == "exp_baseline"].copy()
RF = A[A.experiment == "exp_riskframing"].copy()
for d in (BL, RF):
    d["reach"] = d.target_reached.astype(int)
    d["risk"] = d.risk_probability.astype(float)
    d["excess"] = d.group_total - 120.0


# ------------------------------------------------------------------ load turns
def load_turns(exp):
    rows = []
    for f in glob.glob(str(R / f"open_source/{exp}/*/turns.jsonl")):
        m = f.replace("\\", "/").split("/")[-2]
        for line in open(f, encoding="utf-8"):
            d = json.loads(line)
            rows.append((m, d["game_id"], int(d["round"]), float(d["contribution"]),
                         d.get("language"), float(d.get("risk_probability", 0))))
    t = pd.DataFrame(rows, columns=["model", "game_id", "round", "c", "lang", "risk"])
    rt = t.groupby(["model", "game_id", "round"]).c.sum().rename("rt").reset_index()
    rt["pool_before"] = rt.groupby(["model", "game_id"]).rt.cumsum() - rt.rt
    t = t.merge(rt[["model", "game_id", "round", "pool_before"]], on=["model", "game_id", "round"])
    t["needed"] = (120 - t.pool_before).clip(lower=0)
    return t


TB, TR = load_turns("exp_baseline"), load_turns("exp_riskframing")

# ============================================================================
# R1. HEADLINE — TỔNG đóng góp cả game (trên 240), so với mốc 120
# ============================================================================
fig, ax = plt.subplots(figsize=(9.2, 5.1))
x = np.arange(len(PAIR)); w = 0.38
eb = [BL[BL.model == m].group_total.mean() for m in PAIR]
er = [RF[RF.model == m].group_total.mean() for m in PAIR]
ax.bar(x - w/2, eb, w, color=BASE_C, label=N_BASE, edgecolor="white")
ax.bar(x + w/2, er, w, color=RF_C, label=N_RF, edgecolor="white")
for i, (a, b) in enumerate(zip(eb, er)):
    ax.text(i - w/2, a + 4, f"{a:.0f}", ha="center", fontsize=10, color=DARK)
    ax.text(i + w/2, b + 4, f"{b:.0f}", ha="center", fontsize=10.5, color=RF_C, fontweight="bold")
ax.axhline(120, color=DARK, ls=":", lw=2.0)
ax.set_xlim(-0.62, 6.45)
ax.text(5.62, 123, "mục tiêu\n120", ha="left", va="bottom", fontsize=10, color=DARK)
ax.text(5.62, 116, "phần trên vạch\n= đóng THỪA", ha="left", va="top",
        fontsize=9.5, color="#7a8a90", style="italic")
ax.annotate("Qwen-7B: 233 → 175\nbỏ hơn nửa phần thừa", xy=(0.30, 176), xytext=(2.35, 252),
            fontsize=10.5, color=RF_C, ha="center",
            arrowprops=dict(arrowstyle="->", color=RF_C, connectionstyle="arc3,rad=.14"))
ax.set_xticks(x); ax.set_xticklabels([LBL[m] for m in PAIR], fontsize=10.5)
ax.set_ylabel("Tổng đóng góp cả game\n(tối đa 240)")
ax.set_ylim(0, 288)
ax.set_title(f"{N_RF} → model thôi đóng thừa")
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.11), ncol=2)
save(fig, "R1_excess.png")

# ============================================================================
# R2. …nhưng vẫn KHÔNG biết sợ rủi ro (tỉ lệ đạt theo mức rủi ro)
# ============================================================================
risks = [0.9, 0.5, 0.1]
rr = RF.groupby(["model", "risk"]).reach.mean()
fig, ax = plt.subplots(figsize=(9.4, 4.8))
for m in RF_ALL:
    ax.plot(risks, [rr[(m, k)] for k in risks], "o-", color=COL[m], lw=2.4, ms=8, label=LBL[m], alpha=.9)
ax.plot(risks, [HUMAN[k] for k in risks], "s--", color=DARK, lw=2.6, ms=9, label="Người (Milinski 2008)")
ax.set_xlabel("Xác suất thảm hoạ (rủi ro)"); ax.set_ylabel("Tỉ lệ đạt mục tiêu")
ax.set_title(f"{N_RF} → vẫn không nhạy rủi ro")
ax.set_ylim(-0.05, 1.15); ax.set_xticks(risks); ax.invert_xaxis()
# chú giải ra NGOÀI vùng vẽ (bên phải) — trước đây đè lên chính các đường
ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), frameon=False, fontsize=9.5)
caption(fig, "Đường LLM vẫn PHẲNG: 10% hay 90% rủi ro đều chơi như nhau — chỉ đường “Người” mới dốc xuống.")
save(fig, "R2_reach_risk.png")

# ============================================================================
# R3. CƠ CHẾ — đóng góp khi quỹ ĐÃ đủ 120 (trước / sau)
# ============================================================================
fig, ax = plt.subplots(figsize=(9.4, 5.0))
x = np.arange(len(PAIR))


def past_stat(T, m):
    s = T[(T.model == m) & (T.pool_before >= 120)].c
    return (s.mean() if len(s) else np.nan), len(s)


pb = [past_stat(TB, m) for m in PAIR]
pr = [past_stat(TR, m) for m in PAIR]
ax.bar(x - w/2, [v for v, _ in pb], w, color=BASE_C, label=N_BASE, edgecolor="white")
ax.bar(x + w/2, [v for v, _ in pr], w, color=RF_C, label=N_RF, edgecolor="white")
for i, ((a, na), (b, nb)) in enumerate(zip(pb, pr)):
    for xpos, val, n, col, fw in [(i - w/2, a, na, DARK, "normal"), (i + w/2, b, nb, RF_C, "bold")]:
        if np.isnan(val):
            # xoay dọc + 1 dòng: không còn cấn sang nhãn n= của cột bên cạnh
            ax.text(xpos, 0.14, "chưa từng xảy ra", ha="center", va="bottom", rotation=90,
                    fontsize=8.5, color="#8a969b", style="italic")
        else:
            if val > .6:                       # cột đủ cao -> n= nằm trong cột
                ax.text(xpos, val + .12, f"{val:.1f}", ha="center", fontsize=10.5, color=col, fontweight=fw)
                ax.text(xpos, .12, f"n={n}", ha="center", fontsize=8, color="white")
            else:                              # cột lùn -> n= xếp ngay trên cột, giá trị trên cùng
                ax.text(xpos, val + .42, f"{val:.1f}", ha="center", fontsize=10.5, color=col, fontweight=fw)
                ax.text(xpos, val + .14, f"n={n}", ha="center", fontsize=8, color="#8a969b")
ax.set_xticks(x); ax.set_xticklabels([LBL[m] for m in PAIR], fontsize=10.5)
ax.set_ylabel("Đóng góp TB khi quỹ đã ≥ 120")
ax.set_title("Cái phanh: thấy “đủ rồi” thì lập tức dừng", pad=26)
ax.set_ylim(0, 4.9)
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.11), ncol=2)
caption(fig, "Mọi đồng đóng khi quỹ đã ≥ 120 là VỨT ĐI — mục tiêu đã đạt rồi.")
save(fig, "R3_brake.png")

# ============================================================================
# R4. Nhịp theo vòng — baseline tăng dần, có tổng thì vọt rồi TẮT
# ============================================================================
fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.5), sharey=True)
for ax, (T, ttl) in zip(axes, [(TB, f"{N_BASE} — đóng tăng dần tới cuối"),
                               (TR, f"{N_RF} — vọt rồi TẮT")]):
    for m in PAIR:
        s = T[T.model == m].groupby("round").c.mean()
        ax.plot(s.index, s.values, "o-", color=COL[m], lw=2.2, ms=5, label=LBL[m], alpha=.9)
    ax.set_xlabel("Vòng"); ax.set_xticks(range(1, 11)); ax.set_title(ttl, fontsize=13)
axes[0].set_ylabel("Đóng góp trung bình")
axes[0].set_ylim(-0.18, 4.35)
# chú giải DÙNG CHUNG, đặt dưới cả hai panel — trước đây đè lên đường Qwen-7B
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, frameon=False, fontsize=10, ncol=6,
           loc="upper center", bbox_to_anchor=(0.5, 0.0))
caption(fig, "Nhánh phải, vòng 9–10: đóng góp rơi về 0 vì quỹ đã đủ.", color=RF_C, y=-0.085)
save(fig, "R4_dynamics.png")

# ============================================================================
# R5. CÁI GIÁ — Gemma chơi sát vạch rồi TRƯỢT
# ============================================================================
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.0, 4.4))
gm = ["gemma2-9b-it", "gemma2-27b-it"]
xx = np.arange(len(gm))
a1.bar(xx - w/2, [BL[BL.model == m].reach.mean() for m in gm], w, color=BASE_C, label=N_BASE, edgecolor="white")
a1.bar(xx + w/2, [RF[RF.model == m].reach.mean() for m in gm], w, color=RF_C, label=N_RF, edgecolor="white")
for i, m in enumerate(gm):
    a1.text(i - w/2, BL[BL.model == m].reach.mean() + .02, "100%", ha="center", fontsize=10.5, color=DARK)
    v = RF[RF.model == m].reach.mean()
    a1.text(i + w/2, v + .02, f"{v*100:.0f}%", ha="center", fontsize=11, color=RF_C, fontweight="bold")
    c = RF[RF.model == m].catastrophe.mean()
    a1.text(i + w/2, v/2, f"thảm hoạ\n{c*100:.0f}%", ha="center", fontsize=9.5, color="white", fontweight="bold")
a1.set_xticks(xx); a1.set_xticklabels([LBL[m] for m in gm]); a1.set_ylim(0, 1.18)
a1.set_ylabel("Tỉ lệ đạt mục tiêu"); a1.set_title("Gemma: từ 100% xuống trượt vạch", fontsize=13)

tot = pd.concat([RF[RF.model.isin(gm)].assign(arm="Có in sẵn tổng"),
                 BL[BL.model.isin(gm)].assign(arm="Baseline")])
bins = np.arange(108, 142, 2)
a2.hist([BL[BL.model.isin(gm)].group_total, RF[RF.model.isin(gm)].group_total], bins=bins,
        color=[BASE_C, RF_C], label=[N_BASE, N_RF], edgecolor="white")
a2.axvline(120, color=DARK, ls=":", lw=2.2)
a2.set_ylim(0, a2.get_ylim()[1] * 1.20)          # chừa trần cho nhãn vạch 120
a2.text(120.8, a2.get_ylim()[1] * 0.97, "mục tiêu 120", color=DARK, fontsize=10, va="top")
a2.annotate("trượt 112–118:\nthiếu 2–8 đơn vị", xy=(116, 8), xytext=(109, 30),
            fontsize=10, color=RF_C, arrowprops=dict(arrowstyle="->", color=RF_C))
a2.set_xlabel("Tổng quỹ cuối game"); a2.set_ylabel("Số game")
a2.set_title("Chơi sát vạch → hụt vài đơn vị", fontsize=13)
# một chú giải chung dưới figure — bản cũ để ở "upper right" nên đè lên cột cao nhất
h, l = a1.get_legend_handles_labels()
fig.legend(h, l, frameon=False, fontsize=10.5, ncol=2,
           loc="upper center", bbox_to_anchor=(0.5, 0.0))
save(fig, "R5_gemma_cost.png")

# ============================================================================
# R6. BẤT ĐỐI XỨNG — dùng con số làm PHANH giỏi, làm VÔ LĂNG dở (vòng 10)
# ============================================================================
r10 = TR[TR["round"] == 10].copy()
r10["bucket"] = pd.cut(r10.needed, [-.1, .1, 6, 12, 24],
                       labels=["đã đủ", "thiếu 1–6", "thiếu 7–12", "thiếu 13–24"])
agg = r10.groupby("bucket", observed=False).c.agg(["mean", "size"])
need = [0, 6/6, 12/6, 24/6]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.4, 4.6), gridspec_kw={"width_ratios": [1.35, 1]})

xs = np.arange(len(agg))
a1.bar(xs, agg["mean"].values, 0.55, color=[TEAL, YELL, ACC, ACC], edgecolor="white")
a1.plot(xs, need, "D--", color=DARK, lw=2.2, ms=8, label="mức CẦN đóng để kịp cán đích")
for i, (v, n) in enumerate(zip(agg["mean"].values, agg["size"].values)):
    # lệch trái khỏi tâm cột: kim cương “mức CẦN” nằm đúng tâm nên trước đây chồng nhau
    a1.text(i - .26, v + .13, f"{v:.2f}", ha="center", fontsize=11, color=DARK, fontweight="bold")
    a1.text(i, .1, f"n={n}", ha="center", fontsize=8.5, color="white")
a1.set_xticks(xs); a1.set_xticklabels([str(i) for i in agg.index], fontsize=10.5)
a1.set_ylabel("Đóng góp TB ở vòng 10"); a1.set_ylim(0, 4.8)
a1.set_xlabel("Còn thiếu bao nhiêu khi vào vòng cuối")
a1.set_title("Biết còn thiếu, nhưng không bù thêm", fontsize=13.5)
a1.legend(frameon=False, fontsize=9.5, loc="upper left")

# panel 2: tỉ lệ BÍT được lỗ hổng vòng cuối (thiếu 1..24 => hoàn toàn trong tầm với)
def closed(T, models):
    x = T[(T["round"] == 10) & T.model.isin(models)]
    g = x.groupby(["model", "game_id"]).agg(needed=("needed", "first"), got=("c", "sum")).reset_index()
    g = g[(g.needed > 0) & (g.needed <= 24)]
    return g.groupby("model").apply(lambda d: (d.got >= d.needed).mean(), include_groups=False), \
           g.groupby("model").size()


gm = ["gemma2-9b-it", "gemma2-27b-it"]
cb, nb2 = closed(TB, gm); cr, nr2 = closed(TR, gm)
xx = np.arange(len(gm))
a2.bar(xx - w/2, [cb.get(m, np.nan) for m in gm], w, color=BASE_C, label=N_BASE, edgecolor="white")
a2.bar(xx + w/2, [cr.get(m, np.nan) for m in gm], w, color=RF_C, label=N_RF, edgecolor="white")
for i, m in enumerate(gm):
    a2.text(i - w/2, cb[m] + .02, f"{cb[m]*100:.0f}%", ha="center", fontsize=10.5, color=DARK)
    a2.text(i + w/2, cr[m] + .02, f"{cr[m]*100:.0f}%", ha="center", fontsize=11, color=RF_C, fontweight="bold")
a2.set_xticks(xx); a2.set_xticklabels([LBL[m] for m in gm], fontsize=10.5); a2.set_ylim(0, 1.2)
a2.set_ylabel("Tỉ lệ bít được lỗ hổng vòng cuối")
a2.set_title("Lỗ hổng thừa sức bít (≤24) —\nnay hụt 1/3 số lần", fontsize=12.5)
a2.legend(frameon=False, fontsize=9.5, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2)
fig.suptitle("Cùng một con số: dùng để DỪNG thì giỏi, để BÙ thì không", fontsize=15.5, y=1.03)
caption(fig, "Trái: thiếu gấp đôi, gấp bốn — model vẫn kẹt ở mức quen thuộc “2”, "
             "trong khi mức CẦN đóng (kim cương) tăng dần.", color=ACC, y=-0.10)
save(fig, "R6_asymmetry.png")

# ============================================================================
# R7. Hiệu quả — tiền mỗi người mang về
# ============================================================================
fig, ax = plt.subplots(figsize=(9.0, 4.7))
x = np.arange(len(PAIR))
yb = [BL[BL.model == m].mean_payoff.mean() for m in PAIR]
yr = [RF[RF.model == m].mean_payoff.mean() for m in PAIR]
ax.bar(x - w/2, yb, w, color=BASE_C, label=N_BASE, edgecolor="white")
ax.bar(x + w/2, yr, w, color=RF_C, label=N_RF, edgecolor="white")
for i, (a, b) in enumerate(zip(yb, yr)):
    ax.text(i - w/2, a + .3, f"{a:.1f}", ha="center", fontsize=10, color=DARK)
    ax.text(i + w/2, b + .3, f"{b:.1f}", ha="center", fontsize=10.5,
            color=(TEAL if b > a else ACC), fontweight="bold")
ax.annotate("model phung phí ĐƯỢC LỢI\n(×9 tiền về túi)", xy=(0.36, 10.6), xytext=(1.05, 23.0),
            fontsize=10, color=TEAL, ha="center",
            arrowprops=dict(arrowstyle="->", color=TEAL, connectionstyle="arc3,rad=.2"))
ax.annotate("model vốn đã tiết kiệm\nlại THIỆT (trượt vạch)", xy=(2.36, 14.6), xytext=(3.35, 23.0),
            fontsize=10, color=ACC, ha="center",
            arrowprops=dict(arrowstyle="->", color=ACC, connectionstyle="arc3,rad=-.2"))
ax.set_xticks(x); ax.set_xticklabels([LBL[m] for m in PAIR], fontsize=10.5)
ax.set_ylabel("Tiền TB mỗi người mang về\n(trên 40)")
ax.set_title("Ai được lợi? Chỉ model trước đó tiêu hoang")
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
ax.set_ylim(0, 27.5)
save(fig, "R7_payoff.png")

# ============================================================================
# R8. Vân tay lựa chọn — mức 0 xuất hiện
# ============================================================================
fig, ax = plt.subplots(figsize=(9.0, 5.2))
y = np.arange(len(PAIR) * 2 + 1, dtype=float)
labels, bars = [], []
rows = []
for m in PAIR:
    rows.append((f"{LBL[m]} — {N_BASE.lower()}", TB[TB.model == m].c))
    rows.append((f"{LBL[m]} — {N_RF_SHORT}", TR[TR.model == m].c))
yy = np.arange(len(rows)); left = np.zeros(len(rows))
choice_c = {0: ACC, 2: YELL, 4: TEAL}
for v in [0, 2, 4]:
    frac = np.array([s.eq(v).mean() for _, s in rows])
    ax.barh(yy, frac, left=left, color=choice_c[v], label=f"đóng {v}", edgecolor="white", lw=1.1)
    for i, (fr, lf) in enumerate(zip(frac, left)):
        if fr > 0.06:
            ax.text(lf + fr/2, yy[i], f"{fr*100:.0f}%", va="center", ha="center",
                    fontsize=9.5, color="white", fontweight="bold")
    left += frac
ax.set_yticks(yy); ax.set_yticklabels([n for n, _ in rows], fontsize=9.5)
for i, (n, _) in enumerate(rows):
    if N_RF_SHORT in n:
        ax.get_yticklabels()[i].set_color(RF_C); ax.get_yticklabels()[i].set_fontweight("bold")
ax.invert_yaxis(); ax.set_xlim(0, 1); ax.set_xlabel("Tỉ lệ lượt chọn")
ax.set_title("Mức “0” gần như không tồn tại ở baseline, nay xuất hiện rõ")
ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.13))
ax.grid(axis="y", visible=False)
save(fig, "R8_choice.png")

# ============================================================================
# R9. Ngôn ngữ EN/VN
# ============================================================================
fig, ax = plt.subplots(figsize=(9.0, 4.6))
x = np.arange(len(RF_ALL))
en = [RF[(RF.model == m) & (RF.language == "en")].group_total.mean() for m in RF_ALL]
vn = [RF[(RF.model == m) & (RF.language == "vn")].group_total.mean() for m in RF_ALL]
ax.bar(x - w/2, en, w, color="#2C6E9B", label="Tiếng Anh", edgecolor="white")
ax.bar(x + w/2, vn, w, color="#E9C46A", label="Tiếng Việt", edgecolor="white")
for i, (a, b) in enumerate(zip(en, vn)):
    for xpos, v, inside in [(i - w/2, a, "white"), (i + w/2, b, DARK)]:
        if 118.0 <= v + 1.5 <= 123.0:    # nhãn sẽ đè vạch 120 -> in vào TRONG cột
            ax.text(xpos, v - 1.5, f"{v:.0f}", ha="center", va="top", fontsize=9.5,
                    color=inside, fontweight="bold")   # cột vàng nhạt -> chữ đậm màu
        else:
            ax.text(xpos, v + 1.5, f"{v:.0f}", ha="center", fontsize=9.5, color=DARK)
# vạch dừng trước lề phải để nhãn không nằm ĐÈ lên chính đường nét đứt
ax.axhline(120, color=DARK, ls=":", lw=2, xmax=0.865)
ax.text(6.55, 120, "mục tiêu 120", color=DARK, fontsize=10, ha="left", va="center")
# mũi tên trỏ đúng cột TIẾNG ANH (i-w/2), bản cũ trỏ nhầm sang cột Tiếng Việt
ax.annotate("Gemma-9B: bản Anh tụt DƯỚI vạch\n→ chỉ đạt 37% số game", xy=(1.81, 118.4),
            xytext=(2.75, 168), fontsize=10, color=ACC, arrowprops=dict(arrowstyle="->", color=ACC))
ax.set_xticks(x); ax.set_xticklabels([LBL[m] for m in RF_ALL], fontsize=10, rotation=12)
ax.set_ylabel("Tổng quỹ cuối game"); ax.set_ylim(105, 208); ax.set_xlim(-0.62, 7.5)
ax.set_title(f"Trục Anh–Việt vẫn còn ở nhánh “{N_RF}”")
ax.legend(frameon=False, loc="upper right")
save(fig, "R9_lang.png")

print("\nDone ->", OUT)
