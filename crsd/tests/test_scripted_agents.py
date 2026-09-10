"""Test agent KỊCH BẢN (crsd.models.scripted): hành vi từng chính sách + định dạng
output phải lọt qua ĐÚNG parser hiện có, không phải sửa gì phía sau."""
import pytest

from crsd.engine.agent import CrsdAgent
from crsd.engine.game import CrsdGame
from crsd.engine.round import parse_contribution
from crsd.engine.state import GameConfig
from crsd.models.factory import get_send_batch
from crsd.models.scripted import (
    POLICY_NAMES,
    decide,
    is_scripted_model,
    make_scripted_send_batch,
    nearest_option,
    scripted_policy_name,
)
from crsd.paths import PROMPTS_DIR

EN = (PROMPTS_DIR / "crsd_en.txt").read_text(encoding="utf-8")
GAME = {
    "name": "t", "nPlayers": 6, "endowment": 40, "contributionOptions": [0, 2, 4],
    "target": 120, "nRounds": 10, "riskProbability": 0.90,
}


def _ctx(seat=0, history=None, risk=0.90, n_players=6, n_rounds=10,
         endowment=40.0, target=120.0, options=(0, 2, 4)):
    return {
        "seat": seat,
        "round": len(history or []) + 1,
        "n_players": n_players,
        "n_rounds": n_rounds,
        "endowment": endowment,
        "target": target,
        "options": list(options),
        "risk_probability": risk,
        "history": [list(r) for r in (history or [])],
    }


# --- định dạng output ---

@pytest.mark.parametrize("policy", POLICY_NAMES)
def test_output_parses_with_existing_parser(policy):
    """Mọi chính sách phải trả về văn bản mà parse_contribution nhận (KHÔNG fail)."""
    send = make_scripted_send_batch(policy)
    out = send(["prompt"], [123], contexts=[_ctx()])
    value, failed = parse_contribution(out[0], [0, 2, 4])
    assert failed is False
    assert value in (0, 2, 4)
    assert "\nCONTRIBUTION:" in out[0]      # dòng chốt neo đầu dòng
    assert out[0].startswith(f"[scripted:{policy}]")  # dấu vết kiểm toán


def test_batch_length_matches_prompts():
    send = make_scripted_send_batch("always_2")
    assert len(send(["a", "b", "c"], [1, 2, 3])) == 3


# --- chính sách hằng số ---

@pytest.mark.parametrize("policy,expected", [
    ("always_0", 0), ("always_2", 2), ("always_4", 4),
])
def test_always_constant(policy, expected):
    send = make_scripted_send_batch(policy)
    out = send(["p"] * 4, [1, 2, 3, 4], contexts=[_ctx(seat=i) for i in range(4)])
    for text in out:
        assert parse_contribution(text, [0, 2, 4]) == (expected, False)


def test_always_works_without_context():
    """Hằng số không cần trạng thái -> gọi kiểu backend LLM (2 tham số) vẫn chạy."""
    send = make_scripted_send_batch("always_4")
    assert parse_contribution(send(["p"], [7])[0], [0, 2, 4]) == (4, False)


def test_always_clamps_to_legal_options():
    """Tập lựa chọn khác -> hằng số được kéo về mức HỢP LỆ gần nhất."""
    assert decide("always_4", _ctx(options=(0, 1, 3))) == 3
    assert decide("always_2", _ctx(options=(0, 5, 10))) == 0   # 2 gần 0 hơn 5


# --- tất định & độc lập seed ---

@pytest.mark.parametrize("policy", POLICY_NAMES)
def test_seed_independent_and_deterministic(policy):
    send = make_scripted_send_batch(policy)
    ctxs = [_ctx(seat=1, history=[[0, 2, 4, 2, 0, 2]])]
    a = send(["p"], [1], contexts=ctxs)
    b = send(["p"], [999_999], contexts=ctxs)
    c = make_scripted_send_batch(policy)(["p"], None, contexts=ctxs)
    assert a == b == c


# --- ev_maximiser ---

def test_ev_maximiser_contributes_at_high_risk():
    """p=0.9: (1-p)·40 = 4 < 20 = target/n -> đóng phần mình (2)."""
    assert decide("ev_maximiser", _ctx(risk=0.90)) == 2


def test_ev_maximiser_free_rides_at_low_risk():
    """p=0.1: (1-p)·40 = 36 > 20 -> đóng 0."""
    assert decide("ev_maximiser", _ctx(risk=0.10)) == 0


def test_ev_maximiser_threshold_is_half_for_milinski_parameters():
    """Ngưỡng EV p* = 1 - (target/n)/endowment = 0.5; ĐÚNG ngưỡng thì hợp tác."""
    assert decide("ev_maximiser", _ctx(risk=0.49)) == 0
    assert decide("ev_maximiser", _ctx(risk=0.50)) == 2      # không > nên hợp tác
    assert decide("ev_maximiser", _ctx(risk=0.51)) == 2


def test_ev_maximiser_ignores_history():
    """Không đội lốt điều kiện: lịch sử thế nào cũng cùng quyết định."""
    a = decide("ev_maximiser", _ctx(risk=0.9, history=[[0] * 6] * 3))
    b = decide("ev_maximiser", _ctx(risk=0.9, history=[[4] * 6] * 3))
    assert a == b == 2


def test_ev_maximiser_threshold_shifts_with_endowment():
    """Endowment lớn hơn -> free-ride hấp dẫn hơn -> ngưỡng rủi ro cao hơn."""
    # (1-0.6)·100 = 40 > 20 -> đóng 0 dù p=0.6
    assert decide("ev_maximiser", _ctx(risk=0.60, endowment=100.0)) == 0


# --- conditional_cooperator ---

def test_conditional_cooperator_cooperates_on_round_1():
    """Chưa có lịch sử -> đóng đúng phần mình = 120/(6·10) = 2."""
    assert decide("conditional_cooperator", _ctx(history=[])) == 2


def test_conditional_cooperator_matches_others_mean():
    """Ghế 0; 5 người kia vòng trước đóng 4 -> trung bình 4 -> đóng 4."""
    ctx = _ctx(seat=0, history=[[0, 4, 4, 4, 4, 4]])
    assert decide("conditional_cooperator", ctx) == 4


def test_conditional_cooperator_excludes_own_seat():
    """Đóng góp CỦA CHÍNH MÌNH không được tính vào trung bình 'người khác'."""
    # ghế 5 đóng 4, 5 người kia đóng 0 -> trung bình người khác = 0
    assert decide("conditional_cooperator", _ctx(seat=5, history=[[0] * 5 + [4]])) == 0
    # cùng vòng đó, ghế 0 thấy người khác = [0,0,0,0,4] -> mean 0.8 -> gần 0
    assert decide("conditional_cooperator", _ctx(seat=0, history=[[0] * 5 + [4]])) == 0


def test_conditional_cooperator_rounds_to_nearest_option():
    """mean = (2+2+4+4+4)/5 = 3.2 -> gần 4 hơn 2 -> đóng 4."""
    ctx = _ctx(seat=0, history=[[0, 2, 2, 4, 4, 4]])
    assert decide("conditional_cooperator", ctx) == 4


def test_conditional_cooperator_uses_only_previous_round():
    """Chỉ vòng LIỀN TRƯỚC, không phải trung bình cả ván."""
    ctx = _ctx(seat=0, history=[[0, 4, 4, 4, 4, 4], [0, 0, 0, 0, 0, 0]])
    assert decide("conditional_cooperator", ctx) == 0


def test_conditional_cooperator_tie_rounds_down():
    """Cách đều hai mức -> chọn mức THẤP hơn (bảo thủ, tất định)."""
    # 3 người chơi, ghế 0; hai người kia đóng 0 và 2 -> mean = 1.0, cách đều 0 và 2
    ctx = _ctx(seat=0, n_players=3, history=[[4, 0, 2]])
    assert decide("conditional_cooperator", ctx) == 0


def test_nearest_option_ties_go_low():
    assert nearest_option(1.0, [0, 2, 4]) == 0
    assert nearest_option(3.0, [0, 2, 4]) == 2
    assert nearest_option(1.1, [0, 2, 4]) == 2
    assert nearest_option(-5, [0, 2, 4]) == 0
    assert nearest_option(99, [0, 2, 4]) == 4


# --- lỗi rõ ràng thay vì âm thầm sai ---

@pytest.mark.parametrize("policy", ["ev_maximiser", "conditional_cooperator"])
def test_state_dependent_policy_requires_context(policy):
    send = make_scripted_send_batch(policy)
    with pytest.raises(ValueError):
        send(["p"], [1])          # gọi kiểu backend LLM -> không có ngữ cảnh


def test_unknown_policy_raises():
    with pytest.raises(ValueError):
        make_scripted_send_batch("scripted:always_7")
    with pytest.raises(ValueError):
        decide("khong_ton_tai", _ctx())


def test_context_length_mismatch_raises():
    send = make_scripted_send_batch("always_2")
    with pytest.raises(ValueError):
        send(["a", "b"], [1, 2], contexts=[_ctx()])


# --- nhận diện tên + đi qua factory ---

def test_name_helpers():
    assert is_scripted_model("scripted:always_4")
    assert not is_scripted_model("gpt-5.4-nano")
    assert not is_scripted_model(None)
    assert scripted_policy_name("scripted:ev_maximiser") == "ev_maximiser"
    assert scripted_policy_name("ev_maximiser") == "ev_maximiser"


def test_factory_returns_scripted_backend_without_touching_llm_path():
    """get_send_batch("scripted:...") KHÔNG được import/đụng tới connector LLM."""
    send = get_send_batch("scripted:always_4", offline=True)
    assert getattr(send, "is_scripted", False) is True
    assert parse_contribution(send(["p"], [1])[0], [0, 2, 4]) == (4, False)


# --- chạy hết một ván bằng agent kịch bản (engine KHÔNG có nhánh riêng) ---

def test_full_game_with_scripted_backend():
    cfg = GameConfig.from_dict(GAME, language="en", model="scripted:always_2")
    agents = [CrsdAgent(name=f"Player_{i+1}") for i in range(6)]
    g = CrsdGame(cfg, EN, agents, "g_scripted", seed=0)
    result = g.run(make_scripted_send_batch("always_2"))
    assert result.group_total == 120          # 6 người × 2 × 10 vòng
    assert result.target_reached is True
    assert all(not t.parse_failed for t in g.turns)
    assert all(t.contribution == 2 for t in g.turns)


def test_full_game_conditional_cooperator_follows_history():
    """conditional_cooperator solo: vòng 1 đóng 2 (fair share), rồi bám mean = 2."""
    cfg = GameConfig.from_dict(GAME, language="en", model="scripted:conditional_cooperator")
    agents = [CrsdAgent(name=f"Player_{i+1}") for i in range(6)]
    g = CrsdGame(cfg, EN, agents, "g_cc", seed=0)
    result = g.run(make_scripted_send_batch("conditional_cooperator"))
    assert [t.contribution for t in g.turns[:6]] == [2] * 6
    assert result.group_total == 120


# --- adapter cho lớp phân tích offline (view-based, không qua send_batch) ---

def test_policy_for_view_accepts_attribute_style_view():
    """``policy_for_view`` nhận cả dict lẫn object có thuộc tính (vd SeatView của E7)."""
    import types

    from crsd.models.scripted import policy_for_view

    view = types.SimpleNamespace(
        seat=0, round_number=2, n_players=6, n_rounds=10, endowment=40.0,
        target=120.0, options=(0.0, 2.0, 4.0), risk_probability=0.9,
        history=((0.0, 4.0, 4.0, 4.0, 4.0, 4.0),),
    )
    assert policy_for_view("scripted:conditional_cooperator")(view) == 4.0
    assert policy_for_view("ev_maximiser")(view) == 2.0
    view.risk_probability = 0.1
    assert policy_for_view("ev_maximiser")(view) == 0.0
    # dict ngữ cảnh cho cùng kết quả
    assert policy_for_view("always_0")(_ctx()) == 0


def test_scripted_module_does_not_hijack_the_e7_reference_policies():
    """E7 (crsd.analysis.scripted_reference) dò tên ``get_policy`` để TỰ ĐỘNG thay
    chính sách của nó. ev_maximiser hai bên khác ngữ nghĩa (bản E7 biết dừng khi
    target đã đạt), nên module này CỐ Ý không expose tên đó — hợp nhất phải là
    quyết định tường minh, không phải tác dụng phụ của việc đặt tên hàm."""
    import crsd.models.scripted as sc

    assert not hasattr(sc, "get_policy")
    assert hasattr(sc, "policy_for_view")
