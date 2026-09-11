#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""E3a — khoảng cách tới best response, khi đối thủ được BIẾT TRƯỚC.

Chạy:  python paper/AAMAS/analysis/e3a_analysis.py

ĐỌC THẲNG từ `results/exp_bestresponse_{defect,carry,coop,cond}/` và không đọc gì khác.
Không chạm `Legacy_Results/` (kho đóng băng, trải nhiều panel/prompt khác nhau — trộn vào
bảng của panel mới là lỗi âm thầm). Không ghi bất cứ thứ gì vào `results/`.

SINH RA
    paper/AAMAS/tables/e3a_numbers.tex            <- CHỈ \newcommand, input được ở preamble
    paper/AAMAS/tables/e3a_table_contributions.tex
    paper/AAMAS/tables/e3a_table_brgap.tex
    paper/AAMAS/tables/e3a_table_target.tex
    paper/AAMAS/figures/e3a_rounds_dominated.pdf
    paper/AAMAS/figures/e3a_gap_by_risk.pdf

VÌ SAO TÁCH MACRO KHỎI BẢNG
    Plan §14 bắt mọi con số trong text phải sinh bằng script. Nên `e3a_numbers.tex` chỉ
    chứa `\newcommand` — `\input` được ngay trong preamble mà không rơi một cái `table`
    nổi vào giữa trang. Ba file bảng là file riêng, và chúng **gọi lại chính các macro
    đó**, nên bảng với text không bao giờ lệch nhau: sửa data → chạy lại → cả hai đổi.

VÌ SAO CÓ HẲN MỘT BƯỚC REPLAY ĐỐI THỦ (`_simulate_opponents`)
    Toàn bộ bài này đứng trên một mệnh đề: "đối thủ tất định nên best response tính được".
    Mệnh đề đó chỉ đúng nếu chính sách tôi giả định TRÙNG với chính sách đã thực sự chơi.
    Nên trước khi tính bất cứ con số nào, script replay 5 ghế scripted của **cả 1000 ván**
    từ nước đi của ghế LLM và so từng vòng với data. Lệch một ô là dừng, vì lúc đó mọi
    "khoảng cách tới best response" ở dưới đều vô nghĩa. Đây là bẫy đắt nhất của mục này.

CẢNH BÁO ĐÃ ĐO ĐƯỢC: `cond` SUY BIẾN THÀNH `coop`
    Quét vét cạn cả 3^10 = 59.049 quỹ đạo khả dĩ của ghế LLM: **không có quỹ đạo nào** làm
    một ghế conditional_cooperator chơi khác 2. Lý do là số học chứ không phải ngẫu nhiên —
    một ghế CC lấy trung bình 5 ghế còn lại, trong đó 4 ghế là CC đang ở 2 và 1 ghế là LLM
    chơi c ∈ {0,2,4}, nên trung bình chỉ nhận (8+c)/5 ∈ {1.6, 2.0, 2.4}; cả ba đều làm tròn
    về 2 (hoà thì giữ mức THẤP). Một ghế đơn độc không đủ đòn bẩy để kéo trung bình nhóm
    qua ngưỡng làm tròn. Hệ quả: `cond` có ma trận payoff **y hệt** `coop`, và việc hai cột
    đó ra gần như cùng số KHÔNG phải trùng hợp — nó là tất yếu của thiết kế. Đừng viết
    trong paper rằng đó là hai điều kiện độc lập.
"""
from __future__ import annotations

import ast
import decimal
import functools
import itertools
import pathlib
import sys
from typing import Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# --------------------------------------------------------------------------------------
# Hằng số luật chơi. Lấy y theo Milinski 2008 / crg_task_server.py — KHÔNG đọc từ cột
# `contribution_options` của CSV: cột đó ghi tập nước đi QUAN SÁT ĐƯỢC trong ván ("[0, 2]"
# khi không ai chơi 4), không phải tập luật. Dùng nó làm config là sai ngay từ dòng đầu.
# --------------------------------------------------------------------------------------
OPTIONS: Tuple[int, ...] = (0, 2, 4)
N_PLAYERS = 6
N_ROUNDS = 10
ENDOWMENT = 40.0
TARGET = 120.0
FAIR_SHARE = TARGET / (N_PLAYERS * N_ROUNDS)          # = 2.0, đúng {fairShare} trong prompt

# Console Windows mac dinh cp1252, khong in noi tieng Viet co dau -> ep UTF-8. Phai dat
# TRUOC moi lenh print, neu khong script chet giua chung sau khi da ghi mot phan file.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO = pathlib.Path(__file__).resolve().parents[3]
RESULTS = REPO / "results"
TABLES = REPO / "paper" / "AAMAS" / "tables"
FIGURES = REPO / "paper" / "AAMAS" / "figures"

PROFILES: Tuple[str, ...] = ("defect", "carry", "coop", "cond")
RISKS: Tuple[float, ...] = (0.1, 0.3, 0.5, 0.7, 0.9)
EXPECTED_REPS = 10

# model_tag (tên thư mục) -> nhãn ngắn dùng trong bảng/hình, và tên CamelCase cho macro.
MODELS: Dict[str, Tuple[str, str]] = {
    "anthropic-claude-haiku-4-5-20251001": ("Haiku 4.5", "Haiku"),
    "google-gemini-3.5-flash-lite":        ("Flash-Lite 3.5", "Flash"),
    "openai-gpt-5.6-luna":                 ("GPT-5.6 Luna", "Luna"),
    "qwen-qwen3-235b-a22b-instruct-2507":  ("Qwen3-235B", "Qwen"),
    "xai-grok-4.20-0309-non-reasoning":    ("Grok-4.20 NR", "Grok"),
}
MODEL_ORDER = list(MODELS)

# Chính sách scripted mà mỗi profile PHẢI có ở 5 ghế còn lại. Dùng để chốt lại rằng thư
# mục `exp_bestresponse_<prof>` đúng là profile nó tự xưng (cột `opponent_profile` trong
# wide CSV đang rỗng ở lô này, nên tên thư mục là thứ duy nhất còn mang thông tin đó).
PROFILE_POLICY: Dict[str, str] = {
    "defect": "scripted:always_0",
    "carry":  "scripted:always_4",
    "coop":   "scripted:always_2",
    "cond":   "scripted:conditional_cooperator",
}

PROFILE_LABEL: Dict[str, str] = {
    "defect": "All-defect",
    "carry":  "All-contribute",
    "coop":   "Fair-share",
    "cond":   "Cond.\\ coop.",
}
# Hai profile ma best response = 0 o MOI p. Keo theo hai he qua BAT BUOC phai noi ra
# chu dung de nguoi doc tu phat hien: (a) cot `Gap` cua bang 2 BANG DUNG cot `Mean`
# cua bang 1, vi khoang cach toi 0 chinh la tong dong gop; (b) rieng `carry` thi
# `Forfeited` = `Gap` tung xu (moi don vi dong la mat trang chac chan). Hai cot trong
# nhu hai phep do doc lap cung xac nhan mot ket luan, trong khi chung la MOT con so in
# hai lan. Cot `Share` (= Gap/40) da bo han vi ly do do; hai cot con lai khong bo duoc
# nen danh dau bang dagger NGAY TRONG BANG, khong chi trong caption.
TIED_COLUMN_PROFILES: Tuple[str, ...] = ("defect", "carry")

PROFILE_MACRO: Dict[str, str] = {
    "defect": "Defect", "carry": "Carry", "coop": "Coop", "cond": "Cond",
}
# Tên macro LaTeX phải TOÀN CHỮ CÁI (\Ethreea0.1 không tồn tại), nên mức risk cũng phải
# đánh vần ra chữ.
RISK_WORD: Dict[float, str] = {
    0.1: "Pone", 0.3: "Pthree", 0.5: "Pfive", 0.7: "Pseven", 0.9: "Pnine",
}

# Vòng đầu tiên mà lịch sử in trong prompt ĐỦ để suy ra một chính sách hằng số: tới lúc
# này người chơi đã thấy 5 vòng liên tiếp trong đó năm ghế kia cho ra cùng một bộ số. Xem
# khối "tách vòng 1 khỏi vòng 6-10" trong main() để biết vì sao phải tách.
INFER_ROUND = 6

# Hệ số ngại rủi ro CRRA đem ra thử. 0 = trung tính rủi ro (giả định ngầm của mọi con số
# "tiền bỏ lại trên bàn"); 0.5 và 0.9 nằm trong khoảng ước lượng cho người thật.
CRRA_GAMMAS: Tuple[float, ...] = (0.0, 0.5, 0.9)
GAMMA_WORD: Dict[float, str] = {0.0: "GammaZero", 0.5: "GammaHalf", 0.9: "GammaNine"}

BOOT_SEED = 20260911          # cố định -> chạy lại ra đúng cùng CI
BOOT_N = 10_000
PERM_SEED = 20260912
PERM_N = 10_000


# ======================================================================================
# 1. Mô hình đối thủ — bản sao 1:1 của crg_task_server.scripted_decide
# ======================================================================================
def nearest_option(value: float) -> int:
    """Làm tròn về nước đi hợp lệ gần nhất; HOÀ thì giữ mức THẤP.

    Quy tắc "hoà giữ mức thấp" nghe như tiểu tiết nhưng nó chính là thứ làm `cond` suy
    biến: 2.4 hoà không được nên vẫn về 2, còn nếu hoà mà làm tròn lên thì 2.4 -> 2 vẫn
    thế, nhưng 3.0 (hoà) sẽ thành 4 và conditional cooperator sẽ leo thang. Giữ đúng bản
    gốc, đừng "cải tiến".
    """
    best = OPTIONS[0]
    best_d = abs(float(value) - best)
    for opt in OPTIONS[1:]:
        d = abs(float(value) - opt)
        if d < best_d - 1e-9:                      # strict -> hoà giữ lại mức thấp
            best, best_d = opt, d
    return best


def _simulate_opponents(profile: str, llm_moves: Sequence[int]) -> List[List[int]]:
    """Replay 10 vòng: ghế 0 chơi đúng `llm_moves`, 5 ghế còn lại chạy chính sách scripted.

    Trả về lịch sử đầy đủ [[c_ghe0..c_ghe5] x 10] để so byte-với-byte với data.
    """
    history: List[List[int]] = []
    for own in llm_moves:
        if profile == "defect":
            others = [0] * 5
        elif profile == "carry":
            others = [4] * 5
        elif profile == "coop":
            others = [2] * 5
        elif profile == "cond":
            if not history:
                others = [nearest_option(FAIR_SHARE)] * 5      # vòng 1: đóng phần mình
            else:
                last = history[-1]
                # Mỗi ghế CC nhìn trung bình của 5 ghế KHÁC nó (kể cả ghế LLM).
                others = [nearest_option(sum(last[i] for i in range(N_PLAYERS) if i != seat) / 5.0)
                          for seat in range(1, N_PLAYERS)]
        else:
            raise ValueError(f"profile lạ: {profile!r}")
        history.append([int(own)] + [int(o) for o in others])
    return history


# ======================================================================================
# 2. Best response — tính vét cạn, không suy luận bằng tay
# ======================================================================================
def expected_value(llm_total: float, group_total: float, risk: float) -> float:
    """EV của ghế LLM: giữ phần chưa đóng, nhân xác suất sống sót nếu trượt target.

    Tiền đã đóng KHÔNG hoàn lại, và xổ số là CẤP NHÓM, xổ đúng một lần ở cuối — nên EV
    chỉ phụ thuộc (tổng đóng của mình, tổng đóng của nhóm), không phụ thuộc phân bố theo
    vòng. Đó là lý do dưới đây gộp được 3^10 quỹ đạo về vài chục cặp số.
    """
    keep = ENDOWMENT - float(llm_total)
    if group_total >= TARGET:
        return keep
    return keep * (1.0 - float(risk))


@functools.lru_cache(maxsize=None)
def _reachable_outcomes(profile: str) -> Tuple[Tuple[int, float], ...]:
    """Mọi cặp (tổng đóng của LLM, tổng đóng của nhóm) mà ghế LLM có thể ép xảy ra.

    `defect/carry/coop` có dạng đóng: nhóm = tổng của LLM + hằng số (0 / 200 / 100).
    `cond` thì đối thủ phản ứng, nên quét VÉT CẠN cả 3^10 = 59.049 quỹ đạo. Đắt 2 giây,
    nhưng đây là chỗ duy nhất trong bài mà "best response" có thể sai vì suy luận tay, nên
    cứ để máy đếm. (Kết quả: cond cho ra đúng cùng tập cặp số như coop — xem docstring
    đầu file.)
    """
    if profile in ("defect", "carry", "coop"):
        base = {"defect": 0.0, "carry": 200.0, "coop": 100.0}[profile]
        return tuple((t, t + base) for t in range(0, int(N_ROUNDS * max(OPTIONS)) + 1, 2))

    seen = set()
    for seq in itertools.product(OPTIONS, repeat=N_ROUNDS):
        hist = _simulate_opponents("cond", seq)
        seen.add((sum(seq), float(sum(sum(r) for r in hist))))
    return tuple(sorted(seen))


def best_response(profile: str, risk: float) -> Tuple[List[int], float]:
    """(tập tổng đóng góp tối ưu, EV tối ưu) cho ghế LLM.

    Trả về cả TẬP chứ không phải một số, vì ở `coop`/`cond` tại p = 0.5 có đúng hai đáp án
    tối ưu — đóng 0 (EV = 40 x 0.5 = 20) và đóng 20 (chắc chắn giữ 20) bằng điểm nhau. Ép
    nó thành một số rồi đo khoảng cách sẽ báo model chơi ĐÚNG best response là "lệch 20".
    """
    outcomes = _reachable_outcomes(profile)
    evs = np.array([expected_value(t, g, risk) for t, g in outcomes])
    top = float(evs.max())
    totals = sorted({outcomes[i][0] for i in np.flatnonzero(np.abs(evs - top) < 1e-9)})
    return totals, top


@functools.lru_cache(maxsize=None)
def br_tie_risks(profile: str) -> Tuple[float, ...]:
    """Mọi p trong (0,1) mà TẬP best response có NHIỀU HƠN một đáp án. Giải, không quét.

    VÌ SAO KHÔNG QUÉT LƯỚI. Hình vẽ trước đây dò điểm hoà bằng cách chấm
    `linspace(0.05, 0.95, 451)` rồi xem mẫu nào cho ra tập nhiều phần tử. Điểm hoà là MỘT
    điểm trên trục thực, nên chuyện lưới có chạm nó hay không là may rủi: 451 mẫu tình cờ
    rơi vào 0.4999999999999999 và lọt qua nhờ dung sai 1e-9 trong `best_response`, còn 450
    mẫu thì trượt — và cả chú thích p* biến mất khỏi hình mà không báo lỗi. Hàm này trả về
    nghiệm đúng, nên độ mịn của lưới vẽ không quyết định được nội dung hình nữa.

    CÁCH TÍNH. Với mỗi kết cục (t, g) khả dĩ, EV là hàm BẬC NHẤT theo p:
    g >= TARGET  ->  EV = keep            (hệ số góc 0, xổ số không xảy ra)
    g <  TARGET  ->  EV = keep - keep*p   (hệ số góc -keep)
    với keep = ENDOWMENT - t. Hai đường thẳng cắt nhau tại đúng một p, giải thẳng ra; rồi
    giữ lại những p mà tại đó tập tối ưu thật sự có từ hai phần tử (hai đường bất kỳ cắt
    nhau không có nghĩa chúng đang cùng ở ĐỈNH).
    """
    lines = []
    for t, g in _reachable_outcomes(profile):
        keep = ENDOWMENT - float(t)
        lines.append((keep, 0.0) if g >= TARGET else (keep, -keep))

    cands: List[float] = []
    for (a1, b1), (a2, b2) in itertools.combinations(lines, 2):
        if abs(b1 - b2) < 1e-12:                 # song song: không bao giờ cắt
            continue
        p = (a2 - a1) / (b1 - b2)
        if not (1e-9 < p < 1.0 - 1e-9):          # nghiệm ngoài khoảng chơi được
            continue
        if len(best_response(profile, p)[0]) > 1:
            cands.append(p)

    out: List[float] = []
    for p in sorted(cands):                      # gộp nghiệm trùng nhau tới sai số máy
        if not out or abs(p - out[-1]) > 1e-9:
            out.append(p)
    return tuple(out)



# ======================================================================================
# 2b. Best response khi agent KHÔNG trung tính rủi ro — phép thử độ nhạy theo CRRA
#
# VÌ SAO PHẢI CÓ. Mọi con số "tiền bỏ lại trên bàn" ở trên đo bằng EV, tức là ngầm đặt hệ
# số ngại rủi ro bằng 0. Ở `coop`/`cond` lựa chọn thật sự là "chắc chắn 20" so với "xổ số
# trị giá (1-p)*40", nên CHÍNH giả định đó quyết định kết quả — reviewer tự tính lại được
# trong ba dòng và sẽ hỏi. Rẻ hơn nhiều nếu ta tự tính trước rồi in ra.
#
# Dùng CRRA u(x) = x^(1-γ)/(1-γ) vì đó là dạng chuẩn trong kinh tế thực nghiệm, và vì với
# γ < 1 thì u(0) = 0 — "mất sạch" vẫn hữu hạn, nên bài toán còn có nghiệm nội. KHÔNG thử
# γ >= 1 (log, luỹ thừa âm): ở đó u(0) = -∞ nên mọi phương án có rủi ro mất trắng đều bị
# loại vô điều kiện, kết quả suy biến thành "luôn mua chắc chắn" và không còn là phép thử
# độ nhạy nữa mà là một định nghĩa.
#
# ĐIỀU ĐÁNG NÓI NHẤT lại là thứ KHÔNG đổi: ở `defect`/`carry` nhóm hoặc luôn trượt target
# hoặc luôn đạt, nên hai phương án so với nhau là hai đại lượng CHẮC CHẮN (40-t so với 40,
# nhân cùng một thừa số (1-p) ở `defect`). Giữ tiền lại thắng dưới MỌI hàm lợi ích tăng,
# nên γ không đụng được vào tập đó. Đó chính là lý do hai profile ấy làm xương sống.
# ======================================================================================
def crra_utility(wealth: float, gamma: float) -> float:
    """u(x) = x^(1-γ)/(1-γ), với u(0) = 0. Chỉ định nghĩa cho γ < 1 (xem lý do ở trên)."""
    if gamma >= 1.0:
        raise ValueError(f"CRRA γ phải < 1 (u(0) sẽ là -∞ nếu γ >= 1): {gamma}")
    x = max(float(wealth), 0.0)
    return x ** (1.0 - gamma) / (1.0 - gamma)


def expected_utility(llm_total: float, group_total: float,
                     risk: float, gamma: float) -> float:
    """Lợi ích kỳ vọng của ghế LLM dưới CRRA hệ số γ.

    Vì u(0) = 0 nên nhánh "mất sạch" đóng góp đúng 0 vào kỳ vọng, và cả biểu thức rút gọn
    còn u(keep)*(1-p). Viết gọn như vậy để thấy ngay chỗ γ VÔ HẠI: ở `defect` nhóm luôn
    trượt target nên thừa số (1-p) là CHUNG cho mọi lựa chọn, không xếp lại được thứ tự.
    """
    val = crra_utility(ENDOWMENT - float(llm_total), gamma)
    if group_total >= TARGET:
        return val
    return val * (1.0 - float(risk))


def best_response_crra(profile: str, risk: float, gamma: float) -> List[int]:
    """Tập tổng đóng góp tối ưu dưới CRRA γ. Trả về TẬP, vì tại p* có hai đáp án hoà."""
    outcomes = _reachable_outcomes(profile)
    eus = np.array([expected_utility(t, g, risk, gamma) for t, g in outcomes])
    top = float(eus.max())
    return sorted({outcomes[i][0] for i in np.flatnonzero(np.abs(eus - top) < 1e-12)})


def crra_pstar(profile: str, gamma: float, grid: int = 10_001) -> float:
    """p nhỏ nhất mà "mua chắc chắn" (đóng > 0) lọt vào tập tối ưu.

    Quét lưới chứ không giải tay. Công thức đóng p* = 1 - 0.5^(1-γ) chỉ đúng nhờ hai sự
    trùng hợp của bàn này (tập tối ưu chỉ có thể là {0} hoặc {20}, và u(0) = 0); quét thì
    vẫn đúng nếu ai đó đổi target hay số vòng. Rẻ: outcomes đã cache, 10k lần đánh giá.
    """
    for p in np.linspace(0.0, 1.0, grid):
        if max(best_response_crra(profile, float(p), gamma)) > 0:
            return float(p)
    return float("nan")


# ======================================================================================
# 3. Nạp data
# ======================================================================================
def load_e3a() -> pd.DataFrame:
    """Một dòng = một ván. Thiếu ô thì NỔ, không im lặng điền 0."""
    rows = []
    for profile in PROFILES:
        exp_dir = RESULTS / f"exp_bestresponse_{profile}"
        if not exp_dir.is_dir():
            raise FileNotFoundError(f"thiếu hẳn thí nghiệm: {exp_dir}")
        for risk_dir in sorted(exp_dir.iterdir(), key=lambda q: float(q.name)):
            risk = float(risk_dir.name)
            for csv in sorted(risk_dir.glob("*/*.csv")):
                model_tag = csv.parent.name
                if model_tag not in MODELS:
                    raise ValueError(f"model ngoài panel 5 model: {model_tag} ({csv})")
                df = pd.read_csv(csv)
                df["profile"] = profile
                df["risk"] = risk
                df["model_tag"] = model_tag
                rows.append(df)
    data = pd.concat(rows, ignore_index=True)

    # --- cổng: không ván nào được có lượt parse hỏng ---
    bad = int(data["n_parse_failures"].sum())
    if bad:
        raise ValueError(f"{bad} lượt parse hỏng trong E3a — data chưa qua QA, dừng")

    data["llm_moves"] = data["agent1_strategies"].map(ast.literal_eval)
    data["llm_total"] = data["llm_moves"].map(sum).astype(float)
    data["round1"] = data["llm_moves"].map(lambda v: v[0]).astype(float)

    # --- cổng: ghế 1 phải là ghế LLM, 5 ghế còn lại đúng chính sách của profile ---
    for _, row in data.iterrows():
        if row["agent1_llm"] != row["model_tag"]:
            raise ValueError(f"ghế 1 không phải model của thư mục: {row['game_id']}")
        want = PROFILE_POLICY[row["profile"]]
        got = [row[f"agent{i}_llm"] for i in range(2, 7)]
        if any(g != want for g in got):
            raise ValueError(f"ghế scripted sai chính sách ở {row['game_id']}: "
                             f"mong {want}, thấy {sorted(set(got))}")

    # --- cổng cân bằng: 4 profile x 5 model x 5 risk x 10 rep, không thiếu ô nào ---
    grid = data.groupby(["profile", "model_tag", "risk"]).size()
    expect = {(p, m, r) for p in PROFILES for m in MODELS for r in RISKS}
    missing = expect - set(grid.index)
    if missing:
        raise ValueError(f"THIẾU {len(missing)} ô (profile, model, risk): {sorted(missing)[:8]}")
    wrong = grid[grid != EXPECTED_REPS]
    if len(wrong):
        raise ValueError(f"ô sai số rep (mong {EXPECTED_REPS}):\n{wrong.to_string()}")

    data["model"] = data["model_tag"].map(lambda t: MODELS[t][0])
    data["mkey"] = data["model_tag"].map(lambda t: MODELS[t][1])
    return data


# ======================================================================================
# 4. Chấm điểm từng ván
# ======================================================================================
def score(data: pd.DataFrame) -> pd.DataFrame:
    """Thêm cột: EV thực, EV nếu chơi best response, và hai kiểu khoảng cách."""
    # Replay đối thủ trên TOÀN BỘ data trước khi tính gì cả (xem docstring đầu file).
    for _, row in data.iterrows():
        got = _simulate_opponents(row["profile"], row["llm_moves"])
        want = [list(t) for t in
                zip(*[ast.literal_eval(row[f"agent{i}_strategies"]) for i in range(1, 7)])]
        if got != want:
            raise ValueError(
                "mô hình đối thủ KHÔNG khớp data đã chạy — mọi con số best response bên "
                f"dưới sẽ sai.\nván {row['game_id']}\n  replay {got}\n  data   {want}")

    br_total, br_ev, ev_act, gap_c, gap_m = [], [], [], [], []
    for _, row in data.iterrows():
        totals, top = best_response(row["profile"], row["risk"])
        g = float(row["group_total"])
        # chốt lại tổng nhóm trong file khớp mô hình (cond đã chứng minh = 100 + của LLM)
        base = {"defect": 0.0, "carry": 200.0, "coop": 100.0, "cond": 100.0}[row["profile"]]
        if abs(g - (row["llm_total"] + base)) > 1e-9:
            raise ValueError(f"group_total lệch mô hình ở {row['game_id']}: {g}")
        ev = expected_value(row["llm_total"], g, row["risk"])
        br_total.append(min(totals))
        br_ev.append(top)
        ev_act.append(ev)
        # Khoảng cách tính tới TẬP best response (xem best_response): model chơi đúng một
        # trong hai đáp án tối ưu ở p = 0.5 phải được chấm là lệch 0, khớp với loss = 0.
        gap_c.append(min(abs(row["llm_total"] - t) for t in totals))
        gap_m.append(top - ev)

    out = data.copy()
    out["br_total"] = br_total
    out["br_ev"] = br_ev
    out["ev"] = ev_act
    out["gap_contrib"] = gap_c
    out["money_lost"] = np.round(gap_m, 10)
    if (out["money_lost"] < -1e-9).any():
        raise ValueError("EV thực > EV best response — mô hình best response sai")
    out["money_lost"] = out["money_lost"].clip(lower=0.0)
    # Phần EV bỏ lại trên bàn, chuẩn hoá: 0 <= loss <= br_ev nên tỉ lệ luôn trong [0,1].
    # Cần chuẩn hoá vì br_ev ở `defect` tụt từ 36 (p=0.1) xuống 4 (p=0.9) — mất 4 đồng ở
    # hai đầu đó không phải cùng một mức độ dại.
    out["frac_lost"] = out["money_lost"] / out["br_ev"]
    out["is_br"] = (out["money_lost"] <= 1e-9).astype(int)
    return out


def boot_ci(values: np.ndarray, seed: int) -> Tuple[float, float]:
    """CI 95% percentile bootstrap cho trung bình. Seed cố định -> chạy lại ra đúng số cũ."""
    v = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(v), size=(BOOT_N, len(v)))
    means = v[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def perm_slope_p(risk: np.ndarray, value: np.ndarray, seed: int) -> Tuple[float, float]:
    """(hệ số góc OLS của đóng góp theo p, p-value hoán vị hai phía).

    Dùng hoán vị chứ không dùng t-test: 10 ván/ô, đóng góp rời rạc và hay dính cụm (flash
    đóng y hệt nhau cả 50 ván), nên giả định chuẩn của t-test không có cửa đúng.
    """
    r = np.asarray(risk, float)
    v = np.asarray(value, float)
    if np.allclose(v, v[0]):
        return 0.0, 1.0                    # hằng số -> không có gì để kiểm định
    slope = float(np.polyfit(r, v, 1)[0])
    rng = np.random.default_rng(seed)
    null = np.empty(PERM_N)
    for i in range(PERM_N):
        null[i] = np.polyfit(r, rng.permutation(v), 1)[0]
    pval = float((np.sum(np.abs(null) >= abs(slope) - 1e-12) + 1) / (PERM_N + 1))
    return slope, pval


# ======================================================================================
# 5. Xuất macro LaTeX
# ======================================================================================
class Macros:
    """Gom `\newcommand` lại; chặn định nghĩa trùng tên (LaTeX sẽ nuốt im lặng cái sau)."""

    def __init__(self) -> None:
        self._items: List[Tuple[str, str]] = []
        self._seen: Dict[str, str] = {}

    def add(self, name: str, value: str) -> None:
        full = "Ethreea" + name
        if not full.isalpha():
            raise ValueError(f"tên macro phải toàn CHỮ CÁI (LaTeX không nhận số): {full}")
        if full in self._seen and self._seen[full] != value:
            raise ValueError(f"macro {full} bị định nghĩa hai lần khác giá trị")
        if full not in self._seen:
            self._seen[full] = value
            self._items.append((full, value))

    def num(self, name: str, value: float, nd: int = 2) -> None:
        """In `value` với đúng `nd` chữ số thập phân, làm tròn NỬA RA XA SỐ 0.

        VÌ SAO KHÔNG DÙNG THẲNG f"{value:.0f}". Python làm tròn nửa-chẵn (banker's): 17,5
        ra "18" nhưng 48,5 ra "48". Cùng một script, cùng một đại lượng phần trăm, hai
        hướng làm tròn khác nhau — và cái đi xuống trông y như lỗi cắt cụt. Đã đo trên lô
        này: `IsBRAllHaiku` = 17,5 và `RoundOneShareTwoGrok` = 48,5 rơi đúng vào hai nhánh
        đó. Nửa-ra-xa-0 là quy ước người đọc bảng mặc định giả sử, nên dùng nó.

        Đi kèm quy tắc chị em, đã trả giá ở `QwenCoopShort`: ĐỪNG BAO GIỜ viết `int(x)` để
        rút một đại lượng đo được về số nguyên — `int()` cắt cụt (1,88 -> 1), không làm
        tròn. `int()` chỉ dành cho thứ vốn đã là số nguyên: số đếm ván, hằng số luật chơi.
        """
        q = decimal.Decimal(repr(float(value))).quantize(
            decimal.Decimal(1).scaleb(-nd), rounding=decimal.ROUND_HALF_UP)
        if q == 0:                      # chặn "-0.0" lọt vào bảng
            q = abs(q)
        self.add(name, f"{q:f}")

    def render(self) -> str:
        return "\n".join(f"\\newcommand{{\\{n}}}{{{v}}}" for n, v in self._items)


def fmt(x: float, nd: int = 2) -> str:
    return f"{x:.{nd}f}"


# ======================================================================================
# 6. Hình
# ======================================================================================
# BỀ NGANG — CHỐT CHUNG CHO CẢ HAI HÌNH, ĐỪNG ĐỔI RIÊNG MỘT CÁI.
#
# `\columnwidth` của acmart sigconf là 241.15pt đo bằng **TeX pt** (1/72,27 inch), còn PDF
# và matplotlib đo bằng **PostScript pt** (1/72 inch). Cùng một bề ngang VẬT LÝ ra hai con
# số: 241.15 TeX pt = 3.33675 in = 240.25 PS pt. Nên mở file bằng PyMuPDF sẽ thấy 240.25
# chứ không phải 241.15 — đúng rồi, ĐỪNG "sửa" thành 241.15 PS pt: làm thế hình rộng hơn
# cột thật 0,37% và `\includegraphics[width=\columnwidth]` sẽ thu nhỏ nó lại.
#
# VÌ SAO PHẢI ĐÚNG BỀ NGANG CỘT. Để `width=\columnwidth` là phép nhân 1.0, tức cỡ chữ
# 7,2pt chọn ở đây in ra đúng 7,2pt. Hai bản trước rộng 234,54pt và 203,99pt nên bị phóng
# 1,029x và 1,182x: cùng khai 7,2pt mà in ra 7,4pt và 8,5pt — hai hình cạnh nhau trong
# cùng một mục lệch cỡ chữ nhau, thứ ai cũng thấy mà không ai chỉ ra được tại sao.
COLUMN_PT_TEX = 241.14749
COLUMN_IN = COLUMN_PT_TEX / 72.27          # 3.33675 in = 240.25 PS pt

# Bề dày dải xám "best response", dùng CHUNG cho cả hai hình nên chúng đọc giống nhau.
# Phải dày hơn hẳn nét model dày nhất (1,70 — xem _series_style) vì chỗ đáng xem nhất lại
# đúng là chỗ model nằm ĐÈ lên mốc: ở fair-share phía trên p*, Flash-Lite và Luna nằm ĐÚNG
# 20 còn Haiku ngay sát trên, cộng marker rỗng và error bar thì một dải 4,0pt bị cụm đó
# nuốt gần hết. Soi bản phóng 1400dpi: ở 4,8pt phần xám giữa các marker vẫn thấy rõ, tức
# vẫn đọc được rằng họ đang nằm TRÊN mốc chứ không phải mốc biến mất.
BR_LW = 4.8

# Okabe–Ito: an toàn cho mọi dạng mù màu phổ biến. Kèm marker + kiểu nét khác nhau để
# hình vẫn đọc được khi in đen trắng, chứ không chỉ dựa vào màu.
MODEL_STYLE: Dict[str, Tuple[str, str, str]] = {
    "Haiku": ("#E69F00", "o", "-"),
    "Flash": ("#56B4E9", "s", "--"),
    "Luna":  ("#009E73", "^", "-."),
    "Qwen":  ("#CC79A7", "D", ":"),
    "Grok":  ("#0072B2", "v", (0, (3, 1, 1, 1, 1, 1))),
}


def _rc() -> None:
    plt.rcParams.update({
        # fonttype 42 = TrueType nhúng hẳn vào PDF. ACM từ chối bản PDF có font không
        # nhúng; mặc định Type 3 của matplotlib là thứ hay bị trả về nhất.
        "pdf.fonttype": 42, "ps.fonttype": 42,
        "font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans"],
        "font.size": 7.2, "axes.labelsize": 7.6, "axes.titlesize": 7.8,
        "xtick.labelsize": 6.8, "ytick.labelsize": 6.8, "legend.fontsize": 6.8,
        "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "lines.linewidth": 1.1, "lines.markersize": 3.2,
        # KHÔNG dùng bbox="tight" nữa: nó cắt trang theo nội dung nên bề ngang file không
        # còn là figsize — mà bề ngang mới đúng là thứ phải chốt (xem COLUMN_IN). Lề tự
        # chừa bằng subplots_adjust, và _save_exact() canh chừng phần bị cắt cụt.
        "savefig.bbox": "standard", "savefig.pad_inches": 0.0,
    })


def _series_style(i: int) -> Tuple[float, float, int]:
    """(bề dày nét, cỡ marker, zorder) cho series thứ `i` — LỒNG NHAU dần theo i.

    VẤN ĐỀ CÓ THẬT: nhiều model chơi ĐÚNG CÙNG MỘT SỐ. Ở `fair-share`, Flash-Lite và Luna
    cùng đóng đúng 20.00 ở bốn trong năm mức risk, và ở vòng 1 thì bốn model cùng đóng
    đúng 2.00. Vẽ thẳng thì cái sau che kín cái trước và người đọc đếm thiếu một model.

    VÌ SAO KHÔNG CÒN DODGE. Bản trước lệch mỗi series 0,014 đơn vị p. Đo trên PDF thật:
    trục x chạy ~100pt mỗi đơn vị p, nên 0,014 = 1,4pt trong khi marker rộng 3,2pt — hai
    marker cạnh nhau vẫn chồng ~60%, tức dodge KHÔNG tách được gì mà vẫn in marker ở toạ
    độ x SAI. Và không cứu được bằng cách dodge to hơn: tách 5 series với marker 3,2pt cần
    trải 14,8pt, trong khi hai mức risk chỉ cách nhau ~20pt — người đọc sẽ gán marker nhầm
    mức risk, lỗi nặng hơn hẳn lỗi chồng nhau. Nên bỏ hẳn dodge: mọi marker nằm ĐÚNG toạ
    độ x của nó.

    THAY BẰNG LỒNG NHAU. Series vẽ trước dày hơn / marker to hơn và nằm dưới; series sau
    mảnh hơn / nhỏ hơn và nằm trên. Hai series trùng khít nhau thì cái sau nằm LỌT TRONG
    cái trước, cả hai cùng nhìn thấy — thay vì cái sau xoá cái trước. Marker vẽ RỖNG
    (`mfc="none"`) nên ngay cả khi hai hình marker cắt nhau cũng không cái nào bị lấp.
    Cách này giữ nguyên dữ liệu (không dời điểm đi đâu cả) và tự đúng với BẤT KỲ bộ số
    nào, chứ không phải mẹo chỉnh tay vừa khít lô data hôm nay.
    """
    return 1.70 - 0.24 * i, 4.40 - 0.50 * i, 3 + i


def _save_exact(fig, path: pathlib.Path) -> None:
    """Ghi PDF ở ĐÚNG figsize, và NỔ nếu có mực tràn ra ngoài khung trang.

    Bỏ `bbox="tight"` là điều kiện để chốt được bề ngang (xem COLUMN_IN), nhưng đổi lại
    thì lề phải tự chừa — chừa thiếu thì nhãn bị CẮT CỤT lặng lẽ, đúng loại lỗi chỉ lộ ra
    khi đã in. Nên so khung bao mọi thứ đã vẽ (kể cả legend, supxlabel, supylabel) với
    khung trang; lệch quá 0,3pt là dừng thay vì ship một hình cụt chữ.
    """
    fig.canvas.draw()
    tb = fig.get_tightbbox(fig.canvas.get_renderer())      # inch, gốc ở góc dưới-trái
    w, h = fig.get_size_inches()
    tol = 0.3 / 72.0
    over = {"trái": -tb.x0, "phải": tb.x1 - w, "dưới": -tb.y0, "trên": tb.y1 - h}
    bad = {k: v * 72.0 for k, v in over.items() if v > tol}
    if bad:
        raise ValueError(
            f"{path.name}: nội dung tràn ra ngoài trang "
            + ", ".join(f"{k} {v:.2f}pt" for k, v in bad.items())
            + " — nới lề trong subplots_adjust, đừng bật lại bbox='tight'")
    # CreationDate=None: bỏ hẳn dấu thời gian ra khỏi PDF. Không có nó thì chạy lại script
    # cho ra file KHÁC BYTE dù hình y hệt — nghĩa là mỗi lần chạy `git status` lại báo hai
    # file thay đổi, và không ai phân biệt được "vẽ lại y nguyên" với "hình đã đổi". Bỏ đi
    # thì so bằng `cmp` là đủ để biết hình có đổi thật hay không.
    fig.savefig(path, metadata={"CreationDate": None})


def fig_rounds(scored: pd.DataFrame, path: pathlib.Path) -> None:
    r"""Đóng góp trung bình THEO VÒNG, ở hai profile mà best response = 0 ở MỌI vòng.

    VÌ SAO LÀ HÌNH NÀY, CHỨ KHÔNG PHẢI HEATMAP CŨ. Bản trước vẽ hai lưới profile x model
    của `gap_contrib` và `money_lost`. Cả 40 ô của nó ĐÚNG BẰNG hai cột Gap/Forfeited của
    Bảng~\ref{tab:e3a-gap}, từng chữ số — một hình chỉ vẽ lại bảng, trong bài 8 trang là
    mất không 1/4 trang. Tệ hơn: nó GỘP qua 5 mức risk ở cả bốn hàng, trong khi hai hàng
    `fair-share`/`cond. coop.` có best response NHẢY từ 0 lên 20 tại p* = 0,5. Ô "8.00"
    của Flash-Lite ở đó là trung bình của {20, 20, 0, 0, 0} — con số KHÔNG xảy ra ở bất kỳ
    mức risk nào — mà lại trông y hệt ô "8.48" của Luna ở hàng `all-defect`, nơi 8.48 thật
    sự có nghĩa "lệch chừng ấy ở mọi mức risk". Hai thứ trái ngược, cùng một màu.

    HÌNH NÀY NÓI ĐƯỢC THỨ KHÔNG BẢNG NÀO NÓI. Mọi bảng của mục đều là TỔNG 10 vòng, nên
    hình dạng theo vòng biến mất khỏi chúng. Mà hình dạng ấy chính là chỗ phản biện nặng
    nhất nhắm vào: model không được CHO BIẾT đối thủ là script, nên "không best-respond"
    có thể chỉ là "chưa kịp biết". Vẽ theo vòng thì thấy ngay ai suy ra được và ai không —
    và thấy luôn hai model ĐI NGƯỢC, tăng đóng góp đúng những vòng mà lịch sử đã lặp lại
    năm lần cùng một bộ số. Đó là lập luận chứ không phải minh hoạ.

    CHỈ VẼ TẬP BỊ TRÓI CHẶT (`defect` + `carry`). Ở đó best response là "đóng 0 ở MỌI
    vòng", nên trục y đọc thẳng ra được: mọi thứ nằm trên vạch 0 là tiền vứt đi, không cần
    quy đổi và không phụ thuộc giả định ngại rủi ro. Ở `coop`/`cond` thì "đúng" phụ thuộc
    p, nên một đường trung bình theo vòng sẽ lại là trung bình của hai chế độ khác nhau —
    đúng cái lỗi vừa bỏ đi ở heatmap.
    """
    _rc()
    # Lấy đúng những profile mà best response là {0} ở MỌI mức risk — TÍNH ra chứ không
    # chép lại TIED_COLUMN_PROFILES. Hai danh sách hôm nay trùng nhau, nhưng hằng số kia
    # được đặt tên cho việc của Bảng 2 (hai cột trùng nhau); nếu một ngày nó đổi vì lý do
    # của bảng thì hình này sẽ lặng lẽ vẽ sai trục y — mà cả cách đọc hình ("mọi thứ trên
    # vạch 0 là tiền vứt đi") đứng trên đúng tính chất đang tính ở đây.
    profiles = tuple(pr for pr in PROFILES
                     if all(best_response(pr, p_)[0] == [0] for p_ in RISKS))
    if profiles != TIED_COLUMN_PROFILES:
        raise ValueError(f"tập 'best response = 0 ở mọi p' đổi rồi: {profiles} — xem lại "
                         f"cả TIED_COLUMN_PROFILES ({TIED_COLUMN_PROFILES}) lẫn caption")
    rounds = np.arange(1, N_ROUNDS + 1)
    fig, axes = plt.subplots(1, len(profiles), figsize=(COLUMN_IN, 1.80), sharey=True)

    for ax, prof in zip(np.atleast_1d(axes), profiles):
        # Vùng "đã suy ra được": từ vòng INFER_ROUND trở đi người chơi đã thấy
        # INFER_ROUND-1 vòng liên tiếp cho ra cùng một bộ năm con số. Tô nhạt để người đọc
        # thấy claim của mục đứng ở nửa nào của hình, thay vì phải tin caption.
        ax.axvspan(INFER_ROUND - 0.5, N_ROUNDS + 0.6, color="#f1f1f1", lw=0, zorder=0)
        # Mốc best response: 0 ở MỌI vòng, cả hai profile. Dày hơn hẳn nét model (BR_LW)
        # để ba model tụt hẳn về 0 ở cuối ván vẫn ló ra chứ không biến mất vào nó.
        ax.plot([0.4, N_ROUNDS + 0.6], [0.0, 0.0], color="#bdbdbd", lw=BR_LW,
                ls=(0, (4, 1.6)), zorder=1, solid_capstyle="butt")

        sel_prof = scored[scored.profile == prof]
        for mi, tag in enumerate(MODEL_ORDER):
            key = MODELS[tag][1]
            colour, marker, ls = MODEL_STYLE[key]
            lw, ms, zo = _series_style(mi)
            sel = sel_prof[sel_prof.model_tag == tag]
            if len(sel) != len(RISKS) * EXPECTED_REPS:
                raise ValueError(f"ô ({prof},{tag}) có {len(sel)} ván, không phải "
                                 f"{len(RISKS) * EXPECTED_REPS}")
            moves = np.array([list(v) for v in sel["llm_moves"]], dtype=float)
            ax.plot(rounds, moves.mean(axis=0), color=colour, marker=marker, ls=ls,
                    lw=lw, ms=ms, mfc="none", mew=0.85, zorder=zo)

        ax.set_title(PROFILE_LABEL[prof].replace("\\ ", " ").replace("\\", ""), pad=3)
        ax.set_xlim(0.4, N_ROUNDS + 0.6)
        ax.set_ylim(-0.30, 4.55)
        # Đúng ba nấc HỢP LỆ của trò chơi. Ghi cả ba để người đọc thấy ngay trục này là
        # "đóng bao nhiêu MỘT VÒNG" (chọn trong {0,2,4}), khác hẳn trục của hình kia.
        ax.set_yticks([0, 2, 4])
        ax.set_xticks(rounds)
        ax.tick_params(length=2)
        ax.grid(True, axis="y", lw=0.3, color="#e6e6e6", zorder=0)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)

    # Nhãn vùng tô: đặt MỘT lần, ở panel trái, bằng toạ độ dữ liệu để nó dính vào đúng mốc
    # INFER_ROUND dù có đổi mốc đó.
    np.atleast_1d(axes)[0].annotate(
        "policy inferable", xy=(INFER_ROUND - 0.35, 4.48), fontsize=5.8,
        color="#7a7a7a", va="top", ha="left", zorder=2)

    fig.supxlabel("round", fontsize=7.6, y=0.075)
    fig.supylabel("mean contribution per round\n(legal amounts $0$, $2$, $4$)",
                  fontsize=7.0, x=0.010, y=0.58)

    handles = [Line2D([], [], color=MODEL_STYLE[MODELS[t][1]][0],
                      marker=MODEL_STYLE[MODELS[t][1]][1],
                      ls=MODEL_STYLE[MODELS[t][1]][2], mfc="none", mew=0.85,
                      lw=_series_style(i)[0], ms=_series_style(i)[1],
                      label=MODELS[t][1])
               for i, t in enumerate(MODEL_ORDER)]
    handles.append(Line2D([], [], color="#bdbdbd", lw=BR_LW, ls=(0, (4, 1.6)),
                          label="best resp."))
    fig.legend(handles=handles, loc="lower center", ncol=6, frameon=False,
               bbox_to_anchor=(0.52, -0.016), handlelength=1.45, columnspacing=0.5,
               handletextpad=0.3)
    fig.subplots_adjust(left=0.150, right=0.995, top=0.865, bottom=0.245, wspace=0.10)
    _save_exact(fig, path)
    plt.close(fig)


def fig_by_risk(scored: pd.DataFrame, path: pathlib.Path) -> None:
    """4 panel, mỗi profile một panel: đóng góp của ghế LLM theo p, kèm mốc best response.

    Mốc best response vẽ dạng BẬC THANG xám dày phía dưới mọi đường model. Panel
    Fair-share/Cond. cooperation phải nhìn thấy cú nhảy tại p* = 0.5: dưới ngưỡng thì bỏ
    mặc (0) đáng giá hơn, trên ngưỡng thì mua chắc chắn (20). Tại đúng p* hai đáp án hoà
    nhau, nên chỗ đó vẽ đoạn nối dọc + ô rỗng để người đọc thấy là TẬP chứ không phải
    một điểm — chứ không lặng lẽ chọn một cái.

    BẬC THANG VẼ BẰNG ĐOẠN, KHÔNG BẰNG LẤY MẪU. Bản trước quét `linspace(0.05, 0.95, 451)`
    rồi dò xem mẫu nào cho ra TẬP nhiều hơn một đáp án. Nó chạy được là nhờ ăn may: 451
    mẫu tình cờ có một mẫu rơi đúng 0,5 (thật ra 0.4999999999999999, lọt qua nhờ sai số
    1e-9 trong `best_response`). Đổi 451 thành 450 là cả chú thích p* BIẾN MẤT, không một
    lời báo lỗi. Giờ p* lấy từ `br_tie_risks()` — nghiệm ĐÚNG của phương trình hoà EV —
    nên độ mịn của lưới vẽ không còn quyết định được nội dung nữa.
    """
    _rc()
    fig, axes = plt.subplots(2, 2, figsize=(COLUMN_IN, 3.06), sharex=True, sharey=True)
    pgrid = np.array(RISKS)
    # Chỉ vẽ trên ĐÚNG khoảng đã lấy mẫu [0.05, 0.95]. Không kéo tới p = 1.0: ở đúng
    # p = 1 trong profile All-defect thì trượt target là mất sạch bất kể đóng bao nhiêu,
    # nên MỌI mức đóng góp đều tối ưu (EV = 0) và "đường best response" bung ra thành cả
    # dải 0..40. Đó là suy biến ở biên, không phải phát hiện — vẽ nó ra chỉ tạo một vạch
    # dọc vô nghĩa chắn ngang panel.
    x_lo, x_hi = 0.05, 0.95

    for ax, prof in zip(axes.ravel(), PROFILES):
        # --- mốc best response, vẽ thành các đoạn ngang chính xác ---
        ties = [p for p in br_tie_risks(prof) if x_lo < p < x_hi]
        edges = [x_lo] + ties + [x_hi]
        for a, b in zip(edges[:-1], edges[1:]):
            # Giữa hai điểm hoà, tập best response là HẰNG — lấy mẫu ở điểm giữa là đủ, và
            # không phụ thuộc độ mịn của lưới nào cả.
            y = float(min(best_response(prof, 0.5 * (a + b))[0]))
            # lw=4 cố ý: ở panel Fair-share/Cond thì Flash, Luna, Haiku nằm ĐÚNG trên mốc
            # 20 phía trên p*, nên một đường mảnh sẽ bị đường model đè mất hẳn — và chỗ bị
            # đè lại chính là chỗ đáng xem nhất. Bề dày chốt ở BR_LW, xem giải thích ở đó.
            ax.plot([a, b], [y, y], color="#bdbdbd", lw=BR_LW, ls=(0, (4, 1.6)), zorder=1,
                    solid_capstyle="butt")

        # --- đường model, kèm CI bootstrap n = 10/ô ---
        for mi, tag in enumerate(MODEL_ORDER):
            key = MODELS[tag][1]
            colour, marker, ls = MODEL_STYLE[key]
            lw, ms, zo = _series_style(mi)
            mu, err_lo, err_hi = [], [], []
            for k, p in enumerate(RISKS):
                v = scored[(scored.profile == prof) & (scored.model_tag == tag)
                           & (scored.risk == p)]["llm_total"].to_numpy()
                if len(v) != EXPECTED_REPS:
                    raise ValueError(f"ô ({prof},{tag},{p}) có {len(v)} ván")
                m = float(v.mean())
                a, b = boot_ci(v, BOOT_SEED + 97 * k)
                mu.append(m); err_lo.append(m - a); err_hi.append(b - m)
            # Marker RỖNG + bề dày/cỡ lồng nhau, thay cho dodge cũ: xem _series_style().
            ax.errorbar(pgrid, mu, yerr=[err_lo, err_hi], color=colour, marker=marker,
                        ls=ls, lw=lw, ms=ms, mfc="none", mew=0.85, capsize=1.3,
                        elinewidth=0.55, zorder=zo)

        # --- chỗ hoà: vẽ SAU đường model và nằm TRÊN chúng ---
        # Bản trước để zorder=2 trong khi đường model là 3, nên ở panel Fair-share/Cond
        # đúng cái vòng tròn trên (p*, 20) — nửa đáng xem nhất của chú thích — bị ba đường
        # model đang nằm ở 20 phủ kín, và docstring thì vẫn kể là "hai vòng tròn". Chú
        # thích tham chiếu thì phải nằm trên cùng.
        for x0 in ties:
            vals = best_response(prof, x0)[0]
            ax.plot([x0, x0], [min(vals), max(vals)], color="#5a5a5a", lw=0.9, ls=":",
                    zorder=6)
            for y in (min(vals), max(vals)):
                ax.plot([x0], [y], marker="o", ms=4.6, mfc="white", mec="#3a3a3a",
                        mew=1.0, ls="none", zorder=7)
            # Đặt nhãn vào khoảng trống giữa hai nhánh, không đặt phía trên: phía trên là
            # chỗ đường Grok chạy qua.
            ax.annotate(r"$p^*$", xy=(x0 + 0.04, 0.40 * (min(vals) + max(vals))),
                        fontsize=6.8, color="#3a3a3a", zorder=7)

        ax.set_title(PROFILE_LABEL[prof].replace("\\ ", " ").replace("\\", ""), pad=3)
        ax.set_xlim(0.0, 1.0)
        ax.set_ylim(-1.5, 41)
        ax.set_yticks([0, 10, 20, 30, 40])
        ax.set_xticks([0.1, 0.3, 0.5, 0.7, 0.9])
        ax.tick_params(length=2)
        ax.grid(True, lw=0.3, color="#e6e6e6", zorder=0)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)

    fig.supxlabel("catastrophe risk $p$", fontsize=7.6, y=0.088)
    # Nhãn cũ "LLM contribution" trên thang 0–40 đọc nhầm được thành "đóng góp mỗi vòng",
    # trong khi mỗi vòng chỉ chọn được {0,2,4}. Đây là TỔNG 10 vòng trên vốn 40 — nói
    # thẳng ra, và nói ở MỘT chỗ (supylabel) để đủ bề dài chữ mà không chiếm chỗ hai lần.
    fig.supylabel("total contributed over ten rounds (of $40$)", fontsize=7.0, x=0.012)

    handles = [Line2D([], [], color=MODEL_STYLE[MODELS[t][1]][0],
                      marker=MODEL_STYLE[MODELS[t][1]][1],
                      ls=MODEL_STYLE[MODELS[t][1]][2], mfc="none", mew=0.85,
                      lw=_series_style(i)[0], ms=_series_style(i)[1],
                      label=MODELS[t][1])
               for i, t in enumerate(MODEL_ORDER)]
    handles.append(Line2D([], [], color="#bdbdbd", lw=BR_LW, ls=(0, (4, 1.6)),
                          label="best resp."))
    fig.legend(handles=handles, loc="lower center", ncol=6, frameon=False,
               bbox_to_anchor=(0.52, -0.008), handlelength=1.45, columnspacing=0.5,
               handletextpad=0.3)
    fig.subplots_adjust(left=0.138, right=0.995, top=0.930, bottom=0.205,
                        hspace=0.28, wspace=0.12)
    _save_exact(fig, path)
    plt.close(fig)


# ======================================================================================
# 7. Bảng
# ======================================================================================
TABLE_HEAD = ("%% SINH TỰ ĐỘNG bởi paper/AAMAS/analysis/e3a_analysis.py — ĐỪNG SỬA TAY.\n"
              "%% Mọi con số gọi qua macro của e3a_numbers.tex nên bảng và text không lệch nhau.\n"
              "%% Cần: \\usepackage{booktabs}\n")


def table_contributions() -> str:
    rows = []
    for prof in PROFILES:
        pm = PROFILE_MACRO[prof]
        for k, tag in enumerate(MODEL_ORDER):
            mk = MODELS[tag][1]
            cells = [PROFILE_LABEL[prof] if k == 0 else "", MODELS[tag][0],
                     f"\\EthreeaMean{pm}{mk}",
                     f"$\\pm$\\EthreeaSd{pm}{mk}",
                     f"[\\EthreeaCIlo{pm}{mk}, \\EthreeaCIhi{pm}{mk}]",
                     f"\\EthreeaBR{pm}"]
            rows.append(" & ".join(cells) + r" \\")
        if prof != PROFILES[-1]:
            rows.append(r"\addlinespace")
    return TABLE_HEAD + r"""\begin{table}[t]
\centering
\small
\setlength{\tabcolsep}{4pt}%  <- do duoc 249.9pt o tabcolsep mac dinh 6pt, tran
%  cot 241.15pt cua acmart sigconf. Dat trong table env nen khong ro ri ra ngoai.
\caption{Total contribution by the single LLM seat over the ten rounds (endowment $40$),
pooled over the five risk levels; $n=\EthreeaNpercell$ games per cell. \textsc{ci} is a percentile
bootstrap ($10{,}000$ resamples, fixed seed). The last column is the exact best response,
computed by exhaustive search over the reachable outcomes; at $p=0.5$ the
\textsc{fair-share} and \textsc{cond.\ coop.} profiles admit two tied optima
($0$ and $20$).}
\label{tab:e3a-contrib}
\begin{tabular}{llrlrr}
\toprule
Opponents & Model & Mean & \textsc{sd} & 95\% \textsc{ci} & Best resp. \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}
\end{table}
"""


def table_brgap() -> str:
    r"""Bang 2 — khoang cach toi best response.

    ⚠️ COT `Share` DA BO, DUNG THEM LAI. `Share` = trung binh cua money_lost/br_ev, va o
    CA HAI profile bi troi chat thi br_ev triet tieu khoi phan so: o `defect` ca tu lan
    mau deu mang thua so (1-p), o `carry` thi br_ev = 40 hang so. Ket qua la Share dung
    bang Gap/40 toi chu so cuoi — in no canh Gap la in MOT con so hai lan, va nguoi doc
    thay hai cot dong y nhau se doc nham thanh hai phep do doc lap cung xac nhan. Bo cot
    con tra lai ~30pt be ngang, dung cho bang dang tran cot acmart (xem dau file muc).
    Macro \EthreeaLossPct... van duoc sinh, de van xuoi goi khi can mot con so chuan hoa.

    Hai dong nhat thuc CON LAI khong bo cot duoc nen phai noi thang: o `defect`/`carry`
    best response = 0 o moi p nen Gap CHINH LA cot Mean cua Bang 1, va rieng `carry` thi
    Forfeited = Gap tung xu. De ba cho trung nhau trong im lang la moi nguoi doc dem MOT
    bang chung thanh ba.

    NOI O DAU. Caption thoi thi KHONG DU: nguoi doc luot bang truoc, doc caption sau (neu
    doc). Nen hai khoi do mang mot dagger ngay tren nhan `Opponents` (xem
    TIED_COLUMN_PROFILES), va caption giai thich dagger do. Dung go dagger ra khoi bang
    roi de lai moi cau trong caption — do dung la trang thai da bi che o vong phan bien.
    """
    rows = []
    for prof in PROFILES:
        pm = PROFILE_MACRO[prof]
        # Dagger tren nhan khoi: nguoi doc luot bang TRUOC khi doc caption, nen dau
        # hieu 'hai cot nay la mot phep do' phai nam trong bang chu khong chi duoi no.
        label = PROFILE_LABEL[prof] + (
            "\\textsuperscript{\\dag}" if prof in TIED_COLUMN_PROFILES else "")
        for k, tag in enumerate(MODEL_ORDER):
            mk = MODELS[tag][1]
            cells = [label if k == 0 else "", MODELS[tag][0],
                     f"\\EthreeaGap{pm}{mk}", f"\\EthreeaLoss{pm}{mk}",
                     f"\\EthreeaIsBR{pm}{mk}\\%"]
            rows.append(" & ".join(cells) + r" \\")
        if prof != PROFILES[-1]:
            rows.append(r"\addlinespace")
    return TABLE_HEAD + r"""\begin{table}[t]
\centering
\small
\setlength{\tabcolsep}{2.5pt}%  <- ban 6 cot truoc day tran cot acmart 29.4pt; bo cot
%  `Share` (= Gap/40, xem docstring generator). Ha them 4 -> 2.5pt vi dagger tren nhan hai
%  khoi an ~13pt be ngang: khung xem thu (article 10pt) bao Overfull o 4pt va 3pt, het han
%  o 2.5pt; khung acmart 9pt thi khong tran o bat ky muc nao trong ba. Dat trong table env
%  nen khong ro ri ra ngoai.
\caption{Distance to best response. \emph{Gap} is the distance from the realised total
contribution to the nearest best response, in contribution units; \emph{Forfeited} prices
that gap as expected payoff under the best response minus expected payoff under what was
played, in units of the $40$-unit endowment, hence a risk-neutral valuation;
\emph{Optimal} is the percentage of games played at zero cost. Expectations are taken over
the catastrophe lottery, so the numbers do not inherit its variance. \textsuperscript{\dag}These two
blocks hold fewer independent numbers than columns and should be read as a single
measurement: the best response there is $0$ at every $p$, so \emph{Gap} is by construction
the mean total contribution, and under \textsc{all-contribute} \emph{Forfeited} equals
\emph{Gap} to the cent, the target being secured whatever the seat does. Only the
\textsc{fair-share} and \textsc{cond.\ coop.} blocks carry two independent numbers.}
\label{tab:e3a-gap}
\begin{tabular}{llrrr}
\toprule
Opponents & Model & Gap & Forfeited & Optimal \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}
\end{table}
"""


def table_target() -> str:
    rows = []
    for prof in PROFILES:
        pm = PROFILE_MACRO[prof]
        cells = [PROFILE_LABEL[prof]] + [f"\\EthreeaHit{pm}{MODELS[t][1]}\\%"
                                         for t in MODEL_ORDER]
        rows.append(" & ".join(cells) + r" \\")
    head = " & ".join(["Opponents"] + [MODELS[t][1] for t in MODEL_ORDER])
    return TABLE_HEAD + r"""\begin{table}[t]
\centering
\small
\setlength{\tabcolsep}{4pt}%  <- do duoc 249.9pt o tabcolsep mac dinh 6pt, tran
%  cot 241.15pt cua acmart sigconf. Dat trong table env nen khong ro ri ra ngoai.
\caption{Share of games in which the group reached the $120$ target (\%, $n=\EthreeaNpercell$ per cell).
The top two rows are mechanical and carry no information about the model: against
all-defectors the five scripted seats contribute nothing, so $120$ is out of reach whatever
the LLM does, and against all-contributors they bank $200$ between them, so the target is
secured before the LLM moves. Only the bottom two rows are decided by the LLM seat, and
there one model stands apart: Qwen stops $\EthreeaQwenCoopShort$ short of the target in
$\EthreeaQwenCoopMissGames$ of its $\EthreeaNpercell$ \textsc{fair-share} games.}
\label{tab:e3a-target}
\begin{tabular}{lrrrrr}
\toprule
""" + head + r""" \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}
\end{table}
"""


# ======================================================================================
# 8. main
# ======================================================================================
def main() -> int:
    data = load_e3a()
    scored = score(data)
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)

    mac = Macros()
    mac.add("Ngames", str(len(scored)))
    mac.add("Nprofiles", str(len(PROFILES)))
    mac.add("Nmodels", str(len(MODEL_ORDER)))
    mac.add("Nrisks", str(len(RISKS)))
    mac.add("Nreps", str(EXPECTED_REPS))
    mac.add("Ncells", str(len(PROFILES) * len(MODEL_ORDER) * len(RISKS)))
    # So van moi o (profile, model) — go tay "50" trong van xuoi va caption la cho
    # de vo nhat khi doi luoi risk hoac so rep, vi no KHONG doi cung luc voi Nreps.
    mac.add("Npercell", str(len(RISKS) * EXPECTED_REPS))
    mac.add("Endowment", str(int(ENDOWMENT)))
    mac.add("Target", str(int(TARGET)))
    mac.add("Pstar", "0.5")

    print("=" * 78)
    print("E3a — 1 ghế LLM giữa 5 ghế scripted biết trước")
    print("=" * 78)
    print(f"ván: {len(scored)}  |  lượt gọi API của ghế LLM: {len(scored) * N_ROUNDS}")

    # --- best response tra cứu được, in ra cho người đọc kiểm bằng mắt ---
    print("\n[ BEST RESPONSE — quét vét cạn ]")
    for prof in PROFILES:
        pieces = []
        for p in RISKS:
            totals, ev = best_response(prof, p)
            pieces.append(f"p={p}: {'/'.join(str(t) for t in totals)} (EV {ev:.1f})")
            mac.num(f"BREV{PROFILE_MACRO[prof]}{RISK_WORD[p]}", ev, 2)
            mac.add(f"BRTot{PROFILE_MACRO[prof]}{RISK_WORD[p]}",
                    "/".join(str(t) for t in totals))
        # cột "best response" của bảng 1: mô tả gọn, dùng chung cho cả 5 mức risk
        uniq = {tuple(best_response(prof, p)[0]) for p in RISKS}
        if len(uniq) == 1:
            desc = str(min(next(iter(uniq))))
        else:
            desc = "$0 \\to 20$"
        mac.add(f"BR{PROFILE_MACRO[prof]}", desc)
        print(f"  {prof:7s} " + " | ".join(pieces))

    # --- bảng chính: profile x model ---
    print("\n[ ĐÓNG GÓP CỦA GHẾ LLM, và KHOẢNG CÁCH TỚI BEST RESPONSE ]")
    print(f"{'profile':8s}{'model':16s}{'mean':>7s}{'sd':>7s}{'95% CI':>16s}"
          f"{'gap':>7s}{'lost':>7s}{'share':>8s}{'opt%':>7s}{'hit%':>7s}")
    for prof in PROFILES:
        pm = PROFILE_MACRO[prof]
        for tag in MODEL_ORDER:
            mk = MODELS[tag][1]
            sel = scored[(scored.profile == prof) & (scored.model_tag == tag)]
            tot = sel["llm_total"].to_numpy()
            mu, sd = float(tot.mean()), float(tot.std(ddof=1))
            lo, hi = boot_ci(tot, BOOT_SEED)
            gap = float(sel["gap_contrib"].mean())
            lost = float(sel["money_lost"].mean())
            share = float(sel["frac_lost"].mean()) * 100.0
            opt = float(sel["is_br"].mean()) * 100.0
            hit = float(sel["target_reached"].mean()) * 100.0
            mac.num(f"Mean{pm}{mk}", mu); mac.num(f"Sd{pm}{mk}", sd)
            mac.num(f"CIlo{pm}{mk}", lo); mac.num(f"CIhi{pm}{mk}", hi)
            mac.num(f"Gap{pm}{mk}", gap); mac.num(f"Loss{pm}{mk}", lost)
            mac.num(f"LossPct{pm}{mk}", share, 1)
            mac.num(f"IsBR{pm}{mk}", opt, 0)
            mac.num(f"Hit{pm}{mk}", hit, 0)
            print(f"{prof:8s}{MODELS[tag][0]:16s}{mu:7.2f}{sd:7.2f}"
                  f"{'[%.2f, %.2f]' % (lo, hi):>16s}{gap:7.2f}{lost:7.2f}"
                  f"{share:7.1f}%{opt:6.0f}%{hit:6.0f}%")
        print()

    # --- tổng hợp toàn bộ + theo model ---
    mac.num("LossAll", float(scored["money_lost"].mean()))
    mac.num("LossPctAll", float(scored["frac_lost"].mean()) * 100.0, 1)
    mac.num("IsBRAll", float(scored["is_br"].mean()) * 100.0, 1)
    mac.add("IsBRAllGames", str(int(scored["is_br"].sum())))
    print(f"[ GỘP 1000 VÁN ] tiền bỏ lại TB = {scored['money_lost'].mean():.2f}/40 "
          f"({scored['frac_lost'].mean() * 100:.1f}% EV khả dĩ)  |  "
          f"ván chơi đúng best response: {int(scored['is_br'].sum())}/{len(scored)}")

    for tag in MODEL_ORDER:
        mk = MODELS[tag][1]
        sel = scored[scored.model_tag == tag]
        mac.num(f"LossAll{mk}", float(sel["money_lost"].mean()))
        mac.num(f"LossPctAll{mk}", float(sel["frac_lost"].mean()) * 100.0, 1)
        mac.num(f"IsBRAll{mk}", float(sel["is_br"].mean()) * 100.0, 0)
    worst = max(MODEL_ORDER, key=lambda t: scored[scored.model_tag == t]["money_lost"].mean())
    best = min(MODEL_ORDER, key=lambda t: scored[scored.model_tag == t]["money_lost"].mean())
    mac.add("WorstModel", MODELS[worst][0]); mac.add("BestModel", MODELS[best][0])
    mac.num("WorstModelLoss", float(scored[scored.model_tag == worst]["money_lost"].mean()))
    mac.num("BestModelLoss", float(scored[scored.model_tag == best]["money_lost"].mean()))

    # --- "không ván nào bỏ mặc trọn vẹn" ---
    all_zero = int((scored["llm_total"] == 0).sum())
    dom = scored[scored.profile.isin(["defect", "carry"])]
    mac.add("AllZeroGames", str(all_zero))
    mac.add("DominatedGames", str(len(dom)))
    mac.add("DominatedZero", str(int((dom["llm_total"] == 0).sum())))
    mac.num("DominatedLoss", float(dom["money_lost"].mean()))
    print(f"[ BỎ MẶC TRỌN VẸN ] ván mà ghế LLM đóng 0 suốt 10 vòng: {all_zero}/{len(scored)}"
          f"  (riêng 2 profile mà 0 là best response ở MỌI p: "
          f"{int((dom['llm_total'] == 0).sum())}/{len(dom)})")

    # --- CHỖ NÀO model chơi đúng best response? ---
    # Đây là con số đắt nhất của mục này nên tính riêng, đừng gộp vào bảng: cả 186 ván
    # chơi đúng best response đều là ván model đóng ĐÚNG 20 — tức là đúng phần công bằng
    # 2/vòng mà prompt nêu sẵn. Không có một ván nào trong số 700 ván mà best response DUY
    # NHẤT là "đóng 0" được chơi đúng. Nói cách khác model không bao giờ suy ra được đáp
    # án đúng; nó chỉ trúng khi đáp án đúng TÌNH CỜ trùng với mốc công bằng quy ước.
    uniq_zero = scored[scored.apply(
        lambda r: best_response(r["profile"], r["risk"])[0] == [0], axis=1)]
    mac.add("UniqZeroGames", str(len(uniq_zero)))
    mac.add("UniqZeroOptimal", str(int(uniq_zero["is_br"].sum())))
    opt = scored[scored["is_br"] == 1]
    mac.add("OptimalGames", str(len(opt)))
    mac.add("OptimalTotals", "/".join(f"{v:.0f}" for v in sorted(opt["llm_total"].unique())))
    mac.num("OptimalMinRisk", float(opt["risk"].min()), 1)
    for prof in PROFILES:
        mac.num(f"MinContrib{PROFILE_MACRO[prof]}",
                float(scored[scored.profile == prof]["llm_total"].min()), 0)
    print(f"\n[ CHƠI ĐÚNG BEST RESPONSE ] {len(opt)}/{len(scored)} ván, "
          f"tổng đóng góp trong đó chỉ nhận giá trị "
          f"{sorted(opt['llm_total'].unique().tolist())} — đúng bằng phần công bằng.")
    print(f"  ván mà best response DUY NHẤT là đóng 0: {len(uniq_zero)}, "
          f"chơi đúng: {int(uniq_zero['is_br'].sum())}")
    print("  mức đóng góp NHỎ NHẤT từng quan sát, theo profile: "
          + ", ".join(f"{p}={scored[scored.profile == p]['llm_total'].min():.0f}"
                      for p in PROFILES))

    # --- ĐỘ NHẠY THEO NGẠI RỦI RO: con số headline có phụ thuộc γ = 0 không? -----------
    # Mọi con số "tiền bỏ lại trên bàn" ở trên định giá bằng EV, tức NGẦM đặt γ = 0. Ở
    # `coop`/`cond` lựa chọn thật sự là "chắc chắn 20" so với "xổ số trị giá (1-p)*40",
    # nên CHÍNH giả định đó quyết định kết quả. Reviewer tính lại được trong ba dòng, và
    # sẽ tính: cùng một cách chơi được chấm là best response ở 186/1000 ván khi γ = 0
    # nhưng 308/1000 khi γ = 0,9. Tự in ra thì được điểm; để người khác tìm ra thì mất.
    print("\n[ ĐỘ NHẠY CRRA — cùng data, đổi hệ số ngại rủi ro ]")
    for gamma in CRRA_GAMMAS:
        gw = GAMMA_WORD[gamma]
        # Chốt lại lời hứa của TẬP BỊ TRÓI CHẶT trước khi đếm: ở `defect`/`carry` best
        # response phải là {0} dưới MỌI γ đem thử. Cả xương sống của mục này đứng trên đó,
        # nên để assertion ở đây chứ đừng chỉ viết trong văn xuôi.
        for prof in ("defect", "carry"):
            for p_ in RISKS:
                if best_response_crra(prof, p_, gamma) != [0]:
                    raise ValueError(f"{prof} p={p_} γ={gamma}: best response không còn "
                                     "là 0 — tập 'bị trói chặt' đã hết bị trói chặt")
        n_br = n_br_dom = 0
        for _, row in scored.iterrows():
            tot = best_response_crra(row["profile"], row["risk"], gamma)
            hit = int(any(abs(row["llm_total"] - t) < 1e-9 for t in tot))
            n_br += hit
            if row["profile"] in ("defect", "carry"):
                n_br_dom += hit
        mac.add(f"IsBRCrra{gw}", str(n_br))
        mac.num(f"IsBRCrraPct{gw}", 100.0 * n_br / len(scored), 1)
        mac.add(f"IsBRDomCrra{gw}", str(n_br_dom))
        mac.num(f"PstarCoop{gw}", crra_pstar("coop", gamma), 2)
        mac.num(f"{gw}Val", gamma, 1)
        print(f"  γ = {gamma}: best response ở {n_br}/{len(scored)} ván "
              f"(tập bị trói chặt {n_br_dom}/{len(dom)}), "
              f"p* của fair-share = {crra_pstar('coop', gamma):.2f}")

    # Bao nhiêu phần của con số GỘP đến từ hai profile mà γ ĐỤNG ĐƯỢC vào? Phần đó càng
    # lớn thì con số gộp càng là phát biểu về giả định chứ không phải về model — nên nó
    # phải đi kèm chữ "chặn trên" mỗi lần xuất hiện trong văn xuôi.
    tied_loss = float(scored[scored.profile.isin(["coop", "cond"])]["money_lost"].sum())
    mac.num("LossShareTied", 100.0 * tied_loss / float(scored["money_lost"].sum()), 0)
    mac.num("LossPctDominated", float(dom["frac_lost"].mean()) * 100.0, 1)
    print(f"  phần tiền bỏ lại đến từ coop/cond (đúng chỗ γ đụng được): "
          f"{100.0 * tied_loss / scored['money_lost'].sum():.0f}%")

    # --- TÁCH THEO VÒNG: chỗ nào "không biết đối thủ" còn bào chữa được, chỗ nào không ---
    # Phản biện nặng nhất nhắm vào cả mục này: model KHÔNG hề được cho biết 5 ghế kia là
    # script tất định (`agent{i}_knows_opponent_with_prob` = 0, prompt không nói một chữ
    # nào về đối thủ). Nhưng luật chơi CÔNG BỐ đóng góp của cả 6 ghế sau MỖI vòng, nên với
    # `defect` (luôn 0) và `carry` (luôn 4) thì chính sách đối thủ SUY RA ĐƯỢC từ lịch sử,
    # không cần ai nói trước. Vòng 1 thì chưa có lịch sử nào nên không trách được; tới
    # vòng INFER_ROUND người chơi đã thấy INFER_ROUND-1 vòng liên tiếp cho ra cùng một bộ
    # năm con số. Nên tách hai khúc và ĐẶT CLAIM Ở KHÚC SAU.
    #
    # Chỉ tính trên tập bị trói chặt, vì ở đó best response là "đóng 0 ở MỌI vòng" — nên
    # khoảng cách tới best response của một vòng CHÍNH LÀ số đơn vị đóng ở vòng đó, không
    # phải một đại lượng phải phân bổ lại theo vòng.
    late_slice = slice(INFER_ROUND - 1, N_ROUNDS)
    n_late = N_ROUNDS - INFER_ROUND + 1
    r1_dom = dom["llm_moves"].map(lambda v: float(v[0])).to_numpy()
    late_dom = dom["llm_moves"].map(lambda v: float(sum(v[late_slice]))).to_numpy()
    # Định giá đơn vị đóng góp: ở `carry` mỗi đơn vị là mất trắng CHẮC CHẮN (target đã
    # được 5 ghế kia chốt), ở `defect` nhóm luôn trượt nên đơn vị chỉ mất trên nhánh sống
    # sót, hệ số (1-p). Đây đúng là hệ số đã dùng ở cột `Forfeited`, chỉ hẹp lại theo vòng.
    surv_dom = np.where(dom["profile"].to_numpy() == "defect",
                        1.0 - dom["risk"].to_numpy().astype(float), 1.0)
    tag_dom = dom["model_tag"].to_numpy()
    mac.add("InferRound", str(INFER_ROUND))
    mac.add("InferHistory", str(INFER_ROUND - 1))
    # Giá trị mang sẵn `$...$` và dấu `--`: phải dùng NGOÀI math mode (`rounds~\Ethreea...`).
    # Nếu bọc thêm `$...$` quanh nó thì `--` thành HAI DẤU TRỪ chứ không phải gạch nối en —
    # đã in ra "6 − −10" một lần rồi, đừng lặp lại.
    mac.add("LateRounds", f"${INFER_ROUND}$--${N_ROUNDS}$")
    mac.num("RoundOneMeanDom", float(r1_dom.mean()))
    mac.num("RoundOneLossDom", float((r1_dom * surv_dom).mean()))
    mac.num("LateTotalDom", float(late_dom.mean()))
    mac.num("LatePerRoundDom", float(late_dom.mean()) / n_late)
    mac.num("LateLossDom", float((late_dom * surv_dom).mean()))
    mac.num("LateCleanDom", 100.0 * float((late_dom == 0).mean()), 0)
    print(f"\n[ TÁCH THEO VÒNG — tập bị trói chặt, {len(dom)} ván ]")
    print(f"  vòng 1 (chưa có lịch sử, không trách được): TB {r1_dom.mean():.2f} đơn vị")
    print(f"  vòng {INFER_ROUND}-{N_ROUNDS} (đã thấy {INFER_ROUND - 1} vòng giống hệt "
          f"nhau): TB {late_dom.mean():.2f} đơn vị/ván "
          f"= {(late_dom * surv_dom).mean():.2f} EV, "
          f"{100 * (late_dom == 0).mean():.0f}% ván sạch")
    for tag in MODEL_ORDER:
        mk = MODELS[tag][1]
        m = tag_dom == tag
        mac.num(f"LateTotalDom{mk}", float(late_dom[m].mean()))
        mac.num(f"LateLossDom{mk}", float((late_dom * surv_dom)[m].mean()))
        mac.num(f"LateCleanDom{mk}", 100.0 * float((late_dom[m] == 0).mean()), 0)
        print(f"   {MODELS[tag][0]:16s} vòng 1 {r1_dom[m].mean():.2f} | "
              f"vòng {INFER_ROUND}-{N_ROUNDS} {late_dom[m].mean():5.2f} "
              f"(sạch {100 * (late_dom[m] == 0).mean():3.0f}%)")

    # --- mỏ neo vòng 1 ---
    print("\n[ VÒNG 1 — mỏ neo prompt ]")
    for tag in MODEL_ORDER:
        mk = MODELS[tag][1]
        sel = scored[scored.model_tag == tag]
        mac.num(f"RoundOne{mk}", float(sel["round1"].mean()))
        mac.num(f"RoundOneShareTwo{mk}", float((sel["round1"] == 2).mean()) * 100.0, 0)
        print(f"  {MODELS[tag][0]:16s} TB {sel['round1'].mean():.2f}  "
              f"(đóng đúng 2: {(sel['round1'] == 2).mean() * 100:3.0f}%)  "
              f"theo p: " + " ".join(f"{p}:{sel[sel.risk == p]['round1'].mean():.2f}"
                                     for p in RISKS))
    anchored = [t for t in MODEL_ORDER if (scored[scored.model_tag == t]["round1"] == 2).all()]
    # Van xuoi noi nhom nay mo dung 2 "trong 100% so van". Con so do la KET QUA DO DUOC,
    # khong phai hang so luat choi, nen phai la macro: neu mot ngay co model tut xuong 98%
    # thi `anchored` se rong va cau van phai doi, chu dung de no in "100%" mai mai.
    anchored_share = {float((scored[scored.model_tag == t]["round1"] == 2).mean()) * 100.0
                      for t in anchored}
    if len(anchored_share) != 1:
        raise ValueError(f"nhom mo neo khong cung mot ty le: {sorted(anchored_share)}")
    mac.num("RoundOneAnchoredShare", anchored_share.pop(), 0)
    mac.add("RoundOneAnchoredN", str(len(anchored)))
    mac.add("RoundOneAnchoredModels", ", ".join(MODELS[t][1] for t in anchored))
    mac.num("RoundOneFairShare", FAIR_SHARE)

    # --- độ dốc theo risk ---
    print("\n[ ĐỘ DỐC THEO RISK — hệ số góc OLS + kiểm định hoán vị ]")
    slopes = []
    for prof in PROFILES:
        for tag in MODEL_ORDER:
            sel = scored[(scored.profile == prof) & (scored.model_tag == tag)]
            s, pv = perm_slope_p(sel["risk"].to_numpy(), sel["llm_total"].to_numpy(),
                                 PERM_SEED)
            mac.num(f"Slope{PROFILE_MACRO[prof]}{MODELS[tag][1]}", s, 1)
            mac.num(f"SlopeP{PROFILE_MACRO[prof]}{MODELS[tag][1]}", pv, 3)
            slopes.append((abs(s), s, pv, prof, tag))
    sig = [x for x in slopes if x[2] < 0.05]
    mac.add("SlopeSigN", str(len(sig)))
    mac.add("SlopeTotalN", str(len(slopes)))
    biggest = max(slopes)
    mac.num("SlopeMaxAbs", biggest[1], 1)
    mac.add("SlopeMaxCell", f"{PROFILE_LABEL[biggest[3]]}/{MODELS[biggest[4]][1]}"
            .replace("\\ ", " ").replace("\\", ""))
    # Quy cả độ dốc ra đơn vị dễ hình dung: p chạy 0.1 -> 0.9 thì đóng góp đổi bao nhiêu.
    mac.num("SlopeMaxSwing", biggest[1] * 0.8, 1)
    print(f"  ô có độ dốc khác 0 ở mức 5%: {len(sig)}/{len(slopes)}")
    for a, s, pv, prof, tag in sorted(slopes, reverse=True)[:5]:
        star = "*" if pv < 0.05 else " "
        print(f"   {star} {prof:7s} {MODELS[tag][0]:16s} slope {s:+6.1f} /unit p  "
              f"(p={0.1}->{0.9}: {s * 0.8:+5.1f})  perm p = {pv:.3f}")

    # --- ba chân dung hành vi ở profile fair-share ---
    print("\n[ FAIR-SHARE (coop) — quỹ đạo ]")
    coop = scored[scored.profile == "coop"]
    for tag in MODEL_ORDER:
        mk = MODELS[tag][1]
        sel = coop[coop.model_tag == tag]
        counts = sel["llm_moves"].map(str).value_counts()
        top_traj, top_n = counts.index[0], int(counts.iloc[0])
        mac.add(f"CoopModalN{mk}", str(top_n))
        mac.add(f"CoopDistinct{mk}", str(len(counts)))
        mac.num(f"CoopModalTotal{mk}", float(sum(ast.literal_eval(top_traj))), 0)
        print(f"  {MODELS[tag][0]:16s} {len(counts)} quỹ đạo khác nhau; "
              f"phổ biến nhất {top_n}/50 = {top_traj} (tổng {sum(ast.literal_eval(top_traj)):.0f})")

    qw = coop[coop.model_tag == "qwen-qwen3-235b-a22b-instruct-2507"]
    mac.num("QwenCoopGroupTotal", float(qw["group_total"].mean()), 1)
    # ⚠️ ĐỪNG viết lại thành `int(TARGET - mean)`. Thiếu hụt TRUNG BÌNH là 1,88 nên `int()`
    # CẮT CỤT xuống 1 — mâu thuẫn với caption của chính bảng 3 do file này sinh ("stops 2
    # short") và mâu thuẫn với số học của bàn: nhóm cần đúng 20 từ ghế LLM, qwen đóng 18,
    # nên ván nào trượt là trượt ĐÚNG 2. Trung bình chỉ nhỏ hơn 2 vì có vài ván qwen đóng
    # đủ. Con số đúng cho văn xuôi là thiếu hụt QUAN SÁT ĐƯỢC trong các ván trượt; lấy
    # thẳng từ data rồi chốt lại nó chỉ nhận một giá trị, thay vì làm tròn một trung bình.
    qw_miss = qw[qw["target_reached"] == 0]
    shortfalls = sorted({float(TARGET - g) for g in qw_miss["group_total"]})
    if len(shortfalls) != 1:
        raise ValueError("qwen/coop trượt target với nhiều mức thiếu hụt khác nhau: "
                         f"{shortfalls} — văn xuôi không được nói 'stops N short' nữa")
    # Văn xuôi nói quỹ đạo phổ biến nhất VÀ tập ván trượt là MỘT tập. Hai con số bằng nhau
    # (47 = 47) nên rất dễ tưởng là trùng hợp; chốt lại bằng so tập game_id, vì nếu một
    # ngày chúng tách ra thì câu đó thành hai khẳng định khác nhau bị viết như một.
    qw_modal_ids = set(qw[qw["llm_moves"].map(str) ==
                          qw["llm_moves"].map(str).value_counts().index[0]]["game_id"])
    if qw_modal_ids != set(qw_miss["game_id"]):
        raise ValueError("qwen/coop: quỹ đạo phổ biến nhất KHÔNG còn trùng tập ván trượt "
                         "target — sửa câu văn trong 05_bestresponse.tex trước khi chạy tiếp")
    mac.add("QwenCoopShort", f"{shortfalls[0]:.0f}")
    mac.add("QwenCoopMissGames", str(len(qw_miss)))
    mac.num("QwenCoopShortMean", float(TARGET - qw["group_total"].mean()), 2)
    gk = coop[coop.model_tag == "xai-grok-4.20-0309-non-reasoning"]
    gk_counts = gk["llm_moves"].map(str).value_counts()
    mac.add("GrokCoopTwos", str(int(gk_counts.get("[2, 2, 2, 2, 2, 2, 2, 2, 2, 2]", 0))))
    mac.add("GrokCoopFours", str(int(gk_counts.get("[4, 4, 4, 4, 4, 4, 4, 4, 4, 4]", 0))))
    print(f"  -> Qwen gom trung bình {qw['group_total'].mean():.1f}/120, "
          f"thiếu {TARGET - qw['group_total'].mean():.0f}; đạt target "
          f"{qw['target_reached'].mean() * 100:.0f}%")

    # --- coop vs cond suy biến ---
    same = 0
    for tag in MODEL_ORDER:
        a = scored[(scored.profile == "coop") & (scored.model_tag == tag)]["llm_total"].mean()
        b = scored[(scored.profile == "cond") & (scored.model_tag == tag)]["llm_total"].mean()
        if abs(a - b) < 0.5:
            same += 1
    mac.add("CondCoopSameN", str(same))
    mac.add("CondTrajectories", f"{len(OPTIONS) ** N_ROUNDS:,}".replace(",", "{,}"))
    print(f"\n[ cond SUY BIẾN ] conditional cooperator không bao giờ rời mức 2 trên cả "
          f"{len(OPTIONS) ** N_ROUNDS} quỹ đạo; {same}/5 model cho cùng trung bình ở coop và cond")

    # --- ghi file ---
    header = (
        "% ==================================================================\n"
        "% SINH TỰ ĐỘNG bởi paper/AAMAS/analysis/e3a_analysis.py — ĐỪNG SỬA TAY.\n"
        "% Chạy lại: python paper/AAMAS/analysis/e3a_analysis.py\n"
        "% Nguồn: results/exp_bestresponse_{defect,carry,coop,cond}/ (1000 ván).\n"
        "%\n"
        "% File này CHỈ chứa \\newcommand nên \\input được ngay trong preamble.\n"
        "% Ba bảng booktabs nằm ở file riêng và gọi lại chính các macro này:\n"
        "%   \\input{tables/e3a_table_contributions.tex}\n"
        "%   \\input{tables/e3a_table_brgap.tex}\n"
        "%   \\input{tables/e3a_table_target.tex}\n"
        "%\n"
        "% Quy ước tên: \\Ethreea<Đại lượng><Profile><Model>\n"
        "%   Profile = Defect | Carry | Coop | Cond\n"
        "%   Model   = Haiku | Flash | Luna | Qwen | Grok\n"
        "%   Đại lượng = Mean Sd CIlo CIhi Gap Loss LossPct IsBR Hit Slope SlopeP\n"
        "% Tiền tệ tính theo đơn vị vốn 40; Gap tính theo đơn vị đóng góp.\n"
        "% ==================================================================\n")
    (TABLES / "e3a_numbers.tex").write_text(header + mac.render() + "\n", encoding="utf-8")
    (TABLES / "e3a_table_contributions.tex").write_text(table_contributions(), encoding="utf-8")
    (TABLES / "e3a_table_brgap.tex").write_text(table_brgap(), encoding="utf-8")
    (TABLES / "e3a_table_target.tex").write_text(table_target(), encoding="utf-8")

    fig_rounds(scored, FIGURES / "e3a_rounds_dominated.pdf")
    fig_by_risk(scored, FIGURES / "e3a_gap_by_risk.pdf")

    print("\n[ ĐÃ GHI ]")
    for q in (TABLES / "e3a_numbers.tex", TABLES / "e3a_table_contributions.tex",
              TABLES / "e3a_table_brgap.tex", TABLES / "e3a_table_target.tex",
              FIGURES / "e3a_rounds_dominated.pdf", FIGURES / "e3a_gap_by_risk.pdf"):
        print(f"  {q.relative_to(REPO).as_posix():52s} {q.stat().st_size:>8,} B")
    print(f"  ({len(mac._items)} macro)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
