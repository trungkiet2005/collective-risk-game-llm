"""R1/Q6 — decoding parameters + run-to-run stability of the hosted panel.

Reviewer Q6: "what were the provider-default decoding settings (temperature, top_p)
when available? Any observed instability across runs/days?"

Two things this script establishes, both from artefacts already on disk:

1. What we actually sent. The frontier task sets temperature explicitly (it is NOT a
   provider default) and passes a per-turn seed and an output cap. We read those from
   the task source itself rather than restating them, so the manuscript number cannot
   drift from the code.

2. Whether the same cell, executed twice, gives the same behaviour. The overnight
   Day-A/Day-B sweep re-executed several (model, risk, language, rep) cells on a
   different Kaggle account, at a different hour, and in some cases under a different
   output-token cap, because a Windows path-length bug lost the first download. Those
   accidental repeats are an unplanned but genuine run-to-run replication test.

Output: paper/revision/out/r1_decoding_stability.json + a printed summary.
"""
from __future__ import annotations

import csv
import glob
import json
import os
import re
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

TASK_SRC = ROOT / "kaggle" / "benchmarks" / "crg_task_server.py"
RUNS = ROOT / "plan" / "runs"


# --------------------------------------------------------------------------- #
# 1. what was sent to the proxy
# --------------------------------------------------------------------------- #
def read_declared_params() -> dict:
    src = TASK_SRC.read_text(encoding="utf-8")

    def grab(pattern, cast=str, default=None):
        m = re.search(pattern, src, re.M)
        return cast(m.group(1)) if m else default

    params = {
        "temperature": grab(r"^TEMPERATURE\s*=\s*([0-9.]+)", float),
        "max_out_reasoning_default": grab(r"(\d+) if any\(h in MODEL", int),
        "max_out_other_default": grab(r"else (\d+)\n\)", int),
        "base_seed": grab(r"^BASE_SEED\s*=\s*(\d+)", int),
        "max_parse_retries": grab(r"^MAX_PARSE_RETRIES\s*=\s*(\d+)", int),
    }
    m = re.search(r"_LLM\.prompt\((.*?)\)\n", src, re.S)
    params["call_site"] = " ".join(m.group(1).split()) if m else None
    params["sends_temperature"] = "temperature=TEMPERATURE" in src
    params["sends_seed"] = bool(re.search(r"_LLM\.prompt\([^)]*seed=seed", src, re.S))
    params["sends_top_p"] = "top_p" in src          # False -> provider default top_p
    return params


def observed_caps() -> dict:
    """max_completion_tokens actually used, per model, across all shard logs."""
    caps = defaultdict(set)
    for log in glob.glob(str(RUNS / "*.run.log")):
        for line in open(log, encoding="utf-8", errors="replace"):
            m = re.search(r"\[cfg\] model=(\S+).*?max_completion_tokens=(\d+)", line)
            if m:
                caps[m.group(1)].add(int(m.group(2)))
    return {k: sorted(v) for k, v in sorted(caps.items())}


# --------------------------------------------------------------------------- #
# 2. run-to-run replication
# --------------------------------------------------------------------------- #
SHARD_RE = re.compile(
    r"^(?P<batch>[A-Za-z0-9-]+)__(?:(?P<acct>[a-z0-9]+)__)?(?P<model>.+?)"
    r"__r(?P<risk>[0-9.]+)__l(?P<lang>[a-z]{2})(?:__s(?P<start>\d+))?$"
)


STAGING = Path(os.environ.get("CRG_STAGING", r"D:/tmp/crgdl"))


def shard_games() -> dict:
    """(shard_label) -> list of game dicts, from that shard's own download tree.

    Two download locations exist because the sweep changed mid-flight: early shards
    kept their download inside plan/runs/<label>/download, later ones were staged per
    Kaggle account under D:/tmp/crgdl/<account>. Both are read; the account directory
    is what makes the accidental repeats visible, since a re-run of the same cell was
    always issued from a *different* account.
    """
    out = {}
    for shard_dir in sorted(p for p in RUNS.iterdir() if p.is_dir()):
        rows = []
        for csv_path in glob.glob(str(shard_dir / "download" / "**" / "games.csv"),
                                  recursive=True):
            with open(csv_path, newline="", encoding="utf-8") as fh:
                rows.extend(list(csv.DictReader(fh)))
        if rows:
            out[shard_dir.name] = rows

    if STAGING.is_dir():
        for acct_dir in sorted(p for p in STAGING.iterdir() if p.is_dir()):
            rows = []
            for csv_path in glob.glob(str(acct_dir / "**" / "games.csv"), recursive=True):
                with open(csv_path, newline="", encoding="utf-8") as fh:
                    rows.extend(list(csv.DictReader(fh)))
            if rows:
                out[f"staging__{acct_dir.name}"] = rows
    return out


def replication(shards: dict) -> dict:
    """Find (model, risk, lang, rep) games produced by >1 independent shard."""
    seen = defaultdict(list)
    for label, rows in shards.items():
        m = SHARD_RE.match(label)
        acct = m.group("acct") if m else (
            label.split("__", 1)[1] if label.startswith("staging__") else None)
        for r in rows:
            key = (r["model"], float(r["risk_probability"]), r["language"], int(r["rep"]))
            seen[key].append({
                "shard": label,
                "account": acct,
                "group_total": float(r["group_total"]),
                "target_reached": int(float(r["target_reached"])),
            })

    repeats = {k: v for k, v in seen.items() if len({e["shard"] for e in v}) > 1}
    identical, differing, deltas = 0, 0, []
    detail = []
    for key, entries in sorted(repeats.items()):
        totals = [e["group_total"] for e in entries]
        same = len(set(totals)) == 1
        identical += same
        differing += (not same)
        deltas.append(max(totals) - min(totals))
        detail.append({
            "model": key[0], "risk": key[1], "language": key[2], "rep": key[3],
            "totals": totals,
            "accounts": [e["account"] for e in entries],
            "shards": [e["shard"] for e in entries],
            "reach": [e["target_reached"] for e in entries],
        })

    models = sorted({d["model"] for d in detail})
    return {
        "n_games_seen": len(seen),
        "n_games_replicated": len(repeats),
        "models_replicated": models,
        "n_identical": identical,
        "n_differing": differing,
        "max_abs_delta": max(deltas) if deltas else None,
        "mean_abs_delta": round(statistics.fmean(deltas), 3) if deltas else None,
        "detail": detail,
    }


def account_effect(shards: dict) -> dict:
    """Does *which execution* a game came from predict how the group played?

    Stronger than the six accidental repeats: every Claude-Opus-5 cell was assembled
    from two to four different Kaggle accounts, executed hours apart, and (for the
    refilled reps) under a different output-token cap. If hosted behaviour drifted
    between runs or days, account would carry variance within a cell. We test that
    with a one-way permutation ANOVA on account, within (model, risk, language),
    pooling the F statistic over cells that actually span >1 account.
    """
    import random

    by_cell = defaultdict(lambda: defaultdict(list))
    for label, rows in shards.items():
        m = SHARD_RE.match(label)
        acct = m.group("acct") if m else (
            label.split("__", 1)[1] if label.startswith("staging__") else label)
        for r in rows:
            key = (r["model"], float(r["risk_probability"]), r["language"])
            by_cell[key][acct].append(float(r["group_total"]))

    def f_stat(groups):
        vals = [v for g in groups for v in g]
        n, k = len(vals), len(groups)
        if k < 2 or n <= k:
            return None
        gm = statistics.fmean(vals)
        ssb = sum(len(g) * (statistics.fmean(g) - gm) ** 2 for g in groups)
        ssw = sum((v - statistics.fmean(g)) ** 2 for g in groups for v in g)
        if ssw == 0:
            return float("inf") if ssb > 0 else 0.0
        return (ssb / (k - 1)) / (ssw / (n - k))

    rng = random.Random(20260813)
    results = []
    for key, accts in sorted(by_cell.items()):
        groups = [v for v in accts.values() if v]
        if len(groups) < 2:
            continue
        obs = f_stat(groups)
        if obs is None:
            continue
        sizes = [len(g) for g in groups]
        pool = [v for g in groups for v in g]
        if len(set(pool)) == 1:                     # constant cell: nothing to test
            results.append({"model": key[0], "risk": key[1], "language": key[2],
                            "n_accounts": len(groups), "n_games": len(pool),
                            "F": 0.0, "p_perm": 1.0, "constant": True})
            continue
        ge = 0
        for _ in range(10000):
            rng.shuffle(pool)
            i, perm = 0, []
            for s in sizes:
                perm.append(pool[i:i + s])
                i += s
            fp = f_stat(perm)
            if fp is not None and fp >= obs:
                ge += 1
        results.append({"model": key[0], "risk": key[1], "language": key[2],
                        "n_accounts": len(groups), "n_games": len(pool),
                        "F": round(obs, 3), "p_perm": round((ge + 1) / 10001, 4),
                        "constant": False})
    sig = [r for r in results if r["p_perm"] < 0.05]
    return {"cells_tested": len(results), "cells_significant_at_05": len(sig),
            "significant": sig, "all": results}


def main() -> None:
    params = read_declared_params()
    caps = observed_caps()
    shards = shard_games()
    rep = replication(shards)
    acct = account_effect(shards)

    report = {"declared_decoding": params,
              "observed_max_completion_tokens": caps,
              "run_to_run": rep,
              "account_effect": acct}
    (OUT / "r1_decoding_stability.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")

    print("== decoding parameters actually sent to the Model Proxy ==")
    for k, v in params.items():
        print(f"  {k:28s} {v}")
    print("\n== max_completion_tokens observed per model (from shard logs) ==")
    for k, v in caps.items():
        print(f"  {k:48s} {v}")
    print("\n== run-to-run replication (same cell, different shard) ==")
    for k, v in rep.items():
        if k != "detail":
            print(f"  {k:28s} {v}")
    print()
    for d in rep["detail"]:
        flag = "same " if len(set(d["totals"])) == 1 else "DIFF "
        print(f"  {flag}{d['model']:38s} p={d['risk']} {d['language']} rep{d['rep']:<2d}"
              f" totals={d['totals']} accts={d['accounts']}")

    print("\n== execution-batch (account) effect within cells, permutation ANOVA ==")
    print(f"  cells tested                 {acct['cells_tested']}")
    print(f"  significant at .05           {acct['cells_significant_at_05']}")
    for r in acct["all"]:
        print(f"    {r['model']:38s} p={r['risk']} {r['language']} "
              f"accts={r['n_accounts']} n={r['n_games']:<3d} F={r['F']:<8} "
              f"p={r['p_perm']}{'  (constant)' if r['constant'] else ''}")


if __name__ == "__main__":
    main()
