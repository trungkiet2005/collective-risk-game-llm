"""Ngày B theo 2 PHA — pha push ít song song, pha run song song hết.

Vì sao phải tách: `kaggle b t push` chạy 1 ván validate trên model MẶC ĐỊNH của server
(gemini-3-flash-preview). N lệnh push đồng thời đập vào CÙNG model đó → 429 heavy load →
validate Errored → push hủy. Thực tế 12/15 shard Ngày B chết kiểu này khi phóng song song
với stagger 20s, và không shard nào chạy được ván nào.

Pha 1 (push): tối đa PUSH_CONC lệnh push cùng lúc, có retry. Chậm nhưng chắc.
Pha 2 (run) : phóng toàn bộ run song song — `run` KHÔNG dùng model mặc định nên không
              đập vào nhau như push.

Dùng:
    python plan/scripts/stage_day_b.py --phase push
    python plan/scripts/stage_day_b.py --phase run
    python plan/scripts/stage_day_b.py --phase push --only grok
"""
import argparse
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from launch_day_b import SHARDS, label_of, cost_of, n_games   # noqa: E402

REPO = Path(__file__).resolve().parents[2]
LAUNCH = REPO / "plan" / "scripts" / "launch_shard.py"
PUSH_CONC = 3          # >3 la bat dau 429 lan nhau o buoc validate


def one(shard, phase, wait):
    acc, model, risks, langs, reps, start = shard
    label = label_of(acc, model, risks, langs, start)
    cmd = [sys.executable, str(LAUNCH), "--account", acc, "--model", model,
           "--risks", risks, "--langs", langs, "--reps", reps,
           "--rep-start", start, "--label", label,
           f"--{phase}-only"]
    if phase == "run":
        cmd += ["--wait", wait]
    logf = REPO / "plan" / "runs" / f"{label}.{phase}.log"
    logf.parent.mkdir(parents=True, exist_ok=True)
    with open(logf, "w", encoding="utf-8") as fh:
        rc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT,
                            cwd=str(REPO)).returncode
    print(f"  {phase:<5} {label:<58} rc={rc}", flush=True)
    return label, rc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["push", "run"], required=True)
    ap.add_argument("--only", default=None)
    ap.add_argument("--wait", default="21600")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    shards = [s for s in SHARDS
              if not args.only or args.only in s[0] or args.only in s[1]]
    print(f"PHA {args.phase.upper()} · {len(shards)} shard · "
          f"{sum(n_games(s) for s in shards)} van · ~${sum(cost_of(s) for s in shards):.2f}")
    if args.phase == "push":
        print(f"  push toi da {PUSH_CONC} cung luc (>3 la 429 lan nhau o buoc validate)")
    if args.dry_run:
        for s in shards:
            print("  " + label_of(s[0], s[1], s[2], s[3], s[5]))
        return 0

    t0 = time.time()
    conc = PUSH_CONC if args.phase == "push" else len(shards)
    with ThreadPoolExecutor(max_workers=conc) as pool:
        results = list(pool.map(lambda s: one(s, args.phase, args.wait), shards))

    fails = [lab for lab, rc in results if rc != 0]
    mins = (time.time() - t0) / 60
    print(f"\nPHA {args.phase.upper()} xong sau {mins:.0f} phut · "
          f"{len(results) - len(fails)}/{len(results)} OK")
    if fails:
        print(f"LOI ({len(fails)}):")
        for f in fails:
            print(f"  {f}")
        print("Chay lai dung pha nay cho cac shard do (script tu retry 3 lan moi push).")
        return 1
    nxt = "run" if args.phase == "push" else None
    if nxt:
        print(f"\nTiep: python plan/scripts/stage_day_b.py --phase {nxt}")
    else:
        print("\nGom: python plan/scripts/merge_shards.py "
              "--src plan/runs D:/tmp/crgdl --out results/frontier")
    return 0


if __name__ == "__main__":
    sys.exit(main())
