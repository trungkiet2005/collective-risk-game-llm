"""Cổng cân bằng của `verify_wide.py` phải đếm theo GHẾ khi bàn là hỗn hợp (E3b).

Bản đầu đếm theo **tên thư mục**. Với bàn đồng nhất tên thư mục chính là model nên đếm thế
là đúng; với E3b thì sai hẳn, vì một ván của cặp (A, B) nằm trong `mix__A__B__k3` nên mỗi
cấu hình ghế hoá thành một "model" riêng — cổng đi so `k1` với `k2` của cùng một cặp thay
vì so model A với model B, và xanh trong khi thiếu hẳn một model.

Hai phép đếm được kiểm ở đây bắt hai loại lỗi KHÁC NHAU, nên phải giữ cả hai:

* **đếm-ván** (model giữ ≥ 1 ghế thì tính là có mặt) bắt "thiếu hẳn một cặp";
* **đếm-ghế-ván** (cộng dồn số ghế) bắt "thiếu một mức k" — xem
  :func:`test_hon_hop_lech_ghe_van_thi_do`, nơi đếm-ván của cả 5 model đều bằng nhau mà
  cán ghế vẫn lệch. Đó đúng là ca mà một cổng đếm-ván đơn độc sẽ cho qua.

Ván trong test được SINH chứ không copy từ `results/`: test hồi quy không được phụ thuộc
vào cây kết quả thật (nó đổi mỗi lần gom shard, và test phải chạy được cả khi cây đó trống).
"""
from __future__ import annotations

import csv
import importlib.util
import itertools
import pathlib
import sys

import pytest

from crsd.dataio.wide_csv import PANEL_TAGS, wide_fieldnames

REPO = pathlib.Path(__file__).resolve().parents[2]

# Tên model ngắn có CHỦ Ý. Tag thật dài ~43 ký tự nên `mix__<A>__<B>__k1` lặp lại trong cả
# tên thư mục lẫn tên file đẩy đường dẫn vượt giới hạn 260 ký tự của Windows khi nằm dưới
# tmp_path của pytest — dựng cây gãy giữa chừng vì FileNotFoundError chứ không vì lỗi logic.
# (Đã vấp đúng lỗi này lúc dựng cây giả thủ công.) Cổng cân bằng không quan tâm tên dài hay
# ngắn; thứ nó cần chỉ là thứ tự từ điển, và m-a < m-b < ... giữ đúng thứ tự đó.
MODELS = ["m-a", "m-b", "m-c", "m-d", "m-e"]
RISKS = ["0.1", "0.3"]
SCRIPTED = "scripted:always_0"


@pytest.fixture(scope="module")
def verify_wide():
    """Nạp `plan/scripts/verify_wide.py` như module — nó là script, không phải package."""
    path = REPO / "plan" / "scripts" / "verify_wide.py"
    spec = importlib.util.spec_from_file_location("verify_wide_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(verify_wide, tree, *extra) -> int:
    """Gọi main() với argv giả, trả mã thoát.

    Tự thêm `--panel any` khi lời gọi không tự nói gì về panel. Lý do: file này kiểm
    **cổng cân bằng**, và nó dựng cây giả bằng tag bịa (`m-a`…`m-e`) cho dễ đọc. Hai cổng
    panel — "phải có đủ 5 model thật" và "mọi tag phải thuộc panel" — sẽ đỏ trên mọi cây
    như vậy, và khi đó test cân bằng không còn kiểm được cái nó định kiểm nữa.

    Hai cổng panel có test riêng ở cuối file, dùng tag panel THẬT. Đừng gộp hai nhóm lại:
    tắt panel ở đây là để cô lập phép kiểm, không phải để né nó.
    """
    if not any(str(a) == "--panel" for a in extra):
        extra = (*extra, "--panel", "any")
    argv = ["verify_wide.py", "--wide", str(tree), *extra]
    old, sys.argv = sys.argv, argv
    try:
        return verify_wide.main()
    finally:
        sys.argv = old


def make_row(risk: str, rep: int, seats: list) -> dict:
    """Một ván hợp lệ: 6 ghế đóng 2/vòng × 10 vòng = đúng target 120, không thảm hoạ.

    Mọi bất biến khác mà `verify_wide` kiểm (pot = cumsum, tài khoản riêng không tăng,
    payoff = số dư cuối, tổng 6 ghế = group) đều thoả, nên test chỉ còn phụ thuộc vào
    đúng thứ đang kiểm là cổng cân bằng.
    """
    n_rounds, contrib, endow = 10, 2, 40.0
    group = [contrib * len(seats)] * n_rounds
    pot = list(itertools.accumulate(group))
    scores = [endow - contrib * (r + 1) for r in range(n_rounds)]
    row = {
        "game_id": f"g_{risk}_{rep}", "experiment": "exp_x", "language": "en", "rep": rep,
        "seed": 1000 + rep, "persona_set": "", "persona_seats": "",
        "memory_mode": "full_history", "opponent_profile": "", "framing": 0,
        "risk_framing": "lottery", "show_computed_totals": 0,
        "n_players": len(seats), "endowment": endow, "contribution_options": repr([contrib]),
        "target": 120.0, "risk_probability": float(risk), "n_rounds_is_known": True,
        "max_rounds": n_rounds, "played_rounds": n_rounds, "agents_communicate": False,
        "group_contributions": repr(group), "pot_cumulative": repr(pot),
        "group_total": float(pot[-1]), "target_reached": 1, "catastrophe": 0,
        "mean_payoff": scores[-1], "n_parse_failures": 0,
    }
    for i, llm in enumerate(seats, 1):
        row.update({
            f"agent{i}_name": f"player_{i}", f"agent{i}_llm": llm,
            f"agent{i}_personality": "", f"agent{i}_knows_opponent_with_prob": 0,
            f"agent{i}_strategies": repr([contrib] * n_rounds),
            f"agent{i}_scores": repr(scores), f"agent{i}_messages": "[]",
            f"agent{i}_payoff": scores[-1], f"agent{i}_parse_failures": 0,
        })
    return row


def write_cell(root: pathlib.Path, exp: str, risk: str, tag: str, seats: list, n_reps=10):
    """Ghi một ô `<exp>/<risk>/<tag>/p<risk>_en_<tag>.csv` với n_reps ván cùng cấu hình ghế."""
    d = root / exp / risk / tag
    d.mkdir(parents=True, exist_ok=True)
    with (d / f"p{risk}_en_{tag}.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=wide_fieldnames())
        w.writeheader()
        for rep in range(n_reps):
            w.writerow(make_row(risk, rep, seats))


def mix_tag(a: str, b: str, k: int) -> str:
    return f"mix__{a}__{b}__k{k}"


def build_homogeneous(root: pathlib.Path, exp="exp_homog", drop=None):
    """Bàn đồng nhất: 5 model × 2 risk × 10 rep. `drop` = model bị thiếu một ô."""
    for risk in RISKS:
        for m in MODELS:
            if drop == (risk, m):
                continue
            write_cell(root, exp, risk, m, [m] * 6)


def build_mixed(root: pathlib.Path, exp="exp_mixed", mode="balanced"):
    """Round-robin C(5,2) cặp × k = 1..5 × 2 risk × 10 rep.

    Thiết kế đủ cho **mỗi** model: 4 cặp × 5 mức k × 2 risk × 10 rep = 400 ván có mặt, và
    4 × 15 × 2 × 10 = 1200 ghế-ván (tổng k qua k = 1..5 bằng 15, và tổng 6−k cũng bằng 15,
    nên hai vai trong một cặp đối xứng — đó là lý do K5 cho ra con số bằng nhau).

    * ``drop_pair`` — mất hẳn một cặp: lệch CẢ hai phép đếm.
    * ``seat_skew`` — bỏ k=1 ở risk đầu rồi bù 10 ván vào k=5 ở risk sau. Số ván có mặt
      của hai model trong cặp không đổi (mất 10, được 10) nên **đếm-ván vẫn xanh**; nhưng
      cán ghế dịch 40 ghế từ model này sang model kia nên **đếm-ghế-ván phải đỏ**.
    """
    victim = tuple(sorted(MODELS[:2]))
    for risk in RISKS:
        for a, b in (tuple(sorted(p)) for p in itertools.combinations(MODELS, 2)):
            for k in range(1, 6):
                n = 10
                if (a, b) == victim:
                    if mode == "drop_pair":
                        continue
                    if mode == "seat_skew":
                        if risk == RISKS[0] and k == 1:
                            continue
                        if risk == RISKS[1] and k == 5:
                            n = 20
                write_cell(root, exp, risk, mix_tag(a, b, k), [a] * k + [b] * (6 - k), n)


def test_dong_nhat_van_xanh(verify_wide, tmp_path, capsys):
    """Không được làm hỏng đường đang chạy: bàn đồng nhất vẫn in đúng dòng cũ."""
    build_homogeneous(tmp_path)
    assert run(verify_wide, tmp_path, "--expect-reps", "10") == 0
    assert "5 model x 20 van" in capsys.readouterr().out


def test_e3a_mot_ghe_llm_nam_ghe_con_lai_scripted_van_xanh(verify_wide, tmp_path):
    """E3a (1 ghế LLM + 5 ghế robot) phải rơi vào nhánh ĐỒNG NHẤT, không thành 'hỗn hợp'.

    Ghế `scripted:` bị loại trước khi đếm, nên tập model còn lại có đúng 1 phần tử. Nếu
    một ngày nào đó robot bị tính là model, cả E3a sẽ bị đặt tên `mix__` và cổng đổi nhánh
    — test này là cái chuông báo.
    """
    for risk in RISKS:
        for m in MODELS:
            write_cell(tmp_path, "exp_e3a", risk, m, [m] + [SCRIPTED] * 5)
    assert run(verify_wide, tmp_path, "--expect-reps", "10") == 0


def test_dong_nhat_lech_van_do(verify_wide, tmp_path, capsys):
    build_homogeneous(tmp_path, drop=(RISKS[0], MODELS[0]))
    assert run(verify_wide, tmp_path) == 1
    assert "CONG CAN BANG" in capsys.readouterr().err


def test_hon_hop_can_bang_xanh(verify_wide, tmp_path, capsys):
    build_mixed(tmp_path)
    assert run(verify_wide, tmp_path, "--expect-reps", "10") == 0
    out = capsys.readouterr().out
    # Mỗi model phải được in ra bằng CHÍNH tên nó, kèm cả hai phép đếm.
    for m in MODELS:
        assert f"{m:<44} {400:>6} van co mat  {1200:>6} ghe-van" in out


def test_hon_hop_lech_van_thi_do(verify_wide, tmp_path, capsys):
    """Mất hẳn một cặp -> đỏ, và thông báo phải NÊU TÊN model nào lệch."""
    build_mixed(tmp_path, mode="drop_pair")
    assert run(verify_wide, tmp_path) == 1
    err = capsys.readouterr().err
    assert "VAN CO MAT lech" in err
    assert f"'{MODELS[0]}': 300" in err and f"'{MODELS[2]}': 400" in err


def test_hon_hop_lech_ghe_van_thi_do(verify_wide, tmp_path, capsys):
    """Ca quan trọng nhất: đếm-ván xanh tuyệt đối mà cán ghế vẫn lệch.

    Nếu cổng chỉ đếm ván (hay tệ hơn, chỉ đếm tên thư mục) thì lô này lọt. Chính vì thế
    phép đếm ghế-ván tồn tại.
    """
    build_mixed(tmp_path, mode="seat_skew")
    assert run(verify_wide, tmp_path) == 1
    err = capsys.readouterr().err
    assert "GHE-VAN lech" in err
    assert "VAN CO MAT lech" not in err          # đếm-ván KHÔNG bắt được ca này
    assert f"'{MODELS[0]}': 1240" in err and f"'{MODELS[1]}': 1160" in err


def test_ten_thu_muc_khong_khop_cau_hinh_ghe_thi_do(verify_wide, tmp_path, capsys):
    """Thư mục ghi k=1 nhưng hàng bên trong là k=2 -> phải đỏ.

    Đây là lỗ hổng của bản cũ: nó chỉ so `agent1_llm` với tên thư mục rồi **bỏ qua hẳn**
    khi tên chứa "mix__", nên cả lớp bàn hỗn hợp không được kiểm tên. Ở đây `agent1_llm`
    vẫn đúng là model A, chỉ có số ghế sai — đúng thứ mà phép so cũ không thấy.
    """
    a, b = sorted(MODELS[:2])
    write_cell(tmp_path, "exp_mixed", "0.1", mix_tag(a, b, 1), [a] * 2 + [b] * 4)
    assert run(verify_wide, tmp_path) == 1
    assert "ten suy tu 6 ghe" in capsys.readouterr().err


def test_ba_model_trong_mot_van_thi_do(verify_wide, tmp_path, capsys):
    """3 model/ván là cấu hình ghế sai — phải báo, không được đoán một cái tên."""
    a, b, c = sorted(MODELS[:3])
    write_cell(tmp_path, "exp_mixed", "0.1", mix_tag(a, b, 2), [a] * 2 + [b] * 2 + [c] * 2)
    assert run(verify_wide, tmp_path) == 1
    assert "khong dat duoc ten tu 6 ghe" in capsys.readouterr().err


# `run()` tự thêm `--panel any`, nên ba test dưới phải TỰ khai báo panel thật, nếu không
# chúng lại vô hiệu hoá đúng cái cổng mình đang kiểm.
PANEL_ARG = ",".join(sorted(PANEL_TAGS))


# --- Hai cổng PANEL ------------------------------------------------------------------
#
# Chúng bắt hai lỗi mà mọi phép kiểm nội bộ đều chịu thua, nên chúng dùng tag panel THẬT
# (`PANEL_TAGS`) chứ không dùng `m-a`…`m-e` như phần trên, và chúng KHÔNG được chạy qua
# `--panel any`.

def test_thieu_han_mot_model_thi_do(verify_wide, tmp_path, capsys):
    """Một model biến mất hẳn khỏi experiment phải ĐỎ, dù 4 model còn lại cân bằng.

    Đây chính là ca mà cổng cân bằng mù: nó chỉ so những model CÓ MẶT với nhau. Shard của
    một model chết sạch thì model đó không xuất hiện, bốn model kia vẫn bằng nhau, và cổng
    in ra "4 model x N van — can bang OK" rồi exit 0. Đo bằng cách gài lỗi 11-09-2026 trên
    `exp_nohint` thật: xoá hẳn `openai-gpt-5.6-luna` vẫn qua được cổng.
    """
    panel = sorted(PANEL_TAGS)
    for risk in RISKS:
        for m in panel[:-1]:                      # cố ý bỏ model cuối
            write_cell(tmp_path, "exp_b", risk, m, [m] * 6)
    assert run(verify_wide, tmp_path, "--panel", PANEL_ARG) == 1
    assert "CONG DU PANEL" in capsys.readouterr().err


def test_tag_sai_nhung_nhat_quan_thi_do(verify_wide, tmp_path, capsys):
    """Tag không thuộc panel phải ĐỎ, kể cả khi nó nhất quán ở mọi chỗ.

    Bẫy có thật của E3b: proxy KHÔNG chuẩn hoá slug của ghế lạ, nên `grok-4.20-…` được ghi
    y hệt một model thật — cùng tên thư mục, cùng tên file, cùng cả 6 ô `agent{i}_llm`.
    Không có gì mâu thuẫn với gì cả, nên mọi phép kiểm nội bộ đều cho qua và panel hoá 6
    model. Chỉ một bảng panel BÊN NGOÀI mới nói được "tag này không tồn tại".
    """
    panel = sorted(PANEL_TAGS)
    bad = "grok-4.20-0309-non-reasoning"          # thiếu tiền tố nhà: xai-
    tags = panel[:-1] + [bad]
    for risk in RISKS:
        for m in tags:
            write_cell(tmp_path, "exp_b", risk, m, [m] * 6)
    assert run(verify_wide, tmp_path, "--panel", PANEL_ARG) == 1
    assert "CONG DANH TINH PANEL" in capsys.readouterr().err


def test_panel_du_va_dung_thi_xanh(verify_wide, tmp_path):
    """Đủ cả 5 tag panel thật -> hai cổng panel im, không báo động giả."""
    for risk in RISKS:
        for m in sorted(PANEL_TAGS):
            write_cell(tmp_path, "exp_b", risk, m, [m] * 6)
    assert run(verify_wide, tmp_path, "--panel", PANEL_ARG, "--expect-reps", "10") == 0
