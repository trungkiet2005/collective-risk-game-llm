"""Rebuttal wave, dynamic partners (AAMAS 2027, R1 JJ3F, 2026-11-21): 6 shards.

One llm seat (P1) against five scripted partners that pay 2 in rounds 1-5 and then
switch for good, from round 6 on:

    switch_to_0   partners pay 0 -> the target can no longer be reached
    switch_to_4   partners pay 4 -> the target is certain

The best response from round 6 is 0 in both arms. The control with the same seat
layout is exp_bestresponse_coop (five always_2 partners), already in results/.

    shards  {Haiku, Flash-Lite, Luna} x {switch_to_0, switch_to_4}
    cells   p = 0.1 and 0.9, 10 games each -> 20 games x 10 llm calls = 200 calls
    task    crg-rb-switch (its own name, so it never overwrites crg-rb-probe /
            crg-rb-showpool sweeps on a user that also ran those)

Qwen3-235B and Grok 4.20 are left out on purpose: since 2026-11-21 the endpoint
answers "Skipped (Unsupported model version)" for both (STATE.md).

    python plan/scripts/probe_accounts.py                      # who is alive
    python plan/scripts/launch_rb_switch.py --dry-run
    python plan/scripts/launch_rb_switch.py [--accounts a,b,c,d,e,f] [--only switch_to_0]

Results (CRG_DL_ROOT, default D:/tmp/crgdl) -> results/ with
    python plan/scripts/to_wide_csv.py --src <dl> --experiment exp_bestresponse_switch0
    python plan/scripts/to_wide_csv.py --src <dl> --experiment exp_bestresponse_switch4
    python plan/scripts/verify_wide.py --expect-reps 10
"""
import argparse
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LAUNCH = REPO / "plan" / "scripts" / "launch_shard.py"
sys.path.insert(0, str(LAUNCH.parent))
from launch_shard import ACCOUNTS, ALIASES  # noqa: E402

DL = os.environ.get("CRG_DL_ROOT", "D:/tmp/crgdl")
TASK = "crg-rb-switch"

HAIKU, LUNA, FLASH = "claude-haiku-4-5-20251001", "gpt-5.6-luna", "gemini-3.5-flash-lite"
SHORT = {HAIKU: "haiku", LUNA: "luna", FLASH: "flash"}
POLICIES = ("switch_to_0", "switch_to_4")

# Default users: those of launch_rb.py's Qwen/Grok shards, which the endpoint refused,
# so they spent close to nothing (probe 2026-11-21: all six alive). One Kaggle USER per
# shard; acc1-acc4 are the same users as acc06-acc09 (ALIASES), never pair them.
DEFAULT_ACCOUNTS = ("acc11", "chisboiz", "acc1", "acc2", "acc3", "acc4")
PLAN = [(policy, model) for policy in POLICIES for model in (HAIKU, FLASH, LUNA)]


def seats(policy):
    return "self," + ",".join(["scripted:" + policy] * 5)


def label(policy, model):
    return "rb_switch%s_%s" % (policy[-1], SHORT[model])


def cmd(policy, model, account):
    return [sys.executable, str(LAUNCH), "--account", account, "--model", model,
            "--langs", "en", "--risks", "0.1,0.9", "--reps", "10",
            "--seat-models", seats(policy), "--max-out", "3000",
            "--concurrency", "1", "--on-game-error", "skip", "--wait", "7200",
            "--task", TASK, "--label", label(policy, model)]


def user_of(account):
    """The Kaggle user behind a label: acc06 and acc1 are one user (ALIASES)."""
    back = {v: k for k, v in ALIASES.items()}
    return back.get(account, account)


def one(row):
    policy, model, account = row
    lab = label(policy, model)
    logf = REPO / "plan" / "runs" / ("%s.driver.log" % lab)
    logf.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, CRG_DL_ROOT=DL)
    with open(logf, "w", encoding="utf-8") as fh:
        rc = subprocess.run(cmd(policy, model, account), stdout=fh,
                            stderr=subprocess.STDOUT, cwd=str(REPO), env=env).returncode
    print("%-22s %-14s rc=%d" % (lab, account, rc), flush=True)
    return rc


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--accounts", default=",".join(DEFAULT_ACCOUNTS),
                    help="six labels, one per shard, in PLAN order")
    ap.add_argument("--only", choices=POLICIES)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()

    accounts = [s.strip() for s in a.accounts.split(",") if s.strip()]
    if len(accounts) != len(PLAN):
        raise SystemExit("need %d accounts, got %d" % (len(PLAN), len(accounts)))
    unknown = [x for x in accounts if x not in ACCOUNTS]
    if unknown:
        raise SystemExit("unknown accounts: %s" % ", ".join(unknown))
    users = [user_of(x) for x in accounts]
    if len(users) != len(set(users)):
        raise SystemExit("one Kaggle USER per shard (acc06=acc1 etc.): %s" % accounts)

    rows = [(p, m, acc) for (p, m), acc in zip(PLAN, accounts)
            if not a.only or p == a.only]
    for r in rows:
        print(" ".join(cmd(*r)))
    if not a.dry_run:
        with ThreadPoolExecutor(a.workers) as ex:
            rcs = list(ex.map(one, rows))
        print("done", rcs)
