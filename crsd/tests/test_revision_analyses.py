"""Test đầu-cuối cho hai script phân tích vòng revision.

`paper/revision/r8_nohint_ablation.py` (Q1) và `r9_ev_probe.py` (Q3) chỉ chạy hết
được các nhánh chính KHI ĐÃ CÓ dữ liệu — mà dữ liệu đó phải trả tiền GPU/proxy mới
có. Nghĩa là toàn bộ phần ghép cặp, kiểm định và bảng chéo sẽ chạy LẦN ĐẦU ngay
lúc người dùng vừa tải kết quả về. Hỏng ở thời điểm đó là đắt nhất.

Nên test ở đây dựng dữ liệu giả rồi chạy thẳng ``main()`` của cả hai script:

  - r8: cắm sẵn một hiệu ứng ĐÃ BIẾT (-12 điểm mỗi cặp, -20 nữa ở p=0.9) rồi đòi
    script phải tìm lại đúng con số đó — kèm McNemar, phân phối hành động và
    difference-in-differences của trục risk.
  - r9: dựng 4 model rơi vào 4 ô khác nhau của bảng chéo (biết-và-làm /
    biết-mà-không-làm / làm-mà-không-biết / không-biết-không-làm) rồi đòi script
    xếp đúng ô, và bắt được cả trường hợp ground_truth trong log lệch với công
    thức tính lại.

Cả hai nhánh "chưa có dữ liệu" cũng được test: chúng phải ghi JSON và thoát êm.
"""
import json
import sys
from pathlib import Path

import pytest

REVISION = Path(__file__).resolve().parents[2] / "paper" / "revision"
sys.path.insert(0, str(REVISION))

import _data as D                       # noqa: E402
import r8_nohint_ablation as R8         # noqa: E402
import r9_ev_probe as R9                # noqa: E402

GAMES_COLS = ["game_id", "model", "language", "risk_probability", "group_total",
              "target_reached", "catastrophe", "mean_payoff", "rep", "seed"]
RISKS = (0.1, 0.5, 0.9)
REPS = range(10)


# --------------------------------------------------------------------------- #
# dựng dữ liệu giả
# --------------------------------------------------------------------------- #
def _write_games(path: Path, rows: list, experiment=None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = GAMES_COLS + (["experiment"] if experiment is not None else [])
    lines = [",".join(cols)]
    for r in rows:
        if experiment is not None:
            r = {**r, "experiment": experiment}
        lines.append(",".join(str(r[c]) for c in cols))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _game_row(model, risk, rep, total, reached, seed=999):
    return {"game_id": f"g__{model}__{risk}__{rep}", "model": model, "language": "en",
            "risk_probability": risk, "group_total": total, "target_reached": reached,
            "catastrophe": 0, "mean_payoff": 20.0, "rep": rep, "seed": seed}


def _write_jsonl(path: Path, records: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")


def _turn(game_id, rnd, player, contribution, risk):
    return {"game_id": game_id, "round": rnd, "player": player,
            "contribution": contribution, "parse_failed": False,
            "risk_probability": risk, "language": "en",
            "persona_set": "personas_default", "disposition": "neutral"}


# ---- r8: hai nhánh prompt, hiệu ứng cắm sẵn -------------------------------- #
BASE_TOTAL = {0.1: 100, 0.5: 110, 0.9: 120}
ANCHOR_DROP = 12          # nohint tụt 12 điểm ở mọi mức risk
EXTRA_AT_HIGH = 20        # và tụt thêm 20 ở p=0.9 -> DiD = -20


def _nohint_total(risk, rep):
    jitter = 1 if rep % 2 else -1          # ±1 xen kẽ -> trung bình cặp không đổi
    return (BASE_TOTAL[risk] - ANCHOR_DROP + jitter
            - (EXTRA_AT_HIGH if risk == 0.9 else 0))


@pytest.fixture()
def nohint_tree(tmp_path, monkeypatch):
    """results/ giả: m-pair có CẢ HAI nhánh, hai model kia chỉ có một nhánh."""
    r = tmp_path / "results"

    base_rows = [_game_row("m-pair", p, rep, BASE_TOTAL[p], int(BASE_TOTAL[p] >= 120))
                 for p in RISKS for rep in REPS]
    _write_games(r / "open_source" / "crsd_all_models.csv", base_rows,
                 experiment="exp_baseline")
    # một model chỉ chạy baseline -> phải bị liệt kê, không được im lặng bỏ qua
    _write_games(r / "frontier" / "m-base-only" / "exp_baseline" / "games.csv",
                 [_game_row("m-base-only", p, rep, 120, 1)
                  for p in RISKS for rep in REPS])

    nh_rows = [_game_row("m-pair", p, rep, _nohint_total(p, rep),
                         int(_nohint_total(p, rep) >= 120))
               for p in RISKS for rep in REPS]
    _write_games(r / "raw" / "crsd_results" / "m-pair" / "exp_nohint" / "games.csv",
                 nh_rows)
    # ...và một model chỉ chạy nohint
    _write_games(r / "raw" / "crsd_results" / "m-nh-only" / "exp_nohint" / "games.csv",
                 [_game_row("m-nh-only", p, rep, 100, 0)
                  for p in RISKS for rep in REPS])

    # lượt chơi: baseline góp đúng mức mỏ neo (2), nohint bỏ hẳn mức đó (0/4)
    b_turns, n_turns = [], []
    for p in RISKS:
        for rep in (0, 1):
            gid = f"g__m-pair__{p}__{rep}"
            for rnd in (1, 2):
                for i, pl in enumerate(("Player_1", "Player_2")):
                    b_turns.append(_turn(gid, rnd, pl, 2, p))
                    n_turns.append(_turn(gid, rnd, pl, 0 if i == 0 else 4, p))
    _write_jsonl(r / "open_source" / "archive" / "exp_baseline" / "m-pair"
                 / "turns.jsonl", b_turns)
    _write_jsonl(r / "raw" / "crsd_results" / "m-pair" / "exp_nohint"
                 / "turns.jsonl", n_turns)

    monkeypatch.setattr(D, "RESULTS", r)
    monkeypatch.setattr(R8, "OUT", tmp_path / "out")
    (tmp_path / "out").mkdir()
    return tmp_path


def _r8_report(tmp_path):
    return json.loads((tmp_path / "out" / "r8_nohint_ablation.json")
                      .read_text(encoding="utf-8"))


def test_r8_pairs_on_common_random_numbers_and_audits_the_seed(nohint_tree):
    R8.main()
    audit = _r8_report(nohint_tree)["pairing_audit"]
    assert _r8_report(nohint_tree)["status"] == "compared"
    assert audit["n_paired"] == 30                 # 3 risk x 10 rep, đúng 1 model
    assert audit["n_nohint_unpaired"] == 0
    assert audit["seed_match_rate"] == 1.0
    assert "confirmed" in audit["crn_note"]


def test_r8_only_compares_models_present_in_both_arms(nohint_tree):
    R8.main()
    rep = _r8_report(nohint_tree)
    assert rep["models"]["compared"] == ["m-pair"]
    assert rep["models"]["nohint_without_baseline"] == ["m-nh-only"]
    assert "m-base-only" in rep["models"]["baseline_not_run_with_nohint"]


def test_r8_recovers_the_planted_effect_on_group_total(nohint_tree):
    R8.main()
    eff = _r8_report(nohint_tree)["effects"]["m-pair"]
    assert eff["by_risk"]["0.1"]["delta"] == pytest.approx(-ANCHOR_DROP)
    assert eff["by_risk"]["0.5"]["delta"] == pytest.approx(-ANCHOR_DROP)
    assert eff["by_risk"]["0.9"]["delta"] == pytest.approx(
        -(ANCHOR_DROP + EXTRA_AT_HIGH))
    g = eff["group_total"]
    assert g["n"] == 30
    assert g["mean"] == pytest.approx(-(3 * ANCHOR_DROP + EXTRA_AT_HIGH) / 3)
    assert g["ci"][0] < g["mean"] < g["ci"][1]
    assert g["p"] < 0.001


def test_r8_target_reach_uses_the_discordant_pairs_only(nohint_tree):
    R8.main()
    reach = _r8_report(nohint_tree)["effects"]["m-pair"]["target_reach"]
    assert reach["n_pairs"] == 30
    assert reach["reach_baseline"] == pytest.approx(1 / 3)   # chỉ p=0.9 đạt target
    assert reach["reach_nohint"] == 0.0
    assert (reach["n_lost"], reach["n_gained"]) == (10, 0)
    assert reach["p_mcnemar"] < 0.01


def test_r8_reports_the_action_distribution_shift(nohint_tree):
    R8.main()
    dist = _r8_report(nohint_tree)["distribution"]["pooled"]
    assert dist["baseline"]["p_2"] == 1.0
    assert dist["nohint"]["p_2"] == 0.0
    assert dist["delta_p_focal_pp"] == pytest.approx(-100.0)
    assert dist["total_variation"] == pytest.approx(1.0)
    assert dist["chi2_action_by_arm"]["p"] < 0.001
    assert dist["by_round_mean"]["1"]["baseline"] == 2.0    # vòng 1: mỏ neo mạnh nhất


def test_r8_differences_the_risk_effect_between_the_two_arms(nohint_tree):
    """Con số trả lời "mỏ neo có phải nguyên nhân của null không"."""
    R8.main()
    rs = _r8_report(nohint_tree)["risk_sensitivity"]
    assert rs["baseline_arm"]["mean"] == pytest.approx(20.0)
    assert rs["nohint_arm"]["mean"] == pytest.approx(0.0)
    assert rs["difference_in_differences"]["mean"] == pytest.approx(-EXTRA_AT_HIGH)


def test_r8_flags_a_broken_pairing_when_the_seeds_disagree(nohint_tree):
    """CRN gãy -> phải CẢNH BÁO, vì lúc đó ghép theo cell chứ không theo lượt xổ."""
    p = D.RESULTS / "raw" / "crsd_results" / "m-pair" / "exp_nohint" / "games.csv"
    p.write_text(p.read_text(encoding="utf-8").replace(",999", ",111"),
                 encoding="utf-8")
    R8.main()
    audit = _r8_report(nohint_tree)["pairing_audit"]
    assert audit["seed_match_rate"] == 0.0
    assert audit["crn_note"].startswith("WARNING")


def test_r8_degrades_gracefully_before_the_run_lands(tmp_path, monkeypatch, capsys):
    r = tmp_path / "results"
    # tổng có TRẢI trong từng cell, nếu không MDE tính ra 0 và mất ý nghĩa
    _write_games(r / "open_source" / "crsd_all_models.csv",
                 [_game_row("qwen25-7b-instruct", p, rep, 200 + rep, 1)
                  for p in RISKS for rep in REPS], experiment="exp_baseline")
    monkeypatch.setattr(D, "RESULTS", r)
    monkeypatch.setattr(R8, "OUT", tmp_path / "out")
    (tmp_path / "out").mkdir()
    R8.main()
    rep = _r8_report(tmp_path)
    assert rep["status"] == "awaiting data"
    assert rep["nohint_files_found"] == []
    # phần đối chứng vẫn phải tính được để đánh giá độ mạnh TRƯỚC khi tiêu tiền
    ready = rep["readiness"]["Qwen2.5-7B"]
    assert ready["baseline_games"] == 30
    assert ready["mde80_paired_conservative"] > 0
    assert "no exp_nohint data found" in capsys.readouterr().out


# --------------------------------------------------------------------------- #
# r9 — probe so sánh kỳ vọng
# --------------------------------------------------------------------------- #
# (model, risk, đáp án value_compare, đóng góp mỗi lượt, có đạt target không)
# Bốn model đầu được đặt để rơi vào bốn ô khác nhau của bảng chéo.
EV_CELLS = [
    ("m-knows-acts",  0.9, 1, 2, 1),      # trả lời đúng và chơi đúng EV
    ("m-knows-acts",  0.5, 0, 2, 1),      # p=0.5 là hoà EV -> ô "tie"
    ("m-knows-inert", 0.9, 1, 0, 0),      # BIẾT mà KHÔNG LÀM
    ("m-acts-blind",  0.1, 1, 0, 0),      # làm đúng EV nhưng trả lời sai
    ("m-acts-blind",  0.9, 1, 0, 0),      # cùng đáp án ở mọi p -> không hề so sánh
    ("m-neither",     0.1, 1, 2, 1),      # sai cả hai phía
]
N_GAMES = 2
N_ROUNDS = 2


def _comp_record(model, risk, gid, question_id, answer, truth, category="value"):
    return {"game_id": gid, "round": 1, "player": "Player_1", "player_index": 0,
            "question_id": question_id, "category": category, "params": {},
            "question_text": "?", "raw_response": f"ANSWER: {answer}",
            "parsed_answer": answer, "ground_truth": truth,
            "correct": bool(answer == truth), "parse_failed": False,
            "answer_kind": "int", "answerable_from_prompt": False,
            "language": "en", "risk_probability": risk, "model": model,
            "show_cumulative": False}


@pytest.fixture()
def evprobe_tree(tmp_path, monkeypatch):
    r = tmp_path / "results"
    g = R9.game_parameters()
    per_model = {}
    for model, risk, answer, contrib, reached in EV_CELLS:
        truth = R9.ev_truth(risk, g)
        d = per_model.setdefault(model, {"comp": [], "turns": [], "games": []})
        for k in range(N_GAMES):
            gid = f"g__{model}__{risk}__{k}"
            d["comp"].append(_comp_record(model, risk, gid, "value_compare",
                                          answer, truth["value_compare"]))
            # câu EV bằng tiền: chỉ model "biết" trả lời đúng
            said = truth["value_defect_ev"] if model == "m-knows-acts" else 20
            d["comp"].append(_comp_record(model, risk, gid, "value_defect_ev",
                                          said, truth["value_defect_ev"]))
            d["games"].append(_game_row(model, risk, k, contrib * 6 * 10, reached))
            for rnd in range(1, N_ROUNDS + 1):
                for pl in ("Player_1", "Player_2"):
                    d["turns"].append(_turn(gid, rnd, pl, contrib, risk))

    # trục `rules` làm đối chứng: có ở CẢ probe run lẫn bộ đọc-hiểu cũ
    per_model["m-knows-acts"]["comp"] += [
        _comp_record("m-knows-acts", 0.9, "gx", "rules_target", 120, 120,
                     category="rules"),
        _comp_record("m-knows-acts", 0.9, "gy", "rules_target", 120, 120,
                     category="rules"),
    ]
    for model, d in per_model.items():
        base = r / "raw" / "crsd_results" / model / "exp_evprobe"
        _write_jsonl(base / "comprehension.jsonl", d["comp"])
        _write_jsonl(base / "turns.jsonl", d["turns"])
        _write_games(base / "games.csv", d["games"])

    _write_jsonl(r / "open_source" / "archive" / "exp_comprehension" / "m-knows-acts"
                 / "comprehension.jsonl",
                 [_comp_record("m-knows-acts", 0.9, "go1", "rules_target", 120, 120,
                               category="rules"),
                  _comp_record("m-knows-acts", 0.9, "go2", "rules_target", 99, 120,
                               category="rules")])

    legacy = r / "open_source" / "crsd_comprehension_all_models.csv"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text("model,category,correct\nm,rules,1\nm,time,1\nm,state,0\n",
                      encoding="utf-8")

    monkeypatch.setattr(D, "RESULTS", r)
    monkeypatch.setattr(R9, "LEGACY_COMP_CSV", legacy)
    monkeypatch.setattr(R9, "OUT", tmp_path / "out")
    (tmp_path / "out").mkdir()
    return tmp_path


def _r9_report(tmp_path):
    return json.loads((tmp_path / "out" / "r9_ev_probe.json")
                      .read_text(encoding="utf-8"))


def test_r9_ground_truth_matches_the_engine():
    """Công thức trong script phải TRÙNG với `crsd/engine/comprehension.py`.

    Đây là chỗ dễ trôi nhất: script tự tính lại đáp án đúng, nên nếu engine đổi
    quy ước (1 = hợp tác hơn) mà script không đổi theo thì mọi accuracy đều sai
    mà không có gì báo.
    """
    from crsd.engine.comprehension import REGISTRY_BY_ID, _ev_compare_gt
    from crsd.engine.state import GameConfig

    g = R9.game_parameters()
    for p in (0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0):
        cfg = GameConfig(name="t", n_players=g["n_players"], endowment=g["endowment"],
                         target=g["target"], n_rounds=g["n_rounds"],
                         risk_probability=p)
        mine = R9.ev_truth(p, g)
        assert mine["value_compare"] == _ev_compare_gt(cfg)
        engine_ev = REGISTRY_BY_ID["value_defect_ev"].ground_truth(cfg, [], 1, 0, {})
        assert mine["value_defect_ev"] == engine_ev
    # và hệ quả hành vi: p=0.5 hoà, dưới thì bỏ mặc, trên thì góp đủ phần
    assert R9.ev_truth(0.5, g)["ev_action"] is None
    assert R9.ev_truth(0.1, g)["ev_action"] == 0.0
    assert R9.ev_truth(0.9, g)["ev_action"] == 2.0


def test_r9_scores_the_value_axis_per_model_and_risk(evprobe_tree):
    R9.main()
    rep = _r9_report(evprobe_tree)
    assert rep["status"] == "scored"
    assert rep["ground_truth_check"]["n_mismatched"] == 0
    acc = rep["accuracy"]
    assert acc["by_model"]["m-knows-acts"]["value_compare"]["accuracy"] == 1.0
    assert acc["by_model"]["m-neither"]["value_compare"]["accuracy"] == 0.0
    # accuracy theo mức risk: cùng một đáp án, đúng ở p=0.9 và sai ở p=0.1
    by_risk = acc["by_model_risk"]["m-acts-blind"]
    assert by_risk["0.1"]["value_compare"]["accuracy"] == 0.0
    assert by_risk["0.9"]["value_compare"]["accuracy"] == 1.0
    assert acc["by_model"]["m-knows-acts"]["value_defect_ev"]["accuracy"] == 1.0
    assert acc["by_model"]["m-neither"]["value_defect_ev"]["accuracy"] == 0.0


def test_r9_answer_mix_exposes_a_constant_answer(evprobe_tree):
    """33% vì ăn may khác hẳn 33% vì biết tính — phân phối đáp án mới tách được."""
    R9.main()
    mix = _r9_report(evprobe_tree)["answer_mix"]
    assert mix["m-acts-blind"]["constant_across_risk"] is True
    assert mix["m-knows-acts"]["constant_across_risk"] is False
    assert mix["m-acts-blind"]["by_risk"]["0.1"]["correct_answer"] == 2
    assert mix["m-acts-blind"]["by_risk"]["0.1"]["modal_answer"] == "1"


def test_r9_crosstabulates_probe_accuracy_against_behaviour(evprobe_tree):
    R9.main()
    ct = _r9_report(evprobe_tree)["crosstab"]
    assert ct["quadrants"] == {"knows_and_acts": 1, "knows_but_does_not_act": 2,
                               "acts_without_knowing": 1, "neither": 1,
                               "tie_cells": 1}
    cells = {(c["model"], c["risk"]): c for c in ct["cells"]}
    assert cells[("m-knows-inert", 0.9)]["quadrant"] == "knows_but_does_not_act"
    assert cells[("m-knows-inert", 0.9)]["probe_accuracy"] == 1.0
    assert cells[("m-knows-inert", 0.9)]["behaviour_rate"] == 0.0
    assert cells[("m-acts-blind", 0.1)]["quadrant"] == "acts_without_knowing"
    assert cells[("m-neither", 0.1)]["quadrant"] == "neither"
    assert cells[("m-knows-acts", 0.5)]["quadrant"].startswith("tie")


def test_r9_audits_the_new_value_category(evprobe_tree):
    """`value` là trục THỨ TƯ: mọi thứ gộp theo category sẽ mọc thêm một nhóm."""
    R9.main()
    inv = _r9_report(evprobe_tree)["category_inventory"]
    assert inv["raw_logs"]["exp_evprobe"]["has_value_axis"] is True
    assert inv["raw_logs"]["exp_comprehension"]["has_value_axis"] is False
    assert inv["raw_logs"]["exp_evprobe"]["categories"]["rules"] == 2
    assert inv["legacy_aggregate"]["has_value_axis"] is False
    assert "unaffected" in inv["legacy_aggregate"]["verdict"]


def test_r9_warns_when_the_legacy_aggregate_gains_the_fourth_axis(evprobe_tree):
    legacy = D.RESULTS / "open_source" / "crsd_comprehension_all_models.csv"
    legacy.write_text("model,category,correct\nm,rules,1\nm,value,1\n",
                      encoding="utf-8")
    R9.main()
    lg = _r9_report(evprobe_tree)["category_inventory"]["legacy_aggregate"]
    assert lg["has_value_axis"] is True
    assert "FOURTH axis" in lg["verdict"]


def test_r9_rules_control_compares_the_two_runs(evprobe_tree):
    R9.main()
    ctrl = _r9_report(evprobe_tree)["rules_control"]["m-knows-acts"]
    assert ctrl["rules_accuracy_probe_run"] == 1.0
    assert ctrl["rules_accuracy_earlier_run"] == 0.5
    assert ctrl["delta_pp"] == pytest.approx(50.0)


def test_r9_shouts_when_the_log_was_scored_against_another_rule(evprobe_tree):
    """ground_truth trong log lệch công thức -> báo to, không được lấy trung bình."""
    p = (D.RESULTS / "raw" / "crsd_results" / "m-neither" / "exp_evprobe"
         / "comprehension.jsonl")
    rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()]
    rows[0]["ground_truth"] = 99
    _write_jsonl(p, rows)
    R9.main()
    gt = _r9_report(evprobe_tree)["ground_truth_check"]
    assert gt["n_mismatched"] == 1
    assert gt["verdict"].startswith("MISMATCH")
    assert gt["examples"][0]["logged"] == 99


def test_r9_within_game_link_uses_the_probed_seat(evprobe_tree):
    R9.main()
    wg = _r9_report(evprobe_tree)["within_game"]
    # m-acts-blind: sai ở p=0.1, đúng ở p=0.9, cùng đóng góp 0 -> hai nhóm cùng mức
    d = wg["by_model"]["m-acts-blind"]
    assert d["mean_contribution_probe_wrong"] == 0.0
    assert d["mean_contribution_probe_right"] == 0.0
    assert d["test"]["n_a"] == N_GAMES * N_ROUNDS      # chỉ ghế được probe được ghép
    assert d["test"]["n_b"] == N_GAMES * N_ROUNDS


def test_r9_degrades_gracefully_before_the_run_lands(tmp_path, monkeypatch, capsys):
    """Chưa có probe nào: vẫn in bảng đáp án đúng + NỬA HÀNH VI của bảng chéo."""
    r = tmp_path / "results"
    _write_games(r / "frontier" / "m-x" / "exp_baseline" / "games.csv",
                 [_game_row("m-x", p, rep, 120, 1) for p in RISKS for rep in REPS])
    _write_jsonl(r / "frontier" / "m-x" / "exp_baseline" / "turns.jsonl",
                 [_turn(f"g__m-x__{p}__0", 1, "Player_1", 2, p) for p in RISKS])
    monkeypatch.setattr(D, "RESULTS", r)
    monkeypatch.setattr(R9, "LEGACY_COMP_CSV", r / "nope.csv")
    monkeypatch.setattr(R9, "OUT", tmp_path / "out")
    (tmp_path / "out").mkdir()
    R9.main()
    rep = _r9_report(tmp_path)
    assert rep["status"] == "awaiting data"
    assert rep["evprobe_files_found"] == []
    assert rep["expected_value_truth_table"]["0.9"]["value_compare"] == 1
    beh = rep["behaviour_ready"]["by_model_risk"]["m-x"]
    assert beh["0.9"]["ev_aligned_rate"] == 1.0        # góp 2 ở p=0.9 = đúng EV
    assert beh["0.1"]["ev_aligned_rate"] == 0.0
    assert beh["0.5"]["tie"] is True
    assert "nothing to score yet" in capsys.readouterr().out
