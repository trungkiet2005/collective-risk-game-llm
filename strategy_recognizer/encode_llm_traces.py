"""Encode CRSD LLM gameplay logs (results/data/**/turns.jsonl) into token
sequences, one row per agent trajectory, using the same codebook as the
synthetic data. Output mirrors ClusteringResearch's df_all_strategies layout
(minus the strategy label, which the recogniser adds later).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from collections import defaultdict

import pandas as pd

from codebook import encode_sequence

DEFAULT_GLOB = "results/data/**/turns.jsonl"

# metadata carried from the turn records onto each trajectory row
META_KEYS = ("language", "risk_probability", "persona_set", "memory_mode",
             "framing", "disposition", "rep")


def _model_of(game_id: str) -> str:
    parts = game_id.split("__")
    return parts[1] if len(parts) > 1 else "?"


def _experiment_of(path: str) -> str:
    # .../results/data/<experiment>/crsd_results/<model>/<exp_dir>/turns.jsonl
    norm = path.replace("\\", "/").split("/")
    try:
        return norm[norm.index("data") + 1]
    except (ValueError, IndexError):
        return "?"


def load_turns(pattern):
    files = glob.glob(pattern, recursive=True)
    records = []
    for fp in files:
        exp = _experiment_of(fp)
        for line in open(fp, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            d["_experiment"] = exp
            records.append(d)
    return records, files


def build_trajectories(records):
    """Group by game_id, order players/rounds, and encode each agent."""
    games = defaultdict(list)
    for d in records:
        games[d["game_id"]].append(d)

    rows = []
    for game_id, turns in games.items():
        rounds = sorted({t["round"] for t in turns})
        players = sorted({t["player"] for t in turns})
        # contribution[(round, player)]; treat parse failures / missing as 0
        contrib = {}
        for t in turns:
            c = t.get("contribution")
            if c is None or t.get("parse_failed"):
                c = 0
            contrib[(t["round"], t["player"])] = int(c)

        # T x N matrix in fixed player order
        matrix = [[contrib.get((r, p), 0) for p in players] for r in rounds]
        meta0 = turns[0]
        for j, p in enumerate(players):
            own = [matrix[i][j] for i in range(len(rounds))]
            seq = encode_sequence(own, matrix)
            row = {
                "game_id": game_id,
                "experiment": meta0.get("_experiment"),
                "llm_model": _model_of(game_id),
                "player": p,
                "n_rounds": len(rounds),
                "state_action": " ".join(seq),
                "contributions": " ".join(str(c) for c in own),
            }
            for k in META_KEYS:
                row[k] = meta0.get(k)
            rows.append(row)
    return pd.DataFrame(rows)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--glob", default=DEFAULT_GLOB)
    p.add_argument("--out", default="Dataset/llm_traces_encoded.csv")
    args = p.parse_args()

    records, files = load_turns(args.glob)
    df = build_trajectories(records)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    df.to_csv(args.out, index=False, encoding="utf-8")
    print(f"read {len(files)} files, {len(records)} turns")
    print(f"wrote {args.out}: {len(df)} agent trajectories")
    print("by model:\n", df["llm_model"].value_counts().to_string())
    print("by experiment:\n", df["experiment"].value_counts().to_string())
    print("by language:\n", df["language"].value_counts().to_string())


if __name__ == "__main__":
    main()
