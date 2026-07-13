"""Apply a trained recogniser to the encoded LLM traces and report the inferred
strategy distribution by model / language / experiment.

Uses the LSTM (fine granularity) by default; falls back to the rule labeller if
no trained model is found.
"""

from __future__ import annotations

import argparse
import os
import pickle

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from data_utils import (COARSE_OF, FINE_LABELS, SEQ_LEN, ids_to_onehot,
                        seq_to_ids)

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(HERE, "saved_models")
OUT = os.path.join(HERE, "results")


def load_lstm(gran, n_classes):
    import torch
    from torch_models import build
    path = os.path.join(MODELS, f"lstm_{gran}.pt")
    if not os.path.exists(path):
        return None
    model = build("lstm", n_classes)
    model.load_state_dict(torch.load(path))
    model.eval()
    return model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces", default="Dataset/llm_traces_encoded.csv")
    ap.add_argument("--out", default=os.path.join(OUT, "llm_strategy_predictions.csv"))
    args = ap.parse_args()

    df = pd.read_csv(args.traces)
    ids = np.array([seq_to_ids(s.split()) for s in df["state_action"]],
                   dtype=np.int64)

    model = load_lstm("fine", len(FINE_LABELS))
    if model is not None:
        from torch_models import predict_torch
        pred_idx, conf = predict_torch(model, ids)
        df["strategy"] = [FINE_LABELS[i] for i in pred_idx]
        df["confidence"] = np.round(conf, 4)
        engine = "lstm_fine"
    else:
        from rule_label import label_sequence
        labs, confs = zip(*[label_sequence(s.split()) for s in df["state_action"]])
        df["strategy"], df["confidence"] = list(labs), np.round(confs, 4)
        engine = "rule"

    df["strategy_coarse"] = df["strategy"].map(COARSE_OF)
    os.makedirs(OUT, exist_ok=True)
    df.to_csv(args.out, index=False, encoding="utf-8")
    print(f"engine={engine} | wrote {args.out}: {len(df)} predictions")

    print("\n=== strategy distribution (overall) ===")
    print(df["strategy"].value_counts(normalize=True).round(3).to_string())
    print("\n=== by model (share %) ===")
    print((pd.crosstab(df["llm_model"], df["strategy"], normalize="index")
           .round(3) * 100).to_string())
    print("\n=== by language (share %) ===")
    print((pd.crosstab(df["language"], df["strategy"], normalize="index")
           .round(3) * 100).to_string())

    # stacked bar by model
    ct = pd.crosstab(df["llm_model"], df["strategy"], normalize="index")
    ct = ct.reindex(columns=[c for c in FINE_LABELS if c in ct.columns])
    ax = ct.plot(kind="bar", stacked=True, figsize=(8, 4.5), colormap="viridis")
    ax.set_ylabel("strategy share")
    ax.set_title(f"Inferred CRSD strategy share by model ({engine})")
    ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8)
    plt.tight_layout()
    fig_path = os.path.join(OUT, "llm_strategy_by_model.png")
    plt.savefig(fig_path, dpi=130)
    print(f"\nsaved figure: {fig_path}")


if __name__ == "__main__":
    main()
