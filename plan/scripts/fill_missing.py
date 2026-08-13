"""Chạy lại ĐÚNG các cell còn thiếu sau một đợt shard, không chạy lại cả sweep.

Đọc `results/frontier/<tag>/exp_baseline/games.csv` để biết cell nào đã có, rồi gom các
cell thiếu thành shard liên tiếp theo (risk, lang, khoảng rep) và chạy tiếp.

Vì sao cần: run có thể chết giữa đường mà vẫn để lại data một phần. Ngày B: 15/15 shard
báo rc=0 nhưng `opus-5` chỉ có 44/60 ván (16 cell thiếu ĐỀU là tiếng Việt — cap 6000
không đủ, model trả content rỗng) và `grok-non` 43/60.

Dùng:
    python plan/scripts/fill_missing.py --dry-run
    python plan/scripts/fill_missing.py --phase push
    python plan/scripts/fill_missing.py --phase run
"""
import argparse
import itertools
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
LAUNCH = REPO / "plan" / "scripts" / "launch_shard.py"
FRONTIER = REPO / "results" / "frontier"

RISKS, LANGS, REPS = [0.9, 0.5, 0.1], ["en", "vn"], range(10)

# model_tag -> (slug dùng cho -m, cap max_completion_tokens khi chạy lại)
# opus-5 nâng 6000 -> 16000: 16/16 cell thiếu đều là tiếng Việt, tức prompt VN dài hơn
# làm phần suy luận vượt cap và model trả content RỖNG (guard chặn -> run Errored).
TARGETS = {
    "anthropic-claude-opus-5-default": ("claude-opus-5-default", "16000"),
    "xai-grok-4.20-0309-non-reasoning": ("grok-4.20-0309-non-reasoning", "8000"),
}
# Account dùng để chạy bù. Quota nạp lại mỗi ngày nên dùng lại được.
POOL = ["chiboiz", "chinguyentran", "chisboiz", "chunaiu", "trunkdabest",
        "vinhdinhthien", "acc1", "acc2", "acc3", "acc4", "acc5",
        "trungkiet", "foundnotkiet", "kit567", "hunhtrungkit", "tnkiet"]
CONC = 3          # chạy ít song song: quá tải là nguyên nhân content rỗng


def missing_runs(tag):
    """Trả về [(risk, lang, rep_start, n_reps)] gom từ các cell thiếu."""
    f = FRONTIER / tag / "exp_baseline" / "games.csv"
    have = set()
    if f.is_file():
        d = pd.read_csv(f)
        have = {(round(float(r.risk_probability), 2), r.language, int(r.rep))
                for r in d.itertuples()}
    miss = sorted(set(itertools.product(RISKS, LANGS, REPS)) - have)
    by_cell = defaultdict(list)
    for r, l, p in miss:
        by_cell[(r, l)].append(p)
    out = []
    for (r, l), reps in sorted(by_cell.items(), key=lambda x: (-x[0][0], x[0][1])):
        reps.sort()
        start = prev = reps[0]
        for p in reps[1:] + [None]:            # cắt thành các đoạn rep liên tiếp
            if p != prev + 1:
                out.append((r, l, start, prev - start + 1))
                start = p
            prev = p if p is not None else prev
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["push", "run"], default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--wait", default="21600")
    args = ap.parse_args()

    jobs = []
    for tag, (slug, max_out) in TARGETS.items():
        for risk, lang, start, n in missing_runs(tag):
            jobs.append((slug, max_out, f"{risk}", lang, str(start), str(n)))

    if not jobs:
        print("Khong con cell nao thieu.")
        return 0
    if len(jobs) > len(POOL):
        print(f"!! {len(jobs)} shard nhung chi co {len(POOL)} account.")
        return 2

    print(f"{len(jobs)} shard bu · {sum(int(j[5]) for j in jobs)} van\n")
    for acc, j in zip(POOL, jobs):
        slug, max_out, risk, lang, start, n = j
        print(f"  {acc:<15} {slug:<30} risk={risk:<4} lang={lang}  "
              f"rep {start}..{int(start) + int(n) - 1}  {n:>2} van  cap={max_out}")
    if args.dry_run or not args.phase:
        print("\n(chi xem; them --phase push roi --phase run de chay)")
        return 0

    def one(pair):
        acc, (slug, max_out, risk, lang, start, n) = pair
        label = f"FILL__{acc}__{slug}__r{risk}__l{lang}__s{start}"
        cmd = [sys.executable, str(LAUNCH), "--account", acc, "--model", slug,
               "--risks", risk, "--langs", lang, "--reps", n,
               "--rep-start", start, "--max-out", max_out, "--label", label,
               f"--{args.phase}-only"]
        if args.phase == "run":
            cmd += ["--wait", args.wait]
        logf = REPO / "plan" / "runs" / f"{label}.{args.phase}.log"
        logf.parent.mkdir(parents=True, exist_ok=True)
        with open(logf, "w", encoding="utf-8") as fh:
            rc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT,
                                cwd=str(REPO)).returncode
        print(f"  {args.phase:<5} {label:<62} rc={rc}", flush=True)
        return label, rc

    pairs = list(zip(POOL, jobs))
    conc = CONC if args.phase == "push" else len(pairs)
    with ThreadPoolExecutor(max_workers=conc) as pool:
        res = list(pool.map(one, pairs))
    bad = [l for l, rc in res if rc != 0]
    print(f"\nPHA {args.phase.upper()}: {len(res) - len(bad)}/{len(res)} OK")
    for l in bad:
        print(f"  LOI {l}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
