import csv
import importlib.util
import json
from pathlib import Path


def _load_task_module(monkeypatch):
    monkeypatch.setenv("CRG_SKIP_RUN", "1")
    task_path = Path(__file__).parents[2] / "kaggle" / "benchmarks" / "crg_task_server.py"
    spec = importlib.util.spec_from_file_location("crg_task_server_checkpoint_test", task_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_checkpoint_round_trip_and_materialized_outputs(tmp_path, monkeypatch):
    task = _load_task_module(monkeypatch)
    out_dir = tmp_path / "result"
    checkpoint_dir = out_dir / "checkpoints"
    signature = task._checkpoint_signature("anthropic-claude-haiku-4-5-20251001")
    row = {
        "game_id": "game-1",
        "model": "anthropic-claude-haiku-4-5-20251001",
        "language": "en",
        "risk_probability": 0.9,
        "rep": 0,
    }
    turns = [
        {"game_id": "game-1", "round": i // task.N_PLAYERS + 1,
         "player": f"Player_{i % task.N_PLAYERS + 1}", "parse_failed": False}
        for i in range(task.N_PLAYERS * task.N_ROUNDS)
    ]

    saved = task._save_game_checkpoint(
        checkpoint_dir, signature, row, turns, 0, 123, 45, 6_000_000)
    assert saved.exists()
    assert not list(checkpoint_dir.glob("*.tmp"))

    games, loaded_turns, stats, completed = task._load_game_checkpoints(
        checkpoint_dir, signature)
    assert games == [row]
    assert loaded_turns == turns
    assert completed == {task._condition_key(0.9, "en", 0)}
    assert stats == {"parse_failed": 0, "tok_in": 123, "tok_out": 45,
                     "cost": 6_000_000}

    task._write_materialized_outputs(out_dir, games, loaded_turns)
    with open(out_dir / "games.csv", newline="", encoding="utf-8") as f:
        assert list(csv.DictReader(f))[0]["game_id"] == "game-1"
    with open(out_dir / "turns.jsonl", encoding="utf-8") as f:
        assert [json.loads(line) for line in f] == turns


def test_incompatible_or_partial_checkpoint_is_not_resumed(tmp_path, monkeypatch):
    task = _load_task_module(monkeypatch)
    checkpoint_dir = tmp_path / "checkpoints"
    signature = task._checkpoint_signature("model-a")
    row = {"risk_probability": 0.9, "language": "en", "rep": 0}
    incomplete_turns = [{"turn": 1}]
    task._save_game_checkpoint(
        checkpoint_dir, signature, row, incomplete_turns, 0, 1, 1, 1)

    games, turns, stats, completed = task._load_game_checkpoints(
        checkpoint_dir, signature)
    assert games == []
    assert turns == []
    assert completed == set()
    assert stats == {"parse_failed": 0, "tok_in": 0, "tok_out": 0, "cost": 0}
