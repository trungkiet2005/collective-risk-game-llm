#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""Cổng chặn cho MỆNH ĐỀ 1 của paper AAMAS (`paper/AAMAS/sections/03_game.tex`).

VÌ SAO CÓ FILE NÀY. Mệnh đề đó là thứ duy nhất trong bài mà reviewer kiểm được bằng hai
mươi dòng code, và cả §4 lẫn §6 đều tựa lên nó: mốc `opt(p) = max((1-p)*40, 20)` trong mọi
bảng chính là "payoff của cân bằng tốt nhất", còn câu "ở p = 0 đóng góp bị trội hẳn" là
chỗ duy nhất trong bài không cần giả định gì về thái độ rủi ro. Sai một trong hai thì hỏng
cả hai mục, nên nó được vét cạn ở đây thay vì chỉ chứng minh trên giấy.

CÁI BẪY ĐÃ TRẢ GIÁ: p = 1. Khi p = 1, trượt target thì mọi người được 0 dù chơi thế nào,
nên MỌI profile trượt target đều là cân bằng (yếu) — không chỉ profile toàn 0. Bản đặc
trưng đầu tiên viết cho mọi p và lệch 447 profile, tất cả ở đúng p = 1. Vì thế mệnh đề
phát biểu cho `p < 1`, và `test_p_one_is_degenerate` khoá luôn ngoại lệ ấy để không ai
"dọn dẹp" chữ p<1 đi.
"""
from __future__ import annotations

import itertools

import numpy as np
import pytest

# Luật chơi, y theo prompt trong kaggle/benchmarks/crg_task_server.py.
N, R, END, TGT = 6, 10, 40.0, 120.0
# Tổng đóng góp khả dĩ của một ghế: 10 vòng × {0,2,4} đạt đúng mọi số CHẴN từ 0 tới 40.
TOTALS = list(range(0, 41, 2))
PSTAR = TGT / (N * END)          # = 0.5
GRID = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]   # p < 1, xem docstring


def ev(c_i: float, total: float, p: float) -> float:
    """Kỳ vọng payoff của một ghế đóng `c_i` khi cả nhóm đóng `total`."""
    return END - c_i if total >= TGT else (1.0 - p) * (END - c_i)


def is_ne(c, p: float) -> bool:
    """Vét cạn: không ghế nào có nước đi lệch nào tốt hơn hẳn."""
    total = sum(c)
    for i in range(N):
        for d in TOTALS:
            if ev(d, total - c[i] + d, p) > ev(c[i], total, p) + 1e-12:
                return False
    return True


def predicted(c, p: float) -> bool:
    """Đặc trưng phát biểu trong Mệnh đề 1, cho p < 1."""
    return all(x == 0 for x in c) or (
        sum(c) == TGT and all(x <= p * END + 1e-9 for x in c))


@pytest.mark.parametrize("p", GRID)
def test_characterisation_matches_brute_force(p: float) -> None:
    """Mọi profile đối xứng + 3.000 profile bất đối xứng: đặc trưng khớp tuyệt đối."""
    rng = np.random.default_rng(20260911)
    cands = [[t] * N for t in TOTALS]
    cands += [[int(rng.choice(TOTALS)) for _ in range(N)] for _ in range(3000)]
    bad = [c for c in cands if is_ne(c, p) != predicted(c, p)]
    assert not bad, f"p={p}: {len(bad)} profile lệch, ví dụ {bad[:3]}"


@pytest.mark.parametrize("p", GRID)
def test_target_reaching_equilibrium_exists_iff_p_at_least_half(p: float) -> None:
    exists = any(sum(c) >= TGT and is_ne(list(c), p)
                 for c in itertools.combinations_with_replacement(TOTALS, N))
    assert exists == (p >= PSTAR - 1e-9), f"p={p}: có={exists}, kỳ vọng={p >= PSTAR}"


def test_at_pstar_the_only_one_is_the_equal_split() -> None:
    """Tại p* = 1/2 ràng buộc c_i <= 40p ép mọi ghế về đúng 20 — không còn nghiệm nào khác."""
    got = [list(c) for c in itertools.combinations_with_replacement(TOTALS, N)
           if sum(c) >= TGT and is_ne(list(c), PSTAR)]
    assert got == [[TGT / N] * N], got


def test_zero_profile_is_always_an_equilibrium() -> None:
    """Một ghế đơn độc đóng tối đa 40 < 120, nên không ai một mình kéo nhóm qua target."""
    assert all(is_ne([0] * N, p) for p in GRID + [1.0])


def test_contributing_is_strictly_dominated_at_zero_risk() -> None:
    """Trụ cột của §4: ở p = 0 payoff = 40 - c với MỌI kết cục nhóm, nên đóng góp là lỗ thuần.

    Kiểm cho mọi mức đóng của ghế và mọi tổng nhóm khả dĩ, chứ không chỉ cho vài trường
    hợp: đây là câu duy nhất trong bài không cần giả định nào về thái độ rủi ro, nên nó
    phải đúng theo nghĩa mạnh nhất.
    """
    others = range(0, int(5 * END) + 1, 2)
    assert all(ev(0, o, 0.0) > ev(c, o + c, 0.0) for c in TOTALS[1:] for o in others)


@pytest.mark.parametrize("p", GRID)
def test_welfare_optimum_matches_the_benchmark_used_in_every_table(p: float) -> None:
    """`opt(p) = max((1-p)*40, 20)` đúng là phúc lợi bình quân đầu người lớn nhất."""
    brute = max((N * END - T) / N if T >= TGT else (1 - p) * (N * END - T) / N
                for T in range(0, int(N * END) + 1, 2))
    assert brute == pytest.approx(max((1 - p) * END, TGT / N))


def test_p_one_is_degenerate_and_the_proposition_says_so() -> None:
    """p = 1: mọi profile trượt target cũng là cân bằng (yếu) — ngoại lệ có thật.

    Test này tồn tại để KHOÁ chữ "Fix $p<1$" trong Mệnh đề 1. Ai bỏ nó đi để câu văn gọn
    hơn sẽ làm hỏng test này chứ không làm hỏng bài in ra, và đó mới là thứ ta muốn.
    """
    missing = [[2] * N, [4] * N, [0, 2, 4, 0, 2, 4]]
    assert all(sum(c) < TGT and is_ne(c, 1.0) for c in missing)
    assert not any(predicted(c, 1.0) for c in missing)
