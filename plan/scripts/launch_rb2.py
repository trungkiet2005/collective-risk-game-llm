"""Rebuttal probe wave 2 (AAMAS 2027, 2026-11-21): independent replication at n = 20.

Wave 1 (`launch_rb.py`, task crg-rb-probe) asked 10 counterfactual and 5 explained-decision
calls per cell. Wave 2 asks 20 of each, recognition dropped (wave 1: 10/10 for every model
and template). Same prompts, same decide() and parser: the task file is the committed
kaggle/benchmarks/crg_rb_probe_task.py with three defaults rewritten here, plus a new seed
offset so no call reuses a wave-1 seed. Only Haiku, Flash-Lite and Luna are still served.

    python plan/scripts/launch_rb2.py [--dry-run]
    python paper/AAMAS/analysis/rebuttal_probes.py D:/tmp/crgdl --task crg-rb-probe2 --tag _w2
"""
import argparse
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LAUNCH = REPO / "plan" / "scripts" / "launch_shard.py"
SRC = REPO / "kaggle" / "benchmarks" / "crg_rb_probe_task.py"
DST = REPO / "kaggle" / "benchmarks" / "crg_rb_probe2_task.py"
DL = os.environ.get("CRG_DL_ROOT", "D:/tmp/crgdl")

HAIKU, FLASH, LUNA = "claude-haiku-4-5-20251001", "gemini-3.5-flash-lite", "gpt-5.6-luna"
SHORT = {HAIKU: "haiku", FLASH: "flash", LUNA: "luna"}
PLAN = [(HAIKU, "foundnotkiet"), (FLASH, "trungkiet"), (LUNA, "kakagotto")]

REWRITES = [
    ('RB_SEED_OFFSET = 900_000_000', 'RB_SEED_OFFSET = 950_000_000'),
    ('os.environ.get("CRG_RB_SAMPLES_CF", "10")', 'os.environ.get("CRG_RB_SAMPLES_CF", "20")'),
    ('os.environ.get("CRG_RB_SAMPLES_EX", "5")', 'os.environ.get("CRG_RB_SAMPLES_EX", "20")'),
    ('os.environ.get("CRG_RB_SAMPLES_RC", "5")', 'os.environ.get("CRG_RB_SAMPLES_RC", "0")'),
    # push validation picked one recog item; with none asked it must not raise StopIteration
    ('        items = [items[0], next(i for i in items if i["kind"] == "explain"),\n'
     '                 next(i for i in items if i["kind"] == "recog")]',
     '        items = [i for i in (items[0],\n'
     '                 next((i for i in items if i["kind"] == "explain"), None),\n'
     '                 next((i for i in items if i["kind"] == "recog"), None)) if i]'),
]


def build():
    src = SRC.read_text(encoding="utf-8")
    for old, new in REWRITES:
        if src.count(old) != 1:
            raise SystemExit("rewrite target not found exactly once: %r" % old[:60])
        src = src.replace(old, new)
    DST.write_text(src, encoding="utf-8")
    print("wrote", DST)


def cmd(model, acc):
    return [sys.executable, str(LAUNCH), "--account", acc, "--model", model, "--langs", "en",
            "--max-out", "3000", "--concurrency", "3", "--on-game-error", "skip",
            "--wait", "7200", "--task", "crg-rb-probe2", "--risks", "0.9", "--reps", "1",
            "--label", "rb2_probe_%s" % SHORT[model]]


def one(row):
    model, acc = row
    env = dict(os.environ, CRG_DL_ROOT=DL, CRG_TASK_SRC=str(DST))
    c = cmd(model, acc)
    logf = REPO / "plan" / "runs" / ("rb2_probe_%s.driver.log" % SHORT[model])
    with open(logf, "w", encoding="utf-8") as fh:
        rc = subprocess.run(c, stdout=fh, stderr=subprocess.STDOUT, cwd=str(REPO),
                            env=env).returncode
    print("%-20s %-14s rc=%d" % (SHORT[model], acc, rc), flush=True)
    return rc


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    build()
    assert len({acc for _, acc in PLAN}) == len(PLAN), "one user per shard"
    for r in PLAN:
        print(" ".join(cmd(*r)))
    if not a.dry_run:
        with ThreadPoolExecutor(len(PLAN)) as ex:
            print("done", list(ex.map(one, PLAN)))
