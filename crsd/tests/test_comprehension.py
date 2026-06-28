"""Test module đọc-hiểu (comprehension): ground truth, parser, render EN/VN,
enumerate tham số, và tính BẤT BIẾN của GT theo showCumulative."""
import re

from crsd.engine import comprehension as C
from crsd.engine.comprehension import (
    REGISTRY_BY_ID,
    iter_questions,
    parse_answer,
    score_answer,
)
from crsd.engine.prompt import build_prompt
from crsd.engine.state import GameConfig
from crsd.paths import PROMPTS_DIR

COMP_EN = (PROMPTS_DIR / "crsd_comprehension_en.txt").read_text(encoding="utf-8")
COMP_VN = (PROMPTS_DIR / "crsd_comprehension_vn.txt").read_text(encoding="utf-8")
DEC_EN = (PROMPTS_DIR / "crsd_en.txt").read_text(encoding="utf-8")

GAME = {
    "name": "t", "nPlayers": 6, "endowment": 40, "contributionOptions": [0, 2, 4],
    "target": 120, "nRounds": 10, "riskProbability": 0.90,
}

# Lịch sử 3 vòng đã chơi; agent đang chuẩn bị vòng 4, ghế P1 (index 0 = "you").
HISTORY = [
    [0, 2, 4, 2, 0, 4],   # vòng 1
    [2, 2, 0, 4, 2, 2],   # vòng 2
    [4, 0, 4, 0, 4, 0],   # vòng 3
]
R = 4
PI = 0


def _cfg(lang="en", show_cumulative=False):
    d = dict(GAME, showCumulative=show_cumulative)
    return GameConfig.from_dict(d, language=lang)


def _gt(qid, params=None):
    spec = REGISTRY_BY_ID[qid]
    return spec.ground_truth(_cfg(), HISTORY, R, PI, params or {})


# --------------------------- 1. GROUND TRUTH ---------------------------

def test_gt_rules():
    assert _gt("rules_actions") == {0, 2, 4}
    assert _gt("rules_endowment") == 40
    assert _gt("rules_target") == 120
    assert _gt("rules_n_rounds") == 10
    assert _gt("rules_risk_pct") == 90
    assert _gt("rules_payoff_disaster") == 0
    assert _gt("rules_max_contrib") == 4
    assert _gt("rules_min_contrib") == 0


def test_gt_risk_pct_levels():
    # 0.9/0.5/0.1 -> 90/50/10 (đúng tham số risk theo điều kiện)
    for risk, pct in [(0.90, 90), (0.50, 50), (0.10, 10)]:
        cfg = GameConfig.from_dict(dict(GAME, riskProbability=risk))
        assert REGISTRY_BY_ID["rules_risk_pct"].ground_truth(cfg, HISTORY, R, PI, {}) == pct


def test_gt_time():
    assert _gt("time_round") == 4
    assert _gt("time_action_i", {"i": 1, "x": 3}) == 4   # H[0][2]
    assert _gt("time_action_i", {"i": 3, "x": 5}) == 4   # H[2][4]
    assert _gt("time_own_action_i", {"i": 2}) == 2       # H[1][0]
    assert _gt("time_round_total_i", {"i": 2}) == 12     # sum(H[1])


def test_gt_state():
    assert _gt("state_pool") == 36                        # 12+12+12
    assert _gt("state_remaining_to_target") == 84         # 120-36
    assert _gt("state_X_total", {"x": 3}) == 8            # cột index2: 4+0+4
    assert _gt("state_own_total") == 6                    # cột index0: 0+2+4
    assert _gt("state_own_remaining") == 34               # 40-6
    assert _gt("state_count_p", {"x": 1, "p": 4}) == 1    # ghế self đóng 4 đúng 1 lần (vòng3)
    assert _gt("state_count_p", {"x": 1, "p": 0}) == 1    # vòng1
    assert _gt("state_rounds_left") == 7                  # 10-4+1
    assert _gt("state_target_reached") is False


def test_gt_pool_cross_check_scoring():
    from crsd.engine import scoring
    pool = sum(scoring.group_total(row) for row in HISTORY)
    assert _gt("state_pool") == int(pool)
    own = sum(row[PI] for row in HISTORY)
    assert _gt("state_own_remaining") == int(scoring.player_remaining(40, own))


# --------------------------- 2. PARSER ---------------------------

def test_parse_int_basic():
    assert parse_answer("reasoning...\nANSWER: 40", "int") == (40, False)


def test_parse_int_with_trailing_words():
    assert parse_answer("blah\nANSWER: 40 units", "int") == (40, False)


def test_parse_int_last_answer_line_wins():
    assert parse_answer("ANSWER: 0\nwait, reconsider\nANSWER: 4", "int") == (4, False)


def test_parse_int_ignores_inline_number_in_reasoning():
    # '99' giữa lập luận KHÔNG được nuốt; chỉ dòng ANSWER định dạng tính.
    assert parse_answer("I might say 99 but no.\nANSWER: 8", "int") == (8, False)


def test_parse_int_set():
    parsed, failed = parse_answer("ANSWER: 0, 2 and 4", "int_set")
    assert parsed == {0, 2, 4} and failed is False


def test_parse_yesno_en():
    assert parse_answer("ANSWER: yes", "yesno") == (True, False)
    assert parse_answer("ANSWER: no, not yet", "yesno") == (False, False)


def test_parse_yesno_vn():
    assert parse_answer("ANSWER: có", "yesno") == (True, False)
    assert parse_answer("ANSWER: không", "yesno") == (False, False)


def test_parse_missing_and_empty():
    assert parse_answer("no formatted line here", "int") == (None, True)
    assert parse_answer("", "int") == (None, True)


def test_score_answer():
    assert score_answer(40, 40, "int", False) is True
    assert score_answer(41, 40, "int", False) is False
    assert score_answer(None, 40, "int", True) is False
    assert score_answer({0, 2, 4}, {4, 2, 0}, "int_set", False) is True
    assert score_answer(True, True, "yesno", False) is True
    assert score_answer(False, True, "yesno", False) is False


# --------------------------- 3. RENDER EN/VN ---------------------------

# Tokens tiếng Anh KHÔNG được lọt vào prompt VN (câu hỏi nghiên cứu = hiệu ứng EN/VN
# nên prompt VN phải thuần Việt; token máy 'ANSWER:' nằm ở TEMPLATE, không ở render).
_EN_LEAK = re.compile(
    r"\b(round|you|player|target|climate|money|endowment|contribute|contributed|reach|how|what|the)\b",
    re.IGNORECASE,
)


def _params_for(spec):
    if spec.id in ("time_action_i",):
        return {"i": 2, "x": 3}
    if spec.id in ("time_own_action_i", "time_round_total_i"):
        return {"i": 2}
    if spec.id == "state_X_total":
        return {"x": 3}
    if spec.id == "state_count_p":
        return {"x": 3, "p": 4}
    return {}


def test_render_nonempty_both_languages():
    for spec in C.REGISTRY:
        p = _params_for(spec)
        en = spec.render(_cfg("en"), HISTORY, R, PI, p, "en")
        vn = spec.render(_cfg("vn"), HISTORY, R, PI, p, "vn")
        assert isinstance(en, str) and en.strip(), f"EN render rỗng: {spec.id}"
        assert isinstance(vn, str) and vn.strip(), f"VN render rỗng: {spec.id}"


def test_vn_render_no_english_leak():
    for spec in C.REGISTRY:
        vn = spec.render(_cfg("vn"), HISTORY, R, PI, _params_for(spec), "vn")
        m = _EN_LEAK.search(vn)
        assert m is None, f"VN render lọt tiếng Anh ({spec.id}): {m.group(0)!r} trong {vn!r}"


def test_render_no_float_suffix():
    # Số trong câu hỏi phải sạch '.0' (vd contribute 4 không phải 4.0).
    spec = REGISTRY_BY_ID["state_count_p"]
    en = spec.render(_cfg("en"), HISTORY, R, PI, {"x": 3, "p": 4}, "en")
    assert "4.0" not in en and "exactly 4" in en


# --------------------------- 4. ENUMERATE / CAPS ---------------------------

def test_iter_questions_has_three_categories():
    items = iter_questions(_cfg(), HISTORY, R, PI)
    cats = {spec.category for spec, _ in items}
    assert cats == {"rules", "time", "state"}
    assert len(items) > 0


def test_iter_questions_include_rules_flag():
    full = iter_questions(_cfg(), HISTORY, R, PI, caps={"include_rules": True})
    no_rules = iter_questions(_cfg(), HISTORY, R, PI, caps={"include_rules": False})
    assert any(s.category == "rules" for s, _ in full)
    assert not any(s.category == "rules" for s, _ in no_rules)
    assert len(no_rules) < len(full)


def test_iter_questions_max_seats_cap():
    one = iter_questions(_cfg(), HISTORY, R, PI, caps={"max_seats": 1})
    four = iter_questions(_cfg(), HISTORY, R, PI, caps={"max_seats": 4})
    # max_seats=1 -> chỉ chính mình -> không có câu hỏi 'người khác' (time_action_i / state_X_total)
    assert not any(s.id == "time_action_i" for s, _ in one)
    assert not any(s.id == "state_X_total" for s, _ in one)
    assert any(s.id == "time_action_i" for s, _ in four)
    assert len(one) < len(four)


def test_iter_questions_round1_no_history_questions():
    items = iter_questions(_cfg(), [], 1, PI)
    ids = {s.id for s, _ in items}
    # Vòng 1 chưa có lịch sử -> không hỏi Time/về người khác; vẫn có Rules + state vô hướng.
    assert "time_action_i" not in ids and "state_X_total" not in ids and "state_count_p" not in ids
    assert "time_round" in ids and "state_pool" in ids and "rules_target" in ids


def test_iter_questions_max_past_rounds_cap():
    # Ở vòng 8 (7 vòng quá khứ), cắt còn 3 -> mỗi câu hỏi theo vòng chỉ còn <=3 vòng.
    hist = [[2, 2, 2, 2, 2, 2] for _ in range(7)]
    items = iter_questions(_cfg(), hist, 8, PI, caps={"max_past_rounds": 3, "max_seats": 1})
    own_rounds = [p["i"] for s, p in items if s.id == "time_own_action_i"]
    assert len(own_rounds) == 3 and own_rounds == sorted(set(own_rounds))


# --------------------------- 5. GT BẤT BIẾN theo showCumulative ---------------------------

def test_ground_truth_invariant_to_show_cumulative():
    cfg_f = _cfg("en", show_cumulative=False)
    cfg_t = _cfg("en", show_cumulative=True)
    for spec in C.REGISTRY:
        p = _params_for(spec)
        assert spec.ground_truth(cfg_f, HISTORY, R, PI, p) == spec.ground_truth(cfg_t, HISTORY, R, PI, p), \
            f"GT đổi theo showCumulative ({spec.id}) — phải bất biến"


def test_answerable_flag_tracks_show_cumulative_for_pool():
    # state_pool: KHÔNG đọc được khi pool ẩn (baseline), ĐỌC được khi hiện (A/B).
    assert REGISTRY_BY_ID["state_pool"].answerable(_cfg(show_cumulative=False)) is False
    assert REGISTRY_BY_ID["state_pool"].answerable(_cfg(show_cumulative=True)) is True
    # own_remaining luôn in sẵn (control); risk_pct luôn in trong luật.
    assert REGISTRY_BY_ID["state_own_remaining"].answerable(_cfg()) is True
    assert REGISTRY_BY_ID["rules_risk_pct"].answerable(_cfg()) is True


# --------------------------- 6. TÍCH HỢP TEMPLATE đọc-hiểu ---------------------------

_PLACEHOLDER_RE = re.compile(r"\{[A-Za-z_]+\}")


def _build_comp(template, lang, qtext, current_round=R, history=None):
    history = HISTORY if history is None else history
    return build_prompt(template, _cfg(lang), "Player_1", PI, "", current_round,
                        history, lang, question_text=qtext)


def test_comprehension_prompt_renders_question_and_anchor():
    spec = REGISTRY_BY_ID["state_pool"]
    qtext = spec.render(_cfg("en"), HISTORY, R, PI, {}, "en")
    p = _build_comp(COMP_EN, "en", qtext)
    assert qtext in p                       # câu hỏi nằm trong prompt
    assert "ANSWER:" in p                    # có neo ANSWER cho parser
    assert "CONTRIBUTION:" not in p          # KHÔNG còn đuôi quyết định
    assert not _PLACEHOLDER_RE.search(p), f"còn placeholder sót: {p}"
    # vẫn giữ nguyên phần luật + state + lịch sử mà agent quyết định nhìn thấy
    assert "Round 4 of 10" in p and "90%" in p and "Previous rounds" in p


def test_comprehension_prompt_shares_prefix_with_decision_prompt():
    # Tiền tố luật/state/lịch sử PHẢI trùng prompt quyết định (chỉ khác đuôi).
    qtext = REGISTRY_BY_ID["state_pool"].render(_cfg("en"), HISTORY, R, PI, {}, "en")
    comp = _build_comp(COMP_EN, "en", qtext)
    dec = build_prompt(DEC_EN, _cfg("en"), "Player_1", PI, "", R, HISTORY, "en")
    shared = "in a group experiment that simulates a collective-risk social dilemma."
    pre_comp = comp.split(shared)[0]
    pre_dec = dec.split(shared)[0]
    assert pre_comp == pre_dec
    # cùng dòng lịch sử
    assert "Round 3:" in comp and "Round 3:" in dec


def test_comprehension_vn_prompt_clean():
    qtext = REGISTRY_BY_ID["state_pool"].render(_cfg("vn"), HISTORY, R, PI, {}, "vn")
    p = _build_comp(COMP_VN, "vn", qtext)
    assert qtext in p and "ANSWER:" in p
    assert "Vòng 4 trên tổng 10" in p
    assert not _PLACEHOLDER_RE.search(p), f"còn placeholder VN sót: {p}"


def test_decision_template_ignores_question_text():
    # Template quyết định KHÔNG có placeholder {question}/{questionText} -> truyền
    # question_text vào vẫn ra prompt quyết định y như cũ (tương thích ngược).
    with_q = build_prompt(DEC_EN, _cfg("en"), "Player_1", PI, "", R, HISTORY, "en",
                          question_text="how much is in the pool?")
    without_q = build_prompt(DEC_EN, _cfg("en"), "Player_1", PI, "", R, HISTORY, "en")
    assert with_q == without_q
    assert "CONTRIBUTION:" in with_q


# --------------------------- 7. PROBE KHÔNG ĐỔI QUYẾT ĐỊNH (an toàn) ---------------------------

def test_probe_does_not_change_decisions():
    import json

    from crsd.engine.agent import CrsdAgent
    from crsd.engine.game import CrsdGame
    from crsd.runner.batch import run_games_batched
    from crsd.runner.run_experiment import make_mock_send_batch

    dec = (PROMPTS_DIR / "crsd_en.txt").read_text(encoding="utf-8")
    comp = (PROMPTS_DIR / "crsd_comprehension_en.txt").read_text(encoding="utf-8")

    def make_game(gid):
        agents = [CrsdAgent(name=f"Player_{i + 1}") for i in range(6)]
        return CrsdGame(_cfg("en"), dec, agents, gid, seed=3, sampling_seeds_applied=True)

    g_plain = make_game("g")
    g_probe = make_game("g")

    def builder(game):
        return game.build_comprehension_prompts(comp, 0, {"max_seats": 2, "max_past_rounds": 2})

    mock = make_mock_send_batch("fair")
    r_plain = run_games_batched([g_plain], mock, max_parse_retries=0)
    r_probe = run_games_batched([g_probe], mock, max_parse_retries=0, probe_builder=builder)

    # Quyết định BYTE-IDENTICAL dù bật probe.
    assert g_plain.history == g_probe.history
    assert r_plain[0].per_round_contributions == r_probe[0].per_round_contributions
    assert r_plain[0].group_total == r_probe[0].group_total
    assert [t.to_dict() for t in g_plain.turns] == [t.to_dict() for t in g_probe.turns]

    # Probe có chạy (10 vòng) & sinh record; game không probe thì rỗng.
    assert len(g_plain.comprehension_records) == 0
    assert len(g_probe.comprehension_records) > 0
    rec = g_probe.comprehension_records[0].to_dict()
    for k in ("game_id", "question_id", "category", "ground_truth", "correct",
              "language", "show_cumulative", "answerable_from_prompt"):
        assert k in rec
    json.dumps(rec, ensure_ascii=False)  # JSON-friendly (set GT đã -> list)


# --------------------------- 8. RECORDER + RUNNER HELPERS ---------------------------

def test_recorder_and_runner_helpers(tmp_path):
    import json

    from crsd.dataio.recorder import summarize_comprehension, write_comprehension_jsonl
    from crsd.engine.agent import CrsdAgent
    from crsd.engine.game import CrsdGame
    from crsd.runner.batch import run_games_batched
    from crsd.runner.run_comprehension import make_mock_send, make_probe_builder

    dec = (PROMPTS_DIR / "crsd_en.txt").read_text(encoding="utf-8")
    comp_templates = {"en": (PROMPTS_DIR / "crsd_comprehension_en.txt").read_text(encoding="utf-8")}
    agents = [CrsdAgent(name=f"Player_{i + 1}") for i in range(6)]
    g = CrsdGame(_cfg("en"), dec, agents, "g__en__rep0", seed=2, sampling_seeds_applied=True)

    builder = make_probe_builder(comp_templates, [0], 3, None, [1, 5, 10])
    send = make_mock_send("random", seed=0)
    run_games_batched([g], send, max_parse_retries=0, probe_builder=builder)

    recs = g.comprehension_records
    assert len(recs) > 0
    # rulesCheckpoints: nhóm Rules CHỈ xuất hiện ở vòng 1/5/10.
    rule_rounds = {r.round for r in recs if r.category == "rules"}
    assert rule_rounds and rule_rounds <= {1, 5, 10}

    rows = summarize_comprehension(recs)
    assert rows and all(0.0 <= row["accuracy"] <= 1.0 for row in rows)
    assert all(row["n"] == row["n_correct"] + (row["n"] - row["n_correct"]) for row in rows)

    p = tmp_path / "comprehension.jsonl"
    write_comprehension_jsonl(recs, p)
    back = [json.loads(line) for line in open(p, encoding="utf-8")]
    assert len(back) == len(recs) and "question_id" in back[0]
