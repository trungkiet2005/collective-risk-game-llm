"""Test end-to-end engine với LLM giả lập (không cần GPU)."""
from crsd.engine.agent import CrsdAgent
from crsd.engine.game import CrsdGame
from crsd.engine.state import GameConfig
from crsd.paths import PROMPTS_DIR
from crsd.runner.batch import run_games_batched

EN = (PROMPTS_DIR / "crsd_en.txt").read_text(encoding="utf-8")
GAME = {
    "name": "t", "nPlayers": 6, "endowment": 40, "contributionOptions": [0, 2, 4],
    "target": 120, "nRounds": 10, "riskProbability": 0.90,
}


def _mock(value):
    def send(prompts, seeds=None):
        return [f"reasoning...\nCONTRIBUTION: {value}" for _ in prompts]
    return send


def _make_game(seed=0):
    cfg = GameConfig.from_dict(GAME, language="en", model="Mock")
    agents = [CrsdAgent(name=f"Player_{i+1}") for i in range(6)]
    return CrsdGame(cfg, EN, agents, "g0", seed=seed)


def test_all_fair_reaches_target():
    g = _make_game()
    result = g.run(_mock(2))  # mỗi người 2 x 10 = 20; nhóm 120 = target
    assert result.group_total == 120
    assert result.target_reached is True
    assert result.catastrophe is False
    assert result.payoffs == [20.0] * 6
    assert len(g.turns) == 6 * 10  # 6 người x 10 vòng


def test_all_free_ride_high_risk():
    g = _make_game(seed=1)  # seed 1 -> thảm hoạ ở p=0.9
    result = g.run(_mock(0))
    assert result.group_total == 0
    assert result.target_reached is False
    assert result.catastrophe is True
    assert result.payoffs == [0.0] * 6


def test_batched_runner_matches():
    games = [_make_game(seed=0), _make_game(seed=0)]
    results = run_games_batched(games, _mock(4))  # 4 x 10 = 40 mỗi người -> 240 >= 120
    for r in results:
        assert r.target_reached is True
        assert r.group_total == 240
        assert r.payoffs == [0.0] * 6  # đóng hết 40 -> còn 0
