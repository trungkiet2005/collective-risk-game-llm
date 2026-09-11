"""Chiếu dữ liệu LONG (games.csv + turns.jsonl) sang định dạng WIDE kiểu FAIRGAME.

Một dòng = một ván, mỗi agent chiếm một khối cột (`agent1_strategies`, `agent1_scores`, …)
— học theo corpus prisoner's-dilemma ở `Prisoner_Dilemma_Game/Dataset/data_fairgame_frontier_llm`
nhưng mở rộng cho CRSD 6 agent. Đặc tả đầy đủ: `plan/aamas2027-plan.md` §9.

Đây là một PHÉP CHIẾU, không phải bản thay thế: `games.csv`/`turns.jsonl` vẫn là nguồn sự
thật, và cây `wide/` sinh lại được bất cứ lúc nào. Nên engine đang chạy không chịu rủi ro gì.

Hai chỗ CRSD khác hẳn prisoner's dilemma, và cách xử lý:

* **Không có payoff theo vòng.** Tiền chỉ kết toán một lần ở cuối, sau xổ số cấp nhóm. Nên
  `agent{i}_scores` ở đây là **tài khoản riêng còn lại sau mỗi vòng**
  (`endowment - cumsum(đóng góp)`) — cùng đơn vị tiền, cùng độ dài 10, để code loader dùng
  chung được với corpus PD. Nó là hàm tất định của `agent{i}_strategies`; phần "phụ thuộc
  người khác" mà cột `scores` của PD mang, ở CRSD nằm ở cấp nhóm trong `pot_cumulative`.
* **Kết cục là của cả nhóm.** Thêm hẳn một khối cột nhóm (`group_contributions`,
  `pot_cumulative`, `target_reached`, `catastrophe`) mà trò chơi 2 người không có tương đương.
"""
from __future__ import annotations

import re
from collections import defaultdict

N_PLAYERS = 6
N_ROUNDS = 10

# Lượt nào không có dòng này là đã bị CẮT trước khi model kịp ra quyết định. Khi đó
# `parse_contribution` rơi xuống nhánh quét mọi chữ số rồi lấy số cuối thuộc {0,2,4} —
# và vẫn trả `parse_failed=False`. Nên `parse_failed` KHÔNG phát hiện được lỗi này;
# phải kiểm sự có mặt của chính dòng marker.
CONTRIB_RE = re.compile(r"CONTRIBUTION\s*:", re.I)


def _pylist(xs) -> str:
    """Python literal (nháy đơn) — KHÔNG phải JSON, để khớp corpus PD.

    Bên đọc dùng ``ast.literal_eval``. Giữ int là int để list không lẫn float xấu xí.
    """
    return repr([int(x) if float(x).is_integer() else float(x) for x in xs])


def infer_endowment(games, default=40.0):
    """Suy vốn ban đầu từ dữ liệu thay vì hardcode.

    Với ván KHÔNG thảm hoạ: ``mean_payoff = endowment - group_total / n``. Ván có thảm hoạ
    cho payoff 0 nên không suy được — bỏ qua chúng. Nếu không ván nào dùng được (ví dụ
    file toàn thảm hoạ ở p = 1.0) thì lấy ``default``.
    """
    cands = set()
    for g in games:
        if int(float(g.get("catastrophe", 0))):
            continue
        cands.add(round(float(g["mean_payoff"]) + float(g["group_total"]) / N_PLAYERS, 6))
    if not cands:
        return default
    if len(cands) > 1:
        raise ValueError(f"endowment khong nhat quan trong cung mot file: {sorted(cands)}")
    return cands.pop()


def group_turns(turns):
    """Gom lượt theo (risk, rep) rồi theo người chơi.

    Khoá là (risk, rep) chứ KHÔNG phải ``game_id``: ở schema cũ, ``game_id`` trong
    turns.jsonl không mang hậu tố ngôn ngữ/rep nên nó trùng nhau giữa các rep.
    """
    out = defaultdict(lambda: defaultdict(dict))
    for t in turns:
        key = (f"{float(t['risk_probability']):.1f}", str(t["rep"]))
        out[key][t["player"]][int(t["round"])] = t
    return out


def _seat_llm(seat_model: str | None, fallback: str) -> str:
    """Tên model của một ghế, CÙNG DẠNG với ``<model_tag>`` trong đường dẫn.

    Task server ghi ``seat_model`` là **slug thô** ("qwen/qwen3-235b-…") trong khi thư
    mục và cột ``model`` dùng tag đã chuẩn hoá ("qwen-qwen3-235b-…", sinh bằng
    ``re.sub(r"[^A-Za-z0-9._-]+", "-", slug)``). Để nguyên slug thì ``agent1_llm``
    không join được với đường dẫn, và ``verify_wide.py`` báo lỗi trên **từng dòng** —
    đúng cái đã xảy ra khi gom E3a lần đầu.

    Ghế scripted giữ nguyên ("scripted:always_4"): nó không phải model proxy, không bao
    giờ phải join với tên thư mục, và đổi thành "scripted-always_4" chỉ làm mất dấu
    hiệu đây là ghế tất định.
    """
    if not seat_model:
        return fallback
    if seat_model.startswith("scripted:"):
        return seat_model
    return re.sub(r"[^A-Za-z0-9._-]+", "-", seat_model)


def game_to_wide_row(game: dict, seats: dict, endowment: float, experiment: str) -> dict:
    """Một ván -> một dict 82 cột. ``seats`` = {player_name: {round: turn}}."""
    names = sorted(seats, key=lambda p: int(p.rsplit("_", 1)[-1]))
    if len(names) != N_PLAYERS:
        raise ValueError(f"{game['game_id']}: {len(names)} ghe, cho {N_PLAYERS}")

    rounds = sorted({r for s in seats.values() for r in s})
    played = len(rounds)
    catastrophe = int(float(game.get("catastrophe", 0)))

    per_seat, contribs = {}, {}
    for i, p in enumerate(names, 1):
        by_round = seats[p]
        if sorted(by_round) != rounds:
            raise ValueError(f"{game['game_id']}/{p}: thieu vong {set(rounds) - set(by_round)}")
        c = [float(by_round[r]["contribution"]) for r in rounds]
        run, acc = [], 0.0
        for x in c:
            acc += x
            run.append(endowment - acc)
        fails = sum(
            1 for r in rounds
            if by_round[r].get("parse_failed")
            or not CONTRIB_RE.search(by_round[r].get("raw_response") or "")
        )
        contribs[i] = c
        per_seat[i] = {
            f"agent{i}_name": p,
            f"agent{i}_llm": _seat_llm(by_round[rounds[0]].get("seat_model"),
                                       game["model"]),
            f"agent{i}_personality": by_round[rounds[0]].get("disposition") or "",
            f"agent{i}_knows_opponent_with_prob": 0,
            f"agent{i}_strategies": _pylist(c),
            f"agent{i}_scores": _pylist(run),
            f"agent{i}_messages": "[]",
            f"agent{i}_payoff": 0.0 if catastrophe else round(run[-1], 6),
            f"agent{i}_parse_failures": fails,
        }

    group = [sum(contribs[i][k] for i in contribs) for k in range(played)]
    pot, acc = [], 0.0
    for x in group:
        acc += x
        pot.append(acc)

    opts = sorted({int(x) for c in contribs.values() for x in c})

    row = {
        # A — định danh ván & thiết kế
        "game_id": game["game_id"],
        "experiment": experiment,
        "language": game["language"],
        "rep": int(game["rep"]),
        "seed": int(game["seed"]),
        "persona_set": game.get("persona_set", ""),
        "persona_seats": game.get("persona_seats", ""),
        "memory_mode": game.get("memory_mode", "full_history"),
        "opponent_profile": game.get("opponent_profile", ""),
        "framing": int(float(game.get("framing", 0))),
        # Hai cột dưới không tồn tại trong schema cũ. Mặc định = cấu hình baseline gốc
        # (xổ số kiểu lottery, prompt KHÔNG đưa sẵn tổng tính trước). Ván nào nhập từ
        # data cũ đều ghi rõ trong PROVENANCE.json cạnh file raw.
        "risk_framing": game.get("risk_framing") or "lottery",
        "show_computed_totals": int(float(game.get("show_computed_totals") or 0)),
        # B — luật chơi
        "n_players": N_PLAYERS,
        "endowment": endowment,
        "contribution_options": repr(opts),
        "target": float(game["target"]),
        "risk_probability": float(game["risk_probability"]),
        "n_rounds_is_known": True,
        "max_rounds": N_ROUNDS,
        "played_rounds": played,
        "agents_communicate": False,
        # C — kết cục nhóm
        "group_contributions": _pylist(group),
        "pot_cumulative": _pylist(pot),
        "group_total": float(game["group_total"]),
        "target_reached": int(float(game["target_reached"])),
        "catastrophe": catastrophe,
        "mean_payoff": float(game["mean_payoff"]),
        "n_parse_failures": sum(s[f"agent{i}_parse_failures"] for i, s in per_seat.items()),
    }
    for i in sorted(per_seat):
        row.update(per_seat[i])
    return row


def wide_fieldnames() -> list:
    """Thứ tự cột cố định — dùng cho mọi file để schema đồng nhất."""
    head = [
        "game_id", "experiment", "language", "rep", "seed", "persona_set", "persona_seats",
        "memory_mode", "opponent_profile", "framing", "risk_framing", "show_computed_totals",
        "n_players", "endowment", "contribution_options", "target", "risk_probability",
        "n_rounds_is_known", "max_rounds", "played_rounds", "agents_communicate",
        "group_contributions", "pot_cumulative", "group_total", "target_reached",
        "catastrophe", "mean_payoff", "n_parse_failures",
    ]
    for i in range(1, N_PLAYERS + 1):
        head += [f"agent{i}_{k}" for k in (
            "name", "llm", "personality", "knows_opponent_with_prob",
            "strategies", "scores", "messages", "payoff", "parse_failures")]
    return head
