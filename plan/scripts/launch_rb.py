"""Rebuttal wave (AAMAS 2027, 2026-11-21): 15 shards, one Kaggle user each, plan fixed here.

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

HAIKU, LUNA = "claude-haiku-4-5-20251001", "gpt-5.6-luna"
FLASH, QWEN, GROK = ("gemini-3.5-flash-lite", "qwen3-235b-a22b-instruct-2507",
                     "grok-4.20-0309-non-reasoning")
SHORT = {QWEN: "qwen", GROK: "grok", FLASH: "flash", LUNA: "luna", HAIKU: "haiku"}

PLAN = [
    ("probe", HAIKU, None, "kakagotto"), ("probe", LUNA, None, "tonngohan"),
    ("probe", FLASH, None, "acc5"), ("probe", QWEN, None, "acc11"),
    ("probe", GROK, None, "chisboiz"),
    ("showpool", HAIKU, "0.1", "chunaiu"), ("showpool", HAIKU, "0.9", "hunhtrungkit"),
    ("showpool", LUNA, "0.1", "kit567"), ("showpool", LUNA, "0.9", "tnkiet"),
    ("showpool", FLASH, "0.1", "trunkdabest"), ("showpool", FLASH, "0.9", "vinhdinhthien"),
    ("showpool", QWEN, "0.1", "acc1"), ("showpool", QWEN, "0.9", "acc2"),
    ("showpool", GROK, "0.1", "acc3"), ("showpool", GROK, "0.9", "acc4"),
]


def cmd(arm, model, risk, acc):
    conc = "2" if model == GROK else "3"
    c = [sys.executable, str(LAUNCH), "--account", acc, "--model", model, "--langs", "en",
         "--max-out", "3000", "--concurrency", conc, "--on-game-error", "skip",
         "--wait", "7200"]
    if arm == "probe":
        c += ["--task", "crg-rb-probe", "--risks", "0.9", "--reps", "1",
              "--label", "rb_probe_%s" % SHORT[model]]
    else:
        c += ["--task", "crg-rb-showpool", "--risks", risk, "--reps", "10",
              "--template", "showpool",
              "--label", "rb_showpool_%s_p%s" % (SHORT[model], risk.replace(".", ""))]
    return c


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
    ap.add_argument("--only")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--workers", type=int, default=5)
    a = ap.parse_args()
    rows = [r for r in PLAN if not a.only or r[0] == a.only]
    users = [r[3] for r in rows]
    assert len(users) == len(set(users)), "one user per shard"
    for r in rows:
        print(" ".join(cmd(*r)))
    if not a.dry_run:
        with ThreadPoolExecutor(a.workers) as ex:
            rcs = list(ex.map(one, rows))
        print("done", rcs)
