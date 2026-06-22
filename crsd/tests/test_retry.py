"""Test retry parse-fail trong run_games_batched: gọi lại slot hỏng với seed mới."""
from crsd.runner.run_experiment import build_games_for_model
from crsd.runner.batch import run_games_batched, _failed_slots

BASE_EXP = {
    "games": ["crsd_milinski_high_risk"],
    "languages": ["en"],
    "repetitions": 1,
    "seed": 0,
}


def _build():
    return build_games_for_model(dict(BASE_EXP), "m")


def test_retry_recovers_parse_fail():
    """Lần đầu mọi prompt trả RỖNG (parse-fail); retry với seed mới trả hợp lệ.

    Kỳ vọng: sau retry, KHÔNG còn turn nào parse_failed, và đóng góp = 2 (không phải
    fallback 0).
    """
    seen = {}

    def flaky_send(prompts, seeds=None):
        out = []
        for p in prompts:
            n = seen.get(p, 0)
            seen[p] = n + 1
            out.append("" if n == 0 else "CONTRIBUTION: 2")  # rỗng lần đầu, hợp lệ sau
        return out

    games = _build()
    results = run_games_batched(games, flaky_send, max_parse_retries=3)
    turns = [t for g in games for t in g.turns]
    assert turns, "phải có turn"
    assert all(not t.parse_failed for t in turns), "retry phải xoá hết parse_failed"
    assert all(t.contribution == 2 for t in turns)
    assert results[0].group_total > 0


def test_retry_disabled_keeps_failure():
    """max_parse_retries=0 -> không gọi lại; rỗng -> parse_failed + fallback 0."""
    def empty_send(prompts, seeds=None):
        return ["" for _ in prompts]

    games = _build()
    run_games_batched(games, empty_send, max_parse_retries=0)
    turns = [t for g in games for t in g.turns]
    assert all(t.parse_failed for t in turns)
    assert all(t.contribution == 0 for t in turns)  # fallback = lựa chọn nhỏ nhất


def test_retry_seed_changes_each_attempt():
    """Mỗi lượt retry phải đổi seed (khác seed gốc) để vLLM lấy mẫu khác."""
    calls = []

    def record_send(prompts, seeds=None):
        calls.append(list(seeds) if seeds is not None else None)
        # luôn rỗng -> ép retry chạy hết các lượt
        return ["" for _ in prompts]

    games = _build()
    run_games_batched(games, record_send, max_parse_retries=2, verbose=False)
    # calls: [vòng1 gốc, vòng1 retry1, vòng1 retry2, vòng2 gốc, ...]
    # 1 game, 1 rep, 10 vòng -> mỗi vòng 1 batch gốc + 2 retry
    orig, r1, r2 = calls[0], calls[1], calls[2]
    assert orig != r1 and r1 != r2 and orig != r2, "seed phải đổi mỗi lượt"


def test_failed_slots_helper():
    opts = [[0, 2, 4], [0, 2, 4]]
    assert _failed_slots(["CONTRIBUTION: 2", ""], opts) == [1]
    assert _failed_slots(["CONTRIBUTION: 4", "CONTRIBUTION: 0"], opts) == []
    assert _failed_slots(["CONTRIBUTION: 7", "rác"], opts) == [0, 1]  # 7 ngoài tập
