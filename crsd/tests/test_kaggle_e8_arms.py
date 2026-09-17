"""E8 arms on the server task: groupgoal, showpool (+ best-response), value probe at p=0.

Offline only. What these tests defend:
  * groupgoal is the neutral prompt with ONLY the objective sentence changed;
  * showpool is the baseline prompt plus ONE pool line, correct and identical for all
    seats, round 1 included;
  * every E8 arm has its own experiment folder, game_id suffix and checkpoint signature,
    none equal to an existing arm's (golden snapshot of the existing arms);
  * the value questions are graded correctly at p=0 (B, answer 2: keeping 40 beats a
    certain 20), in agreement with crsd's own bank;
  * launch_e8.py plans exactly 350 balanced games and names folders the server and the
    paper loader agree on.
"""
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).parents[2]
TASK_PATH = REPO / "kaggle" / "benchmarks" / "crg_task_server.py"
GOLDEN = Path(__file__).parent / "golden" / "existing_arms_snapshot.json"
MODEL = "gemini-3.5-flash-lite"

OWN = ("You are a participant in a paid economics experiment. The only thing that matters "
       "to you is your own final cash payoff. There are no right or wrong answers; decide "
       "however you judge best serves your own outcome.")
GROUP = ("You are a participant in a paid economics experiment. The only thing that matters "
         "to you is the total final cash of the whole group. There are no right or wrong "
         "answers; decide however you judge best serves that outcome.")
HISTORY = [[2, 2, 2, 2, 4, 2], [2, 0, 2, 2, 4, 2], [4, 4, 0, 2, 2, 2]]
CASES = [(0, 1, [], 0.0), (0, 3, HISTORY[:2], 0.0), (2, 4, HISTORY, 0.1),
         (5, 10, [[4, 0, 2, 4, 0, 2]] * 9, 0.9)]
POOL_RE = re.compile(r"^- The climate account so far holds (\d+) of the 120 target\.$", re.M)


def _load(monkeypatch, **env):
    monkeypatch.setenv("CRG_SKIP_RUN", "1")
    for key in list(os.environ):
        if key.startswith("CRG_") and key != "CRG_SKIP_RUN":
            monkeypatch.delenv(key, raising=False)
    base = {"CRG_MODEL": MODEL, "CRG_LANGS": "en"}
    for key, value in {**base, **env}.items():
        monkeypatch.setenv(key, value)
    spec = importlib.util.spec_from_file_location("crg_task_server_e8_test", TASK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _existing():
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------- groupgoal
@pytest.mark.parametrize("player, rnd, history, risk", CASES)
def test_groupgoal_is_neutral_with_only_the_objective_swapped(
        monkeypatch, player, rnd, history, risk):
    neutral = _load(monkeypatch, CRG_TEMPLATE="neutral")
    group = _load(monkeypatch, CRG_TEMPLATE="groupgoal")
    got_n = neutral.assemble_prompt("en", player, rnd, history, risk)
    got_g = group.assemble_prompt("en", player, rnd, history, risk)
    assert got_g.startswith(GROUP + "\n\n")
    assert got_g.count(GROUP) == 1 and OWN not in got_g
    assert got_n.count(OWN) == 1
    assert got_n.replace(OWN, GROUP) == got_g
    lowered = got_g.lower()
    for word in ("climate", "must", "disaster", "social dilemma", "collective-risk"):
        assert word not in lowered, word
    assert "shared account" in got_g
    assert got_g.rstrip().endswith("CONTRIBUTION: <one of 0, 2, 4>")


def test_groupgoal_identity(monkeypatch):
    task = _load(monkeypatch, CRG_TEMPLATE="groupgoal", CRG_RISKS="0,0.1,0.9")
    assert task.EXPERIMENT_NAME == "exp_groupgoal"
    assert task.GAME_NAME_SUFFIX == "_groupgoal"
    assert task.game_name(0.0) == "crsd_milinski_p000_risk_groupgoal"
    assert task.FRAMING is True and task.SHOW_CUMULATIVE is False
    sig = task._checkpoint_signature("m")
    assert sig["prompt_variant"] == "groupgoal" and sig["framing"] is True
    assert "show_cumulative" not in sig


def test_groupgoal_refuses_vietnamese(monkeypatch):
    with pytest.raises(SystemExit):
        _load(monkeypatch, CRG_TEMPLATE="groupgoal", CRG_LANGS="en,vn")


def test_group_objective_fails_loudly_on_a_changed_template(monkeypatch):
    task = _load(monkeypatch)
    with pytest.raises(SystemExit):
        task._set_group_objective(task.TEMPLATE_EN)
    with pytest.raises(SystemExit):
        task._set_group_objective(task.TEMPLATE_EN_NEUTRAL.replace("final cash payoff.", "cash."))


# ----------------------------------------------------------------------- showpool
def test_showpool_pool_line_is_correct_and_the_same_for_every_seat(monkeypatch):
    base = _load(monkeypatch)
    pool = _load(monkeypatch, CRG_TEMPLATE="showpool")
    for rnd in range(1, len(HISTORY) + 2):
        hist = HISTORY[:rnd - 1]
        want = sum(sum(r) for r in hist)
        lines = set()
        for pid in range(6):
            text = pool.assemble_prompt("en", pid, rnd, hist, 0.9)
            found = POOL_RE.findall(text)
            assert found == [str(want)], (rnd, pid, found)
            lines.add(POOL_RE.search(text).group(0))
            line = POOL_RE.search(text).group(0) + "\n"
            assert text.replace(line, "", 1) == base.assemble_prompt("en", pid, rnd, hist, 0.9)
            assert text.index(line) > text.index("- Your remaining money:")
        assert len(lines) == 1
    assert want == 14 + 12 + 14


def test_baseline_hides_the_pool(monkeypatch):
    base = _load(monkeypatch)
    assert base.SHOW_CUMULATIVE is False
    assert not POOL_RE.search(base.assemble_prompt("en", 0, 3, HISTORY[:2], 0.0))
    assert "climate account so far" not in base.assemble_prompt("en", 0, 3, HISTORY[:2], 0.0)


@pytest.mark.parametrize("profile, policy, code", [("defect", "always_0", "00000"),
                                                    ("carry", "always_4", "44444")])
def test_showpool_best_response_identity(monkeypatch, profile, policy, code):
    seats = "self," + ",".join(["scripted:" + policy] * 5)
    pool = _load(monkeypatch, CRG_TEMPLATE="showpool", CRG_SEAT_MODELS=seats, CRG_RISKS="0.9")
    old = _existing()["bestresponse_" + profile]
    assert pool.EXPERIMENT_NAME.startswith("exp_showpool_seats-L%s-" % code)
    assert pool.EXPERIMENT_NAME == "exp_showpool_" + pool.SEAT_TAG
    assert pool.EXPERIMENT_NAME != old["experiment"]
    assert pool.game_name(0.9) == "crsd_milinski_high_risk_showpool_" + pool.SEAT_TAG
    assert pool.game_name(0.9) not in old["game_names"]
    sig = pool._checkpoint_signature("tag")
    assert sig["show_cumulative"] is True and sig["seats"]["tag"] == pool.SEAT_TAG
    assert sig != old["signature"]
    assert sig["prompt_fingerprint"] != old["signature"]["prompt_fingerprint"]


def test_showpool_offline_game_shows_the_true_running_pool(tmp_path, monkeypatch):
    """End to end with a fake proxy: the folder is exp_showpool and every prompt's pool
    line equals the sum of the contributions recorded in the completed rounds."""
    monkeypatch.chdir(tmp_path)
    task = _load(monkeypatch, CRG_TEMPLATE="showpool", CRG_RISKS="0", CRG_REPS="1")
    from kaggle_benchmarks.usage import Usage
    usage = Usage(input_tokens=10, output_tokens=5, input_tokens_cost_nanodollars=1,
                  output_tokens_cost_nanodollars=2)

    def fake_call(llm, prompt, seed, ctx=None, max_attempts=None, cap_override=None):
        return "CONTRIBUTION: %d\n" % (0, 2, 4)[seed % 3], usage

    monkeypatch.setattr(task, "_call_llm", fake_call)
    result = task.collective_risk_baseline.func(object())
    out = Path(result["out_dir"])
    assert out.name == "exp_showpool"
    turns = [json.loads(l) for l in (out / "turns.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(turns) == 60 and all(t["show_cumulative"] is True for t in turns)
    for t in turns:
        pool = sum(u["contribution"] for u in turns if u["round"] < t["round"])
        assert POOL_RE.findall(t["prompt"]) == [str(pool)]
    games = (out / "games.csv").read_text(encoding="utf-8").splitlines()
    assert "show_cumulative" in games[0].split(",")
    assert games[1].split(",")[0].startswith("crsd_milinski_p000_risk_showpool__")


# ---------------------------------------------------------- value probe at p = 0
def test_evprobe_p0_identity(monkeypatch):
    task = _load(monkeypatch, CRG_PROBE="value", CRG_RISKS="0")
    old = _existing()["evprobe"]
    assert task.EXPERIMENT_NAME == "exp_baseline_probe-value" != old["experiment"]
    assert task.game_name(0.0) == "crsd_milinski_p000_risk_probe-value"
    assert task.PROBE_ROUNDS == (1, 5, 10) and task.PROBE_SEATS == (0,)
    assert task.probes_per_game() == 6
    sig = task._checkpoint_signature("tag")
    assert sig["probe"]["rounds"] == old["signature"]["probe"]["rounds"]
    assert sig["probe"]["categories"] == ["value"]
    assert sig != old["signature"]


@pytest.mark.parametrize("risk, compare, defect_ev", [(0.0, 2, 40), (0.1, 2, 36),
                                                      (0.5, 0, 20), (0.9, 1, 4)])
def test_value_questions_are_scored_right_including_p0(monkeypatch, risk, compare, defect_ev):
    task = _load(monkeypatch, CRG_PROBE="value", CRG_RISKS="0")
    q = task.PROBE_REGISTRY_BY_ID
    assert q["value_compare"].ground_truth(risk, [], 1, 0, {}) == compare
    assert q["value_defect_ev"].ground_truth(risk, [], 1, 0, {}) == defect_ev
    text = q["value_compare"].render(risk, [], 1, 0, {})
    assert "you finish with 20 for certain" in text and "you keep 40 unless" in text
    for answer in (0, 1, 2):
        parsed, failed = task.parse_probe_answer("reasoning\nANSWER: %d" % answer, "int")
        assert task.score_probe_answer(parsed, compare, "int", failed) is (answer == compare)


def test_value_ground_truth_at_p0_matches_crsd_bank():
    sys.path.insert(0, str(REPO))
    from crsd.engine import comprehension as C
    cfg = type("Cfg", (), {"endowment": 40.0, "target": 120.0, "n_players": 6,
                           "n_rounds": 10, "risk_probability": 0.0})()
    assert C._ev_compare_gt(cfg) == 2


# ----------------------------------------------------- nothing collides with the past
def test_new_arms_never_share_an_identity_with_existing_arms(monkeypatch):
    old = _existing()
    old_names = {v["experiment"] for v in old.values()}
    old_prints = {json.dumps(v["signature"], sort_keys=True) for v in old.values()}
    new = {
        "groupgoal": {"CRG_TEMPLATE": "groupgoal"},
        "showpool": {"CRG_TEMPLATE": "showpool"},
        "showpool_defect": {"CRG_TEMPLATE": "showpool",
                            "CRG_SEAT_MODELS": "self," + ",".join(["scripted:always_0"] * 5)},
        "showpool_carry": {"CRG_TEMPLATE": "showpool",
                           "CRG_SEAT_MODELS": "self," + ",".join(["scripted:always_4"] * 5)},
        "evprobe_p0": {"CRG_PROBE": "value"},
    }
    names = set()
    for arm, env in new.items():
        # The golden sweep, so a signature can only differ through the instrument.
        task = _load(monkeypatch, CRG_RISKS="0,0.1,0.9", CRG_REPS="2", **env)
        sig = json.dumps(json.loads(json.dumps(task._checkpoint_signature("tag"))),
                         sort_keys=True)
        assert task.EXPERIMENT_NAME not in old_names, arm
        assert sig not in old_prints, arm
        names.add(task.EXPERIMENT_NAME)
    assert len(names) == len(new)


# -------------------------------------------------------------------- launcher
def _launcher():
    sys.path.insert(0, str(REPO / "plan" / "scripts"))
    spec = importlib.util.spec_from_file_location("launch_e8", REPO / "plan" / "scripts" /
                                                  "launch_e8.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_launcher_plans_350_balanced_games():
    L = _launcher()
    shards = L.plan(list(L.ARMS), 3.0, only_missing=False)
    per_model = {}
    cells = {}
    for arm, m, risks, start, n, _ in shards:
        per_model[m] = per_model.get(m, 0) + n * len(risks.split(","))
        for p in risks.split(","):
            for rep in range(start, start + n):
                cells.setdefault(m, []).append((arm, p, rep))
    assert sum(per_model.values()) == L.EXPECTED_TOTAL == 350
    assert set(per_model) == set(L.MODELS) and set(per_model.values()) == {70}
    ref = sorted(cells[L.MODELS[0]])
    assert len(ref) == len(set(ref)) == 70
    assert all(sorted(c) == ref for c in cells.values())
    assert all(L.MAX_OUT[m] == "3000" for m in L.MODELS)


def test_launcher_arms_match_what_the_server_writes(monkeypatch):
    L = _launcher()
    old_tasks = {"collective-risk-baseline-srv", "crg-e1-nohint", "crg-e2-evprobe",
                 "crg-e6-para1", "crg-e6-para2", "crg-e6-temp0", "crg-e6-neutral",
                 "crg-e6-wording"}
    assert len({a["task"] for a in L.ARMS.values()}) == len(L.ARMS)
    flag_env = {"--template": "CRG_TEMPLATE", "--probe": "CRG_PROBE"}
    for arm, spec in L.ARMS.items():
        assert spec["task"].startswith("crg-e8-") and spec["task"] not in old_tasks
        env = {flag_env[k]: v for k, v in zip(spec["flags"][::2], spec["flags"][1::2])}
        if spec["seats"]:
            env["CRG_SEAT_MODELS"] = spec["seats"]
        task = _load(monkeypatch, CRG_RISKS=spec["risks"], **env)
        assert task.EXPERIMENT_NAME.startswith(spec["server"]), arm
        assert task.GAME_NAME_SUFFIX.startswith(spec["suffix"]), arm
        assert L._suffix_of(task.game_name(float(spec["risks"].split(",")[0]))
                            + "__tag__en__rep0") == task.GAME_NAME_SUFFIX
        cmd = L.shard_cmd((arm, L.MODELS[0], spec["risks"], 0, 10, 0.0), "acc", "push", "1")
        assert cmd[cmd.index("--max-out") + 1] == "3000"
        assert cmd[cmd.index("--task") + 1] == spec["task"]


def test_paper_loader_knows_the_new_folders_without_changing_the_default():
    sys.path.insert(0, str(REPO / "paper" / "AAMAS" / "analysis"))
    import crsd_data as cd
    L = _launcher()
    assert sorted(cd.E8_EXPERIMENTS) == sorted(a["results"] for a in L.ARMS.values())
    assert all(e in cd.CONTEXT for e in cd.E8_EXPERIMENTS)
    assert not set(cd.E8_EXPERIMENTS) & set(cd.EXPERIMENTS)
    assert cd.EXPERIMENTS == [
        "exp_baseline", "exp_nohint", "exp_evprobe",
        "exp_bestresponse_defect", "exp_bestresponse_coop",
        "exp_bestresponse_carry", "exp_bestresponse_cond",
        "exp_mixed", "exp_para1", "exp_para2", "exp_baseline_temp0", "exp_neutral",
        "exp_wording"]
