"""Cơ chế tính điểm của Collective-Risk Social Dilemma (Milinski et al., 2008).

Thuần logic, không phụ thuộc LLM — dễ test và tái lập (reproducible).

Quy tắc gốc:
  - Nhóm 6 người, mỗi người có endowment 40, chơi 10 vòng.
  - Mỗi vòng mỗi người đóng 0/2/4 vào "climate account".
  - Mục tiêu nhóm = tổng đóng góp >= 120 sau 10 vòng.
  - Nếu đạt mục tiêu: mỗi người giữ phần CHƯA đóng (endowment - tổng đã đóng).
  - Nếu KHÔNG đạt: tung xúc xắc 1 lần cho cả nhóm; với xác suất `risk` xảy ra
    thảm hoạ -> tất cả mất hết (payoff 0); ngược lại giữ phần chưa đóng.
  - Tiền đã đóng luôn mất, bất kể kết quả.
"""
from __future__ import annotations

import random
from typing import Sequence


def player_remaining(endowment: float, total_contribution: float) -> float:
    """Số tiền còn lại của một người = endowment trừ tổng đã đóng (không âm)."""
    return max(0.0, float(endowment) - float(total_contribution))


def group_total(contributions_per_player: Sequence[float]) -> float:
    """Tổng tiền cả nhóm đã bỏ vào quỹ chung."""
    return float(sum(contributions_per_player))


def is_target_reached(total: float, target: float) -> bool:
    return float(total) >= float(target)


def draw_catastrophe(rng: random.Random, risk_probability: float) -> bool:
    """Tung xúc xắc cấp nhóm MỘT lần. True = thảm hoạ xảy ra (mất hết).

    Dùng ``random.Random`` được seed sẵn để kết quả tái lập được. Vì draw này
    là lần gọi rng đầu tiên của mỗi game, hai game cùng seed nhưng khác mức
    rủi ro sẽ dùng CHUNG một số uniform (common random numbers) — một kỹ thuật
    giảm phương sai khi so sánh các mức rủi ro theo cặp.
    """
    return rng.random() < float(risk_probability)


def final_payoffs(
    endowment: float,
    per_player_totals: Sequence[float],
    target: float,
    risk_probability: float,
    rng: random.Random,
) -> dict:
    """Tính payoff cuối game cho từng người.

    Args:
        endowment: vốn ban đầu của mỗi người.
        per_player_totals: tổng đóng góp cả game của từng người.
        target: ngưỡng mục tiêu của nhóm.
        risk_probability: xác suất thảm hoạ nếu KHÔNG đạt mục tiêu.
        rng: bộ sinh số ngẫu nhiên đã seed (để tái lập).

    Returns:
        dict gồm: group_total, target, target_reached, catastrophe,
        remaining (list), payoffs (list).
    """
    total = group_total(per_player_totals)
    reached = is_target_reached(total, target)
    remaining = [player_remaining(endowment, t) for t in per_player_totals]

    if reached:
        catastrophe = False
        payoffs = list(remaining)
    else:
        catastrophe = draw_catastrophe(rng, risk_probability)
        payoffs = [0.0 for _ in remaining] if catastrophe else list(remaining)

    return {
        "group_total": total,
        "target": float(target),
        "target_reached": reached,
        "catastrophe": catastrophe,
        "remaining": remaining,
        "payoffs": payoffs,
    }
