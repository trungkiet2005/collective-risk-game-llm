"""Wave E1 (exp_nohint) + E2 (EV probe) — 12 shard, 2 PHA.

E1  bo mo neo equal-split  : CRG_TEMPLATE=nohint      -> exp_nohint
E2  probe so sanh EV       : CRG_PROBE=rules,value    -> exp_baseline_probe-rules-value

Ca hai: 3 risk (0.9/0.5/0.1) x 10 rep = 30 van/model x 5 model. LUAT CAN BANG (§7):
so van GIONG HET nhau cho ca 5 model; gia chi duoc anh huong toi cach CHIA SHARD.
haiku dat gap 23x qwen -> haiku chia doi theo rep, cac model khac 1 shard.

HAI PHA — dung phong song song ca hai (xem stage_day_b.py):
    python plan/scripts/launch_wave_e12.py --dry-run
    python plan/scripts/launch_wave_e12.py --phase push
    python plan/scripts/launch_wave_e12.py --phase run

Gom ket qua (chu y --experiment: to_wide_csv lay ten experiment tu thu muc cha, va
thu muc cua E2 la exp_baseline_probe-rules-value chu khong phai exp_evprobe):
    python plan/scripts/to_wide_csv.py --src plan/runs D:/tmp/crgdl
    python plan/scripts/verify_wide.py --expect-reps 10
"""
import argparse
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LAUNCH = REPO / "plan" / "scripts" / "launch_shard.py"

RISKS = "0.9,0.5,0.1"
LANGS = "en"          # CHI TIENG ANH (§5.1)
N_RISKS = 3
CONCURRENCY = 4
MAX_OUT = 3000        # phu DUOI phan bo, khong phu trung binh (CLAUDE.md)

PUSH_CONC = 3         # >3 la push tu choi im lang o buoc validate

# $/van DO THAT tu smoke 10-09-2026, cell 0.9/en.
COST = {
    "qwen3-235b-a22b-instruct-2507": 0.0078,
    "grok-4.20-0309-non-reasoning": 0.0230,
    "gemini-3.5-flash-lite": 0.0327,
    "gpt-5.6-luna": 0.0787,
    "claude-haiku-4-5-20251001": 0.1780,
}
# CRG_PROBE=rules,value = 30 cau/van tren 60 quyet dinh -> 1.50x (docstring task).
PROBE_MULT = 1.50

# (wave, model, account, reps, rep_start)
# 10-09-2026: trunkdabest (e1 luna) va acc5 (e2 luna) HET QUOTA -- push validate tra
# 403 "max estimated cost $0.0092 exceeds your available quota" ca 3 lan. Ca hai probe
# XANH truoc do: probe chi tra loi CON/HET key, khong tra loi CON BAO NHIEU. Doi sang
# acc09 / acc11. Giu ghi chu nay de khong giao lai hai account do ma khong probe bang push.
SHARDS = [
    # ---- E1: nohint ----
    ("e1", "claude-haiku-4-5-20251001",     "chisboiz",      5, 0),
    ("e1", "claude-haiku-4-5-20251001",     "chunaiu",       5, 5),
    ("e1", "gpt-5.6-luna",                  "acc09",        10, 0),
    ("e1", "gemini-3.5-flash-lite",         "vinhdinhthien",10, 0),
    ("e1", "grok-4.20-0309-non-reasoning",  "acc1",         10, 0),
    ("e1", "qwen3-235b-a22b-instruct-2507", "acc2",         10, 0),
    # ---- E2: EV probe ----
    ("e2", "claude-haiku-4-5-20251001",     "acc3",          5, 0),
    ("e2", "claude-haiku-4-5-20251001",     "acc4",          5, 5),
    ("e2", "gpt-5.6-luna",                  "acc11",        10, 0),
    ("e2", "gemini-3.5-flash-lite",         "acc06",        10, 0),
    ("e2", "grok-4.20-0309-non-reasoning",  "acc07",        10, 0),
    ("e2", "qwen3-235b-a22b-instruct-2507", "acc08",        10, 0),
]

WAVE = {
    "e1": {"task": "crg-e1-nohint",  "flag": ("--template", "nohint")},
    "e2": {"task": "crg-e2-evprobe", "flag": ("--probe", "rules,value")},
}


def short(model):
    return model.replace("-instruct", "").replace("-20251001", "")[:22]


def label(wave, model, rep_start):
    return f"{wave}_{short(model)}_s{rep_start:02d}"


def n_games(sh):
    return sh[3] * N_RISKS


def cost(sh):
    wave, model, _, reps, _ = sh
    c = reps * N_RISKS * COST[model]
    return c * PROBE_MULT if wave == "e2" else c


def one(sh, phase, wait):
    wave, model, account, reps, rep_start = sh
    lab = label(wave, model, rep_start)
    cmd = [sys.executable, str(LAUNCH),
           "--account", account, "--model", model,
           "--risks", RISKS, "--langs", LANGS,
           "--reps", str(reps), "--rep-start", str(rep_start),
           "--max-out", str(MAX_OUT), "--concurrency", str(CONCURRENCY),
           "--task", WAVE[wave]["task"], "--label", lab,
           f"--{phase}-only"]
    cmd += list(WAVE[wave]["flag"])
    if phase == "run":
        cmd += ["--wait", wait]
    logf = REPO / "plan" / "runs" / f"{lab}.{phase}.log"
    logf.parent.mkdir(parents=True, exist_ok=True)
    with open(logf, "w", encoding="utf-8") as fh:
        rc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT,
                            cwd=str(REPO)).returncode
    print(f"  {phase:<5} {lab:<34} {account:<14} rc={rc}", flush=True)
    return lab, rc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["push", "run"])
    ap.add_argument("--only", default=None, help="loc theo wave/model/account")
    ap.add_argument("--wait", default="21600")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    shards = [s for s in SHARDS
              if not args.only or args.only in s[0] or args.only in s[1]
              or args.only in s[2]]

    print(f"{len(shards)} shard · {sum(n_games(s) for s in shards)} van · "
          f"~${sum(cost(s) for s in shards):.2f}")
    if args.dry_run or not args.phase:
        for s in shards:
            print(f"  {label(s[0], s[1], s[4]):<34} {s[2]:<14} "
                  f"{n_games(s):>3} van  ${cost(s):>5.2f}")
        # Cong bang: moi model phai co DUNG cung so van trong moi wave.
        for wave in ("e1", "e2"):
            per = {}
            for s in shards:
                if s[0] == wave:
                    per[s[1]] = per.get(s[1], 0) + n_games(s)
            if per:
                ok = len(set(per.values())) == 1
                print(f"  can bang {wave}: {sorted(set(per.values()))} "
                      f"{'OK' if ok else '!! LECH'}")
        return 0

    t0 = time.time()
    conc = PUSH_CONC if args.phase == "push" else len(shards)
    print(f"PHA {args.phase.upper()} · {conc} luong song song")
    with ThreadPoolExecutor(max_workers=conc) as pool:
        results = list(pool.map(lambda s: one(s, args.phase, args.wait), shards))

    fails = [lab for lab, rc in results if rc != 0]
    print(f"\nPHA {args.phase.upper()} xong sau {(time.time()-t0)/60:.0f} phut · "
          f"{len(results)-len(fails)}/{len(results)} OK")
    for f in fails:
        print(f"  LOI: {f}  -> xem plan/runs/{f}.{args.phase}.log")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
