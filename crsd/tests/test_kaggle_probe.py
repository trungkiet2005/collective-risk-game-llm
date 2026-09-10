"""E2 comprehension probe on the server task (CRG_PROBE).

Covers kaggle/benchmarks/crg_task_server.py, a self-contained reimplementation (it
does NOT import crsd), so everything here loads that file as a module and drives it
OFFLINE -- no proxy call is ever made.

Two claims these tests exist to defend:

1. The probe bank is the crsd bank. The server file cannot import crsd, so its
   questions, its enumeration and its ground truth are a hand copy -- and a hand copy
   is worthless unless something walks both side by side. `test_parity_*` does exactly
   that for every category, at every checkpoint round, at every risk level on the grid.
   If a word or a formula drifts, E2 stops being comparable with the open-weight arm
   and the drift shows up here instead of in a merged figure.

2. The probe cannot touch the play it measures. Probing must leave the decisions
   byte-identical and must happen only after a round's decisions are already in hand.
"""
import contextlib
import importlib.util
import json
import os
import re
from pathlib import Path

import pytest

from crsd.engine import comprehension as C
from crsd.engine.prompt import build_prompt
from crsd.engine.state import GameConfig
from crsd.dataio.config_loader import load_json

ROOT = Path(__file__).parents[2]
TASK_PATH = ROOT / "kaggle" / "benchmarks" / "crg_task_server.py"
GAME_DIR = ROOT / "crsd" / "configs" / "game"
COMP_TEMPLATE = (ROOT / "crsd" / "prompts" / "crsd_comprehension_en.txt").read_text(
    encoding="utf-8")

RISK_CONFIG = {0.9: "crsd_milinski_high_risk",
               0.5: "crsd_milinski_medium_risk",
               0.1: "crsd_milinski_low_risk"}

# The caps the crsd probe configs use (exp_evprobe.json / exp_comprehension.json).
CRSD_CAPS = {"max_seats": 4, "max_past_rounds": None, "include_rules": True}

# A handful of states that exercise every enumerator: the empty history at round 1,
# a mid-game history with a clear free-rider and altruist, and the last round.
STATES = [
    (1, []),
    (5, [[0, 2, 4, 2, 0, 4], [0, 4, 4, 2, 2, 0], [0, 2, 4, 4, 0, 2],
         [2, 2, 4, 0, 0, 4]]),
    (10, [[0, 2, 4, 2, 0, 4]] * 9),
]


def _load_task(monkeypatch, **env):
    """Fresh import of the server task with a controlled environment."""
    monkeypatch.setenv("CRG_SKIP_RUN", "1")
    for key in ("CRG_PROBE", "CRG_PROBE_ROUNDS", "CRG_PROBE_SEATS", "CRG_TEMPLATE",
                "CRG_PROMPT_VARIANT", "CRG_OUT", "CRG_CONCURRENCY"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    spec = importlib.util.spec_from_file_location("crg_task_server_probe_test", TASK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _cfg(risk):
    """The REAL open-weight game config for this risk level, so the parity check is
    against the instrument the other arm plays, not against a hand-built stand-in."""
    return GameConfig.from_dict(load_json(GAME_DIR / f"{RISK_CONFIG[risk]}.json"),
                                language="en", model="m")


def _records(captured, tag):
    out = []
    for line in captured.splitlines():
        if line.startswith(tag + " "):
            out.append(json.loads(line[len(tag) + 1:]))
    return out


def _fake_llm(module, monkeypatch, decision="CONTRIBUTION: 2\n", answer="ANSWER: 4\n"):
    """Replace the proxy call site and record every prompt actually sent."""
    from kaggle_benchmarks.usage import Usage

    class _Chat:
        usage = Usage(input_tokens=10, output_tokens=5,
                      input_tokens_cost_nanodollars=1_000,
                      output_tokens_cost_nanodollars=2_000)

    @contextlib.contextmanager
    def new_chat(*args, **kwargs):
        yield _Chat()

    calls = []

    class _LLM:
        model = module.MODEL

        def prompt(self, prompt, **kwargs):
            calls.append(prompt)
            return answer if "ANSWER:" in prompt else decision

    monkeypatch.setattr(module.kbench.chats, "new", new_chat)
    monkeypatch.setattr(module.time, "sleep", lambda *_: None)
    return _LLM(), calls


def _run_sweep(task, tmp_path, monkeypatch, **env):
    """One offline sweep into tmp_path; returns (result, prompts sent)."""
    monkeypatch.setenv("CRG_OUT", str(tmp_path))
    llm, calls = _fake_llm(task, monkeypatch)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return task.collective_risk_baseline.func(llm), calls


# ============================================================== defaults (OFF) ===
def test_probe_is_off_by_default_and_changes_nothing(monkeypatch):
    """An unset CRG_PROBE must leave the sweep exactly as it was: no questions, no
    signature field, no probes.jsonl, no extra key on the records a supervisor parses."""
    task = _load_task(monkeypatch)
    assert task.PROBE_CATEGORIES == ()
    assert task.probes_per_game() == 0
    assert task.PROBE_TEMPLATES == {}
    assert "probe" not in task._checkpoint_signature("m")
    assert task._probe_fingerprint() == ""
    # The pinned baseline instrument is untouched by the probe plumbing.
    assert task._prompt_fingerprint() == "f78785cba0905583"
    assert task.run_probes(None, 0.9, "en", 0, 1, [], "g", "m") == ([], 0, 0, 0)


def test_default_sweep_sends_only_decisions_and_writes_no_probe_file(
        tmp_path, monkeypatch):
    task = _load_task(monkeypatch, CRG_RISKS="0.9", CRG_LANGS="en", CRG_REPS="1")
    result, calls = _run_sweep(task, tmp_path, monkeypatch)
    assert len(calls) == task.N_PLAYERS * task.N_ROUNDS == 60
    assert not any("ANSWER:" in p for p in calls)
    assert not (tmp_path / "probes.jsonl").exists()
    assert "n_probes" not in result
    shard = json.loads(next((tmp_path / "checkpoints").glob("*.json")).read_text(
        encoding="utf-8"))
    assert "probes" not in shard


# ================================================== parity with crsd's bank =====
@pytest.mark.parametrize("risk", [0.9, 0.5, 0.1])
@pytest.mark.parametrize("current_round, history", STATES)
def test_parity_every_question_matches_crsd_item_by_item(
        monkeypatch, risk, current_round, history):
    """The whole bank, side by side: same ids in the same order, same parameter sets,
    same rendered English question, same ground truth, same answer kind, same
    'answerable from the prompt' flag."""
    task = _load_task(monkeypatch, CRG_PROBE="rules,value,time,state", CRG_LANGS="en")
    cfg = _cfg(risk)
    for pi in (0, 3):
        mine = task.probe_items(current_round, history, pi)
        theirs = C.iter_questions(cfg, history, current_round, pi, dict(CRSD_CAPS))
        assert [q.id for q, _ in mine] == [s.id for s, _ in theirs]
        assert [p for _, p in mine] == [p for _, p in theirs]
        for (q, params), (spec, sparams) in zip(mine, theirs):
            assert q.category == spec.category
            assert q.answer_kind == spec.answer_kind
            assert q.answerable == spec.answerable(cfg), q.id
            assert (q.render(risk, history, current_round, pi, params)
                    == spec.render(cfg, history, current_round, pi, sparams, "en")), q.id
            assert (q.ground_truth(risk, history, current_round, pi, params)
                    == spec.ground_truth(cfg, history, current_round, pi, sparams)), q.id


def test_parity_registry_order_is_the_crsd_registry_order(monkeypatch):
    """The per-seat question ordinal keys each probe's sampling seed, so the order is
    part of the instrument, not a detail."""
    task = _load_task(monkeypatch, CRG_PROBE="rules,value,time,state", CRG_LANGS="en")
    assert [q.id for q in task.PROBE_REGISTRY] == [s.id for s in C.REGISTRY]
    assert [q.category for q in task.PROBE_REGISTRY] == [s.category for s in C.REGISTRY]


def test_value_ground_truth_is_the_pinned_expected_value_comparison(monkeypatch):
    """E2's whole point, stated as numbers: withholding wins at p=.1, the two are
    exactly equal at p=.5, cooperating wins at p=.9 -- and the EV of withholding is
    (1-p)*40. Recomputed here from the Milinski parameters, not copied from a comment."""
    task = _load_task(monkeypatch, CRG_PROBE="value", CRG_LANGS="en")
    compare = task.PROBE_REGISTRY_BY_ID["value_compare"]
    defect = task.PROBE_REGISTRY_BY_ID["value_defect_ev"]
    for risk, expect_compare, expect_ev in ((0.1, 2, 36), (0.5, 0, 20), (0.9, 1, 4)):
        assert compare.ground_truth(risk, [], 1, 0, {}) == expect_compare
        assert defect.ground_truth(risk, [], 1, 0, {}) == expect_ev
        # and the same numbers out of crsd, from the real config file
        cfg = _cfg(risk)
        assert C._ev_compare_gt(cfg) == expect_compare
    # The revision grid (p = 0.3 / 0.7) has no tie and follows the same rule.
    assert compare.ground_truth(0.3, [], 1, 0, {}) == 2      # (1-.3)*40 = 28 > 20
    assert compare.ground_truth(0.7, [], 1, 0, {}) == 1      # (1-.7)*40 = 12 < 20
    # Neither is readable from the prompt: both must be computed.
    assert compare.answerable is False and defect.answerable is False


def test_probe_prompt_is_byte_identical_to_the_crsd_comprehension_prompt(monkeypatch):
    """Same game description, same state, same history, same ANSWER anchor. If these
    two ever diverge, the server arm is measuring comprehension of a prompt the
    open-weight arm never showed anyone."""
    task = _load_task(monkeypatch, CRG_PROBE="rules,value,time,state", CRG_LANGS="en")
    for risk in (0.9, 0.5, 0.1):
        cfg = _cfg(risk)
        for current_round, history in STATES:
            for pi in (0, 3):
                for q, params in task.probe_items(current_round, history, pi):
                    qtext = q.render(risk, history, current_round, pi, params)
                    mine = task.assemble_probe_prompt("en", pi, current_round, history,
                                                      risk, qtext)
                    theirs = build_prompt(
                        COMP_TEMPLATE, cfg, task.PLAYER_NAMES[pi], pi, "",
                        current_round, history, "en", question_text=qtext)
                    assert mine == theirs, (q.id, current_round, pi)


def test_probe_text_stays_pure_ascii(monkeypatch):
    """The file is pushed to Kaggle and read with the system codepage; non-ASCII in it
    has already killed one push. Everything the probe adds to the wire is checked."""
    task = _load_task(monkeypatch, CRG_PROBE="rules,value,time,state", CRG_LANGS="en")
    blobs = [task.PROBE_TEMPLATES["en"]] + list(task._PROBE_Q_TEXT.values())
    for current_round, history in STATES:
        for q, params in task.probe_items(current_round, history, 0):
            blobs.append(q.render(0.9, history, current_round, 0, params))
            blobs.append(task.assemble_probe_prompt(
                "en", 0, current_round, history, 0.9,
                q.render(0.9, history, current_round, 0, params)))
    for blob in blobs:
        assert all(ord(ch) < 128 for ch in blob), blob[:80]


# ================================================== parsing and grading =========
@pytest.mark.parametrize("reply, kind, parsed, failed", [
    ("ANSWER: 4", "int", 4, False),
    ("thinking...\nANSWER: 2\nANSWER: 0", "int", 0, False),          # last line wins
    ("ANSWER: 80 (still needed to reach 120)", "int", 80, False),    # first number
    ("ANSWER: 0, 2 and 4", "int_set", {0, 2, 4}, False),
    ("ANSWER: no, not yet", "yesno", False, False),
    ("ANSWER: yes", "yesno", True, False),
    ("I think it is four.", "int", None, True),                      # no ANSWER line
    ("", "int", None, True),
])
def test_parse_matches_crsd_parse(monkeypatch, reply, kind, parsed, failed):
    task = _load_task(monkeypatch, CRG_PROBE="value", CRG_LANGS="en")
    assert task.parse_probe_answer(reply, kind) == (parsed, failed)
    assert C.parse_answer(reply, kind) == (parsed, failed)


def test_grading_matches_crsd_and_a_malformed_answer_is_wrong(monkeypatch):
    task = _load_task(monkeypatch, CRG_PROBE="value", CRG_LANGS="en")
    for parsed, truth, kind, failed in ((2, 2, "int", False), (1, 2, "int", False),
                                        ({0, 2, 4}, {0, 2, 4}, "int_set", False),
                                        (True, True, "yesno", False),
                                        (None, 2, "int", True)):
        assert (task.score_probe_answer(parsed, truth, kind, failed)
                == C.score_answer(parsed, truth, kind, failed))
    assert task.score_probe_answer(None, 2, "int", True) is False


# ====================================================== the probe in a sweep ====
def test_e2_sweep_asks_at_checkpoints_only_and_after_the_decisions(
        tmp_path, monkeypatch, capsys):
    """Six extra calls for one game with CRG_PROBE=value: rounds 1/5/10, seat P1, two
    questions each -- and every one of them lands AFTER that round's six decisions."""
    task = _load_task(monkeypatch, CRG_PROBE="value", CRG_RISKS="0.9",
                      CRG_LANGS="en", CRG_REPS="1")
    assert task.probes_per_game() == 6
    result, calls = _run_sweep(task, tmp_path, monkeypatch)

    decisions = [i for i, p in enumerate(calls) if "CONTRIBUTION: <one of" in p]
    probes = [i for i, p in enumerate(calls) if "ANSWER: <your answer>" in p]
    assert len(decisions) == 60 and len(probes) == 6
    # Interleaving: 6 decisions, then the round's probes, never the other way round.
    # r1: 6 decisions then 2 probes; r5: 26..31 then 32,33; r10: 58..63 then 64,65.
    assert probes == [6, 7, 32, 33, 64, 65]
    for i in probes:
        assert sum(1 for d in decisions if d < i) % task.N_PLAYERS == 0

    rows = [json.loads(line) for line in
            (tmp_path / "probes.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 6
    assert sorted({r["round"] for r in rows}) == [1, 5, 10]
    assert {r["player_index"] for r in rows} == {0}
    assert {r["question_id"] for r in rows} == {"value_defect_ev", "value_compare"}
    assert all(r["game_id"] == rows[0]["game_id"] for r in rows)
    assert all(r["answerable_from_prompt"] is False for r in rows)
    assert len({r["sampling_seed"] for r in rows}) == 6         # no seed collisions

    # The fake answers "4" everything: right for value_defect_ev at p=0.9, wrong for
    # value_compare (which is 1). Grading is against ground truth, not against hope.
    by_q = {r["question_id"]: r for r in rows}
    assert by_q["value_defect_ev"]["ground_truth"] == 4
    assert by_q["value_defect_ev"]["correct"] is True
    assert by_q["value_compare"]["ground_truth"] == 1
    assert by_q["value_compare"]["correct"] is False

    assert result["n_probes"] == 6 and result["probe_correct"] == 3
    assert result["probe_accuracy"] == 0.5
    assert result["probe_accuracy_by_question"] == {"value_compare": 0.0,
                                                    "value_defect_ev": 1.0}
    done = _records(capsys.readouterr().out, "[CRG_DONE]")[-1]
    assert done["n_probes"] == 6 and done["probe_accuracy"] == 0.5
    assert done["probe_categories"] == ["value"] and done["probes_per_game"] == 6


def test_probing_leaves_the_decisions_byte_identical(tmp_path, monkeypatch):
    """The one property that makes E2 interpretable at all: the game is the same game."""
    plain = _load_task(monkeypatch, CRG_RISKS="0.9", CRG_LANGS="en", CRG_REPS="1")
    plain_result, plain_calls = _run_sweep(plain, tmp_path / "plain", monkeypatch)
    probed = _load_task(monkeypatch, CRG_PROBE="rules,value", CRG_RISKS="0.9",
                        CRG_LANGS="en", CRG_REPS="1")
    probed_result, probed_calls = _run_sweep(probed, tmp_path / "probed", monkeypatch)

    plain_decisions = [p for p in plain_calls if "ANSWER: <your answer>" not in p]
    probed_decisions = [p for p in probed_calls if "ANSWER: <your answer>" not in p]
    assert probed_decisions == plain_decisions
    assert len(probed_calls) - len(plain_calls) == probed.probes_per_game() == 30
    for field in ("group_total", "target_reached", "catastrophe", "mean_payoff"):
        assert probed_result.get(field) == plain_result.get(field)
    assert ((tmp_path / "probed" / "turns.jsonl").read_text(encoding="utf-8")
            == (tmp_path / "plain" / "turns.jsonl").read_text(encoding="utf-8"))


def test_probes_are_identical_under_concurrency(tmp_path, monkeypatch):
    """The parallel path exists for wall-clock only. Probe records are gathered in job
    order and graded single-threaded, so the files it writes must match the sequential
    run byte for byte -- otherwise the arm is not reproducible."""
    env = {"CRG_PROBE": "rules,value", "CRG_RISKS": "0.9", "CRG_LANGS": "en",
           "CRG_REPS": "1"}
    serial = _load_task(monkeypatch, **env)
    _run_sweep(serial, tmp_path / "serial", monkeypatch)
    parallel = _load_task(monkeypatch, CRG_CONCURRENCY="4", **env)
    _run_sweep(parallel, tmp_path / "parallel", monkeypatch)

    assert parallel._CONCURRENCY == 4
    for fname in ("probes.jsonl", "turns.jsonl", "games.csv"):
        assert ((tmp_path / "parallel" / fname).read_bytes()
                == (tmp_path / "serial" / fname).read_bytes()), fname


def test_probe_seats_all_multiplies_by_the_number_of_agents(monkeypatch):
    one = _load_task(monkeypatch, CRG_PROBE="value", CRG_LANGS="en")
    every = _load_task(monkeypatch, CRG_PROBE="value", CRG_LANGS="en",
                       CRG_PROBE_SEATS="all")
    assert one.PROBE_SEATS == (0,) and every.PROBE_SEATS == tuple(range(6))
    assert every.probes_per_game() == one.probes_per_game() * one.N_PLAYERS == 36
    # And the documented cost table for the other arms.
    assert _load_task(monkeypatch, CRG_PROBE="rules,value",
                      CRG_LANGS="en").probes_per_game() == 30
    assert _load_task(monkeypatch, CRG_PROBE="rules,value,time,state",
                      CRG_LANGS="en").probes_per_game() == 146
    assert _load_task(monkeypatch, CRG_PROBE="value", CRG_LANGS="en",
                      CRG_PROBE_ROUNDS="1").probes_per_game() == 2


# ============================================================ resume behaviour ==
def test_resumed_run_neither_re_asks_nor_loses_probes(tmp_path, monkeypatch, capsys):
    env = {"CRG_PROBE": "value", "CRG_RISKS": "0.9", "CRG_LANGS": "en", "CRG_REPS": "2"}
    first = _load_task(monkeypatch, **env)
    first_result, first_calls = _run_sweep(first, tmp_path, monkeypatch)
    assert first_result["n_probes"] == 12 and len(first_calls) == 2 * (60 + 6)

    second = _load_task(monkeypatch, **env)
    second_result, second_calls = _run_sweep(second, tmp_path, monkeypatch)
    assert second_calls == []                          # nothing re-asked, nothing re-paid
    assert second_result["n_probes"] == 12             # nothing lost either
    assert second_result["resumed_games"] == 2
    rows = (tmp_path / "probes.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(rows) == 12
    start = _records(capsys.readouterr().out, "[CRG_START]")[-1]
    assert start["probes_resumed"] == 12


def test_a_shard_missing_its_probes_is_replayed_not_adopted(tmp_path, monkeypatch):
    """The failure this guards against is silent: a shard from a run whose probe set
    was different would otherwise be counted as done, and its answers would simply be
    absent from the analysis."""
    env = {"CRG_PROBE": "value", "CRG_RISKS": "0.9", "CRG_LANGS": "en", "CRG_REPS": "1"}
    task = _load_task(monkeypatch, **env)
    _run_sweep(task, tmp_path, monkeypatch)
    shard_path = next((tmp_path / "checkpoints").glob("*.json"))
    payload = json.loads(shard_path.read_text(encoding="utf-8"))
    payload["probes"] = payload["probes"][:3]          # half the answers went missing
    shard_path.write_text(json.dumps(payload), encoding="utf-8")

    again = _load_task(monkeypatch, **env)
    games, turns, _stats, completed, records = again._load_game_checkpoints(
        tmp_path / "checkpoints", again._checkpoint_signature("m"))
    assert (games, turns, completed, records) == ([], [], set(), [])


def test_probe_and_non_probe_runs_do_not_share_a_signature(tmp_path, monkeypatch):
    sweep = {"CRG_RISKS": "0.9", "CRG_LANGS": "en", "CRG_REPS": "1"}
    plain = _load_task(monkeypatch, **sweep)
    probed = _load_task(monkeypatch, CRG_PROBE="value", **sweep)
    other = _load_task(monkeypatch, CRG_PROBE="rules,value", **sweep)
    rounds = _load_task(monkeypatch, CRG_PROBE="value", CRG_PROBE_ROUNDS="1,5", **sweep)

    sig_plain = plain._checkpoint_signature("m")
    sig_probed = probed._checkpoint_signature("m")
    assert "probe" not in sig_plain
    assert sig_probed["probe"]["categories"] == ["value"]
    assert sig_probed["probe"]["questions_per_game"] == 6
    assert len(sig_probed["probe"]["fingerprint"]) == 16
    for module in (other, rounds):
        assert module._checkpoint_signature("m") != sig_probed
    # Everything that is not the probe still agrees: it is the same game.
    for field in ("risks", "languages", "reps", "prompt_fingerprint", "n_players",
                  "n_rounds", "target", "options", "temperature", "base_seed"):
        assert sig_plain[field] == sig_probed[field], field

    # A baseline shard on disk is refused by a probe run rather than absorbed.
    row = {"game_id": "g1", "model": "m", "language": "en", "risk_probability": 0.9,
           "rep": 0, "target_reached": 1, "group_total": 240.0, "catastrophe": 0}
    turns = [{"game_id": "g1"} for _ in range(plain.N_PLAYERS * plain.N_ROUNDS)]
    plain._save_game_checkpoint(tmp_path, sig_plain, row, turns, 0, 1, 1, 1)
    assert probed._load_game_checkpoints(tmp_path, sig_probed)[0] == []


def test_probe_fingerprint_tracks_the_question_bank(monkeypatch):
    """Declared config is not enough: editing a question text or a ground truth must
    also break resumption, or half a probe run could be finished with another bank."""
    task = _load_task(monkeypatch, CRG_PROBE="value", CRG_LANGS="en")
    before = task._probe_fingerprint()
    monkeypatch.setitem(task._PROBE_Q_TEXT, "value_compare", "which is better?")
    assert task._probe_fingerprint() != before


# ========================================================== misconfiguration ====
def test_unknown_category_is_refused_at_import(monkeypatch):
    with pytest.raises(SystemExit):
        _load_task(monkeypatch, CRG_PROBE="values")        # the axis is "value"
    with pytest.raises(SystemExit):
        _load_task(monkeypatch, CRG_PROBE="rules,ev")


def test_probe_refuses_a_language_it_has_no_question_bank_for(monkeypatch):
    """Better an import-time failure than Vietnamese cells quietly asked English
    questions -- or, worse, quietly not asked at all."""
    with pytest.raises(SystemExit):
        _load_task(monkeypatch, CRG_PROBE="value", CRG_LANGS="en,vn")
    with pytest.raises(SystemExit):
        _load_task(monkeypatch, CRG_PROBE="value", CRG_LANGS="vn")


def test_impossible_probe_settings_are_refused_at_import(monkeypatch):
    with pytest.raises(SystemExit):
        _load_task(monkeypatch, CRG_PROBE="value", CRG_PROBE_ROUNDS="0")
    with pytest.raises(SystemExit):
        _load_task(monkeypatch, CRG_PROBE="value", CRG_PROBE_ROUNDS="11")
    with pytest.raises(SystemExit):
        _load_task(monkeypatch, CRG_PROBE="value", CRG_PROBE_SEATS="6")
    with pytest.raises(SystemExit):
        _load_task(monkeypatch, CRG_PROBE="value", CRG_PROBE_ROUNDS="first")
    with pytest.raises(SystemExit):
        _load_task(monkeypatch, CRG_PROBE="value", CRG_PROBE_SEATS="")


def test_a_probe_template_that_lost_its_decision_tail_fails_loudly(monkeypatch):
    """A silent no-op would keep the CONTRIBUTION anchor, every answer would fail to
    parse, and the shard would report 0% comprehension as if it were a finding."""
    task = _load_task(monkeypatch, CRG_PROBE="value", CRG_LANGS="en")
    with pytest.raises(SystemExit):
        task._to_probe_template("a template with no decision tail")


# ============================================================== launcher fit ====
@pytest.mark.parametrize("knob, default", [("CRG_PROBE", ""),
                                           ("CRG_PROBE_ROUNDS", "1,5,10"),
                                           ("CRG_PROBE_SEATS", "0")])
def test_new_knobs_have_the_textual_shape_the_shard_launcher_rewrites(knob, default):
    """plan/scripts/launch_shard.py bakes values into a shard copy with
    `re.subn(r'os\\.environ\\.get\\("CRG_X", "[^"]*"\\)', ...)`. The server never sees
    an environment variable, so a knob written any other way cannot be set there."""
    source = TASK_PATH.read_text(encoding="utf-8")
    pattern = re.compile(r'os\.environ\.get\("%s", "([^"]*)"\)' % knob)
    assert pattern.findall(source) == [default]
    rewritten, n = pattern.subn('os.environ.get("%s", "x")' % knob, source)
    assert n == 1 and 'os.environ.get("%s", "x")' % knob in rewritten


def test_a_shard_file_with_the_probe_baked_in_imports_and_runs(tmp_path, monkeypatch):
    """End to end through the launcher's mechanism: rewrite the defaults the way
    make_shard_file does, import THAT file, and check the probe is really on. The
    server receives no environment variables, so this is the only path that exists."""
    source = TASK_PATH.read_text(encoding="utf-8")
    for knob, value in (("CRG_PROBE", "rules,value"), ("CRG_LANGS", "en"),
                        ("CRG_RISKS", "0.9"), ("CRG_REPS", "1")):
        source, n = re.subn(r'os\.environ\.get\("%s", "[^"]*"\)' % knob,
                            'os.environ.get("%s", "%s")' % (knob, value), source)
        assert n == 1, knob
    shard = tmp_path / "shard_task.py"
    shard.write_text(source, encoding="utf-8", newline="")

    monkeypatch.setenv("CRG_SKIP_RUN", "1")
    for key in ("CRG_PROBE", "CRG_PROBE_ROUNDS", "CRG_PROBE_SEATS", "CRG_RISKS",
                "CRG_LANGS", "CRG_REPS", "CRG_OUT"):
        monkeypatch.delenv(key, raising=False)
    spec = importlib.util.spec_from_file_location("crg_task_shard_test", shard)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.PROBE_CATEGORIES == ("rules", "value")
    assert module.RISKS == [0.9] and module.LANGS == ["en"] and module.REPS == 1
    assert module.probes_per_game() == 30
    result, calls = _run_sweep(module, tmp_path / "out", monkeypatch)
    assert len(calls) == 60 + 30 and result["n_probes"] == 30
