"""Generalisation wave (AAMAS 2027 rebuttal, mTF6 Q3), plan fixed 2026-11-21 before any run.

Six newer or open models, same instruments; data stays in plan/runs (never results/).
Day 1: per model, one user runs the probe (185 calls) then base self-play at p = 0 (10 games).
Day 2 (`--day 2`, after the 24 h quota window): base self-play at p = 0.1 and 0.9.

Original rebuttal-wave docstring follows.

    probe     crg-rb-probe     185 single calls per model (crg_rb_probe_task.py)
    showpool  crg-rb-showpool  baseline wording + running pool shown, self-play, 10 games
                               per (model, risk), p = 0.1 and 0.9

    python plan/scripts/launch_rb.py [--only probe|showpool] [--dry-run]
"""
import argparse
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LAUNCH = REPO / "plan" / "scripts" / "launch_shard.py"
PROBE_SRC = REPO / "kaggle" / "benchmarks" / "crg_rb_probe_task.py"
DL = os.environ.get("CRG_DL_ROOT", str(REPO / "plan" / "runs" / "_dl"))

MODELS = {"haiku55": ("claude-haiku-5-5", "3000"), "luna6": ("gpt-6-luna", "6000"),
          "grok47": ("grok-4.7", "6000"), "flash38": ("gemini-3.8-flash", "6000"),
          "gemma31": ("gemma-4-31b-it", "3000"), "oss120": ("gpt-oss-120b", "6000")}
DAY1 = {"haiku55": "acc1", "luna6": "acc2", "grok47": "acc3", "flash38": "acc4",
        "gemma31": "acc11", "oss120": "chisboiz"}
DAY2 = {}   # filled on day 2 from probe_accounts.py, one user per (model, risk)


def cmd(arm, short, risk, acc):
    slug, cap = MODELS[short]
    c = [sys.executable, str(LAUNCH), "--account", acc, "--model", slug, "--langs", "en",
         "--max-out", cap, "--concurrency", "2", "--on-game-error", "skip", "--wait", "7200"]
    if arm == "probe":
        c += ["--task", "crg-gen-probe", "--risks", "0.9", "--reps", "1",
              "--label", "gen_probe_%s" % short]
    else:
        c += ["--task", "crg-gen-selfplay-p%s" % risk.replace(".", ""), "--risks", risk,
              "--reps", "10", "--label", "gen_self_%s_p%s" % (short, risk.replace(".", ""))]
    return c


def chain(rows):
    """Run one user's rows in order (probe first), so a user never runs two shards at once."""
    return [one(r) for r in rows]


def one(row):
    arm, model, risk, acc = row
    env = dict(os.environ, CRG_DL_ROOT=DL)
    if arm == "probe":
        env["CRG_TASK_SRC"] = str(PROBE_SRC)
    lab = cmd(*row)[cmd(*row).index("--label") + 1]
    logf = REPO / "plan" / "runs" / ("%s.driver.log" % lab)
    logf.parent.mkdir(parents=True, exist_ok=True)
    with open(logf, "w", encoding="utf-8") as fh:
        rc = subprocess.run(cmd(*row), stdout=fh, stderr=subprocess.STDOUT, cwd=str(REPO),
                            env=env).returncode
    print("%-28s %-14s rc=%d" % (lab, acc, rc), flush=True)
    return rc


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.day == 1:
        users = {acc: [("probe", m, None, acc), ("self", m, "0", acc)] for m, acc in DAY1.items()}
    else:
        users = {acc: [("self", m, r, acc)] for (m, r), acc in DAY2.items()}
    for rows in users.values():
        for r in rows:
            print(" ".join(cmd(*r)))
    if not a.dry_run:
        with ThreadPoolExecutor(len(users)) as ex:
            print("done", list(ex.map(chain, users.values())))
