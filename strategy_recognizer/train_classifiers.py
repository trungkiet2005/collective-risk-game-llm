"""Train + evaluate the CRSD strategy recognisers.

Train on the exogenous (context-covering) synthetic data; evaluate on a held-out
exogenous split AND on the endogenous (realistic group-dynamics) data. Two label
granularities: fine (R1..R6, AD) and coarse (Lenient/Moderate/Strict, AD).

Models: rule baseline, LogisticRegression, RandomForest, LSTM, GRU, 1D-CNN.
Outputs: saved_models/, results/metrics.csv, results/confusion_*.png.
"""

from __future__ import annotations

import os
import pickle

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from data_utils import (LABEL_SETS, encode_labels, ids_to_onehot, load_files,
                        map_to_coarse)
from rule_label import label_sequence
from torch_models import predict_torch, train_torch
from codebook import TOKENS

HERE = os.path.dirname(os.path.abspath(__file__))
DS = os.path.join(HERE, "Dataset", "noise_dataset_crsd")
OUT = os.path.join(HERE, "results")
MODELS = os.path.join(HERE, "saved_models")
os.makedirs(OUT, exist_ok=True)
os.makedirs(MODELS, exist_ok=True)

TRAIN_GLOB = os.path.join(DS, "exogenous", "*", "*.txt")
EVAL_SETS = {
    "endo_nonoise": os.path.join(DS, "endogenous", "NoNoise", "*.txt"),
    "endo_noise005": os.path.join(DS, "endogenous", "Noise005", "*.txt"),
}


def rule_predict(ids_unused, raw_tokens, label_list, coarse):
    preds = []
    for toks in raw_tokens:
        lab, _ = label_sequence(toks)
        preds.append(map_to_coarse([lab])[0] if coarse else lab)
    idx = {l: i for i, l in enumerate(label_list)}
    return np.array([idx[p] for p in preds])


def tokens_from_ids(ids):
    return [[TOKENS[i] for i in row] for row in ids]


def plot_confusion(cm, labels, title, path):
    fig, ax = plt.subplots(figsize=(5, 4.2))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(labels)), labels, rotation=45, ha="right")
    ax.set_yticks(range(len(labels)), labels)
    thr = cm.max() / 2 if cm.max() else 0.5
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(j, i, cm[i, j], ha="center", va="center",
                    color="white" if cm[i, j] > thr else "black", fontsize=8)
    ax.set_xlabel("predicted")
    ax.set_ylabel("true")
    ax.set_title(title, fontsize=9)
    fig.colorbar(im, fraction=0.046)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main():
    print("loading training data (exogenous) ...")
    Xtr_ids, ytr_str, tr_paths = load_files(TRAIN_GLOB)
    print(f"  train: {Xtr_ids.shape[0]} sequences from {len(tr_paths)} files")

    evals = {}
    for name, pat in EVAL_SETS.items():
        Xe, ye, _ = load_files(pat)
        evals[name] = (Xe, ye)
        print(f"  eval[{name}]: {Xe.shape[0]} sequences")

    rows = []
    for gran, (label_list, mapper) in LABEL_SETS.items():
        print(f"\n=== granularity: {gran}  ({label_list}) ===")
        ytr = encode_labels(np.array([mapper(s) for s in ytr_str]), label_list)

        # internal held-out split of exogenous for a clean-data ceiling
        Xtr, Xval, ytr_s, yval = train_test_split(
            Xtr_ids, ytr, test_size=0.15, random_state=1, stratify=ytr)
        Xtr_oh, Xval_oh = ids_to_onehot(Xtr), ids_to_onehot(Xval)

        eval_prepared = {"exo_val": (Xval, yval)}
        for name, (Xe, ye_str) in evals.items():
            ye = encode_labels(np.array([mapper(s) for s in ye_str]), label_list)
            eval_prepared[name] = (Xe, ye)

        # ---- fit models ----
        fitted = {}
        print(" logreg ..."); fitted["logreg"] = LogisticRegression(
            max_iter=2000).fit(Xtr_oh, ytr_s)
        print(" rf ...");     fitted["rf"] = RandomForestClassifier(
            n_estimators=150, n_jobs=-1, random_state=0).fit(Xtr_oh, ytr_s)
        for kind in ("lstm", "gru", "cnn"):
            print(f" {kind} ...")
            fitted[kind] = train_torch(kind, Xtr, ytr_s, len(label_list))

        # ---- evaluate every model on every eval set ----
        for ename, (Xe, ye) in eval_prepared.items():
            Xe_oh = ids_to_onehot(Xe)
            raw = tokens_from_ids(Xe)
            preds = {
                "rule": rule_predict(Xe, raw, label_list, gran == "coarse"),
                "logreg": fitted["logreg"].predict(Xe_oh),
                "rf": fitted["rf"].predict(Xe_oh),
                "lstm": predict_torch(fitted["lstm"], Xe)[0],
                "gru": predict_torch(fitted["gru"], Xe)[0],
                "cnn": predict_torch(fitted["cnn"], Xe)[0],
            }
            for mname, yp in preds.items():
                acc = accuracy_score(ye, yp)
                f1 = f1_score(ye, yp, average="macro")
                rows.append(dict(granularity=gran, eval_set=ename,
                                 model=mname, accuracy=round(acc, 4),
                                 macro_f1=round(f1, 4)))
                if ename == "endo_noise005":  # save confusion for realistic set
                    cm = confusion_matrix(ye, yp, labels=range(len(label_list)))
                    plot_confusion(
                        cm, label_list,
                        f"{mname} | {gran} | {ename}\nacc={acc:.2f} f1={f1:.2f}",
                        os.path.join(OUT, f"confusion_{gran}_{mname}.png"))

        # persist the strongest neural model + sklearn models per granularity
        import torch
        torch.save(fitted["lstm"].state_dict(),
                   os.path.join(MODELS, f"lstm_{gran}.pt"))
        for m in ("logreg", "rf"):
            with open(os.path.join(MODELS, f"{m}_{gran}.pkl"), "wb") as f:
                pickle.dump(fitted[m], f)

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "metrics.csv"), index=False)
    print("\n===== METRICS =====")
    print(df.to_string(index=False))
    print(f"\nsaved: {OUT}/metrics.csv, confusion_*.png, {MODELS}/*")


if __name__ == "__main__":
    main()
