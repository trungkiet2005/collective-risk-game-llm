"""Game-aligned uncertainty for the answer/action contrasts in Figure 3."""
from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "paper" / "AAMAS" / "analysis"))
import probes as pr


@pytest.fixture
def paired_cells(monkeypatch):
    monkeypatch.setattr(pr.cd, "N_BOOT", 200)
    answers, games = [], []
    for model in pr.cs.MODEL_ORDER:
        for p in (0.1, 0.9):
            for rep in range(10):
                gid = f"{model}|{p}|{rep}"
                keep = float(rep < (8 if p == 0.1 else 2))
                for _ in range(3):
                    answers.append(dict(model=model, p=p, gid=gid, keep=keep))
                games.append(dict(model=model, p=p, gid=gid, p1_total=20 * (1 - keep)))
    return pd.DataFrame(answers), pd.DataFrame(games).set_index("gid")


def test_shifts_invariant_to_input_order(paired_cells):
    answers, games = paired_cells
    expected = pr.shifts(answers, games)
    shuffled = pr.shifts(answers.sample(frac=1, random_state=9),
                         games.sample(frac=1, random_state=13))
    pd.testing.assert_frame_equal(expected, shuffled)


def test_shifts_resample_answer_and_action_from_same_game(paired_cells):
    answers, games = paired_cells
    result = pr.shifts(answers, games.sample(frac=1, random_state=13))
    for a, b in (("dx", "dy"), ("x_lo", "y_lo"), ("x_hi", "y_hi")):
        assert result[b].to_numpy() == pytest.approx(20 * result[a].to_numpy())


def test_shifts_reject_unmatched_games(paired_cells):
    answers, games = paired_cells
    games = games.rename(index={games.index[0]: "unmatched"})
    with pytest.raises(RuntimeError, match="must match by game"):
        pr.shifts(answers, games)


def test_shifts_reject_duplicate_games(paired_cells):
    answers, games = paired_cells
    games = pd.concat([games, games.iloc[:1]])
    with pytest.raises(RuntimeError, match="must match by game"):
        pr.shifts(answers, games)
