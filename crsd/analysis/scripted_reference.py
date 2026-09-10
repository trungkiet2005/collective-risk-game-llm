"""E7 — đường tham chiếu của các nhóm agent KỊCH BẢN (scripted), chạy offline.

Mọi hình trong paper cần một đường chuẩn "nếu nhóm chơi theo chính sách X thì kết
quả ra sao" để đặt hành vi của LLM vào bối cảnh. Toàn bộ phần này chạy qua ĐÚNG
engine (``crsd.engine``) chứ không mô phỏng lại luật chơi, nên số ở đây so trực
tiếp được với ``results/`` mà không cần giả định thêm.

Module này KHÔNG cài lại chính sách nào. Nó chỉ:
  * dựng LƯỚI THÀNH PHẦN NHÓM cần chạy (5 nhóm thuần + quét k = 0..n hỗn hợp),
  * nối chúng vào cơ chế sẵn có: ``crsd.models.scripted`` (năm chính sách) +
    ``crsd.models.routing.make_seat_router`` (định tuyến theo ghế),
  * và tính payoff KỲ VỌNG giải tích để đối chứng với xổ số thật của engine.

Năm chính sách (định nghĩa ở ``crsd/models/scripted.py``, tóm tắt lại để đọc hình):

  ``always_0`` / ``always_2`` / ``always_4``   hằng số mỗi vòng.
  ``ev_maximiser``            trung lập rủi ro: đóng đúng phần mình mỗi vòng khi
                              ``(1-p)·E <= target/n``, ngược lại đóng 0. Với tham số
                              Milinski ngưỡng là ``p* = 0.5``.
  ``conditional_cooperator``  vòng 1 đóng phần mình; từ vòng 2 khớp TRUNG BÌNH đóng
                              góp của những người KHÁC ở vòng trước.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from ..engine import scoring
from ..models.routing import make_seat_router
from ..models.scripted import (
    POLICY_NAMES as SCRIPTED_POLICY_NAMES,
    SCRIPTED_PREFIX,
    make_scripted_send_batch,
    scripted_policy_name,
)

# Thứ tự HIỂN THỊ của năm chính sách trên hình/bảng (từ "không đóng gì" tới "hợp tác").
# Tập hợp phải trùng với crsd.models.scripted — kiểm ngay lúc import để lệch tên là
# gãy ồn ào chứ không âm thầm bỏ sót một đường tham chiếu.
POLICY_NAMES: Tuple[str, ...] = (
    "always_0",
    "always_2",
    "always_4",
    "ev_maximiser",
    "conditional_cooperator",
)
assert set(POLICY_NAMES) == set(SCRIPTED_POLICY_NAMES), (
    f"lệch tên chính sách: E7 {sorted(POLICY_NAMES)} vs "
    f"crsd.models.scripted {sorted(SCRIPTED_POLICY_NAMES)}"
)

# Mã một ký tự cho từng chính sách -> chuỗi mô tả nhóm theo ghế (vd "EEECCC").
SEAT_CODE = {
    "always_0": "0",
    "always_2": "2",
    "always_4": "4",
    "ev_maximiser": "E",
    "conditional_cooperator": "C",
}

POLICY_MODULE = "crsd.models.scripted"   # ghi vào kết quả để truy nguyên


def seat_model(policy: str) -> str:
    """Tên model của một ghế kịch bản: ``"always_2" -> "scripted:always_2"``."""
    name = scripted_policy_name(policy)
    if name not in POLICY_NAMES:
        raise ValueError(
            f"chính sách kịch bản không tồn tại: {policy!r} (có: {', '.join(POLICY_NAMES)})"
        )
    return f"{SCRIPTED_PREFIX}{name}"


def scripted_router(seat_policies: Sequence[str]):
    """``send_batch`` định tuyến theo ghế cho một bàn TOÀN agent kịch bản.

    Dùng lại nguyên xi cơ chế của nhánh E0 (``make_seat_router`` +
    ``make_scripted_send_batch``) nên đường chạy của E7 giống hệt đường chạy thật
    của E3a — chỉ khác là không ghế nào gọi LLM.
    """
    return make_seat_router(
        [seat_model(p) for p in seat_policies], make_scripted_send_batch
    )


# --------------------------------------------------------------------------
# Lưới điều kiện: 5 nhóm thuần + quét thành phần hỗn hợp k = 0..n
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Condition:
    """Một thành phần nhóm cần chạy."""

    name: str
    family: str                      # "homogeneous" | "mix_ev_in_cc"
    seat_policies: Tuple[str, ...]
    k_invader: Optional[int] = None  # số ghế 'invader' (chỉ với family hỗn hợp)

    @property
    def seat_code(self) -> str:
        return "".join(SEAT_CODE.get(s, "?") for s in self.seat_policies)

    @property
    def seat_models(self) -> List[str]:
        return [seat_model(p) for p in self.seat_policies]


def homogeneous_conditions(n_players: int = 6,
                           policies: Sequence[str] = POLICY_NAMES) -> List[Condition]:
    """Năm nhóm thuần: cả 6 ghế cùng một chính sách."""
    return [
        Condition(name=f"all_{p}", family="homogeneous",
                  seat_policies=tuple([p] * n_players))
        for p in policies
    ]


def mixed_conditions(n_players: int = 6,
                     invader: str = "ev_maximiser",
                     resident: str = "conditional_cooperator") -> List[Condition]:
    """Quét k = 0..n ghế 'invader' trộn vào nhóm 'resident'.

    k = 0 và k = n trùng với hai nhóm thuần tương ứng — GIỮ LẠI để đường quét theo k
    liền mạch (hai đầu mút chính là điểm neo).
    """
    out = []
    for k in range(n_players + 1):
        seats = tuple([invader] * k + [resident] * (n_players - k))
        out.append(
            Condition(name=f"mix_ev{k}_cc{n_players - k}", family="mix_ev_in_cc",
                      seat_policies=seats, k_invader=k)
        )
    return out


def default_conditions(n_players: int = 6) -> List[Condition]:
    return homogeneous_conditions(n_players) + mixed_conditions(n_players)


# --------------------------------------------------------------------------
# Kỳ vọng giải tích (đối chứng với xổ số thật của engine)
# --------------------------------------------------------------------------


def expected_payoffs(endowment: float, per_player_totals: Sequence[float],
                     target: float, risk_probability: float) -> List[float]:
    """Payoff KỲ VỌNG (trung bình trên xổ số thảm hoạ), không rút thăm.

    Đạt target -> giữ phần chưa đóng; trượt -> phần chưa đóng nhân ``(1-p)``.
    Dùng lại đúng ``scoring`` của engine để repo không có luật chơi thứ hai.

    Chính sách kịch bản là tất định nên tổng nhóm giống hệt nhau ở mọi rep; chỉ xổ
    số thay đổi. Vì thế cột kỳ vọng này là giá trị ĐÚNG (không có sai số Monte Carlo),
    còn ``mean_payoff`` thực nghiệm chỉ để kiểm tra engine khớp với nó.
    """
    remaining = [scoring.player_remaining(endowment, t) for t in per_player_totals]
    if scoring.is_target_reached(scoring.group_total(per_player_totals), target):
        return list(remaining)
    keep = 1.0 - float(risk_probability)
    return [keep * r for r in remaining]
