"""Bộ câu hỏi "prompt comprehension" cho CRSD (phỏng theo Fontana et al. 2024,
"Nicer Than Humans").

Mục tiêu: ĐO xem LLM có HIỂU LUẬT CHƠI của collective-risk game không, theo 3 trục
như paper gốc:
  - ``rules`` : luật TĨNH (mức đóng được phép, vốn, mục tiêu, số vòng, rủi ro, payoff).
  - ``time``  : LỊCH SỬ theo vòng (đang vòng mấy, ai đóng bao nhiêu ở vòng i).
  - ``state`` : THỐNG KÊ TÍCH LUỸ (quỹ hiện có, còn thiếu bao nhiêu, tổng đã đóng…),
                phần lớn đòi CỘNG DỒN qua các vòng -> bài test số học (giống Fig A7
                của paper: khi prompt KHÔNG in sẵn tổng, model phải tự cộng).

Module THUẦN LOGIC (không LLM, không I/O) như ``scoring.py`` -> dễ unit-test & tái lập.
Ground truth tính trực tiếp từ ``GameConfig`` + ``history`` (``history[i][p]`` = đóng
góp của người chơi p ở vòng i+1), tái dùng ``scoring.group_total/player_remaining``.

Quy ước ký hiệu trong file:
  - ``r`` = vòng hiện tại (1-based, vòng SẮP chơi); ``history`` có ``r-1`` hàng.
  - vòng ``i`` (1-based) -> ``history[i-1]``; vị trí người chơi ``x`` (1-based) -> cột ``x-1``.
  - ``player_index`` = ghế (0-based) của agent ĐANG được probe ("you").
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from . import scoring
from .prompt import _fmt
from .state import ComprehensionRecord


# ---------------------------------------------------------------------------
# Parser câu trả lời (clone khuôn ``parse_contribution`` / ``parse_note``)
# ---------------------------------------------------------------------------

_ANSWER_LINE_RE = re.compile(
    r"^\s*ANSWER\s*[:=]\s*(.+?)\s*$", flags=re.IGNORECASE | re.MULTILINE
)


def _parse_int(captured: str) -> Tuple[Optional[int], bool]:
    """Lấy SỐ NGUYÊN ĐẦU TIÊN trong nội dung dòng ANSWER (vị trí 'đáp án là X').

    Chọn số đầu (không phải cuối) để bền với phần bối cảnh phía sau, vd
    'ANSWER: 80 (còn thiếu để đạt 120)' -> 80, không phải 120.
    """
    nums = re.findall(r"-?\d+", captured)
    if not nums:
        return None, True
    return int(nums[0]), False


def _parse_int_set(captured: str) -> Tuple[Optional[set], bool]:
    nums = re.findall(r"-?\d+", captured)
    if not nums:
        return None, True
    return set(int(x) for x in nums), False


def _parse_yesno(captured: str) -> Tuple[Optional[bool], bool]:
    s = captured.strip().lower()
    # Phủ định trước (tránh 'không' bị 'có'/'yes' nuốt — 'không' không chứa 'có').
    if "không" in s or "chưa" in s or re.search(r"\bno\b", s):
        return False, False
    if "có" in s or "rồi" in s or "đã đạt" in s or "yes" in s:
        return True, False
    return None, True


def parse_answer(text: str, kind: str):
    """Trích & chuẩn hoá đáp án từ dòng ``ANSWER: ...`` ĐỊNH DẠNG cuối cùng.

    Neo vào ĐẦU DÒNG (``^`` + MULTILINE), lấy match CUỐI — giống ``parse_note``:
    model hay "suy nghĩ rồi mới chốt", nên dòng ANSWER cuối là câu trả lời thật.

    Returns: ``(parsed, parse_failed)`` với parsed kiểu int / set[int] / bool / None.
    """
    if not text:
        return None, True
    matches = _ANSWER_LINE_RE.findall(text)
    if not matches:
        return None, True
    captured = matches[-1].strip()
    if kind == "int":
        return _parse_int(captured)
    if kind == "int_set":
        return _parse_int_set(captured)
    if kind == "yesno":
        return _parse_yesno(captured)
    return None, True


def score_answer(parsed, ground_truth, kind: str, parse_failed: bool) -> bool:
    """Chấm 1 probe. parse_failed (sai định dạng) -> SAI (conservative).

    Giữ ``parse_failed`` riêng ở record để phân tích nhạy (loại các lượt sai định dạng).
    """
    if parse_failed or parsed is None:
        return False
    if kind == "int":
        return int(parsed) == int(ground_truth)
    if kind == "int_set":
        return set(parsed) == set(int(x) for x in ground_truth)
    if kind == "yesno":
        return bool(parsed) == bool(ground_truth)
    return False


# ---------------------------------------------------------------------------
# Helper: chọn ghế đại diện & chọn vòng quá khứ (tất định, để chặn bùng nổ)
# ---------------------------------------------------------------------------

def _representative_seats(history, player_index: int, n_players: int, k: int) -> List[int]:
    """Trả về tối đa ``k`` ghế (0-based) ĐẠI DIỆN, gồm chính mình + free-rider (đóng ít
    nhất) + altruist (đóng nhiều nhất) + 1 ghế giữa, để giữ TƯƠNG PHẢN mà không hỏi
    cả 6 ghế (chặn bùng nổ). Tất định theo ``history`` (rerun ra y hệt)."""
    if k <= 0:
        return []
    others = [s for s in range(n_players) if s != player_index]
    if not history:
        return ([player_index] + others)[:k]
    totals = [sum(row[s] for row in history) for s in range(n_players)]
    by_total = sorted(others, key=lambda s: (totals[s], s))
    picks = [player_index]
    if by_total:
        picks += [by_total[0], by_total[-1], by_total[len(by_total) // 2]]
    seen, uniq = set(), []
    for s in picks + others:           # ưu tiên ghế đại diện, rồi điền nốt theo thứ tự
        if s not in seen:
            seen.add(s)
            uniq.append(s)
        if len(uniq) >= k:
            break
    return uniq[:k]


def _select_rounds(num_past: int, cap: Optional[int]) -> List[int]:
    """Danh sách vòng quá khứ 1..num_past; nếu vượt ``cap`` thì lấy mẫu CÁCH ĐỀU
    (luôn giữ vòng đầu & cuối), tất định."""
    rounds = list(range(1, num_past + 1))
    if cap is None or num_past <= cap or cap <= 1:
        return rounds
    idxs = sorted(set(round(j * (num_past - 1) / (cap - 1)) for j in range(cap)))
    return [rounds[i] for i in idxs]


def _seat_label(x_pos: int, player_index: int, language: str) -> str:
    """Nhãn vị trí 'P{x}', thêm '(you)/(bạn)' nếu là ghế đang được probe."""
    base = f"P{x_pos}"
    if x_pos - 1 == player_index:
        return base + (" (bạn)" if language == "vn" else " (you)")
    return base


# ---------------------------------------------------------------------------
# QuestionSpec + bảng REGISTRY
# ---------------------------------------------------------------------------

@dataclass
class QuestionSpec:
    """Một LOẠI câu hỏi đọc-hiểu.

    - ``render(cfg, H, r, pi, params, lang) -> str`` : câu hỏi (EN/VN).
    - ``ground_truth(cfg, H, r, pi, params) -> int|set[int]|bool`` : đáp án đúng (engine).
    - ``enum(cfg, H, r, pi, caps) -> list[dict]`` : các bộ tham số cần hỏi.
    - ``answerable(cfg) -> bool`` : đáp án có IN SẴN trong prompt (đọc) hay phải TỰ TÍNH.
    """

    id: str
    category: str          # "rules" | "time" | "state"
    answer_kind: str       # "int" | "int_set" | "yesno"
    render: Callable
    ground_truth: Callable
    enum: Callable
    answerable: Callable


# ----- enum helpers (đóng theo caps) -----

def _enum_none(cfg, H, r, pi, caps):
    return [{}]


def _enum_scalar_state(cfg, H, r, pi, caps):
    # state vô hướng: hỏi mọi vòng (kể cả r=1 -> trạng thái rỗng, GT=0/đầy đủ).
    return [{}]


def _enum_time_rounds(cfg, H, r, pi, caps):
    past = _select_rounds(r - 1, (caps or {}).get("max_past_rounds"))
    return [{"i": i} for i in past]


def _enum_time_action(cfg, H, r, pi, caps):
    past = _select_rounds(r - 1, (caps or {}).get("max_past_rounds"))
    seats = _representative_seats(H, pi, cfg.n_players, (caps or {}).get("max_seats", 4))
    others = [s for s in seats if s != pi]          # 'you' đã có ở time_own_action_i
    return [{"i": i, "x": s + 1} for i in past for s in others]


def _enum_state_x_total(cfg, H, r, pi, caps):
    if r <= 1:
        return []                                    # chưa có lịch sử -> bỏ
    seats = _representative_seats(H, pi, cfg.n_players, (caps or {}).get("max_seats", 4))
    others = [s for s in seats if s != pi]           # 'you' đã có ở state_own_total
    return [{"x": s + 1} for s in others]


def _enum_state_count(cfg, H, r, pi, caps):
    if r <= 1:
        return []
    seats = _representative_seats(H, pi, cfg.n_players, (caps or {}).get("max_seats", 4))
    return [{"x": s + 1, "p": int(p)} for s in seats for p in cfg.contribution_options]


# ----- ground-truth helpers -----

def _pool(H) -> int:
    return int(sum(scoring.group_total(row) for row in H))


def _own_total(H, pi) -> int:
    return int(sum(row[pi] for row in H))


# ----- render helpers (EN/VN) -----

def _opts_str(cfg) -> str:
    return ", ".join(_fmt(o) for o in cfg.contribution_options)


REGISTRY: List[QuestionSpec] = [
    # ===================== RULES (đáp án in sẵn trong luật) =====================
    QuestionSpec(
        "rules_actions", "rules", "int_set",
        lambda cfg, H, r, pi, p, lang: (
            "Mỗi vòng bạn được phép chọn những mức đóng góp nào?" if lang == "vn"
            else "Which contribution amounts are you allowed to choose each round?"),
        lambda cfg, H, r, pi, p: set(int(o) for o in cfg.contribution_options),
        _enum_none, lambda cfg: True),
    QuestionSpec(
        "rules_endowment", "rules", "int",
        lambda cfg, H, r, pi, p, lang: (
            "Mỗi người chơi nhận bao nhiêu đơn vị tiền làm vốn ban đầu?" if lang == "vn"
            else "How many monetary units did each player receive as their starting endowment?"),
        lambda cfg, H, r, pi, p: int(round(cfg.endowment)),
        _enum_none, lambda cfg: True),
    QuestionSpec(
        "rules_target", "rules", "int",
        lambda cfg, H, r, pi, p, lang: (
            "Tổng đóng góp của tất cả người chơi phải đạt ít nhất bao nhiêu vào cuối trò chơi để tránh rủi ro?"
            if lang == "vn" else
            "What combined total must all players reach by the end of the game to avoid the risk?"),
        lambda cfg, H, r, pi, p: int(round(cfg.target)),
        _enum_none, lambda cfg: True),
    QuestionSpec(
        "rules_n_rounds", "rules", "int",
        lambda cfg, H, r, pi, p, lang: (
            "Trò chơi kéo dài tổng cộng bao nhiêu vòng?" if lang == "vn"
            else "How many rounds does the game last in total?"),
        lambda cfg, H, r, pi, p: int(cfg.n_rounds),
        _enum_none, lambda cfg: True),
    QuestionSpec(
        "rules_risk_pct", "rules", "int",
        lambda cfg, H, r, pi, p, lang: (
            "Nếu nhóm KHÔNG đạt mục tiêu, xác suất (theo phần trăm, 0-100) mọi người mất hết số tiền còn lại là bao nhiêu?"
            if lang == "vn" else
            "If the group does NOT reach the target, what is the percent chance (0-100) that everyone loses all of their remaining money?"),
        lambda cfg, H, r, pi, p: int(round(cfg.risk_probability * 100)),
        _enum_none, lambda cfg: True),
    QuestionSpec(
        "rules_payoff_disaster", "rules", "int",
        lambda cfg, H, r, pi, p, lang: (
            "Nếu nhóm không đạt mục tiêu và thảm hoạ XẢY RA, số tiền mặt cuối cùng của bạn là bao nhiêu?"
            if lang == "vn" else
            "If the group fails to reach the target and the disaster does strike, what is your final cash payoff?"),
        lambda cfg, H, r, pi, p: 0,
        _enum_none, lambda cfg: True),
    QuestionSpec(
        "rules_max_contrib", "rules", "int",
        lambda cfg, H, r, pi, p, lang: (
            "Mức LỚN NHẤT mà một người chơi có thể bỏ vào quỹ khí hậu trong một vòng là bao nhiêu?"
            if lang == "vn" else
            "What is the largest amount any single player may put into the climate account in one round?"),
        lambda cfg, H, r, pi, p: int(max(cfg.contribution_options)),
        _enum_none, lambda cfg: True),
    QuestionSpec(
        "rules_min_contrib", "rules", "int",
        lambda cfg, H, r, pi, p, lang: (
            "Mức NHỎ NHẤT mà một người chơi có thể bỏ vào quỹ khí hậu trong một vòng là bao nhiêu?"
            if lang == "vn" else
            "What is the smallest amount any single player may put into the climate account in one round?"),
        lambda cfg, H, r, pi, p: int(min(cfg.contribution_options)),
        _enum_none, lambda cfg: True),

    # ===================== TIME (tra cứu lịch sử) =====================
    QuestionSpec(
        "time_round", "time", "int",
        lambda cfg, H, r, pi, p, lang: (
            "Trò chơi hiện đang ở vòng nào (vòng bạn sắp chơi)?" if lang == "vn"
            else "Which round is the game currently in (the round you are about to play)?"),
        lambda cfg, H, r, pi, p: int(r),
        _enum_none, lambda cfg: True),
    QuestionSpec(
        "time_action_i", "time", "int",
        lambda cfg, H, r, pi, p, lang: (
            f"Ở vòng {p['i']}, người chơi ở vị trí {_seat_label(p['x'], pi, lang)} đã bỏ bao nhiêu vào quỹ khí hậu?"
            if lang == "vn" else
            f"In round {p['i']}, how much did the player in position {_seat_label(p['x'], pi, lang)} put into the climate account?"),
        lambda cfg, H, r, pi, p: int(H[p["i"] - 1][p["x"] - 1]),
        _enum_time_action, lambda cfg: bool(cfg.show_individual_contributions)),
    QuestionSpec(
        "time_own_action_i", "time", "int",
        lambda cfg, H, r, pi, p, lang: (
            f"Ở vòng {p['i']}, BẠN (vị trí P{pi + 1}) đã bỏ bao nhiêu vào quỹ khí hậu?"
            if lang == "vn" else
            f"In round {p['i']}, how much did YOU (position P{pi + 1}) put into the climate account?"),
        lambda cfg, H, r, pi, p: int(H[p["i"] - 1][pi]),
        _enum_time_rounds, lambda cfg: bool(cfg.show_individual_contributions)),
    QuestionSpec(
        "time_round_total_i", "time", "int",
        lambda cfg, H, r, pi, p, lang: (
            f"Ở vòng {p['i']}, tổng số tiền mà cả {cfg.n_players} người chơi bỏ vào quỹ khí hậu là bao nhiêu?"
            if lang == "vn" else
            f"In round {p['i']}, what was the combined total that all {cfg.n_players} players put into the climate account?"),
        lambda cfg, H, r, pi, p: int(scoring.group_total(H[p["i"] - 1])),
        _enum_time_rounds, lambda cfg: False),

    # ===================== STATE (thống kê tích luỹ — phần lớn phải tự cộng) =====================
    QuestionSpec(
        "state_pool", "state", "int",
        lambda cfg, H, r, pi, p, lang: (
            "Tính tất cả các vòng đã chơi đến giờ, hiện quỹ khí hậu có tổng cộng bao nhiêu (gộp mọi người chơi)?"
            if lang == "vn" else
            "Across all rounds played so far, what is the total amount currently in the climate account (all players combined)?"),
        lambda cfg, H, r, pi, p: _pool(H),
        _enum_scalar_state, lambda cfg: bool(cfg.show_cumulative)),
    QuestionSpec(
        "state_remaining_to_target", "state", "int",
        lambda cfg, H, r, pi, p, lang: (
            "Nhóm còn phải bỏ thêm bao nhiêu nữa vào quỹ khí hậu để đạt mục tiêu?" if lang == "vn"
            else "How much more must the group still put into the climate account to reach the target?"),
        lambda cfg, H, r, pi, p: int(max(0, int(round(cfg.target)) - _pool(H))),
        _enum_scalar_state, lambda cfg: False),
    QuestionSpec(
        "state_X_total", "state", "int",
        lambda cfg, H, r, pi, p, lang: (
            f"Tính tất cả các vòng đến giờ, người chơi ở vị trí {_seat_label(p['x'], pi, lang)} đã bỏ tổng cộng bao nhiêu vào quỹ khí hậu?"
            if lang == "vn" else
            f"Across all rounds so far, what is the total amount the player in position {_seat_label(p['x'], pi, lang)} has put into the climate account?"),
        lambda cfg, H, r, pi, p: int(sum(row[p["x"] - 1] for row in H)),
        _enum_state_x_total, lambda cfg: False),
    QuestionSpec(
        "state_own_total", "state", "int",
        lambda cfg, H, r, pi, p, lang: (
            f"Tính tất cả các vòng đến giờ, BẠN (vị trí P{pi + 1}) đã bỏ tổng cộng bao nhiêu vào quỹ khí hậu?"
            if lang == "vn" else
            f"Across all rounds so far, what is the total amount YOU (position P{pi + 1}) have put into the climate account?"),
        lambda cfg, H, r, pi, p: _own_total(H, pi),
        _enum_scalar_state, lambda cfg: False),
    QuestionSpec(
        "state_own_remaining", "state", "int",   # CONTROL: số này IN SẴN trong prompt
        lambda cfg, H, r, pi, p, lang: (
            "Ngay lúc này, bạn còn lại bao nhiêu trong khoản vốn của mình (phần chưa đóng góp)?"
            if lang == "vn" else
            "Right now, how much of your own endowment do you have left (the part not yet contributed)?"),
        lambda cfg, H, r, pi, p: int(round(scoring.player_remaining(cfg.endowment, _own_total(H, pi)))),
        _enum_scalar_state, lambda cfg: True),
    QuestionSpec(
        "state_count_p", "state", "int",
        lambda cfg, H, r, pi, p, lang: (
            f"Tính tất cả các vòng đến giờ, người chơi ở vị trí {_seat_label(p['x'], pi, lang)} đã đóng đúng {_fmt(p['p'])} bao nhiêu lần?"
            if lang == "vn" else
            f"Across all rounds so far, how many times has the player in position {_seat_label(p['x'], pi, lang)} contributed exactly {_fmt(p['p'])}?"),
        lambda cfg, H, r, pi, p: int(sum(1 for row in H if int(row[p["x"] - 1]) == int(p["p"]))),
        _enum_state_count, lambda cfg: False),
    QuestionSpec(
        "state_rounds_left", "state", "int",
        lambda cfg, H, r, pi, p, lang: (
            "Tính CẢ vòng hiện tại, còn lại bao nhiêu vòng để chơi?" if lang == "vn"
            else "Including the current round, how many rounds are left to play?"),
        lambda cfg, H, r, pi, p: int(cfg.n_rounds - r + 1),
        _enum_scalar_state, lambda cfg: False),
    QuestionSpec(
        "state_target_reached", "state", "yesno",
        lambda cfg, H, r, pi, p, lang: (
            "Nhóm đã đạt mục tiêu chưa? Trả lời có hoặc không." if lang == "vn"
            else "Has the group already reached the target? Answer yes or no."),
        lambda cfg, H, r, pi, p: bool(_pool(H) >= int(round(cfg.target))),
        _enum_scalar_state, lambda cfg: False),
]


REGISTRY_BY_ID = {q.id: q for q in REGISTRY}


def _jsonable(v):
    """set -> list đã sắp xếp (để json.dumps được); còn lại giữ nguyên."""
    if isinstance(v, set):
        return sorted(v)
    return v


def make_record(meta: dict, raw_response: str) -> ComprehensionRecord:
    """Parse + chấm 1 probe rồi dựng ``ComprehensionRecord``.

    ``meta`` do ``CrsdGame.build_comprehension_prompts`` sinh (mọi trường tĩnh đã có,
    chỉ thiếu phần đáp án của model).
    """
    kind = meta["answer_kind"]
    parsed, parse_failed = parse_answer(raw_response or "", kind)
    correct = score_answer(parsed, meta["ground_truth"], kind, parse_failed)
    return ComprehensionRecord(
        game_id=meta["game_id"], round=meta["round"], player=meta["player"],
        player_index=meta["player_index"], question_id=meta["question_id"],
        category=meta["category"], params=dict(meta["params"]),
        question_text=meta["question_text"], raw_response=raw_response or "",
        parsed_answer=_jsonable(parsed), ground_truth=_jsonable(meta["ground_truth"]),
        correct=bool(correct), parse_failed=bool(parse_failed), answer_kind=kind,
        answerable_from_prompt=bool(meta["answerable_from_prompt"]),
        language=meta["language"], risk_probability=meta["risk_probability"],
        model=meta["model"], show_cumulative=bool(meta["show_cumulative"]),
        sampling_seed=meta["sampling_seed"],
    )


def iter_questions(cfg, history, current_round, player_index, caps=None):
    """Sinh toàn bộ (spec, params) cần hỏi ở một trạng thái game.

    ``caps`` (dict, tuỳ chọn):
      - ``max_seats``       : số ghế tối đa cho câu hỏi theo người chơi (mặc định 4).
      - ``max_past_rounds`` : cắt số vòng quá khứ cho câu hỏi Time (None = tất cả).
      - ``include_rules``   : có hỏi nhóm Rules ở vòng này không (mặc định True).
                              Runner đặt False ở các vòng ngoài ``rulesCheckpoints``.
    """
    caps = caps or {}
    include_rules = caps.get("include_rules", True)
    out = []
    for spec in REGISTRY:
        if spec.category == "rules" and not include_rules:
            continue
        for params in spec.enum(cfg, history, current_round, player_index, caps):
            out.append((spec, params))
    return out
