"""Shared loaders for the revision analyses.

One rule: read the per-model raw files, never `results/frontier/crsd_all_models.csv`.
That merged file is stale — it predates the top-tier sweep and still contains only
gemini-3.1-flash-lite, so anything joined against it silently drops the two models the
paper's central result rests on. `paper/make_figures_toptier.py` globs the per-model
directories for the same reason; we match it exactly.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pandas as pd

# The manuscript is archived under plan/legacy, while the data remain at the
# repository root. Keep this path derived from the file location so the
# analysis remains runnable after the archive move.
ROOT = Path(__file__).resolve().parents[4]
# The archived manuscript and the current AAMAS study use different layouts.
# Make the source explicit so an analyst cannot accidentally mix them.
RESULTS = Path(os.environ.get("CRG_IF_RESULTS", str(ROOT / "Legacy_Results" / "results")))
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

# display label -> raw model directory / csv name
FRONTIER_LABELS = {
    "google-gemini-3.1-pro-preview": ("Gemini-3.1-Pro", "Google", "top"),
    "openai-gpt-5.6-sol": ("GPT-5.6-sol", "OpenAI", "top"),
    "anthropic-claude-opus-5-default": ("Claude-Opus-5", "Anthropic", "top"),
    "xai-grok-4.20-0309-reasoning": ("Grok-4.20 (reasoning)", "xAI", "top"),
    "xai-grok-4.20-0309-non-reasoning": ("Grok-4.20 (no reasoning)", "xAI", "top"),
    "google-gemini-3.1-flash-lite-preview": ("Gemini-3.1-Flash-Lite", "Google", "cheap"),
    "openai-gpt-5.4-nano": ("GPT-5.4-nano", "OpenAI", "cheap"),
    # the nano runs predate the frontier task and write their own model string
    "OpenAIGPT5Nano": ("GPT-5.4-nano", "OpenAI", "cheap"),
}

OPEN_LABELS = {
    "qwen25-7b-instruct": ("Qwen2.5-7B", 7),
    "llama-3-1-8b": ("Llama-3.1-8B", 8),
    "gemma2-9b-it": ("Gemma-2-9B", 9),
    "gemma2-27b-it": ("Gemma-2-27B", 27),
    "qwen25-32b-instruct": ("Qwen2.5-32B", 32),
    "llama-3-1-70b-instruct-awq": ("Llama-3.1-70B", 70),
    "qwen25-72b-instruct-awq": ("Qwen2.5-72B", 72),
    "llama-3-3-70b-instruct-awq": ("Llama-3.3-70B", 70),
}


#: The risk grid every configuration in the panel shares, in both languages.
#: The four top-tier commercial configurations were additionally run at p=0.3 and
#: p=0.7 in ENGLISH ONLY (reviewer Q8, analysed by r7). Those cells exist for 4 of
#: 14 configurations and on one side of the language factor, so pooling over them
#: makes any cross-panel mean incomparable and silently moves numbers the
#: manuscript already quotes. Loaders therefore drop them by default; pass
#: all_risks=True to get them back, which only r7 should need.
CORE_RISKS = (0.1, 0.5, 0.9)


def _core(df: pd.DataFrame, all_risks: bool) -> pd.DataFrame:
    if all_risks or "risk_probability" not in df.columns:
        return df
    return df[df["risk_probability"].isin(CORE_RISKS)].copy()


def frontier_games(experiment: str = "exp_baseline",
                   all_risks: bool = False) -> pd.DataFrame:
    paths = sorted((RESULTS / "frontier").glob(f"*/{experiment}/games.csv"))
    df = pd.concat([pd.read_csv(p) for p in paths], ignore_index=True)
    df["arm"] = "commercial"
    df["experiment"] = experiment
    return _core(df, all_risks)


def open_games(experiment: str = "exp_baseline") -> pd.DataFrame:
    df = pd.read_csv(RESULTS / "open_source" / "crsd_all_models.csv")
    df = df[df.experiment == experiment].copy()
    df["arm"] = "open_source"
    return df


def baseline_all() -> pd.DataFrame:
    keep = ["arm", "experiment", "model", "language", "risk_probability", "group_total",
            "target_reached", "catastrophe", "mean_payoff", "rep"]
    o, f = open_games(), frontier_games()
    return pd.concat([o[keep], f[keep]], ignore_index=True)


def label(model: str) -> str:
    if model in FRONTIER_LABELS:
        return FRONTIER_LABELS[model][0]
    if model in OPEN_LABELS:
        return OPEN_LABELS[model][0]
    return model


def turns(model_dir: Path) -> pd.DataFrame:
    """Read a turns.jsonl into a frame of the fields the revision analyses need."""
    rows = []
    with open(model_dir, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            d = json.loads(line)
            rows.append({
                "game_id": d.get("game_id"),
                "round": d.get("round"),
                "player": d.get("player"),
                "contribution": d.get("contribution"),
                "parse_failed": d.get("parse_failed"),
                "risk_probability": d.get("risk_probability"),
                "language": d.get("language"),
                "persona_set": d.get("persona_set"),
                "disposition": d.get("disposition"),
            })
    return pd.DataFrame(rows)


def all_turns(experiment: str = "exp_baseline",
              all_risks: bool = False) -> pd.DataFrame:
    """Every turn of `experiment`, both arms, with a model column.

    Filtered to CORE_RISKS by default; see the note on that constant."""
    frames = []
    for p in sorted((RESULTS / "frontier").glob(f"*/{experiment}/turns.jsonl")):
        t = turns(p)
        t["model"] = p.parts[-3]
        t["arm"] = "commercial"
        frames.append(t)
    for p in sorted((RESULTS / "open_source" / "archive").glob(f"{experiment}/*/turns.jsonl")):
        t = turns(p)
        t["model"] = p.parts[-2]
        t["arm"] = "open_source"
        frames.append(t)
    for p in sorted((RESULTS / "open_source" / "exp_test").glob(f"{experiment}/*/turns.jsonl")):
        t = turns(p)
        t["model"] = p.parts[-2]
        t["arm"] = "open_source"
        frames.append(t)
    if not frames:
        raise FileNotFoundError(f"no turns.jsonl found for {experiment}")
    return _core(pd.concat(frames, ignore_index=True), all_risks)


# --------------------------------------------------------------------------- #
# Revision-round experiments: exp_nohint (Q1) and exp_evprobe (Q3)
# --------------------------------------------------------------------------- #
# Everything above hard-codes a directory layout, because the frontier sweep and
# the open-weight archive each have exactly one. The two revision runs do not:
# they come back as a Kaggle zip that is unpacked by hand, so the same
# experiment can arrive as
#
#   results/raw/crsd_results/<model>/<experiment>/games.csv     (zip layout)
#   results/open_source/archive/<experiment>/<model>/games.csv  (open-weight archive)
#   results/frontier/<model>/<experiment>/games.csv             (frontier sweep)
#
# and a loader that commits to one of them silently reports "no data" for a run
# that is sitting on disk. The functions below search for the file by name and
# work out which neighbouring directory is the model from the `exp_` prefix that
# every experiment config carries, so all three layouts load.
#
# Under results/frontier/ ONLY <model>/<experiment>/<file> is the panel. The
# globs above encode that depth literally ("*/{experiment}/games.csv"), so
# anything nested one level deeper is invisible to r1-r7; a recursive search has
# to reimpose the same rule or it quietly analyses a different study. Two such
# subtrees exist today -- frontier/archive/ (a superseded haiku run) and
# frontier/dense_grid/ (the eleven-point risk sweep of the five-model panel,
# which also names its experiment `exp_baseline`) -- and pooling either into the
# fourteen-configuration panel moves numbers the manuscript quotes. The depth
# rule covers both without naming them, so a third side study is excluded the
# day it lands rather than the day someone notices a mean has drifted.


def rel_to_root(path: Path) -> str:
    """Repo-relative path for reporting; falls back to the absolute path when the
    results tree is not under the repository (a test fixture, an external disk)."""
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return Path(path).as_posix()


def _model_and_experiment(path: Path) -> tuple[str, str]:
    """(model, experiment) for a result file, from either directory layout."""
    parent, grand = path.parent.name, path.parent.parent.name
    if parent.startswith("exp_"):
        return grand, parent
    if grand.startswith("exp_"):
        return parent, grand
    return grand, parent            # last resort: assume <model>/<experiment>/


def discover_files(filename: str, experiment: str | None = None) -> list[tuple[Path, str, str]]:
    """Every `filename` under results/, as (path, model, experiment) triples."""
    hits = []
    if not RESULTS.exists():
        return hits
    for p in sorted(RESULTS.rglob(filename)):
        rel = p.relative_to(RESULTS).parts
        if rel[0] == "frontier" and len(rel) != 3 + 1:   # <model>/<exp>/<file>
            continue
        model, exp = _model_and_experiment(p)
        if experiment is not None and exp != experiment:
            continue
        hits.append((p, model, exp))
    return hits


def discover_games(experiment: str, all_risks: bool = False) -> pd.DataFrame:
    """games.csv rows of `experiment` from wherever they landed.

    Returns an empty frame (not an error) when the run has not been downloaded
    yet, so the analyses can report "awaiting data" instead of crashing.
    """
    frames = []
    for path, model, exp in discover_files("games.csv", experiment):
        try:
            df = pd.read_csv(path)
        except Exception:                                    # noqa: BLE001
            continue
        if df.empty:
            continue
        if "model" not in df.columns:
            df["model"] = model
        df["experiment"] = exp
        df["arm"] = "commercial" if path.relative_to(RESULTS).parts[0] == "frontier" \
            else "open_source"
        df["source"] = rel_to_root(path)
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    if "game_id" in out.columns:
        out = out.drop_duplicates(subset=["model", "game_id"], keep="first")
    return _core(out, all_risks).reset_index(drop=True)


def discover_turns(experiment: str, all_risks: bool = False) -> pd.DataFrame:
    """turns.jsonl rows of `experiment` from wherever they landed."""
    frames = []
    for path, model, exp in discover_files("turns.jsonl", experiment):
        t = turns(path)
        if t.empty:
            continue
        t["model"] = model
        t["experiment"] = exp
        t["arm"] = "commercial" if path.relative_to(RESULTS).parts[0] == "frontier" \
            else "open_source"
        frames.append(t)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    if "game_id" in out.columns:
        out = out.drop_duplicates(subset=["model", "game_id", "round", "player"],
                                  keep="first")
    return _core(out, all_risks).reset_index(drop=True)


_COMP_FIELDS = ("game_id", "round", "player", "player_index", "question_id",
                "category", "question_text", "raw_response", "parsed_answer",
                "ground_truth", "correct", "parse_failed", "answer_kind",
                "answerable_from_prompt", "language", "risk_probability",
                "model", "show_cumulative")


#: Cheap enough to run over the whole battery: a full comprehension run is ~380k
#: lines per model set, and json.loads on all of them costs minutes, while a regex
#: over the raw line costs seconds.
_CATEGORY_RE = re.compile(r'"category"\s*:\s*"([^"]+)"')


def comprehension_categories(experiment: str | None = None) -> list[dict]:
    """Which probe axes each comprehension.jsonl holds, and how many of each.

    Used to spot a new question category (the revision adds `value`) without
    paying to parse every record.
    """
    out = []
    for path, model, exp in discover_files("comprehension.jsonl", experiment):
        counts: dict[str, int] = {}
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                m = _CATEGORY_RE.search(line)
                if m is None:
                    continue
                counts[m.group(1)] = counts.get(m.group(1), 0) + 1
        out.append({"path": rel_to_root(path), "model": model, "experiment": exp,
                    "categories": counts})
    return out


def discover_comprehension(experiment: str | None = None,
                           categories=None,
                           all_risks: bool = False) -> pd.DataFrame:
    """comprehension.jsonl rows, from every experiment or just one.

    The record already carries its own model/language/risk, so nothing here has
    to be inferred except the experiment name (used to keep the probe axes of
    different runs apart).

    `categories` restricts the axes read. Pass it: the Time and State axes are
    ~95% of a full battery and parsing them costs minutes, so an analysis that
    only wants `value` (or `rules`) should say so.
    """
    want = set(categories) if categories else None
    rows = []
    for path, model, exp in discover_files("comprehension.jsonl", experiment):
        source = rel_to_root(path)
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                if want is not None:
                    m = _CATEGORY_RE.search(line)
                    if m is not None and m.group(1) not in want:
                        continue
                d = json.loads(line)
                if want is not None and d.get("category") not in want:
                    continue
                rec = {k: d.get(k) for k in _COMP_FIELDS}
                rec["model"] = rec["model"] or model
                rec["experiment"] = exp
                rec["source"] = source
                rows.append(rec)
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    return _core(out, all_risks).reset_index(drop=True)
