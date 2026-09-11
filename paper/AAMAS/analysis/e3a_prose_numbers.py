#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""E3a — các con số mà §P-5 cần NHƯNG `e3a_analysis.py` không sinh.

Chạy:  python paper/AAMAS/analysis/e3a_prose_numbers.py
Sinh ra:  paper/AAMAS/tables/e3a_prose_numbers.tex   (CHỈ \newcommand)

VÌ SAO TÁCH RA MỘT FILE RIÊNG THAY VÌ SỬA `e3a_numbers.tex`
    `e3a_numbers.tex` có dòng đầu ghi "SINH TỰ ĐỘNG — ĐỪNG SỬA TAY". Thêm macro vào đó
    bằng tay thì lần sau ai chạy lại `e3a_analysis.py` là bay sạch, và bản nháp paper sẽ
    hỏng với `Undefined control sequence` ở một chỗ không ai ngờ. Nên file này là file
    THỨ HAI, sinh độc lập, tiền tố macro là `\Ethreeax` (x = extra) để không bao giờ đụng
    tên với `\Ethreea` của file kia. Hai file input cạnh nhau trong preamble.

NÓ ĐỌC GÌ
    results/exp_bestresponse_{defect,carry,coop,cond}/   (1000 ván E3a)
    results/exp_baseline/{0.1,0.5,0.9}/                  (150 ván, 6 ghế đều LLM)
    results/exp_nohint/{0.1,0.5,0.9}/                    (150 ván, cùng template trừ
                                                         hai đoạn mỏ neo equal-split)
    results/exp_evprobe_probes.jsonl                     (4.500 câu hỏi hiểu luật)
    KHÔNG chạm `Legacy_Results/`. KHÔNG ghi gì vào `results/`.

BA ĐẠI LƯỢNG CHÍNH VÀ VÌ SAO CHÚNG ĐÁNG TIN HƠN "KHOẢNG CÁCH TỚI BEST RESPONSE"

1. LÃNG PHÍ SAU KHI ĐÃ CHỨNG MINH ĐƯỢC (`PostProof*`, chỉ profile `carry`).
   Phản biện nặng nhất nhắm vào cả mục này là: agent KHÔNG được cho biết 5 ghế kia là
   script tất định (`agent1_knows_opponent_with_prob=0`), nên chấm nó bằng best response
   tính từ tri thức đó là chấm bằng thông tin ta cố tình giấu nó. Đại lượng này miễn
   nhiễm với phản biện đó: prompt CÓ trả lại nguyên văn đóng góp từng ghế sau mỗi vòng
   ("Round r: P1(you)=.., P2=.."), nên khi tổng quỹ hiện trong lịch sử đã >= 120 thì mục
   tiêu đã đạt — KHÔNG một niềm tin nào về đối thủ cứu được một đồng đóng thêm sau đó.
   Ta chỉ đếm phần đóng góp ở các vòng SAU vòng chứng minh được, nên con số này không
   giả định gì về risk attitude lẫn về tri thức đối thủ.

   Bẫy: quỹ 120 gần như luôn đủ ở cuối vòng 6 (5 ghế x 4 x 6 = 120) chứ không phải vòng
   7 — nên vòng chứng minh tính THEO TỪNG VÁN từ lịch sử thật, không hardcode.

2. LUẬT VÒNG CUỐI (`LastZero*`). Đây là thứ biến một quan sát lẻ về qwen thành luận điểm
   multi-agent: cùng một heuristic "vòng chót thì thôi đóng" là VÔ HẠI ở `carry`/`defect`
   và làm HỎNG mục tiêu ở `coop`/`cond`. Đo bằng % ván chơi 0 ở vòng 10, tách theo profile.

3. MỎ NEO CÓ THẬT LÀ DO PROMPT KHÔNG (`Anchor*`). `exp_nohint` là đúng template baseline
   trừ hai span nêu equal-split. So vòng 1 của hai nhánh là phép thử trực tiếp. Kết quả
   KHÔNG như giả thuyết ban đầu: hai model đổi hẳn, ba model vẫn mở đúng 2. Script này
   in ra cả hai phía; phần văn xuôi phải nói đúng như thế chứ đừng nói gọn thành "đó là
   mỏ neo prompt".
   Bẫy: hai nhánh KHÔNG chạy cùng đợt (nhánh baseline nhập lại từ Legacy_Results, xem
   results/PROVENANCE.json), nên hiệu ứng batch không loại trừ được hoàn toàn.

KIỂM ĐỊNH: n = 10 ván/ô nên mọi p-value ở đây là permutation test, cụm theo VÁN (6 ghế
trong một ván không độc lập), không dùng t-test.
"""
from __future__ import annotations

import ast
import decimal
import pathlib
import sys
from typing import Dict, List

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):          # console Windows mặc định cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO = pathlib.Path(__file__).resolve().parents[3]
RESULTS = REPO / "results"
TABLES = REPO / "paper" / "AAMAS" / "tables"

N_ROUNDS = 10
N_PLAYERS = 6
TARGET = 120.0
ENDOWMENT = 40.0

# Giữ y hệt thứ tự và nhãn của e3a_analysis.py để hai file macro không mâu thuẫn nhau.
MODELS: Dict[str, str] = {
    "anthropic-claude-haiku-4-5-20251001": "Haiku",
    "google-gemini-3.5-flash-lite":        "Flash",
    "openai-gpt-5.6-luna":                 "Luna",
    "qwen-qwen3-235b-a22b-instruct-2507":  "Qwen",
    "xai-grok-4.20-0309-non-reasoning":    "Grok",
}
MODEL_ORDER = list(MODELS.values())

# --------------------------------------------------------------------------------------
# Tên model DÙNG TRONG VĂN XUÔI, tách khỏi khoá dùng để đặt tên macro.
#
# Khoá "Flash" phải giữ nguyên vì nó ghép thành tên macro (`\EthreeaMeanCarryFlash`) và
# tên macro LaTeX không nhận dấu gạch nối. Nhưng in "Flash" ra giữa một câu thì mơ hồ —
# panel có `gemini-3.5-flash-lite`, không phải `gemini-3.5-flash`. Nên mọi chuỗi ĐI VÀO
# VĂN XUÔI đi qua hàm này, còn tên macro thì không. Đừng hợp nhất hai thứ đó lại.
# --------------------------------------------------------------------------------------
PROSE_NAME = {"Flash": "Flash-Lite"}


def pname(m: str) -> str:
    return PROSE_NAME.get(m, m)

PROFILES = ("defect", "carry", "coop", "cond")
PROFILE_MACRO = {"defect": "Defect", "carry": "Carry", "coop": "Coop", "cond": "Cond"}
ROUND_WORD = ["Rone", "Rtwo", "Rthree", "Rfour", "Rfive",
              "Rsix", "Rseven", "Reight", "Rnine", "Rten"]

ANCHOR_RISKS = (0.1, 0.5, 0.9)      # lưới chung của exp_nohint; baseline cắt xuống cho khớp
PERM_N = 10_000
PERM_SEED = 20260913


# ======================================================================================
# Bộ gom macro — chống trùng tên, vì trùng tên trong LaTeX là `\newcommand` lỗi cứng.
# ======================================================================================
class Macros:
    def __init__(self) -> None:
        self._d: Dict[str, str] = {}

    def add(self, name: str, value: str) -> None:
        key = "Ethreeax" + name
        if key in self._d and self._d[key] != value:
            raise SystemExit("macro trung ten voi gia tri khac: " + key)
        self._d[key] = value

    def num(self, name: str, value: float, nd: int = 2) -> None:
        """Làm tròn NỬA RA XA SỐ 0, không dùng "%.*f".

        Cùng lý do và cùng quy ước với `Macros.num` của `e3a_analysis.py` (xem docstring
        dài ở đó): định dạng mặc định của Python làm tròn nửa-CHẴN, nên 17,5 ra "18" còn
        48,5 ra "48" — hai hướng khác nhau trong cùng một bảng phần trăm, và hướng đi
        xuống trông y như lỗi cắt cụt. Hai file phải làm tròn giống nhau, nếu không hai
        khối macro đặt cạnh nhau trong cùng một câu sẽ lệch nhau ở chữ số cuối.
        """
        q = decimal.Decimal(repr(float(value))).quantize(
            decimal.Decimal(1).scaleb(-nd), rounding=decimal.ROUND_HALF_UP)
        if q == 0:                      # chặn "-0.0" lọt vào bảng
            q = abs(q)
        self.add(name, format(q, "f"))

    def dump(self, path: pathlib.Path, header: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(header)
            for k in self._d:
                fh.write("\\newcommand{\\%s}{%s}\n" % (k, self._d[k]))
        print("  -> %s  (%d macro)" % (path.relative_to(REPO), len(self._d)))


def load_experiment(name: str) -> pd.DataFrame:
    """Đọc wide CSV theo layout đã chốt: <experiment>/<p>/<model_tag>/p<p>_<lang>_<tag>.csv.

    Mức risk lấy từ TÊN THƯ MỤC chứ không từ cột `risk_probability`: tên thư mục là thứ
    loader chính thức dùng (DATA_CARD §2) và là thứ verify_wide.py canh.
    """
    files = sorted((RESULTS / name).glob("*/*/*.csv"))
    if not files:
        raise SystemExit("khong thay van nao trong results/%s/" % name)
    frames = []
    for f in files:
        df = pd.read_csv(f)
        df["_risk"] = float(f.parent.parent.name)
        df["_tag"] = f.parent.name
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def seat_moves(row: pd.Series, seat: int) -> List[int]:
    """Chuỗi 10 nước đi của một ghế. `agent{i}_strategies` là chuỗi "[2, 2, 0, ...]"."""
    moves = ast.literal_eval(row["agent%d_strategies" % seat])
    if len(moves) != N_ROUNDS:
        raise SystemExit("van %s ghe %d: %d vong, cho %d"
                         % (row["game_id"], seat, len(moves), N_ROUNDS))
    return [int(m) for m in moves]


# ======================================================================================
# 1. E3a — quỹ đạo theo vòng, lãng phí sau khi chứng minh được, luật vòng cuối
# ======================================================================================
def build_e3a() -> pd.DataFrame:
    rows = []
    for prof in PROFILES:
        df = load_experiment("exp_bestresponse_" + prof)
        for _, r in df.iterrows():
            if r["agent1_llm"] != r["_tag"]:
                raise SystemExit("%s: ghe 1 khong phai model cua thu muc" % r["game_id"])
            llm = seat_moves(r, 1)
            table = [seat_moves(r, s) for s in range(1, N_PLAYERS + 1)]
            pot = np.cumsum([sum(seat[t] for seat in table) for t in range(N_ROUNDS)])

            # Vòng chứng minh được = vòng đầu tiên mà quỹ HIỆN TRONG LỊCH SỬ đã >= target.
            # Từ vòng kế tiếp trở đi, mọi đồng đóng thêm là mất trắng dưới MỌI niềm tin về
            # đối thủ — đây là chỗ đại lượng này mạnh hơn "khoảng cách tới best response".
            proof = next((t + 1 for t in range(N_ROUNDS) if pot[t] >= TARGET), None)
            post = sum(llm[t] for t in range(N_ROUNDS)
                       if proof is not None and t + 1 > proof)

            row = {
                "profile": prof,
                "model": MODELS[r["agent1_llm"]],
                "risk": r["_risk"],
                "game_id": r["game_id"],
                "total": sum(llm),
                "proof_round": proof,
                "post_proof": post,
                "last_zero": int(llm[-1] == 0),
            }
            for t in range(N_ROUNDS):
                row["rd%d" % (t + 1)] = llm[t]
            rows.append(row)
    out = pd.DataFrame(rows)
    if len(out) != 1000:
        raise SystemExit("E3a phai co 1000 van, doc duoc %d" % len(out))
    return out


def emit_e3a(mac: Macros, e3a: pd.DataFrame) -> None:
    mac.add("SeatsLLM", "1")
    mac.add("SeatsScripted", "5")
    mac.add("CallsPerGame", str(N_ROUNDS))
    mac.add("CallsSelfPlay", str(N_ROUNDS * N_PLAYERS))
    mac.add("CallSaving", str(N_PLAYERS))
    mac.add("PermN", "10{,}000")
    mac.add("CellN", "10")

    # --- quỹ đạo theo vòng, hai profile mà best response = 0 ở MỌI vòng -----------------
    for prof in ("defect", "carry"):
        sub = e3a[e3a.profile == prof]
        for model in MODEL_ORDER:
            s = sub[sub.model == model]
            for t, word in enumerate(ROUND_WORD, start=1):
                mac.num("Rd%s%s%s" % (PROFILE_MACRO[prof], model, word),
                        float(s["rd%d" % t].mean()))
            # "Vòng bỏ cuộc": vòng đầu tiên mà trung bình tụt xuống dưới 1 đơn vị. Không
            # phải một test, chỉ là cách đọc bảng quỹ đạo thành MỘT con số cho văn xuôi.
            quit_round = None
            for t in range(1, N_ROUNDS + 1):
                if float(s["rd%d" % t].mean()) < 1.0:
                    quit_round = t
                    break
            mac.add("Quit%s%s" % (PROFILE_MACRO[prof], model),
                    "--" if quit_round is None else str(quit_round))

    # Model nao CHIU DIEU CHINH nhung cham nhat, va la nhung model nao. Can macro rieng vi
    # hai model co the trung so: viet "rounds 7 and 7" trong paper doc nhu mot cai bug.
    # Gom lai thanh MOT vong + danh sach ten thi dung voi moi lo data ve sau.
    # Chi tinh model THUC SU dieu chinh giua ván: bo qua model chi tut xuong dung o vong
    # CHOT (Qwen), vi do la luat vong cuoi chu khong phai hoc tu phan hoi — gop chung vao
    # se lam cau "cham nhat la vong 10" sai ve ban chat.
    carry_quit = {}
    for model in MODEL_ORDER:
        s = e3a[(e3a.profile == "carry") & (e3a.model == model)]
        for t in range(1, N_ROUNDS):
            if float(s["rd%d" % t].mean()) < 1.0:
                carry_quit[model] = t
                break
    if carry_quit:
        late = max(carry_quit.values())
        names = [m for m in MODEL_ORDER if carry_quit.get(m) == late]
        mac.add("QuitCarryLate", str(late))
        mac.add("QuitCarryLateModels",
                (", ".join(map(pname, names[:-1])) + " and " + pname(names[-1]))
                if len(names) > 1 else pname(names[0]))
        mac.add("QuitCarryLateN", str(len(names)))

    # --- lãng phí sau khi chứng minh được (chỉ `carry` có chứng minh) -------------------
    carry = e3a[e3a.profile == "carry"]
    modal = int(carry.proof_round.mode().iloc[0])
    mac.add("ProofRoundModal", str(modal))
    mac.add("ProofRoundModalN", str(int((carry.proof_round == modal).sum())))
    mac.add("ProofGames", str(len(carry)))
    mac.num("PostProofAll", float(carry.post_proof.mean()))
    mac.num("PostProofAllContrib", float(carry.total.mean()))
    mac.num("PostProofAllPct", 100.0 * carry.post_proof.mean() / carry.total.mean(), 1)
    for model in MODEL_ORDER:
        s = carry[carry.model == model]
        mac.num("PostProof" + model, float(s.post_proof.mean()))
        mac.num("PostProofPct" + model, 100.0 * s.post_proof.mean() / s.total.mean(), 1)
        mac.num("PostProofClean" + model, 100.0 * float((s.post_proof == 0).mean()), 0)
    mac.add("PostProofWorstModel", str(carry.groupby("model").post_proof.mean().idxmax()))

    # `defect` KHÔNG có đại lượng tương ứng và đó là điều phải nói rõ: lịch sử không bao
    # giờ chứng minh được mục tiêu BẤT KHẢ THI (quỹ tối đa còn lại luôn đủ lớn về mặt số
    # học), nên ở đó chỉ còn lập luận trội — vốn cần giả định biết đối thủ.
    if e3a[e3a.profile == "defect"].proof_round.notna().any():
        raise SystemExit("bat ngo: co van `defect` dat target -- kiem lai du lieu")

    # --- luật vòng cuối ----------------------------------------------------------------
    for prof in PROFILES:
        sub = e3a[e3a.profile == prof]
        for model in MODEL_ORDER:
            s = sub[sub.model == model]
            mac.num("LastZero%s%s" % (PROFILE_MACRO[prof], model),
                    100.0 * float(s.last_zero.mean()), 0)
            mac.num("LastMean%s%s" % (PROFILE_MACRO[prof], model), float(s.rd10.mean()))
    # Model nào áp luật vòng cuối VÔ ĐIỀU KIỆN (cả 4 profile đều >= 95% ván chơi 0)?
    uncond = []
    for m in MODEL_ORDER:
        shares = [100.0 * e3a[(e3a.profile == p) & (e3a.model == m)].last_zero.mean()
                  for p in PROFILES]
        if all(v >= 95.0 for v in shares):
            uncond.append(m)
    mac.add("LastZeroUncondN", str(len(uncond)))
    mac.add("LastZeroUncondModels", ", ".join(map(pname, uncond)))
    # Mat kia cua cung mot phat hien: model nao RUT LUI KHI RUT LUI LA MIEN PHI, tuc la
    # choi 0 o vong chot trong 100% van cua CA HAI profile ma dong gop bi troi chat. Van
    # xuoi truoc day go tay "100%" cho nhom nay — con so do la ket qua do duoc, phai la
    # macro, va nhom thanh vien cung vay (Qwen chi 98% o `defect` nen KHONG thuoc nhom).
    free = [m for m in MODEL_ORDER
            if all(float(e3a[(e3a.profile == p) & (e3a.model == m)].last_zero.mean()) == 1.0
                   for p in ("defect", "carry"))]
    if not free:
        raise SystemExit("khong model nao rut lui 100% o ca defect lan carry -- sua van xuoi")
    mac.add("LastZeroFreeN", str(len(free)))
    mac.add("LastZeroFreeModels",
            (", ".join(map(pname, free[:-1])) + " and " + pname(free[-1]))
            if len(free) > 1 else pname(free[0]))
    mac.num("LastZeroFreeShare", 100.0, 0)

    # --- kiểm chứng lại cách diễn giải "bị bóc lột" -------------------------------------
    # Ở `defect` 5 ghế script giữ nguyên 40 còn ghế LLM giữ 40 - c, và target không bao giờ
    # đạt nên cả sáu ghế cùng chịu một xổ số. Vậy khoảng cách thu nhập giữa một ghế KHÔNG
    # LÀM GÌ CẢ và ghế LLM đúng bằng c*(1-p) — tức đúng cột `Forfeited` mà e3a_analysis.py
    # đã in. In ra để đối chiếu; văn xuôi dùng lại \EthreeaLossDefect<Model>, không đẻ số mới.
    dfc = e3a[e3a.profile == "defect"]
    print("  kiem: boc lot o `defect` = c*(1-p), phai trung \\EthreeaLossDefect<Model>")
    for model in MODEL_ORDER:
        s = dfc[dfc.model == model]
        print("      %-6s %6.2f" % (model, float((s.total * (1.0 - s.risk)).mean())))


# ======================================================================================
# 2. Mỏ neo: exp_baseline vs exp_nohint ở vòng 1
# ======================================================================================
def round_one_table(experiment: str) -> pd.DataFrame:
    """Một dòng = một QUYẾT ĐỊNH vòng 1 (6 ghế LLM mỗi ván), kèm khoá ván để cụm."""
    df = load_experiment(experiment)
    df = df[df._risk.isin(ANCHOR_RISKS)]
    rows = []
    for _, r in df.iterrows():
        for seat in range(1, N_PLAYERS + 1):
            if str(r["agent%d_llm" % seat]) not in MODELS:
                raise SystemExit("%s: ghe %d khong phai model cua panel" % (r["game_id"], seat))
            rows.append({"model": MODELS[r["_tag"]], "game_id": r["game_id"],
                         "risk": r["_risk"], "move": seat_moves(r, seat)[0]})
    return pd.DataFrame(rows)


def perm_pvalue(base: np.ndarray, treat: np.ndarray, rng: np.random.Generator) -> float:
    """Permutation test hai phía trên hiệu trung bình, đơn vị hoán vị = VÁN.

    Vì sao không t-test: mỗi ô chỉ 10 ván, và 6 ghế trong một ván chia chung lịch sử nên
    không độc lập. Ta gộp mỗi ván thành MỘT số (trung bình vòng 1 của 6 ghế) rồi hoán vị
    nhãn nhánh giữa các ván — đúng đơn vị ngẫu nhiên hoá của thiết kế.
    """
    obs = abs(treat.mean() - base.mean())
    pool = np.concatenate([base, treat])
    n_b = len(base)
    hits = 0
    for _ in range(PERM_N):
        rng.shuffle(pool)
        if abs(pool[n_b:].mean() - pool[:n_b].mean()) >= obs - 1e-12:
            hits += 1
    return (hits + 1.0) / (PERM_N + 1.0)


def emit_anchor(mac: Macros) -> None:
    base = round_one_table("exp_baseline")
    nohint = round_one_table("exp_nohint")
    mac.add("AnchorRisks", ", ".join("%g" % p for p in ANCHOR_RISKS))
    mac.add("AnchorGames", str(base.game_id.nunique()))
    mac.add("AnchorDec", str(len(base)))
    if base.game_id.nunique() != nohint.game_id.nunique():
        raise SystemExit("hai nhanh lech so van -- phep so vong 1 se khong can")

    rng = np.random.default_rng(PERM_SEED)
    for arm, tbl in (("Base", base), ("Nohint", nohint)):
        mac.num("Anchor%sMeanAll" % arm, float(tbl.move.mean()))
        mac.num("Anchor%sShareAll" % arm, 100.0 * float((tbl.move == 2).mean()), 1)
        for model in MODEL_ORDER:
            s = tbl[tbl.model == model]
            mac.num("Anchor%sMean%s" % (arm, model), float(s.move.mean()))
            mac.num("Anchor%sShare%s" % (arm, model), 100.0 * float((s.move == 2).mean()), 0)

    # p nhỏ nhất mà phép thử này CÓ THỂ trả về là 1/(PERM_N+1); in "0.000" ở đó là nói dối
    # về độ phân giải, nên chặn lại thành "<0.001" — đúng quy ước của permutation test.
    def pfmt(p: float) -> str:
        return "$<$0.001" if p < 0.001 else "%.3f" % p

    moved, stayed, stayed_p = [], [], []
    for model in MODEL_ORDER:
        b = base[base.model == model].groupby("game_id").move.mean().to_numpy()
        t = nohint[nohint.model == model].groupby("game_id").move.mean().to_numpy()
        p = perm_pvalue(b.copy(), t.copy(), rng)
        mac.add("AnchorP" + model, pfmt(p))
        mac.num("AnchorDelta" + model, float(t.mean() - b.mean()))
        if p < 0.05:
            moved.append(model)
        else:
            stayed.append(model)
            stayed_p.append(p)
    # Văn xuôi cần MỘT con số để nói "ba model kia không nhúc nhích": con số đúng là p NHỎ
    # NHẤT trong ba, vì nó chặn trên cả ba. Tính ở đây chứ đừng gõ tay một ngưỡng.
    mac.add("AnchorPStayedMin", pfmt(min(stayed_p)) if stayed_p else "--")
    mac.add("AnchorMovedN", str(len(moved)))
    mac.add("AnchorMovedModels",
            " and ".join(map(pname, moved)) if len(moved) <= 2
            else ", ".join(map(pname, moved)))
    mac.add("AnchorStayedN", str(len(stayed)))
    mac.add("AnchorStayedModels",
            (", ".join(map(pname, stayed[:-1])) + " and " + pname(stayed[-1]))
            if len(stayed) > 1 else "".join(map(pname, stayed)))


# ======================================================================================
# 3. Tham chiếu chéo: probe hiểu luật của E2 (chỉ dùng MỘT câu trong §P-5)
# ======================================================================================
def emit_probes(mac: Macros) -> None:
    pr = pd.read_json(RESULTS / "exp_evprobe_probes.jsonl", lines=True)
    mac.add("ProbeN", "{:,}".format(len(pr)).replace(",", "{,}"))
    for cat, name in (("rules", "Rules"), ("value", "Value")):
        mac.num("Probe" + name, 100.0 * float(pr[pr.category == cat].correct.mean()), 1)
    mac.num("ProbeCompare",
            100.0 * float(pr[pr.question_id == "value_compare"].correct.mean()), 1)


# ======================================================================================
# 4. Hằng số có nguồn gốc là BẢN GHI ĐO, không tính lại được từ `results/`
# ======================================================================================
def emit_recorded_constants(mac: Macros) -> None:
    """Phép đo tái lập theo seed, ghi ở CLAUDE.md (10-09-2026).

    KHÔNG tính lại được từ `results/` vì lô dữ liệu cũ đã bị thay bằng lô chạy lại — đúng
    cái làm nên phép đo. Để ở đây, tách khỏi mọi macro tính từ dữ liệu, để người đọc file
    này thấy ngay nó thuộc loại khác. Nếu chạy lại phép đo thì sửa ở đây.
    """
    mac.add("ReproModel", "Qwen3-235B")
    mac.add("ReproCells", "54")
    mac.add("ReproDiff", "31")
    mac.add("ReproPct", "57")


HEADER = """% ==================================================================
% SINH TU DONG boi paper/AAMAS/analysis/e3a_prose_numbers.py -- DUNG SUA TAY.
% Chay lai: python paper/AAMAS/analysis/e3a_prose_numbers.py
%
% File macro THU HAI cua muc P-5. File thu nhat la tables/e3a_numbers.tex (tien to
% \\Ethreea); file nay dung tien to \\Ethreeax de khong bao gio dung ten voi no.
% Ca hai chi chua \\newcommand nen \\input duoc ngay trong preamble.
%
% Nguon: results/exp_bestresponse_*/ . results/exp_baseline/ . results/exp_nohint/
%        . results/exp_evprobe_probes.jsonl
% ==================================================================
"""


def main() -> None:
    print("E3a -- macro bo sung cho phan van xuoi")
    mac = Macros()
    emit_e3a(mac, build_e3a())
    emit_anchor(mac)
    emit_probes(mac)
    emit_recorded_constants(mac)
    mac.dump(TABLES / "e3a_prose_numbers.tex", HEADER)


if __name__ == "__main__":
    main()
