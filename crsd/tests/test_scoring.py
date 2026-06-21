"""Test logic tính điểm CRSD — thuần, không cần GPU/LLM."""
import random

from crsd.analysis.metrics import gini
from crsd.engine import scoring


def test_target_reached_all_fair():
    # 6 người, mỗi người đóng tổng 20 (= 2 x 10 vòng) -> nhóm 120 = target.
    totals = [20, 20, 20, 20, 20, 20]
    out = scoring.final_payoffs(40, totals, 120, 0.90, random.Random(0))
    assert out["group_total"] == 120
    assert out["target_reached"] is True
    assert out["catastrophe"] is False
    assert out["payoffs"] == [20.0] * 6  # giữ phần chưa đóng = 40 - 20


def test_free_ride_high_risk_catastrophe():
    # Tất cả free-ride -> nhóm 0 < 120. Seed 1: random()~0.134 < 0.90 -> thảm hoạ.
    totals = [0] * 6
    out = scoring.final_payoffs(40, totals, 120, 0.90, random.Random(1))
    assert out["target_reached"] is False
    assert out["catastrophe"] is True
    assert out["payoffs"] == [0.0] * 6


def test_free_ride_low_risk_safe():
    # Nhóm 0 < 120 nhưng rủi ro thấp. Seed 1: 0.134 < 0.10 = False -> an toàn.
    totals = [0] * 6
    out = scoring.final_payoffs(40, totals, 120, 0.10, random.Random(1))
    assert out["target_reached"] is False
    assert out["catastrophe"] is False
    assert out["payoffs"] == [40.0] * 6  # giữ nguyên endowment


def test_remaining_never_negative():
    assert scoring.player_remaining(40, 50) == 0.0
    assert scoring.player_remaining(40, 12) == 28.0


def test_gini():
    assert abs(gini([10, 10, 10, 10])) < 1e-9
    assert gini([0, 0, 0, 40]) > 0.5
    assert gini([]) == 0.0
