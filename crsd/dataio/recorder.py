"""Ghi log per-turn (JSONL) và bảng tổng hợp per-game (CSV)."""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


def write_turns_jsonl(turns, path) -> None:
    """Mỗi dòng = một lượt quyết định (game, vòng, người chơi) — cho phân tích reasoning."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for t in turns:
            f.write(json.dumps(t.to_dict(), ensure_ascii=False) + "\n")


def write_comprehension_jsonl(records, path) -> None:
    """Mỗi dòng = một probe đọc-hiểu (game, vòng, người chơi, câu hỏi) — chấm so GT."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            d = r.to_dict() if hasattr(r, "to_dict") else r
            f.write(json.dumps(d, ensure_ascii=False) + "\n")


def summarize_comprehension(records) -> list:
    """Gom accuracy theo (model, language, risk, show_cumulative, category, question_id,
    answerable_from_prompt) — đầu vào cho bảng/figure Figure-1 analog & A/B."""
    groups = defaultdict(lambda: {"n": 0, "n_correct": 0, "n_parse_failed": 0})
    for r in records:
        d = r.to_dict() if hasattr(r, "to_dict") else r
        key = (
            d["model"], d["language"], d["risk_probability"],
            int(bool(d["show_cumulative"])), d["category"], d["question_id"],
            int(bool(d.get("answerable_from_prompt", False))),
        )
        g = groups[key]
        g["n"] += 1
        g["n_correct"] += int(bool(d["correct"]))
        g["n_parse_failed"] += int(bool(d["parse_failed"]))
    rows = []
    for (model, lang, risk, showcum, cat, qid, ans), g in groups.items():
        n = g["n"]
        rows.append({
            "model": model, "language": lang, "risk_probability": risk,
            "show_cumulative": showcum, "category": cat, "question_id": qid,
            "answerable_from_prompt": ans,
            "n": n, "n_correct": g["n_correct"],
            "accuracy": (g["n_correct"] / n) if n else 0.0,
            "n_parse_failed": g["n_parse_failed"],
            "parse_fail_rate": (g["n_parse_failed"] / n) if n else 0.0,
        })
    rows.sort(key=lambda x: (x["model"], x["language"], x["risk_probability"],
                             x["show_cumulative"], x["category"], x["question_id"]))
    return rows


def write_comprehension_summary_csv(records, path) -> None:
    """Bảng accuracy tổng hợp (mỗi dòng = một ô model×lang×risk×showcum×category×qid)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = summarize_comprehension(records)
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
        "risk_framing": cfg.get("risk_framing", "lottery"),
        "show_computed_totals": int(bool(cfg.get("show_computed_totals", False))),
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
