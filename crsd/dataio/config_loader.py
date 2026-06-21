"""Đọc & kiểm tra (light) các file config JSON."""
from __future__ import annotations

import json
from pathlib import Path


class ConfigError(Exception):
    pass


def load_json(path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


REQUIRED_GAME_KEYS = [
    "name",
    "nPlayers",
    "endowment",
    "contributionOptions",
    "target",
    "nRounds",
    "riskProbability",
]


def validate_game(d: dict) -> dict:
    """Kiểm tra game config có đủ khoá & hợp lệ tối thiểu. Trả lại chính d."""
    missing = [k for k in REQUIRED_GAME_KEYS if k not in d]
    if missing:
        raise ConfigError(f"Game config thiếu khoá: {missing}")
    if not d.get("contributionOptions"):
        raise ConfigError("contributionOptions không được rỗng")
    if float(d["target"]) <= 0:
        raise ConfigError("target phải > 0")
    if not (0.0 <= float(d["riskProbability"]) <= 1.0):
        raise ConfigError("riskProbability phải trong [0, 1]")
    return d
