"""Test ĐỊNH TUYẾN THEO GHẾ (crsd.models.routing) + ghi model từng ghế vào log.

Trọng tâm: THỨ TỰ ghép lại. Engine ``zip(agents, responses)`` theo vị trí, nên lệch
một ô là gán nhầm quyết định cho người chơi khác mà không lỗi nào bật lên -> test ở
đây khoá đúng bất biến đó với 3 backend và các phần chia KHÔNG bằng nhau.
"""
import json

import pytest

from crsd.dataio.recorder import summarize_game, write_games_csv, write_turns_jsonl
from crsd.engine.agent import CrsdAgent
from crsd.engine.game import CrsdGame
from crsd.engine.state import GameConfig
from crsd.models.routing import call_backend, make_seat_router, seats_for_slots
from crsd.models.scripted import make_scripted_send_batch
from crsd.paths import PROMPTS_DIR
from crsd.runner.batch import run_games_batched
from crsd.runner.run_experiment import (
    build_games_for_model,
    make_seat_send_batch,
    resolve_seat_models,
)

EN = (PROMPTS_DIR / "crsd_en.txt").read_text(encoding="utf-8")
GAME = {
    "name": "t", "nPlayers": 6, "endowment": 40, "contributionOptions": [0, 2, 4],
    "target": 120, "nRounds": 10, "riskProbability": 0.90,
}
BASE_EXP = {
    "games": ["crsd_milinski_high_risk"],
    "languages": ["en"],
    "repetitions": 1,
    "seed": 0,
}


def _tagging_backend(tag, log):
    """Backend giả: trả về '<tag>|<prompt>' và ghi lại từng lời gọi (để đếm/kiểm)."""
    def send(prompts, seeds=None):
        log.append((tag, list(prompts), list(seeds) if seeds is not None else None))
        return [f"{tag}|{p}" for p in prompts]
    return send


def _ctxs(seats):
    return [{"seat": s} for s in seats]


# --- bất biến THỨ TỰ ---

def test_reassembly_order_three_backends_unequal_partitions():
    """3 backend, phần chia 3/2/1, hai game ghép nối tiếp -> ghép lại ĐÚNG vị trí."""
    log = []
    seat_models = ["A", "A", "A", "B", "B", "C"]   # 3 ghế A, 2 ghế B, 1 ghế C
    route = make_seat_router(seat_models, lambda n: _tagging_backend(n, log))

    prompts = [f"p{i}" for i in range(12)]         # 2 game × 6 ghế
    seeds = list(range(100, 112))
    contexts = _ctxs([0, 1, 2, 3, 4, 5] * 2)

    out = route(prompts, seeds, contexts=contexts)

    expected = [f"{seat_models[i % 6]}|p{i}" for i in range(12)]
    assert out == expected                         # <- bất biến sống còn

    # mỗi backend được gọi ĐÚNG MỘT LẦN, với đúng tập con của nó
    assert [t for t, _, _ in log] == ["A", "B", "C"]
    by_tag = {t: (ps, ss) for t, ps, ss in log}
    assert by_tag["A"][0] == ["p0", "p1", "p2", "p6", "p7", "p8"]
    assert by_tag["B"][0] == ["p3", "p4", "p9", "p10"]
    assert by_tag["C"][0] == ["p5", "p11"]
    # seed phải đi kèm đúng prompt của nó
    assert by_tag["C"][1] == [105, 111]


def test_reassembly_order_with_shuffled_subset_like_retry():
    """Lô CON, ghế lộn xộn (giống lượt retry parse-fail) vẫn ghép đúng chỗ."""
    log = []
    seat_models = ["A", "B", "C", "A", "C", "B"]
    route = make_seat_router(seat_models, lambda n: _tagging_backend(n, log))

    seats = [4, 0, 5, 5, 1, 2, 0]                 # 7 slot, thứ tự bất kỳ
    prompts = [f"q{i}" for i in range(len(seats))]
    out = route(prompts, None, contexts=_ctxs(seats))

    assert out == [f"{seat_models[s]}|q{i}" for i, s in enumerate(seats)]
    assert len(log) == 3                           # vẫn chỉ 1 lời gọi / backend


def test_single_backend_for_repeated_name_is_shared():
    """Hai ghế cùng tên model -> DÙNG CHUNG một backend, gộp một lời gọi."""
    built = []

    def backend_for(name):
        built.append(name)
        return _tagging_backend(name, [])

    route = make_seat_router(["A", "A", "A", "A", "A", "A"], backend_for)
    assert built == ["A"]                          # chỉ dựng một lần
    assert len(route.backends) == 1


def test_positional_fallback_without_contexts():
    """Không có contexts -> suy ghế theo vị trí (i % nSeats) cho lô lockstep đầy đủ."""
    log = []
    seat_models = ["A", "B", "A", "B", "A", "B"]
    route = make_seat_router(seat_models, lambda n: _tagging_backend(n, log))
    out = route([f"p{i}" for i in range(12)], None)
    assert out == [f"{seat_models[i % 6]}|p{i}" for i in range(12)]


def test_positional_fallback_refuses_ambiguous_length():
    route = make_seat_router(["A"] * 6, lambda n: _tagging_backend(n, []))
    with pytest.raises(ValueError):
        route(["p0", "p1", "p2"], None)            # 3 không chia hết cho 6


def test_seats_for_slots_validation():
    assert seats_for_slots(4, None, 2) == [0, 1, 0, 1]
    assert seats_for_slots(3, _ctxs([2, 0, 1]), 3) == [2, 0, 1]
    with pytest.raises(ValueError):
        seats_for_slots(2, _ctxs([0]), 3)          # lệch độ dài
    with pytest.raises(ValueError):
        seats_for_slots(1, [{}], 3)                # thiếu khoá 'seat'
    with pytest.raises(ValueError):
        seats_for_slots(1, _ctxs([9]), 3)          # ghế ngoài phạm vi


def test_router_detects_backend_length_mismatch():
    def bad(prompts, seeds=None):
        return ["only-one"]
    route = make_seat_router(["A", "A"], lambda n: bad)
    with pytest.raises(RuntimeError):
        route(["p0", "p1"], None)


# --- đường mặc định KHÔNG ĐỔI ---

def test_default_path_calls_backend_with_two_positional_args():
    """Không có modelsPerSeat -> backend LLM vẫn được gọi ĐÚNG send_batch(prompts, seeds).

    Backend ở đây CỐ Ý chỉ nhận 2 tham số: nếu batch.py lỡ truyền contexts cho backend
    thường thì test này vỡ ngay (TypeError).
    """
    calls = []

    def strict_send(prompts, seeds):
        calls.append(len(prompts))
        return ["CONTRIBUTION: 2" for _ in prompts]

    games = build_games_for_model(dict(BASE_EXP), "m")
    results = run_games_batched(games, strict_send, max_parse_retries=0)
    assert calls == [6] * 10                        # 1 game × 6 ghế × 10 vòng
    assert results[0].group_total == 120


def test_default_game_records_single_model_for_every_seat():
    cfg = GameConfig.from_dict(GAME, language="en", model="ModelX")
    agents = [CrsdAgent(name=f"Player_{i+1}") for i in range(6)]
    g = CrsdGame(cfg, EN, agents, "g0", seed=0)
    assert g.seat_models == ["ModelX"] * 6
    result = g.run(make_scripted_send_batch("always_2"))
    assert result.seat_models == ["ModelX"] * 6
    assert {t.seat_model for t in g.turns} == {"ModelX"}
    assert summarize_game(result)["seat_models"] == "|".join(["ModelX"] * 6)


def test_build_games_without_models_per_seat_is_unchanged():
    games = build_games_for_model(dict(BASE_EXP), "m")
    assert games[0].seat_models == ["m"] * 6
    assert games[0].game_id == "crsd_milinski_high_risk__m__en__rep0"
    assert resolve_seat_models(dict(BASE_EXP), "m") is None


# --- ghế dị thể: cấu hình, chạy, và quy hành vi về đúng agent ---

def test_resolve_seat_models_self_sentinel_and_length_check():
    exp = dict(BASE_EXP, modelsPerSeat=["self", "scripted:always_0", "", None,
                                        "other-llm", "scripted:ev_maximiser"])
    assert resolve_seat_models(exp, "m", 6) == [
        "m", "scripted:always_0", "m", "m", "other-llm", "scripted:ev_maximiser"
    ]
    with pytest.raises(Exception):
        resolve_seat_models(dict(BASE_EXP, modelsPerSeat=["a", "b"]), "m", 6)


def test_build_games_with_models_per_seat_tags_every_seat():
    spec = ["self"] + ["scripted:always_4"] * 5
    games = build_games_for_model(dict(BASE_EXP, modelsPerSeat=spec), "m")
    assert games[0].seat_models == ["m"] + ["scripted:always_4"] * 5


def test_heterogeneous_table_end_to_end_and_log_attribution():
    """1 ghế LLM (giả) + 5 ghế kịch bản: mỗi ghế hành xử theo backend CỦA NÓ, và
    turns.jsonl ghi đúng ai cầm ghế nào."""
    seat_models = ["llm-mock", "scripted:always_0", "scripted:always_4",
                   "scripted:always_4", "scripted:conditional_cooperator",
                   "scripted:ev_maximiser"]

    def backend_for(name):
        if name == "llm-mock":
            def send(prompts, seeds=None):
                return ["thinking...\nCONTRIBUTION: 2" for _ in prompts]
            return send
        return make_scripted_send_batch(name)

    route = make_seat_router(seat_models, backend_for)
    games = build_games_for_model(
        dict(BASE_EXP, modelsPerSeat=seat_models), "llm-mock"
    )
    results = run_games_batched(games, route, max_parse_retries=0)
    turns = games[0].turns

    assert all(not t.parse_failed for t in turns)
    by_seat = {}
    for t in turns:
        by_seat.setdefault(t.player, []).append(t)

    # ghế 1 = LLM giả -> luôn 2; ghế 2 = always_0; ghế 3,4 = always_4
    assert [t.contribution for t in by_seat["Player_1"]] == [2] * 10
    assert [t.contribution for t in by_seat["Player_2"]] == [0] * 10
    assert [t.contribution for t in by_seat["Player_3"]] == [4] * 10
    # ghế 6 = ev_maximiser ở p=0.9 -> hợp tác 2 mọi vòng
    assert [t.contribution for t in by_seat["Player_6"]] == [2] * 10
    # ghế 5 = conditional_cooperator: vòng 1 đóng fair share 2, sau đó bám mean
    # của 5 người kia vòng trước = (2+0+4+4+2)/5 = 2.4 -> làm tròn về 2
    cc = [t.contribution for t in by_seat["Player_5"]]
    assert cc[0] == 2 and cc[1] == 2

    # quy hành vi về đúng agent: mỗi lượt mang tên backend cầm ghế đó
    for t in turns:
        seat = int(t.player.split("_")[1]) - 1
        assert t.seat_model == seat_models[seat]
    assert results[0].seat_models == seat_models


def test_seat_attribution_survives_the_recorders(tmp_path):
    seat_models = ["llm-a"] * 3 + ["scripted:always_0"] * 3
    games = build_games_for_model(dict(BASE_EXP, modelsPerSeat=seat_models), "llm-a")

    def backend_for(name):
        if name == "llm-a":
            return lambda prompts, seeds=None: ["CONTRIBUTION: 4" for _ in prompts]
        return make_scripted_send_batch(name)

    results = run_games_batched(
        games, make_seat_router(seat_models, backend_for), max_parse_retries=0
    )

    turns_path = tmp_path / "turns.jsonl"
    write_turns_jsonl(games[0].turns, turns_path)
    rows = [json.loads(line) for line in turns_path.read_text(encoding="utf-8").splitlines()]
    assert {r["seat_model"] for r in rows} == {"llm-a", "scripted:always_0"}
    assert all(r["seat_model"] == "scripted:always_0"
               for r in rows if r["player"] in ("Player_4", "Player_5", "Player_6"))

    games_path = tmp_path / "games.csv"
    write_games_csv(results, games_path)
    header = games_path.read_text(encoding="utf-8").splitlines()[0]
    assert "seat_models" in header
    assert summarize_game(results[0])["seat_models"] == "|".join(seat_models)


def test_retry_subset_still_routes_to_the_right_seat():
    """Lô retry chỉ gồm các slot hỏng: router phải theo contexts, không đoán vị trí."""
    seat_models = ["flaky", "scripted:always_4", "scripted:always_4",
                   "scripted:always_4", "scripted:always_4", "scripted:always_4"]
    seen = {}

    def backend_for(name):
        if name == "flaky":
            def send(prompts, seeds=None):
                out = []
                for p in prompts:
                    n = seen.get(p, 0)
                    seen[p] = n + 1
                    out.append("" if n == 0 else "CONTRIBUTION: 0")
                return out
            return send
        return make_scripted_send_batch(name)

    games = build_games_for_model(dict(BASE_EXP, modelsPerSeat=seat_models), "flaky")
    run_games_batched(games, make_seat_router(seat_models, backend_for),
                      max_parse_retries=3)
    turns = games[0].turns
    assert all(not t.parse_failed for t in turns), "retry phải xoá hết parse_failed"
    p1 = [t.contribution for t in turns if t.player == "Player_1"]
    assert p1 == [0] * 10                      # ghế hỏng nhận lại đúng phản hồi của nó
    p2 = [t.contribution for t in turns if t.player == "Player_2"]
    assert p2 == [4] * 10                      # ghế kịch bản KHÔNG bị lây


# --- kênh contexts ---

def test_call_backend_skips_context_for_plain_backends():
    def strict(prompts, seeds):
        return ["ok"]
    assert call_backend(strict, ["p"], [1], [{"seat": 0}]) == ["ok"]


def test_contexts_align_with_prompts_in_lockstep_batch():
    """contexts[i] phải mô tả ĐÚNG slot i (ghế, vòng, lịch sử) trong lô phẳng."""
    seen = {}

    def probe(prompts, seeds=None, contexts=None):
        for i, c in enumerate(contexts):
            seen.setdefault(c["round"], []).append((c["game_id"], c["seat"]))
        return ["CONTRIBUTION: 2" for _ in prompts]

    probe.wants_context = True
    exp = dict(BASE_EXP, repetitions=2)
    games = build_games_for_model(exp, "m")
    run_games_batched(games, probe, max_parse_retries=0)
    # mỗi vòng: 2 game × 6 ghế, ghế 0..5 lặp lại theo từng game, đúng thứ tự
    assert seen[1] == [(games[0].game_id, s) for s in range(6)] + \
                      [(games[1].game_id, s) for s in range(6)]
    assert seen[10][0][1] == 0


def test_probe_contexts_carry_the_probed_seat():
    """Probe đọc-hiểu hỏi từ góc nhìn một GHẾ cụ thể; ngữ cảnh kèm theo phải là
    ngữ cảnh của ĐÚNG ghế đó (không phải suy theo vị trí trong lô probe)."""
    from crsd.runner.run_comprehension import make_probe_builder

    comp = {"en": (PROMPTS_DIR / "crsd_comprehension_en.txt").read_text(encoding="utf-8")}
    probe_builder = make_probe_builder(comp, probe_players=[0, 3], max_seats=2,
                                       max_past_rounds=1, rules_checkpoints=[1])
    seen_probe, seen_decision = [], []

    def backend(prompts, seeds=None, contexts=None):
        out = []
        for p, c in zip(prompts, contexts):
            if "ANSWER:" in p:
                seen_probe.append((c["seat"], c.get("probe")))
                out.append("ANSWER: 4")
            else:
                seen_decision.append(c["seat"])
                out.append("CONTRIBUTION: 2")
        return out

    backend.wants_context = True
    games = build_games_for_model(dict(BASE_EXP), "m")
    run_games_batched(games, backend, max_parse_retries=0, probe_builder=probe_builder)

    assert seen_decision == [0, 1, 2, 3, 4, 5] * 10
    assert seen_probe, "phải có probe"
    assert {seat for seat, _ in seen_probe} == {0, 3}      # đúng hai ghế được hỏi
    assert all(flag is True for _, flag in seen_probe)     # có cờ đánh dấu probe
    assert games[0].comprehension_records


# --- helper DÙNG CHUNG cho mọi runner (run_experiment + run_comprehension) ---

def test_make_seat_send_batch_returns_the_same_backend_when_no_models_per_seat():
    """Không có modelsPerSeat -> trả về CHÍNH object truyền vào (không bọc gì cả).

    Kiểm tra bằng ``is``: chỉ cần bọc thêm một lớp là router sẽ đòi contexts và đổi
    cách gọi backend LLM cũ -> phải giữ nguyên tuyệt đối.
    """
    def base(prompts, seeds):
        return ["CONTRIBUTION: 2" for _ in prompts]

    assert make_seat_send_batch(dict(BASE_EXP), "m", base, verbose=False) is base


def test_make_seat_send_batch_reuses_the_running_model_backend():
    """Ghế mang đúng tên model đang chạy phải DÙNG LẠI backend đã dựng (không nạp
    lại GPU / không mở phiên API mới); ghế kịch bản đi qua module scripted."""
    def base(prompts, seeds=None):
        return ["CONTRIBUTION: 2" for _ in prompts]

    spec = ["self", "scripted:always_4", "self", "self", "self", "self"]
    route = make_seat_send_batch(dict(BASE_EXP, modelsPerSeat=spec), "m", base,
                                 verbose=False)
    assert route.seat_models == ["m", "scripted:always_4"] + ["m"] * 4
    assert route.backends["m"] is base                      # <- dùng lại, không dựng mới
    assert getattr(route.backends["scripted:always_4"], "is_scripted", False) is True


def test_make_seat_send_batch_uses_mock_factory_for_other_llm_seats():
    """--mock: ghế LLM KHÁC được giả lập (khỏi API key), ghế kịch bản vẫn là kịch bản."""
    built = []

    def mock_factory():
        built.append(1)
        return lambda prompts, seeds=None: ["CONTRIBUTION: 0" for _ in prompts]

    spec = ["self", "other-llm", "scripted:always_4", "self", "self", "self"]
    route = make_seat_send_batch(
        dict(BASE_EXP, modelsPerSeat=spec), "m",
        lambda prompts, seeds=None: ["CONTRIBUTION: 2" for _ in prompts],
        mock_send_factory=mock_factory, verbose=False,
    )
    assert built == [1]                                      # chỉ ghế 'other-llm'
    assert getattr(route.backends["scripted:always_4"], "is_scripted", False) is True


# --- run_comprehension phải bọc router GIỐNG run_experiment ---

def test_comprehension_runner_routes_per_seat_and_skips_scripted_probes(monkeypatch, tmp_path):
    """Bẫy im lặng: nếu runner đọc-hiểu dựng game có modelsPerSeat nhưng QUÊN bọc
    router thì log ghi seat_model dị thể trong khi MỘT model chơi hết mọi ghế.

    Test chạy nguyên ``run_comprehension.main`` ở chế độ --mock với bàn dị thể và
    kiểm: (a) ghế kịch bản thực sự do chính sách chơi, (b) probe đọc-hiểu KHÔNG bị
    ném vào ghế kịch bản, (c) probe còn lại được quy về đúng model của ghế.
    """
    import json as _json

    from crsd.runner import run_comprehension as rc

    seat_models = ["self", "self", "self",
                   "scripted:always_0", "scripted:always_0", "scripted:always_0"]
    exp = {
        "name": "exp_tmp_hetero_comp",
        "games": ["crsd_milinski_high_risk"],
        "languages": ["en"],
        "models": ["mock-llm"],
        "useOffline": False,
        "repetitions": 1,
        "seed": 0,
        "modelsPerSeat": seat_models,
        # ghế 0 = LLM (được hỏi), ghế 3 = kịch bản (phải bị loại khỏi probe)
        "comprehension": {"probePlayers": [0, 3], "maxSeats": 2,
                          "maxPastRounds": 1, "rulesCheckpoints": [1]},
    }
    exp_path = tmp_path / "exp.json"
    exp_path.write_text(_json.dumps(exp), encoding="utf-8")
    monkeypatch.setattr(rc, "RESULTS_DIR", tmp_path / "results")

    rc.main(["prog", str(exp_path), "--mock"])

    rows = [_json.loads(l) for l in
            (tmp_path / "results" / "exp_tmp_hetero_comp" / "turns.jsonl")
            .read_text(encoding="utf-8").splitlines()]

    # (a) ghế kịch bản THỰC SỰ do chính sách chơi: always_0 -> 0, chứ không phải
    # mock LLM (vốn trả 2). Đây là phần vỡ nếu quên bọc router.
    scripted = [r for r in rows if r["player"] in ("Player_4", "Player_5", "Player_6")]
    assert scripted and all(r["seat_model"] == "scripted:always_0" for r in scripted)
    assert all(r["contribution"] == 0 for r in scripted)
    llm = [r for r in rows if r["player"] == "Player_1"]
    assert all(r["seat_model"] == "mock-llm" and r["contribution"] == 2 for r in llm)

    # (b)+(c) probe chỉ hỏi ghế LLM, và được quy về đúng model của ghế đó
    probes = [_json.loads(l) for l in
              (tmp_path / "results" / "exp_tmp_hetero_comp" / "comprehension.jsonl")
              .read_text(encoding="utf-8").splitlines()]
    assert probes
    assert {p["player_index"] for p in probes} == {0}
    assert {p["model"] for p in probes} == {"mock-llm"}


def test_llm_probe_players_is_a_noop_without_models_per_seat():
    from crsd.runner.run_comprehension import llm_probe_players

    assert llm_probe_players({}, [0, 3]) == [0, 3]
    assert llm_probe_players({"modelsPerSeat": ["a"] * 6}, [0, 3]) == [0, 3]
    assert llm_probe_players(
        {"modelsPerSeat": ["a", "b", "c", "scripted:always_0", "e", "f"]}, [0, 3]
    ) == [0]


def test_comprehension_probe_model_defaults_to_the_game_model():
    """Bàn ĐỒNG NHẤT: meta['model'] của probe vẫn đúng bằng model của ván (như cũ)."""
    cfg = GameConfig.from_dict(GAME, language="en", model="ModelX")
    agents = [CrsdAgent(name=f"Player_{i+1}") for i in range(6)]
    g = CrsdGame(cfg, EN, agents, "g0", seed=0)
    comp = (PROMPTS_DIR / "crsd_comprehension_en.txt").read_text(encoding="utf-8")
    _, _, metas = g.build_comprehension_prompts(comp, 2, {"max_seats": 2})
    assert metas and {m["model"] for m in metas} == {"ModelX"}
