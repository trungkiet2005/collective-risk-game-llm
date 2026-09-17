"""Drive the prompt-framing arms (exp_neutral, exp_wording) shard by shard.

Two arms, one question from the AAMAS review: is payment at p=0 a habit, or a response
to the prompt's framing?
    neutral  normative words replaced AND the own-cash objective stated
    wording  the same words replaced, objective NOT stated
Both play p = 0, 0.1, 0.9 with 10 repetitions per model, like every other arm.

    python plan/scripts/drive_neutral.py --arm wording --dry-run
    python plan/scripts/drive_neutral.py --arm wording
    python plan/scripts/drive_neutral.py --arm wording --missing   # cells not downloaded yet

Why a driver and not launch_e6.py, learned on 17-09-2026:
  * one shard per Kaggle USER. acc06=acc1, acc07=acc2, acc08=acc3, acc09=acc4 are one user
    each; two shards of one task on one user overwrite each other's sweep. Refused here.
  * launch_e6.py reruns a whole repetition when any risk of it is missing, which would
    replay cells that already exist. Fills here are per cell: see --missing.
  * shards are small (Haiku 6 games) because two accounts stopped at about $2 of spend
    that day; a small shard that dies loses little.
"""
import argparse
import collections
import csv
import glob
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from launch_shard import ALIASES  # noqa: E402

LAUNCH = REPO / "plan" / "scripts" / "launch_shard.py"
DL = "D:/tmp/crgdl"
RISKS = "0,0.1,0.9"
HAIKU, LUNA = "claude-haiku-4-5-20251001", "gpt-5.6-luna"
FLASH, QWEN, GROK = "gemini-3.5-flash-lite", "qwen3-235b-a22b-instruct-2507", "grok-4.20-0309-non-reasoning"
TAG = {HAIKU: "anthropic-claude-haiku-4-5-20251001", LUNA: "openai-gpt-5.6-luna",
       FLASH: "google-gemini-3.5-flash-lite", QWEN: "qwen-qwen3-235b-a22b-instruct-2507",
       GROK: "xai-grok-4.20-0309-non-reasoning"}

# arm -> [(label, account, model, risks, rep_start, reps, concurrency)]
PLANS = {
    "wording": [
        ("e6_wording_qwen_s00", "kit567", QWEN, RISKS, 0, 10, 4),
        ("e6_wording_grok_s00", "trunkdabest", GROK, RISKS, 0, 10, 2),   # 429-prone
        ("e6_wording_flash_s00", "trungkiet", FLASH, RISKS, 0, 10, 4),
        ("e6_wording_luna_s00", "vinhdinhthien", LUNA, RISKS, 0, 10, 4),
        ("e6_wording_haiku_s00", "acc06", HAIKU, RISKS, 0, 2, 2),
        ("e6_wording_haiku_s02", "acc07", HAIKU, RISKS, 2, 2, 2),
        ("e6_wording_haiku_s04", "chunaiu", HAIKU, RISKS, 4, 2, 2),
        ("e6_wording_haiku_s06", "acc5", HAIKU, RISKS, 6, 2, 2),
        ("e6_wording_haiku_s08", "acc11", HAIKU, RISKS, 8, 2, 2),
    ],
}
LOG = REPO / "plan" / "runs" / "e6_neutral_driver.log"


def say(msg):
    line = "[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def shard_cmd(arm, sh, phase):
    label, account, model, risks, rep_start, reps, conc = sh
    cmd = [sys.executable, str(LAUNCH), "--account", account, "--model", model,
           "--risks", risks, "--langs", "en", "--reps", str(reps),
           "--rep-start", str(rep_start), "--max-out", "3000", "--concurrency", str(conc),
           "--task", "crg-e6-%s" % arm, "--label", label, "--on-game-error", "skip",
           "--template", arm, "--%s-only" % phase]
    if phase == "run":
        cmd += ["--wait", "21600"]
    return cmd


def run_phase(arm, sh, phase):
    logf = REPO / "plan" / "runs" / ("%s.%s.log" % (sh[0], phase))
    with open(logf, "a", encoding="utf-8") as fh:
        return subprocess.run(shard_cmd(arm, sh, phase), stdout=fh,
                              stderr=subprocess.STDOUT, cwd=str(REPO)).returncode


def drive(arm, sh):
    rc = run_phase(arm, sh, "push")
    say("%s: push rc=%d" % (sh[0], rc))
    if rc != 0:
        return sh[0], "push rc=%d" % rc
    rc = run_phase(arm, sh, "run")
    say("%s: run rc=%d" % (sh[0], rc))
    return sh[0], "ok" if rc == 0 else "run rc=%d" % rc


def downloaded(arm):
    """model tag -> {(risk, rep)} over every downloaded games.csv of this arm."""
    got = collections.defaultdict(collections.Counter)
    for f in glob.glob("%s/*/crg-e6-%s/**/games.csv" % (DL, arm), recursive=True):
        with open(f, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                got[r["model"]][(float(r["risk_probability"]), int(r["rep"]))] += 1
    return got


def report_missing(arm):
    got = downloaded(arm)
    want = {(float(p), rep) for p in RISKS.split(",") for rep in range(10)}
    bad = False
    for slug, tag in TAG.items():
        cells = got.get(tag, collections.Counter())
        missing = sorted(want - set(cells))
        dups = sorted(k for k, v in cells.items() if v > 1)
        bad |= bool(missing or dups)
        print("%-40s have %2d/30  missing %s%s" % (
            tag, len(set(cells) & want), missing or "-",
            ("  DUPLICATES %s" % dups) if dups else ""))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=sorted(PLANS))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--missing", action="store_true")
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    if args.missing:
        return report_missing(args.arm)
    todo = [s for s in PLANS[args.arm] if not args.only or args.only in s[0]]
    users = [ALIASES.get(s[1], s[1]) for s in todo]
    if len(set(users)) != len(users):
        raise SystemExit("two shards on one Kaggle user: %s" % users)
    games = collections.Counter()
    for s in todo:
        games[s[2]] += len(s[3].split(",")) * s[5]
        say("plan %-24s %-14s %-30s p=%s reps %d..%d conc %d"
            % (s[0], s[1], s[2], s[3], s[4], s[4] + s[5] - 1, s[6]))
    say("games per model: %s" % dict(games))
    if args.dry_run:
        return 0
    with ThreadPoolExecutor(max_workers=len(todo)) as pool:
        futures = []
        for s in todo:
            futures.append(pool.submit(drive, args.arm, s))
            time.sleep(90)            # stagger pushes; validations share one server model
        results = [f.result() for f in futures]
    for label, outcome in results:
        say("DONE %-24s %s" % (label, outcome))
    say("ALL DONE %s: %d/%d ok" % (args.arm, sum(o == "ok" for _, o in results), len(results)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
