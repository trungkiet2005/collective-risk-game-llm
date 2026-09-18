"""Analysis guardrails; follow-up evidence is not accepted by row count alone."""
from pathlib import Path
import hashlib
import importlib.util
import sys
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / 'paper/AAMAS/analysis'
sys.path.insert(0, str(ANALYSIS))
SPEC = importlib.util.spec_from_file_location('e8_followup', ANALYSIS / 'e8_controls.py')
e8 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(e8)


def test_partial_panel_is_not_analysed():
    with pytest.raises(ValueError):
        e8.extract({'complete': False, 'counts': {'games': 340, 'turns': 20400, 'probes': 300}})


def test_bootstrap_is_reproducible_and_preserves_constant_game_means():
    first = e8.estimate([20.0] * 10, 'same-key')
    second = e8.estimate([20.0] * 10, 'same-key')
    assert first[:3] == second[:3] == (20.0, 20.0, 20.0)
    assert np.array_equal(first[3], second[3])


def test_distinct_contrast_groups_do_not_share_resampling_indices():
    x = list(range(10))
    assert not np.array_equal(e8.estimate(x, 'baseline')[3], e8.estimate(x, 'followup')[3])


@pytest.mark.parametrize('name,digest', [
    ('e8_contrasts.csv', '3b876611882ff7fc498e4acd5038b1408900790448440333c4be047145fabb06'),
    ('e8_probes.csv', '02ff257f8bf6c9e6f8afdd431c482a455a0a8a52d51590d4433ad446c725a438'),
])
def test_committed_outputs_match_accepted_execution(name, digest):
    assert hashlib.sha256((ANALYSIS / 'followups' / name).read_bytes()).hexdigest() == digest
