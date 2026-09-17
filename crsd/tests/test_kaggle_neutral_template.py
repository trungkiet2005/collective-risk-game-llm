"""Neutral arm: CRG_TEMPLATE=neutral on the server task.

The reviewer's question this arm answers: is the cooperation "habit" just instruction
following, because the baseline prompt says the group "must" reach a target in a
"climate account" and never says what the player wants? The arm is only interpretable
if it changes exactly those words, turns on the objective sentence, and leaves the
game, the equal-split hint and the answer format alone. These tests defend that, offline.
"""
import importlib.util
import re
from pathlib import Path

import pytest

TASK_PATH = Path(__file__).parents[2] / "kaggle" / "benchmarks" / "crg_task_server.py"
BASELINE_FINGERPRINT = "f78785cba0905583"     # same pin as test_kaggle_template_variant
OBJECTIVE = ("You are a participant in a paid economics experiment. The only thing that "
             "matters to you is your own final cash payoff. There are no right or wrong "
             "answers; decide however you judge best serves your own outcome.\n\n")
RENDERED_ANCHORS = (
    " (an average of 2 per player per round)",
    " (for example, contributing 2 every round leaves you 20 at the end)",
)
CASES = [(0, 1, [], 0.0),
         (2, 3, [[2, 2, 2, 2, 4, 2], [2, 0, 2, 2, 4, 2]], 0.1),
         (5, 10, [[4, 0, 2, 4, 0, 2]] * 9, 0.9)]


def _load_task(monkeypatch, **env):
    monkeypatch.setenv("CRG_SKIP_RUN", "1")
    monkeypatch.delenv("CRG_TEMPLATE", raising=False)
    monkeypatch.delenv("CRG_PROMPT_VARIANT", raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    spec = importlib.util.spec_from_file_location("crg_task_server_neutral_test", TASK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _render(module, span_values):
    """Render a template span the way the task does for the default game constants."""
    return (span_values.replace("{nPlayers}", "6").replace("{target}", "120")
            .replace("{groupAccount}", "0"))


def test_baseline_is_untouched_by_the_new_arm(monkeypatch):
    task = _load_task(monkeypatch)
    assert task.FRAMING is False
    assert task._prompt_fingerprint() == BASELINE_FINGERPRINT
    assert task._checkpoint_signature("m")["framing"] is False


def test_neutral_selects_its_own_experiment_names_and_framing(monkeypatch):
    task = _load_task(monkeypatch, CRG_TEMPLATE="neutral", CRG_LANGS="en")
    assert task.EXPERIMENT_NAME == "exp_neutral"
    assert task.TEMPLATES == {"en": task.TEMPLATE_EN_NEUTRAL}
    assert task.FRAMING is True
    assert task.game_name(0.9) == "crsd_milinski_high_risk_neutral"
    assert task.game_name(0.0) == "crsd_milinski_p000_risk_neutral"


@pytest.mark.parametrize("player, rnd, history, risk", CASES)
def test_neutral_prompt_differs_only_in_the_declared_spans(
        monkeypatch, player, rnd, history, risk):
    """Undo every declared change on the neutral prompt and the baseline must come back
    byte for byte. Any other moved word fails here."""
    baseline = _load_task(monkeypatch)
    neutral = _load_task(monkeypatch, CRG_TEMPLATE="neutral", CRG_LANGS="en")
    got_base = baseline.assemble_prompt("en", player, rnd, history, risk)
    got_neut = neutral.assemble_prompt("en", player, rnd, history, risk)

    assert got_neut.startswith(OBJECTIVE)
    undone = got_neut[len(OBJECTIVE):]
    for old, new in neutral._NEUTRAL_SPANS:
        old_r, new_r = _render(neutral, old), _render(neutral, new)
        if new_r.startswith("[- The shared account"):   # pool line: block is off
            continue
        assert undone.count(new_r) == 1, new_r
        undone = undone.replace(new_r, old_r)
    assert undone == got_base


@pytest.mark.parametrize("player, rnd, history, risk", CASES)
def test_neutral_prompt_keeps_the_game_hint_and_answer_format(
        monkeypatch, player, rnd, history, risk):
    neutral = _load_task(monkeypatch, CRG_TEMPLATE="neutral", CRG_LANGS="en")
    text = neutral.assemble_prompt("en", player, rnd, history, risk)
    lowered = text.lower()
    for word in ("climate", "must", "disaster", "social dilemma", "collective-risk"):
        assert word not in lowered, word
    for anchor in RENDERED_ANCHORS:            # the hint is E1's variable, not this arm's
        assert text.count(anchor) == 1
    assert "with probability %d%%" % round(risk * 100) in text
    assert text.rstrip().endswith("CONTRIBUTION: <one of 0, 2, 4>")


def test_neutral_cannot_resume_a_baseline_shard(monkeypatch):
    sweep = {"CRG_RISKS": "0.9", "CRG_LANGS": "en", "CRG_REPS": "1"}
    base = _load_task(monkeypatch, **sweep)._checkpoint_signature("m")
    neut = _load_task(monkeypatch, CRG_TEMPLATE="neutral", **sweep)._checkpoint_signature("m")
    assert base["prompt_variant"] == "baseline" and neut["prompt_variant"] == "neutral"
    assert base["prompt_fingerprint"] != neut["prompt_fingerprint"]
    assert (base["framing"], neut["framing"]) == (False, True)


def test_neutral_refuses_other_languages(monkeypatch):
    with pytest.raises(SystemExit):
        _load_task(monkeypatch, CRG_TEMPLATE="neutral", CRG_LANGS="en,vn")


def test_neutralising_a_changed_baseline_fails_loudly(monkeypatch):
    task = _load_task(monkeypatch)
    with pytest.raises(SystemExit):
        task._neutralise("a template that shares none of the spans")


def test_neutral_game_rows_and_turns_record_the_framing(tmp_path, monkeypatch):
    """End to end offline: the arm writes exp_neutral, and every row says framing=1."""
    monkeypatch.chdir(tmp_path)
    task = _load_task(monkeypatch, CRG_TEMPLATE="neutral", CRG_RISKS="0",
                      CRG_LANGS="en", CRG_REPS="1")
    from kaggle_benchmarks.usage import Usage
    usage = Usage(input_tokens=10, output_tokens=5,
                  input_tokens_cost_nanodollars=1_000,
                  output_tokens_cost_nanodollars=2_000)
    prompts = []

    def fake_call(llm, prompt, seed, ctx=None, max_attempts=None):
        prompts.append(prompt)
        return "CONTRIBUTION: 0\n", usage

    monkeypatch.setattr(task, "_call_llm", fake_call)
    monkeypatch.delenv("CRG_OUT", raising=False)
    result = task.collective_risk_baseline.func(object())
    out = Path(result["out_dir"])
    assert out.name == "exp_neutral"
    games = (out / "games.csv").read_text(encoding="utf-8")
    assert re.search(r"\bframing\b", games.splitlines()[0])
    assert prompts and all(p.startswith(OBJECTIVE) for p in prompts)


# ------------------------------------------------ wording arm (objective OFF) ---
@pytest.mark.parametrize("player, rnd, history, risk", CASES)
def test_wording_arm_is_the_neutral_prompt_without_the_objective(
        monkeypatch, player, rnd, history, risk):
    """Wording = neutral minus the objective sentence, byte for byte. So the pair
    baseline -> wording measures the words, and wording -> neutral the objective."""
    neutral = _load_task(monkeypatch, CRG_TEMPLATE="neutral", CRG_LANGS="en")
    wording = _load_task(monkeypatch, CRG_TEMPLATE="wording", CRG_LANGS="en")
    got_neut = neutral.assemble_prompt("en", player, rnd, history, risk)
    got_word = wording.assemble_prompt("en", player, rnd, history, risk)
    assert not got_word.startswith(OBJECTIVE)
    assert OBJECTIVE + got_word == got_neut
    assert "climate" not in got_word.lower() and "must" not in got_word.lower()


def test_wording_arm_has_its_own_identity(monkeypatch):
    sweep = {"CRG_RISKS": "0.9", "CRG_LANGS": "en", "CRG_REPS": "1"}
    wording = _load_task(monkeypatch, CRG_TEMPLATE="wording", **sweep)
    assert wording.FRAMING is False
    assert wording.EXPERIMENT_NAME == "exp_wording"
    assert wording.game_name(0.0) == "crsd_milinski_p000_risk_wording"
    sigs = {name: _load_task(monkeypatch, CRG_TEMPLATE=name, **sweep)._checkpoint_signature("m")
            for name in ("baseline", "neutral", "wording")}
    prints = {name: sig["prompt_fingerprint"] for name, sig in sigs.items()}
    assert len(set(prints.values())) == 3, prints
    assert sigs["wording"]["framing"] is False and sigs["neutral"]["framing"] is True
