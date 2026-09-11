#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""Panel tự chơi — lưới risk (B), bỏ mỏ neo (E1), probe hiểu-biết (E2).

Chạy:  python paper/AAMAS/analysis/panel_analysis.py

ĐỌC THẲNG từ `results/exp_baseline/`, `results/exp_nohint/`, `results/exp_evprobe/` và
`results/exp_evprobe_probes.jsonl`. Không chạm `Legacy_Results/` (kho đóng băng, trải
nhiều panel/prompt khác nhau). Không ghi bất cứ thứ gì vào `results/`.

SINH RA
    paper/AAMAS/tables/panel_numbers.tex          <- CHỈ \newcommand, input ở preamble
    paper/AAMAS/tables/panel_table_grid.tex       <- Bảng lưới risk (§4)
    paper/AAMAS/tables/panel_table_controls.tex   <- Bảng E1 + E2 (§5)
    paper/AAMAS/figures/panel_risk_response.pdf   <- Hình trang 1

VÌ SAO DÙNG LẠI HÀM CỦA `e3a_analysis`
    Bề ngang cột, bảng màu, kiểu nét lồng nhau và `_save_exact` đã được chốt rất kỹ ở đó
    (xem comment dài trong file ấy). Hai mục cạnh nhau trong cùng một bài mà hình khác cỡ
    chữ là lỗi ai cũng thấy. Nên import chứ không chép lại.

MỐC CHUẨN — ĐỌC TRƯỚC KHI SỬA
    Mọi con số "thiệt hại" trong mục này đo so với `opt(p) = max((1-p)*40, 20)`. Con số đó
    ĐỒNG THỜI là hai thứ, và đó là lý do nó dùng được làm mốc mà không phải bào chữa:
      (a) payoff bình quân đầu người của kết cục TỐI ƯU XÃ HỘI (phúc lợi nhóm lớn nhất), và
      (b) payoff của cân bằng Nash TỐT NHẤT cho người chơi.
    Cả hai đổi nhánh tại đúng p* = 1/2 — dưới ngưỡng thì không đóng gì là tốt nhất theo cả
    hai nghĩa, trên ngưỡng thì chia đều đúng target là tốt nhất theo cả hai nghĩa. Không có
    khoảng nào mà "tối ưu xã hội" và "cân bằng tốt nhất" đá nhau, nên không cần chọn phe.

    Mốc này GIẢ ĐỊNH TRUNG DUNG RỦI RO. Đó là một giả định thật, và mục Limitations của
    paper phải khai. Nhưng ở p = 0 thì nó KHÔNG làm việc gì cả: khi p = 0 trượt target
    không có hậu quả nào, nên payoff = 40 - c với mọi c, và đóng góp bị TRỘI HẲN
    (strictly dominated) dưới mọi hàm lợi ích tăng. Đó là lý do cột p = 0 là cột đáng tin
    nhất của cả mục và là chỗ claim nên tựa vào.
"""
from __future__ import annotations

import ast
import pathlib
import sys
from typing import Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from e3a_analysis import (  # noqa: E402  — cùng thư mục, chốt chung kiểu hình/macro/tên
    COLUMN_IN, MODEL_STYLE, MODELS as E3A_MODELS, Macros, _rc, _save_exact,
    _series_style, fmt, pname,
)

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[3]
RESULTS = REPO / "results"
TABLES = REPO / "paper" / "AAMAS" / "tables"
FIGURES = REPO / "paper" / "AAMAS" / "figures"

# --------------------------------------------------------------------------------------
# Hằng số luật chơi — lấy từ prompt trong `kaggle/benchmarks/crg_task_server.py`, KHÔNG
# đọc từ cột `contribution_options` (cột đó ghi tập nước đi QUAN SÁT ĐƯỢC trong ván, không
# phải luật chơi — xem DATA_CARD §4).
# --------------------------------------------------------------------------------------
N_PLAYERS = 6
N_ROUNDS = 10
ENDOWMENT = 40.0
TARGET = 120.0
FAIR_SHARE = TARGET / (N_PLAYERS * N_ROUNDS)          # = 2.0
FAIR_TOTAL = TARGET / N_PLAYERS                       # = 20.0, đóng đủ phần mình cả ván
PSTAR = FAIR_TOTAL / ENDOWMENT                        # = 0.5, xem docstring mốc chuẩn

N_BOOT = 10_000
N_PERM = 10_000
SEED = 20260911

# Một nguồn duy nhất cho tên model: `MODELS` của e3a_analysis. Bản trước chép lại bảng ánh
# xạ ở đây, tức là hai chỗ phải sửa khi panel đổi — và chỗ thứ hai chắc chắn sẽ bị quên.
SHORT: Dict[str, str] = {tag: short for tag, (_label, short) in E3A_MODELS.items()}
# Thứ tự trình bày: theo mức đóng góp bình quân TĂNG DẦN trên lưới baseline, để bảng và
# hình đọc cùng một chiều. Chốt cứng chứ không sắp theo data — sắp theo data thì thứ tự
# bảng đổi mỗi lần thêm ván, và người đọc bản nháp trước sẽ so nhầm hàng.
ORDER: Tuple[str, ...] = ("Qwen", "Flash", "Luna", "Haiku", "Grok")
# Nhãn bảng — LẤY THẲNG từ `MODELS` của e3a_analysis, không tự đặt bộ tên thứ hai.
#
# Bản trước ở đây dùng slug đầy đủ (`\textsc{gemini-3.5-flash-lite}`) trong khi §6 đã dùng
# "Flash-Lite 3.5" trong bảng và "Flash-Lite" trong văn xuôi. Hai hệ tên trong cùng một
# bài là thứ người đọc thấy ngay ở lần lật thứ hai và không cách nào bào chữa được — và
# slug đầy đủ còn nuốt mất bề ngang của cột model trong bài hai cột. Slug đầy đủ chỉ xuất
# hiện ĐÚNG MỘT LẦN, ở §3 khi giới thiệu panel, kèm nhãn ngắn trong ngoặc.
FULL: Dict[str, str] = {short: label for label, short in E3A_MODELS.values()}


def opt_payoff(p: float) -> float:
    """Payoff bình quân đầu người của kết cục tối ưu (= của cân bằng Nash tốt nhất)."""
    return max((1.0 - p) * ENDOWMENT, FAIR_TOTAL)


# ======================================================================================
# 1. Nạp dữ liệu
# ======================================================================================
LIST_KEYS = ("strategies", "scores")


def load(experiment: str) -> pd.DataFrame:
    """Một dòng = một ván, thêm cột `m` (tên ngắn) và `own` (đóng góp bình quân/ghế).

    `own` là trung bình của SÁU ghế trong đúng ván đó, nên đơn vị phân tích là VÁN chứ
    không phải ghế: sáu ghế của một ván không độc lập (chúng đọc lịch sử của nhau), nên
    coi mỗi ghế là một quan sát sẽ thổi phồng n lên sáu lần và mọi p-value đều sai. Mọi
    bootstrap và permutation dưới đây lấy mẫu trên VÁN, đúng vì lý do này.
    """
    root = RESULTS / experiment
    if not root.is_dir():
        raise SystemExit(f"không thấy {root} — chạy to_wide_csv.py trước")
    frames: List[pd.DataFrame] = []
    for f in sorted(root.glob("*/*/*.csv"), key=lambda q: (float(q.parent.parent.name), q.name)):
        d = pd.read_csv(f)
        tag = f.parent.name
        if tag not in SHORT:
            raise SystemExit(f"model lạ trong {f}: {tag} — panel đã khoá 5 model (plan §5)")
        d["m"] = SHORT[tag]
        frames.append(d)
    df = pd.concat(frames, ignore_index=True)

    for i in range(1, N_PLAYERS + 1):
        col = f"agent{i}_strategies"
        df[col] = df[col].map(ast.literal_eval)
        df[f"tot{i}"] = df[col].map(sum)
    df["own"] = df[[f"tot{i}" for i in range(1, N_PLAYERS + 1)]].mean(axis=1)
    df["round1"] = df[[f"agent{i}_strategies" for i in range(1, N_PLAYERS + 1)]].apply(
        lambda r: float(np.mean([s[0] for s in r])), axis=1)
    df["opt"] = df.risk_probability.map(opt_payoff)
    df["forfeit"] = df.opt - df.mean_payoff

    if int(df.n_parse_failures.sum()) != 0:
        raise SystemExit(f"{experiment}: có parse failure — verify_wide.py lẽ ra đã chặn")
    if set(df.language.unique()) != {"en"}:
        raise SystemExit(f"{experiment}: có ngôn ngữ khác en — plan §5.1")
    return df


def exact_share(df: pd.DataFrame, value: int) -> pd.Series:
    """Tỉ lệ ghế chơi ĐÚNG `value` ở cả mười vòng, tính theo model.

    Đây là thước đo "chính sách suy biến" rẻ nhất và khó cãi nhất: nó không hỏi trung bình
    bao nhiêu mà hỏi có bao nhiêu ghế chạy đúng MỘT quỹ đạo hằng. Trung bình 20,0 có thể
    là chia đều mọi vòng, cũng có thể là nửa số vòng chơi 0 nửa chơi 4 — cột này tách hai
    thứ đó ra.
    """
    want = [value] * N_ROUNDS
    frac = df[[f"agent{i}_strategies" for i in range(1, N_PLAYERS + 1)]].apply(
        lambda r: float(np.mean([list(s) == want for s in r])), axis=1)
    return df.assign(_f=frac).groupby("m")._f.mean()


# ======================================================================================
# 2. Thống kê: bootstrap phần trăm, permutation hai mẫu, permutation cho hệ số góc
# ======================================================================================
def boot_ci(x: Sequence[float], rng: np.random.Generator, q: float = 95.0) -> Tuple[float, float]:
    a = np.asarray(x, dtype=float)
    if a.size == 0:
        return float("nan"), float("nan")
    idx = rng.integers(0, a.size, size=(N_BOOT, a.size))
    means = a[idx].mean(axis=1)
    lo, hi = (100.0 - q) / 2.0, 100.0 - (100.0 - q) / 2.0
    return float(np.percentile(means, lo)), float(np.percentile(means, hi))


def perm_two_sample(x: Sequence[float], y: Sequence[float], rng: np.random.Generator) -> Tuple[float, float]:
    """Trả (hiệu trung bình y-x, p hai phía). Đơn vị lấy mẫu là VÁN (xem `load`)."""
    a, b = np.asarray(x, float), np.asarray(y, float)
    obs = b.mean() - a.mean()
    pool = np.concatenate([a, b])
    n = a.size
    idx = np.argsort(rng.random((N_PERM, pool.size)), axis=1)
    draws = pool[idx]
    stat = draws[:, n:].mean(axis=1) - draws[:, :n].mean(axis=1)
    return float(obs), float((np.abs(stat) >= abs(obs) - 1e-12).mean())


def perm_slope(p: Sequence[float], y: Sequence[float], rng: np.random.Generator) -> Tuple[float, float]:
    """Hệ số góc OLS của `y` theo `p`, p-value bằng hoán vị nhãn risk.

    Hoán vị NHÃN RISK chứ không hoán vị y: giả thuyết không là "đóng góp không phụ thuộc
    risk", nên thứ phải xáo là ánh xạ ván -> mức risk. Hai cách cho cùng phân phối ở đây
    (thiết kế cân bằng, 10 ván mỗi ô) nhưng cách này mới phát biểu đúng giả thuyết.
    """
    x, yy = np.asarray(p, float), np.asarray(y, float)
    obs = float(np.polyfit(x, yy, 1)[0])
    stat = np.empty(N_PERM)
    for k in range(N_PERM):
        stat[k] = np.polyfit(rng.permutation(x), yy, 1)[0]
    return obs, float((np.abs(stat) >= abs(obs) - 1e-12).mean())


def ptex(pv: float) -> str:
    r"""p-value cho văn xuôi. `< 0.001` thay vì `0.000` — `0.000` là sai, p không bằng 0."""
    return r"{<}0.001" if pv < 0.001 else f"{pv:.3f}"


def nz(x: float, nd: int = 2) -> str:
    """Như `fmt`, nhưng KHÔNG BAO GIỜ in ra `-0.00`.

    Hệ số góc của Flash-Lite đo được $-0{,}0016$, làm tròn hai chữ số thành `-0.00`. Đọc
    trong bảng thì "âm không phẩy không không" trông như lỗi định dạng, và tệ hơn là nó
    gợi một chiều hướng ở một đại lượng vốn KHÔNG phân biệt được với 0 ($P=0{,}911$). Dấu
    trừ ở đây mang thông tin bằng không nhưng gây hiểu nhầm khác không.
    """
    s = fmt(x, nd)
    return s.lstrip("-") if float(s) == 0.0 else s


_WORDS = ("none", "one", "two", "three", "four", "five", "six", "seven", "eight",
          "nine", "ten", "eleven", "twelve")


def word(n: int) -> str:
    """Số đếm nhỏ viết thành CHỮ, vì `\\PanelNFlat` in ra "3" đọc rất tệ trong văn xuôi.

    Bản nháp đầu ra câu "Of 5 models, 3 show no dependence" — đúng số, sai văn. Không
    được chữa bằng cách gõ tay "three" vào section: gõ tay là mất liên kết với data, và
    lần chạy sau data đổi thì con số trong bảng đổi còn con số trong câu thì không. Nên
    mỗi đại lượng đếm nhỏ xuất hai macro: `<Tên>` (chữ số, dùng trong ngoặc/bảng) và
    `<Tên>Word` (chữ, dùng trong câu).
    """
    return _WORDS[n] if 0 <= n < len(_WORDS) else str(n)


def join_and(names: Sequence[str]) -> str:
    """`a`, `a and b`, `a, b and c` — KHÔNG phải "a, b" như `", ".join` cho ra.

    Danh sách model nối bằng dấu phẩy lọt vào giữa một câu tiếng Anh đọc như câu bị cụt
    ("Qwen, Grok give the same answer"). Đây là chỗ duy nhất sửa; mọi macro danh sách đều
    đi qua hàm này.
    """
    n = [pname(x) for x in names]
    if len(n) <= 1:
        return n[0] if n else ""
    return f"{', '.join(n[:-1])} and {n[-1]}"


# ======================================================================================
# 3. Hình trang 1
# ======================================================================================
def fig_risk_response(base: pd.DataFrame, path: pathlib.Path, rng: np.random.Generator) -> None:
    r"""Hai bảng con dùng CHUNG trục risk: (a) đóng góp, (b) payoff, kèm mốc tối ưu.

    VÌ SAO HAI BẢNG CON CHỨ KHÔNG MỘT. Bảng (a) một mình không nói được cái giá: Grok đóng
    38 và Qwen đóng 18 trông chỉ như "khác mức hợp tác", trong khi payoff của chúng là 0,1
    và 0,0 — cùng một kết cục tệ, tới bằng hai con đường ngược nhau. Bảng (b) là chỗ duy
    nhất trong bài mà hai con đường ấy gặp nhau ở đáy.

    VÌ SAO MỐC TỐI ƯU ĐƯỢC VẼ Ở CẢ HAI. Ở (a) nó gãy khúc TỪ 0 LÊN 20 tại p*, ở (b) nó đi
    XUỐNG rồi phẳng. Một đường thẳng model nằm ngang cắt ngang cả hai cho thấy ngay: không
    phải "hợp tác nhiều quá" mà là "không đổi gì cả khi mốc đổi".
    """
    _rc()
    fig, axes = plt.subplots(2, 1, figsize=(COLUMN_IN, 3.20), sharex=True)
    ps = np.array(sorted(base.risk_probability.unique()))
    grid = np.linspace(0.0, 1.0, 601)

    # Mốc: vẽ TRƯỚC và dày, để model nằm đúng trên nó vẫn thấy được cả hai (xem BR_LW
    # trong e3a_analysis — cùng lý do, cùng cách xử lý).
    bench_c = np.where(grid < PSTAR, 0.0, FAIR_TOTAL)
    bench_p = np.array([opt_payoff(float(g)) for g in grid])
    for ax, bench in ((axes[0], bench_c), (axes[1], bench_p)):
        ax.plot(grid, bench, lw=4.0, color="#BBBBBB", solid_capstyle="butt", zorder=1)

    for i, m in enumerate(ORDER):
        d = base[base.m == m]
        colour, marker, dash = MODEL_STYLE[m]
        lw, ms, z = _series_style(i)
        for ax, col in ((axes[0], "own"), (axes[1], "mean_payoff")):
            mu = np.array([d[d.risk_probability == p][col].mean() for p in ps])
            ci = np.array([boot_ci(d[d.risk_probability == p][col].values, rng) for p in ps])
            ax.errorbar(ps, mu, yerr=[mu - ci[:, 0], ci[:, 1] - mu],
                        color=colour, marker=marker, ls=dash, lw=lw, markersize=ms,
                        mfc="none", mew=0.9, elinewidth=0.6, capsize=1.2, zorder=z,
                        label=m if col == "own" else None)

    axes[0].set_ylabel("contributed, of 40")
    axes[1].set_ylabel("final cash, of 40")
    axes[1].set_xlabel("catastrophe risk $p$")
    axes[0].set_ylim(-2.0, 42.0)
    axes[1].set_ylim(-2.0, 42.0)
    for ax in axes:
        ax.set_xlim(-0.04, 1.04)
        ax.set_xticks(np.arange(0.0, 1.01, 0.2))
        ax.axvline(PSTAR, color="#888888", lw=0.5, ls=(0, (1, 2)), zorder=0)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axes[0].legend(ncol=5, loc="upper center", bbox_to_anchor=(0.5, 1.30),
                   frameon=False, handlelength=1.9, columnspacing=0.8, handletextpad=0.4)
    fig.subplots_adjust(left=0.155, right=0.995, top=0.885, bottom=0.128, hspace=0.13)
    _save_exact(fig, path)
    plt.close(fig)


# ======================================================================================
# 4. Bảng
# ======================================================================================
def table_grid(stats: Dict[str, Dict[str, float]]) -> str:
    r"""Bảng §4 — mỗi model một hàng, cột p = 0 tách riêng vì nó là cột KHÔNG cần giả định.

    Cột `p=0` đứng riêng chứ không gộp vào trung bình gộp: ở p = 0 đóng góp bị trội hẳn
    dưới mọi hàm lợi ích tăng, nên con số ở đó không phụ thuộc mốc trung dung rủi ro, còn
    cột gộp thì có. Gộp hai loại bằng chứng vào một con số là làm mất cái mạnh hơn.
    """
    rows = []
    for m in ORDER:
        s = stats[m]
        rows.append(
            # Hai cột cuối bọc `$...$`: dấu trừ của hệ số góc phải là dấu TRỪ toán học chứ
            # không phải gạch nối, và `{<}` chỉ có nghĩa trong math mode.
            f"{FULL[m]} & {fmt(s['zero_own'], 1)} & {fmt(s['zero_pay'], 1)} & "
            f"{fmt(s['own'], 1)} & {fmt(s['reach'], 0)} & {fmt(s['pay'], 1)} & "
            f"{fmt(s['forfeit_pct'], 0)} & ${nz(s['slope'], 2)}$ & ${ptex(s['slope_p'])}$ \\\\")
    body = "\n".join(rows)
    return (
        "% SINH TỰ ĐỘNG bởi paper/AAMAS/analysis/panel_analysis.py — ĐỪNG SỬA TAY.\n"
        "\\begin{table}[t]\n\\centering\n\\small\n\\setlength{\\tabcolsep}{3.2pt}\n"
        "\\begin{tabular}{lrrrrrrrr}\n\\toprule\n"
        " & \\multicolumn{2}{c}{$p=0$} & \\multicolumn{4}{c}{all \\PanelNrisks{} risk levels} & "
        "\\multicolumn{2}{c}{slope in $p$} \\\\\n"
        "\\cmidrule(lr){2-3}\\cmidrule(lr){4-7}\\cmidrule(lr){8-9}\n"
        "model & giv. & cash & giv. & hit\\% & cash & lost\\% & $\\hat\\beta$ & $P$ \\\\\n"
        "\\midrule\n" + body + "\n\\bottomrule\n\\end{tabular}\n"
        "\\caption{Self-play on the eleven-point risk grid, $\\PanelNgamesBaseline$ games. "
        "``giv.'' is the mean total a seat contributes of its $\\PanelEndowment$-unit "
        "endowment, ``cash'' its mean final payoff, ``hit\\%'' the share of games reaching "
        "the target. ``lost\\%'' is the share of the attainable payoff forfeited, measured "
        "against $\\max\\{(1-p)\\PanelEndowment,\\PanelFairTotal\\}$, which is both the "
        "welfare-optimal outcome and the best Nash equilibrium "
        "(Proposition~\\ref{prop:eq}). The two $p=0$ columns need no such benchmark: there "
        "contributing is strictly dominated, so every unit given is lost under any "
        "increasing utility. $\\hat\\beta$ is the OLS slope of ``giv.'' on $p$, with $P$ "
        "from a $\\PanelNpermTex$-resample permutation test over risk labels; the unit of "
        "analysis is the game.}\n"
        "\\label{tab:grid}\n\\end{table}\n")


def table_controls(nohint: Dict[str, Dict[str, float]], probe: Dict[str, Dict[str, float]]) -> str:
    r"""Bảng §5 — E1 và E2 cạnh nhau, cố ý.

    Hai thí nghiệm này trả lời hai câu hỏi khác nhau ("có phải chỉ làm theo mỏ neo trong
    prompt?" và "có phải không hiểu luật/không tính được?") nhưng chúng chỉ có sức nặng KHI
    ĐỌC CÙNG NHAU: mỗi cái một mình loại bỏ một cách giải thích, hai cái cùng lúc thì không
    còn cách giải thích rẻ tiền nào. Tách thành hai bảng là mời người đọc bỏ qua một cái.
    """
    rows = []
    for m in ORDER:
        n, q = nohint[m], probe[m]
        rows.append(
            f"{FULL[m]} & {fmt(n['base'], 1)} & {fmt(n['after'], 1)} & "
            f"${nz(n['delta'], 1)}$ & ${ptex(n['p'])}$ & {fmt(q['rules'], 0)} & "
            f"{fmt(q['compare'], 0)} & {fmt(q['compare_low'], 0)} & {fmt(q['contrib_low'], 1)} \\\\")
    body = "\n".join(rows)
    return (
        "% SINH TỰ ĐỘNG bởi paper/AAMAS/analysis/panel_analysis.py — ĐỪNG SỬA TAY.\n"
        "\\begin{table}[t]\n\\centering\n\\small\n\\setlength{\\tabcolsep}{3.0pt}\n"
        "\\begin{tabular}{lrrrrrrrr}\n\\toprule\n"
        " & \\multicolumn{4}{c}{focal point deleted (\\S\\ref{sec:nohint})} & "
        "\\multicolumn{4}{c}{asked outright (\\S\\ref{sec:evprobe})} \\\\\n"
        "\\cmidrule(lr){2-5}\\cmidrule(lr){6-9}\n"
        "model & with & w/o & $\\Delta$ & $P$ & rules & EV & "
        "EV$_{.1}$ & giv.$_{.1}$ \\\\\n"
        "\\midrule\n" + body + "\n\\bottomrule\n\\end{tabular}\n"
        "\\caption{Two controls, on the same panel. Left: mean total contributed per seat "
        "with the prompt's equal-split gloss present (``with'') and deleted (``w/o''), at "
        "$p\\in\\{0.1,0.5,0.9\\}$, $\\PanelNohintGames$ games each; $P$ from a "
        "$\\PanelNpermTex$-resample permutation test on games. Deleting the focal point "
        "never lowers contribution. Right: accuracy (\\%) on in-situ questions asked of the "
        "playing agent --- ``rules'' over $\\PanelProbeRulesN$ questions on the mechanics, "
        "``EV'' on the expected-value comparison between contributing one's share and "
        "contributing nothing. ``EV$_{.1}$'' restricts that comparison to $p=0.1$, where "
        "the correct answer is that contributing nothing pays more, and ``giv.$_{.1}$'' is "
        "what the same seats contributed in the same games. Read the EV columns together "
        "with \\S\\ref{sec:evprobe}: \\PanelProbeConstantModels{} give the same answer at "
        "every risk level, so their EV$_{.1}$ scores are a coincidence rather than a "
        "computation, and the dissociation is claimed only for the three models that "
        "answer differently at each level and get each one right.}\n"
        "\\label{tab:controls}\n\\end{table}\n")


# ======================================================================================
# 5. main
# ======================================================================================
def main() -> int:
    rng = np.random.default_rng(SEED)
    mac = Macros()
    mac._prefix = "Panel"  # noqa: SLF001 — Macros gắn cứng tiền tố Ethreea, xem `add` dưới

    # Macros.add() của e3a_analysis gắn cứng tiền tố "Ethreea". Bọc lại thay vì sửa file
    # kia: file kia đang sinh 394 macro mà mục E3a đã dùng, đổi tiền tố ở đó là hỏng hết.
    items: List[Tuple[str, str]] = []
    seen: Dict[str, str] = {}

    def add(name: str, value: str) -> None:
        full = "Panel" + name
        if not full.isalpha():
            raise ValueError(f"tên macro phải toàn chữ cái: {full}")
        if full in seen and seen[full] != value:
            raise ValueError(f"macro {full} định nghĩa hai lần khác giá trị")
        if full not in seen:
            seen[full] = value
            items.append((full, value))

    def count(name: str, n: int) -> None:
        """Xuất BA dạng của cùng một số đếm, vì cả ba đều cần và không thay nhau được.

        `<name>`        chữ số   — cho bảng và cho trong ngoặc.
        `<name>Word`    chữ      — cho giữa câu. Đừng bọc trong `$...$`: math mode in chữ
                                   ra kiểu NGHIÊNG, nên "the two models" hoá "the *two*
                                   models". Đã dính lỗi này một lần, ở 22 chỗ.
        `<name>WordCap` chữ hoa  — cho ĐẦU CÂU. Không có nó thì hoặc là câu bắt đầu bằng
                                   chữ thường, hoặc là phải gõ tay "Three" — mà gõ tay thì
                                   lần chạy sau data đổi, bảng đổi, câu thì không.
        """
        add(name, str(n))
        add(name + "Word", word(n))
        add(name + "WordCap", word(n).capitalize())

    def num(name: str, value: float, nd: int = 2) -> None:
        import decimal
        q = decimal.Decimal(repr(float(value))).quantize(
            decimal.Decimal(1).scaleb(-nd), rounding=decimal.ROUND_HALF_UP)
        if q == 0:
            q = abs(q)
        add(name, f"{q:f}")

    # ---------------------------------------------------------------------------- B
    base = load("exp_baseline")
    ps = sorted(base.risk_probability.unique())
    print(f"[B] {len(base)} ván · {len(ps)} mức risk · {base.m.nunique()} model")

    add("Ngames", str(len(base) + 150 + 150 + 1000))
    add("NgamesBaseline", str(len(base)))
    add("NgamesPerModel", str(len(base) // base.m.nunique()))
    count("Nmodels", int(base.m.nunique()))
    count("Nrisks", len(ps))
    add("Nreps", str(base.rep.nunique()))
    add("Npercell", str(int(base.groupby(["m", "risk_probability"]).size().unique()[0])))
    count("Nplayers", N_PLAYERS)
    count("Nrounds", N_ROUNDS)
    add("Endowment", f"{ENDOWMENT:.0f}")
    add("Target", f"{TARGET:.0f}")
    add("FairShare", f"{FAIR_SHARE:.0f}")
    add("FairTotal", f"{FAIR_TOTAL:.0f}")
    add("Pstar", "1/2")
    add("Ndecisions", f"{len(base) * N_PLAYERS * N_ROUNDS:,}".replace(",", "{,}"))
    # 1850 ván × 6 ghế × 10 vòng. Đếm cả E3a, vì cổng "0 lượt hỏng / 0 lượt bị cắt" chạy
    # trên TOÀN BỘ vòng chạy chứ không riêng lưới baseline.
    add("NdecisionsAll", f"{1850 * N_PLAYERS * N_ROUNDS:,}".replace(",", "{,}"))
    add("Nperm", str(N_PERM))
    add("NpermTex", f"{N_PERM:,}".replace(",", "{,}"))
    add("Nboot", f"{N_BOOT:,}".replace(",", "{,}"))

    stats: Dict[str, Dict[str, float]] = {}
    for m in ORDER:
        d = base[base.m == m]
        z = d[d.risk_probability == 0.0]
        one = d[d.risk_probability == 1.0]
        slope, slope_p = perm_slope(d.risk_probability.values, d.own.values, rng)
        delta, delta_p = perm_two_sample(z.own.values, one.own.values, rng)
        s = dict(
            own=d.own.mean(), reach=100 * d.target_reached.mean(), pay=d.mean_payoff.mean(),
            forfeit=d.forfeit.mean(), forfeit_pct=100 * d.forfeit.mean() / d.opt.mean(),
            zero_own=z.own.mean(), zero_pay=z.mean_payoff.mean(),
            zero_reach=100 * z.target_reached.mean(), one_own=one.own.mean(),
            slope=slope, slope_p=slope_p, delta=delta, delta_p=delta_p,
            cat=int(d.catastrophe.sum()), miss=int((1 - d.target_reached).sum()),
        )
        stats[m] = s
        num(f"Own{m}", s["own"], 1); num(f"Reach{m}", s["reach"], 0)
        num(f"Pay{m}", s["pay"], 1); num(f"Forfeit{m}", s["forfeit"], 1)
        num(f"ForfeitPct{m}", s["forfeit_pct"], 0)
        num(f"ZeroOwn{m}", s["zero_own"], 1); num(f"ZeroPay{m}", s["zero_pay"], 1)
        num(f"ZeroReach{m}", s["zero_reach"], 0); num(f"OneOwn{m}", s["one_own"], 1)
        num(f"Slope{m}", s["slope"], 2); add(f"SlopeP{m}", ptex(s["slope_p"]))
        add(f"ZeroOneP{m}", ptex(s["delta_p"])); num(f"ZeroOneDelta{m}", s["delta"], 1)
        add(f"Cat{m}", str(s["cat"])); add(f"Miss{m}", str(s["miss"]))
        print(f"  {m:6s} own={s['own']:5.2f} pay={s['pay']:5.2f} lost={s['forfeit_pct']:4.1f}% "
              f"slope={s['slope']:+.2f} (P={s['slope_p']:.3f})  p0: own={s['zero_own']:5.2f}")

    # Ai PHẲNG, ai KHÔNG — đếm bằng chính p-value của hệ số góc, đừng đếm bằng mắt.
    flat = [m for m in ORDER if stats[m]["slope_p"] >= 0.05]
    moved = [m for m in ORDER if stats[m]["slope_p"] < 0.05]
    count("NFlat", len(flat))
    add("FlatModels", join_and(flat))
    count("NMoved", len(moved))
    add("MovedModels", join_and(moved))

    # Hai model CÓ hệ số góc: đo lại khi BỎ p = 0, vì với Luna toàn bộ độ dốc nằm ở đúng
    # bước nhảy tại p = 0 và gọi nó là "phản ứng với risk" là đọc sai một bậc thang thành
    # một đường dốc. Cột này là chỗ duy nhất tách được hai thứ đó.
    for m in moved:
        d = base[(base.m == m) & (base.risk_probability > 0.0)]
        sl, pv = perm_slope(d.risk_probability.values, d.own.values, rng)
        num(f"SlopePos{m}", sl, 2)
        add(f"SlopePosP{m}", ptex(pv))
        num(f"PosOwn{m}", d.own.mean(), 1)
        print(f"  {m:6s} bỏ p=0: slope={sl:+.2f} (P={pv:.3f}), own={d.own.mean():.2f}")

    # Grok không đơn điệu: cao nhất ở HAI đầu. Ghi lại mức thấp nhất và nó rơi ở đâu, vì
    # một hệ số góc dương gán cho một đường chữ U là mô tả sai.
    gk = base[base.m == "Grok"].groupby("risk_probability").own.mean()
    num("MinOwnGrok", gk.min(), 1)
    add("MinOwnGrokAt", f"{gk.idxmin():g}")
    # "Đóng ở p=0 nhiều hơn ở BAO NHIÊU mức risk dương" — đếm, đừng viết "cao thứ nhì".
    # Đã suýt viết "thứ nhì" trong bản nháp: thật ra p=0 đứng thứ TƯ (sau p=1; 0,8; 0,9).
    gk_pos = gk[gk.index > 0.0]
    add("GrokZeroBeats", str(int((gk_pos < gk.loc[0.0]).sum())))
    add("GrokPosLevels", str(len(gk_pos)))

    num("ForfeitPanel", base.forfeit.mean(), 1)
    num("ForfeitPanelPct", 100 * base.forfeit.mean() / base.opt.mean(), 0)
    num("PayPanel", base.mean_payoff.mean(), 1)
    num("OptPanel", base.opt.mean(), 1)

    # p = 0: cột không cần giả định rủi ro
    z = base[base.risk_probability == 0.0]
    seats_zero = np.concatenate([z[f"tot{i}"].values for i in range(1, N_PLAYERS + 1)])
    add("ZeroGames", str(len(z)))
    add("ZeroGamesPaying", str(int((z.group_total > 0).sum())))
    add("ZeroSeats", str(seats_zero.size))
    add("ZeroSeatsPaying", str(int((seats_zero > 0).sum())))
    num("ZeroSeatsPayingPct", 100 * (seats_zero > 0).mean(), 0)
    num("ZeroOwnPanel", z.own.mean(), 1)
    num("ZeroForfeitPanel", z.forfeit.mean(), 1)
    count("ZeroModelsAtCeiling", int((z.groupby("m").target_reached.mean() == 1.0).sum()))

    # Chính sách suy biến
    # MỘT CHỮ SỐ THẬP PHÂN, KHÔNG PHẢI SỐ NGUYÊN — cố ý. Làm tròn 99,7% thành "100%" biến
    # một mô tả đúng thành một khẳng định tuyệt đối sai, và đây đúng là cột hay bị trích
    # thành "chơi y hệt trong MỌI ván". Flash đo được 99,6% chứ không phải 100%.
    two, four = exact_share(base, 2), exact_share(base, 4)
    for m in ORDER:
        num(f"ExactTwo{m}", 100 * two[m], 1)
        num(f"ExactFour{m}", 100 * four[m], 1)
    num("FlashSd", base[base.m == "Flash"].own.std(), 2)

    # ---------------------------------------------------------------------------- E1
    nh = load("exp_nohint")
    rs = sorted(nh.risk_probability.unique())
    bb = base[base.risk_probability.isin(rs)]
    add("NohintGames", str(len(nh) // nh.m.nunique()))
    add("NohintRisks", ", ".join(f"{r:g}" for r in rs))
    print(f"[E1] {len(nh)} ván tại p ∈ {rs}")
    nohint: Dict[str, Dict[str, float]] = {}
    for m in ORDER:
        x, y = bb[bb.m == m].own.values, nh[nh.m == m].own.values
        delta, pv = perm_two_sample(x, y, rng)
        nohint[m] = dict(base=x.mean(), after=y.mean(), delta=delta, p=pv,
                         reach_base=100 * bb[bb.m == m].target_reached.mean(),
                         reach_after=100 * nh[nh.m == m].target_reached.mean(),
                         pay_base=bb[bb.m == m].mean_payoff.mean(),
                         pay_after=nh[nh.m == m].mean_payoff.mean())
        for k, nd in (("base", 1), ("after", 1), ("delta", 1), ("reach_base", 0),
                      ("reach_after", 0), ("pay_base", 1), ("pay_after", 1)):
            num(f"Nohint{k.title().replace('_', '')}{m}", nohint[m][k], nd)
        add(f"NohintP{m}", ptex(pv))
        print(f"  {m:6s} {x.mean():6.2f} -> {y.mean():6.2f}  ({delta:+.2f}, P={pv:.4f})")
    count("NohintDown", sum(1 for m in ORDER if nohint[m]["delta"] < 0 and nohint[m]["p"] < 0.05))
    count("NohintUp", sum(1 for m in ORDER if nohint[m]["delta"] > 0 and nohint[m]["p"] < 0.05))
    count("NohintFlat", sum(1 for m in ORDER if nohint[m]["p"] >= 0.05))
    add("NohintFlatModels", join_and([m for m in ORDER if nohint[m]["p"] >= 0.05]))
    add("NohintUpModels", join_and([m for m in ORDER if nohint[m]["delta"] > 0 and nohint[m]["p"] < 0.05]))
    nh_two, nh_four = exact_share(nh, 2), exact_share(nh, 4)
    bb_two, bb_four = exact_share(bb, 2), exact_share(bb, 4)
    for m in ORDER:
        num(f"NohintExactTwo{m}", 100 * nh_two[m], 1)
        num(f"NohintExactFour{m}", 100 * nh_four[m], 1)
        num(f"NohintBaseExactTwo{m}", 100 * bb_two[m], 1)
        num(f"NohintBaseExactFour{m}", 100 * bb_four[m], 1)

    # ---------------------------------------------------------------------------- E2
    pr = pd.read_json(RESULTS / "exp_evprobe_probes.jsonl", lines=True)
    pr["m"] = pr.model.map(SHORT)
    if int(pr.parse_failed.sum()) != 0:
        raise SystemExit("probe có parse failure")
    ev = load("exp_evprobe")
    seat_tot = []
    for _, g in ev.iterrows():
        for i in range(1, N_PLAYERS + 1):
            seat_tot.append(dict(game_id=g.game_id, player=g[f"agent{i}_name"], tot=g[f"tot{i}"]))
    seat = pd.DataFrame(seat_tot)
    linked = pr.merge(seat, on=["game_id", "player"], how="inner", validate="many_to_one")
    if len(linked) != len(pr):
        raise SystemExit(f"probe không khớp ghế: {len(linked)} / {len(pr)}")

    rules = pr[pr.category == "rules"]
    cmp_ = linked[linked.question_id == "value_compare"]
    cmp_low = cmp_[cmp_.risk_probability == rs[0]]
    add("ProbeN", str(len(pr)))
    add("ProbeRulesN", f"{len(rules):,}".replace(",", "{,}"))
    add("ProbeRounds", ", ".join(str(r) for r in sorted(pr["round"].unique())))
    add("ProbePerGame", str(int(pr.groupby("game_id").size().unique()[0])))
    count("ProbeRuleKinds", int(rules.question_id.nunique()))
    num("ProbeRulesAcc", 100 * rules.correct.mean(), 1)
    num("ProbeCompareAcc", 100 * cmp_.correct.mean(), 1)
    add("ProbeCompareN", str(len(cmp_)))
    num("ProbeCompareLowAcc", 100 * cmp_low.correct.mean(), 1)
    num("ProbeLowContrib", cmp_low.tot.mean(), 1)
    num("ProbeLowOptCash", (1 - rs[0]) * ENDOWMENT, 0)
    add("ProbeLowRisk", f"{rs[0]:g}")
    num("ProbeValueAcc", 100 * pr[pr.category == "value"].correct.mean(), 1)

    # Câu value thứ hai (`value_defect_ev`, "trung bình bạn còn bao nhiêu tiền") KHÔNG
    # dùng để đặt claim, và đây là lý do — đọc kỹ trước khi ai đó định trích nó.
    # Hỏi giữa ván, "contribute 0 in every round" đọc được theo hai nghĩa: mọi vòng của
    # CẢ VÁN (ground truth (1-p)*40) hay mọi vòng CÒN LẠI (thành (1-p)*số dư hiện có).
    # Nhiều câu sai là model tính ĐÚNG nghĩa thứ hai. Nên con số này là CẬN DƯỚI của hiểu
    # biết thật, và paper chỉ dùng `value_compare` — câu so sánh hai chiến lược đã nêu rõ
    # cả hai bằng lời, không có chỗ cho cách đọc thứ hai.
    pt = pr[pr.question_id == "value_defect_ev"]
    num("ProbeEvPointAcc", 100 * pt.correct.mean(), 1)
    add("ProbeEvPointN", str(len(pt)))

    # Model trả lời HẰNG bất kể p thì "đúng ở p=0,1" chỉ là trùng, không phải tính được.
    # Cột này là thứ tách hai chuyện đó, và nó là lý do §5.2 không đọc bảng theo cột `EV`.
    for m in ORDER:
        a = cmp_[cmp_.m == m].parsed_answer
        num(f"ProbeModalShare{m}", 100 * a.value_counts(normalize=True).iloc[0], 0)
    add("ProbeConstantModels", join_and([
        m for m in ORDER
        if cmp_[cmp_.m == m].groupby("risk_probability").parsed_answer.agg(
            lambda s: s.value_counts().idxmax()).nunique() == 1]))

    probe: Dict[str, Dict[str, float]] = {}
    for m in ORDER:
        q = dict(rules=100 * rules[rules.m == m].correct.mean(),
                 compare=100 * cmp_[cmp_.m == m].correct.mean(),
                 compare_low=100 * cmp_low[cmp_low.m == m].correct.mean(),
                 contrib_low=cmp_low[cmp_low.m == m].tot.mean())
        probe[m] = q
        num(f"ProbeRules{m}", q["rules"], 0); num(f"ProbeCompare{m}", q["compare"], 0)
        num(f"ProbeCompareLow{m}", q["compare_low"], 0)
        num(f"ProbeLowContrib{m}", q["contrib_low"], 1)
        print(f"  {m:6s} rules={q['rules']:5.1f}%  EV={q['compare']:5.1f}%  "
              f"EV@p={rs[0]}: {q['compare_low']:5.1f}% while giving {q['contrib_low']:.1f}")
    count("ProbeRulesPerfect", sum(1 for m in ORDER if probe[m]["rules"] == 100.0))
    count("ProbeCompareLowPerfect", sum(1 for m in ORDER if probe[m]["compare_low"] == 100.0))

    # ---------------------------------------------------------------------------- ghi
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    header = (
        "% ==================================================================\n"
        "% SINH TỰ ĐỘNG bởi paper/AAMAS/analysis/panel_analysis.py — ĐỪNG SỬA TAY.\n"
        "% Chạy lại: python paper/AAMAS/analysis/panel_analysis.py\n"
        "% Nguồn: results/exp_baseline, exp_nohint, exp_evprobe (+ probes.jsonl).\n"
        "%\n"
        "% File này CHỈ chứa \\newcommand nên \\input được ngay trong preamble.\n"
        "% Hai bảng booktabs nằm ở file riêng và gọi lại chính các macro này:\n"
        "%   \\input{tables/panel_table_grid.tex}\n"
        "%   \\input{tables/panel_table_controls.tex}\n"
        "%\n"
        "% Quy ước tên: \\Panel<Đại lượng><Model>, Model = Haiku|Flash|Luna|Qwen|Grok.\n"
        "% ==================================================================\n")
    body = "\n".join(f"\\newcommand{{\\{n}}}{{{v}}}" for n, v in items)
    (TABLES / "panel_numbers.tex").write_text(header + body + "\n", encoding="utf-8")
    (TABLES / "panel_table_grid.tex").write_text(table_grid(stats), encoding="utf-8")
    (TABLES / "panel_table_controls.tex").write_text(table_controls(nohint, probe), encoding="utf-8")
    fig_risk_response(base, FIGURES / "panel_risk_response.pdf", rng)

    print("\n[ ĐÃ GHI ]")
    for q in (TABLES / "panel_numbers.tex", TABLES / "panel_table_grid.tex",
              TABLES / "panel_table_controls.tex", FIGURES / "panel_risk_response.pdf"):
        print(f"  {q.relative_to(REPO).as_posix():52s} {q.stat().st_size:>8,} B")
    print(f"  ({len(items)} macro)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
