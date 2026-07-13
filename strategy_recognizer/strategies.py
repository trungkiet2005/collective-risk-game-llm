"""Aspiration-level reciprocator strategies for the CRSD (Van Segbroeck 2012).

An ``R_M`` player contributes in round 1, and from round 2 on contributes only
if at least ``M`` of the ``N`` players contributed in the previous round. ``AD``
never contributes. Contributions use the discrete levels ``{0, 2, 4}``: when a
reciprocator is triggered it contributes its per-agent ``coop_level`` (2 or 4).
"""

from __future__ import annotations

import random

from codebook import CONTRIB_LEVELS, contributor_count

# 7-class label space for N = 6, in a fixed order.
R_LABELS = ["R1", "R2", "R3", "R4", "R5", "R6"]
CORE_LABELS = R_LABELS + ["AD"]
# Optional baselines / distractors.
EXTRA_LABELS = ["AC", "RND"]


def threshold_of(label: str):
    """Return M for an ``R_M`` label, else None."""
    return int(label[1:]) if label.startswith("R") and label[1:].isdigit() else None


def decide(label, coop_level, round_idx, prev_group, rng):
    """Contribution this round for a player of the given strategy.

    prev_group : list of all N contributions in the previous round (or None in
                 round 1). round_idx is 0-based.
    """
    if label == "AD":
        return 0
    if label == "AC":
        return coop_level
    if label == "RND":
        return rng.choice(CONTRIB_LEVELS)

    M = threshold_of(label)
    if M is None:
        raise ValueError(f"Unknown strategy: {label}")
    if round_idx == 0:
        return coop_level  # reciprocators always contribute in round 1
    return coop_level if contributor_count(prev_group) >= M else 0
