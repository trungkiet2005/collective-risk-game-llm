"""Q8 — hai muc rui ro TRUNG GIAN p = 0.3 va 0.7 (reviewer, Interface Focus).

Cau hoi reviewer:
    "Have you tested additional intermediate risk levels (e.g. p = 0.3, 0.7) to probe
     whether the two step-function models truly pivot at EV = 0.5 or if small
     hysteresis/noise exists around the threshold?"

Diem ban le EV nam DUNG o p = 0.5: gop du phan minh -> chac chan giu 20; bo mac -> ky
vong (1-p)*40, bang 20 khi p = 0.5. Luoi ba muc hien co (0.1/0.5/0.9) khong noi duoc
hai model EV xoay dung o 0.5 hay dau do lan can. Hai muc moi kep chat ban le:
    p = 0.3 -> bo mac van hon (28 > 20)
    p = 0.7 -> hop tac da hon (12 < 20)

CHAY (2 PHA — dung phong song song ca hai, xem stage_day_b.py de biet vi sao):
    python plan/scripts/launch_q8.py --dry-run
    python plan/scripts/launch_q8.py --phase push
    python plan/scripts/launch_q8.py --phase run
    python plan/scripts/merge_shards.py --src plan/runs D:/tmp/crgdl --out results/frontier

CHIA SHARD: tran $10/account la rang buoc cung. Gia/van do that o Ngay A/B, nhan he so
cell (risk thap dat hon vi model sinh nhieu token hon). Cell 0.3 duoc uoc theo he so
1.50 (noi suy giua 0.5 = 1.02 va 0.1 = 2.02); cell 0.7 theo 1.01. opus-5 o 0.3 uoc
$8.8/10 van -> qua sat tran, nen chia doi 5+5 tren hai account.

TIENG ANH THOI. Cau hoi cua reviewer la ve vi tri ban le, va cot "Δ risk (en)" cua
paper la tieng Anh. Them tieng Viet se gap doi chi phi ma khong tra loi them gi.
"""
import argparse
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LAUNCH = REPO / "plan" / "scripts" / "launch_shard.py"
PUSH_CONC = 3          # >3 la cac lenh push 429 lan nhau o buoc validate

# $/van o cell moc 0.9/en, do that trong dot 13-08-2026.
COST = {
    "gemini-3.1-pro-preview": 0.419,
    "gpt-5.6-sol": 0.250,
    "claude-opus-5-default": 0.585,
    "grok-4.20-0309-reasoning": 0.100,
}
# He so gia theo muc risk (tieng Anh). 0.9 = 1.00 (moc), 0.5 = 1.02, 0.1 = 2.02 do
# that; 0.7 va 0.3 noi suy tuyen tinh giua chung.
RISK_MULT = {"0.9": 1.00, "0.7": 1.01, "0.5": 1.02, "0.3": 1.50, "0.1": 2.02}

# (account, model, risks, langs, reps, rep_start, max_out)
# max_out=None -> de task tu chon (6000 cho model reasoning). opus-5 tung tra content
# RONG o cap 6000 nen ep 16000, dung cap da dung o dot FILL Ngay B.
SHARDS = [
    # --- BAT BUOC: hai model choi dung EV. Day la cau tra loi cho Q8. ---
    ("acc1",          "gemini-3.1-pro-preview", "0.3", "en", "10", "0", None),
    ("acc2",          "gemini-3.1-pro-preview", "0.7", "en", "10", "0", None),
    ("acc3",          "gpt-5.6-sol",            "0.3", "en", "10", "0", None),
    ("acc4",          "gpt-5.6-sol",            "0.7", "en", "10", "0", None),
    # --- DOI CHUNG: hai model bac dinh phang. Cho biet hai muc moi co lam
    #     chung dong day khong, hay chung phang xuyen suot nhu o 3 muc cu. ---
    ("acc5",          "claude-opus-5-default",  "0.3", "en", "5",  "0", "16000"),
    ("chiboiz",       "claude-opus-5-default",  "0.3", "en", "5",  "5", "16000"),
    ("chinguyentran", "claude-opus-5-default",  "0.7", "en", "10", "0", "16000"),
    ("chisboiz",      "grok-4.20-0309-reasoning", "0.3,0.7", "en", "10", "0", None),
]


def n_games(s):
    return len(s[2].split(",")) * len(s[3].split(",")) * int(s[4])


def cost_of(s):
    base = COST[s[1]]
    mult = max(RISK_MULT.get(r, 1.5) for r in s[2].split(","))
    return n_games(s) * base * mult


def label_of(s):
    account, model, risks, langs, _, rep_start, _ = s
    return (f"Q8__{account}__{model}__r{risks.replace(',', '-')}"
            f"__l{langs.replace(',', '-')}__s{rep_start}")


def one(shard, phase, wait):
    account, model, risks, langs, reps, rep_start, max_out = shard
    label = label_of(shard)
    cmd = [sys.executable, str(LAUNCH), "--account", account, "--model", model,
           "--risks", risks, "--langs", langs, "--reps", reps,
           "--rep-start", rep_start, "--label", label, f"--{phase}-only"]
    if max_out:
        cmd += ["--max-out", max_out]
    if phase == "run":
        cmd += ["--wait", wait]
    logf = REPO / "plan" / "runs" / f"{label}.{phase}.log"
    logf.parent.mkdir(parents=True, exist_ok=True)
    with open(logf, "w", encoding="utf-8") as fh:
        rc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT,
                            cwd=str(REPO)).returncode
    print(f"  {phase:<5} {label:<62} rc={rc}", flush=True)
    return label, rc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["push", "run"])
    ap.add_argument("--only", default=None,
                    help="loc theo account hoac model, vd --only gemini")
    ap.add_argument("--wait", default="21600")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    shards = [s for s in SHARDS
              if not args.only or args.only in s[0] or args.only in s[1]]
    total_games = sum(n_games(s) for s in shards)
    total_cost = sum(cost_of(s) for s in shards)
    print(f"Q8 · {len(shards)} shard · {total_games} van · ~${total_cost:.2f}")
    for s in shards:
        print(f"  {label_of(s):<62} {n_games(s):>3} van  ~${cost_of(s):5.2f}")
    over = [s for s in shards if cost_of(s) > 9.0]
    if over:
        print(f"\nCANH BAO: {len(over)} shard uoc > $9 — sat tran $10/account:")
        for s in over:
            print(f"  {label_of(s)}  ~${cost_of(s):.2f}")

    if args.dry_run or not args.phase:
        if not args.phase:
            print("\nChua chon --phase. Chay: --phase push  roi  --phase run")
        return 0

    if args.phase == "push":
        print(f"\npush toi da {PUSH_CONC} cung luc (>3 la 429 lan nhau o buoc validate)")

    t0 = time.time()
    conc = PUSH_CONC if args.phase == "push" else len(shards)
    with ThreadPoolExecutor(max_workers=conc) as pool:
        results = list(pool.map(lambda s: one(s, args.phase, args.wait), shards))

    fails = [lab for lab, rc in results if rc != 0]
    mins = (time.time() - t0) / 60
    print(f"\nPHA {args.phase.upper()} xong sau {mins:.0f} phut · "
          f"{len(results) - len(fails)}/{len(results)} OK")
    for f in fails:
        print("  LOI:", f)
    if args.phase == "push" and not fails:
        print("\nTiep: python plan/scripts/launch_q8.py --phase run")
    if args.phase == "run":
        print("\nGom: python plan/scripts/merge_shards.py "
              "--src plan/runs D:/tmp/crgdl --out results/frontier")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
