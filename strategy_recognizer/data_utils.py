"""Shared loading / featurisation for the CRSD strategy recogniser."""

from __future__ import annotations

import glob

import numpy as np

from codebook import TOKEN_TO_ID, TOKENS
from strategies import CORE_LABELS

VOCAB_SIZE = len(TOKENS)
SEQ_LEN = 10

# ---- label spaces -------------------------------------------------------
FINE_LABELS = list(CORE_LABELS)  # R1..R6, AD
COARSE_OF = {"R1": "Lenient", "R2": "Lenient",
             "R3": "Moderate", "R4": "Moderate",
             "R5": "Strict", "R6": "Strict", "AD": "AD"}
COARSE_LABELS = ["Lenient", "Moderate", "Strict", "AD"]

LABEL_SETS = {
    "fine": (FINE_LABELS, lambda s: s),
    "coarse": (COARSE_LABELS, lambda s: COARSE_OF[s]),
}


def read_token_file(path):
    """Yield (label, [tokens]) for each line of a synthetic dataset file."""
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            head, rest = line.split(":", 1)
            yield head.strip(), rest.split()


def load_files(patterns):
    """Load one or many token files (globs allowed) -> (ids [N,SEQ_LEN], labels)."""
    if isinstance(patterns, str):
        patterns = [patterns]
    paths = []
    for pat in patterns:
        paths.extend(sorted(glob.glob(pat)))
    ids, labels = [], []
    for path in paths:
        for lab, toks in read_token_file(path):
            ids.append(seq_to_ids(toks))
            labels.append(lab)
    return np.array(ids, dtype=np.int64), np.array(labels), paths


def seq_to_ids(toks):
    row = [TOKEN_TO_ID.get(t, 0) for t in toks][:SEQ_LEN]
    row += [0] * (SEQ_LEN - len(row))
    return row


def ids_to_onehot(ids):
    """[N, SEQ_LEN] int ids -> [N, SEQ_LEN*VOCAB_SIZE] float one-hot."""
    n = ids.shape[0]
    oh = np.zeros((n, SEQ_LEN, VOCAB_SIZE), dtype=np.float32)
    rows = np.arange(n)[:, None]
    oh[rows, np.arange(SEQ_LEN)[None, :], ids] = 1.0
    return oh.reshape(n, SEQ_LEN * VOCAB_SIZE)


def encode_labels(labels, label_list):
    idx = {lab: i for i, lab in enumerate(label_list)}
    return np.array([idx[l] for l in labels], dtype=np.int64)


def map_to_coarse(labels):
    return np.array([COARSE_OF[l] for l in labels])
