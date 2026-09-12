#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""E3b — quần thể hỗn hợp: ai nhìn đồng đội, và ai không.

Chạy:  python paper/AAMAS/analysis/e3b_analysis.py

ĐỌC THẲNG từ `results/exp_mixed/` và không đọc gì khác. Không chạm `Legacy_Results/`
(kho đóng băng, trải nhiều panel/prompt khác nhau). Không ghi gì vào `results/`.

SINH RA
    paper/AAMAS/tables/e3b_numbers.tex          <- CHỈ \newcommand, input ở preamble
    paper/AAMAS/tables/e3b_table_reciprocity.tex
    paper/AAMAS/tables/e3b_table_composition.tex
    paper/AAMAS/figures/e3b_reciprocity.pdf

CÂU HỎI CỦA MỤC NÀY
    E3a hỏi "có chơi best response không" với đối thủ SCRIPTED, và câu trả lời là không,
    một ván cũng không. E3b hỏi câu kế tiếp, thứ mà chỉ bàn dị thể mới trả lời được: khi
    bạn cùng bàn là một MODEL KHÁC thật, model có nhìn hành vi của họ mà điều chỉnh không?

ĐẶC TẢ, VÀ VÌ SAO KHÔNG DÙNG ĐẶC TẢ HIỂN NHIÊN HƠN
    Hồi quy: đóng góp của ghế i ở vòng t  ~  đóng góp TRUNG BÌNH của 5 ghế kia ở vòng t-1.

    Dùng t-1 chứ không phải t: trong trò chơi này sáu ghế quyết định ĐỒNG THỜI, nên hồi
    quy lên cùng vòng là hồi quy lên thứ mà agent chưa thể nhìn thấy — hệ số khi đó đo sự
    giống nhau, không đo phản ứng.

    Khử bằng HIỆU ỨNG CỐ ĐỊNH theo ván và theo vòng, chứ KHÔNG khử bằng hai biến liên tục
    "số vòng đã chơi" + "phần thiếu hụt của quỹ". Đo thật trên 735 ván đầu: hai biến đó
    cộng tuyến mạnh (quỹ càng đầy thì vòng càng muộn), và hệ số của qwen nhảy từ -0,28 lên
    -0,90 tuỳ cách đưa chúng vào — tức là con số phụ thuộc đặc tả chứ không phụ thuộc dữ
    liệu. Hiệu ứng cố định hút hết cả hai kênh đó mà không phải giả định dạng hàm nào.

    Hiệu ứng cố định theo VÁN còn hút luôn một thứ quan trọng hơn: mức rủi ro, cặp model,
    và thành phần nhóm k đều là hằng số trong một ván. Nên hệ số còn lại chỉ đọc được là
    phản ứng TRONG NỘI BỘ một ván — đúng thứ ta muốn, và miễn nhiễm với việc các cặp khác
    nhau có mức đóng góp nền khác nhau.

VÌ SAO SAI SỐ CHUẨN PHẢI GOM CỤM THEO VÁN
    Một ván sinh ra 6 ghế × 9 vòng = 54 quan sát, và chúng phụ thuộc nhau nặng: cùng một
    lịch sử, cùng một quỹ, cùng một cú xổ số. Lấy sai số chuẩn thường là coi 54 thứ đó
    độc lập và sẽ hẹp đi vài lần. Plan §14 đòi khai báo cluster theo ván, và đây là chỗ
    thực hiện điều đó.
"""
from __future__ import annotations

import argparse
import ast
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
RESULTS = REPO / "results" / "exp_mixed"
TABLES = REPO / "paper" / "AAMAS" / "tables"
FIGURES = REPO / "paper" / "AAMAS" / "figures"

SHORT = {
    "anthropic-claude-haiku-4-5-20251001": "haiku",
    "google-gemini-3.5-flash-lite": "flash",
    "openai-gpt-5.6-luna": "luna",
    "qwen-qwen3-235b-a22b-instruct-2507": "qwen",
    "xai-grok-4.20-0309-non-reasoning": "grok",
}
PRETTY = {
    "haiku": r"Claude Haiku 4.5",
    "flash": r"Gemini 3.5 Flash Lite",
    "luna": r"GPT-5.6 Luna",
    "qwen": r"Qwen3 235B",
    "grok": r"Grok 4.20",
}
ORDER = ["haiku", "flash", "luna", "qwen", "grok"]
# ten rut gon -> tag day du, de sap dung thu tu ma ingest da dung khi dat ten tag
FULL = {v: k for k, v in SHORT.items()}
N_SEATS = 6


# --------------------------------------------------------------------- doc du lieu ---
def load_e3b(src: Path):
    """-> danh sach van, moi van la mot dict da parse.

    Doc `agent{i}_llm` chu KHONG doc ten thu muc: ten thu muc mang tag `mix__A__B__kN`
    do ingest suy ra, con `agent{i}_llm` la thu server that su da choi o tung ghe. Hai
    cai do lech nhau la loai loi im lang dat nhat o day, va cong ben duoi kiem dung no.
    """
    import csv
    games = []
    files = sorted(src.glob("*/*/*.csv"))
    if not files:
        raise SystemExit(
            "Khong tim thay file nao duoi %s.\n"
            "E3b phai duoc gom vao results/ truoc:\n"
            "  python plan/scripts/to_wide_csv.py --experiment exp_mixed --src "
            "D:/tmp/crgdl/*/crg-e3b-haiku-* ... \n"
            "  python plan/scripts/verify_wide.py --expect-reps 10" % src)
    for f in files:
        with open(f, encoding="utf-8") as h:
            for r in csv.DictReader(h):
                seats = [SHORT.get(r["agent%d_llm" % i]) for i in range(1, N_SEATS + 1)]
                if any(s is None for s in seats):
                    raise SystemExit(
                        "%s: ghe mang model ngoai panel 5 model -> %s"
                        % (f.name, [r["agent%d_llm" % i] for i in range(1, N_SEATS + 1)]))
                moves = [ast.literal_eval(r["agent%d_strategies" % i])
                         for i in range(1, N_SEATS + 1)]
                games.append({
                    "id": r["game_id"],
                    "risk": float(r["risk_probability"]),
                    "rep": int(r["rep"]),
                    "seats": seats,
                    "moves": moves,
                    "tag_dir": f.parent.name,
                    "target_reached": int(r["target_reached"]),
                    "group_total": float(r["group_total"]),
                })
    return games


def audit(games):
    """Cong kiem chay TRUOC moi con so. Sai o day thi moi thu duoi deu vo nghia."""
    errs = []
    present = defaultdict(int)      # model -> so van CO MAT
    seatgames = defaultdict(int)    # model -> so ghe-van
    for g in games:
        if len(set(g["seats"])) != 2:
            errs.append("%s: ban KHONG di the (%d loai model)"
                        % (g["id"], len(set(g["seats"]))))
        for m in set(g["seats"]):
            present[m] += 1
        for m in g["seats"]:
            seatgames[m] += 1
        # Tag thu muc phai khop voi ghe that. `k` trong `mix__A__B__kN` dem model
        # dung TRUOC theo thu tu TAG DAY DU (anthropic- < google- < openai- < qwen- <
        # xai-), KHONG phai theo ten rut gon dung trong file nay (flash < haiku ...).
        # Hai thu tu do khac nhau, va lan dau viet cong nay toi sap theo ten rut gon ->
        # no bao sai 9 van hoan toan lanh.
        a = min(set(g["seats"]), key=lambda s: FULL[s])
        k = g["seats"].count(a)
        if "__k%d" % k not in g["tag_dir"]:
            errs.append("%s: tag thu muc %r khong khop k=%d suy tu ghe that"
                        % (g["id"], g["tag_dir"], k))
    if len(set(present.values())) > 1:
        errs.append("CAN BANG: so van co mat lech giua cac model -> %s" % dict(present))
    if len(set(seatgames.values())) > 1:
        errs.append("CAN BANG: so ghe-van lech giua cac model -> %s" % dict(seatgames))
    return errs, present, seatgames


# ------------------------------------------------------------------- hoi quy ------
def panel_rows(games, model):
    """(y, x, pot, own, game, round, seat) cho MOT model.

    y   = dong gop cua ghe do o vong t
    x   = dong gop TRUNG BINH cua 5 ghe kia o vong t-1
    pot = tong quy TRUOC vong t
    own = tong gop cua CHINH ghe do truoc vong t

    `pot` co mat de tach hai co che khac nhau ma bo ba chung mot dau.
    `own` va `seat` chi phuc vu phep hoan vi: quy la HAM XAC DINH cua chuoi dong doi
        quy_t = own_t + 5 * (tong trung binh dong doi o cac vong < t)
    (dang thuc nay duoc kiem dung tren toan bo data), nen khi hoan vi xao chuoi dong doi
    thi PHAI dung lai quy tu chuoi da xao. Ban truoc giu nguyen quy va vi the sinh phan
    phoi null voi mot bien khu khong tuong thich voi hoi quy tu.
    """
    y, x, pot, own, gid, rnd, seat = [], [], [], [], [], [], []
    for g in games:
        T = min(len(m) for m in g["moves"])
        for t in range(1, T):
            pot_t = sum(sum(mv[:t]) for mv in g["moves"])
            for i, m in enumerate(g["seats"]):
                if m != model:
                    continue
                others = sum(g["moves"][j][t - 1]
                             for j in range(N_SEATS) if j != i) / (N_SEATS - 1)
                y.append(g["moves"][i][t])
                x.append(others)
                pot.append(pot_t)
                own.append(sum(g["moves"][i][:t]))
                gid.append(g["id"])
                rnd.append(t)
                seat.append(i)
    return (np.array(y, float), np.array(x, float), np.array(pot, float),
            np.array(own, float), np.array(gid), np.array(rnd, int),
            np.array(seat, int))


def twoway_fe_ols(y, x, gid, rnd, coef_only=False, extra=None):
    """He so cua x sau khi hut HIEU UNG CO DINH theo van va theo vong.

    Hut hieu ung co dinh theo van bang cach tru trung binh trong van (within), roi dua
    bien gia cua VONG vao hoi quy da bien. Sai so chuan gom cum theo van (Liang-Zeger),
    vi 6 ghe x 9 vong trong cung mot van khong he doc lap.
    """
    uniq_g, g_idx = np.unique(gid, return_inverse=True)
    uniq_r, r_idx = np.unique(rnd, return_inverse=True)

    def demean(v):
        sums = np.bincount(g_idx, weights=v, minlength=len(uniq_g))
        cnts = np.bincount(g_idx, minlength=len(uniq_g))
        return v - (sums / cnts)[g_idx]

    # bien gia vong, bo mot cai lam moc (da co hang so bi hut boi within)
    D = np.zeros((len(y), max(len(uniq_r) - 1, 0)))
    for j in range(1, len(uniq_r)):
        D[:, j - 1] = (r_idx == j).astype(float)

    cols = [demean(x)]
    if extra is not None:
        # Bien khu them (muc quy). Phai demean giong moi cot khac, neu khong hieu ung
        # co dinh theo van khong duoc hut het va he so cua x se lech.
        cols.append(demean(extra))
    cols += [demean(D[:, j]) for j in range(D.shape[1])]
    X = np.column_stack(cols)
    yy = demean(y)

    XtX_inv = np.linalg.pinv(X.T @ X)
    b = XtX_inv @ (X.T @ yy)
    if coef_only:
        # Phep hoan vi goi ham nay hang tram lan va chi can he so. Vong lap gom cum ben
        # duoi chay qua tung van bang Python, tot ~350 vong moi lan goi; bo qua no lam
        # phep hoan vi nhanh hon hai bac do lon.
        return float(b[0]), float("nan"), 0, len(y)
    e = yy - X @ b

    meat = np.zeros((X.shape[1], X.shape[1]))
    for j in range(len(uniq_g)):
        m = g_idx == j
        u = X[m].T @ e[m]
        meat += np.outer(u, u)
    n_g = len(uniq_g)
    # hieu chinh mau nho chuan cho cluster
    scale = n_g / max(n_g - 1, 1)
    V = XtX_inv @ meat @ XtX_inv * scale
    return float(b[0]), float(np.sqrt(V[0, 0])), n_g, len(y)


def perm_p(y, x, gid, rnd, seed=20260912, n=500, own=None, seat=None):
    """p hoan vi: thay chuoi hanh vi cua dong doi bang chuoi cua MOT VAN KHAC.

    Gia thuyet khong can kiem la: "dong gop cua toi khong lien quan toi hanh vi cua
    CHINH nhung nguoi cung ban toi". Nen phep hoan vi phai cat dung lien ket do va
    khong cat gi khac. Cach lam: giu nguyen y, nhan van, va so vong -- tuc giu nguyen
    ca cau truc hieu ung co dinh lan quy dao rieng cua tung ghe -- roi GAN LAI khoi x
    cua mot van khac cho van nay.

    Mot ban truoc cua ham nay xao nhan VAN thay vi xao x. Cach do chi doi cau truc hieu
    ung co dinh chu khong he cat lien ket x-y, nen no kiem mot gia thuyet khong rong
    tuech va luon cho p lon. Ghi lai o day vi loi nay khong lo ra qua bat ky assertion
    nao: no van chay, van in ra mot con so trong hinh dang cua mot p-value.
    """
    rng = np.random.default_rng(seed)

    def pool_of(xv):
        """Dung lai muc quy tu mot chuoi dong doi bat ky, theo dung dang thuc tren."""
        if own is None or seat is None:
            return None
        out = np.empty_like(xv)
        for key, idx in per_seat.items():
            out[idx] = own[idx] + 5 * np.cumsum(xv[idx])
        return out

    # nhom chi so theo (van, ghe) va sap theo vong: cumsum chi dung khi dung thu tu
    per_seat = defaultdict(list)
    for i in range(len(y)):
        per_seat[(gid[i], seat[i] if seat is not None else 0)].append(i)
    for key in per_seat:
        per_seat[key] = np.array(sorted(per_seat[key], key=lambda i: rnd[i]))

    b0, _, _, _ = twoway_fe_ols(y, x, gid, rnd, extra=pool_of(x))

    # gom chi so theo van, roi nhom cac van theo DO DAI khoi: chi hoan doi duoc giua
    # nhung van co cung so quan sat, neu khong x va y khong con xep hang duoc voi nhau.
    order = defaultdict(list)
    for i, g in enumerate(gid):
        order[g].append(i)
    by_len = defaultdict(list)
    for g, idx in order.items():
        by_len[len(idx)].append(g)

    hits = 0
    for _ in range(n):
        x_perm = np.empty_like(x)
        for L, games_L in by_len.items():
            if len(games_L) < 2:
                # khong co ban de doi -> giu nguyen; mot vai van le khong lam lech p
                for g in games_L:
                    x_perm[order[g]] = x[order[g]]
                continue
            src = rng.permutation(games_L)
            for dst, s in zip(games_L, src):
                x_perm[order[dst]] = x[order[s]]
        b, _, _, _ = twoway_fe_ols(y, x_perm, gid, rnd, coef_only=True,
                                   extra=pool_of(x_perm))
        if abs(b) >= abs(b0):
            hits += 1
    return (hits + 1) / (n + 1)


# ------------------------------------------------------------------ xuat tex ------
class Macros:
    """Gom `\newcommand`; chan dinh nghia trung ten (LaTeX nuot im lang cai sau)."""

    def __init__(self):
        self._seen = {}
        self._lines = []

    def add(self, name, value):
        if name in self._seen:
            raise SystemExit("macro trung ten: %s" % name)
        self._seen[name] = value
        self._lines.append(r"\newcommand{\%s}{%s}" % (name, value))

    def write(self, path):
        path.write_text("\n".join(self._lines) + "\n", encoding="utf-8")
        print("  ghi %s (%d macro)" % (path.relative_to(REPO), len(self._lines)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(RESULTS),
                    help="CHI de chay thu tren mot ban gom TUNG PHAN truoc khi wave xong. "
                         "Ban dung cho paper luon doc results/exp_mixed/.")
    ap.add_argument("--skip-audit", action="store_true",
                    help="CHI de chay thu khi wave chua xong (luc do can bang chua the "
                         "dung). Ban dung cho paper KHONG duoc dat co nay.")
    args = ap.parse_args()

    games = load_e3b(Path(args.src))
    print("E3b: %d van" % len(games))

    errs, present, seatgames = audit(games)
    if errs:
        print("\n".join("  !! " + e for e in errs[:10]))
        if not args.skip_audit:
            raise SystemExit("Cong kiem do. Dung lai truoc khi sinh bat cu con so nao.")
        print("  (--skip-audit: di tiep, CHI dung de chay thu)")

    M = Macros()
    M.add("EthreebGames", "%d" % len(games))
    M.add("EthreebSeatGames", "%d" % sum(seatgames.values()))
    # Thiet ke duoc SUY TU DATA, khong go tay: so cap model thuc co, so muc pha tron,
    # so muc rui ro, so lan lap. Neu mot ô chet thi cac con so nay tu giam theo va van
    # khop voi bang, thay vi mo ta mot thiet ke khong ton tai.
    pairs = {tuple(sorted(set(g["seats"]))) for g in games}
    mixes = {g["seats"].count(min(set(g["seats"]), key=lambda s: FULL[s])) for g in games}
    risks = {g["risk"] for g in games}
    reps = {g["rep"] for g in games}
    M.add("EthreebPairs", "%d" % len(pairs))
    M.add("EthreebMixtures", "%d" % len(mixes))
    M.add("EthreebRisks", "%d" % len(risks))
    M.add("EthreebReps", "%d" % len(reps))
    M.add("EthreebGamesPerModel", "%d" % min(present.values()))
    M.add("EthreebSeatGamesPerModel", "%d" % min(seatgames.values()))
    M.add("EthreebModels", "%d" % len(present))

    # ---- co di co lai -------------------------------------------------------
    print("\nPHAN UNG VOI DONG DOI (hieu ung co dinh van + vong, cluster theo van)")
    print("  Cot 'tho' khong khu muc quy; cot 'khu quy' co. Chenh lech giua hai cot la")
    print("  phan do BAM MUC TIEU chu khong phai phan ung voi nguoi.")
    print("  %-7s %17s %17s %7s %9s"
          % ("model", "tho", "khu quy", "van", "p hoan vi"))
    reciprocity = {}
    for m in ORDER:
        y, x, pot, own, gid, rnd, seat = panel_rows(games, m)
        b_raw, se_raw, n_g, n_obs = twoway_fe_ols(y, x, gid, rnd)
        b, se, _, _ = twoway_fe_ols(y, x, gid, rnd, extra=pot)
        tstat = b / se if se else float("nan")
        p = perm_p(y, x, gid, rnd, own=own, seat=seat)
        reciprocity[m] = (b, se, tstat, n_g, n_obs, p, b_raw, se_raw)
        print("  %-7s %8.3f (%.3f) %8.3f (%.3f) %7d %9.4f"
              % (m, b_raw, se_raw, b, se, n_g, p))
        M.add("Erecip%s" % m.capitalize(), "%.2f" % b)
        M.add("Erecip%sSE" % m.capitalize(), "%.2f" % se)
        M.add("Erecip%sRaw" % m.capitalize(), "%.2f" % b_raw)
        M.add("Erecip%sP" % m.capitalize(),
              ("<0.001" if p < 0.001 else "%.3f" % p))

    # Dem theo Y NGHIA, khong theo dau. Dau khong phai cau hoi: mot he so 0,08 tren tap
    # lua chon {0, 2, 4} nghia la dong doi gop them mot don vi thi model gop them tam
    # phan tram don vi, tuc khong phan ung. Nen tach ba nhom: khong phat hien duoc,
    # phat hien duoc nhung nho hon mot buoc, va du lon de thay trong hanh vi.
    ALPHA, STEP = 0.05, 0.25
    null = [m for m in ORDER if reciprocity[m][5] >= ALPHA]
    tiny = [m for m in ORDER
            if reciprocity[m][5] < ALPHA and abs(reciprocity[m][0]) < STEP]
    real = [m for m in ORDER
            if reciprocity[m][5] < ALPHA and abs(reciprocity[m][0]) >= STEP]
    M.add("ErecipNNull", "%d" % len(null))
    M.add("ErecipNTiny", "%d" % len(tiny))
    M.add("ErecipNReal", "%d" % len(real))
    M.add("ErecipNBlind", "%d" % (len(null) + len(tiny)))
    M.add("ErecipRealModels", ", ".join(PRETTY[m] for m in real) or "none")
    M.add("ErecipThreshold", "%.2f" % STEP)
    print("  khong phat hien duoc: %s" % ([PRETTY[m] for m in null] or "khong co"))
    print("  phat hien duoc nhung < %.2f buoc: %s"
          % (STEP, [PRETTY[m] for m in tiny] or "khong co"))
    print("  du lon de thay: %s" % ([PRETTY[m] for m in real] or "khong co"))

    # ---- thanh phan nhom ----------------------------------------------------
    print("\nTONG GOP MOI GHE THEO SO DONG LOAI TRONG NHOM")
    comp = defaultdict(lambda: defaultdict(list))
    for g in games:
        for m in set(g["seats"]):
            k = g["seats"].count(m)
            for i, s in enumerate(g["seats"]):
                if s == m:
                    comp[m][k].append(sum(g["moves"][i]))
    spans_all = {}
    print("  %-7s" % "model" + "".join("%8s" % ("k=%d" % k) for k in range(1, 6)) + "%10s" % "bien thien")
    for m in ORDER:
        vals = [np.mean(comp[m][k]) if comp[m][k] else np.nan for k in range(1, 6)]
        good = [v for v in vals if not np.isnan(v)]
        span = (max(good) - min(good)) if len(good) > 1 else float("nan")
        print("  %-7s" % m + "".join("%8.1f" % v for v in vals) + "%10.1f" % span)
        M.add("Ecomp%sSpan" % m.capitalize(), "%.1f" % span)
        spans_all[m] = span

    top = max(spans_all, key=lambda m: spans_all[m])
    rest = max((m for m in spans_all if m != top), key=lambda m: spans_all[m])
    M.add("EcompTopModel", PRETTY[top])
    M.add("EcompTopSpan", "%.1f" % spans_all[top])
    M.add("EcompNextSpan", "%.1f" % spans_all[rest])
    M.add("EcompRatio", "%.1f" % (spans_all[top] / max(spans_all[rest], 1e-9)))

    TABLES.mkdir(parents=True, exist_ok=True)
    M.write(TABLES / "e3b_numbers.tex")

    # ---- bang ---------------------------------------------------------------
    rows = []
    for m in ORDER:
        b, se, tstat, n_g, n_obs, p, b_raw, se_raw = reciprocity[m]
        rows.append(r"%s & $%.2f$ & $%.2f$ & $(%.2f)$ & %s \\" % (
            PRETTY[m], b_raw, b, se,
            ("$<$0.001" if p < 0.001 else "%.3f" % p)))
    (TABLES / "e3b_table_reciprocity.tex").write_text(
        "\n".join([
            "%% SINH TU DONG boi paper/AAMAS/analysis/e3b_analysis.py -- DUNG SUA TAY.",
            "%% Moi con so goi qua macro cua e3b_numbers.tex nen bang va van "
            "xuoi khong lech nhau.",
            "%% Can: \\usepackage{booktabs}",
            r"\begin{table}[t]", r"\centering", r"\small",
            # Cot acmart chi 241,15pt. Do that: o tabcolsep mac dinh 6pt, bang
            # phan ung tran 4,96pt va bang thanh phan tran 15,12pt. Dat trong
            # table env nen khong ro ri ra ngoai.
            r"\setlength{\tabcolsep}{2.5pt}%",
            r"\caption{How each model answers its partners. The slope is the change in "
            r"a seat's contribution in one round for a one unit change in the mean "
            r"contribution of the other five seats in the previous round. \emph{Raw} "
            r"compares within a game and within a round, which holds the catastrophe "
            r"probability, the pair and the mixture fixed. \emph{Net of pool} adds the "
            r"size of the pool, which removes the part of the association that is only "
            r"an agent steering toward the threshold. Contributions are chosen from 0, "
            r"2 or 4, so a slope well below one is small in behaviour as well as in "
            r"arithmetic. Standard errors treat one game as one unit; $p$ is a "
            r"permutation test that gives a game the partner history of another game.}",
            r"\label{tab:mixed-recip}",
            r"\begin{tabular}{lrrrr}", r"\toprule",
            r"Model & Raw & Net of pool & (SE) & $p$ \\", r"\midrule",
            *rows, r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]),
        encoding="utf-8")
    print("  ghi paper/AAMAS/tables/e3b_table_reciprocity.tex")

    comp_rows = []
    for m in ORDER:
        vals = [np.mean(comp[m][k]) if comp[m][k] else float("nan") for k in range(1, 6)]
        comp_rows.append(PRETTY[m] + " & " +
                         " & ".join("%.1f" % v for v in vals) + r" \\")
    (TABLES / "e3b_table_composition.tex").write_text(
        "\n".join([
            "%% SINH TU DONG boi paper/AAMAS/analysis/e3b_analysis.py -- DUNG SUA TAY.",
            "%% Moi con so goi qua macro cua e3b_numbers.tex nen bang va van "
            "xuoi khong lech nhau.",
            "%% Can: \\usepackage{booktabs}",
            r"\begin{table}[t]", r"\centering", r"\small",
            # Cot acmart chi 241,15pt. Do that: o tabcolsep mac dinh 6pt, bang
            # phan ung tran 4,96pt va bang thanh phan tran 15,12pt. Dat trong
            # table env nen khong ro ri ra ngoai.
            r"\setlength{\tabcolsep}{2.5pt}%",
            r"\caption{Mean contribution per seat over a whole game, against the number "
            r"of seats the model holds, given in the column headings. A seat can pay "
            r"at most 40 across the "
            r"game. A flat row means the company at the table does not change what the "
            r"model pays.}",
            r"\label{tab:mixed-comp}",
            r"\begin{tabular}{lrrrrr}", r"\toprule",
            r"Model & 1 & 2 & 3 & 4 & 5 \\",
            r"\midrule", *comp_rows, r"\bottomrule", r"\end{tabular}",
            r"\end{table}", ""]),
        encoding="utf-8")
    print("  ghi paper/AAMAS/tables/e3b_table_composition.tex")

    # KHONG sinh hinh. Hinh duy nhat co the ve o day la cac he so cua
    # tab:mixed-recip kem khoang tin cay, tuc trung noi dung voi mot bang da co.
    # Ghi chu ngan sach trang trong 06_bestresponse.tex da ghi bai hoc nay khi xoa
    # mot heatmap chua bao gio duoc \\input vi moi o cua no trung voi hai cot bang.
    return 0


if __name__ == "__main__":
    sys.exit(main())
