#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""Cổng chặn cho MỆNH ĐỀ 1 của paper AAMAS (`paper/AAMAS/main.tex`, mục 3, `prop:eq`).

Đối chiếu đặc trưng Nash trong trò chơi chọn tổng đóng góp với mọi sai lệch đơn
phương; kiểm tra mốc phúc lợi và tính trội nghiêm ngặt ở p=0. Mệnh đề chính chỉ
phát biểu cho p<1.

Ở p=1, một số profile không đạt target là cân bằng yếu, nhưng KHÔNG phải tất cả.
Ví dụ sáu ghế đóng 18 có tổng 108 và payoff 0; một ghế tăng lên 30 đạt target và
còn 10. Đặc trưng đầy đủ cho p=1 được kiểm tra riêng trong
`test_p_one_equilibrium_boundary.py` trên mọi profile không phân biệt hoán vị.
"""
from __future__ import annotations

import itertools

import numpy as np
import pytest

# Luật chơi, y theo prompt trong kaggle/benchmarks/crg_task_server.py.
N, R, END, TGT = 6, 10, 40.0, 120.0
# Tổng đóng góp khả dĩ của một ghế: 10 vòng × {0,2,4} đạt mọi số CHẴN từ 0 tới 40.
TOTALS = list(range(0, 41, 2))
PSTAR = TGT / (N * END)
GRID = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]


def ev(c_i: float, total: float, p: float) -> float:
    """Kỳ vọng payoff của một ghế đóng c_i khi cả nhóm đóng total."""
    return END - c_i if total >= TGT else (1.0 - p) * (END - c_i)


def is_ne(c, p: float) -> bool:
    """Vét cạn mọi sai lệch đơn phương, không giả định chiến lược đối xứng."""
    total = sum(c)
    for i in range(N):
        for d in TOTALS:
            if ev(d, total - c[i] + d, p) > ev(c[i], total, p) + 1e-12:
                return False
    return True


def predicted(c, p: float) -> bool:
    """Đặc trưng trong Mệnh đề 1; miền áp dụng p<1."""
    return all(x == 0 for x in c) or (
        sum(c) == TGT and all(x <= p * END + 1e-9 for x in c))


@pytest.mark.parametrize('p', GRID)
def test_characterisation_matches_brute_force(p: float) -> None:
    """Mọi profile đối xứng và 3.000 profile lấy mẫu tại mỗi mức risk."""
    rng = np.random.default_rng(20260911)
    cands = [[t] * N for t in TOTALS]
    cands += [[int(rng.choice(TOTALS)) for _ in range(N)] for _ in range(3000)]
    bad = [c for c in cands if is_ne(c, p) != predicted(c, p)]
    assert not bad, f'p={p}: {len(bad)} profile lệch, ví dụ {bad[:3]}'


@pytest.mark.parametrize('p', GRID)
def test_target_reaching_equilibrium_exists_iff_p_at_least_half(p: float) -> None:
    exists = any(sum(c) >= TGT and is_ne(list(c), p)
                 for c in itertools.combinations_with_replacement(TOTALS, N))
    assert exists == (p >= PSTAR - 1e-9), f'p={p}: có={exists}, kỳ vọng={p >= PSTAR}'


def test_at_pstar_the_only_one_is_the_equal_split() -> None:
    got = [list(c) for c in itertools.combinations_with_replacement(TOTALS, N)
           if sum(c) >= TGT and is_ne(list(c), PSTAR)]
    assert got == [[TGT / N] * N], got


def test_zero_profile_is_always_an_equilibrium() -> None:
    assert all(is_ne([0] * N, p) for p in GRID + [1.0])


def test_contributing_is_strictly_dominated_at_zero_risk() -> None:
    others = range(0, int(5 * END) + 1, 2)
    assert all(ev(0, o, 0.0) > ev(c, o + c, 0.0) for c in TOTALS[1:] for o in others)


@pytest.mark.parametrize('p', GRID)
def test_welfare_optimum_matches_the_benchmark_used_in_every_table(p: float) -> None:
    brute = max((N * END - total) / N if total >= TGT else (1 - p) * (N * END - total) / N
                for total in range(0, int(N * END) + 1, 2))
    assert brute == pytest.approx(max((1 - p) * END, END - TGT / N))


def test_p_one_is_degenerate_and_the_proposition_says_so() -> None:
    """Một số profile không đạt target là cân bằng yếu ở p=1, ngoài đặc trưng p<1."""
    missing = [[2] * N, [4] * N, [0, 2, 4, 0, 2, 4]]
    assert all(sum(c) < TGT and is_ne(c, 1.0) for c in missing)
    assert not any(predicted(c, 1.0) for c in missing)
