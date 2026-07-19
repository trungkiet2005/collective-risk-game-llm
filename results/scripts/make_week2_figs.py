"""Sinh hình tuần 2 — large-model scaling + comprehension. Palette khớp deck tuần 1."""
from pathlib import Path
import json, glob
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
DARK, ACC, TEAL, YELL = "#264653", "#E76F51", "#2A9D8F", "#E9C46A"
# small = nhạt, large = đậm (cùng họ); llama = coral
COL = {"qwen25-7b-instruct": "#5FA8D3", "qwen25-32b-instruct": "#1B4965",
       "gemma2-9b-it": "#83C5BE", "gemma2-27b-it": "#14746F", "llama-3-1-8b": "#E76F51"}
LBL = {"qwen25-7b-instruct": "Qwen2.5-7B", "qwen25-32b-instruct": "Qwen2.5-32B",
       "gemma2-9b-it": "Gemma-2-9B", "gemma2-27b-it": "Gemma-2-27B", "llama-3-1-8b": "Llama-3.1-8B"}
ALLM = ["qwen25-7b-instruct", "qwen25-32b-instruct", "gemma2-9b-it", "gemma2-27b-it", "llama-3-1-8b"]
HUMAN = {0.9: 0.50, 0.5: 0.10, 0.1: 0.00}

def save(fig, name):
    fig.tight_layout(); fig.savefig(OUT / name, bbox_inches="tight", facecolor="white"); plt.close(fig)
    print("  ->", name)

# ---------------------------------------------------------------- load behavior
A = pd.read_csv(R / "open_source/crsd_all_models.csv")
A = A[A.experiment == "exp_baseline"].copy()   # layout exp-first: lọc baseline từ master
A["reach"] = A.target_reached.astype(int); A["risk"] = A.risk_probability.astype(float)

def load_turns(pattern):
    rows = []
    for f in glob.glob(str(R / pattern)):
        m = f.replace("\\", "/").split("/")[-2]
        for line in open(f, encoding="utf-8"):
            d = json.loads(line)
            rows.append((m, d["round"], d["contribution"], d.get("language"),
                         float(d.get("risk_probability", 0))))
    return rows
T = pd.DataFrame(load_turns("open_source/exp_baseline/*/turns.jsonl"),
                 columns=["model", "round", "c", "lang", "risk"])

# ============================================================================
# L1. SCALING headline — contribution small vs large (Qwen sụp, Gemma đứng yên)
# ============================================================================
gt = A.groupby("model").group_total.mean()
fig, ax = plt.subplots(figsize=(8.2, 4.6))
fams = [("Qwen", "qwen25-7b-instruct", "qwen25-32b-instruct"),
        ("Gemma", "gemma2-9b-it", "gemma2-27b-it")]
xc = [0, 1]
# nhãn endpoint lớn lệch dọc để không chồng (Qwen-32B & Gemma-27B gần trùng ~127/126)
lg_voff = {"qwen25-32b-instruct": (10, "bottom"), "gemma2-27b-it": (-10, "top")}
for fam, sm, lg in fams:
    ys = [gt[sm], gt[lg]]
    ax.plot(xc, ys, "-", color="#aab4b8", lw=2.6, zorder=1)
    ax.scatter(xc[0], ys[0], s=150, color=COL[sm], zorder=3, edgecolor="white", lw=1.5)
    ax.scatter(xc[1], ys[1], s=150, color=COL[lg], zorder=3, edgecolor="white", lw=1.5)
    ax.annotate(f"{ys[1]-ys[0]:+.0f}", xy=(0.42, (ys[0]+ys[1])/2), fontsize=12,
                color=ACC if abs(ys[1]-ys[0]) > 10 else "#7a8a90", fontweight="bold",
                ha="center", va="center")
    ax.text(-0.06, ys[0], LBL[sm], ha="right", va="center", fontsize=11, color=COL[sm], fontweight="bold")
    voff, valign = lg_voff[lg]
    ax.annotate(LBL[lg], xy=(1, ys[1]), xytext=(10, voff), textcoords="offset points",
                ha="left", va=valign, fontsize=11, color=COL[lg], fontweight="bold")
ax.axhline(120, color=DARK, ls=":", lw=1.8); ax.text(0.0, 116, "mục tiêu 120", color=DARK, fontsize=10, ha="center")
ax.axhline(gt["llama-3-1-8b"], color=ACC, ls="--", lw=1.4, alpha=.7)
ax.text(1.34, gt["llama-3-1-8b"], "Llama-3.1-8B (185)", color=ACC, fontsize=9.5, va="center")
ax.set_xticks(xc); ax.set_xticklabels(["model NHỎ (7-9B)", "model LỚN (27-32B)"])
ax.set_xlim(-0.55, 1.7); ax.set_ylim(110, 250)
ax.set_ylabel("Tổng đóng góp / game (trên 240)")
ax.set_title("Phóng to model → Qwen thôi hào phóng, hội tụ về “vừa đủ 120”")
ax.grid(axis="x", visible=False)
save(fig, "L1_scaling_contrib.png")

# ============================================================================
# L2. Reach vs risk — large models VẪN phẳng 100% (scaling không cứu risk-sens)
# ============================================================================
risks = [0.9, 0.5, 0.1]
rr = A.groupby(["model", "risk"]).reach.mean()
fig, ax = plt.subplots(figsize=(7.6, 4.6))
for m in ["qwen25-32b-instruct", "gemma2-27b-it"]:
    ax.plot(risks, [rr[(m, k)] for k in risks], "o-", color=COL[m], lw=2.8, ms=10, label=LBL[m])
ax.plot(risks, [1.0]*3, ":", color="#8a989e", lw=1.6)
ax.plot(risks, [HUMAN[k] for k in risks], "s--", color=DARK, lw=2.6, ms=9, label="Người (Milinski 2008)")
ax.annotate("model lớn vẫn ~100%\nbất kể rủi ro", xy=(0.5, 0.98), xytext=(0.5, 0.72),
            ha="center", color=DARK, fontsize=11,
            arrowprops=dict(arrowstyle="->", color=DARK))
ax.set_xlabel("Xác suất thảm hoạ (rủi ro)"); ax.set_ylabel("Tỉ lệ đạt mục tiêu")
ax.set_title("Phóng to KHÔNG phục hồi nhạy-rủi-ro")
ax.set_ylim(-0.05, 1.12); ax.set_xticks(risks); ax.invert_xaxis(); ax.legend(loc="center right", frameon=False)
save(fig, "L2_scaling_reach.png")

# ============================================================================
# L3. Choice fingerprint flip — Qwen 7B(4) -> 32B(2), hội tụ về Gemma
# ============================================================================
fig, ax = plt.subplots(figsize=(8.4, 4.4))
y = np.arange(len(ALLM)); choice_c = {0: ACC, 2: YELL, 4: TEAL}
left = np.zeros(len(ALLM))
for v in [0, 2, 4]:
    frac = np.array([T[T.model == m].c.eq(v).mean() for m in ALLM])
    ax.barh(y, frac, left=left, color=choice_c[v], label=f"đóng {v}", edgecolor="white", lw=1.2)
    for i, (fr, lf) in enumerate(zip(frac, left)):
        if fr > 0.05:
            ax.text(lf + fr/2, y[i], f"{fr*100:.0f}%", va="center", ha="center",
                    fontsize=10.5, color="white", fontweight="bold")
    left += frac
ax.set_yticks(y); ax.set_yticklabels([LBL[m] for m in ALLM]); ax.invert_yaxis()
ax.set_xlim(0, 1); ax.set_xlabel("Tỉ lệ lượt chọn mỗi mức đóng góp")
ax.set_title("“Vân tay” lật: Qwen-7B kịch trần (4) → Qwen-32B về “2” như Gemma")
ax.legend(ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.16)); ax.grid(False)
save(fig, "L3_choice_flip.png")

# ============================================================================
# L4. Round dynamics — large models: phẳng rồi RAMP cuối game (deadline)
# ============================================================================
gr = T.groupby(["model", "round"]).c.mean().reset_index()
fig, ax = plt.subplots(figsize=(7.8, 4.5))
for m in ALLM:
    s = gr[gr.model == m].sort_values("round")
    lw = 2.8 if "32b" in m or "27b" in m else 1.8
    al = 1.0 if ("32b" in m or "27b" in m) else 0.55
    ax.plot(s["round"], s.c, "o-", color=COL[m], lw=lw, ms=5, label=LBL[m], alpha=al)
ax.annotate("ramp sát deadline\n(đóng mạnh vì game sắp hết)", xy=(9.5, 2.87), xytext=(6.0, 3.5),
            fontsize=10, color=DARK, ha="center", arrowprops=dict(arrowstyle="->", color=DARK))
ax.set_xlabel("Vòng (trên 10)"); ax.set_ylabel("Đóng góp TB / người")
ax.set_title("Vẫn TĂNG dần — ngược người; model lớn “ép vạch” muộn hơn")
ax.set_xticks(range(1, 11)); ax.set_ylim(1.6, 4.2); ax.legend(frameon=False, ncol=2, fontsize=9.5, loc="upper left")
save(fig, "L4_scaling_dynamics.png")

# ============================================================================
# L5. EN vs VN ở scale — Gemma-27B "đảo dấu" so với Gemma-9B
# ============================================================================
lb = A.groupby(["model", "language"]).group_total.mean().unstack()
fig, ax = plt.subplots(figsize=(8.2, 4.4))
x = np.arange(len(ALLM)); w = 0.36
for i, lang in enumerate(["en", "vn"]):
    ax.bar(x + (i-0.5)*w, [lb.loc[m, lang] for m in ALLM], w,
           label={"en": "Tiếng Anh", "vn": "Tiếng Việt"}[lang], color=[DARK, ACC][i])
ax.axhline(120, color="#888", ls=":", lw=1.5, label="Mục tiêu 120")
for i, m in enumerate(ALLM):
    d = lb.loc[m, "vn"] - lb.loc[m, "en"]
    ax.text(x[i], max(lb.loc[m, "en"], lb.loc[m, "vn"]) + 5, f"{d:+.0f}", ha="center",
            fontsize=10, color=ACC if abs(d) > 8 else DARK, fontweight="bold")
ax.set_xticks(x); ax.set_xticklabels([LBL[m] for m in ALLM], rotation=14, ha="right")
ax.set_ylabel("Tổng đóng góp (trên 240)"); ax.set_ylim(0, 260)
ax.set_title("Trục ngôn ngữ co lại khi phóng to (Llama vẫn lệch mạnh nhất)")
ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.18))
save(fig, "L5_scaling_lang.png")

# ============================================================================
#  COMPREHENSION
# ============================================================================
frames = []
for f in glob.glob(str(R / "open_source/exp_comprehension/*/comprehension_summary.csv")):
    frames.append(pd.read_csv(f))
C = pd.concat(frames, ignore_index=True)
CMODELS = ["qwen25-7b-instruct", "gemma2-9b-it", "llama-3-1-8b"]
CCOL = {"qwen25-7b-instruct": "#1B4965", "gemma2-9b-it": "#2A9D8F", "llama-3-1-8b": "#E76F51"}
CLBL = {"qwen25-7b-instruct": "Qwen2.5-7B", "gemma2-9b-it": "Gemma-2-9B", "llama-3-1-8b": "Llama-3.1-8B"}

def acc_by(df, by, col):
    a = df.groupby(by).agg(n=("n", "sum"), nc=("n_correct", "sum"))
    a["acc"] = a.nc / a.n.replace(0, np.nan)
    return a["acc"].unstack(col)

# K1. Headline — accuracy theo 3 trục Rules|Time|State
cat = acc_by(C, ["model", "category"], "category").reindex(CMODELS)
fig, ax = plt.subplots(figsize=(7.8, 4.5))
cats = ["rules", "time", "state"]; x = np.arange(len(cats)); w = 0.25
for j, m in enumerate(CMODELS):
    ax.bar(x + (j-1)*w, [cat.loc[m, c] for c in cats], w, color=CCOL[m], label=CLBL[m])
    for i, c in enumerate(cats):
        ax.text(x[i]+(j-1)*w, cat.loc[m, c]+0.015, f"{cat.loc[m,c]*100:.0f}", ha="center", fontsize=9, color=DARK)
ax.axhline(0.9, color="#888", ls=":", lw=1.2)
ax.set_xticks(x); ax.set_xticklabels(["RULES\n(luật tĩnh)", "TIME\n(tra lịch sử)", "STATE\n(cộng dồn)"])
ax.set_ylabel("Accuracy đọc-hiểu"); ax.set_ylim(0, 1.12)
ax.set_title("Hiểu LUẬT & đọc LỊCH SỬ tốt — sụp ở CỘNG DỒN trạng thái")
ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.13))
save(fig, "K1_comp_category.png")

# K2. CONTROL money-shot — đọc (own_remaining) vs cộng (state_pool), pool ẩn/hiện
ctl = acc_by(C[C.question_id.isin(["state_own_remaining", "state_pool"])],
             ["model", "show_cumulative", "question_id"], "question_id")
fig, ax = plt.subplots(figsize=(8.4, 4.6))
groups = [("đọc số IN SẴN\n(own_remaining)", "state_own_remaining", None),
          ("CỘNG dồn, pool ẨN\n(state_pool, showcum=0)", "state_pool", 0),
          ("CỘNG dồn, pool HIỆN\n(state_pool, showcum=1)", "state_pool", 1)]
x = np.arange(len(groups)); w = 0.25
for j, m in enumerate(CMODELS):
    vals = []
    for _, q, sc in groups:
        if q == "state_own_remaining":
            v = C[(C.model==m)&(C.question_id==q)]
        else:
            v = C[(C.model==m)&(C.question_id==q)&(C.show_cumulative==sc)]
        vals.append(v.n_correct.sum()/v.n.sum())
    ax.bar(x + (j-1)*w, vals, w, color=CCOL[m], label=CLBL[m])
    for i, vv in enumerate(vals):
        ax.text(x[i]+(j-1)*w, vv+0.015, f"{vv*100:.0f}", ha="center", fontsize=9, color=DARK)
ax.axvspan(0.5, 1.5, color=ACC, alpha=0.06)
ax.set_xticks(x); ax.set_xticklabels([g[0] for g in groups], fontsize=10)
ax.set_ylabel("Accuracy"); ax.set_ylim(0, 1.12)
ax.set_title("Đọc được ≠ cộng được: ẩn tổng → sụp 10–21%, in tổng → ~trần")
ax.legend(frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.22)); ax.grid(axis="x", visible=False)
save(fig, "K2_comp_read_vs_add.png")

# K3. RISK GATE — họ BIẾT rủi ro (rules_risk_pct ~100%) -> phớt lờ là HÀNH VI
rr = C[C.question_id == "rules_risk_pct"]
acc_rg = acc_by(rr, ["model", "risk_probability"], "risk_probability").reindex(CMODELS)
fig, ax = plt.subplots(figsize=(7.8, 4.5))
risks3 = [0.9, 0.5, 0.1]; x = np.arange(len(risks3)); w = 0.25
for j, m in enumerate(CMODELS):
    ax.bar(x + (j-1)*w, [acc_rg.loc[m, r] for r in risks3], w, color=CCOL[m], label=CLBL[m])
ax.set_xticks(x); ax.set_xticklabels([f"rủi ro {r:g}  (đáp đúng {int(r*100)}%)" for r in risks3])
ax.set_ylabel("Accuracy câu “rủi ro bao nhiêu %”"); ax.set_ylim(0, 1.15)
ax.set_title("Họ TRẢ ĐÚNG mức rủi ro ~100%\n→ phớt-lờ-rủi-ro là LỰA CHỌN, không phải hiểu sai", fontsize=14)
ax.legend(frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.2))
save(fig, "K3_comp_risk_gate.png")

# K4. EN vs VN — state accuracy rớt ở tiếng Việt (số học bị ngôn ngữ đánh)
fig, ax = plt.subplots(figsize=(8.2, 4.5))
cats = ["rules", "time", "state"]; x = np.arange(len(cats)); w = 0.36
# tính accuracy theo n cho từng category × ngôn ngữ (gộp model)
def cat_lang(dfl):
    a = dfl.groupby("category").agg(n=("n","sum"), nc=("n_correct","sum"))
    return (a.nc/a.n)
ce, cv = cat_lang(C[C.language=="en"]), cat_lang(C[C.language=="vn"])
ax.bar(x - w/2, [ce[c] for c in cats], w, label="Tiếng Anh", color=DARK)
ax.bar(x + w/2, [cv[c] for c in cats], w, label="Tiếng Việt", color=ACC)
for i, c in enumerate(cats):
    d = cv[c]-ce[c]
    ax.text(x[i], max(ce[c], cv[c])+0.02, f"{d*100:+.0f}pp", ha="center", fontsize=10,
            color=ACC if d < -0.03 else DARK, fontweight="bold")
ax.set_xticks(x); ax.set_xticklabels(["RULES", "TIME", "STATE"]); ax.set_ylim(0, 1.12)
ax.set_ylabel("Accuracy (gộp 3 model)")
ax.set_title("Tiếng Việt đánh đúng vào CỘNG DỒN trạng thái")
ax.legend(frameon=False, ncol=2, loc="lower center", bbox_to_anchor=(0.5, -0.16))
save(fig, "K4_comp_lang.png")

# K5. Figure-1 analog đầy đủ — accuracy mỗi câu, nhóm Rules|Time|State, 2 panel showcum
try:
    import sys; sys.path.insert(0, str(R.parent))
    from crsd.engine.comprehension import REGISTRY
    qorder = [q.id for q in REGISTRY]; qcat = {q.id: q.category for q in REGISTRY}
except Exception:
    qorder = sorted(C.question_id.unique()); qcat = dict(zip(C.question_id, C.category))
present = [q for q in qorder if q in set(C.question_id)]
fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
for ax, sc in zip(axes, [0, 1]):
    d_sc = C[C.show_cumulative == sc]
    xq = np.arange(len(present))
    for j, m in enumerate(CMODELS):
        accs = []
        for q in present:
            dd = d_sc[(d_sc.model == m) & (d_sc.question_id == q)]
            accs.append(dd.n_correct.sum()/dd.n.sum() if dd.n.sum() else np.nan)
        ax.plot(xq + (j-1)*0.0, accs, "o", ms=6, color=CCOL[m], label=CLBL[m] if sc == 0 else None)
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
axes[0].set_ylabel("Response accuracy"); axes[0].legend(frameon=False, fontsize=9, loc="lower left")
fig.suptitle("Comprehension theo từng câu hỏi (Rules | Time | State) — CRG", y=1.0)
save(fig, "K5_comp_figure1.png")

print("\n[OK] figs ->", OUT)
