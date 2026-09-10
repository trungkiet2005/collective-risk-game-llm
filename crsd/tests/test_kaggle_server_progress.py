"""Server-arm resumability, stdout progress protocol and self-healing.

Covers kaggle/benchmarks/crg_task_server.py, which is a self-contained
reimplementation (it does NOT import crsd), so everything here loads that file as
a module and drives it OFFLINE -- no proxy call is ever made.
"""
import contextlib
import csv
import importlib.util
import json
from pathlib import Path

import pytest

TASK_PATH = Path(__file__).parents[2] / "kaggle" / "benchmarks" / "crg_task_server.py"


def _load_task(monkeypatch, **env):
    """Fresh import of the server task with a controlled sweep (no run fired)."""
    monkeypatch.setenv("CRG_SKIP_RUN", "1")
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    spec = importlib.util.spec_from_file_location("crg_task_server_progress_test", TASK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _records(captured, tag):
    """Parse one tag out of captured stdout, asserting the line protocol holds."""
    out = []
    for line in captured.splitlines():
        if line.startswith(tag + " "):
            body = line[len(tag) + 1:]
            assert body == body.strip(), "record must be a single trimmed JSON object"
            out.append(json.loads(body))
    return out


def _usage(module):
    from kaggle_benchmarks.usage import Usage
    return Usage(input_tokens=10, output_tokens=5,
                 input_tokens_cost_nanodollars=1_000,
                 output_tokens_cost_nanodollars=2_000)


def _fake_chat(module, monkeypatch, replies):
    """Replace the proxy call site: `_LLM.prompt` inside `kbench.chats.new`."""
    calls = []

    class _Chat:
        usage = _usage(module)

    @contextlib.contextmanager
    def new_chat(*args, **kwargs):
        yield _Chat()

    class _LLM:
        model = module.MODEL

        def prompt(self, prompt, **kwargs):
            calls.append(prompt)
            reply = replies[min(len(calls) - 1, len(replies) - 1)]
            if isinstance(reply, Exception):
                raise reply
            return reply

    monkeypatch.setattr(module.kbench.chats, "new", new_chat)
    monkeypatch.setattr(module, "_LLM", _LLM())
    monkeypatch.setattr(module.time, "sleep", lambda *_: None)
    return calls


# ---------------------------------------------------------------- signature ---
def test_signature_separates_prompt_variants(monkeypatch):
    """A nohint run and a baseline run of the same model MUST NOT share a
    signature, or the variant run silently resumes baseline games."""
    baseline = _load_task(monkeypatch)
    sig_baseline = baseline._checkpoint_signature("m")
    assert sig_baseline["prompt_variant"] == "baseline"
    assert len(sig_baseline["prompt_fingerprint"]) == 16

    variant = _load_task(monkeypatch, CRG_PROMPT_VARIANT="nohint")
    sig_variant = variant._checkpoint_signature("m")
    assert sig_variant["prompt_variant"] == "nohint"
    assert sig_variant != sig_baseline


def test_signature_covers_every_meaning_bearing_parameter(monkeypatch):
    task = _load_task(monkeypatch)
    sig = task._checkpoint_signature("m")
    for field in ("schema_version", "model", "prompt_variant", "prompt_fingerprint",
                  "risks", "languages", "reps", "rep_start", "max_completion_tokens",
                  "n_players", "n_rounds", "endowment", "target", "options",
                  "temperature", "base_seed", "persona_set", "memory_mode", "framing"):
        assert field in sig, field


def test_fingerprint_tracks_the_rendered_prompt(monkeypatch):
    """Editing the instrument without touching CRG_PROMPT_VARIANT still changes the
    signature: the fingerprint hashes the RENDERED prompt, not the declared name."""
    task = _load_task(monkeypatch)
    before = task._prompt_fingerprint()
    monkeypatch.setattr(task, "TEMPLATES", dict(task.TEMPLATES, en="edited {history}: [x]"))
    assert task._prompt_fingerprint() != before


def test_variant_run_does_not_resume_a_baseline_shard(tmp_path, monkeypatch):
    baseline = _load_task(monkeypatch)
    row = {"game_id": "g1", "model": "m", "language": "en", "risk_probability": 0.9,
           "rep": 0, "target_reached": 1, "group_total": 240.0, "catastrophe": 0}
    turns = [{"game_id": "g1"} for _ in range(baseline.N_PLAYERS * baseline.N_ROUNDS)]
    baseline._save_game_checkpoint(tmp_path, baseline._checkpoint_signature("m"),
                                   row, turns, 0, 1, 1, 1)

    variant = _load_task(monkeypatch, CRG_PROMPT_VARIANT="nohint")
    games, _, _, completed, records = variant._load_game_checkpoints(
        tmp_path, variant._checkpoint_signature("m"))
    assert games == [] and completed == set() and records == []


# --------------------------------------------------------------- resumption ---
def _shard(task, tmp_path, risk, lang, rep, game_id, n_turns=None, turn_id=None):
    row = {"game_id": game_id, "model": "m", "language": lang,
           "risk_probability": risk, "rep": rep, "target_reached": 1,
           "group_total": 240.0, "catastrophe": 0}
    n = task.N_PLAYERS * task.N_ROUNDS if n_turns is None else n_turns
    turns = [{"game_id": turn_id or game_id} for _ in range(n)]
    return task._save_game_checkpoint(tmp_path, task._checkpoint_signature("m"),
                                      row, turns, 0, 1, 1, 1)


def test_duplicate_game_id_is_never_counted_twice(tmp_path, monkeypatch, capsys):
    task = _load_task(monkeypatch, CRG_RISKS="0.9", CRG_LANGS="en", CRG_REPS="2")
    _shard(task, tmp_path, 0.9, "en", 0, "dup")
    _shard(task, tmp_path, 0.9, "en", 1, "dup")            # same id, other cell
    games, turns, _, completed, records = task._load_game_checkpoints(
        tmp_path, task._checkpoint_signature("m"))
    assert len(games) == 1 and len(records) == 1
    assert len(turns) == task.N_PLAYERS * task.N_ROUNDS
    errors = _records(capsys.readouterr().out, "[CRG_ERROR]")
    assert any(e["kind"] == "checkpoint_invalid" and "duplicate game_id" in e["message"]
               for e in errors)


def test_misfiled_and_half_written_shards_are_replayed(tmp_path, monkeypatch):
    task = _load_task(monkeypatch, CRG_RISKS="0.9", CRG_LANGS="en", CRG_REPS="3")
    sig = task._checkpoint_signature("m")
    # rep recorded in the row disagrees with the cell the file is filed under
    path = _shard(task, tmp_path, 0.9, "en", 0, "g0")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["game"]["rep"] = 1
    path.write_text(json.dumps(payload), encoding="utf-8")
    # a game whose turns belong to another game
    _shard(task, tmp_path, 0.9, "en", 1, "g1", turn_id="somewhere-else")
    # a game that died half way through
    _shard(task, tmp_path, 0.9, "en", 2, "g2", n_turns=17)

    games, turns, _, completed, records = task._load_game_checkpoints(tmp_path, sig)
    assert games == [] and turns == [] and completed == set() and records == []


def test_csv_survives_a_row_written_by_an_older_schema(tmp_path, monkeypatch):
    task = _load_task(monkeypatch)
    rows = [{"game_id": "a", "rep": 0}, {"game_id": "b", "rep": 1, "extra": 7}]
    task._write_materialized_outputs(tmp_path, rows, [])
    with open(tmp_path / "games.csv", newline="", encoding="utf-8") as f:
        got = list(csv.DictReader(f))
    assert [r["game_id"] for r in got] == ["a", "b"]
    assert got[0]["extra"] == "" and got[1]["extra"] == "7"


# ------------------------------------------------------------ stdout protocol --
def test_emitted_records_are_one_ascii_line_of_json(capsys, monkeypatch):
    task = _load_task(monkeypatch)
    task._emit("[CRG_ERROR]", {"msg": "line one\nline two", "vn": "tieếng Việt"})
    out = capsys.readouterr().out
    assert out.count("\n") == 1
    assert all(ord(c) < 128 for c in out)
    assert json.loads(out.split(" ", 1)[1])["msg"] == "line one\nline two"


def test_error_records_carry_kind_http_and_cell(capsys, monkeypatch):
    task = _load_task(monkeypatch)
    task._emit_error("transient", "Error code: 503 - heavy load", fatal=False,
                     ctx={"game_id": "g", "risk": 0.9, "lang": "vn", "rep": 3,
                          "round": 4, "player": "Player_2"}, attempt=2)
    rec = _records(capsys.readouterr().out, "[CRG_ERROR]")[0]
    assert rec["kind"] == "transient" and rec["http"] == 503 and rec["fatal"] is False
    assert (rec["risk"], rec["lang"], rec["rep"], rec["round"]) == (0.9, "vn", 3, 4)
    assert rec["attempt"] == 2


# --------------------------------------------------------------- self-healing --
def test_transient_5xx_is_retried_then_succeeds(monkeypatch, capsys):
    task = _load_task(monkeypatch)
    calls = _fake_chat(task, monkeypatch, [
        RuntimeError("Error code: 503 - model is under heavy load"),
        "CONTRIBUTION: 4\n"])
    text, _ = task._call_llm(None, "p", 1, ctx={"risk": 0.9})
    assert text.strip() == "CONTRIBUTION: 4" and len(calls) == 2
    errors = _records(capsys.readouterr().out, "[CRG_ERROR]")
    assert [e["kind"] for e in errors] == ["transient"]
    assert errors[0]["http"] == 503 and errors[0]["fatal"] is False


def test_transient_exhaustion_is_reported_as_fatal(monkeypatch, capsys):
    task = _load_task(monkeypatch, CRG_MAX_ATTEMPTS="3")
    calls = _fake_chat(task, monkeypatch, [RuntimeError("429 rate limit")])
    with pytest.raises(RuntimeError):
        task._call_llm(None, "p", 1)
    assert len(calls) == 3
    kinds = [e["kind"] for e in _records(capsys.readouterr().out, "[CRG_ERROR]")]
    assert kinds == ["transient", "transient", "transient_exhausted"]


def test_empty_reply_is_retried_and_never_becomes_a_contribution(monkeypatch, capsys):
    """HTTP 200 with reply == '' must not fall through to parse_contribution, which
    would silently record a contribution of 0 (run 1 fabricated whole games so)."""
    task = _load_task(monkeypatch)
    calls = _fake_chat(task, monkeypatch, ["", "", "CONTRIBUTION: 4\n"])
    text, _ = task._call_llm(None, "p", 1)
    assert text.strip() == "CONTRIBUTION: 4" and len(calls) == 3
    errors = _records(capsys.readouterr().out, "[CRG_ERROR]")
    assert [e["kind"] for e in errors] == ["empty_content", "empty_content"]
    assert all(e["http"] == 200 for e in errors)
    assert task.parse_contribution("")[1] is True          # would have been a 0


def test_empty_reply_budget_is_separate_from_the_transient_budget(monkeypatch):
    task = _load_task(monkeypatch, CRG_MAX_ATTEMPTS="2")
    calls = _fake_chat(task, monkeypatch, ["", "", "", "", "CONTRIBUTION: 2\n"])
    text, _ = task._call_llm(None, "p", 1)
    assert text.strip() == "CONTRIBUTION: 2" and len(calls) == 5


def test_cost_cap_403_is_distinct_and_not_retried(monkeypatch, capsys):
    task = _load_task(monkeypatch)
    reauths = []
    monkeypatch.setattr(task, "_reauth", lambda: reauths.append(1))
    calls = _fake_chat(task, monkeypatch, [RuntimeError(
        "Error code: 403 - max estimated cost of operation ($3.200045) exceeds your "
        "available quota (based on max_output_tokens)")])
    with pytest.raises(RuntimeError):
        task._call_llm(None, "p", 1)
    assert len(calls) == 1 and reauths == []               # retry/reauth cannot help
    rec = _records(capsys.readouterr().out, "[CRG_ERROR]")[0]
    assert rec["kind"] == "quota_cap_403" and rec["http"] == 403 and rec["fatal"] is True
    assert "CRG_MAX_OUT" in rec["hint"]


def test_401_refreshes_the_token_and_keeps_going(monkeypatch, capsys):
    task = _load_task(monkeypatch)
    reauths = []
    monkeypatch.setattr(task, "_reauth", lambda: reauths.append(1))
    calls = _fake_chat(task, monkeypatch, [
        RuntimeError("Error code: 401 - expired token"), "CONTRIBUTION: 0\n"])
    text, _ = task._call_llm(None, "p", 1)
    assert text.strip() == "CONTRIBUTION: 0" and len(calls) == 2 and reauths == [1]
    rec = _records(capsys.readouterr().out, "[CRG_ERROR]")[0]
    assert rec["kind"] == "auth_refresh" and rec["http"] == 401


def test_reauth_reports_and_repairs_a_model_switch(monkeypatch, capsys):
    """A refresh that quietly rebuilds on the account default model would file every
    later game under the selected model's name -- unrecoverable, so it is repaired."""
    task = _load_task(monkeypatch)
    task.MODEL = "anthropic/claude-opus-5-default"

    import dotenv
    from kaggle_benchmarks.kaggle import models

    monkeypatch.setattr(task.subprocess, "run", lambda *a, **k: None)
    monkeypatch.setattr(dotenv, "load_dotenv", lambda override=False: None)

    class _Client:
        def __init__(self, model):
            self.model = model

    monkeypatch.setattr(models, "load_default_model",
                        lambda: _Client("google/gemini-3-flash-preview"))
    monkeypatch.setattr(models, "load_model", lambda name: _Client(name))

    task._reauth()
    assert task._LLM.model == "anthropic/claude-opus-5-default"
    rec = _records(capsys.readouterr().out, "[CRG_ERROR]")[0]
    assert rec["kind"] == "model_drift" and rec["got"] == "google/gemini-3-flash-preview"


# ------------------------------------------------------- end-to-end, offline ---
def _run_sweep(task, out_dir, monkeypatch, reply="CONTRIBUTION: 4\n", fail_on=None):
    """Drive the real sweep with the proxy call replaced. Returns (result, n_calls)."""
    calls = []

    def fake_call(llm, prompt, seed, ctx=None, max_attempts=None):
        calls.append(ctx)
        if fail_on is not None and ctx is not None and fail_on(ctx):
            raise RuntimeError("Error code: 503 - heavy load (test)")
        return reply, _usage(task)

    monkeypatch.setattr(task, "_call_llm", fake_call)
    monkeypatch.setenv("CRG_OUT", str(out_dir))
    result = task.collective_risk_baseline.func(object())
    return result, calls


def test_full_offline_sweep_emits_the_progress_protocol(tmp_path, monkeypatch, capsys):
    task = _load_task(monkeypatch, CRG_RISKS="0.9", CRG_LANGS="en", CRG_REPS="2",
                      CRG_OUT=str(tmp_path / "out"))
    result, calls = _run_sweep(task, tmp_path / "out", monkeypatch)
    out = capsys.readouterr().out

    start = _records(out, "[CRG_START]")
    progress = _records(out, "[CRG_PROGRESS]")
    done = _records(out, "[CRG_DONE]")
    assert len(start) == 1 and start[0]["total"] == 2 and start[0]["resumed"] == 0
    assert start[0]["prompt_variant"] == "baseline"
    assert [p["done"] for p in progress] == [1, 2]
    for p in progress:
        for field in ("done", "total", "model", "risk", "lang", "rep", "game_id",
                      "reached", "cost_usd", "elapsed_s", "resumed", "parse_failed"):
            assert field in p, field
        assert p["total"] == 2 and p["resumed"] is False and p["reached"] is True
    assert len(done) == 1 and done[0]["status"] == "ok"
    assert done[0]["done"] == 2 and done[0]["parse_failed"] == 0
    assert done[0]["cost_usd"] == pytest.approx(result["usage_total_cost_usd"])
    assert done[0]["failed_games"] == 0
    assert len(calls) == 2 * task.N_PLAYERS * task.N_ROUNDS
    assert (tmp_path / "out" / "games.csv").is_file()
    assert result["n_games"] == 2 and result["resumed_games"] == 0


def test_the_sweep_resumes_and_replays_nothing(tmp_path, monkeypatch, capsys):
    out_dir = tmp_path / "out"
    first = _load_task(monkeypatch, CRG_RISKS="0.9", CRG_LANGS="en", CRG_REPS="2",
                       CRG_OUT=str(out_dir))
    _run_sweep(first, out_dir, monkeypatch)
    capsys.readouterr()

    second = _load_task(monkeypatch, CRG_RISKS="0.9", CRG_LANGS="en", CRG_REPS="2",
                        CRG_OUT=str(out_dir))
    result, calls = _run_sweep(second, out_dir, monkeypatch)
    out = capsys.readouterr().out

    assert calls == []                                  # not one paid call replayed
    assert result["resumed_games"] == 2 and result["new_games"] == 0
    progress = _records(out, "[CRG_PROGRESS]")
    assert [p["done"] for p in progress] == [1, 2]
    assert all(p["resumed"] is True for p in progress)
    assert _records(out, "[CRG_DONE]")[0]["status"] == "ok"

    with open(out_dir / "games.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2                               # no double-counted game
    assert len({r["game_id"] for r in rows}) == 2
    with open(out_dir / "turns.jsonl", encoding="utf-8") as f:
        assert sum(1 for _ in f) == 2 * second.N_PLAYERS * second.N_ROUNDS


def test_partial_sweep_resumes_where_it_died(tmp_path, monkeypatch, capsys):
    """The Kaggle-dies-mid-way case: shard 1 is already on disk, the re-run plays
    only the cells that are missing."""
    out_dir = tmp_path / "out"
    first = _load_task(monkeypatch, CRG_RISKS="0.9", CRG_LANGS="en", CRG_REPS="3",
                       CRG_OUT=str(out_dir))
    with pytest.raises(RuntimeError):
        _run_sweep(first, out_dir, monkeypatch, fail_on=lambda ctx: ctx["rep"] == 1)
    aborted = _records(capsys.readouterr().out, "[CRG_DONE]")
    assert aborted[0]["status"] == "aborted" and aborted[0]["done"] == 1

    second = _load_task(monkeypatch, CRG_RISKS="0.9", CRG_LANGS="en", CRG_REPS="3",
                        CRG_OUT=str(out_dir))
    result, calls = _run_sweep(second, out_dir, monkeypatch)
    assert result["resumed_games"] == 1 and result["new_games"] == 2
    assert len(calls) == 2 * second.N_PLAYERS * second.N_ROUNDS
    progress = _records(capsys.readouterr().out, "[CRG_PROGRESS]")
    assert [p["resumed"] for p in progress] == [True, False, False]


def test_default_aborts_on_a_dead_cell_and_skip_mode_carries_on(tmp_path, monkeypatch,
                                                                capsys):
    out_dir = tmp_path / "abort"
    task = _load_task(monkeypatch, CRG_RISKS="0.9", CRG_LANGS="en", CRG_REPS="2",
                      CRG_OUT=str(out_dir))
    assert task.ON_GAME_ERROR == "abort"                 # unchanged default
    with pytest.raises(RuntimeError):
        _run_sweep(task, out_dir, monkeypatch, fail_on=lambda ctx: ctx["rep"] == 0)
    errors = _records(capsys.readouterr().out, "[CRG_ERROR]")
    fail = [e for e in errors if e["kind"] == "game_failed"][0]
    assert fail["fatal"] is True and fail["action"] == "abort"

    out_dir = tmp_path / "skip"
    task = _load_task(monkeypatch, CRG_RISKS="0.9", CRG_LANGS="en", CRG_REPS="2",
                      CRG_ON_GAME_ERROR="skip", CRG_OUT=str(out_dir))
    result, _ = _run_sweep(task, out_dir, monkeypatch,
                           fail_on=lambda ctx: ctx["rep"] == 0)
    out = capsys.readouterr().out
    assert result["n_games"] == 1 and result["failed_games"] == 1
    assert result["failed_cells"][0]["rep"] == 0
    done = _records(out, "[CRG_DONE]")[0]
    assert done["status"] == "partial" and done["failed_games"] == 1
    fail = [e for e in _records(out, "[CRG_ERROR]") if e["kind"] == "game_failed"][0]
    assert fail["action"] == "skip" and fail["http"] == 503
