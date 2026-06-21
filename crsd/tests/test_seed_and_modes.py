"""Test seed sinh văn bản (reproducible + độc lập) và 2 chế độ mới:
scratchpad (trí nhớ giới hạn) + framing (khung dẫn nhập trung lập)."""
import re

from crsd.engine.agent import CrsdAgent
from crsd.engine.game import CrsdGame, _extract_reasoning
from crsd.engine.prompt import build_prompt
from crsd.engine.round import parse_note
from crsd.engine.state import GameConfig
from crsd.paths import PROMPTS_DIR
from crsd.runner.run_experiment import make_mock_send_batch
from crsd.runner.batch import run_games_batched

EN = (PROMPTS_DIR / "crsd_en.txt").read_text(encoding="utf-8")
SCRATCH_EN = (PROMPTS_DIR / "crsd_scratchpad_en.txt").read_text(encoding="utf-8")
SCRATCH_VN = (PROMPTS_DIR / "crsd_scratchpad_vn.txt").read_text(encoding="utf-8")

GAME = {
    "name": "t", "nPlayers": 6, "endowment": 40, "contributionOptions": [0, 2, 4],
    "target": 120, "nRounds": 10, "riskProbability": 0.90,
}


def _cfg(**over):
    d = dict(GAME)
    d.update(over)
    return GameConfig.from_dict(d, language=d.get("language", "en"))


def _agents():
    return [CrsdAgent(name=f"P{i+1}") for i in range(6)]


def _no_unresolved(text):
    assert not re.search(r"\{[A-Za-z_]+\}", text), f"placeholder sót: {text}"


# --------------------------- SEED ---------------------------

def _game(seed, risk=0.90, sampling_base=0):
    cfg = _cfg(riskProbability=risk)
    return CrsdGame(cfg, EN, _agents(), f"g_s{seed}", seed=seed,
                    sampling_seed_base=sampling_base)


def test_sampling_seed_deterministic():
    """Cùng (seed, vòng, agent) -> cùng seed sinh văn bản, mọi lần."""
    g1 = _game(12345)
    g2 = _game(12345)
    for rnd in (1, 5, 10):
        assert [g1.sampling_seed(i, rnd) for i in range(6)] == \
               [g2.sampling_seed(i, rnd) for i in range(6)]


def test_sampling_seed_unique_across_rep_round_agent():
    """Seed phải KHÁC nhau giữa các (rep, vòng, agent) -> phá vỡ rep-collapse."""
    seen = set()
    for rep in range(10):                     # seed = base + rep
        g = _game(12345 + rep)
        for rnd in range(1, 11):
            for i in range(6):
                s = g.sampling_seed(i, rnd)
                assert s not in seen, f"trùng seed ở rep{rep} vòng{rnd} agent{i}"
                seen.add(s)
    assert len(seen) == 10 * 10 * 6


def test_sampling_seed_common_random_numbers_across_risk():
    """Cùng (rep, vòng, agent) ở mức rủi ro khác nhau -> CHUNG seed (CRN)."""
    g_hi = _game(12345, risk=0.90)
    g_lo = _game(12345, risk=0.10)
    for rnd in (1, 4, 10):
        assert [g_hi.sampling_seed(i, rnd) for i in range(6)] == \
               [g_lo.sampling_seed(i, rnd) for i in range(6)]


def test_build_round_sampling_seeds_matches():
    g = _game(7)
    g.current_round = 3
    assert g.build_round_sampling_seeds() == [g.sampling_seed(i, 3) for i in range(6)]


# --------------------------- FRAMING ---------------------------

def test_framing_block_off_by_default():
    p = build_prompt(EN, _cfg(), "P1", 0, "", current_round=1, history=[], language="en")
    assert "paid economics experiment" not in p
    _no_unresolved(p)


def test_framing_block_on():
    p = build_prompt(EN, _cfg(framing=True), "P1", 0, "", current_round=1,
                     history=[], language="en")
    assert "paid economics experiment" in p
    assert "your own final cash payoff" in p
    _no_unresolved(p)


# --------------------------- SCRATCHPAD ---------------------------

def test_scratchpad_round1_no_history():
    cfg = _cfg(memoryMode="scratchpad", promptTemplate="crsd_scratchpad")
    p = build_prompt(SCRATCH_EN, cfg, "P1", 0, "", current_round=1, history=[],
                     language="en")
    assert "limited memory" in p
    assert "NOTE:" in p and "CONTRIBUTION:" in p
    assert "Most recent round" not in p     # chưa có lịch sử
    assert "notepad so far" not in p        # chưa có ghi chú nào
    _no_unresolved(p)


def test_scratchpad_shows_only_last_round():
    cfg = _cfg(memoryMode="scratchpad", promptTemplate="crsd_scratchpad")
    history = [[2, 2, 2, 2, 2, 2], [0, 4, 2, 0, 2, 4], [4, 0, 0, 2, 2, 2]]
    p = build_prompt(SCRATCH_EN, cfg, "P1", 0, "", current_round=4, history=history,
                     language="en", agent_notes=["grp ~ 36, P2 free-riding"])
    # CHỈ vòng gần nhất (vòng 3) của LỊCH SỬ xuất hiện; vòng 1 & 2 KHÔNG.
    assert "Round 3:" in p
    assert "Round 1:" not in p and "Round 2:" not in p
    # ghi chú riêng được nạp lại
    assert "grp ~ 36, P2 free-riding" in p
    # KHÔNG lộ tổng tích luỹ
    assert "cumulative" not in p.lower()
    _no_unresolved(p)


def test_scratchpad_notes_accumulate_by_default():
    """Mặc định (noteWindow=0): cuốn sổ TÍCH LUỸ mọi dòng đã viết, có nhãn vòng."""
    cfg = _cfg(memoryMode="scratchpad", promptTemplate="crsd_scratchpad")
    history = [[2]*6, [0, 4, 2, 0, 2, 4], [4, 0, 0, 2, 2, 2]]
    notes = ["r1: all fair ~12", "r2: P1 jumped to 4", "r3: P2/P3 dropped to 0"]
    p = build_prompt(SCRATCH_EN, cfg, "P1", 0, "", current_round=4, history=history,
                     language="en", agent_notes=notes)
    for nt in notes:
        assert nt in p                     # mọi dòng cũ đều còn đó
    assert "[Round 1]" in p and "[Round 2]" in p and "[Round 3]" in p
    _no_unresolved(p)


def test_scratchpad_note_window_overwrite():
    """noteWindow=1: chỉ dòng ghi chú gần nhất (biến thể overwrite)."""
    cfg = _cfg(memoryMode="scratchpad", promptTemplate="crsd_scratchpad", noteWindow=1)
    history = [[2]*6, [0, 4, 2, 0, 2, 4], [4, 0, 0, 2, 2, 2]]
    notes = ["r1: all fair ~12", "r2: P1 jumped to 4", "r3: P2/P3 dropped to 0"]
    p = build_prompt(SCRATCH_EN, cfg, "P1", 0, "", current_round=4, history=history,
                     language="en", agent_notes=notes)
    assert "r3: P2/P3 dropped to 0" in p
    assert "r1: all fair ~12" not in p and "r2: P1 jumped to 4" not in p
    _no_unresolved(p)


def test_notepad_skips_empty_notes_keeps_round_numbers():
    cfg = _cfg(memoryMode="scratchpad", promptTemplate="crsd_scratchpad")
    history = [[2]*6, [0]*6, [4, 0, 0, 2, 2, 2]]
    notes = ["r1 note", "", "r3 note"]      # vòng 2 model quên ghi
    p = build_prompt(SCRATCH_EN, cfg, "P1", 0, "", current_round=4, history=history,
                     language="en", agent_notes=notes)
    assert "[Round 1] r1 note" in p and "[Round 3] r3 note" in p
    assert "[Round 2]" not in p
    _no_unresolved(p)


def test_scratchpad_window_2():
    cfg = _cfg(memoryMode="scratchpad", promptTemplate="crsd_scratchpad", historyWindow=2)
    history = [[2]*6, [0, 4, 2, 0, 2, 4], [4, 0, 0, 2, 2, 2]]
    p = build_prompt(SCRATCH_EN, cfg, "P1", 0, "", current_round=4, history=history,
                     language="en")
    assert "Round 2:" in p and "Round 3:" in p
    assert "Round 1:" not in p
    _no_unresolved(p)


def test_scratchpad_vn_basics():
    cfg = _cfg(memoryMode="scratchpad", promptTemplate="crsd_scratchpad", language="vn")
    p = build_prompt(SCRATCH_VN, cfg, "P1", 0, "", current_round=1, history=[],
                     language="vn")
    assert "trí nhớ giới hạn" in p
    assert "NOTE:" in p and "CONTRIBUTION:" in p
    _no_unresolved(p)


# --------------------------- parse_note ---------------------------

def test_parse_note_basic():
    assert parse_note("reasoning...\nNOTE: total ~ 40, watch P3\nCONTRIBUTION: 2") \
        == "total ~ 40, watch P3"


def test_parse_note_missing():
    assert parse_note("blah\nCONTRIBUTION: 4") == ""


def test_parse_note_case_insensitive_one_line():
    assert parse_note("note: keep it short\nmore text") == "keep it short"


def test_parse_note_ignores_inline_prose():
    """Chữ 'note' giữa câu lập luận KHÔNG được nuốt nhầm; phải lấy dòng NOTE: định dạng."""
    resp = ("Let me think. I should note: the group seems to be free-riding.\n"
            "NOTE: group total ~ 48, P3 free-rides\n"
            "CONTRIBUTION: 2")
    assert parse_note(resp) == "group total ~ 48, P3 free-rides"


def test_parse_note_last_formatted_line_wins():
    resp = "NOTE: draft idea\nmore reasoning\nNOTE: final estimate ~ 60\nCONTRIBUTION: 4"
    assert parse_note(resp) == "final estimate ~ 60"


def test_reasoning_excludes_note_block_and_overflow():
    """Note nhiều dòng (vi phạm định dạng) KHÔNG lọt vào log reasoning."""
    resp = "I think P2 is selfish.\nNOTE: estimate total around 50\nbut maybe 4 is risky\nCONTRIBUTION: 0"
    r = _extract_reasoning(resp)
    assert r == "I think P2 is selfish."
    assert "estimate total" not in r and "but maybe 4 is risky" not in r


# --------------------------- e2e reproducibility (mock) ---------------------------

def _run_once():
    cfg = _cfg(memoryMode="scratchpad", promptTemplate="crsd_scratchpad")
    games = [
        CrsdGame(cfg, SCRATCH_EN, _agents(), f"g{rep}", seed=12345 + rep,
                 sampling_seed_base=0)
        for rep in range(3)
    ]
    send = make_mock_send_batch("random", seed=999)
    results = run_games_batched(games, send, verbose=False)
    return [r.group_total for r in results]


def test_mock_random_reproducible_per_request():
    """Mock 'random' dùng seed per-lượt -> chạy lại cho kết quả y hệt (reproducible),
    nhưng các rep KHÁC nhau (độc lập)."""
    a = _run_once()
    b = _run_once()
    assert a == b                      # reproducible
    assert len(set(a)) > 1             # các rep không bị collapse thành một


def test_scratchpad_notes_recorded():
    cfg = _cfg(memoryMode="scratchpad", promptTemplate="crsd_scratchpad")
    g = CrsdGame(cfg, SCRATCH_EN, _agents(), "g", seed=1)
    send = make_mock_send_batch("random", seed=1)
    g.run(send)
    # mock luôn phát "NOTE: mock note" -> agent phải có note ghi lại
    assert all(a.last_note() == "mock note" for a in g.agents)
    # turns có note + sampling_seed
    assert all(t.note == "mock note" for t in g.turns)
    assert all(isinstance(t.sampling_seed, int) for t in g.turns)
