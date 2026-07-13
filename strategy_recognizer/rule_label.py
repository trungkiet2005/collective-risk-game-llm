"""Deterministic rule-based labeller for CRSD traces (baseline + sanity check).

Given a token sequence, score every candidate strategy by how well the observed
own-actions match what that strategy would have done given the observed
previous-round contributor counts, and return the best match. On noiseless data
this recovers the generating strategy essentially perfectly.
"""

from __future__ import annotations

from codebook import parse_token
from strategies import CORE_LABELS, threshold_of


def _predict_contribute(label, ctx):
    """Would this strategy contribute, given context ctx ('E' or k_prev)?"""
    if label == "AD":
        return False
    if ctx == "E":  # round 1: reciprocators contribute
        return True
    M = threshold_of(label)
    return ctx >= M


def score_label(seq_tokens, label):
    hits = 0
    for tok in seq_tokens:
        ctx, amt = parse_token(tok)
        contributed = amt > 0
        if _predict_contribute(label, ctx) == contributed:
            hits += 1
    return hits / len(seq_tokens)


def label_sequence(seq_tokens, labels=CORE_LABELS):
    scored = [(lab, score_label(seq_tokens, lab)) for lab in labels]
    best = max(scored, key=lambda x: x[1])
    return best[0], best[1]


def _read_dataset(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            head, rest = line.split(":", 1)
            rows.append((head.strip(), rest.split()))
    return rows


if __name__ == "__main__":
    import argparse
    from collections import Counter

    p = argparse.ArgumentParser()
    p.add_argument("path")
    args = p.parse_args()

    rows = _read_dataset(args.path)
    correct = 0
    confusion = Counter()
    for true_label, toks in rows:
        pred, conf = label_sequence(toks)
        correct += (pred == true_label)
        confusion[(true_label, pred)] += 1
    print(f"{args.path}: rule-label accuracy = {correct}/{len(rows)} "
          f"= {correct / len(rows):.3f}")
    for (t, pr), n in sorted(confusion.items()):
        if t != pr:
            print(f"  {t} -> {pr}: {n}")
