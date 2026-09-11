#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""E7 — đường tham chiếu scripted: trò chơi này TRÔNG NHƯ THẾ NÀO nếu chơi duy lý.

Chạy:  python paper/AAMAS/analysis/e7_reference.py

KHÔNG gọi API, không tốn một xu. Năm chính sách scripted chạy qua ĐÚNG engine
(`crsd.engine`) chứ không mô phỏng lại luật, nên số ở đây so thẳng được với `results/`.
Không ghi gì vào `results/` — `run_scripted_reference.main()` mặc định ghi vào
`results/scripted_reference/`, sai layout đã chốt, nên script này gọi `run_sweep()`
trong tiến trình và tự xuất ra `paper/AAMAS/`.

SINH RA
    paper/AAMAS/tables/e7_numbers.tex        <- CHỈ \newcommand
    paper/AAMAS/tables/e7_table_reference.tex
    paper/AAMAS/figures/e7_reference.pdf

VÌ SAO MỤC NÀY ĐÁNG GIÁ NHẤT SO VỚI CHI PHÍ CỦA NÓ
    Toàn bộ bài báo đứng trên một tương phản: agent duy lý trung lập rủi ro sẽ ĐỔI hành
    vi tại ngưỡng `p* = 0.5`, còn LLM thì không đổi gì cả. Cho tới khi có mục này, vế
    thứ nhất chỉ là một câu khẳng định trong văn bản. Chạy nó qua chính engine biến nó
    thành một đường vẽ được: `all_ev_maximiser` giữ quỹ ở 0 với mọi `p < 0.5` rồi nhảy
    thẳng lên đúng mục tiêu 120 từ `p = 0.5`. Reviewer hỏi "so với baseline nào" thì đây
    là câu trả lời, và nó không tốn tiền chạy.

    Hai đường nữa cần cho hình: `all_always_2` (đóng đúng phần mình mọi vòng -> đúng 120,
    phẳng) và `all_always_4` (240, tức lãng phí đúng một nửa). Chúng kẹp lấy vùng mà mọi
    quan sát LLM rơi vào, nên người đọc thấy ngay các model nằm ở đâu giữa "vừa đủ" và
    "thừa gấp đôi".

MỘT KẾT QUẢ PHỤ ĐÁNG NHỚ
    `mix_ev3_cc3` — ba kẻ tối ưu EV ngồi cùng ba kẻ hợp tác có điều kiện — cho tổng quỹ
    **6** ở rủi ro thấp, chứ không phải 60. Ba ghế EV đóng 0, và ghế CC khớp trung bình
    của những người khác nên bị kéo về 0 chỉ sau một hai vòng. Hợp tác có điều kiện
    không sống sót khi có đủ kẻ ăn không, và đó là bối cảnh trực tiếp cho E3b.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from crsd.runner.run_scripted_reference import run_sweep  # noqa: E402

TABLES = REPO / "paper" / "AAMAS" / "tables"
FIGURES = REPO / "paper" / "AAMAS" / "figures"
BASELINE = REPO / "results" / "exp_baseline"

RISKS = [round(0.1 * i, 1) for i in range(11)]      # đúng lưới 11 điểm của B
REPS = 20                                           # chính sách tất định; rep lấy mẫu xổ số
TARGET = 120.0

# Đường nào vào bảng/hình, và tên đọc được trong paper.
LINES = [
    ("all_always_0", "All defect (0 each round)"),
    ("all_always_2", "All fair share (2 each round)"),
    ("all_always_4", "All maximum (4 each round)"),
    ("all_conditional_cooperator", "All conditional cooperators"),
    ("all_ev_maximiser", "All risk-neutral EV maximisers"),
]

PRETTY = {
    "anthropic-claude-haiku-4-5-20251001": "Claude Haiku 4.5",
    "google-gemini-3.5-flash-lite": "Gemini 3.5 Flash Lite",
    "openai-gpt-5.6-luna": "GPT-5.6 Luna",
    "qwen-qwen3-235b-a22b-instruct-2507": "Qwen3 235B",
    "xai-grok-4.20-0309-non-reasoning": "Grok 4.20",
}


class Macros:
    """Gom `\newcommand`; chặn định nghĩa trùng tên (LaTeX nuốt im lặng cái sau)."""

    def __init__(self):
        self._seen, self._lines = {}, []

    def add(self, name, value):
        if name in self._seen:
            raise SystemExit("macro trung ten: %s" % name)
        self._seen[name] = value
        self._lines.append(r"\newcommand{\%s}{%s}" % (name, value))

    def write(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(self._lines) + "\n", encoding="utf-8")
        print("  ghi %s (%d macro)" % (path.relative_to(REPO), len(self._lines)))


def load_baseline():
    """{model_tag: {risk: tong quy TB}} tu results/exp_baseline, hoac {} neu chua co.

    Doc `group_total` chu khong cong lai tu tung ghe: cot do la thu engine da ghi, va
    cong tay lai la co hoi de lech mot cach im lang.
    """
    import csv
    out = {}
    if not BASELINE.exists():
        return out
    for f in sorted(BASELINE.glob("*/*/*.csv")):
        risk = float(f.parent.parent.name)
        with open(f, encoding="utf-8") as h:
            for r in csv.DictReader(h):
                tag = r["agent1_llm"]
                out.setdefault(tag, {}).setdefault(risk, []).append(float(r["group_total"]))
    return {t: {p: sum(v) / len(v) for p, v in d.items()} for t, d in out.items()}


def main():
    print("E7: chay %d muc rui ro x %d rep, offline" % (len(RISKS), REPS))
    rows, games, _ = run_sweep(risks=RISKS, reps=REPS, verbose=False)
    print("  %d van, %d o" % (len(games), len(rows)))

    by = {}
    for r in rows:
        by.setdefault(r["condition"], {})[r["risk_probability"]] = r

    # --- cong tu kiem: duong EV phai la BAC THANG tai p* = 0.5 ------------------
    # Day la ly do ton tai cua ca muc nay. Neu no khong bac thang thi hoac chinh sach
    # ev_maximiser sai, hoac tham so tro choi da doi, va moi so ben duoi vo nghia.
    ev = by["all_ev_maximiser"]
    low = [ev[p]["group_total_mean"] for p in RISKS if p < 0.5]
    high = [ev[p]["group_total_mean"] for p in RISKS if p >= 0.5]
    if not (max(low) == 0.0 and min(high) == TARGET):
        raise SystemExit(
            "Duong EV KHONG phai bac thang tai p*=0.5: duoi nguong %s, tren nguong %s.\n"
            "Hoac chinh sach ev_maximiser da doi, hoac tham so tro choi da doi. "
            "Dung lai truoc khi sinh bat cu con so nao." % (low, high))
    print("  cong tu kiem: duong EV la bac thang tai p*=0.5 (duoi=0, tren=%g)" % TARGET)

    M = Macros()
    M.add("EsevenGames", "%d" % len(games))
    M.add("EsevenCells", "%d" % len(rows))
    M.add("EsevenReps", "%d" % REPS)
    M.add("EsevenPivot", "0.5")
    M.add("EsevenEVBelow", "0")
    M.add("EsevenEVAbove", "%g" % TARGET)
    M.add("EsevenFairTotal", "%g" % by["all_always_2"][0.9]["group_total_mean"])
    M.add("EsevenMaxTotal", "%g" % by["all_always_4"][0.9]["group_total_mean"])
    # ba ke toi uu EV keo sap ba ke hop tac co dieu kien
    M.add("EsevenMixThreeThree", "%g" % by["mix_ev3_cc3"][0.1]["group_total_mean"])

    # --- LLM nam o dau giua cac duong do ----------------------------------------
    base = load_baseline()
    if base:
        # Bien thien phai lay tren PHAN TRONG cua luoi (0.1..0.9), khong lay ca hai dau.
        # Do that: p = 0.0 la diem SUY BIEN -- khong the co tham hoa, nen dong gop la lo
        # thuan va bat ky agent nao hieu luat deu dong 0. Luna dong dung 0 o do va ~120 o
        # moi muc con lai, nen bien thien TOAN LUOI cua no la 121, lon hon ca duong chuan
        # EV (120). Bao con so do la noi rang Luna nhay rui ro ngang muc chuan tac, trong
        # khi thuc te no PHANG tuyet doi tren toan bo vung 0.1-0.9 va chi co dung mot cong
        # tac o cho khong con rui ro nao. Mot diem suy bien khong duoc phep dieu khien mot
        # chi so do do nhay rui ro.
        span_all, span_in = {}, {}
        inner = [p for p in sorted({p for d in base.values() for p in d})
                 if 0.0 < p < 1.0]
        for tag, d in base.items():
            vals = [d[p] for p in sorted(d)]
            span_all[tag] = max(vals) - min(vals)
            iv = [d[p] for p in inner if p in d]
            span_in[tag] = (max(iv) - min(iv)) if iv else float("nan")
        worst = max(span_in, key=lambda t: span_in[t])
        M.add("EsevenLLMMaxSpan", "%.0f" % span_in[worst])
        M.add("EsevenLLMMaxSpanModel", PRETTY.get(worst, worst))
        M.add("EsevenEVSpan", "%g" % TARGET)
        flat = [t for t in span_in if span_in[t] <= 10]
        M.add("EsevenNFlat", "%d" % len(flat))
        print("  bien thien tong quy (phan TRONG cua luoi, 0.1-0.9; ca luoi de doi chieu):")
        print("    %-36s %6.0f" % ("duong EV chuan tac", TARGET))
        for tag in sorted(span_in, key=lambda t: -span_in[t]):
            print("    %-36s %6.0f   (ca luoi %3.0f)"
                  % (PRETTY.get(tag, tag), span_in[tag], span_all[tag]))

        # p = 0: dong gop bi TROI CHAT. Khong the co tham hoa, nen moi dong bo vao quy la
        # mat han. Day la phep thu de nhat trong ca luoi, va no khong doi hoi tinh ky vong
        # -- chi doi hoi doc duoc luat.
        zero = {t: d[0.0] for t, d in base.items() if 0.0 in d}
        if zero:
            payers = {t: v for t, v in zero.items() if v > 0}
            M.add("EsevenZeroRiskPayers", "%d" % len(payers))
            M.add("EsevenZeroRiskTotal", "%d" % len(zero))
            M.add("EsevenZeroRiskMax", "%.0f" % max(zero.values()))
            M.add("EsevenZeroRiskMaxModel",
                  PRETTY.get(max(zero, key=lambda t: zero[t]), ""))
            print("  o p=0 dong gop bi TROI CHAT (khong the co tham hoa):")
            for tag in sorted(zero, key=lambda t: zero[t]):
                mark = "  <- dong 0, dung" if zero[tag] == 0 else ""
                print("    %-36s %6.0f%s" % (PRETTY.get(tag, tag), zero[tag], mark))
    else:
        print("  (chua co results/exp_baseline -> bo qua phan so sanh voi LLM)")

    M.write(TABLES / "e7_numbers.tex")

    # --- bang -------------------------------------------------------------------
    head = r"\begin{tabular}{l" + "r" * len(RISKS) + "}"
    cols = " & ".join("%g" % p for p in RISKS)
    body = []
    for cond, name in LINES:
        vals = " & ".join("%.0f" % by[cond][p]["group_total_mean"] for p in RISKS)
        body.append("%s & %s \\\\" % (name, vals))
    (TABLES / "e7_table_reference.tex").write_text(
        "\n".join([head, r"\toprule", "Reference group & " + cols + r" \\",
                   r"\midrule", *body, r"\bottomrule", r"\end{tabular}", ""]),
        encoding="utf-8")
    print("  ghi paper/AAMAS/tables/e7_table_reference.tex")

    # --- hinh -------------------------------------------------------------------
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("  (khong co matplotlib -> bo qua hinh)")
        return 0

    fig, ax = plt.subplots(figsize=(5.4, 3.2))
    ax.axhline(TARGET, color="0.75", lw=0.8, ls=":", zorder=0)
    for cond, name in LINES:
        ys = [by[cond][p]["group_total_mean"] for p in RISKS]
        ax.plot(RISKS, ys, lw=1.4, ls="--", color="0.45", zorder=1)
        ax.annotate(name, (RISKS[-1], ys[-1]), fontsize=6.5, color="0.35",
                    xytext=(2, 0), textcoords="offset points", va="center")
    for tag, d in sorted(base.items()):
        ps = sorted(d)
        ax.plot(ps, [d[p] for p in ps], marker="o", ms=3, lw=1.4,
                label=PRETTY.get(tag, tag), zorder=2)
    ax.axvline(0.5, color="0.3", lw=0.8)
    ax.annotate(r"EV pivot $p^*=0.5$", (0.5, 250), fontsize=7, rotation=90,
                ha="right", va="top", color="0.3")
    ax.set_xlabel("catastrophe probability $p$")
    ax.set_ylabel("group total (target 120)")
    ax.set_xlim(-0.02, 1.28)
    if base:
        ax.legend(fontsize=6.5, frameon=False, loc="lower left", ncol=2)
    fig.tight_layout()
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / "e7_reference.pdf")
    print("  ghi paper/AAMAS/figures/e7_reference.pdf")
    return 0


if __name__ == "__main__":
    sys.exit(main())
