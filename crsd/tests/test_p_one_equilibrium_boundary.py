"""Certainty boundary for the static total-contribution game (not an SPE claim).

A failed pool at p=1 is NOT automatically a Nash equilibrium. A player who can
reach the target while keeping positive cash has a profitable deviation.
"""
import itertools
import pytest
from crsd.tests.test_paper_equilibrium import END, N, TGT, TOTALS, ev, is_ne


def certainty_characterisation(profile):
    total = sum(profile)
    return total == TGT or (total < TGT and
                           all(total - contribution <= TGT - END for contribution in profile))


@pytest.mark.parametrize('profile,expected', [
    ([0] * N, True), ([2] * N, True), ([16] * N, True),
    ([18] * N, False), ([20] * N, True), ([22] * N, False),
])
def test_certainty_boundary_examples(profile, expected):
    assert is_ne(profile, 1.0) is expected
    assert certainty_characterisation(profile) is expected


def test_failed_pool_counterexample_has_profitable_deviation():
    assert ev(18, 108, 1.0) == 0
    assert ev(30, 120, 1.0) == 10
    assert not is_ne([18] * N, 1.0)


def test_all_unordered_total_profiles_at_certainty():
    # Exchangeable players: this covers all 21^6 labelled profiles up to permutation.
    checked = 0
    for profile in itertools.combinations_with_replacement(TOTALS, N):
        assert is_ne(profile, 1.0) == certainty_characterisation(profile), profile
        checked += 1
    assert checked == 230230
