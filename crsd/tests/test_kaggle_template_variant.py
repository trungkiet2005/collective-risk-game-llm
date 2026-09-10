"""E1 no-anchor arm: CRG_TEMPLATE on the server task.

Covers kaggle/benchmarks/crg_task_server.py, a self-contained reimplementation (it
does NOT import crsd), so everything here loads that file as a module and drives it
OFFLINE -- no proxy call is ever made.

The one claim these tests exist to defend: the nohint prompt is the baseline prompt
MINUS the two equal-split anchors and nothing else. If any other word moves, E1 stops
measuring the anchor and starts measuring wording, and the run cannot be interpreted.
"""
import difflib
import importlib.util
import re
from pathlib import Path

import pytest

TASK_PATH = Path(__file__).parents[2] / "kaggle" / "benchmarks" / "crg_task_server.py"
PROMPT_DIR = Path(__file__).parents[1] / "prompts"

# The two spans, as they appear RENDERED for the baseline game constants
# (fairShare = 120 / (6 * 10) = 2, fairShareKept = 40 - 2 * 10 = 20).
RENDERED_ANCHORS = (
    " (an average of 2 per player per round)",
    " (for example, contributing 2 every round leaves you 20 at the end)",
)

# Rendered-prompt hash of the baseline instrument, pinned. Every game already in
# results/frontier was measured with this exact text, and the checkpoint signature
# keys on it: if this value moves, every existing baseline shard stops resuming and
# the frontier arm is no longer one instrument. A deliberate change to the baseline
# wording must therefore update this line AND re-derive the nohint variant.
BASELINE_FINGERPRINT = "f78785cba0905583"


def _load_task(monkeypatch, **env):
    """Fresh import of the server task with a controlled environment."""
    monkeypatch.setenv("CRG_SKIP_RUN", "1")
    monkeypatch.delenv("CRG_TEMPLATE", raising=False)
    monkeypatch.delenv("CRG_PROMPT_VARIANT", raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    spec = importlib.util.spec_from_file_location("crg_task_server_tpl_test", TASK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------- defaults ---
def test_default_environment_is_the_untouched_baseline(monkeypatch):
    """No CRG_TEMPLATE set == the instrument that produced results/frontier."""
    task = _load_task(monkeypatch)
    assert task.TEMPLATE_VARIANT == "baseline"
    assert task.EXPERIMENT_NAME == "exp_baseline"
    assert task.PROMPT_VARIANT == "baseline"
    assert task.TEMPLATES == {"en": task.TEMPLATE_EN, "vn": task.TEMPLATE_VN}
    assert task._prompt_fingerprint() == BASELINE_FINGERPRINT
    for anchor in RENDERED_ANCHORS:
        assert anchor in task.assemble_prompt("en", 0, 1, [], 0.9)


def test_prompt_variant_defaults_to_the_template_but_stays_overridable(monkeypatch):
    """The declared name follows the template, so the two cannot disagree by
    accident; an explicit CRG_PROMPT_VARIANT still wins (two arms, one template)."""
    assert _load_task(monkeypatch, CRG_TEMPLATE="nohint",
                      CRG_LANGS="en").PROMPT_VARIANT == "nohint"
    assert _load_task(monkeypatch, CRG_PROMPT_VARIANT="probe").PROMPT_VARIANT == "probe"


# ------------------------------------------------------- the nohint arm ---
def test_nohint_selects_its_own_template_experiment_and_language_set(monkeypatch):
    baseline = _load_task(monkeypatch)
    nohint = _load_task(monkeypatch, CRG_TEMPLATE="nohint", CRG_LANGS="en")

    assert nohint.TEMPLATE_VARIANT == "nohint"
    assert nohint.EXPERIMENT_NAME == "exp_nohint"
    assert nohint.TEMPLATES == {"en": nohint.TEMPLATE_EN_NOHINT}
    # English-only panel: no Vietnamese no-anchor template, and the Vietnamese
    # baseline template is left exactly as it was.
    assert "vn" not in nohint.TEMPLATES
    assert nohint.TEMPLATE_VN == baseline.TEMPLATE_VN
    # The unmodified English baseline is still present and still carries the anchors.
    assert nohint.TEMPLATE_EN == baseline.TEMPLATE_EN


def test_game_names_match_the_open_weight_arm_for_each_variant(monkeypatch):
    """Baseline names are the untouched join key; nohint names match the open-weight
    no-anchor configs (crsd/configs/game/crsd_milinski_high_risk_nohint.json), so the
    two arms join -- and so a nohint row can never share a game_id with the baseline
    row of the same cell."""
    baseline = _load_task(monkeypatch)
    nohint = _load_task(monkeypatch, CRG_TEMPLATE="nohint", CRG_LANGS="en")
    cfg_dir = Path(__file__).parents[1] / "configs" / "game"

    for risk, stem in ((0.9, "crsd_milinski_high_risk"),
                       (0.5, "crsd_milinski_medium_risk"),
                       (0.1, "crsd_milinski_low_risk")):
        assert baseline.game_name(risk) == stem
        assert nohint.game_name(risk) == stem + "_nohint"
        assert (cfg_dir / f"{stem}.json").is_file()
        assert (cfg_dir / f"{stem}_nohint.json").is_file()
    # Generated levels (the Q8 grid) follow the same rule.
    assert baseline.game_name(0.3) == "crsd_milinski_p030_risk"
    assert nohint.game_name(0.3) == "crsd_milinski_p030_risk_nohint"


@pytest.mark.parametrize(
    "player, rnd, history, risk",
    [(0, 1, [], 0.9),
     (0, 2, [[0, 2, 4, 0, 2, 4]], 0.9),
     (3, 5, [[2] * 6] * 4, 0.5),
     (5, 10, [[4, 0, 2, 4, 0, 2]] * 9, 0.1)],
)
def test_rendered_prompts_differ_only_in_the_two_anchor_spans(
        monkeypatch, player, rnd, history, risk):
    """The whole point of E1, asserted at the level of the delivered bytes."""
    baseline = _load_task(monkeypatch)
    nohint = _load_task(monkeypatch, CRG_TEMPLATE="nohint", CRG_LANGS="en")

    rendered_baseline = baseline.assemble_prompt("en", player, rnd, history, risk)
    rendered_nohint = nohint.assemble_prompt("en", player, rnd, history, risk)

    stripped = rendered_baseline
    for anchor in RENDERED_ANCHORS:
        assert stripped.count(anchor) == 1, anchor
        stripped = stripped.replace(anchor, "")
    assert stripped == rendered_nohint

    # Same claim from the other side: a line diff may touch exactly two lines.
    changed = [line for line in difflib.unified_diff(
        rendered_baseline.splitlines(), rendered_nohint.splitlines(), lineterm="", n=0)
        if line[:1] in "+-" and line[:3] not in ("+++", "---")]
    assert len(changed) == 4, changed          # 2 removed + 2 added
    assert "{fairShare}" not in rendered_nohint


def test_nohint_template_matches_the_recorded_crsd_prompt(monkeypatch):
    """Cross-check against crsd/prompts/crsd_nohint_en.txt, the repo's record of the
    no-anchor instrument. The two files differ in their optional blocks (the server
    copy is frozen at the baseline block set), so the comparison is on the two lines
    the anchor removal actually touches."""
    nohint = _load_task(monkeypatch, CRG_TEMPLATE="nohint", CRG_LANGS="en")
    recorded = (PROMPT_DIR / "crsd_nohint_en.txt").read_text(
        encoding="utf-8").splitlines()
    produced = nohint.TEMPLATE_EN_NOHINT.splitlines()
    for prefix in ("The group's target:", "- If the group reaches"):
        got = [line for line in produced if line.startswith(prefix)]
        want = [line for line in recorded if line.startswith(prefix)]
        assert len(got) == 1 and len(want) == 1, prefix
        assert got[0] == want[0]


def test_the_probe_prompt_follows_the_active_template(monkeypatch):
    """E1 and E2 can share one shard (CRG_TEMPLATE=nohint CRG_PROBE=rules,value).

    The probe prompt is DERIVED from the ACTIVE decision template, so a comprehension
    question asked inside the no-anchor arm must be anchor-free as well. A probe still
    carrying "an average of 2 per player per round" would do two kinds of damage at
    once: it would grade comprehension of a prompt that arm never played, and it would
    hand the agent the anchor mid-game -- the one thing E1 exists to remove.
    """
    probe = {"CRG_PROBE": "rules,value", "CRG_LANGS": "en"}
    baseline = _load_task(monkeypatch, **probe)
    nohint = _load_task(monkeypatch, CRG_TEMPLATE="nohint", **probe)

    question = "How many rounds does the game last?"
    args = ("en", 0, 3, [[0, 2, 4, 0, 2, 4], [2] * 6], 0.9, question)
    rendered_baseline = baseline.assemble_probe_prompt(*args)
    rendered_nohint = nohint.assemble_probe_prompt(*args)

    # It is still a probe: the question is asked and the ANSWER anchor is intact.
    assert question in rendered_nohint
    assert "ANSWER:" in rendered_nohint
    assert "CONTRIBUTION:" not in rendered_nohint

    # And it differs from the baseline probe by the two anchor spans, nothing else.
    stripped = rendered_baseline
    for anchor in RENDERED_ANCHORS:
        assert stripped.count(anchor) == 1, anchor
        stripped = stripped.replace(anchor, "")
    assert stripped == rendered_nohint


def test_stripping_a_missing_anchor_fails_loudly(monkeypatch):
    """A silent no-op is the expensive failure: the arm would play the baseline
    prompt, spend the shard's budget and return a null result that looks real."""
    task = _load_task(monkeypatch)
    with pytest.raises(SystemExit):
        task._strip_anchors("a template with no anchors in it at all")
    with pytest.raises(SystemExit):       # first span present, second one gone
        task._strip_anchors(
            "reach at least {target}"
            + task._ANCHOR_SPANS[0] + ".")


# ------------------------------------------- resume / overwrite protection ---
def test_nohint_cannot_resume_or_be_confused_with_baseline_shards(
        tmp_path, monkeypatch):
    """Same model, same sweep, different template -> different signature, and a
    baseline shard on disk is refused rather than absorbed."""
    sweep = {"CRG_RISKS": "0.9", "CRG_LANGS": "en", "CRG_REPS": "1"}
    baseline = _load_task(monkeypatch, **sweep)
    nohint = _load_task(monkeypatch, CRG_TEMPLATE="nohint", **sweep)

    sig_baseline = baseline._checkpoint_signature("m")
    sig_nohint = nohint._checkpoint_signature("m")
    assert sig_baseline != sig_nohint
    assert sig_baseline["prompt_variant"] == "baseline"
    assert sig_nohint["prompt_variant"] == "nohint"
    assert sig_baseline["prompt_fingerprint"] != sig_nohint["prompt_fingerprint"]
    # Everything that is NOT the prompt still agrees -- the arms are the same game.
    for field in ("risks", "languages", "reps", "n_players", "n_rounds", "endowment",
                  "target", "options", "temperature", "base_seed", "model"):
        assert sig_baseline[field] == sig_nohint[field], field

    checkpoints = tmp_path / "checkpoints"
    row = {"game_id": "g1", "risk_probability": 0.9, "language": "en", "rep": 0}
    turns = [{"game_id": "g1"} for _ in range(baseline.N_PLAYERS * baseline.N_ROUNDS)]
    baseline._save_game_checkpoint(checkpoints, sig_baseline, row, turns, 0, 1, 1, 1)

    assert baseline._load_game_checkpoints(checkpoints, sig_baseline)[3] == {
        baseline._condition_key(0.9, "en", 0)}
    games, loaded, _stats, completed, _records = nohint._load_game_checkpoints(
        checkpoints, sig_nohint)
    assert (games, loaded, completed) == ([], [], set())


def test_nohint_results_land_in_their_own_experiment_directory(tmp_path, monkeypatch):
    """End to end, offline: a nohint sweep writes results/frontier/<model>/exp_nohint
    and leaves exp_baseline alone."""
    monkeypatch.chdir(tmp_path)                    # default CRG_OUT is relative
    task = _load_task(monkeypatch, CRG_TEMPLATE="nohint", CRG_RISKS="0.9",
                      CRG_LANGS="en", CRG_REPS="1")
    from kaggle_benchmarks.usage import Usage
    usage = Usage(input_tokens=10, output_tokens=5,
                  input_tokens_cost_nanodollars=1_000,
                  output_tokens_cost_nanodollars=2_000)
    prompts = []

    def fake_call(llm, prompt, seed, ctx=None, max_attempts=None):
        prompts.append(prompt)
        return "CONTRIBUTION: 4\n", usage

    monkeypatch.setattr(task, "_call_llm", fake_call)
    monkeypatch.delenv("CRG_OUT", raising=False)
    result = task.collective_risk_baseline.func(object())

    model_tag = re.sub(r"[^A-Za-z0-9._-]+", "-", task.MODEL)
    expected = tmp_path / "results" / "frontier" / model_tag / "exp_nohint"
    assert Path(result["out_dir"]).resolve() == expected.resolve()
    assert (expected / "games.csv").is_file()
    assert not (tmp_path / "results" / "frontier" / model_tag / "exp_baseline").exists()
    assert result["template_variant"] == "nohint"
    assert result["experiment"] == "exp_nohint"
    # Every prompt actually delivered to the model is anchor-free.
    assert prompts and not any(a in p for p in prompts for a in RENDERED_ANCHORS)


# --------------------------------------------------------- misconfiguration ---
def test_unknown_template_variant_is_refused_at_import(monkeypatch):
    with pytest.raises(SystemExit):
        _load_task(monkeypatch, CRG_TEMPLATE="no-hint")     # typo: the real one is nohint


def test_nohint_refuses_a_language_it_has_no_template_for(monkeypatch):
    """Better an import-time failure than a Vietnamese cell silently served the
    baseline wording, which still carries the anchor."""
    with pytest.raises(SystemExit):
        _load_task(monkeypatch, CRG_TEMPLATE="nohint", CRG_LANGS="en,vn")
    with pytest.raises(SystemExit):
        _load_task(monkeypatch, CRG_TEMPLATE="nohint", CRG_LANGS="vn")


# ------------------------------------------------------------ launcher fit ---
def test_new_knob_has_the_textual_shape_the_shard_launcher_rewrites():
    """plan/scripts/launch_shard.py bakes sweep values into a shard copy with
    `re.subn(r'os\\.environ\\.get\\("CRG_X", "[^"]*"\\)', ...)`. A knob written any
    other way (a variable default, a different quote style) cannot be set on the
    server, where env vars do not reach the task."""
    source = TASK_PATH.read_text(encoding="utf-8")
    pattern = re.compile(r'os\.environ\.get\("CRG_TEMPLATE", "([^"]*)"\)')
    matches = pattern.findall(source)
    assert matches == ["baseline"], matches
    rewritten, n = pattern.subn('os.environ.get("CRG_TEMPLATE", "nohint")', source)
    assert n == 1
    assert 'os.environ.get("CRG_TEMPLATE", "nohint")' in rewritten
