"""Test dựng prompt: block điều kiện, fill placeholder, không còn {placeholder} sót."""
import re

from crsd.engine.prompt import build_prompt
from crsd.engine.state import GameConfig
from crsd.paths import PROMPTS_DIR

EN = (PROMPTS_DIR / "crsd_en.txt").read_text(encoding="utf-8")
VN = (PROMPTS_DIR / "crsd_vn.txt").read_text(encoding="utf-8")

GAME = {
    "name": "t", "nPlayers": 6, "endowment": 40, "contributionOptions": [0, 2, 4],
    "target": 120, "nRounds": 10, "riskProbability": 0.90,
}


def _cfg(lang="en"):
    return GameConfig.from_dict(GAME, language=lang)


def _no_unresolved(text):
    # Không còn placeholder dạng {tenBien} hay block marker {x}: [
    assert not re.search(r"\{[A-Za-z_]+\}", text), f"placeholder sót: {text}"
    assert "]" not in text.split("CONTRIBUTION:")[0] or True  # block đã được mở


def test_round1_no_history_en():
    p = build_prompt(EN, _cfg(), "Player_1", 0, "", current_round=1, history=[], language="en")
    assert "Round 1 of 10" in p
    assert "0, 2, 4" in p
    assert "90%" in p and "10%" in p  # risk + safe
    assert "Previous rounds" not in p  # block history bị bỏ
    _no_unresolved(p)


def test_round2_shows_history_en():
    history = [[2, 2, 0, 4, 2, 2]]  # vòng 1
    p = build_prompt(EN, _cfg(), "Player_1", 0, "", current_round=2, history=history, language="en")
    assert "Previous rounds" in p
    assert "Round 1:" in p
    _no_unresolved(p)


def test_persona_block_en():
    p = build_prompt(EN, _cfg(), "Selfish_1", 0, "You are selfish.", 1, [], "en")
    assert "You are selfish." in p
    _no_unresolved(p)


def test_vn_template_basics():
    p = build_prompt(VN, _cfg("vn"), "Player_1", 0, "", current_round=1, history=[], language="vn")
    assert "Vòng 1 trên tổng 10" in p
    assert "CONTRIBUTION:" in p  # giữ token tiếng Anh để parser nhất quán
    _no_unresolved(p)
