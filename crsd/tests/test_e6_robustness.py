"""E6 robustness arms: two paraphrases and a temperature=0 control.

Covers kaggle/benchmarks/crg_task_server.py, loaded as a module and driven OFFLINE --
no proxy call is ever made.

Two claims these tests exist to defend.

First: the paraphrase arms change the WORDING and nothing else. E6 answers the reviewer
question "is this an artifact of how you phrased it?", and that answer is only
interpretable if the rewrite left the game identical. A paraphrase that silently drops
a placeholder still renders into fluent English, still costs a full shard, and returns
a difference that reads like a wording effect but is really a different game.

Second: the temperature arm must not land in the baseline's folder. It plays the
baseline wording, so without a suffix its games would be written into the very
directory the risk grid lives in, and to_wide_csv.py reads the experiment name off
that directory -- the decoding control would be merged into the frame it is meant to
be compared against. Identical hazard to the one PROBE_SUFFIX and SEAT_SUFFIX exist
to prevent.
"""
import importlib.util
import re
from pathlib import Path

import pytest

TASK_PATH = Path(__file__).parents[2] / "kaggle" / "benchmarks" / "crg_task_server.py"

# Rendered-prompt hash of the baseline instrument, pinned in
# test_kaggle_template_variant.py and repeated here on purpose: E6 adds template
# variants, and the one thing it must never do is move the baseline. Every game
# already in results/ was measured with this exact text and the checkpoint signature
# keys on it.
BASELINE_FINGERPRINT = "f78785cba0905583"

# The equal-split anchors as RENDERED for the baseline constants (fairShare = 120 /
# (6 * 10) = 2, fairShareKept = 40 - 2 * 10 = 20). They belong to E1's contrast, not
# E6's, so BOTH paraphrases must still carry them: an E6 arm that quietly dropped the
# anchor would be running E1 under another name.
RENDERED_ANCHORS = (
    " (an average of 2 per player per round)",
    " (for example, contributing 2 every round leaves you 20 at the end)",
)


def _load_task(monkeypatch, **env):
    """Fresh import of the server task with a controlled environment."""
    monkeypatch.setenv("CRG_SKIP_RUN", "1")
    for key in ("CRG_TEMPLATE", "CRG_PROMPT_VARIANT", "CRG_TEMPERATURE",
                "CRG_PROBE", "CRG_SEAT_MODELS"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    spec = importlib.util.spec_from_file_location("crg_task_server_e6_test", TASK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _placeholders(text):
    return set(re.findall(r"\{(\w+)\}", text))


def _block_keys(text):
    return set(re.findall(r"\{(\w+)\}: \[", text))


# ------------------------------------------------------------ the untouched default
def test_mac_dinh_khong_doi_mot_byte_nao(monkeypatch):
    """An unset environment is the instrument that produced every existing game."""
    task = _load_task(monkeypatch)
    assert task.TEMPLATE_VARIANT == "baseline"
    assert task.TEMPERATURE == 0.7
    assert task.TEMP_SUFFIX == ""
    assert task.EXPERIMENT_NAME == "exp_baseline"
    assert task.GAME_NAME_SUFFIX == ""
    assert task._prompt_fingerprint() == BASELINE_FINGERPRINT


# ------------------------------------------------------------------ the paraphrases
@pytest.mark.parametrize("variant", ["para1", "para2"])
def test_paraphrase_doi_cach_dien_dat_chu_khong_doi_tro_choi(monkeypatch, variant):
    task = _load_task(monkeypatch, CRG_TEMPLATE=variant)
    base = task.TEMPLATE_SETS["baseline"]["en"]
    text = task.TEMPLATES["en"]

    assert task.EXPERIMENT_NAME == "exp_" + variant
    assert task.GAME_NAME_SUFFIX == "_" + variant
    # cung bo placeholder va cung bo khoi dieu kien -> cung mot tro choi
    assert _placeholders(text) == _placeholders(base)
    assert _block_keys(text) == _block_keys(base)
    # khac baseline that su, khong phai ban sao
    assert text != base
    # duoi quyet dinh GIU Y HET: doi huong dan dinh dang tra loi se tron ty le parse
    # vao cai le ra phai la hieu ung dien dat
    assert text.count(task._DECISION_TAIL_EN) == 1


@pytest.mark.parametrize("variant", ["para1", "para2"])
def test_paraphrase_van_mang_du_hai_mo_neo(monkeypatch, variant):
    """The equal-split anchor is E1's variable, held CONSTANT across E6's arms."""
    task = _load_task(monkeypatch, CRG_TEMPLATE=variant)
    prompt = task.assemble_prompt("en", 0, 1, [], 0.9)
    for anchor in RENDERED_ANCHORS:
        assert anchor in prompt, "%s danh mat mo neo %r" % (variant, anchor)


def test_hai_paraphrase_khac_nhau_va_khac_baseline(monkeypatch):
    """Three distinct instruments, or E6 spends its budget measuring one twice."""
    fps = {}
    for variant in ("baseline", "para1", "para2"):
        task = _load_task(monkeypatch, CRG_TEMPLATE=variant)
        fps[variant] = task._prompt_fingerprint()
    assert len(set(fps.values())) == 3, fps
    assert fps["baseline"] == BASELINE_FINGERPRINT


@pytest.mark.parametrize("variant", ["para1", "para2"])
def test_paraphrase_thuan_ascii(monkeypatch, variant):
    """Kaggle's push reads this file with the system codepage and has died on that."""
    task = _load_task(monkeypatch, CRG_TEMPLATE=variant)
    task.TEMPLATES["en"].encode("ascii")


def test_bien_the_la_chet_ngay_luc_import(monkeypatch):
    with pytest.raises(SystemExit) as err:
        _load_task(monkeypatch, CRG_TEMPLATE="para9")
    assert "para9" in str(err.value)


# -------------------------------------------------------------- the decoding control
def test_temp0_khong_roi_vao_thu_muc_baseline(monkeypatch):
    """The whole point of TEMP_SUFFIX: a temp arm plays the baseline WORDING."""
    task = _load_task(monkeypatch, CRG_TEMPERATURE="0")
    assert task.TEMPERATURE == 0.0
    assert task.TEMP_SUFFIX == "_temp0"
    assert task.EXPERIMENT_NAME == "exp_baseline_temp0"
    assert task.GAME_NAME_SUFFIX == "_temp0"
    # van la prompt baseline, tung byte
    assert task._prompt_fingerprint() == BASELINE_FINGERPRINT


def test_temp0_khong_resume_duoc_tu_checkpoint_cua_temp07(monkeypatch):
    """Folder separation is half the fix; the signature is the other half."""
    hot = _load_task(monkeypatch)._checkpoint_signature("m")
    cold = _load_task(monkeypatch, CRG_TEMPERATURE="0")._checkpoint_signature("m")
    assert hot["temperature"] == 0.7
    assert cold["temperature"] == 0.0
    assert hot != cold


def test_hau_to_nhiet_do_le_van_doc_duoc_lam_ten_thu_muc(monkeypatch):
    """Directory names cannot carry a dot cleanly; risk-0p9 already sets the rule."""
    task = _load_task(monkeypatch, CRG_TEMPERATURE="0.3")
    assert task.TEMP_SUFFIX == "_temp0p3"
    assert task.EXPERIMENT_NAME == "exp_baseline_temp0p3"


def test_paraphrase_cong_temp0_gop_ca_hai_hau_to(monkeypatch):
    task = _load_task(monkeypatch, CRG_TEMPLATE="para1", CRG_TEMPERATURE="0")
    assert task.EXPERIMENT_NAME == "exp_para1_temp0"
    assert task.GAME_NAME_SUFFIX == "_para1_temp0"
