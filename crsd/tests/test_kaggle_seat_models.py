"""Mixed-model groups and scripted seats on the server task (CRG_SEAT_MODELS).

Covers kaggle/benchmarks/crg_task_server.py, a self-contained reimplementation (it
does NOT import crsd), so everything here loads that file as a module and drives it
OFFLINE -- no proxy call is ever made, no client is ever built for real.

Three claims these tests exist to defend:
  1. An unset CRG_SEAT_MODELS is byte-for-byte the sweep the file played before the
     knob existed -- same folder, same game_id, same signature, same records.
  2. A scripted seat decides EXACTLY what crsd/models/scripted.py decides. The two
     arms have to agree or the best-response baseline means different things in the
     open-weight and frontier halves of the same figure.
  3. A mixed run cannot be confused with a baseline run: different output folder,
     different game_id, different checkpoint signature -- and only one seat per llm
     seat calls the proxy, which is where the 6x saving comes from.
"""
import contextlib
import csv
import importlib.util
import itertools
import json
from pathlib import Path

import pytest

from crsd.models import scripted as crsd_scripted

TASK_PATH = Path(__file__).parents[2] / "kaggle" / "benchmarks" / "crg_task_server.py"

# The seat spec used by the best-response arm: one llm seat, five known opponents.
BEST_RESPONSE = ("self,scripted:always_4,scripted:always_4,scripted:always_4,"
                 "scripted:always_4,scripted:always_4")
TEST_MODEL = "test-model-a"


def _load_task(monkeypatch, **env):
    """Fresh import of the server task with a controlled environment.

    CRG_MODEL and LLM_DEFAULT are pinned together: the module writes LLM_DEFAULT into
    the real environment at import, and pinning it through monkeypatch is what makes
    that write revert at teardown instead of leaking into the next test module.
    """
    monkeypatch.setenv("CRG_SKIP_RUN", "1")
    for key in ("CRG_SEAT_MODELS", "CRG_TEMPLATE", "CRG_PROMPT_VARIANT", "CRG_PROBE",
                "CRG_PROBE_SEATS", "CRG_PROBE_ROUNDS", "CRG_MAX_OUT", "CRG_OUT"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("CRG_MODEL", TEST_MODEL)
    monkeypatch.setenv("LLM_DEFAULT", TEST_MODEL)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    spec = importlib.util.spec_from_file_location("crg_task_server_seat_test",
                                                  TASK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _stub_proxy(task, monkeypatch, reply="reasoning\nCONTRIBUTION: 2"):
    """Replace the proxy call site and hand back a per-client record of prompts."""
    from kaggle_benchmarks.usage import Usage

    class _Chat:
        usage = Usage(input_tokens=10, output_tokens=5,
                      input_tokens_cost_nanodollars=1_000,
                      output_tokens_cost_nanodollars=2_000)

    @contextlib.contextmanager
    def new_chat(*args, **kwargs):
        yield _Chat()

    seen = {}

    class _Client:
        def __init__(self, model):
            self.model = model

        def prompt(self, prompt, **kwargs):
            seen.setdefault(self.model, []).append(kwargs)
            return reply

    monkeypatch.setattr(task.kbench.chats, "new", new_chat)
    monkeypatch.setattr(task, "_LLM", _Client(task.MODEL))
    # Never build a real client: a seat on another slug gets a stub with that slug.
    monkeypatch.setattr(task, "_build_seat_client", _Client)
    monkeypatch.setattr(task, "_SEAT_CLIENTS", {})
    monkeypatch.setattr(task.time, "sleep", lambda *_: None)
    return seen


# ------------------------------------------------------------------ defaults ---
def test_unset_knob_is_the_untouched_baseline(monkeypatch):
    """The whole point of the default: nothing about a normal sweep moves."""
    task = _load_task(monkeypatch)
    assert task.SEAT_MODELS == ()
    assert task.SEAT_TAG == "" and task.SEAT_SUFFIX == ""
    assert task.EXPERIMENT_NAME == "exp_baseline"
    # The three original game configs are the join key against results/ and the
    # open-weight arm. They must be spelled exactly as they always were.
    assert task.game_name(0.9) == "crsd_milinski_high_risk"
    assert task.game_name(0.5) == "crsd_milinski_medium_risk"
    assert task.game_name(0.1) == "crsd_milinski_low_risk"
    signature = task._checkpoint_signature("m")
    assert "seats" not in signature
    # Pinned in test_kaggle_template_variant.py as well: the instrument is unchanged.
    assert signature["prompt_fingerprint"] == "f78785cba0905583"


def test_unset_knob_leaves_records_without_seat_fields(monkeypatch):
    task = _load_task(monkeypatch)
    _stub_proxy(task, monkeypatch)
    turns = []
    row, parse_failed, _, _, _ = task.play_game(None, 0.9, "en", 0, "tag", turns)
    assert parse_failed == 0
    assert len(turns) == task.N_PLAYERS * task.N_ROUNDS
    assert all("seat_model" not in turn for turn in turns)
    assert "seat_models" not in row
    assert row["game_id"] == "crsd_milinski_high_risk__tag__en__rep0"


def test_unset_knob_routes_every_call_through_the_global_client(monkeypatch):
    """None and the selected MODEL both resolve to `_LLM`, the client _reauth
    rebuilds in place -- otherwise a token refresh would stop taking effect."""
    task = _load_task(monkeypatch)
    _stub_proxy(task, monkeypatch)
    assert task._client_for(None) is task._LLM
    assert task._client_for(task.MODEL) is task._LLM
    assert task._SEAT_CLIENTS == {}


# ------------------------------------------------------------- spec parsing ---
def test_spec_resolves_self_and_empty_entries_to_the_selected_model(monkeypatch):
    task = _load_task(monkeypatch,
                      CRG_SEAT_MODELS="self,,SELF,scripted:always_0,other-slug,self")
    assert task.SEAT_MODELS == (TEST_MODEL, TEST_MODEL, TEST_MODEL,
                                "scripted:always_0", "other-slug", TEST_MODEL)
    assert task.SEAT_LLM_SEATS == (0, 1, 2, 4, 5)
    assert task.SEAT_FOREIGN_SLUGS == ("other-slug",)


@pytest.mark.parametrize("spec", [
    "self,self,self",                                   # too few seats
    "self,self,self,self,self,self,self",               # too many
    "self,scripted:always_3,self,self,self,self",       # policy does not exist
    "self,scripted:,self,self,self,self",               # empty policy
    "self,my model,self,self,self,self",                # whitespace in a slug
])
def test_a_bad_spec_dies_at_import_not_mid_shard(monkeypatch, spec):
    """Every one of these would otherwise spend a shard's budget measuring something
    other than what was asked for."""
    with pytest.raises(SystemExit):
        _load_task(monkeypatch, CRG_SEAT_MODELS=spec)


def test_probing_a_scripted_seat_is_refused(monkeypatch):
    """A policy has nothing to comprehend; grading one would fabricate accuracy."""
    with pytest.raises(SystemExit):
        _load_task(monkeypatch, CRG_SEAT_MODELS=BEST_RESPONSE, CRG_PROBE="value",
                   CRG_PROBE_SEATS="1", CRG_LANGS="en")
    # The llm seat of the same group is still probeable.
    task = _load_task(monkeypatch, CRG_SEAT_MODELS=BEST_RESPONSE, CRG_PROBE="value",
                      CRG_PROBE_SEATS="0", CRG_LANGS="en")
    assert task.PROBE_SEATS == (0,)


# ------------------------------------ parity with the open-weight arm's policies ---
def _crsd_ctx(task, seat, history, risk):
    return {
        "seat": seat,
        "round": len(history) + 1,
        "n_players": task.N_PLAYERS,
        "n_rounds": task.N_ROUNDS,
        "endowment": float(task.ENDOWMENT),
        "target": float(task.TARGET),
        "options": list(task.OPTIONS),
        "risk_probability": risk,
        "history": [list(row) for row in history],
    }


HISTORIES = [
    [],
    [[0, 0, 0, 0, 0, 0]],
    [[4, 4, 4, 4, 4, 4]],
    [[0, 2, 4, 0, 2, 4]],
    [[0, 0, 0, 0, 0, 4], [4, 4, 4, 4, 4, 0]],
    [[2, 2, 2, 2, 2, 2], [0, 4, 0, 4, 0, 4], [2, 0, 2, 0, 2, 0]],
]


def test_scripted_policies_match_crsd_case_by_case(monkeypatch):
    """The server file cannot import crsd, so the only thing keeping the two
    implementations together is this comparison."""
    task = _load_task(monkeypatch)
    assert set(task.SCRIPTED_POLICIES) == set(crsd_scripted.POLICY_NAMES)
    for policy, risk, history, seat in itertools.product(
            task.SCRIPTED_POLICIES, (0.1, 0.5, 0.9), HISTORIES, range(6)):
        here = task.scripted_decide(policy, risk, history, seat)
        there = crsd_scripted.decide(policy, _crsd_ctx(task, seat, history, risk))
        assert here == there, (policy, risk, history, seat, here, there)
        assert here in task.OPTIONS


def test_scripted_policy_behaviour_is_the_documented_one(monkeypatch):
    """Spot-check the two policies that actually reason, so a parity bug that moved
    BOTH implementations the same way still fails."""
    task = _load_task(monkeypatch)
    assert task.scripted_decide("always_0", 0.9, [], 0) == 0
    assert task.scripted_decide("always_4", 0.1, HISTORIES[3], 2) == 4
    # ev_maximiser: (1-p)*40 vs 120/6 = 20 -> withhold below p*=0.5, pay at or above.
    assert task.scripted_decide("ev_maximiser", 0.1, [], 0) == 0
    assert task.scripted_decide("ev_maximiser", 0.49, HISTORIES[2], 0) == 0
    assert task.scripted_decide("ev_maximiser", 0.5, [], 0) == 2
    assert task.scripted_decide("ev_maximiser", 0.9, HISTORIES[1], 0) == 2
    # conditional_cooperator: fair share first, then the mean of the OTHERS.
    assert task.scripted_decide("conditional_cooperator", 0.9, [], 3) == 2
    assert task.scripted_decide("conditional_cooperator", 0.9, [[0, 4, 4, 4, 4, 4]],
                                0) == 4
    assert task.scripted_decide("conditional_cooperator", 0.9, [[4, 0, 0, 0, 0, 0]],
                                0) == 0
    # A tie between two legal amounts keeps the LOWER one, as crsd does.
    assert task._nearest_option(1) == 0 and task._nearest_option(3) == 2
    assert crsd_scripted.nearest_option(1) == 0


def test_scripted_reply_parses_back_to_the_same_number(monkeypatch):
    """The stub reply travels through turns.jsonl like a model's, so it must survive
    the same parser -- and it must say which policy produced it."""
    task = _load_task(monkeypatch)
    text = task.scripted_response_text("scripted:always_4", 4)
    assert text.splitlines()[0] == "[scripted:always_4]"
    assert task.parse_contribution(text) == (4, False)
    assert task.extract_reasoning(text) == "[scripted:always_4]"


# ------------------------------------------------------------- routing a game ---
def test_best_response_group_calls_the_proxy_for_one_seat_only(monkeypatch):
    """The 6x saving, and the reason E3a is affordable: five of six seats are free."""
    task = _load_task(monkeypatch, CRG_SEAT_MODELS=BEST_RESPONSE)
    seen = _stub_proxy(task, monkeypatch)
    turns = []
    row, parse_failed, tok_in, tok_out, cost = task.play_game(
        None, 0.9, "en", 0, "tag", turns)

    assert parse_failed == 0
    assert len(seen[TEST_MODEL]) == task.N_ROUNDS       # 10 calls, not 60
    assert sum(len(v) for v in seen.values()) == task.N_ROUNDS
    assert len(turns) == task.N_PLAYERS * task.N_ROUNDS
    # P1 answered 2 every round (the stub), P2..P6 played always_4.
    assert [t["contribution"] for t in turns[:6]] == [2, 4, 4, 4, 4, 4]
    assert row["group_total"] == float(10 * (2 + 4 * 5))
    # Usage is charged for the llm seat only.
    assert (tok_in, tok_out) == (10 * 10, 10 * 5)
    assert cost == 10 * 3_000


def test_turn_and_game_records_attribute_every_seat(monkeypatch):
    task = _load_task(monkeypatch, CRG_SEAT_MODELS=BEST_RESPONSE)
    _stub_proxy(task, monkeypatch)
    turns = []
    row, _, _, _, _ = task.play_game(None, 0.9, "en", 0, "tag", turns)

    assert [t["seat_model"] for t in turns[:6]] == [
        TEST_MODEL] + ["scripted:always_4"] * 5
    assert row["seat_models"] == "|".join(task.SEAT_MODELS)
    # Same key and same "|" separator as crsd/dataio/recorder.py writes.
    assert row["seat_models"].split("|")[1] == "scripted:always_4"
    scripted_turn = turns[1]
    assert scripted_turn["raw_response"].endswith("CONTRIBUTION: 4")
    assert scripted_turn["parse_failed"] is False
    assert scripted_turn["prompt"]                      # still built, still logged


def test_two_llm_seats_use_two_clients_and_one_credential(monkeypatch):
    """The mixed-population arm: the second slug gets its own client, built once,
    from the same proxy credential -- and the seats do not cross."""
    task = _load_task(
        monkeypatch,
        CRG_SEAT_MODELS="self,self,self,other-slug,other-slug,scripted:always_0")
    seen = _stub_proxy(task, monkeypatch)
    turns = []
    row, _, _, _, _ = task.play_game(None, 0.9, "en", 0, "tag", turns)

    assert task.SEAT_FOREIGN_SLUGS == ("other-slug",)
    assert len(seen[TEST_MODEL]) == 3 * task.N_ROUNDS
    assert len(seen["other-slug"]) == 2 * task.N_ROUNDS
    assert task._client_for("other-slug") is task._client_for("other-slug")  # cached
    assert task._client_for("other-slug") is not task._LLM
    assert [t["seat_model"] for t in turns[:6]] == [
        TEST_MODEL, TEST_MODEL, TEST_MODEL, "other-slug", "other-slug",
        "scripted:always_0"]
    assert [t["contribution"] for t in turns[:6]] == [2, 2, 2, 2, 2, 0]


def test_a_reauth_rebuilds_the_seat_clients_too(monkeypatch):
    """Seat clients bake the key in at construction, so a refresh that rebuilt only
    `_LLM` would leave the other seats on the dead token."""
    import dotenv
    import kaggle_benchmarks.kaggle.models as kmodels

    task = _load_task(monkeypatch, CRG_SEAT_MODELS=BEST_RESPONSE)
    seen = _stub_proxy(task, monkeypatch)
    assert seen is not None
    stale = task._client_for("x-slug")
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr(task.subprocess, "run", lambda *a, **k: None)
    monkeypatch.setattr(kmodels, "load_default_model",
                        lambda: type(task._LLM)(task.MODEL))

    task._reauth()

    assert task._client_for("x-slug") is not stale
    assert task._client_for("x-slug").model == "x-slug"


# ------------------------------------------------- separation from baseline ---
def test_the_seat_configuration_renames_folder_game_and_signature(monkeypatch):
    baseline = _load_task(monkeypatch)
    mixed = _load_task(monkeypatch, CRG_SEAT_MODELS=BEST_RESPONSE)

    assert mixed.SEAT_TAG.startswith("seats-L44444-")
    assert mixed.EXPERIMENT_NAME == "exp_baseline_" + mixed.SEAT_TAG
    assert mixed.game_name(0.9) == "crsd_milinski_high_risk_" + mixed.SEAT_TAG
    assert mixed.game_name(0.9) != baseline.game_name(0.9)

    signature = mixed._checkpoint_signature("m")
    assert signature["seats"]["models"] == list(mixed.SEAT_MODELS)
    assert signature["seats"]["tag"] == mixed.SEAT_TAG
    assert signature != baseline._checkpoint_signature("m")


def test_different_groups_never_share_a_tag(monkeypatch):
    """Same policies, different order, and a different invader slug: three groups,
    three folders. A shared tag would silently merge two experiments."""
    a = _load_task(monkeypatch, CRG_SEAT_MODELS=BEST_RESPONSE)
    b = _load_task(monkeypatch,
                   CRG_SEAT_MODELS="scripted:always_4,self,scripted:always_4,"
                                   "scripted:always_4,scripted:always_4,"
                                   "scripted:always_4")
    c = _load_task(monkeypatch,
                   CRG_SEAT_MODELS="self,self,self,slug-x,slug-x,slug-x")
    d = _load_task(monkeypatch,
                   CRG_SEAT_MODELS="self,self,self,slug-y,slug-y,slug-y")
    tags = {a.SEAT_TAG, b.SEAT_TAG, c.SEAT_TAG, d.SEAT_TAG}
    assert len(tags) == 4
    assert c.SEAT_TAG.startswith("seats-LLLMMM-")


def test_a_mixed_run_does_not_resume_a_baseline_shard(tmp_path, monkeypatch):
    baseline = _load_task(monkeypatch)
    row = {"game_id": "g1", "model": "m", "language": "en", "risk_probability": 0.9,
           "rep": 0, "target_reached": 1, "group_total": 240.0, "catastrophe": 0}
    turns = [{"game_id": "g1"} for _ in range(baseline.N_PLAYERS * baseline.N_ROUNDS)]
    baseline._save_game_checkpoint(tmp_path, baseline._checkpoint_signature("m"),
                                   row, turns, 0, 1, 1, 1)

    mixed = _load_task(monkeypatch, CRG_SEAT_MODELS=BEST_RESPONSE)
    games, _, _, completed, records = mixed._load_game_checkpoints(
        tmp_path, mixed._checkpoint_signature("m"))
    assert games == [] and completed == set() and records == []


# ------------------------------------------------------------ per-seat caps ---
def test_output_cap_follows_the_seat_model(monkeypatch):
    """A reasoning model in seat P4 needs its own budget or it returns EMPTY content;
    raising the cap for the cheap seats instead invites the reservation 403."""
    task = _load_task(monkeypatch,
                      CRG_SEAT_MODELS="self,self,self,gemini-3.6-flash,"
                                      "gemini-3.6-flash,scripted:always_0")
    assert task.MAX_OUT == 512                       # test-model-a is not a reasoner
    assert task._max_out_for(None) == 512
    assert task._max_out_for(task.MODEL) == 512
    assert task._max_out_for("gemini-3.6-flash") == 6000
    assert task._checkpoint_signature("m")["seats"]["max_completion_tokens"] == {
        "gemini-3.6-flash": 6000}

    pinned = _load_task(monkeypatch, CRG_MAX_OUT="1234",
                        CRG_SEAT_MODELS="self,self,self,gemini-3.6-flash,"
                                        "gemini-3.6-flash,scripted:always_0")
    # An explicit cap is the manual override, and it holds for every seat.
    assert pinned._max_out_for("gemini-3.6-flash") == 1234
    assert pinned._max_out_for(None) == 1234


# ------------------------------------------------------- end-to-end, offline ---
def _records(captured, tag):
    return [json.loads(line[len(tag) + 1:]) for line in captured.splitlines()
            if line.startswith(tag + " ")]


def test_full_mixed_sweep_writes_an_attributable_folder(tmp_path, monkeypatch,
                                                        capsys):
    """The whole path, offline: preflight, banner, per-seat routing, materialized
    outputs. The folder must be the mixed one -- a best-response sweep that landed in
    exp_baseline would overwrite the baseline games of the same model."""
    task = _load_task(monkeypatch, CRG_RISKS="0.9", CRG_LANGS="en", CRG_REPS="1",
                      CRG_SEAT_MODELS="self,other-slug,scripted:always_4,"
                                      "scripted:always_4,scripted:ev_maximiser,"
                                      "scripted:conditional_cooperator")
    seen = _stub_proxy(task, monkeypatch)
    monkeypatch.chdir(tmp_path)                 # CRG_OUT unset -> the real layout
    result = task.collective_risk_baseline.func(task._LLM)
    out = capsys.readouterr().out

    out_dir = tmp_path / "results" / "frontier" / task.MODEL / task.EXPERIMENT_NAME
    assert task.EXPERIMENT_NAME.startswith("exp_baseline_seats-LM44EC-")
    assert out_dir.is_dir(), sorted(p.name for p in (tmp_path / "results").rglob("*"))
    assert result["n_games"] == 1 and result["parse_fail_rate"] == 0.0
    assert result["seat_models"] == "|".join(task.SEAT_MODELS)
    assert result["llm_calls_per_game"] == 2 * task.N_ROUNDS

    # Two llm seats called, four scripted seats did not.
    assert len(seen[TEST_MODEL]) == task.N_ROUNDS
    assert len(seen["other-slug"]) == task.N_ROUNDS
    # The preflight built the foreign client before any game was played.
    assert set(task._SEAT_CLIENTS) == {"other-slug"}

    start = _records(out, "[CRG_START]")[0]
    assert start["seat_models"] == list(task.SEAT_MODELS)
    assert start["seat_tag"] == task.SEAT_TAG
    assert start["llm_seats"] == [0, 1]
    assert start["foreign_slugs"] == ["other-slug"]
    assert _records(out, "[CRG_DONE]")[0]["seat_tag"] == task.SEAT_TAG

    with open(out_dir / "games.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["seat_models"] == "|".join(task.SEAT_MODELS)
    assert task.SEAT_TAG in rows[0]["game_id"]
    with open(out_dir / "turns.jsonl", encoding="utf-8") as f:
        turns = [json.loads(line) for line in f]
    assert len(turns) == task.N_PLAYERS * task.N_ROUNDS
    assert {t["seat_model"] for t in turns} == set(task.SEAT_MODELS)


def test_an_unlisted_slug_warns_but_does_not_stop_the_run(tmp_path, monkeypatch,
                                                          capsys):
    """LLMS_AVAILABLE has never been pinned down on the production server, so a slug
    missing from it is evidence, not a verdict."""
    task = _load_task(monkeypatch, CRG_RISKS="0.9", CRG_LANGS="en", CRG_REPS="1",
                      CRG_OUT=str(tmp_path / "out"),
                      CRG_SEAT_MODELS="self,self,self,other-slug,other-slug,"
                                      "scripted:always_0")
    monkeypatch.setenv("LLMS_AVAILABLE", "%s,something-else" % TEST_MODEL)
    _stub_proxy(task, monkeypatch)
    result = task.collective_risk_baseline.func(task._LLM)
    out = capsys.readouterr().out

    warned = [r for r in _records(out, "[CRG_ERROR]")
              if r["kind"] == "seat_model_unlisted"]
    assert len(warned) == 1
    assert warned[0]["unlisted"] == ["other-slug"] and warned[0]["fatal"] is False
    assert result["n_games"] == 1                       # the sweep still ran
