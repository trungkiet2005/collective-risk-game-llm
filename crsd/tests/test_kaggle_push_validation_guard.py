"""Push validation must play one game, whatever the server's default model is called.

`kaggle b t push` runs the task once on the server default model before the task can be
run. The old guard recognised that model by name ("gemini-3-flash-preview"); the server
switched to gemini-3.7-flash and every push silently validated over the whole shard,
which on 17-09-2026 took 35 minutes and drained two accounts. CRG_EXPECT_MODEL names the
model the shard is for; anything else importing it is the validation.
"""
import importlib.util
import re
from pathlib import Path

import pytest

TASK_PATH = Path(__file__).parents[2] / "kaggle" / "benchmarks" / "crg_task_server.py"
LAUNCH = Path(__file__).parents[2] / "plan" / "scripts" / "launch_shard.py"

# (slug passed to `kaggle b t run -m`, MODEL string the server sets), as logged in [cfg].
SERVER_NAMES = [
    ("claude-haiku-4-5-20251001", "anthropic/claude-haiku-4-5@20251001"),
    ("gpt-5.6-luna", "openai/gpt-5.6-luna"),
    ("gemini-3.5-flash-lite", "google/gemini-3.5-flash-lite"),
    ("qwen3-235b-a22b-instruct-2507", "qwen/qwen3-235b-a22b-instruct-2507"),
    ("grok-4.20-0309-non-reasoning", "xai/grok-4.20-0309-non-reasoning"),
    ("claude-opus-5-default", "anthropic/claude-opus-5@default"),
]
SWEEP = {"CRG_RISKS": "0,0.1,0.9", "CRG_LANGS": "en", "CRG_REPS": "5", "CRG_REP_START": "5"}


def _load(monkeypatch, **env):
    monkeypatch.setenv("CRG_SKIP_RUN", "1")
    for key in ("CRG_MODEL", "LLM_DEFAULT", "CRG_EXPECT_MODEL", "CRG_RISKS", "CRG_LANGS",
                "CRG_REPS", "CRG_REP_START"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    spec = importlib.util.spec_from_file_location("crg_task_server_guard_test", TASK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("slug, server_name", SERVER_NAMES)
def test_the_real_run_keeps_its_full_sweep(monkeypatch, slug, server_name):
    task = _load(monkeypatch, CRG_MODEL=server_name, CRG_EXPECT_MODEL=slug,
                 CRG_RISKS="0,0.1,0.9", CRG_LANGS="en", CRG_REPS="10")
    assert not task.IS_PUSH_VALIDATION
    assert task.RISKS == [0.0, 0.1, 0.9]
    assert list(task.REP_RANGE) == list(range(10))


@pytest.mark.parametrize("default_model", ["google/gemini-3.7-flash", "google/gemini-9-flash"])
def test_any_other_model_is_the_validation_and_plays_one_game(monkeypatch, default_model):
    task = _load(monkeypatch, CRG_MODEL=default_model,
                 CRG_EXPECT_MODEL="claude-haiku-4-5-20251001")
    assert task.IS_PUSH_VALIDATION
    assert (task.RISKS, task.LANGS, list(task.REP_RANGE)) == ([0.9], ["en"], [0])


def test_unset_knob_changes_nothing(monkeypatch):
    task = _load(monkeypatch, CRG_MODEL="google/gemini-3.7-flash", **SWEEP)
    assert not task.IS_PUSH_VALIDATION
    assert list(task.REP_RANGE) == [5, 6, 7, 8, 9]


def test_knob_has_the_shape_the_launcher_rewrites_and_the_launcher_sets_it():
    source = TASK_PATH.read_text(encoding="utf-8")
    assert re.findall(r'os\.environ\.get\("CRG_EXPECT_MODEL", "([^"]*)"\)', source) == [""]
    assert 'overrides = {"CRG_EXPECT_MODEL": ",".join(args.model)}' in LAUNCH.read_text(
        encoding="utf-8")
