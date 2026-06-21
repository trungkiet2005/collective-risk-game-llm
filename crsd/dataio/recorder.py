"""Ghi log per-turn (JSONL) và bảng tổng hợp per-game (CSV)."""
from __future__ import annotations

import csv
import json
from pathlib import Path


def write_turns_jsonl(turns, path) -> None:
    """Mỗi dòng = một lượt quyết định (game, vòng, người chơi) — cho phân tích reasoning."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for t in turns:
            f.write(json.dumps(t.to_dict(), ensure_ascii=False) + "\n")


_SEAT_TAG = {"selfish": "S", "cooperative": "C", "neutral": "N"}


def summarize_game(result) -> dict:
    payoffs = result.payoffs
    n = len(payoffs)
    cfg = result.config or {}
    dispositions = getattr(result, "dispositions", None) or []
    return {
        "game_id": result.game_id,
        "model": result.model,
        "language": result.language,
        "risk_probability": result.risk_probability,
        "persona_set": result.persona_set,
        # Sắp xếp tính cách theo ghế thực tế (vd "SSCCCC"); phản ánh cả khi đã hoán vị
        # vị trí (shufflePersonas) -> games.csv tự mô tả nhóm, không cần đoán theo slot.
        "persona_seats": "".join(_SEAT_TAG.get(d, "?") for d in dispositions),
        "memory_mode": cfg.get("memory_mode", "full_history"),
        "framing": int(bool(cfg.get("framing", False))),
        "group_total": result.group_total,
        "target": result.target,
        "target_reached": int(result.target_reached),
        "catastrophe": int(result.catastrophe),
        "mean_payoff": (sum(payoffs) / n) if n else 0.0,
        "rep": getattr(result, "rep", None),   # khoá join trực tiếp với đối chứng baseline
        "seed": result.seed,
    }


def write_games_csv(results, path) -> None:
    """Mỗi dòng = một ván, gồm các chỉ số tổng hợp để phân tích."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [summarize_game(r) for r in results]
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    try:
        import pandas as pd

        pd.DataFrame(rows).to_csv(path, index=False)
    except ImportError:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
