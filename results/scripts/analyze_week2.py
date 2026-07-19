"""Tuần 2 — IN MỌI CON SỐ cho slide: (A) large vs small scaling, (B) comprehension.
Chạy: python results/analyze_week2.py
"""
from pathlib import Path
import json, glob
import numpy as np, pandas as pd

R = Path(__file__).resolve().parent.parent   # results/ (script dưới results/scripts/)
pd.set_option("display.width", 200); pd.set_option("display.max_columns", 40)

def banner(t): print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)

# ======================================================================
# A. SCALING — small baseline vs large baseline
# ======================================================================
A = pd.read_csv(R / "open_source/crsd_all_models.csv")
A = A[A.experiment == "exp_baseline"].copy()   # layout exp-first: lọc baseline từ master
A["reach"] = A.target_reached.astype(int); A["risk"] = A.risk_probability.astype(float)
A["kept"] = 240 - A.group_total

PAIRS = {  # family -> (small, large)
    "Qwen": ("qwen25-7b-instruct", "qwen25-32b-instruct"),
    "Gemma": ("gemma2-9b-it", "gemma2-27b-it"),
}
ALLM = ["qwen25-7b-instruct", "qwen25-32b-instruct",
        "gemma2-9b-it", "gemma2-27b-it", "llama-3-1-8b"]

banner("A1. Reach-rate & contribution & kept — per model (overall)")
g = A.groupby("model").agg(reach=("reach","mean"), contrib=("group_total","mean"),
                           kept=("kept","mean"), payoff=("mean_payoff","mean"),
                           n=("reach","size")).reindex(ALLM)
print(g.round(2).to_string())

banner("A2. Reach-rate by risk (does scaling restore risk sensitivity?)")
piv = A.groupby(["model","risk"]).reach.mean().unstack("risk").reindex(ALLM)
print(piv.round(3).to_string())
print("\nHUMAN (Milinski): risk0.9=0.50  risk0.5=0.10  risk0.1=0.00")

banner("A3. Contribution (group_total /240) by risk")
piv = A.groupby(["model","risk"]).group_total.mean().unstack("risk").reindex(ALLM)
print(piv.round(1).to_string())

banner("A4. Contribution EN vs VN")
piv = A.groupby(["model","language"]).group_total.mean().unstack("language").reindex(ALLM)
piv["d(vn-en)"] = piv["vn"] - piv["en"]
print(piv.round(1).to_string())

banner("A5. Reach EN vs VN")
piv = A.groupby(["model","language"]).reach.mean().unstack("language").reindex(ALLM)
print(piv.round(3).to_string())

# choice distribution {0,2,4} from turns.jsonl
def load_turns():
    rows=[]
    for f in glob.glob(str(R/"open_source/exp_baseline/*/turns.jsonl")):
        m=f.replace("\\","/").split("/")[-2]
        for line in open(f,encoding="utf-8"):
            d=json.loads(line); rows.append((m,d["round"],d["contribution"],
                d.get("language"),float(d.get("risk_probability",0))))
    return rows
T = pd.DataFrame(load_turns(), columns=["model","round","c","lang","risk"])

banner("A6. Choice distribution {0,2,4} per model (% of turns)")
for m in ALLM:
    d=T[T.model==m]
    if len(d):
        print(f"  {m:<22} 0:{d.c.eq(0).mean()*100:5.1f}  2:{d.c.eq(2).mean()*100:5.1f}  4:{d.c.eq(4).mean()*100:5.1f}  mean={d.c.mean():.2f}")

banner("A7. Choice distribution by risk (risk-insensitive at choice level?)")
for m in ALLM:
    print(f"  -- {m}")
    for r in [0.9,0.5,0.1]:
        d=T[(T.model==m)&(T.risk==r)]
        if len(d):
            print(f"     risk{r:>3}: 0:{d.c.eq(0).mean()*100:5.1f}  2:{d.c.eq(2).mean()*100:5.1f}  4:{d.c.eq(4).mean()*100:5.1f}")

banner("A8. Round dynamics — mean contribution per round")
gr = T.groupby(["model","round"]).c.mean().unstack("round").reindex(ALLM)
print(gr.round(2).to_string())

# ======================================================================
# B. COMPREHENSION
# ======================================================================
banner("B0. Load comprehension summaries")
frames=[]
for f in glob.glob(str(R/"open_source/exp_comprehension/*/comprehension_summary.csv")):
    m=f.replace("\\","/").split("/")[-2]
    df=pd.read_csv(f); frames.append(df)
C=pd.concat(frames,ignore_index=True)
CMODELS=["qwen25-7b-instruct","gemma2-9b-it","llama-3-1-8b"]
print(f"loaded {len(C)} summary rows; models={sorted(C.model.unique())}")
print(f"categories={sorted(C.category.unique())}; showcum={sorted(C.show_cumulative.unique())}; langs={sorted(C.language.unique())}")
print(f"questions per category:")
for cat in ["rules","time","state"]:
    print(f"  {cat}: {sorted(C[C.category==cat].question_id.unique())}")

def acc_by(df, by, col):
    a=df.groupby(by).agg(n=("n","sum"),nc=("n_correct","sum"))
    a["acc"]=a.nc/a.n.replace(0,np.nan)
    return a["acc"].unstack(col)

banner("B1. Accuracy by model × category (overall, both showcum)")
print(acc_by(C,["model","category"],"category").reindex(CMODELS).round(3).to_string())

banner("B2. Accuracy by model × category × showCumulative (0=pool hidden, 1=pool shown)")
for m in CMODELS:
    print(f"  -- {m}")
    sub=C[C.model==m]
    print(acc_by(sub,["category","show_cumulative"],"show_cumulative").reindex(["rules","time","state"]).round(3).to_string())

banner("B3. rules_risk_pct GATE — accuracy by model × language × risk")
rr=C[C.question_id=="rules_risk_pct"]
print(acc_by(rr,["model","language","risk_probability"],"risk_probability").reindex(
    pd.MultiIndex.from_product([CMODELS,["en","vn"]],names=["model","language"])).round(3).to_string())

banner("B4. EN vs VN by model × category")
piv=acc_by(C,["model","category","language"],"language").reindex(
    pd.MultiIndex.from_product([CMODELS,["rules","time","state"]],names=["model","category"]))
piv["d(vn-en)"]=piv["vn"]-piv["en"]
print(piv.round(3).to_string())

banner("B5. CONTROL — state_own_remaining (PRINTED) vs state_pool (must ADD) by showcum")
ctl=C[C.question_id.isin(["state_own_remaining","state_pool"])]
print(acc_by(ctl,["model","show_cumulative","question_id"],"question_id").round(3).to_string())
print("  expect: own_remaining ~ceiling both branches; state_pool low at showcum=0, jumps at showcum=1")

banner("B6. Per-question accuracy (model × question_id, both showcum) — full Figure-1 table")
pq=acc_by(C,["category","question_id","model"],"model").reindex(columns=CMODELS)
print(pq.round(3).to_string())

banner("B7. parse_fail_rate per model")
pf=C.groupby("model").agg(nf=("n_parse_failed","sum"),n=("n","sum"))
pf["rate"]=pf.nf/pf.n
print(pf.round(4).to_string())

print("\nDONE.")
