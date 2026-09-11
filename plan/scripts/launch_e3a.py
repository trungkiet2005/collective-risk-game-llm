"""E3a — best-response: 1 ghe LLM giua 5 ghe scripted (§7.3).

Chi ghe P1 goi proxy, 5 ghe con lai la chinh sach tat dinh khong ton mot lenh goi nao
-> 10 lenh goi/van thay vi 60, re gap 6. Va vi doi thu la BIET TRUOC chinh xac, cau
"model co duy ly khong" tro thanh mot con so do duoc tung o: khoang cach toi best
response.

Bon profile (§7.3), best response cua LLM neu duy ly:

    defect  always_0               mot minh khong the dat target -> BO MAC o moi p
    coop    always_2               nhom dat 100 ma khong can minh -> gop 20 o p cao,
                                   free-ride o p thap
    carry   always_4               nhom dat 200 chac chan -> LUON GOP 0. Day la bay
                                   sac nhat: gop them mot xu nao cung la lo thuan, nen
                                   model nao van gop deu o day thi khong he dang choi
                                   game, no dang tuan theo huong dan trong prompt.
    cond    conditional_cooperator khop trung binh vong truoc -> co anh huong, dang dau tu

Luoi: 5 risk {0.1,0.3,0.5,0.7,0.9} x 10 rep x 4 profile = 200 van/model, deu nhau ca 5
model (luat can bang §7).

MOI PROFILE MOT TASK RIENG (`crg-e3a-<profile>`) nen shard cua hai profile khong bao gio
de len nhau, va thu muc output cung tach san vi seat tag di vao ten thu muc.

    python plan/scripts/launch_e3a.py --smoke --accounts acc1     # 1 van, kiem ghe scripted
    python plan/scripts/launch_e3a.py --dry-run
    python plan/scripts/launch_e3a.py --accounts a,b,c
"""
import argparse
import csv
import glob
import os
import subprocess
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fill_wave_e12 import COST, TAG2SLUG, runs  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
LAUNCH = REPO / "plan" / "scripts" / "launch_shard.py"
DL = "D:/tmp/crgdl"
PUSH_CONC = 3

RISKS = ("0.1", "0.3", "0.5", "0.7", "0.9")
REPS = 10
SIX = 6.0            # chi 1/6 ghe goi API -> chi phi/van bang 1/6 van thuong

PROFILES = {
    "defect": "always_0",
    "coop": "always_2",
    "carry": "always_4",
    "cond": "conditional_cooperator",
}


def seat_spec(profile):
    """P1 la model duoc chon, 5 ghe con lai deu la chinh sach cua profile."""
    return "self," + ",".join(f"scripted:{PROFILES[profile]}" for _ in range(5))


def task_of(profile):
    return f"crg-e3a-{profile}"


def have():
    """(profile, slug) -> {risk: set(rep)} da tai ve."""
    got = defaultdict(lambda: defaultdict(set))
    for f in glob.glob(f"{DL}/*/crg-e3a-*/**/games.csv", recursive=True):
        profile = next((p for p in PROFILES if f"crg-e3a-{p}" in f), None)
        if profile is None:
            continue
        with open(f, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                tag = r.get("model") or r.get("model_tag")
                got[(profile, TAG2SLUG.get(tag, tag))][r["risk_probability"]].add(
                    int(r["rep"]))
    return got


def missing_shards():
    """[(profile, slug, risks, rep_start, n, $)] — re truoc.

    `risks` la MOT CHUOI co the nhieu muc ("0.1,0.3,..."): `launch_shard.py` nhan ca
    danh sach, nen cac muc risk cung thieu DUNG mot dai rep duoc gom vao MOT shard.
    Khong gom thi mot model chua chay gi se thanh 5 shard 10 van thay vi 1 shard 50
    van — tuc la can 5 account thay vi 1, va account moi la thu dang hiem chu khong
    phai tien.
    """
    got, out = have(), []
    for profile in PROFILES:
        for slug in sorted(set(TAG2SLUG.values())):
            d = got.get((profile, slug), {})
            by_run = defaultdict(list)          # (start, n) -> [risk, ...]
            for p in RISKS:
                for start, n in runs(set(range(REPS)) - d.get(p, set())):
                    by_run[(start, n)].append(p)
            for (start, n), ps in sorted(by_run.items()):
                out.append((profile, slug, ",".join(ps), start, n,
                            n * len(ps) * COST[slug] / SIX))
    return sorted(out, key=lambda s: s[5])


def label(sh):
    profile, slug, p, start, _, _ = sh
    ps = p.replace(",", "-") if p.count(",") < 2 else f"x{p.count(',')+1}"
    return f"e3a_{profile}_{slug[:18]}_p{ps}_s{start:02d}"


def one(sh, account, phase, wait):
    profile, slug, p, start, n, _ = sh
    lab = label(sh)
    cmd = [sys.executable, str(LAUNCH), "--account", account, "--model", slug,
           "--risks", p, "--langs", "en", "--reps", str(n),
           "--rep-start", str(start), "--max-out", "3000", "--concurrency", "4",
           "--task", task_of(profile), "--seat-models", seat_spec(profile),
           "--label", lab, f"--{phase}-only"]
    if phase == "run":
        cmd += ["--wait", wait]
    logf = REPO / "plan" / "runs" / f"{lab}.{phase}.log"
    logf.parent.mkdir(parents=True, exist_ok=True)
    with open(logf, "w", encoding="utf-8") as fh:
        rc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT,
                            cwd=str(REPO)).returncode
    print(f"  {phase:<5} {lab:<44} {account:<14} rc={rc}", flush=True)
    return rc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--accounts", default=None, help="cach nhau bang dau phay")
    ap.add_argument("--wait", default="21600")
    ap.add_argument("--max-rounds", type=int, default=4)
    ap.add_argument("--smoke", action="store_true",
                    help="1 van (carry, p=0.9, rep 0) de kiem ghe scripted chay that")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.smoke:
        sh = ("carry", "gemini-3.5-flash-lite", "0.9", 0, 1,
              COST["gemini-3.5-flash-lite"] / SIX)
        acc = (args.accounts or "").split(",")[0]
        if not acc:
            print("--smoke can --accounts <mot account>")
            return 2
        print(f"SMOKE: {label(sh)} tren {acc}\n  seats = {seat_spec('carry')}")
        if args.dry_run:
            return 0
        if one(sh, acc, "push", args.wait) != 0:
            print("push hong -> account het quota hoac file shard sai. DUNG.")
            return 1
        return one(sh, acc, "run", args.wait)

    shards = missing_shards()
    if not shards:
        print("E3a: khong thieu o nao.")
        return 0
    print(f"E3a: thieu {sum(s[4]*len(s[2].split(',')) for s in shards)} van · "
          f"{len(shards)} shard · "
          f"~${sum(s[5] for s in shards):.2f}")
    per = defaultdict(int)
    for s in shards:
        per[s[1]] += s[4] * len(s[2].split(","))
    for slug, n in sorted(per.items()):
        print(f"  {slug:<34} thieu {n:>3} van")
    if args.dry_run:
        return 0
    if not args.accounts:
        print("Can --accounts")
        return 2

    accounts = [a.strip() for a in args.accounts.split(",") if a.strip()]
    todo, rnd = list(shards), 0
    while todo and rnd < args.max_rounds:
        rnd += 1
        batch = [(todo.pop(0), accounts[i]) for i in range(min(len(accounts), len(todo)))]
        print(f"\n=== DOT {rnd}: {len(batch)} shard ===\nPHA PUSH")
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=PUSH_CONC) as pool:
            pushed = list(pool.map(lambda b: (b, one(b[0], b[1], "push", args.wait)),
                                   batch))
        ok = [b for b, rc in pushed if rc == 0]
        dead = [b[1] for b, rc in pushed if rc != 0]
        print(f"push {len(ok)}/{len(batch)} OK sau {(time.time()-t0)/60:.0f} phut")
        if dead:
            print(f"  het quota (loai): {' '.join(dead)}")
            accounts = [a for a in accounts if a not in dead]
        todo = [b[0] for b, rc in pushed if rc != 0] + todo
        if not ok:
            print("Khong account nao con quota. DUNG.")
            break
        print("PHA RUN")
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=len(ok)) as pool:
            ran = list(pool.map(lambda b: (b, one(b[0], b[1], "run", args.wait)), ok))
        print(f"run {sum(1 for _, rc in ran if rc == 0)}/{len(ok)} OK sau "
              f"{(time.time()-t0)/60:.0f} phut")
        if not accounts:
            break

    print("\nKiem lai: python plan/scripts/launch_e3a.py --dry-run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
