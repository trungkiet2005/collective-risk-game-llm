"""Test build_games_for_model: persona conditions (FairGame-style) + backward-compat."""
from crsd.runner.run_experiment import build_games_for_model

BASE_EXP = {
    "games": ["crsd_milinski_high_risk"],
    "languages": ["en"],
    "repetitions": 2,
    "seed": 0,
}


def test_agents_conditions_multiplies_and_tags():
    exp = dict(BASE_EXP, agentsConditions=["personas_default", "personas_selfish"])
    games = build_games_for_model(exp, "m")
    # 1 game × 2 conditions × 1 lang × 2 reps = 4
    assert len(games) == 4
    assert {g.persona_set for g in games} == {"personas_default", "personas_selfish"}
    # game_id mang tên điều kiện persona
    assert any("personas_selfish" in g.game_id for g in games)
    assert all("__m__" in g.game_id for g in games)


def test_selfish_persona_text_reaches_agents():
    exp = dict(BASE_EXP, agentsConditions=["personas_selfish"])
    games = build_games_for_model(exp, "m")
    g = games[0]
    assert all("selfish" in a.persona_text.lower() for a in g.agents)
    # persona xuất hiện trong prompt vòng 1
    p = g.build_round_prompts()[0]
    assert "selfish" in p.lower()


def test_backward_compat_single_agents_unchanged():
    """Không có agentsConditions -> game_id format CŨ (không chèn persona), persona_set=agents_name."""
    exp = dict(BASE_EXP, agents="personas_default")
    games = build_games_for_model(exp, "m", agents_name="personas_default")
    assert len(games) == 2  # 1 game × 1 lang × 2 reps
    assert all(g.persona_set == "personas_default" for g in games)
    # game_id KHÔNG có segment persona (đúng format cũ: game__model__lang__repN)
    assert games[0].game_id == "crsd_milinski_high_risk__m__en__rep0"


def test_cooperative_condition_loads():
    exp = dict(BASE_EXP, agentsConditions=["personas_cooperative"])
    games = build_games_for_model(exp, "m")
    assert all("cooperative" in a.persona_text.lower() for a in games[0].agents)


def test_no_shuffle_keeps_fixed_seats():
    """Mặc định (không shufflePersonas) -> selfish luôn ở ghế đầu (hành vi cũ)."""
    exp = dict(BASE_EXP, agentsConditions=["personas_mixed_2sel_4coop"], repetitions=2)
    games = build_games_for_model(exp, "m")
    for g in games:
        assert [a.disposition for a in g.agents] == \
            ["selfish", "selfish", "cooperative", "cooperative", "cooperative", "cooperative"]


def test_shuffle_preserves_composition_and_is_deterministic():
    exp = dict(BASE_EXP, agentsConditions=["personas_mixed_2sel_4coop"],
               shufflePersonas=True, repetitions=10)
    g1 = build_games_for_model(exp, "m")
    g2 = build_games_for_model(exp, "m")
    arr1 = [tuple(a.disposition for a in g.agents) for g in g1]
    arr2 = [tuple(a.disposition for a in g.agents) for g in g2]
    assert arr1 == arr2                       # tất định: chạy lại y hệt
    for seats in arr1:                        # giữ thành phần 2 selfish + 4 cooperative
        assert seats.count("selfish") == 2 and seats.count("cooperative") == 4
    assert len(set(arr1)) >= 2                 # vị trí có thực sự xáo qua các rep
    # disposition phải khớp persona_text từng ghế (đi theo persona đã hoán vị)
    for g in g1:
        for a in g.agents:
            assert a.disposition in a.persona_text.lower() or a.disposition == "neutral"


def test_shuffle_seat_arrangement_independent_of_language():
    """Cùng (điều kiện, rep) -> CÙNG sắp xếp ghế ở EN và VN (giữ CRN, chỉ ngôn ngữ đổi)."""
    exp = dict(BASE_EXP, agentsConditions=["personas_mixed_3sel_3coop"],
               shufflePersonas=True, languages=["en", "vn"], repetitions=3)
    games = build_games_for_model(exp, "m")
    by_lang = {"en": [], "vn": []}
    for g in games:
        lang = "vn" if "__vn__" in g.game_id else "en"
        by_lang[lang].append(tuple(a.disposition for a in g.agents))
    assert by_lang["en"] == by_lang["vn"]
