"""E8 -- three follow-up arms from the AAMAS review, 350 games on the five-model panel.

    arm              task                      server folder                  results/ folder                    p          seats
    groupgoal        crg-e8-groupgoal          exp_groupgoal                  exp_groupgoal                      0,0.1,0.9  self-play
    showpool         crg-e8-showpool           exp_showpool                   exp_showpool                       0          self-play
    showpool_defect  crg-e8-showpool-defect    exp_showpool_seats-L00000-<h>  exp_showpool_bestresponse_defect   0.9        P1 + 5 x always_0
    showpool_carry   crg-e8-showpool-carry     exp_showpool_seats-L44444-<h>  exp_showpool_bestresponse_carry    0.9        P1 + 5 x always_4
    evprobe_p0       crg-e8-evprobe-p0         exp_baseline_probe-value       exp_evprobe_p0                     0          self-play, CRG_PROBE=value

10 reps per cell, 5 models: 150 + 50 + 50 + 50 + 50 = 350 games, every model the same cells.

    groupgoal   neutral wording, {framing} ON with the GROUP's total cash as the objective
    showpool    baseline wording, the running pool shown to every seat every round
    evprobe_p0  baseline wording, the two value questions at rounds 1/5/10 (seat P1), p = 0

Every arm has its own task name, so no shard of this wave can push over a shard of an
existing wave, and its own server folder / game_id suffix / checkpoint signature (see
crsd/tests/test_kaggle_e8_arms.py), so no shard can resume into an existing arm.

    python plan/scripts/launch_e8.py --dry-run
    python plan/scripts/launch_e8.py --dry-run --arms showpool,evprobe_p0
    python plan/scripts/launch_e8.py --missing
    python plan/scripts/launch_e8.py --accounts a,b,c,...

Like launch_e3a.py, what is missing is read from the DOWNLOADED data, per (risk, rep)
cell, so running this again never replays a cell that is already on disk.
"""
import argparse
import csv
import glob
import subprocess
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from launch_shard import ALIASES  # noqa: E402

LAUNCH = REPO / "plan" / "scripts" / "launch_shard.py"
DL = "D:/tmp/crgdl"
LANGS = "en"
REPS = 10
PUSH_CONC = 3
MODEL_CAP = 8
PUSH_VALIDATE_COST = 0.10
EXPECTED_TOTAL = 350

HAIKU, LUNA = "claude-haiku-4-5-20251001", "gpt-5.6-luna"
FLASH, QWEN, GROK = ("gemini-3.5-flash-lite", "qwen3-235b-a22b-instruct-2507",
                     "grok-4.20-0309-non-reasoning")
MODELS = [QWEN, GROK, FLASH, LUNA, HAIKU]
TAG = {HAIKU: "anthropic-claude-haiku-4-5-20251001", LUNA: "openai-gpt-5.6-luna",
       FLASH: "google-gemini-3.5-flash-lite", QWEN: "qwen-qwen3-235b-a22b-instruct-2507",
       GROK: "xai-grok-4.20-0309-non-reasoning"}
SHORT = {QWEN: "qwen", GROK: "grok", FLASH: "flash", LUNA: "luna", HAIKU: "haiku"}
# $/game measured on the 6-seat self-play cell (launch_e6.py).
COST = {QWEN: 0.0078, GROK: 0.0230, FLASH: 0.0327, LUNA: 0.0787, HAIKU: 0.1780}
# Output cap per model: the tail cap every existing arm ran with (CLAUDE.md, truncation).
MAX_OUT = {m: "3000" for m in MODELS}
# Grok 429s under 4 parallel seats (drive_neutral.py); the rest ran at 4.
CONCURRENCY = {m: ("2" if m == GROK else "4") for m in MODELS}


def seat_spec(policy):
    return "self," + ",".join(["scripted:" + policy] * 5)


# cost_factor: share of a self-play game's llm calls. One llm seat = 10 of 60 calls;
# CRG_PROBE=value asks 2 questions at 3 rounds = 6 extra calls on 60.
ARMS = {
    "groupgoal": dict(task="crg-e8-groupgoal", risks="0,0.1,0.9",
                      flags=["--template", "groupgoal"], seats=None,
                      server="exp_groupgoal", suffix="_groupgoal",
                      results="exp_groupgoal", cost_factor=1.0),
    "showpool": dict(task="crg-e8-showpool", risks="0",
                     flags=["--template", "showpool"], seats=None,
                     server="exp_showpool", suffix="_showpool",
                     results="exp_showpool", cost_factor=1.0),
    "showpool_defect": dict(task="crg-e8-showpool-defect", risks="0.9",
                            flags=["--template", "showpool"], seats=seat_spec("always_0"),
                            server="exp_showpool_seats-L00000-",
                            suffix="_showpool_seats-L00000-",
                            results="exp_showpool_bestresponse_defect",
                            cost_factor=1 / 6),
    "showpool_carry": dict(task="crg-e8-showpool-carry", risks="0.9",
                           flags=["--template", "showpool"], seats=seat_spec("always_4"),
                           server="exp_showpool_seats-L44444-",
                           suffix="_showpool_seats-L44444-",
                           results="exp_showpool_bestresponse_carry",
                           cost_factor=1 / 6),
    "evprobe_p0": dict(task="crg-e8-evprobe-p0", risks="0",
                       flags=["--probe", "value"], seats=None,
                       server="exp_baseline_probe-value", suffix="_probe-value",
                       results="exp_evprobe_p0", cost_factor=66 / 60),
}


def risks_of(arm):
    return ARMS[arm]["risks"].split(",")


def label(arm, model, rep_start, risks):
    tail = "" if risks == ARMS[arm]["risks"] else "_p" + risks.replace(",", "-")
    return "e8_%s_%s_s%02d%s" % (arm, SHORT[model], rep_start, tail)


def _suffix_of(game_id):
    """'crsd_milinski_p000_risk_showpool__tag__en__rep0' -> '_showpool'."""
    name = game_id.split("__", 1)[0]
    for base in ("crsd_milinski_high_risk", "crsd_milinski_medium_risk",
                 "crsd_milinski_low_risk"):
        if name.startswith(base):
            return name[len(base):]
    if name.startswith("crsd_milinski_p") and "_risk" in name:
        return name[name.index("_risk") + len("_risk"):]
    return None


def downloaded(arm):
    """model tag -> Counter((risk, rep)) over downloaded games.csv of this arm's task.

    A row counts only if its game_id carries the arm's own suffix: the task folder says
    what we meant to run, the game_id says what the server actually played.
    """
    spec = ARMS[arm]
    got = defaultdict(lambda: defaultdict(int))
    for f in glob.glob("%s/*/%s/**/games.csv" % (DL, spec["task"]), recursive=True):
        with open(f, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                sfx = _suffix_of(r.get("game_id") or "")
                ok = (sfx is not None and sfx.startswith(spec["suffix"])
                      and (spec["seats"] or "_seats-" not in sfx))
                if ok:
                    got[r["model"]][(float(r["risk_probability"]), int(r["rep"]))] += 1
    return got


def plan(arms, max_cost, only_missing=True):
    """[(arm, model, risks, rep_start, n_reps, $)] -- cheap first.

    Reps whose missing risk set is identical and contiguous share one shard, so a shard
    never replays a cell that is already downloaded.
    """
    out = []
    for arm in arms:
        got = downloaded(arm) if only_missing else {}
        for m in MODELS:
            cells = got.get(TAG[m], {})
            per_rep = {}
            for rep in range(REPS):
                need = tuple(p for p in risks_of(arm) if (float(p), rep) not in cells)
                if need:
                    per_rep[rep] = need
            unit = COST[m] * ARMS[arm]["cost_factor"]
            reps = sorted(per_rep)
            i = 0
            while i < len(reps):
                need = per_rep[reps[i]]
                step = max(1, int(max_cost // (unit * len(need))))
                j = i + 1
                while (j < len(reps) and j - i < step and reps[j] == reps[j - 1] + 1
                       and per_rep[reps[j]] == need):
                    j += 1
                n = j - i
                out.append((arm, m, ",".join(need), reps[i], n,
                            n * len(need) * unit + PUSH_VALIDATE_COST))
                i = j
    out.sort(key=lambda s: s[5])
    return out


def design_games(arms):
    return sum(len(risks_of(a)) * REPS * len(MODELS) for a in arms)


def shard_cmd(sh, account, phase, wait):
    arm, model, risks, rep_start, n, _ = sh
    spec = ARMS[arm]
    cmd = [sys.executable, str(LAUNCH), "--account", account, "--model", model,
           "--risks", risks, "--langs", LANGS, "--reps", str(n),
           "--rep-start", str(rep_start), "--max-out", MAX_OUT[model],
           "--concurrency", CONCURRENCY[model], "--task", spec["task"],
           "--label", label(arm, model, rep_start, risks),
           "--on-game-error", "skip", "--%s-only" % phase] + list(spec["flags"])
    if spec["seats"]:
        cmd += ["--seat-models", spec["seats"]]
    if phase == "run":
        cmd += ["--wait", wait]
    return cmd


def one(sh, account, phase, wait):
    lab = label(sh[0], sh[1], sh[3], sh[2])
    logf = REPO / "plan" / "runs" / ("%s.%s.log" % (lab, phase))
    logf.parent.mkdir(parents=True, exist_ok=True)
    with open(logf, "w", encoding="utf-8") as fh:
        rc = subprocess.run(shard_cmd(sh, account, phase, wait), stdout=fh,
                            stderr=subprocess.STDOUT, cwd=str(REPO)).returncode
    print("  %-5s %-36s %-14s rc=%d" % (phase, lab, account, rc), flush=True)
    return rc


def take_batch(todo, accounts, cap):
    """One batch: at most one shard per Kaggle USER (ALIASES) and per-model load <= cap."""
    load, batch, rest, users = defaultdict(int), [], [], set()
    free = list(accounts)
    for sh in todo:
        m = sh[1]
        acc = next((a for a in free if ALIASES.get(a, a) not in users), None)
        if acc is None or load[m] + int(CONCURRENCY[m]) > cap:
            rest.append(sh)
            continue
        free.remove(acc)
        users.add(ALIASES.get(acc, acc))
        load[m] += int(CONCURRENCY[m])
        batch.append((sh, acc))
    return batch, rest


def preflight():
    bad = []
    srv = (REPO / "kaggle" / "benchmarks" / "crg_task_server.py").read_text(
        encoding="utf-8", errors="replace")
    for name in ("groupgoal", "showpool"):
        if '"%s"' % name not in srv:
            bad.append("crg_task_server.py has no template variant %r" % name)
    if "SHOW_CUMULATIVE_VARIANTS" not in srv:
        bad.append("crg_task_server.py cannot switch the pool line on (SHOW_CUMULATIVE)")
    return bad


def print_plan(shards, arms, header):
    print(header)
    print("  %-30s %-16s %-10s %-5s %-5s %-18s %-7s %-6s %-5s %s" % (
        "model", "arm", "risks", "reps", "games", "seats", "max-out", "$", "task",
        "output folder: server -> results/"))
    order = {a: i for i, a in enumerate(ARMS)}
    for arm, m, risks, start, n, cost in sorted(
            shards, key=lambda s: (order[s[0]], MODELS.index(s[1]), s[3])):
        spec = ARMS[arm]
        games = n * len(risks.split(","))
        seats = ("P1 + 5x " + spec["seats"].rsplit(":", 1)[1]) if spec["seats"] else "self-play"
        print("  %-30s %-16s %-10s %-5s %-5d %-18s %-7s %-6.2f %s  %s* -> %s" % (
            m, arm, risks, "%d-%d" % (start, start + n - 1), games, seats, MAX_OUT[m],
            cost, spec["task"], spec["server"], spec["results"]))
    per_model, per_arm = defaultdict(int), defaultdict(int)
    for arm, m, risks, _, n, _ in shards:
        per_model[SHORT[m]] += n * len(risks.split(","))
        per_arm[arm] += n * len(risks.split(","))
    total = sum(per_model.values())
    print("  games by model: " + "  ".join("%s=%d" % kv for kv in sorted(per_model.items())))
    print("  games by arm:   " + "  ".join("%s=%d" % kv for kv in sorted(per_arm.items())))
    print("  shards=%d  games=%d  est=$%.2f  design total for these arms=%d"
          % (len(shards), total, sum(s[5] for s in shards), design_games(arms)))
    if len(set(per_model.values())) > 1:
        print("  !! UNBALANCED across models (expected only while a fill is partial)")
    return total


def gather_hint(arms):
    print("\nGather (one arm per call, --src narrow, --experiment explicit):")
    for arm in arms:
        spec = ARMS[arm]
        print("  python plan/scripts/to_wide_csv.py --src %s/*/%s --experiment %s"
              % (DL, spec["task"], spec["results"]))
    print("  python plan/scripts/verify_wide.py --expect-reps 10")
    if "evprobe_p0" in arms:
        print("  probes: collect_probes.py is pinned to crg-e2-evprobe -> exp_evprobe_probes.*;"
              " it needs a --task/--experiment option before exp_evprobe_p0 can be collected")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--accounts", default="")
    ap.add_argument("--arms", default="", help="subset, e.g. 'showpool,evprobe_p0'")
    ap.add_argument("--wait", default="21600")
    ap.add_argument("--max-rounds", type=int, default=12)
    ap.add_argument("--net-wait", type=int, default=300)
    ap.add_argument("--model-cap", type=int, default=MODEL_CAP)
    ap.add_argument("--max-cost", type=float, default=3.0)
    ap.add_argument("--dry-run", action="store_true",
                    help="print the FULL design plan and what is still missing, launch nothing")
    ap.add_argument("--missing", action="store_true",
                    help="per model: downloaded cells vs design")
    args = ap.parse_args()
    arms = [a.strip() for a in args.arms.split(",") if a.strip()] or list(ARMS)
    unknown = [a for a in arms if a not in ARMS]
    if unknown:
        print("unknown arm(s) %s (known: %s)" % (unknown, ", ".join(ARMS)))
        return 2
    problems = preflight()
    for msg in problems:
        print("!! " + msg)

    if args.missing:
        bad = 0
        for arm in arms:
            got = downloaded(arm)
            want = {(float(p), r) for p in risks_of(arm) for r in range(REPS)}
            for m in MODELS:
                cells = got.get(TAG[m], {})
                miss = sorted(want - set(cells))
                dups = sorted(k for k, v in cells.items() if v > 1)
                bad |= bool(miss or dups)
                print("%-16s %-40s have %3d/%3d  missing %d%s" % (
                    arm, TAG[m], len(set(cells) & want), len(want), len(miss),
                    ("  DUPLICATES %s" % dups) if dups else ""))
        return 1 if bad else 0

    if args.dry_run:
        full = plan(arms, args.max_cost, only_missing=False)
        total = print_plan(full, arms, "E8 design plan (every shard, nothing downloaded assumed):")
        if set(arms) == set(ARMS) and total != EXPECTED_TOTAL:
            print("!! design total %d != %d" % (total, EXPECTED_TOTAL))
            return 1
        todo = plan(arms, args.max_cost)
        print("\nstill missing from %s: %d games in %d shards"
              % (DL, sum(s[4] * len(s[2].split(",")) for s in todo), len(todo)))
        gather_hint(arms)
        return 0

    if problems:
        print("STOP: fix the task before launching.")
        return 2
    accounts = [a.strip() for a in args.accounts.split(",") if a.strip()]
    if not accounts:
        print("need --accounts")
        return 2
    from launch_e3b import classify_push_fail  # noqa: E402

    todo = plan(arms, args.max_cost)
    if not todo:
        print("E8: nothing missing.")
        return 0
    print_plan(todo, arms, "E8 missing shards:")
    rnd, fails, parked = 0, defaultdict(int), []
    while todo and rnd < args.max_rounds:
        rnd += 1
        batch, todo = take_batch(todo, accounts, args.model_cap)
        if not batch:
            print("no shard fits the account/user/model caps. STOP.")
            break
        accounts = accounts[len(batch):] + accounts[:len(batch)]
        print("\n=== ROUND %d: %d shards, $%.2f ===" % (rnd, len(batch),
                                                     sum(b[0][5] for b in batch)))
        with ThreadPoolExecutor(max_workers=PUSH_CONC) as pool:
            pushed = list(pool.map(lambda b: (b, one(b[0], b[1], "push", args.wait)), batch))
        ok = [b for b, rc in pushed if rc == 0]
        if not ok and len(pushed) > 1:
            print("  !! all %d pushes failed at once -> infrastructure; wait %ds"
                  % (len(pushed), args.net_wait))
            todo = [b[0] for b, _ in pushed] + todo
            time.sleep(args.net_wait)
            rnd -= 1
            continue
        retry = []
        for (sh, acc), rc in pushed:
            if rc == 0:
                continue
            lab = label(sh[0], sh[1], sh[3], sh[2])
            cause = classify_push_fail(lab)
            if cause == "busy":
                retry.append(sh)
                continue
            fails[lab] += 1
            if cause == "shard" or fails[lab] >= 2:
                print("  !! %s failed (%s, %d times) -> parked" % (lab, cause, fails[lab]))
                parked.append(sh)
            else:
                print("  %s: drop account %s, shard back in the queue" % (cause, acc))
                accounts = [a for a in accounts if a != acc]
                retry.append(sh)
        todo = retry + todo
        if not ok:
            print("no push succeeded. STOP.")
            break
        with ThreadPoolExecutor(max_workers=len(ok)) as pool:
            ran = list(pool.map(lambda b: (b, one(b[0], b[1], "run", args.wait)), ok))
        bad = [label(b[0][0], b[0][1], b[0][3], b[0][2]) for b, rc in ran if rc != 0]
        if bad:
            print("  run failed (%d): %s -> rerun this command" % (len(bad), " ".join(bad)))
        if not accounts:
            print("out of accounts. STOP.")
            break
    for sh in parked:
        print("  parked: " + label(sh[0], sh[1], sh[3], sh[2]))
    gather_hint(arms)
    return 0


if __name__ == "__main__":
    sys.exit(main())
