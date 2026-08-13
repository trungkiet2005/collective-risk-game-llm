"""Shared loaders for the revision analyses.

One rule: read the per-model raw files, never `results/frontier/crsd_all_models.csv`.
That merged file is stale — it predates the top-tier sweep and still contains only
gemini-3.1-flash-lite, so anything joined against it silently drops the two models the
paper's central result rests on. `paper/make_figures_toptier.py` globs the per-model
directories for the same reason; we match it exactly.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

# display label -> raw model directory / csv name
FRONTIER_LABELS = {
    "google-gemini-3.1-pro-preview": ("Gemini-3.1-Pro", "Google", "top"),
    "openai-gpt-5.6-sol": ("GPT-5.6-sol", "OpenAI", "top"),
    "anthropic-claude-opus-5-default": ("Claude-Opus-5", "Anthropic", "top"),
    "xai-grok-4.20-0309-reasoning": ("Grok-4.20 (reasoning)", "xAI", "top"),
    "xai-grok-4.20-0309-non-reasoning": ("Grok-4.20 (no reasoning)", "xAI", "top"),
    "google-gemini-3.1-flash-lite-preview": ("Gemini-3.1-Flash-Lite", "Google", "cheap"),
    "openai-gpt-5.4-nano": ("GPT-5.4-nano", "OpenAI", "cheap"),
    # the nano runs predate the frontier task and write their own model string
    "OpenAIGPT5Nano": ("GPT-5.4-nano", "OpenAI", "cheap"),
}

OPEN_LABELS = {
    "qwen25-7b-instruct": ("Qwen2.5-7B", 7),
    "llama-3-1-8b": ("Llama-3.1-8B", 8),
    "gemma2-9b-it": ("Gemma-2-9B", 9),
    "gemma2-27b-it": ("Gemma-2-27B", 27),
    "qwen25-32b-instruct": ("Qwen2.5-32B", 32),
    "llama-3-1-70b-instruct-awq": ("Llama-3.1-70B", 70),
    "qwen25-72b-instruct-awq": ("Qwen2.5-72B", 72),
    "llama-3-3-70b-instruct-awq": ("Llama-3.3-70B", 70),
}


def frontier_games(experiment: str = "exp_baseline") -> pd.DataFrame:
    paths = sorted((RESULTS / "frontier").glob(f"*/{experiment}/games.csv"))
    df = pd.concat([pd.read_csv(p) for p in paths], ignore_index=True)
    df["arm"] = "commercial"
    df["experiment"] = experiment
    return df


def open_games(experiment: str = "exp_baseline") -> pd.DataFrame:
    df = pd.read_csv(RESULTS / "open_source" / "crsd_all_models.csv")
    df = df[df.experiment == experiment].copy()
    df["arm"] = "open_source"
    return df


def baseline_all() -> pd.DataFrame:
    keep = ["arm", "experiment", "model", "language", "risk_probability", "group_total",
            "target_reached", "catastrophe", "mean_payoff", "rep"]
    o, f = open_games(), frontier_games()
    return pd.concat([o[keep], f[keep]], ignore_index=True)


def label(model: str) -> str:
    if model in FRONTIER_LABELS:
        return FRONTIER_LABELS[model][0]
    if model in OPEN_LABELS:
        return OPEN_LABELS[model][0]
    return model


def turns(model_dir: Path) -> pd.DataFrame:
    """Read a turns.jsonl into a frame of the fields the revision analyses need."""
    rows = []
    with open(model_dir, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            d = json.loads(line)
            rows.append({
                "game_id": d.get("game_id"),
                "round": d.get("round"),
                "player": d.get("player"),
                "contribution": d.get("contribution"),
                "parse_failed": d.get("parse_failed"),
                "risk_probability": d.get("risk_probability"),
                "language": d.get("language"),
                "persona_set": d.get("persona_set"),
                "disposition": d.get("disposition"),
            })
    return pd.DataFrame(rows)


def all_turns(experiment: str = "exp_baseline") -> pd.DataFrame:
    """Every turn of `experiment`, both arms, with a model column."""
    frames = []
    for p in sorted((RESULTS / "frontier").glob(f"*/{experiment}/turns.jsonl")):
        t = turns(p)
        t["model"] = p.parts[-3]
        t["arm"] = "commercial"
        frames.append(t)
    for p in sorted((RESULTS / "open_source" / "archive").glob(f"{experiment}/*/turns.jsonl")):
        t = turns(p)
        t["model"] = p.parts[-2]
        t["arm"] = "open_source"
        frames.append(t)
    for p in sorted((RESULTS / "open_source" / "exp_test").glob(f"{experiment}/*/turns.jsonl")):
        t = turns(p)
        t["model"] = p.parts[-2]
        t["arm"] = "open_source"
        frames.append(t)
    if not frames:
        raise FileNotFoundError(f"no turns.jsonl found for {experiment}")
    return pd.concat(frames, ignore_index=True)
