"""Test E7 — đường tham chiếu scripted (offline, không GPU/API).

Chính sách nằm ở ``crsd/models/scripted.py`` và có test riêng
(``test_scripted_agents.py``); ở đây chỉ kiểm phần của E7: lưới thành phần nhóm,
việc nối vào định tuyến theo ghế, kỳ vọng giải tích, và CÁC CON SỐ THAM CHIẾU mà
paper trích dẫn.
"""
import json

import pytest

from crsd.analysis import scripted_reference as sr
from crsd.dataio.config_loader import load_json
from crsd.models import scripted as scripted_mod
from crsd.paths import CONFIGS_DIR
from crsd.runner import run_scripted_reference as runner

HIGH = load_json(CONFIGS_DIR / "game" / "crsd_milinski_high_risk.json")
CONDITIONS = {c.name: c for c in sr.default_conditions(6)}


def _run(condition_name, risk, reps=1, seed=0):
    """Chạy một ô qua ĐÚNG engine + router theo ghế."""
    base = dict(HIGH)
    template = runner.load_template(base.get("promptTemplate", "crsd"), "en")
    agents_cfg = load_json(CONFIGS_DIR / "agents" / f"{base['agents']}.json")
    return runner.run_condition(
        base, CONDITIONS[condition_name], risk, reps, template, agents_cfg, base_seed=seed
    )


# --- lưới điều kiện -----------------------------------------------------------


def test_policy_names_match_the_canonical_module():
    """E7 phải phủ ĐÚNG năm chính sách của crsd.models.scripted, không thiếu không thừa."""
    assert set(sr.POLICY_NAMES) == set(scripted_mod.POLICY_NAMES)
    assert len(sr.POLICY_NAMES) == 5


def test_condition_grid_has_5_homogeneous_and_7_mixed():
    conds = sr.default_conditions(6)
    assert len(conds) == 12
    homo = [c for c in conds if c.family == "homogeneous"]
    mix = [c for c in conds if c.family == "mix_ev_in_cc"]
    assert [c.name for c in homo] == [f"all_{p}" for p in sr.POLICY_NAMES]
    assert [c.k_invader for c in mix] == list(range(7))
    assert mix[3].seat_code == "EEECCC"
    assert mix[0].seat_policies == ("conditional_cooperator",) * 6
    assert mix[6].seat_policies == ("ev_maximiser",) * 6


def test_seat_model_names_use_the_scripted_prefix():
    assert sr.seat_model("always_2") == "scripted:always_2"
    assert sr.seat_model("scripted:always_2") == "scripted:always_2"
    assert CONDITIONS["mix_ev2_cc4"].seat_models == (
        ["scripted:ev_maximiser"] * 2 + ["scripted:conditional_cooperator"] * 4
    )
    with pytest.raises(ValueError):
        sr.seat_model("always_3")


def test_scripted_router_builds_one_backend_per_distinct_policy():
    route = sr.scripted_router(CONDITIONS["mix_ev2_cc4"].seat_policies)
    assert route.wants_context is True          # engine phải kèm contexts cho router
    assert sorted(route.backends) == ["scripted:conditional_cooperator",
                                      "scripted:ev_maximiser"]


# --- kỳ vọng giải tích --------------------------------------------------------


def test_expected_payoffs_reached_vs_missed():
    assert sr.expected_payoffs(40, [20] * 6, 120, 0.9) == [20.0] * 6   # đạt -> chắc chắn giữ
    assert sr.expected_payoffs(40, [0] * 6, 120, 0.9) == pytest.approx([4.0] * 6)
    assert sr.expected_payoffs(40, [0] * 6, 120, 0.0) == [40.0] * 6


# --- đường tham chiếu chạy thật qua engine -----------------------------------


@pytest.mark.parametrize("cond,risk,total,reached", [
    ("all_always_0", 0.9, 0.0, False),
    ("all_always_2", 0.9, 120.0, True),
    ("all_always_4", 0.9, 240.0, True),
    ("all_conditional_cooperator", 0.1, 120.0, True),
    ("all_conditional_cooperator", 0.9, 120.0, True),
    ("all_ev_maximiser", 0.9, 120.0, True),
    ("all_ev_maximiser", 0.5, 120.0, True),   # p* = 0.5, hoà -> vẫn đóng
    ("all_ev_maximiser", 0.1, 0.0, False),
])
def test_homogeneous_reference_curves(cond, risk, total, reached):
    results, _games = _run(cond, risk)
    assert results[0].group_total == total
    assert results[0].target_reached is reached


def test_all_always_4_burns_the_whole_endowment():
    (r,), _ = _run("all_always_4", 0.9)
    assert r.per_player_totals == [40.0] * 6
    assert r.payoffs == [0.0] * 6      # đạt target nhưng không còn gì để giữ


def test_ev_maximiser_pivot_is_the_ev_threshold_not_a_taste_for_risk():
    # p* = target/(n·E) = 120/240 = 0.5: dưới ngưỡng -> quỹ rỗng, từ ngưỡng -> đúng 120.
    assert _run("all_ev_maximiser", 0.49)[0][0].group_total == 0.0
    assert _run("all_ev_maximiser", 0.5)[0][0].group_total == 120.0


def test_mixed_population_collapse_threshold_at_low_risk():
    # p = 0.1: ev_maximiser ôm tiền; conditional_cooperator khớp TB người khác.
    # k <= 2 -> nhóm còn đóng 2/vòng; k >= 3 -> TB người khác < 1 -> sập từ vòng 2.
    totals = {k: _run(f"mix_ev{k}_cc{6-k}", 0.1)[0][0].group_total for k in range(7)}
    assert totals == {0: 120.0, 1: 100.0, 2: 80.0, 3: 6.0, 4: 4.0, 5: 2.0, 6: 0.0}
    for k in range(1, 7):
        assert _run(f"mix_ev{k}_cc{6-k}", 0.1)[0][0].target_reached is False


def test_mixed_population_reaches_target_at_high_risk_for_every_k():
    for k in range(7):
        (r,), _ = _run(f"mix_ev{k}_cc{6-k}", 0.9)
        assert r.group_total == 120.0 and r.target_reached is True


def test_ev_seats_outearn_cooperators_at_low_risk():
    (r,), _ = _run("mix_ev1_cc5", 0.1)
    exp = sr.expected_payoffs(40, r.per_player_totals, r.target, r.risk_probability)
    assert exp[0] == pytest.approx(36.0)               # ghế ev_maximiser (ôm hết)
    assert exp[1:] == pytest.approx([18.0] * 5)        # ghế conditional_cooperator


def test_engine_payoffs_are_either_remaining_or_zero():
    results, _ = _run("all_always_0", 0.5, reps=40)
    for r in results:
        assert r.payoffs == ([0.0] * 6 if r.catastrophe else [40.0] * 6)


def test_empirical_catastrophe_rate_tracks_p():
    # Tất định theo seed (seed ván = base_seed + rep) -> không phập phù giữa các lần chạy.
    results, _ = _run("all_always_0", 0.5, reps=40)
    rate = sum(1 for r in results if r.catastrophe) / len(results)
    assert 0.3 <= rate <= 0.7


def test_seat_attribution_reaches_the_turn_log():
    _results, games = _run("mix_ev2_cc4", 0.1)
    game = games[0]
    assert game.seat_models == CONDITIONS["mix_ev2_cc4"].seat_models
    round1 = [t for t in game.turns if t.round == 1]
    assert [t.disposition for t in round1] == list(CONDITIONS["mix_ev2_cc4"].seat_policies)
    assert [t.contribution for t in round1] == [0, 0, 2, 2, 2, 2]   # ev ôm tiền, cc đóng phần mình
    assert all(t.parse_failed is False for t in game.turns)


# --- tổng hợp & CLI -----------------------------------------------------------


def test_summarize_cell_columns():
    results, _ = _run("mix_ev2_cc4", 0.1, reps=3)
    row = runner.summarize_cell(CONDITIONS["mix_ev2_cc4"], 0.1, results)
    assert row["condition"] == "mix_ev2_cc4"
    assert row["family"] == "mix_ev_in_cc"
    assert row["k_ev"] == 2
    assert row["seat_code"] == "EECCCC"
    assert row["game_config"] == "crsd_milinski_low_risk"   # khoá join sang results/
    assert row["group_total_mean"] == 80.0
    assert row["group_total_sd"] == 0.0                     # chính sách tất định
    assert row["target_reach_rate"] == 0.0
    assert row["expected_payoff_ev"] == pytest.approx(36.0)
    assert row["expected_payoff_cc"] == pytest.approx(18.0)
    assert row["mean_contribution_per_round"] == pytest.approx(80.0 / 60.0)
    assert row["policy_module"] == "crsd.models.scripted"


def test_run_condition_rejects_zero_reps():
    with pytest.raises(ValueError):
        _run("all_always_2", 0.9, reps=0)


def test_cli_writes_summary_games_and_manifest(tmp_path):
    rc = runner.main(["--reps", "1", "--risks", "0.9", "--out", str(tmp_path), "--no-figure"])
    assert rc == 0
    summary = (tmp_path / "summary.csv").read_text(encoding="utf-8").splitlines()
    games = (tmp_path / "games.csv").read_text(encoding="utf-8").splitlines()
    assert len(summary) == 1 + 12          # header + 12 điều kiện
    assert len(games) == 1 + 12            # 1 ván mỗi điều kiện
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["experiment"] == "E7_scripted_reference"
    assert manifest["policy_module"] == "crsd.models.scripted"
    assert manifest["n_games"] == 12


# --- ràng buộc khoá join: KHÔNG được đổi 3 config gốc ------------------------


def test_overriding_risk_on_the_base_config_reproduces_the_three_originals():
    """Ghi đè riskProbability trên high_risk phải ra ĐÚNG low/medium config gốc.

    Nếu test này gãy nghĩa là ba config Milinski đã lệch nhau ở chỗ khác mức rủi ro
    -> đường tham chiếu E7 không còn so được với dữ liệu trong results/.
    """
    for name, risk in [("crsd_milinski_low_risk", 0.1),
                       ("crsd_milinski_medium_risk", 0.5),
                       ("crsd_milinski_high_risk", 0.9)]:
        original = load_json(CONFIGS_DIR / "game" / f"{name}.json")
        derived = dict(HIGH)
        derived["riskProbability"] = risk
        derived["name"] = original["name"]     # chỉ tên là khác
        assert derived == original
        assert runner.CANONICAL_CONFIG_BY_RISK[risk] == name
