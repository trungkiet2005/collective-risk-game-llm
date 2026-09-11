"""Tinh chinh xac o nao con THIEU cua wave E1/E2 va sinh lenh chay bu.

Vi sao can script rieng thay vi chay lai shard: chay lai mot shard da chay mot phan
se CHOI LAI nhung o da tra tien -- va theo CLAUDE.md, chay lai mot o KHONG cho ket qua
cu ma cho mot QUAN SAT MOI (proxy khong tai lap van ban theo seed). Vay nen phai chi
chay dung nhung (risk, rep) chua co.

Doc data DA TAI VE (D:/tmp/crgdl), doi chieu voi luoi mong doi 3 risk x 10 rep,
roi in ra cac shard con thieu duoi dang day rep LIEN TUC (vi launch_shard.py chi
nhan --rep-start/--reps chu khong nhan tap rep roi rac).

    python plan/scripts/fill_wave_e12.py              # bang thieu + lenh chay
    python plan/scripts/fill_wave_e12.py --accounts acc1,acc2,...   # gan account
"""
import argparse
import csv
import collections
import glob
import os
import sys

DL = "D:/tmp/crgdl"
RISKS = ("0.9", "0.5", "0.1")
REPS = 10
SINCE = 1757500000          # chi lay file cua dot 10-09-2026 tro di

# model_tag trong games.csv -> slug dung cho `kaggle b t run -m`
TAG2SLUG = {
    "anthropic-claude-haiku-4-5-20251001": "claude-haiku-4-5-20251001",
    "google-gemini-3.5-flash-lite": "gemini-3.5-flash-lite",
    "openai-gpt-5.6-luna": "gpt-5.6-luna",
    "qwen-qwen3-235b-a22b-instruct-2507": "qwen3-235b-a22b-instruct-2507",
    "xai-grok-4.20-0309-non-reasoning": "grok-4.20-0309-non-reasoning",
}
COST = {
    "qwen3-235b-a22b-instruct-2507": 0.0078,
    "grok-4.20-0309-non-reasoning": 0.0230,
    "gemini-3.5-flash-lite": 0.0327,
    "gpt-5.6-luna": 0.0787,
    "claude-haiku-4-5-20251001": 0.1780,
}
PROBE_MULT = 1.50
WAVE_TASK = {"e1": "crg-e1-nohint", "e2": "crg-e2-evprobe"}
WAVE_FLAG = {"e1": "--template nohint", "e2": "--probe rules,value"}


def have():
    """(wave, slug) -> {risk: set(rep)} da co tren dia."""
    got = collections.defaultdict(lambda: collections.defaultdict(set))
    for f in glob.glob(f"{DL}/*/crg-e*/**/games.csv", recursive=True):
        if os.path.getmtime(f) < SINCE:
            continue
        wave = "e1" if "crg-e1" in f else "e2"
        with open(f, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                tag = r.get("model") or r.get("model_tag")
                slug = TAG2SLUG.get(tag, tag)
                got[(wave, slug)][r["risk_probability"]].add(int(r["rep"]))
    return got


def runs(missing):
    """Tap rep roi rac -> danh sach day LIEN TUC (start, n)."""
    out, seq = [], sorted(missing)
    i = 0
    while i < len(seq):
        j = i
        while j + 1 < len(seq) and seq[j + 1] == seq[j] + 1:
            j += 1
        out.append((seq[i], seq[j] - seq[i] + 1))
        i = j + 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--accounts", default=None,
                    help="danh sach account de gan lan luot, cach nhau bang dau phay")
    args = ap.parse_args()

    got = have()
    all_slugs = sorted(set(TAG2SLUG.values()))
    shards, total_missing, total_cost = [], 0, 0.0

    print(f"{'wave':<5} {'model':<32} {'0.9':>5} {'0.5':>5} {'0.1':>5}  {'thieu':>6}")
    for wave in ("e1", "e2"):
        for slug in all_slugs:
            d = got.get((wave, slug), {})
            counts, miss_n = [], 0
            for p in RISKS:
                present = d.get(p, set())
                counts.append(len(present))
                missing = set(range(REPS)) - present
                miss_n += len(missing)
                for start, n in runs(missing):
                    c = n * COST[slug] * (PROBE_MULT if wave == "e2" else 1)
                    shards.append((wave, slug, p, start, n, c))
                    total_cost += c
            total_missing += miss_n
            flag = "" if miss_n == 0 else "  <-"
            print(f"{wave:<5} {slug:<32} {counts[0]:>5} {counts[1]:>5} "
                  f"{counts[2]:>5}  {miss_n:>6}{flag}")

    print(f"\nTHIEU {total_missing} van / {2*5*3*REPS} · chay bu ~${total_cost:.2f} · "
          f"{len(shards)} shard")
    if not shards:
        print("Khong thieu gi. Chay to_wide_csv.py + verify_wide.py.")
        return 0

    accts = args.accounts.split(",") if args.accounts else None
    print("\n# Moi dong = 1 shard. Mot account chi chay MOT shard (2 shard cung account")
    print("# dung chung ten task -> dung do). Push toi da 3 luong song song.")
    for i, (wave, slug, p, start, n, c) in enumerate(shards):
        acc = accts[i % len(accts)] if accts else "<ACCOUNT>"
        lab = f"fill_{wave}_{slug[:18]}_p{p}_s{start:02d}"
        print(f"python plan/scripts/launch_shard.py --account {acc} "
              f"--model {slug} --risks {p} --langs en --reps {n} --rep-start {start} "
              f"--max-out 3000 --concurrency 4 --task {WAVE_TASK[wave]} "
              f"{WAVE_FLAG[wave]} --label {lab}   # {n} van ${c:.2f}")
    if accts and len(shards) > len(accts):
        print(f"\n!! CANH BAO: {len(shards)} shard nhung chi {len(accts)} account "
              f"-> co account bi giao 2 shard. Chia lam nhieu dot.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
