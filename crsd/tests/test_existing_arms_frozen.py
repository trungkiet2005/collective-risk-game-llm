"""Every arm that already has data in results/ must keep its instrument byte for byte.

The snapshot in golden/existing_arms_snapshot.json was captured from the server task
BEFORE the E8 arms (groupgoal, showpool, evprobe at p=0) were added. For each existing
arm it pins: the experiment folder name, the game_id suffix, the full checkpoint
signature, the sha256 of every rendered decision prompt (and probe prompt) on a fixed
set of states, and the sha256 of the game row and turn records of one offline game.

A later arm that moves any of these for an existing arm would let new shards resume
into old ones, or silently change what an old arm's name means. Regenerate the file
only when an existing arm is changed on purpose:

    CRSD_REGEN_GOLDEN=1 python -m pytest crsd/tests/test_existing_arms_frozen.py
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path

import pytest

TASK_PATH = Path(__file__).parents[2] / "kaggle" / "benchmarks" / "crg_task_server.py"
GOLDEN = Path(__file__).parent / "golden" / "existing_arms_snapshot.json"

E3A = {"defect": "always_0", "coop": "always_2", "carry": "always_4",
       "cond": "conditional_cooperator"}
ARMS = {
    "baseline": {"CRG_LANGS": "en,vn"},
    "nohint": {"CRG_TEMPLATE": "nohint"},
    "para1": {"CRG_TEMPLATE": "para1"},
    "para2": {"CRG_TEMPLATE": "para2"},
    "neutral": {"CRG_TEMPLATE": "neutral"},
    "wording": {"CRG_TEMPLATE": "wording"},
    "temp0": {"CRG_TEMPERATURE": "0"},
    "evprobe": {"CRG_PROBE": "rules,value"},
    **{"bestresponse_" + k: {"CRG_SEAT_MODELS": "self," + ",".join(["scripted:" + v] * 5)}
       for k, v in E3A.items()},
    "mixed": {"CRG_SEAT_MODELS": "self,self,self,gpt-5.6-luna,gpt-5.6-luna,gpt-5.6-luna"},
}
SWEEP = {"CRG_MODEL": "gemini-3.5-flash-lite", "CRG_RISKS": "0,0.1,0.9",
         "CRG_LANGS": "en", "CRG_REPS": "2"}
STATES = [(0, 1, [], 0.0),
          (2, 3, [[2, 2, 2, 2, 4, 2], [2, 0, 2, 2, 4, 2]], 0.1),
          (5, 10, [[4, 0, 2, 4, 0, 2]] * 9, 0.9),
          (0, 6, [[0, 0, 0, 0, 0, 0]] * 5, 0.5)]


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load(monkeypatch, env):
    monkeypatch.setenv("CRG_SKIP_RUN", "1")
    for key in list(os.environ):
        if key.startswith("CRG_") and key != "CRG_SKIP_RUN":
            monkeypatch.delenv(key, raising=False)
    for key, value in {**SWEEP, **env}.items():
        monkeypatch.setenv(key, value)
    spec = importlib.util.spec_from_file_location("crg_task_server_frozen", TASK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _offline_game(task, monkeypatch):
    from kaggle_benchmarks.usage import Usage
    usage = Usage(input_tokens=10, output_tokens=5,
                  input_tokens_cost_nanodollars=1_000,
                  output_tokens_cost_nanodollars=2_000)

    def fake_call(llm, prompt, seed, ctx=None, max_attempts=None, cap_override=None):
        reply = ("CONTRIBUTION: %d\n" % (2 if seed % 2 else 4)
                 if "CONTRIBUTION: <one of" in prompt else "ANSWER: 2\n")
        return reply, usage

    monkeypatch.setattr(task, "_call_llm", fake_call)
    turns, probes = [], ([] if task.PROBE_CATEGORIES else None)
    row, pf, ti, to, cn = task.play_game(None, 0.9, "en", 1, "tag", turns, probes)
    return {"row": _sha(json.dumps(row, sort_keys=True)),
            "turns": _sha(json.dumps(turns, sort_keys=True)),
            "probes": _sha(json.dumps(probes, sort_keys=True)),
            "totals": [pf, ti, to, cn]}


def snapshot(task, monkeypatch):
    prompts = {}
    for lang in sorted(task.TEMPLATES):
        for pid, rnd, hist, risk in STATES:
            prompts["%s|%d|%d|%g" % (lang, pid, rnd, risk)] = _sha(
                task.assemble_prompt(lang, pid, rnd, hist, risk))
    probe_prompts = {}
    if task.PROBE_CATEGORIES:
        for pid, rnd, hist, risk in STATES:
            for q, params in task.probe_items(rnd, hist, pid):
                qtext = q.render(risk, hist, rnd, pid, params)
                key = "%d|%d|%g|%s|%s" % (pid, rnd, risk, q.id, sorted(params.items()))
                probe_prompts[key] = [
                    _sha(task.assemble_probe_prompt("en", pid, rnd, hist, risk, qtext)),
                    json.dumps(task._probe_jsonable(q.ground_truth(risk, hist, rnd, pid,
                                                                    params)))]
    return {
        "experiment": task.EXPERIMENT_NAME,
        "game_name_suffix": task.GAME_NAME_SUFFIX,
        "game_names": [task.game_name(p) for p in (0.0, 0.1, 0.3, 0.5, 0.9)],
        "prompt_variant": task.PROMPT_VARIANT,
        "framing": task.FRAMING,
        "signature": json.loads(json.dumps(task._checkpoint_signature("tag"))),
        "prompts": prompts,
        "probe_prompts": probe_prompts,
        "offline_game": _offline_game(task, monkeypatch),
    }


@pytest.mark.parametrize("arm", sorted(ARMS))
def test_existing_arm_is_byte_identical(arm, monkeypatch):
    got = snapshot(_load(monkeypatch, ARMS[arm]), monkeypatch)
    if os.environ.get("CRSD_REGEN_GOLDEN") == "1":
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        data = json.loads(GOLDEN.read_text(encoding="utf-8")) if GOLDEN.is_file() else {}
        data[arm] = got
        GOLDEN.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        pytest.skip("golden regenerated")
    want = json.loads(GOLDEN.read_text(encoding="utf-8"))[arm]
    assert got == want


def test_golden_covers_every_existing_arm():
    assert sorted(json.loads(GOLDEN.read_text(encoding="utf-8"))) == sorted(ARMS)
