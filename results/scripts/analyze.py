"""Phân tích 3 exp (baseline/framing/memory) — dữ liệu MỚI sau fix, 3 model đều hợp lệ."""
from pathlib import Path
import pandas as pd, numpy as np

ROOT = Path(__file__).resolve().parent.parent / "open_source"   # results/open_source
# layout exp-first: đọc 1 master rồi lọc theo cột 'experiment'
EXP_FILE = {"baseline": "exp_baseline", "framing": "exp_framing", "memory": "exp_memory_ablation"}
_MASTER = pd.read_csv(ROOT / "crsd_all_models.csv")
HUMAN = {0.9:0.50, 0.5:0.10, 0.1:0.00}

fr=[]
for e,exp in EXP_FILE.items():
    d=_MASTER[_MASTER.experiment==exp].copy(); d["exp_file"]=e; fr.append(d)
a=pd.concat(fr, ignore_index=True)
a["risk"]=a.risk_probability.astype(float); a["reach"]=a.target_reached.astype(int); a["cat"]=a.catastrophe.astype(int)
def pct(x): return f"{100*x:5.1f}%"
def banner(t): print("\n"+"="*78+f"\n{t}\n"+"="*78)

base=a[a.exp_file=="baseline"]
banner("1. BASELINE — reach / contribution theo model × risk (3 model ĐỀU hợp lệ)")
g=(base.groupby(["model","risk"]).agg(n=("reach","size"),reach=("reach","mean"),
     cat=("cat","mean"),contrib=("group_total","mean"),payoff=("mean_payoff","mean")).reset_index())
g["human"]=g.risk.map(HUMAN)
for m in sorted(g.model.unique()):
    print(f"\n  ── {m}")
    print(f"  {'risk':>5}{'n':>4}{'reach':>8}{'human':>8}{'cat':>8}{'contrib':>9}{'payoff':>8}")
    for _,r in g[g.model==m].sort_values("risk",ascending=False).iterrows():
        print(f"  {r.risk:>5}{int(r.n):>4}{pct(r.reach):>8}{pct(r.human):>8}{pct(r['cat']):>8}{r.contrib:>9.1f}{r.payoff:>8.2f}")

banner("1b. BASELINE — ngôn ngữ EN vs VN (reach)")
gl=base.groupby(["model","language","risk"])["reach"].mean().reset_index()
piv=gl.pivot_table(index=["model","risk"],columns="language",values="reach")
if "en" in piv and "vn" in piv: piv["Δ(vn-en)"]=piv["vn"]-piv["en"]
print(piv.map(lambda x:f"{100*x:.0f}%" if pd.notna(x) else "-").to_string())

banner("2. MEMORY — scratchpad vs full_history(baseline), reach & contribution")
mem=a[a.exp_file=="memory"].assign(cond="scratchpad")
ctrl=base.assign(cond="full_history")
mm=pd.concat([mem,ctrl],ignore_index=True)
mt=mm.groupby(["model","cond"]).agg(reach=("reach","mean"),contrib=("group_total","mean")).reset_index()
print(mt.pivot_table(index="model",columns="cond",values=["reach","contrib"]).to_string(float_format=lambda x:f"{x:.2f}"))

banner("3. FRAMING 2x2 — framing × memory (control từ baseline+memory)")
frm=a[a.exp_file=="framing"].assign(frame="framed")
ctrl2=pd.concat([base.assign(memory_mode="full_history"),mem.assign(memory_mode="scratchpad")],ignore_index=True).assign(frame="neutral")
ff=pd.concat([frm,ctrl2],ignore_index=True)
ft=ff.groupby(["frame","memory_mode"]).agg(reach=("reach","mean"),contrib=("group_total","mean"),n=("reach","size")).reset_index()
print(ft.to_string(index=False,float_format=lambda x:f"{x:.3f}"))

# so sánh gemma CŨ (artifact) vs MỚI
banner("4. GEMMA: trước (artifact, rỗng 87%) vs giờ (hợp lệ) — baseline contribution")
gg=base[base.model=="gemma2-9b-it"].groupby("risk").agg(reach=("reach","mean"),contrib=("group_total","mean")).reset_index()
print("  (giờ)  ", gg.to_dict("records"))
print("  Nhắc: lần trước gemma reach 0% / contrib ~15 là DO RỖNG, không phải hành vi.")

# Plots
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
FIG=Path(__file__).resolve().parent.parent/"figures"; FIG.mkdir(exist_ok=True)
MODELS=sorted(base.model.unique()); COL=dict(zip(MODELS,["#1f77b4","#d62728","#2ca02c"]))
fig,ax=plt.subplots(figsize=(7,5))
for m in MODELS:
    s=g[g.model==m].sort_values("risk"); ax.plot(s.risk,s.reach,"o-",color=COL[m],label=m,lw=2)
hk=sorted(HUMAN); ax.plot(hk,[HUMAN[k] for k in hk],"k--s",label="Human (Milinski)",lw=2)
ax.set_xlabel("Risk"); ax.set_ylabel("Reach rate"); ax.set_title("Baseline reach vs risk (3 model hợp lệ)")
ax.invert_xaxis(); ax.set_ylim(-.03,1.03); ax.legend(); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG/"reach_vs_risk_3models.png",dpi=130)
fig,ax=plt.subplots(figsize=(7,5))
for m in MODELS:
    s=g[g.model==m].sort_values("risk"); ax.plot(s.risk,s.contrib,"o-",color=COL[m],label=m,lw=2)
ax.axhline(120,color="k",ls="--",label="Target"); ax.set_xlabel("Risk"); ax.set_ylabel("Mean contribution")
ax.set_title("Baseline contribution vs risk"); ax.invert_xaxis(); ax.legend(); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG/"contrib_vs_risk_3models.png",dpi=130)
print(f"\n[OK] Hình -> {FIG}")
