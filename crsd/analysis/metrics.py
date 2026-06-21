"""Chỉ số phân tích cho các research question.

Bao gồm: tỉ lệ đạt mục tiêu theo mức rủi ro (so với baseline người của Milinski),
bất bình đẳng (Gini), free-riding, hiệu ứng vòng cuối, và so sánh EN vs VN.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable


def gini(values: Iterable[float]) -> float:
    """Hệ số Gini (0 = hoàn toàn bình đẳng)."""
    xs = sorted(float(v) for v in values)
    n = len(xs)
    if n == 0:
        return 0.0
    s = sum(xs)
    if s == 0:
        return 0.0
    cum = sum((i + 1) * x for i, x in enumerate(xs))
    return (2.0 * cum) / (n * s) - (n + 1.0) / n


def mean_payoff(result) -> float:
    p = result.payoffs
    return sum(p) / len(p) if p else 0.0


def contribution_gini(result) -> float:
    """Bất bình đẳng đóng góp giữa người chơi (theo tổng cả game)."""
    return gini(result.per_player_totals)


def free_riding_rate(result, fair_share_per_round: float = 2.0) -> float:
    """Tỉ lệ lượt đóng góp DƯỚI mức công bằng (= free-riding)."""
    below = total = 0
    for round_contribs in result.per_round_contributions:
        for c in round_contribs:
            total += 1
            if c < fair_share_per_round:
                below += 1
    return below / total if total else 0.0


def last_round_drop(result) -> float:
    """Hiệu ứng vòng cuối = (đóng góp TB vòng cuối) − (đóng góp TB vòng đầu)."""
    rounds = result.per_round_contributions
    if len(rounds) < 2:
        return 0.0
    first = sum(rounds[0]) / len(rounds[0])
    last = sum(rounds[-1]) / len(rounds[-1])
    return last - first


def target_reach_rate(results) -> dict:
    """Tỉ lệ đạt mục tiêu theo (ngôn ngữ, mức rủi ro)."""
    agg = defaultdict(list)
    for r in results:
        agg[(r.language, r.risk_probability)].append(1 if r.target_reached else 0)
    return {k: sum(v) / len(v) for k, v in agg.items()}


def language_comparison(results) -> dict:
    """So sánh EN vs VN: tỉ lệ đạt mục tiêu & đóng góp TB theo từng (ngôn ngữ, rủi ro)."""
    by_key = defaultdict(lambda: {"n": 0, "reached": 0, "total_contrib": 0.0})
    for r in results:
        key = (r.language, r.risk_probability)
        b = by_key[key]
        b["n"] += 1
        b["reached"] += 1 if r.target_reached else 0
        b["total_contrib"] += r.group_total
    out = {}
    for (lang, risk), b in by_key.items():
        out[(lang, risk)] = {
            "n_games": b["n"],
            "reach_rate": b["reached"] / b["n"] if b["n"] else 0.0,
            "mean_group_total": b["total_contrib"] / b["n"] if b["n"] else 0.0,
        }
    return out


# Baseline trên NGƯỜI từ Milinski et al. (2008): tỉ lệ nhóm đạt mục tiêu.
# 90% risk -> ~50% nhóm đạt; 50% và 10% -> hầu hết KHÔNG đạt.
HUMAN_BASELINE_REACH_RATE = {0.90: 0.50, 0.50: 0.10, 0.10: 0.00}
