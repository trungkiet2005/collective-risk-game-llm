"""Phân tích bài ĐỌC-HIỂU (prompt comprehension) — Figure-1 analog + A/B showCumulative
+ cổng rules_risk_pct + EN/VN + đường suy giảm theo độ dài lịch sử.

Đọc MỌI ``comprehension.jsonl`` dưới ROOT (mặc định results/, rglob) rồi gộp. Mỗi dòng
= một probe (đã chấm so ground truth của engine). Xuất bảng ra stdout + hình PNG vào
results/analysis_comprehension/figures/.

  python results/analyze_comprehension.py            # quét results/
  python results/analyze_comprehension.py <thư_mục>  # quét thư mục khác
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# cho phép `from crsd...` khi chạy `python results/analyze_comprehension.py` từ repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))   # repo root (script dưới results/scripts/)

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "open_source"
OUT = Path(__file__).resolve().parent.parent / "analysis_comprehension"
FIG = OUT / "figures"

CAT_ORDER = ["rules", "time", "state"]
HUMAN_NOTE = "HUMAN (Milinski 2008) reach-rate: p0.1=0.00 p0.5=0.10 p0.9=0.50"


def banner(t):
    print("\n" + "=" * 80 + f"\n{t}\n" + "=" * 80)


def wilson(k, n, z=1.96):
    """Khoảng tin cậy Wilson cho tỉ lệ (ổn định ở gần 0/1, đúng cho accuracy ~trần)."""
    if n == 0:
        return (np.nan, np.nan, np.nan)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return p, max(0.0, center - half), min(1.0, center + half)


def load() -> pd.DataFrame:
    files = sorted(ROOT.rglob("comprehension.jsonl"))
    if not files:
        print(f"Không thấy comprehension.jsonl nào dưới {ROOT}. Chạy run_comprehension hoặc tải kết quả Kaggle về đây.")
        sys.exit(0)
    rows = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                rows.append(json.loads(line))
    df = pd.DataFrame(rows)
    df["correct"] = df["correct"].astype(int)
    df["parse_failed"] = df["parse_failed"].astype(int)
    df["risk"] = df["risk_probability"].astype(float)
    df["showcum"] = df["show_cumulative"].astype(int)
    print(f"Nạp {len(df)} probe từ {len(files)} file ({df.model.nunique()} model, "
          f"langs={sorted(df.language.unique())}, showcum={sorted(df.showcum.unique())}).")
    return df


def acc_ci(d):
    p, lo, hi = wilson(int(d["correct"].sum()), len(d))
    return pd.Series({"n": len(d), "acc": p, "lo": lo, "hi": hi,
                      "pfail": d["parse_failed"].mean()})


def table_by_category(df):
    banner("1. Accuracy theo model × category × showCumulative (0=pool ẩn baseline, 1=hiện)")
    g = (df.groupby(["model", "showcum", "category"]).apply(acc_ci, include_groups=False)
         .reset_index())
    for m in sorted(g.model.unique()):
        print(f"\n  ── {m}")
        sub = g[g.model == m].copy()
        sub["category"] = pd.Categorical(sub.category, CAT_ORDER, ordered=True)
        piv = sub.pivot_table(index="category", columns="showcum", values="acc", observed=False)
        print(piv.to_string(float_format=lambda x: f"{x:.3f}"))
    return g


def table_risk_gate(df):
    banner("2. CỔNG rules_risk_pct — accuracy + phân biệt mức risk (mở khoá claim risk-insensitivity)")
    rr = df[df.question_id == "rules_risk_pct"].copy()
    if rr.empty:
        print("  (không có probe rules_risk_pct)")
        return
    g = rr.groupby(["model", "language", "risk"]).apply(acc_ci, include_groups=False).reset_index()
    piv = g.pivot_table(index=["model", "language"], columns="risk", values="acc")
    print("  Accuracy theo risk (đúng = trả đúng 90/50/10 theo điều kiện):")
    print(piv.to_string(float_format=lambda x: f"{x:.3f}"))
    # Phân biệt: mức trung bình câu trả lời (số) phải BÁM 90/50/10; Spearman parsed~true.
    rr["pa"] = pd.to_numeric(rr["parsed_answer"], errors="coerce")
    rr["true"] = (rr["risk"] * 100).round()
    print("\n  Giá trị risk% model TRẢ trung bình theo điều kiện (lý tưởng = 90/50/10):")
    mean_pa = rr.groupby(["model", "language", "risk"])["pa"].mean().unstack("risk")
    print(mean_pa.to_string(float_format=lambda x: f"{x:.1f}"))
    print("\n  Spearman(parsed, true) theo model×language (1.0 = phân biệt hoàn hảo):")
    for (m, l), d in rr.dropna(subset=["pa"]).groupby(["model", "language"]):
        if d["pa"].nunique() > 1 and d["true"].nunique() > 1:
            rho = d[["pa", "true"]].corr(method="spearman").iloc[0, 1]
        else:
            rho = float("nan")
        print(f"    {m:<22} {l}: rho={rho:.3f}")


def table_language(df):
    banner("3. EN vs VN (RQ ngôn ngữ) — accuracy theo model × category")
    g = df.groupby(["model", "category", "language"]).apply(acc_ci, include_groups=False).reset_index()
    piv = g.pivot_table(index=["model", "category"], columns="language", values="acc")
    if {"en", "vn"} <= set(piv.columns):
        piv["Δ(vn-en)"] = piv["vn"] - piv["en"]
    print(piv.to_string(float_format=lambda x: f"{x:.3f}" if pd.notna(x) else "-"))


def table_control(df):
    banner("4. Manipulation check nội-prompt: own_remaining (IN SẴN) vs state_pool (PHẢI CỘNG)")
    sub = df[df.question_id.isin(["state_own_remaining", "state_pool"])]
    g = sub.groupby(["model", "showcum", "question_id"]).apply(acc_ci, include_groups=False).reset_index()
    piv = g.pivot_table(index=["model", "showcum"], columns="question_id", values="acc")
    print(piv.to_string(float_format=lambda x: f"{x:.3f}"))
    print("  Kỳ vọng: own_remaining ~trần ở cả 2 nhánh; state_pool thấp khi showcum=0, nhảy khi =1.")


def fig_figure1(df):
    """Figure-1 analog: accuracy/câu hỏi, nhóm Rules|Time|State, 3 model, 2 panel showcum."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from crsd.engine.comprehension import REGISTRY  # thứ tự câu hỏi ổn định
    qorder = [q.id for q in REGISTRY]
    qcat = {q.id: q.category for q in REGISTRY}
    present = [q for q in qorder if q in set(df.question_id)]
    models = sorted(df.model.unique())
    showcums = sorted(df.showcum.unique())

    fig, axes = plt.subplots(1, len(showcums), figsize=(max(10, 0.55 * len(present)), 5),
                             sharey=True, squeeze=False)
    for ax, sc in zip(axes[0], showcums):
        d_sc = df[df.showcum == sc]
        x = np.arange(len(present))
        for j, m in enumerate(models):
            accs, los, his = [], [], []
            for q in present:
                dd = d_sc[(d_sc.model == m) & (d_sc.question_id == q)]
                p, lo, hi = wilson(int(dd.correct.sum()), len(dd)) if len(dd) else (np.nan,) * 3
                accs.append(p); los.append(p - lo if np.isfinite(lo) else 0); his.append(hi - p if np.isfinite(hi) else 0)
            ax.errorbar(x + (j - len(models) / 2) * 0.12, accs, yerr=[los, his], fmt="o",
                        ms=4, capsize=2, label=m)
        # phân vạch giữa các category
        bounds = {}
        for i, q in enumerate(present):
            bounds.setdefault(qcat[q], []).append(i)
        for c in CAT_ORDER:
            if c in bounds:
                ax.axvspan(min(bounds[c]) - 0.5, max(bounds[c]) + 0.5,
                           alpha=0.05, color="k")
                ax.text((min(bounds[c]) + max(bounds[c])) / 2, 1.04, c.upper(),
                        ha="center", va="bottom", fontsize=9, transform=ax.get_xaxis_transform())
        ax.set_xticks(x)
        ax.set_xticklabels(present, rotation=90, fontsize=7)
        ax.set_ylim(0, 1.08)
        ax.set_title(f"showCumulative = {sc}  ({'pool hiện' if sc else 'pool ẩn'})")
        ax.axhline(0.9, ls=":", c="grey", lw=0.8)
    axes[0][0].set_ylabel("Response accuracy")
    axes[0][-1].legend(fontsize=7, loc="lower left")
    fig.suptitle("Prompt-comprehension accuracy (Rules | Time | State) — CRG", y=1.02)
    fig.tight_layout()
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / "figure1_comprehension.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {FIG / 'figure1_comprehension.png'}")


def fig_decay(df):
    """Đường suy giảm: accuracy theo độ dài lịch sử (round) cho từng category."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 4.5))
    for c in CAT_ORDER:
        d = df[df.category == c]
        if d.empty:
            continue
        g = d.groupby("round").apply(lambda x: wilson(int(x.correct.sum()), len(x))[0],
                                     include_groups=False)
        ax.plot(g.index, g.values, "-o", ms=3, label=c.upper())
    ax.set_xlabel("Round (độ dài lịch sử tăng dần)")
    ax.set_ylabel("Accuracy")
    ax.set_ylim(0, 1.05)
    ax.legend()
    ax.set_title("Suy giảm accuracy theo độ dài lịch sử (gộp model/showcum)")
    fig.tight_layout()
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / "decay_by_round.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {FIG / 'decay_by_round.png'}")


def glmm(df):
    banner("5. (TUỲ CHỌN) GLM logistic khẳng định — hướng hệ số (random-effects = future)")
    try:
        import statsmodels.formula.api as smf
    except Exception as e:  # noqa: BLE001
        print("  statsmodels không có -> bỏ qua. (", e, ")")
        return
    d = df.copy()
    d["round_c"] = d["round"] - d["round"].mean()
    try:
        model = smf.logit(
            "correct ~ C(category, Treatment('rules')) * C(showcum) + C(language) "
            "+ round_c + C(model) + risk",
            data=d,
        ).fit(disp=False, maxiter=200)
        print(model.summary().tables[1].as_text())
        print("  Lưu ý: đây là GLM cố-định-hiệu-ứng (ước lượng hướng); bản chuẩn Q1 nên là "
              "GLMM có (1|state)+(1|question_type) + Firth/Bayes cho ô gần trần.")
    except Exception as e:  # noqa: BLE001
        print("  Fit GLM lỗi (có thể do separation ở ô trần):", e)


def main():
    df = load()
    table_by_category(df)
    table_risk_gate(df)
    table_language(df)
    table_control(df)
    banner("HÌNH")
    try:
        fig_figure1(df)
        fig_decay(df)
    except Exception as e:  # noqa: BLE001
        print("  (bỏ qua vẽ hình:", e, ")")
    glmm(df)
    print("\n" + HUMAN_NOTE)
    print(f"Hình + bảng -> {OUT}")


if __name__ == "__main__":
    main()
