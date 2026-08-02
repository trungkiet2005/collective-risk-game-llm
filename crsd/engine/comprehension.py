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
from .prompt import _fmt, _lang
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


_NO_MARKERS = ("không", "chưa", "non", "否", "没有", "不", "لا")
_YES_MARKERS = ("có", "rồi", "đã đạt", "oui", "是", "已", "有", "نعم")


def _parse_yesno(captured: str) -> Tuple[Optional[bool], bool]:
    s = captured.strip().lower()
    # Phủ định trước (tránh dấu hiệu "có/yes" bị nuốt bởi câu phủ định chứa nó,
    # vd zh "不是" chứa "是" nhưng phải chấm là "không" vì bắt được "不" trước).
    if re.search(r"\bno\b", s) or any(m in s for m in _NO_MARKERS):
        return False, False
    if re.search(r"\byes\b", s) or any(m in s for m in _YES_MARKERS):
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
    """Nhãn vị trí 'P{x}', thêm marker 'bạn/you/vous/你/أنت' nếu là ghế đang probe.

    Tái dùng bảng ``_LANG_STRINGS`` của prompt.py (key "you") để khỏi lặp danh sách
    ngôn ngữ hỗ trợ ở hai chỗ.
    """
    base = f"P{x_pos}"
    if x_pos - 1 == player_index:
        return base + " " + _lang(language)["you"]
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


# ----- render helpers (EN/VN/FR/ZH/AR) -----

def _opts_str(cfg) -> str:
    return ", ".join(_fmt(o) for o in cfg.contribution_options)


def _tr(lang: str, strings: dict) -> str:
    """Chọn chuỗi câu hỏi theo ngôn ngữ, fallback English nếu thiếu bản dịch.

    Dùng cùng ``_Q_TEXT`` dưới đây cho MỌI QuestionSpec -> thêm ngôn ngữ mới chỉ
    cần thêm key vào từng entry, không phải sửa logic từng lambda.
    """
    return strings.get(lang, strings["en"])


# Bảng câu hỏi đọc-hiểu theo 5 ngôn ngữ. Câu có tham số ({i}/{seat}/{n}/{pnum}/{p})
# là chuỗi .format()-able; render lambda truyền tham số vào sau khi _tr() chọn ngôn ngữ.
_Q_TEXT = {
    "rules_actions": {
        "en": "Which contribution amounts are you allowed to choose each round?",
        "vn": "Mỗi vòng bạn được phép chọn những mức đóng góp nào?",
        "fr": "Quelles sont les montants de contribution que vous pouvez choisir à chaque manche ?",
        "zh": "每一轮你可以选择哪些投入金额？",
        "ar": "ما هي مبالغ المساهمة المسموح لك باختيارها في كل جولة؟",
    },
    "rules_endowment": {
        "en": "How many monetary units did each player receive as their starting endowment?",
        "vn": "Mỗi người chơi nhận bao nhiêu đơn vị tiền làm vốn ban đầu?",
        "fr": "Combien d'unités monétaires chaque joueur a-t-il reçu comme dotation de départ ?",
        "zh": "每位玩家获得了多少个货币单位作为初始资金？",
        "ar": "كم عدد الوحدات النقدية التي حصل عليها كل لاعب كمخصصات ابتدائية؟",
    },
    "rules_target": {
        "en": "What combined total must all players reach by the end of the game to avoid the risk?",
        "vn": "Tổng đóng góp của tất cả người chơi phải đạt ít nhất bao nhiêu vào cuối trò chơi để tránh rủi ro?",
        "fr": "Quel total combiné tous les joueurs doivent-ils atteindre d'ici la fin de la partie pour éviter le risque ?",
        "zh": "到游戏结束时，全体玩家的总投入必须达到多少才能避免风险？",
        "ar": "ما هو المجموع الذي يجب أن يصل إليه جميع اللاعبين بحلول نهاية اللعبة لتجنب المخاطرة؟",
    },
    "rules_n_rounds": {
        "en": "How many rounds does the game last in total?",
        "vn": "Trò chơi kéo dài tổng cộng bao nhiêu vòng?",
        "fr": "Combien de manches dure la partie au total ?",
        "zh": "游戏总共持续多少轮？",
        "ar": "كم عدد الجولات التي تستمر فيها اللعبة إجمالاً؟",
    },
    "rules_risk_pct": {
        "en": "If the group does NOT reach the target, what is the percent chance (0-100) that everyone loses all of their remaining money?",
        "vn": "Nếu nhóm KHÔNG đạt mục tiêu, xác suất (theo phần trăm, 0-100) mọi người mất hết số tiền còn lại là bao nhiêu?",
        "fr": "Si le groupe n'atteint PAS l'objectif, quelle est la probabilité (en pourcentage, 0-100) que tout le monde perde tout l'argent qu'il lui reste ?",
        "zh": "如果小组未达到目标，所有人失去剩余全部资金的概率（百分比，0-100）是多少？",
        "ar": "إذا لم تحقق المجموعة الهدف، ما هي نسبة الاحتمال (0-100) أن يخسر الجميع كل ما تبقى من أموالهم؟",
    },
    "rules_payoff_disaster": {
        "en": "If the group fails to reach the target and the disaster does strike, what is your final cash payoff?",
        "vn": "Nếu nhóm không đạt mục tiêu và thảm hoạ XẢY RA, số tiền mặt cuối cùng của bạn là bao nhiêu?",
        "fr": "Si le groupe n'atteint pas l'objectif et que la catastrophe SURVIENT, quel est votre gain final en argent ?",
        "zh": "如果小组未达到目标且灾难确实发生了，你最终的现金收益是多少？",
        "ar": "إذا لم تحقق المجموعة الهدف ووقعت الكارثة فعلاً، ما هو صافي ربحك النقدي النهائي؟",
    },
    "rules_max_contrib": {
        "en": "What is the largest amount any single player may put into the climate account in one round?",
        "vn": "Mức LỚN NHẤT mà một người chơi có thể bỏ vào quỹ khí hậu trong một vòng là bao nhiêu?",
        "fr": "Quel est le montant le PLUS ÉLEVÉ qu'un seul joueur peut verser dans le compte climat en une manche ?",
        "zh": "单个玩家在一轮中最多可以向气候账户投入多少？",
        "ar": "ما هو أكبر مبلغ يمكن لأي لاعب واحد وضعه في حساب المناخ في جولة واحدة؟",
    },
    "rules_min_contrib": {
        "en": "What is the smallest amount any single player may put into the climate account in one round?",
        "vn": "Mức NHỎ NHẤT mà một người chơi có thể bỏ vào quỹ khí hậu trong một vòng là bao nhiêu?",
        "fr": "Quel est le montant le PLUS FAIBLE qu'un seul joueur peut verser dans le compte climat en une manche ?",
        "zh": "单个玩家在一轮中最少可以向气候账户投入多少？",
        "ar": "ما هو أصغر مبلغ يمكن لأي لاعب واحد وضعه في حساب المناخ في جولة واحدة؟",
    },
    "time_round": {
        "en": "Which round is the game currently in (the round you are about to play)?",
        "vn": "Trò chơi hiện đang ở vòng nào (vòng bạn sắp chơi)?",
        "fr": "À quelle manche la partie en est-elle actuellement (la manche que vous allez jouer) ?",
        "zh": "游戏目前正处于第几轮（你即将进行的这一轮）？",
        "ar": "في أي جولة تجري اللعبة حاليًا (الجولة التي أنت على وشك لعبها)؟",
    },
    "time_action_i": {
        "en": "In round {i}, how much did the player in position {seat} put into the climate account?",
        "vn": "Ở vòng {i}, người chơi ở vị trí {seat} đã bỏ bao nhiêu vào quỹ khí hậu?",
        "fr": "À la manche {i}, combien le joueur en position {seat} a-t-il versé dans le compte climat ?",
        "zh": "在第{i}轮，位于{seat}位置的玩家向气候账户投入了多少？",
        "ar": "في الجولة {i}، كم ساهم اللاعب في الموضع {seat} في حساب المناخ؟",
    },
    "time_own_action_i": {
        "en": "In round {i}, how much did YOU (position P{pnum}) put into the climate account?",
        "vn": "Ở vòng {i}, BẠN (vị trí P{pnum}) đã bỏ bao nhiêu vào quỹ khí hậu?",
        "fr": "À la manche {i}, combien VOUS (position P{pnum}) avez-vous versé dans le compte climat ?",
        "zh": "在第{i}轮，你（位置P{pnum}）向气候账户投入了多少？",
        "ar": "في الجولة {i}، كم ساهمتَ أنت (الموضع P{pnum}) في حساب المناخ؟",
    },
    "time_round_total_i": {
        "en": "In round {i}, what was the combined total that all {n} players put into the climate account?",
        "vn": "Ở vòng {i}, tổng số tiền mà cả {n} người chơi bỏ vào quỹ khí hậu là bao nhiêu?",
        "fr": "À la manche {i}, quel était le total combiné versé dans le compte climat par les {n} joueurs ?",
        "zh": "在第{i}轮，全体{n}名玩家向气候账户投入的总额是多少？",
        "ar": "في الجولة {i}، ما هو المجموع الذي وضعه جميع اللاعبين الـ{n} في حساب المناخ؟",
    },
    "state_pool": {
        "en": "Across all rounds played so far, what is the total amount currently in the climate account (all players combined)?",
        "vn": "Tính tất cả các vòng đã chơi đến giờ, hiện quỹ khí hậu có tổng cộng bao nhiêu (gộp mọi người chơi)?",
        "fr": "En comptant toutes les manches jouées jusqu'à présent, quel est le montant total actuellement dans le compte climat (tous joueurs confondus) ?",
        "zh": "计算到目前为止已进行的所有轮次，气候账户目前的总金额（所有玩家合计）是多少？",
        "ar": "بحساب جميع الجولات الملعوبة حتى الآن، ما هو المبلغ الإجمالي الموجود حاليًا في حساب المناخ (جميع اللاعبين مجتمعين)؟",
    },
    "state_remaining_to_target": {
        "en": "How much more must the group still put into the climate account to reach the target?",
        "vn": "Nhóm còn phải bỏ thêm bao nhiêu nữa vào quỹ khí hậu để đạt mục tiêu?",
        "fr": "Combien le groupe doit-il encore verser dans le compte climat pour atteindre l'objectif ?",
        "zh": "小组还需要向气候账户再投入多少才能达到目标？",
        "ar": "كم يجب أن تضع المجموعة أيضًا في حساب المناخ للوصول إلى الهدف؟",
    },
    "state_X_total": {
        "en": "Across all rounds so far, what is the total amount the player in position {seat} has put into the climate account?",
        "vn": "Tính tất cả các vòng đến giờ, người chơi ở vị trí {seat} đã bỏ tổng cộng bao nhiêu vào quỹ khí hậu?",
        "fr": "En comptant toutes les manches jusqu'à présent, quel est le montant total versé dans le compte climat par le joueur en position {seat} ?",
        "zh": "计算到目前为止的所有轮次，位于{seat}位置的玩家总共向气候账户投入了多少？",
        "ar": "بحساب جميع الجولات حتى الآن، ما هو المبلغ الإجمالي الذي وضعه اللاعب في الموضع {seat} في حساب المناخ؟",
    },
    "state_own_total": {
        "en": "Across all rounds so far, what is the total amount YOU (position P{pnum}) have put into the climate account?",
        "vn": "Tính tất cả các vòng đến giờ, BẠN (vị trí P{pnum}) đã bỏ tổng cộng bao nhiêu vào quỹ khí hậu?",
        "fr": "En comptant toutes les manches jusqu'à présent, quel est le montant total que VOUS (position P{pnum}) avez versé dans le compte climat ?",
        "zh": "计算到目前为止的所有轮次，你（位置P{pnum}）总共向气候账户投入了多少？",
        "ar": "بحساب جميع الجولات حتى الآن، ما هو المبلغ الإجمالي الذي وضعتَه أنت (الموضع P{pnum}) في حساب المناخ؟",
    },
    "state_own_remaining": {
        "en": "Right now, how much of your own endowment do you have left (the part not yet contributed)?",
        "vn": "Ngay lúc này, bạn còn lại bao nhiêu trong khoản vốn của mình (phần chưa đóng góp)?",
        "fr": "En ce moment, combien vous reste-t-il de votre propre dotation (la part non encore contribuée) ?",
        "zh": "现在，你自己的资金还剩多少（尚未投入的部分）？",
        "ar": "الآن، كم تبقى من مخصصاتك الخاصة (الجزء الذي لم تساهم به بعد)؟",
    },
    "state_count_p": {
        "en": "Across all rounds so far, how many times has the player in position {seat} contributed exactly {p}?",
        "vn": "Tính tất cả các vòng đến giờ, người chơi ở vị trí {seat} đã đóng đúng {p} bao nhiêu lần?",
        "fr": "En comptant toutes les manches jusqu'à présent, combien de fois le joueur en position {seat} a-t-il contribué exactement {p} ?",
        "zh": "计算到目前为止的所有轮次，位于{seat}位置的玩家恰好投入{p}的次数是多少？",
        "ar": "بحساب جميع الجولات حتى الآن، كم مرة ساهم اللاعب في الموضع {seat} بمبلغ {p} بالضبط؟",
    },
    "state_rounds_left": {
        "en": "Including the current round, how many rounds are left to play?",
        "vn": "Tính CẢ vòng hiện tại, còn lại bao nhiêu vòng để chơi?",
        "fr": "En comptant la manche actuelle, combien de manches reste-t-il à jouer ?",
        "zh": "包括当前这一轮，还剩多少轮要玩？",
        "ar": "بما في ذلك الجولة الحالية، كم عدد الجولات المتبقية للعب؟",
    },
    "state_target_reached": {
        "en": "Has the group already reached the target? Answer yes or no.",
        "vn": "Nhóm đã đạt mục tiêu chưa? Trả lời có hoặc không.",
        "fr": "Le groupe a-t-il déjà atteint l'objectif ? Répondez par oui ou non.",
        "zh": "小组是否已经达到目标？请回答是或否。",
        "ar": "هل حققت المجموعة الهدف بالفعل؟ أجب بنعم أو لا.",
    },
}


REGISTRY: List[QuestionSpec] = [
    # ===================== RULES (đáp án in sẵn trong luật) =====================
    QuestionSpec(
        "rules_actions", "rules", "int_set",
        lambda cfg, H, r, pi, p, lang: _tr(lang, _Q_TEXT["rules_actions"]),
        lambda cfg, H, r, pi, p: set(int(o) for o in cfg.contribution_options),
        _enum_none, lambda cfg: True),
    QuestionSpec(
        "rules_endowment", "rules", "int",
        lambda cfg, H, r, pi, p, lang: _tr(lang, _Q_TEXT["rules_endowment"]),
        lambda cfg, H, r, pi, p: int(round(cfg.endowment)),
        _enum_none, lambda cfg: True),
    QuestionSpec(
        "rules_target", "rules", "int",
        lambda cfg, H, r, pi, p, lang: _tr(lang, _Q_TEXT["rules_target"]),
        lambda cfg, H, r, pi, p: int(round(cfg.target)),
        _enum_none, lambda cfg: True),
    QuestionSpec(
        "rules_n_rounds", "rules", "int",
        lambda cfg, H, r, pi, p, lang: _tr(lang, _Q_TEXT["rules_n_rounds"]),
        lambda cfg, H, r, pi, p: int(cfg.n_rounds),
        _enum_none, lambda cfg: True),
    QuestionSpec(
        "rules_risk_pct", "rules", "int",
        lambda cfg, H, r, pi, p, lang: _tr(lang, _Q_TEXT["rules_risk_pct"]),
        lambda cfg, H, r, pi, p: int(round(cfg.risk_probability * 100)),
        _enum_none, lambda cfg: True),
    QuestionSpec(
        "rules_payoff_disaster", "rules", "int",
        lambda cfg, H, r, pi, p, lang: _tr(lang, _Q_TEXT["rules_payoff_disaster"]),
        lambda cfg, H, r, pi, p: 0,
        _enum_none, lambda cfg: True),
    QuestionSpec(
        "rules_max_contrib", "rules", "int",
        lambda cfg, H, r, pi, p, lang: _tr(lang, _Q_TEXT["rules_max_contrib"]),
        lambda cfg, H, r, pi, p: int(max(cfg.contribution_options)),
        _enum_none, lambda cfg: True),
    QuestionSpec(
        "rules_min_contrib", "rules", "int",
        lambda cfg, H, r, pi, p, lang: _tr(lang, _Q_TEXT["rules_min_contrib"]),
        lambda cfg, H, r, pi, p: int(min(cfg.contribution_options)),
        _enum_none, lambda cfg: True),

    # ===================== TIME (tra cứu lịch sử) =====================
    QuestionSpec(
        "time_round", "time", "int",
        lambda cfg, H, r, pi, p, lang: _tr(lang, _Q_TEXT["time_round"]),
        lambda cfg, H, r, pi, p: int(r),
        _enum_none, lambda cfg: True),
    QuestionSpec(
        "time_action_i", "time", "int",
        lambda cfg, H, r, pi, p, lang: _tr(lang, _Q_TEXT["time_action_i"]).format(
            i=p["i"], seat=_seat_label(p["x"], pi, lang)),
        lambda cfg, H, r, pi, p: int(H[p["i"] - 1][p["x"] - 1]),
        _enum_time_action, lambda cfg: bool(cfg.show_individual_contributions)),
    QuestionSpec(
        "time_own_action_i", "time", "int",
        lambda cfg, H, r, pi, p, lang: _tr(lang, _Q_TEXT["time_own_action_i"]).format(
            i=p["i"], pnum=pi + 1),
        lambda cfg, H, r, pi, p: int(H[p["i"] - 1][pi]),
        _enum_time_rounds, lambda cfg: bool(cfg.show_individual_contributions)),
    QuestionSpec(
        "time_round_total_i", "time", "int",
        lambda cfg, H, r, pi, p, lang: _tr(lang, _Q_TEXT["time_round_total_i"]).format(
            i=p["i"], n=cfg.n_players),
        lambda cfg, H, r, pi, p: int(scoring.group_total(H[p["i"] - 1])),
        _enum_time_rounds, lambda cfg: False),

    # ===================== STATE (thống kê tích luỹ — phần lớn phải tự cộng) =====================
    QuestionSpec(
        "state_pool", "state", "int",
        lambda cfg, H, r, pi, p, lang: _tr(lang, _Q_TEXT["state_pool"]),
        lambda cfg, H, r, pi, p: _pool(H),
        _enum_scalar_state, lambda cfg: bool(cfg.show_cumulative)),
    QuestionSpec(
        "state_remaining_to_target", "state", "int",
        lambda cfg, H, r, pi, p, lang: _tr(lang, _Q_TEXT["state_remaining_to_target"]),
        lambda cfg, H, r, pi, p: int(max(0, int(round(cfg.target)) - _pool(H))),
        _enum_scalar_state, lambda cfg: False),
    QuestionSpec(
        "state_X_total", "state", "int",
        lambda cfg, H, r, pi, p, lang: _tr(lang, _Q_TEXT["state_X_total"]).format(
            seat=_seat_label(p["x"], pi, lang)),
        lambda cfg, H, r, pi, p: int(sum(row[p["x"] - 1] for row in H)),
        _enum_state_x_total, lambda cfg: False),
    QuestionSpec(
        "state_own_total", "state", "int",
        lambda cfg, H, r, pi, p, lang: _tr(lang, _Q_TEXT["state_own_total"]).format(pnum=pi + 1),
        lambda cfg, H, r, pi, p: _own_total(H, pi),
        _enum_scalar_state, lambda cfg: False),
    QuestionSpec(
        "state_own_remaining", "state", "int",   # CONTROL: số này IN SẴN trong prompt
        lambda cfg, H, r, pi, p, lang: _tr(lang, _Q_TEXT["state_own_remaining"]),
        lambda cfg, H, r, pi, p: int(round(scoring.player_remaining(cfg.endowment, _own_total(H, pi)))),
        _enum_scalar_state, lambda cfg: True),
    QuestionSpec(
        "state_count_p", "state", "int",
        lambda cfg, H, r, pi, p, lang: _tr(lang, _Q_TEXT["state_count_p"]).format(
            seat=_seat_label(p["x"], pi, lang), p=_fmt(p["p"])),
        lambda cfg, H, r, pi, p: int(sum(1 for row in H if int(row[p["x"] - 1]) == int(p["p"]))),
        _enum_state_count, lambda cfg: False),
    QuestionSpec(
        "state_rounds_left", "state", "int",
        lambda cfg, H, r, pi, p, lang: _tr(lang, _Q_TEXT["state_rounds_left"]),
        lambda cfg, H, r, pi, p: int(cfg.n_rounds - r + 1),
        _enum_scalar_state, lambda cfg: False),
    QuestionSpec(
        "state_target_reached", "state", "yesno",
        lambda cfg, H, r, pi, p, lang: _tr(lang, _Q_TEXT["state_target_reached"]),
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
