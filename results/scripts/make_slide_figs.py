"""Sinh bộ hình thuyết trình — palette hài hoà, theo từng experiment."""
from pathlib import Path
import json, glob, os
import pandas as pd, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent / "data"   # results/data (script dưới results/scripts/)
OUT = Path(__file__).resolve().parents[2] / "slides" / "week1" / "figs"; OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 150, "font.size": 13,
    "axes.titlesize": 15, "axes.labelsize": 13, "legend.fontsize": 11,
    "xtick.labelsize": 11, "ytick.labelsize": 11, "axes.grid": True,
    "grid.alpha": 0.22, "axes.spines.top": False, "axes.spines.right": False,
    "font.family": "DejaVu Sans", "axes.edgecolor": "#52646b", "text.color": "#264653",
    "axes.labelcolor": "#264653", "xtick.color": "#264653", "ytick.color": "#264653",
})
# Palette hài hoà với deck (#264653 / #2A9D8F / #E76F51)
COL = {"qwen25-7b-instruct": "#1B4965", "llama-3-1-8b": "#E76F51", "gemma2-9b-it": "#2A9D8F"}
LBL = {"qwen25-7b-instruct": "Qwen2.5-7B", "llama-3-1-8b": "Llama-3.1-8B", "gemma2-9b-it": "Gemma-2-9B"}
MODELS = ["qwen25-7b-instruct", "llama-3-1-8b", "gemma2-9b-it"]
HUMAN = {0.9: 0.50, 0.5: 0.10, 0.1: 0.00}
DARK, ACC = "#264653", "#E76F51"
TEAL, YELL = "#2A9D8F", "#E9C46A"

def load(exp):
    d = pd.read_csv(ROOT / f"{exp}/crsd_results/crsd_all_models.csv")
    d["reach"] = d.target_reached.astype(int); d["risk"] = d.risk_probability.astype(float)
    d["nsel"] = d.persona_seats.fillna("").str.count("S")
    return d
base, mem, frm, per = load("baseline"), load("memory"), load("framing"), load("persona")

def save(fig, name):
    fig.tight_layout(); fig.savefig(OUT / name, bbox_inches="tight", facecolor="white"); plt.close(fig)
    print("  ->", name)

# A. Reach vs risk (LLM gộp vs human) ----------------------------------------
fig, ax = plt.subplots(figsize=(7.2, 4.4))
risks = [0.9, 0.5, 0.1]
ax.plot(risks, [1.0]*3, "o-", color=DARK, lw=3, ms=11, label="Cả 3 LLM (Qwen=Llama=Gemma)")
ax.plot(risks, [HUMAN[k] for k in risks], "s--", color=ACC, lw=2.6, ms=9, label="Người (Milinski 2008)")
ax.annotate("phẳng ở 100%", xy=(0.5, 1.0), xytext=(0.5, 0.87), ha="center", color=DARK, fontsize=11)
ax.set_xlabel("Xác suất thảm hoạ (rủi ro)"); ax.set_ylabel("Tỉ lệ đạt mục tiêu")
ax.set_title("LLM đạt mục tiêu bất kể rủi ro")
ax.set_ylim(-0.04, 1.12); ax.set_xticks(risks); ax.invert_xaxis(); ax.legend(loc="center right", frameon=False)
save(fig, "A_reach_vs_risk.png")

# B. Contribution vs risk ----------------------------------------------------
gc = base.groupby(["model", "risk"]).group_total.mean().reset_index()
fig, ax = plt.subplots(figsize=(7.2, 4.4))
for m in MODELS:
    s = gc[gc.model == m].sort_values("risk")
    ax.plot(s.risk, s.group_total, "o-", color=COL[m], lw=2.4, ms=8, label=LBL[m])
ax.axhline(120, color=DARK, ls=":", lw=1.8, label="Mục tiêu = 120")
ax.set_xlabel("Xác suất thảm hoạ (rủi ro)"); ax.set_ylabel("Tổng đóng góp (trên 240)")
ax.set_title("Đóng góp vượt mục tiêu, phẳng theo rủi ro")
ax.set_xticks(risks); ax.invert_xaxis(); ax.legend(loc="center left", frameon=False)
save(fig, "B_contrib_vs_risk.png")

# C. Round dynamics ----------------------------------------------------------
rows = []
for f in glob.glob(str(ROOT / "baseline/crsd_results/*/exp_baseline/turns.jsonl")):
    m = f.replace("\\", "/").split("/")[-3]
    for line in open(f, encoding="utf-8"):
        d = json.loads(line); rows.append((m, d["round"], d["contribution"]))
gr = pd.DataFrame(rows, columns=["model", "round", "c"]).groupby(["model", "round"]).c.mean().reset_index()
fig, ax = plt.subplots(figsize=(7.2, 4.4))
for m in MODELS:
    s = gr[gr.model == m].sort_values("round")
    ax.plot(s["round"], s.c, "o-", color=COL[m], lw=2.4, ms=6, label=LBL[m])
ax.annotate("Người: hợp tác GIẢM dần\n(+ phản bội cuối game)", xy=(7.4, 1.15),
            fontsize=10.5, color=DARK, ha="center",
            bbox=dict(boxstyle="round", fc="#fdeee7", ec=ACC))
ax.set_xlabel("Vòng (trên 10)"); ax.set_ylabel("Đóng góp TB / người")
ax.set_title("LLM hợp tác TĂNG dần — ngược con người")
ax.set_xticks(range(1, 11)); ax.set_ylim(0, 4.2); ax.legend(loc="lower right", frameon=False)
save(fig, "C_round_dynamics.png")

# M. Memory: full_history vs scratchpad (reach + contribution) ---------------
mm = (pd.concat([base.assign(cond="full_history"), mem.assign(cond="scratchpad")])
        .groupby(["model", "cond"]).agg(reach=("reach", "mean"), contrib=("group_total", "mean")).reset_index())
fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.2))
x = np.arange(len(MODELS)); w = 0.36
for i, c in enumerate(["full_history", "scratchpad"]):
    axes[0].bar(x + (i-0.5)*w, [mm[(mm.model==m)&(mm.cond==c)].reach.values[0] for m in MODELS], w,
                label=c, color=[DARK, ACC][i])
axes[0].set_xticks(x); axes[0].set_xticklabels([LBL[m] for m in MODELS], rotation=12, ha="right")
axes[0].set_ylabel("Tỉ lệ đạt mục tiêu"); axes[0].set_title("Reach: chỉ Gemma bị ảnh hưởng")
axes[0].set_ylim(0, 1.08); axes[0].legend(frameon=False, fontsize=10)
axes[0].annotate("100→77%", xy=(2.18, 0.77), color=ACC, fontsize=10, ha="left")
for i, c in enumerate(["full_history", "scratchpad"]):
    axes[1].bar(x + (i-0.5)*w, [mm[(mm.model==m)&(mm.cond==c)].contrib.values[0] for m in MODELS], w,
                label=c, color=[DARK, ACC][i])
axes[1].axhline(120, color="#888", ls=":", lw=1.5)
axes[1].set_xticks(x); axes[1].set_xticklabels([LBL[m] for m in MODELS], rotation=12, ha="right")
axes[1].set_ylabel("Tổng đóng góp"); axes[1].set_title("Đóng góp gần như không đổi")
axes[1].legend(frameon=False, fontsize=10)
save(fig, "M_memory.png")

# FR. Framing: dumbbell trung tính -> khung ích kỷ (tổng tuyệt đối), EN vs VN --
neu = pd.concat([base, mem]).groupby(["model", "language"]).group_total.mean()
fra = frm.groupby(["model", "language"]).group_total.mean()
rows = [(m, lang, neu[(m, lang)], fra[(m, lang)]) for m in MODELS for lang in ["en", "vn"]]
fig, ax = plt.subplots(figsize=(7.8, 4.6))
y = np.arange(len(rows))[::-1]; ylabels = []
for yi, (m, lang, n, f) in zip(y, rows):
    ax.plot([n, f], [yi, yi], "-", color="#aab4b8", lw=2.6, zorder=1, solid_capstyle="round")
    ax.scatter(n, yi, s=95, color=TEAL, zorder=3, edgecolor="white", lw=1.3)
    ax.scatter(f, yi, s=95, color=ACC, zorder=3, edgecolor="white", lw=1.3)
    ax.annotate(f"{f-n:+.0f}", xy=(min(n, f), yi), xytext=(-8, 0), textcoords="offset points",
                ha="right", va="center", fontsize=10,
                color=ACC if (f-n) < -1 else "#7a8a90", fontweight="bold")
    ylabels.append(f"{LBL[m]} · {'VN' if lang=='vn' else 'EN'}")
ax.axvline(120, color=DARK, ls=":", lw=1.6)
ax.text(120, len(rows)-0.35, "mục tiêu 120", color=DARK, fontsize=9, va="bottom", ha="center")
ax.set_yticks(y); ax.set_yticklabels(ylabels)
ax.set_ylim(-0.6, len(rows)-0.1); ax.set_xlim(90, 250)
ax.set_xlabel("Tổng đóng góp (trên 240)")
ax.set_title("Framing kéo đóng góp xuống — đoạn VN dài hơn hẳn")
ax.legend([plt.Line2D([], [], marker="o", ls="", color=TEAL, ms=10, mec="white"),
           plt.Line2D([], [], marker="o", ls="", color=ACC, ms=10, mec="white")],
          ["trung tính", "khung ích kỷ"], frameon=False, loc="lower right", fontsize=10)
ax.grid(axis="y", visible=False)
save(fig, "FR_framing.png")

# FR2. Framing × MEMORY (2x2): Δ contribution (framed − neutral) theo memory mode
fr_fh = frm[frm.memory_mode == "full_history"].groupby("model").group_total.mean()
fr_sc = frm[frm.memory_mode == "scratchpad"].groupby("model").group_total.mean()
neu_fh = base.groupby("model").group_total.mean()    # neutral full_history = baseline
neu_sc = mem.groupby("model").group_total.mean()     # neutral scratchpad  = memory exp
fig, ax = plt.subplots(figsize=(7.6, 4.4))
x = np.arange(len(MODELS)); w = 0.36
for i, (lab, fr_, neu_, col) in enumerate([
        ("full-history (như baseline)", fr_fh, neu_fh, DARK),
        ("scratchpad (như memory)", fr_sc, neu_sc, ACC)]):
    ax.bar(x + (i-0.5)*w, [fr_[m] - neu_[m] for m in MODELS], w, label=lab, color=col)
ax.axhline(0, color="#444", lw=1)
ax.set_xticks(x); ax.set_xticklabels([LBL[m] for m in MODELS])
ax.set_ylabel("Δ tổng đóng góp (framed − neutral)")
ax.set_title("Trí nhớ KHUẾCH ĐẠI framing — full-history nhạy hơn")
ax.legend(frameon=False, fontsize=10, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.12))
save(fig, "FR2_framing_memory.png")

# D. Persona reach vs #selfish -----------------------------------------------
pr = per.groupby(["model", "nsel"]).reach.mean().reset_index()
fig, ax = plt.subplots(figsize=(7.2, 4.4))
for m in MODELS:
    s = pr[pr.model == m].sort_values("nsel")
    ax.plot(s.nsel, s.reach, "o-", color=COL[m], lw=2.4, ms=8, label=LBL[m])
ax.set_xlabel("Số tác nhân ích kỷ trong nhóm (trên 6)"); ax.set_ylabel("Tỉ lệ đạt mục tiêu")
ax.set_title("Persona — đòn bẩy hiệu quả nhất")
ax.set_ylim(-0.04, 1.08); ax.set_xticks(range(0, 7)); ax.legend(frameon=False)
save(fig, "D_persona_reach.png")

# E. Persona linear engine ---------------------------------------------------
pc = per.groupby(["model", "nsel"]).group_total.mean().reset_index()
fig, ax = plt.subplots(figsize=(7.2, 4.4))
for m in MODELS:
    s = pc[pc.model == m].sort_values("nsel")
    b, a = np.polyfit(s.nsel, s.group_total, 1)
    ax.scatter(s.nsel, s.group_total, color=COL[m], s=42, zorder=3)
    ax.plot([0, 6], [a, a+6*b], "-", color=COL[m], lw=2.2, label=f"{LBL[m]}: {a:.0f} − {abs(b):.1f}·k")
ax.axhline(120, color=DARK, ls=":", lw=2, label="Mục tiêu = 120")
ax.set_xlabel("Số tác nhân ích kỷ  (k)"); ax.set_ylabel("Tổng đóng góp")
ax.set_title("Một động cơ tuyến tính → ba chế độ")
ax.set_xticks(range(0, 7)); ax.legend(fontsize=10, frameon=False)
save(fig, "E_persona_linear.png")

# G. Individual disposition effect -------------------------------------------
rows = []
for f in glob.glob(str(ROOT / "persona/crsd_results/*/exp_persona/turns.jsonl")):
    m = f.replace("\\", "/").split("/")[-3]
    for line in open(f, encoding="utf-8"):
        d = json.loads(line); rows.append((m, d.get("disposition"), d["contribution"]))
dd = pd.DataFrame(rows, columns=["model", "disp", "c"])
piv = dd[dd.disp.isin(["selfish", "cooperative"])].groupby(["model", "disp"]).c.mean().unstack()
fig, ax = plt.subplots(figsize=(7.2, 4.2))
x = np.arange(len(MODELS)); w = 0.36
ax.bar(x - w/2, [piv.loc[m, "cooperative"] for m in MODELS], w, label="persona hợp tác", color="#2A9D8F")
ax.bar(x + w/2, [piv.loc[m, "selfish"] for m in MODELS], w, label="persona ích kỷ", color=ACC)
ax.set_xticks(x); ax.set_xticklabels([LBL[m] for m in MODELS])
ax.set_ylabel("Đóng góp TB / lượt"); ax.set_title("Persona ăn ở cấp cá nhân — Qwen ít nghe nhất")
ax.set_ylim(0, 4.3); ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.12))
for m, xi in zip(MODELS, x):
    ax.text(xi, 4.05, f"Δ={piv.loc[m,'cooperative']-piv.loc[m,'selfish']:.2f}", ha="center", fontsize=10, color=DARK)
save(fig, "G_disposition.png")

# ============================================================================
#  HÌNH BỔ SUNG — đào sâu từng phần (số liệu bám results/insights.md đã verify)
# ============================================================================
INNER = {"baseline": "exp_baseline", "memory": "exp_memory_ablation",
         "framing": "exp_framing", "persona": "exp_persona"}

def load_turns(exp):
    rows = []
    for f in glob.glob(str(ROOT / f"{exp}/crsd_results/*/{INNER[exp]}/turns.jsonl")):
        m = f.replace("\\", "/").split("/")[-3]
        for line in open(f, encoding="utf-8"):
            d = json.loads(line)
            rows.append((m, d["game_id"], d["round"], d["player"], d["contribution"],
                         d.get("disposition"), d.get("language"),
                         float(d.get("risk_probability", 0)), d.get("memory_mode"),
                         bool(d.get("framing", False))))
    return pd.DataFrame(rows, columns=["model", "gid", "round", "player", "c",
                                       "disp", "lang", "risk", "mem", "framing"])
tb, tm = load_turns("baseline"), load_turns("memory")

# ---- BASELINE ----------------------------------------------------------------
# H. "Vân tay" — phân phối lựa chọn {0,2,4} mỗi model (kiểm duyệt biên) ---------
fig, ax = plt.subplots(figsize=(7.8, 4.0))
y = np.arange(len(MODELS)); choice_c = {0: ACC, 2: YELL, 4: TEAL}
left = np.zeros(len(MODELS))
for v in [0, 2, 4]:
    frac = np.array([tb[tb.model == m].c.eq(v).mean() for m in MODELS])
    ax.barh(y, frac, left=left, color=choice_c[v], label=f"đóng {v}", edgecolor="white", lw=1.2)
    for i, (fr, lf) in enumerate(zip(frac, left)):
        if fr > 0.05:
            ax.text(lf + fr/2, y[i], f"{fr*100:.0f}%", va="center", ha="center",
                    fontsize=11, color="white", fontweight="bold")
    left += frac
ax.set_yticks(y); ax.set_yticklabels([LBL[m] for m in MODELS]); ax.invert_yaxis()
ax.set_xlim(0, 1); ax.set_xlabel("Tỉ lệ lượt chọn mỗi mức đóng góp")
ax.set_title("“Vân tay” lựa chọn — mỗi model kẹt ở một biên khác")
ax.legend(ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.18)); ax.grid(False)
save(fig, "H_choice_dist.png")

# H2. "Vân tay" tách theo 3 mức rủi ro (risk-insensitive ở cấp lựa chọn?) -----
risks3 = [0.9, 0.5, 0.1]
fig, axes = plt.subplots(1, 3, figsize=(10.4, 3.9), sharey=True)
for ax, m in zip(axes, MODELS):
    xpos = np.arange(len(risks3)); bottom = np.zeros(len(risks3))
    for v in [0, 2, 4]:
        frac = np.array([tb[(tb.model == m) & (tb.risk == r)].c.eq(v).mean() for r in risks3])
        ax.bar(xpos, frac, 0.62, bottom=bottom, color=choice_c[v], edgecolor="white", lw=1,
               label=f"đóng {v}" if m == MODELS[0] else None)
        for i, (fr, bt) in enumerate(zip(frac, bottom)):
            if fr > 0.08:
                ax.text(xpos[i], bt + fr/2, f"{fr*100:.0f}", va="center", ha="center",
                        fontsize=9.5, color="white", fontweight="bold")
        bottom += frac
    ax.set_title(LBL[m]); ax.set_xticks(xpos); ax.set_xticklabels([f"{r:g}" for r in risks3])
    ax.set_xlabel("rủi ro"); ax.set_ylim(0, 1.0); ax.grid(False)
axes[0].set_ylabel("Tỉ lệ lượt chọn")
handles = [plt.Rectangle((0, 0), 1, 1, fc=choice_c[v]) for v in [0, 2, 4]]
fig.legend(handles, ["đóng 0", "đóng 2", "đóng 4"], ncol=3, frameon=False,
           loc="lower center", bbox_to_anchor=(0.5, -0.02))
fig.suptitle("“Vân tay” gần như không đổi theo rủi ro — phớt lờ rủi ro cả ở cấp lựa chọn", fontsize=13.5)
fig.subplots_adjust(bottom=0.22)
save(fig, "H2_choice_dist_risk.png")

# I. Ngôn ngữ EN vs VN ở baseline (gần như null) ------------------------------
lb = base.groupby(["model", "language"]).group_total.mean().unstack()
fig, ax = plt.subplots(figsize=(7.2, 4.2))
x = np.arange(len(MODELS)); w = 0.36
for i, lang in enumerate(["en", "vn"]):
    ax.bar(x + (i-0.5)*w, [lb.loc[m, lang] for m in MODELS], w,
           label={"en": "Tiếng Anh", "vn": "Tiếng Việt"}[lang], color=[DARK, ACC][i])
ax.axhline(120, color="#888", ls=":", lw=1.5, label="Mục tiêu 120")
for i, m in enumerate(MODELS):
    ax.text(x[i], max(lb.loc[m, "en"], lb.loc[m, "vn"]) + 5,
            f"Δ={abs(lb.loc[m,'en']-lb.loc[m,'vn']):.0f}", ha="center", fontsize=10, color=DARK)
ax.set_xticks(x); ax.set_xticklabels([LBL[m] for m in MODELS])
ax.set_ylabel("Tổng đóng góp (trên 240)"); ax.set_ylim(0, 260)
ax.set_title("Baseline: Qwen/Gemma ổn định, Llama đã giảm ở tiếng Việt"); ax.legend(frameon=False, ncol=3,
            loc="upper center", bbox_to_anchor=(0.5, -0.12))
save(fig, "I_lang_baseline.png")

# ---- MEMORY ------------------------------------------------------------------
# M2. Động lực vòng: full-history vs scratchpad ------------------------------
gf = tb.groupby(["model", "round"]).c.mean().reset_index()
gs = tm.groupby(["model", "round"]).c.mean().reset_index()
fig, ax = plt.subplots(figsize=(7.8, 4.4))
for m in MODELS:
    a = gf[gf.model == m].sort_values("round"); ax.plot(a["round"], a.c, "-", color=COL[m], lw=2.6, ms=5, marker="o")
    b = gs[gs.model == m].sort_values("round"); ax.plot(b["round"], b.c, "--", color=COL[m], lw=2.2, ms=5, marker="s", alpha=0.85)
mh = [plt.Line2D([], [], color=DARK, ls="-", lw=2.6), plt.Line2D([], [], color=DARK, ls="--", lw=2.2)]
leg1 = ax.legend(mh, ["full-history (baseline)", "scratchpad (memory)"], frameon=False, loc="lower right", fontsize=10)
ax.add_artist(leg1)
ax.legend([plt.Line2D([], [], color=COL[m], lw=2.6) for m in MODELS], [LBL[m] for m in MODELS],
          frameon=False, loc="upper left", fontsize=10)
ax.annotate("Qwen dè dặt ngay vòng 1\n(chỉ vì prompt sổ tay dài hơn)", xy=(1, 2.62), xytext=(2.2, 1.35),
            fontsize=9.5, color=DARK, arrowprops=dict(arrowstyle="->", color=DARK))
ax.set_xlabel("Vòng (trên 10)"); ax.set_ylabel("Đóng góp TB / người")
ax.set_title("Trí nhớ giới hạn đổi quỹ đạo Qwen, không đổi Gemma/Llama")
ax.set_xticks(range(1, 11)); ax.set_ylim(0, 4.3)
save(fig, "M2_memory_dynamics.png")

# M3. Phân phối tổng đóng góp: chỉ Gemma bị giãn phương sai xuống dưới 120 ----
fig, ax = plt.subplots(figsize=(7.8, 4.4))
pos = []; box_data = []; box_col = []
for j, m in enumerate(MODELS):
    for k, (df, col) in enumerate([(base, DARK), (mem, ACC)]):
        pos.append(j*1.0 + (k-0.5)*0.34); box_data.append(df[df.model == m].group_total.values); box_col.append(col)
bp = ax.boxplot(box_data, positions=pos, widths=0.30, patch_artist=True, showfliers=True,
                medianprops=dict(color="white", lw=1.6), flierprops=dict(marker="o", ms=3, mfc="#999", mec="none"))
for patch, c in zip(bp["boxes"], box_col): patch.set_facecolor(c); patch.set_alpha(0.85)
ax.axhline(120, color="#c0392b", ls="--", lw=1.6); ax.text(2.55, 122, "mục tiêu 120", color="#c0392b", fontsize=10)
ax.set_xticks(np.arange(len(MODELS))); ax.set_xticklabels([LBL[m] for m in MODELS])
ax.legend([plt.Rectangle((0, 0), 1, 1, fc=DARK, alpha=.85), plt.Rectangle((0, 0), 1, 1, fc=ACC, alpha=.85)],
          ["full-history", "scratchpad"], frameon=False, loc="upper right", fontsize=10)
ax.annotate("scratchpad: min 106 < 120\n→ 14/60 game trượt sát nút", xy=(2.17, 106), xytext=(1.15, 95),
            fontsize=9.5, color=ACC, arrowprops=dict(arrowstyle="->", color=ACC))
ax.set_ylabel("Tổng đóng góp / game"); ax.set_title("Scratchpad không đổi trung bình — chỉ giãn phương sai Gemma")
save(fig, "M3_memory_dist.png")

# ---- FRAMING -----------------------------------------------------------------
# FR3. Reach framed vs neutral (knife-edge của Gemma) ------------------------
neu_r = base.groupby("model").reach.mean()                                   # neutral full_history
fra_r = frm[frm.memory_mode == "full_history"].groupby("model").reach.mean()  # framed full_history
fig, ax = plt.subplots(figsize=(7.2, 4.4))
x = np.arange(len(MODELS)); w = 0.36
ax.bar(x - w/2, [neu_r[m] for m in MODELS], w, label="trung tính", color=DARK)
ax.bar(x + w/2, [fra_r[m] for m in MODELS], w, label="khung ích kỷ", color=ACC)
for i, m in enumerate(MODELS):
    dpp = (fra_r[m] - neu_r[m]) * 100
    ax.text(x[i], max(neu_r[m], fra_r[m]) + 0.03, f"{dpp:+.0f}pp", ha="center", fontsize=10,
            color=ACC if dpp < -1 else DARK, fontweight="bold")
ax.set_xticks(x); ax.set_xticklabels([LBL[m] for m in MODELS]); ax.set_ylim(0, 1.12)
ax.set_ylabel("Tỉ lệ đạt mục tiêu"); ax.set_title("Framing cắt reach Gemma (knife-edge); Qwen/Llama trơ")
ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.1))
save(fig, "FR3_framing_reach.png")

# ---- PERSONA -----------------------------------------------------------------
# D2. mean ± sd của tổng theo #selfish — reach chỉ là P(tuyến tính > 120) -----
g = per.groupby(["model", "nsel"]).group_total.agg(["mean", "std"]).reset_index()
fig, ax = plt.subplots(figsize=(7.8, 4.4))
for m in MODELS:
    s = g[g.model == m].sort_values("nsel")
    ax.plot(s.nsel, s["mean"], "o-", color=COL[m], lw=2.4, ms=7, label=LBL[m])
    ax.fill_between(s.nsel, s["mean"]-s["std"], s["mean"]+s["std"], color=COL[m], alpha=0.13)
ax.axhline(120, color="#c0392b", ls="--", lw=1.6); ax.text(4.4, 126, "mục tiêu 120", color="#c0392b", fontsize=10)
ax.set_xlabel("Số tác nhân ích kỷ (k)"); ax.set_ylabel("Tổng đóng góp (mean ± sd)")
ax.set_title("Reach = xác suất dải tuyến tính cắt 120 — tất cả ở phương sai")
ax.set_xticks(range(0, 7)); ax.legend(frameon=False)
save(fig, "D2_persona_dispersion.png")

# J. Sụp đổ persona: EN vs VN (small multiples) -------------------------------
pj = per.groupby(["model", "language", "nsel"]).reach.mean().reset_index()
fig, axes = plt.subplots(1, 3, figsize=(10.2, 3.7), sharey=True)
for ax, m in zip(axes, MODELS):
    for lang, ls, mk in [("en", "-", "o"), ("vn", "--", "s")]:
        s = pj[(pj.model == m) & (pj.language == lang)].sort_values("nsel")
        ax.plot(s.nsel, s.reach, ls, marker=mk, color=COL[m], lw=2.3, ms=6,
                label={"en": "EN", "vn": "VN"}[lang], alpha=1 if lang == "en" else 0.8)
    ax.set_title(LBL[m]); ax.set_xticks(range(0, 7, 2)); ax.set_ylim(-0.05, 1.1)
    ax.set_xlabel("k ích kỷ"); ax.legend(frameon=False, fontsize=9, loc="lower left")
axes[0].set_ylabel("Tỉ lệ đạt mục tiêu")
fig.suptitle("Sụp đổ persona của Gemma là do tiếng Anh (sụp ngay ở 1); VN có bậc thang", fontsize=14)
save(fig, "J_persona_lang.png")

# Q. Robustness — phương sai do SỐ LƯỢNG ích kỷ vs CÁCH XẾP GHẾ ---------------
def eta2_decomp(s):
    gt = s["group_total"]; grand = gt.mean(); sst = ((gt - grand)**2).sum()
    ssc = s.groupby("nsel")["group_total"].apply(lambda x: len(x)*(x.mean()-grand)**2).sum()
    ssa = 0.0
    for _, g in s.groupby("nsel"):
        gm = g["group_total"].mean()
        ssa += g.groupby("persona_seats")["group_total"].apply(lambda x: len(x)*(x.mean()-gm)**2).sum()
    return 100*ssc/sst, 100*ssa/sst
dec = {m: eta2_decomp(per[per.model == m]) for m in MODELS}
fig, ax = plt.subplots(figsize=(7.4, 4.4))
x = np.arange(len(MODELS)); w = 0.36
ax.bar(x - w/2, [dec[m][0] for m in MODELS], w, label="Số lượng ích kỷ (k)", color=DARK)
ax.bar(x + w/2, [dec[m][1] for m in MODELS], w, label="Cách xếp ghế (arrangement)", color=ACC)
for i, m in enumerate(MODELS):
    ax.text(x[i]-w/2, dec[m][0]+1.5, f"{dec[m][0]:.0f}%", ha="center", fontsize=11, color=DARK, fontweight="bold")
    ax.text(x[i]+w/2, dec[m][1]+1.5, f"{dec[m][1]:.1f}%", ha="center", fontsize=10, color=ACC, fontweight="bold")
ax.set_xticks(x); ax.set_xticklabels([LBL[m] for m in MODELS]); ax.set_ylim(0, 88)
ax.set_ylabel("% phương sai tổng đóng góp được giải thích")
ax.set_title("Quan trọng là BAO NHIÊU ích kỷ, không phải ngồi ĐÂU")
ax.legend(frameon=False, loc="upper right")
save(fig, "Q_persona_variance.png")

# ---- TỔNG HỢP ----------------------------------------------------------------
# P. Hiệu quả kinh tế — ít hào phóng nhất lại giữ nhiều tiền nhất -------------
eff = base.groupby("model").agg(gt=("group_total", "mean"), reach=("reach", "mean"))
fig, ax = plt.subplots(figsize=(7.4, 4.4))
x = np.arange(len(MODELS))
contrib = np.array([eff.loc[m, "gt"] for m in MODELS]); kept = 240 - contrib
ax.bar(x, contrib, color=ACC, label="Đóng vào quỹ (mất vĩnh viễn)")
ax.bar(x, kept, bottom=contrib, color=TEAL, label="Giữ lại (tiền mặt cuối game)")
ax.axhline(120, color=DARK, ls=":", lw=1.6); ax.text(2.55, 122, "mục tiêu 120", color=DARK, fontsize=9.5)
for i, m in enumerate(MODELS):
    ax.text(x[i], contrib[i]/2, f"{contrib[i]:.0f}", ha="center", va="center", color="white", fontweight="bold")
    ax.text(x[i], contrib[i] + kept[i]/2, f"giữ {kept[i]:.0f}", ha="center", va="center", color="white", fontweight="bold")
    ax.text(x[i], 246, f"đạt {eff.loc[m,'reach']*100:.0f}%", ha="center", fontsize=10, color=DARK)
ax.set_xticks(x); ax.set_xticklabels([LBL[m] for m in MODELS]); ax.set_ylim(0, 262)
ax.set_ylabel("Đơn vị tiền (tổng vốn nhóm = 240)")
ax.set_title("Kẻ ít hào phóng nhất (Gemma) là kẻ lời nhất — vẫn đạt 100%")
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2)
save(fig, "P_efficiency.png")

print("\n[OK]", sorted(os.listdir(OUT)))
