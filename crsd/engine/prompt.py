"""Dựng prompt cho agent từ template.

Phong cách template mô phỏng FairGame:
  - Placeholder đơn: ``{tenBien}``
  - Block điều kiện: ``{tenBlock}: [ ... nội dung ... ]`` — giữ nội dung nếu
    điều kiện bật, ngược lại bỏ cả block.

Các block dùng trong template CRSD:
  - ``persona``       : bật khi agent có persona (non-empty)
  - ``framing``       : bật khi cfg.framing=True (khung dẫn nhập trung lập)
  - ``gameLength``    : bật khi agent biết số vòng (nRoundsIsKnown)
  - ``history``       : (full_history) nạp lại TOÀN BỘ đóng góp từng vòng
  - ``showCumulative``/``noCumulative`` : có/không hiển thị tổng tích luỹ
  - ``lastRound``     : (scratchpad) chỉ hiển thị ``memory_window`` vòng gần nhất
  - ``scratchpadNote``: (scratchpad) hiển thị ghi chú riêng của chính agent
"""
from __future__ import annotations

import re
from typing import List

_BLOCK_RE = re.compile(r"\{(\w+)\}:\s*\[(.*?)\]", re.DOTALL)


def _fmt(x) -> str:
    """40.0 -> '40'; 0.9 -> '0.9' (tránh đuôi .0 thừa trong prompt)."""
    if isinstance(x, float) and x.is_integer():
        return str(int(x))
    return str(x)


def _resolve_blocks(template: str, enabled: dict) -> str:
    def repl(m: "re.Match") -> str:
        name = m.group(1)
        body = m.group(2)
        return body if enabled.get(name, False) else ""

    return _BLOCK_RE.sub(repl, template)


def build_history_text(history: List[List[float]], player_index: int, cfg, language: str) -> str:
    """Mô tả các vòng trước cho người chơi.

    Trung thành với Milinski 2008: hiển thị đóng góp 6 người theo VỊ TRÍ CỐ ĐỊNH
    (P1..Pn, đánh dấu "you") để có thể nhận diện free-rider/altruist qua các vòng,
    nhưng KHÔNG tiết lộ tổng tích luỹ trừ khi ``cfg.show_cumulative`` bật.
    """
    if not history:
        return ""
    show_cum = getattr(cfg, "show_cumulative", False)
    lines: List[str] = []
    cumulative = 0.0
    for r, round_contribs in enumerate(history, start=1):
        total = sum(round_contribs)
        cumulative += total
        own = round_contribs[player_index]
        if cfg.show_individual_contributions:
            labeled = ", ".join(
                f"P{i + 1}{('(bạn)' if language == 'vn' else '(you)') if i == player_index else ''}={_fmt(c)}"
                for i, c in enumerate(round_contribs)
            )
            if language == "vn":
                line = f"Vòng {r}: {labeled}"
                line += f" (tích luỹ {_fmt(cumulative)})." if show_cum else "."
            else:
                line = f"Round {r}: {labeled}"
                line += f" (cumulative {_fmt(cumulative)})." if show_cum else "."
        else:
            if language == "vn":
                line = f"Vòng {r}: bạn đóng {_fmt(own)}; tổng nhóm vòng này {_fmt(total)}"
                line += f"; tích luỹ {_fmt(cumulative)}." if show_cum else "."
            else:
                line = f"Round {r}: you contributed {_fmt(own)}; group round total {_fmt(total)}"
                line += f"; cumulative {_fmt(cumulative)}." if show_cum else "."
        lines.append(line)
    return "\n".join(lines)


def build_per_player_totals(history, player_index, cfg, language) -> str:
    """Tổng đóng góp TÍCH LUỸ của TỪNG người chơi (P1..Pn) tính đến hiện tại.

    Dùng cho block ``computedTotals`` (show_computed_totals): thay vì bắt agent tự
    cộng dồn từng cột trong lịch sử, đưa sẵn tổng của mỗi ghế theo VỊ TRÍ CỐ ĐỊNH
    (đánh dấu "you"/"bạn" cho chính agent), khớp nhãn với build_history_text. Lịch
    sử rỗng (vòng 1) -> mọi người = 0.
    """
    n = cfg.n_players
    totals = [0.0] * n
    for round_contribs in history:
        for i, c in enumerate(round_contribs):
            if i < n:
                totals[i] += c
    you = "(bạn)" if language == "vn" else "(you)"
    parts = [
        f"P{i + 1}{you if i == player_index else ''}={_fmt(totals[i])}"
        for i in range(n)
    ]
    return ", ".join(parts)


def build_window_text(history, player_index, cfg, language, window):
    """Mô tả ``window`` vòng GẦN NHẤT cho chế độ scratchpad.

    Mô phỏng việc con người chỉ thấy màn hình hiển thị của (các) vòng vừa xong,
    KHÔNG có transcript đầy đủ và KHÔNG có tổng tích luỹ — phần còn lại phải tự
    nhớ qua ghi chú (xem ``scratchpadNote``). Mặc định window=1 (chỉ vòng cuối).
    """
    if not history:
        return ""
    window = max(1, int(window))
    start = max(0, len(history) - window)
    lines: List[str] = []
    for r in range(start, len(history)):
        round_contribs = history[r]
        total = sum(round_contribs)
        round_no = r + 1
        if cfg.show_individual_contributions:
            labeled = ", ".join(
                f"P{i + 1}{('(bạn)' if language == 'vn' else '(you)') if i == player_index else ''}={_fmt(c)}"
                for i, c in enumerate(round_contribs)
            )
            if language == "vn":
                lines.append(f"Vòng {round_no}: {labeled}.")
            else:
                lines.append(f"Round {round_no}: {labeled}.")
        else:
            own = round_contribs[player_index]
            if language == "vn":
                lines.append(f"Vòng {round_no}: bạn đóng {_fmt(own)}; tổng nhóm vòng này {_fmt(total)}.")
            else:
                lines.append(f"Round {round_no}: you contributed {_fmt(own)}; group round total {_fmt(total)}.")
    return "\n".join(lines)


def build_notepad_text(notes, language, window):
    """Dựng "cuốn sổ tay" của agent từ các ghi chú nó đã tự viết.

    Mô phỏng tờ giấy ĐẦY DẦN: mỗi vòng thêm một dòng, agent đọc lại được mọi dòng
    cũ (chỉ những gì NÓ tự viết, không phải transcript đầy đủ). ``notes[i]`` ứng với
    vòng ``i+1``. ``window``: 0 = tích luỹ tất cả; k>0 = chỉ k dòng gần nhất. Bỏ qua
    các dòng rỗng (vòng model quên ghi).
    """
    if not notes:
        return ""
    n = len(notes)
    start = 0 if window <= 0 else max(0, n - int(window))
    lines: List[str] = []
    for i in range(start, n):
        note = (notes[i] or "").strip()
        if not note:
            continue
        round_no = i + 1
        if language == "vn":
            lines.append(f"[Vòng {round_no}] {note}")
        else:
            lines.append(f"[Round {round_no}] {note}")
    return "\n".join(lines)


def build_prompt(
    template: str,
    cfg,
    player_name: str,
    player_index: int,
    persona_text: str,
    current_round: int,
    history: List[List[float]],
    language: str,
    agent_notes=None,
    question_text: str = "",
) -> str:
    """Trả về prompt hoàn chỉnh cho một agent ở một vòng.

    ``agent_notes`` chỉ dùng ở chế độ scratchpad (``cfg.memory_mode``): danh sách
    các ghi chú mà chính agent đã viết ở các vòng trước (``notes[i]`` = vòng i+1).
    Được nạp lại thành "cuốn sổ tay" (tích luỹ theo ``cfg.note_window``) thay cho
    transcript đầy đủ.

    ``question_text`` chỉ dùng cho template ĐỌC-HIỂU (``crsd_comprehension_*``): khi
    có, block ``{question}`` bật và thay đuôi "quyết định" bằng một câu hỏi +
    neo ``ANSWER:``. Template quyết định thường KHÔNG có placeholder này nên truyền
    vào cũng vô hại (tương thích ngược).
    """
    cumulative = sum(sum(r) for r in history)
    own_total = sum(r[player_index] for r in history)
    remaining = max(0.0, cfg.endowment - own_total)
    # Tổng tính sẵn (chỉ dùng khi block computedTotals bật): còn thiếu bao nhiêu để
    # đạt target + tổng tích luỹ TỪNG người (per-player) đưa qua {perPlayerTotals}.
    # (own_total/others_total/n_others giữ lại cho tương thích ngược — template mới
    # dùng per-player nên không tham chiếu, nhưng vô hại nếu template khác cần.)
    others_total = max(0.0, cumulative - own_total)
    needed_to_target = max(0.0, cfg.target - cumulative)
    n_others = cfg.n_players - 1
    risk_percent = round(cfg.risk_probability * 100)
    safe_percent = 100 - risk_percent
    options_str = ", ".join(_fmt(o) for o in cfg.contribution_options)

    player_position = player_index + 1
    denom = cfg.n_players * cfg.n_rounds
    fair_share = (cfg.target / denom) if denom else 0.0
    fair_share_kept = cfg.endowment - fair_share * cfg.n_rounds
    show_cum = getattr(cfg, "show_cumulative", False)
    memory_mode = getattr(cfg, "memory_mode", "full_history")
    memory_window = getattr(cfg, "memory_window", 1)
    note_window = getattr(cfg, "note_window", 0)
    framing = getattr(cfg, "framing", False)
    risk_framing = getattr(cfg, "risk_framing", "lottery")
    show_computed_totals = getattr(cfg, "show_computed_totals", False)
    has_history = current_round > 1 and bool(history)
    is_scratchpad = memory_mode == "scratchpad"
    notepad_text = build_notepad_text(agent_notes or [], language, note_window)

    enabled = {
        "persona": bool(persona_text),
        "framing": bool(framing),
        # Framing hậu quả rủi ro: bật ĐÚNG MỘT trong hai bản mô tả. Mặc định "lottery"
        # (giữ nguyên prompt gốc); "plain" nêu xác suất trực tiếp. Template CŨ không có
        # hai block này -> cả hai key vô hại (không khớp gì để bật/tắt).
        "riskLottery": risk_framing != "plain",
        "riskPlain": risk_framing == "plain",
        "gameLength": cfg.n_rounds_known,
        # full_history: nạp lại toàn bộ lịch sử; scratchpad: KHÔNG dùng block này.
        "history": (not is_scratchpad) and has_history,
        "showCumulative": (not is_scratchpad) and show_cum,
        # Tổng tính sẵn: chỉ ở full_history (scratchpad cố ý tự-ghi-nhớ nên không đưa).
        "computedTotals": (not is_scratchpad) and bool(show_computed_totals),
        # scratchpad: chỉ hiển thị vòng gần nhất + cuốn sổ tay ghi chú riêng.
        "lastRound": is_scratchpad and has_history,
        "scratchpadNote": is_scratchpad and bool(notepad_text),
        # đọc-hiểu: thay đuôi "quyết định" bằng một câu hỏi + neo ANSWER.
        "question": bool(question_text),
    }
    text = _resolve_blocks(template, enabled)

    replacements = {
        "personaText": persona_text or "",
        "currentPlayerName": player_name,
        "playerPosition": player_position,
        "nPlayers": cfg.n_players,
        "endowment": _fmt(cfg.endowment),
        "nRounds": cfg.n_rounds,
        "contributionOptions": options_str,
        "target": _fmt(cfg.target),
        "fairShare": _fmt(fair_share),
        "fairShareKept": _fmt(fair_share_kept),
        "riskPercent": risk_percent,
        "safePercent": safe_percent,
        "currentRound": current_round,
        "groupAccount": _fmt(cumulative),
        "remainingEndowment": _fmt(remaining),
        "ownContributed": _fmt(own_total),
        "othersContributed": _fmt(others_total),
        "neededToTarget": _fmt(needed_to_target),
        "nOthers": n_others,
        "perPlayerTotals": build_per_player_totals(history, player_index, cfg, language),
        "historyText": build_history_text(history, player_index, cfg, language),
        "lastRoundText": build_window_text(history, player_index, cfg, language, memory_window),
        "noteText": notepad_text,
        "questionText": question_text or "",
    }
    for k, v in replacements.items():
        text = text.replace("{" + k + "}", str(v))

    # Dọn các dòng trống thừa do bỏ block.
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"
