"""Shared data layer for every number, table and figure in the AAMAS paper.

Run any analysis script from the repository root, e.g.
    python paper/AAMAS/analysis/fig_riskgrid.py

Reads results/ read-only. Never reads Legacy_Results/. Never writes into results/.

Three tables are built from the wide CSVs:
  games : one row per game (all experiments)
  units : one row per (game, LLM model present in that game); self-play averages the
          six seats, scripted-opponent games use seat 1, mixed tables average the seats
          the model holds (seat truth from agent{i}_llm, never from the folder name)
  seats : one row per LLM seat, with its ten-round trajectory

PAYOFFS. All welfare numbers in the paper use the EXPECTED payoff over the catastrophe
lottery, given the contributions:
    40 - x_i              if the group reached the target
    (1 - p) * (40 - x_i)  if it missed
The realised payoff is kept as `real_pay` for reference only. Reason: the engine keys the
lottery on the repetition index, so the whole corpus holds ten uniform draws, reused at
every p, model and experiment, and all ten fall below 0.47. Every missed game at
p >= 0.5 therefore ended in catastrophe, which biases realised welfare against models
that miss. Behaviour is unaffected because the draw is never shown to the agents.
"""
from __future__ import annotations

import ast
import pathlib
import random
import re
from typing import Dict, Iterable, List, Sequence

import numpy as np
import pandas as pd

REPO = pathlib.Path(__file__).resolve().parents[3]
RESULTS = REPO / "results"
PAPER = REPO / "paper" / "AAMAS"
TABLES = PAPER / "tables"
FIGURES = PAPER / "figures"

N_PLAYERS = 6
N_ROUNDS = 10
ENDOWMENT = 40.0
TARGET = 120.0
FAIR_SHARE = TARGET / (N_PLAYERS * N_ROUNDS)   # 2 per seat per round
FAIR_TOTAL = TARGET / N_PLAYERS                # 20 per seat per game
PSTAR = FAIR_TOTAL / ENDOWMENT                 # 0.5
BASE_SEED = 12345                              # engine seed = BASE_SEED + rep

SEED = 20260916
N_BOOT = 5000
N_PERM = 5000

# One naming system for the whole paper. Order is the paper's model order.
SLUG = {
    "anthropic-claude-haiku-4-5-20251001": "Haiku",
    "google-gemini-3.5-flash-lite": "Flash-Lite",
    "openai-gpt-5.6-luna": "Luna",
    "qwen-qwen3-235b-a22b-instruct-2507": "Qwen",
    "xai-grok-4.20-0309-non-reasoning": "Grok",
}
MODELS = ["Haiku", "Flash-Lite", "Luna", "Qwen", "Grok"]
# Reader-facing names. The internal keys above stay short for code, but every figure,
# table and name-valued macro prints the model with its family: a bare "Luna" hides
# that it is a GPT model, and one model per provider is how the panel was chosen.
DISPLAY = {"Haiku": "Claude Haiku", "Flash-Lite": "Gemini Flash-Lite", "Luna": "GPT Luna",
           "Qwen": "Qwen", "Grok": "Grok"}


def show(name: str, wrap: bool = False) -> str:
    """Display name for a model key; wrap=True breaks after the family (narrow axes)."""
    text = DISPLAY.get(name, name)
    return text.replace(" ", "\n", 1) if wrap else text


# Macro-safe names (letters only).
MACRO = {"Haiku": "Haiku", "Flash-Lite": "Flash", "Luna": "Luna", "Qwen": "Qwen", "Grok": "Grok"}

EXPERIMENTS = [
    "exp_baseline", "exp_nohint", "exp_evprobe",
    "exp_bestresponse_defect", "exp_bestresponse_coop",
    "exp_bestresponse_carry", "exp_bestresponse_cond",
    "exp_mixed", "exp_para1", "exp_para2", "exp_baseline_temp0", "exp_neutral", "exp_wording",
]
CONTEXT = {
    "exp_baseline": "selfplay",
    "exp_nohint": "nohint",
    "exp_evprobe": "probe",
    "exp_bestresponse_defect": "all0",
    "exp_bestresponse_coop": "all2",
    "exp_bestresponse_carry": "all4",
    "exp_bestresponse_cond": "cond",
    "exp_mixed": "mixed",
    "exp_para1": "para1",
    "exp_para2": "para2",
    "exp_baseline_temp0": "temp0",
    "exp_neutral": "neutral",
    "exp_wording": "wording",
}
SELFPLAY_ARMS = ["exp_baseline", "exp_evprobe", "exp_nohint", "exp_para1", "exp_para2", "exp_neutral", "exp_wording",
                 "exp_baseline_temp0"]
SCRIPTED = {"all0": "exp_bestresponse_defect", "all2": "exp_bestresponse_coop",
            "all4": "exp_bestresponse_carry", "cond": "exp_bestresponse_cond"}


def lottery_draws() -> List[float]:
    """The ten uniform draws the engine uses, one per repetition."""
    return [random.Random(BASE_SEED + rep).random() for rep in range(10)]


def opt_payoff(p):
    """Per-seat payoff of the welfare-optimal outcome (Proposition 1)."""
    return np.maximum((1.0 - np.asarray(p, float)) * ENDOWMENT, FAIR_TOTAL)


def expected_payoff(own_total, reached, p):
    own_total = np.asarray(own_total, float)
    factor = np.where(np.asarray(reached).astype(bool), 1.0, 1.0 - np.asarray(p, float))
    return factor * (ENDOWMENT - own_total)


def _parse(value):
    return ast.literal_eval(value) if isinstance(value, str) else value


def _read_experiment(exp: str) -> pd.DataFrame:
    files = sorted((RESULTS / exp).glob("*/*/*.csv"))
    if not files:
        raise FileNotFoundError(f"no CSV files under results/{exp}")
    frames = []
    for path in files:
        frame = pd.read_csv(path)
        frame["folder_model"] = path.parent.name
        frame["folder_p"] = float(path.parent.parent.name)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


_CACHE: Dict[str, tuple] = {}


def build(experiments: Sequence[str] = tuple(EXPERIMENTS)):
    """Return (games, units, seats) for the given experiments."""
    key = ",".join(experiments)
    if key in _CACHE:
        return _CACHE[key]
    games, units, seats = [], [], []
    for exp in experiments:
        raw = _read_experiment(exp)
        for row in raw.to_dict("records"):
            if row["experiment"] != exp:
                raise ValueError(f"experiment field {row['experiment']!r} in folder {exp}")
            p = float(row["risk_probability"])
            if abs(p - row["folder_p"]) > 1e-9:
                raise ValueError(f"risk mismatch in {exp}: {p} vs folder {row['folder_p']}")
            strat = np.array([_parse(row[f"agent{i}_strategies"]) for i in range(1, 7)], float)
            if strat.shape != (N_PLAYERS, N_ROUNDS):
                raise ValueError(f"bad strategy shape {strat.shape} in {exp}")
            llm = [row[f"agent{i}_llm"] for i in range(1, 7)]
            totals = strat.sum(axis=1)
            G = float(totals.sum())
            if abs(G - float(row["group_total"])) > 1e-9:
                raise ValueError(f"group total mismatch in {exp}")
            reached = int(row["target_reached"])
            if reached != int(G >= TARGET):
                raise ValueError(f"target flag mismatch in {exp}")
            exp_pay = expected_payoff(totals, reached, p)
            real_pay = np.array([float(row[f"agent{i}_payoff"]) for i in range(1, 7)])
            pot = np.cumsum(strat.sum(axis=0))
            gid = f"{exp}|{row['folder_model']}|{p:g}|{int(row['rep'])}"
            present = [m for m in MODELS if any(SLUG.get(s) == m for s in llm)]
            games.append(dict(
                gid=gid, exp=exp, ctx=CONTEXT[exp], p=p, rep=int(row["rep"]),
                folder_model=row["folder_model"], G=G, reached=reached,
                catastrophe=int(row["catastrophe"]), exp_welfare=float(exp_pay.mean()),
                real_welfare=float(real_pay.mean()), n_parse=int(row["n_parse_failures"]),
                models=tuple(present), strat=strat, llm=tuple(llm), pot=pot,
            ))
            for m in present:
                idx = [i for i in range(N_PLAYERS) if SLUG.get(llm[i]) == m]
                others = sorted({SLUG[s] for s in llm if s in SLUG and SLUG[s] != m})
                if exp == "exp_mixed":
                    partner = others[0]
                elif exp.startswith("exp_bestresponse"):
                    partner = CONTEXT[exp]
                else:
                    partner = "self"
                units.append(dict(
                    gid=gid, exp=exp, ctx=CONTEXT[exp], p=p, rep=int(row["rep"]),
                    model=m, partner=partner, k=len(idx),
                    own=float(totals[idx].mean()),
                    exp_pay=float(exp_pay[idx].mean()),
                    real_pay=float(real_pay[idx].mean()),
                    exact2=float(np.mean([np.all(strat[i] == 2) for i in idx])),
                    exact4=float(np.mean([np.all(strat[i] == 4) for i in idx])),
                    G=G, reached=reached,
                ))
                for i in idx:
                    seats.append(dict(
                        gid=gid, exp=exp, ctx=CONTEXT[exp], p=p, rep=int(row["rep"]),
                        model=m, partner=partner, k=len(idx), seat=i + 1,
                        traj=tuple(int(a) for a in strat[i]), own=float(totals[i]),
                        exp_pay=float(exp_pay[i]), G=G, reached=reached,
                    ))
    out = (pd.DataFrame(games), pd.DataFrame(units), pd.DataFrame(seats))
    _CACHE[key] = out
    return out


def load_probes() -> pd.DataFrame:
    probes = pd.read_csv(RESULTS / "exp_evprobe_probes.csv")
    probes["model"] = probes["model"].map(SLUG)
    if probes["model"].isna().any():
        raise ValueError("unknown model slug in probe file")
    return probes


# ------------------------------------------------------------------ statistics
def rng(offset: int = 0) -> np.random.Generator:
    return np.random.default_rng(SEED + offset)


def boot_ci(values: Iterable[float], n: int = N_BOOT, offset: int = 0, stat=np.mean):
    """Percentile bootstrap over games (each value is one game)."""
    a = np.asarray(list(values), float)
    if a.size == 0:
        raise ValueError("empty sample")
    g = rng(offset)
    draws = np.array([stat(a[g.integers(0, a.size, a.size)]) for _ in range(n)])
    return float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))


def perm_test(x: Iterable[float], y: Iterable[float], n: int = N_PERM, offset: int = 0) -> float:
    """Two-sided permutation test for a difference in means; games are exchangeable."""
    x = np.asarray(list(x), float)
    y = np.asarray(list(y), float)
    pooled = np.concatenate([x, y])
    observed = abs(x.mean() - y.mean())
    g = rng(offset)
    hits = 0
    for _ in range(n):
        g.shuffle(pooled)
        if abs(pooled[: x.size].mean() - pooled[x.size:].mean()) >= observed - 1e-12:
            hits += 1
    return (hits + 1) / (n + 1)


# ------------------------------------------------------------------ LaTeX macros
class Macros:
    """Collects \\newcommand definitions; names must be letters only."""

    def __init__(self, source: str):
        self.source = source
        self.items: Dict[str, str] = {}

    def add(self, name: str, value) -> None:
        if not re.fullmatch(r"[A-Za-z]+", name):
            raise ValueError(f"macro name {name!r} must be letters only")
        if name in self.items:
            raise ValueError(f"macro {name} defined twice")
        self.items[name] = str(value)

    def write(self, filename: str) -> pathlib.Path:
        TABLES.mkdir(parents=True, exist_ok=True)
        path = TABLES / filename
        lines = [f"% Generated by paper/AAMAS/analysis/{self.source}. Do not edit by hand."]
        lines += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in self.items.items()]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path


def fmt(x: float, digits: int = 1) -> str:
    s = f"{x:.{digits}f}"
    if s.startswith("-") and float(s) == 0:
        s = s[1:]
    return s.replace("-", "$-$") if s.startswith("-") else s


def pct(x: float) -> str:
    return f"{100 * x:.0f}"


WORDS = {0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
         7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}


def word(n: int, cap: bool = False) -> str:
    w = WORDS.get(int(n), str(n))
    return w.capitalize() if cap else w


if __name__ == "__main__":
    games, units, seats = build()
    print(games.groupby("exp").size())
    print(units.groupby(["exp", "model"]).size().unstack())
    print("lottery draws:", [round(u, 3) for u in lottery_draws()])
    print("parse failures:", games.groupby("exp").n_parse.sum().to_dict())
