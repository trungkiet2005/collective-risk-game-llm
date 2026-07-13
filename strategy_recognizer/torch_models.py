"""Small PyTorch sequence classifiers (LSTM / GRU / 1D-CNN) for token traces."""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from data_utils import VOCAB_SIZE

torch.manual_seed(0)


class SeqRNN(nn.Module):
    def __init__(self, n_classes, kind="lstm", emb=16, hidden=32):
        super().__init__()
        self.emb = nn.Embedding(VOCAB_SIZE, emb)
        rnn = nn.LSTM if kind == "lstm" else nn.GRU
        self.rnn = rnn(emb, hidden, batch_first=True)
        self.fc = nn.Linear(hidden, n_classes)

    def forward(self, x):
        h = self.emb(x)
        out, _ = self.rnn(h)
        return self.fc(out[:, -1, :])


class SeqCNN(nn.Module):
    def __init__(self, n_classes, emb=16, ch=32, k=3):
        super().__init__()
        self.emb = nn.Embedding(VOCAB_SIZE, emb)
        self.conv = nn.Conv1d(emb, ch, k, padding=k // 2)
        self.fc = nn.Linear(ch, n_classes)

    def forward(self, x):
        h = self.emb(x).transpose(1, 2)      # [B, emb, T]
        h = torch.relu(self.conv(h))
        h = torch.max(h, dim=2).values       # global max pool
        return self.fc(h)


def build(kind, n_classes):
    if kind in ("lstm", "gru"):
        return SeqRNN(n_classes, kind=kind)
    if kind == "cnn":
        return SeqCNN(n_classes)
    raise ValueError(kind)


def train_torch(kind, Xtr, ytr, n_classes, epochs=18, bs=256, lr=1e-3):
    model = build(kind, n_classes)
    ds = TensorDataset(torch.from_numpy(Xtr), torch.from_numpy(ytr))
    dl = DataLoader(ds, batch_size=bs, shuffle=True)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    lossf = nn.CrossEntropyLoss()
    model.train()
    for _ in range(epochs):
        for xb, yb in dl:
            opt.zero_grad()
            loss = lossf(model(xb), yb)
            loss.backward()
            opt.step()
    return model


@torch.no_grad()
def predict_torch(model, X):
    model.eval()
    logits = model(torch.from_numpy(X))
    prob = torch.softmax(logits, dim=1).numpy()
    return prob.argmax(1), prob.max(1)
