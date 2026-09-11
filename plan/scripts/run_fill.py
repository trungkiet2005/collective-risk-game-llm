"""Chay bu cac o con thieu cua E1/E2, theo TUNG DOT, tren nhung account con quota.

Khac `launch_wave_e12.py` (phong ca luoi tu dau), script nay lay danh sach o thieu tu
`fill_wave_e12.py` -- tuc la doc data DA co tren dia -- nen khong bao gio choi lai mot o
da tra tien. Quan trong vi chay lai mot o cho ra QUAN SAT MOI chu khong phai ban sao
(proxy khong tai lap van ban theo seed), nen choi lai la tron hai run vao nhau.

MOT ACCOUNT = MOT SHARD MOI DOT. Hai shard cung account dung chung ten task -> dung do.
Nhieu shard hon account thi chia lam nhieu dot, moi dot push (3 luong) roi run (song song).

Buoc `push` chinh la phep do quota re nhat va dung nhat: no dat coc ~$0,009 tren model
mac dinh cua server, nen account gan can 403 ngay tai do va that bai khong ton gi.
`probe_quota.py` chi phan biet duoc duoi/tren ~$0,03 nen KHONG thay the duoc buoc nay.

    python plan/scripts/run_fill.py --wave e1 --accounts a,b,c --dry-run
    python plan/scripts/run_fill.py --wave e1 --accounts a,b,c
"""
import argparse
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fill_wave_e12 import (COST, PROBE_MULT, REPS, RISKS, TAG2SLUG,  # noqa: E402
                           WAVE_FLAG, WAVE_TASK, have, runs)

REPO = Path(__file__).resolve().parents[2]
LAUNCH = REPO / "plan" / "scripts" / "launch_shard.py"
PUSH_CONC = 3


def missing_shards(wave):
    """[(wave, slug, risk, rep_start, n, $)] — re truoc de mot dot ngan tien it nhat."""
    got = have()
    out = []
    for slug in sorted(set(TAG2SLUG.values())):
        d = got.get((wave, slug), {})
        for p in RISKS:
            for start, n in runs(set(range(REPS)) - d.get(p, set())):
                c = n * COST[slug] * (PROBE_MULT if wave == "e2" else 1)
                out.append((wave, slug, p, start, n, c))
    return sorted(out, key=lambda s: s[5])


def label(sh):
    wave, slug, p, start, n, _ = sh
    return f"fill_{wave}_{slug[:18]}_p{p}_s{start:02d}"


def one(sh, account, phase, wait):
    wave, slug, p, start, n, _ = sh
    lab = label(sh)
    cmd = [sys.executable, str(LAUNCH), "--account", account, "--model", slug,
           "--risks", p, "--langs", "en", "--reps", str(n),
           "--rep-start", str(start), "--max-out", "3000", "--concurrency", "4",
           "--task", WAVE_TASK[wave], "--label", lab, f"--{phase}-only"]
    cmd += WAVE_FLAG[wave].split()
    if phase == "run":
        cmd += ["--wait", wait]
    logf = REPO / "plan" / "runs" / f"{lab}.{phase}.log"
    logf.parent.mkdir(parents=True, exist_ok=True)
    with open(logf, "w", encoding="utf-8") as fh:
        rc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT,
                            cwd=str(REPO)).returncode
    print(f"  {phase:<5} {lab:<40} {account:<14} rc={rc}", flush=True)
    return rc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wave", choices=["e1", "e2"], required=True)
    ap.add_argument("--accounts", required=True, help="cach nhau bang dau phay")
    ap.add_argument("--wait", default="21600")
    ap.add_argument("--max-rounds", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    accounts = [a.strip() for a in args.accounts.split(",") if a.strip()]
    shards = missing_shards(args.wave)
    if not shards:
        print(f"{args.wave}: khong thieu o nao.")
        return 0

    print(f"{args.wave}: thieu {sum(s[4] for s in shards)} van · {len(shards)} shard · "
          f"~${sum(s[5] for s in shards):.2f} · {len(accounts)} account")
    for sh in shards:
        print(f"  {label(sh):<40} {sh[4]:>3} van  ${sh[5]:>5.2f}")
    if args.dry_run:
        return 0

    todo, rnd = list(shards), 0
    while todo and rnd < args.max_rounds:
        rnd += 1
        batch = [(todo.pop(0), accounts[i]) for i in range(min(len(accounts), len(todo)))]
        print(f"\n=== DOT {rnd}: {len(batch)} shard ===")

        print("PHA PUSH (push validate = phep do quota; 403 o day khong ton tien)")
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=PUSH_CONC) as pool:
            pushed = list(pool.map(lambda b: (b, one(b[0], b[1], "push", args.wait)),
                                   batch))
        ok = [b for b, rc in pushed if rc == 0]
        dead = [b[1] for b, rc in pushed if rc != 0]
        print(f"push {len(ok)}/{len(batch)} OK sau {(time.time()-t0)/60:.0f} phut")
        if dead:
            print(f"  het quota (loai khoi cac dot sau): {' '.join(dead)}")
            accounts = [a for a in accounts if a not in dead]
        # Shard cua account chet quay lai hang doi, chua chay gi nen chua ton dong nao.
        todo = [b[0] for b, rc in pushed if rc != 0] + todo
        if not ok:
            print("Khong account nao con quota. DUNG.")
            break

        print("PHA RUN")
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=len(ok)) as pool:
            ran = list(pool.map(lambda b: (b, one(b[0], b[1], "run", args.wait)), ok))
        n_ok = sum(1 for _, rc in ran if rc == 0)
        print(f"run {n_ok}/{len(ok)} OK sau {(time.time()-t0)/60:.0f} phut")
        # Shard chay do (403 giua chung) se tu hien lai o lan tinh missing_shards sau.
        if not accounts:
            break

    print("\nKiem lai con thieu gi:")
    print("  python plan/scripts/fill_wave_e12.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
