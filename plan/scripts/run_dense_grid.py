#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Phong sweep LUOI RISK DAY cho panel AAMAS (5 model, tieng Anh).

Thiet ke:
  - 11 muc risk: 0, 0.1, ..., 0.9, 1.0  (gom ca hai dau mut p=0 va p=1)
  - 30 rep / cell, tieng Anh
  - 5 model, 330 van/model, 1650 van tong

Chia shard theo REP (dung --rep-start cua launch_shard.py) sao cho KHONG shard nao
cham tran $10/account. Moi shard mot account rieng -> khong dung task name.

Chay 2 PHA (bat buoc, khong duoc phong song song kieu Ngay A):
  push  : toi da 3 luc, vi `kaggle b t push` bi TU CHOI IM LANG (rc=1, output rong,
          ~3 giay) neu version truoc con dang validate.
  run   : phong song song thoai mai.

Dung:
  python plan/scripts/run_dense_grid.py --phase push
  python plan/scripts/run_dense_grid.py --phase run
  python plan/scripts/run_dense_grid.py --phase download
  python plan/scripts/run_dense_grid.py --status
  python plan/scripts/run_dense_grid.py --phase push --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LAUNCH = REPO / "plan" / "scripts" / "launch_shard.py"
STATE = REPO / "plan" / "runs" / "_dense_grid_state.json"
# Ghim ban task DA QUA SMOKE 10-09-2026 (parse_fail=0 tren ca 4 model, p=0 sach).
# File goc dang bi sua song song bo E0 -> khong duoc sinh shard tu no.
TASK_SRC = REPO / "kaggle" / "benchmarks" / "crg_task_server_v1_smoked.py"

RISKS = "0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0"
N_RISKS = 11
LANGS = "en"

# Gia/van DO THAT tu smoke 10-09-2026 (2 van/model, p=0.9 + p=0).
COST = {
    "qwen3-235b-a22b-instruct-2507": 0.0078,
    "grok-4.20-0309-non-reasoning": 0.0230,
    "gemini-3.5-flash-lite": 0.0327,
    "gpt-5.6-luna": 0.0787,
    "claude-haiku-4-5-20251001": 0.1780,   # cap 3000
}
# Giay/van DO THAT tu smoke (concurrency=1).
SECS = {
    "qwen3-235b-a22b-instruct-2507": 32,
    "grok-4.20-0309-non-reasoning": 60,
    "gemini-3.5-flash-lite": 61,
    "gpt-5.6-luna": 135,
    "claude-haiku-4-5-20251001": 313,
}

# Song song hoa 6 ghe trong 1 vong. KHONG doi chi phi, chi giam wall-clock ~3.5x.
# Output byte-identical voi duong tuan tu (ThreadPoolExecutor.map giu thu tu input).
CONCURRENCY = 4
SPEEDUP = 3.0     # do that: haiku 626.5s -> 207.5s cho 2 van

# Cap output/quyet dinh. Mac dinh cua task: 6000 neu model co "reasoning hint",
# nguoc lai 512. Do that 10-09: haiku sinh 476 tok/quyet dinh -> cap 512 cat cut
# ~1-3% quyet dinh, va parse_contribution KHONG bao loi khi do (no quet chu so bua
# trong van ban roi tra parse_failed=False). Nang cap len 3000 gan nhu mien phi
# ($0.1765 -> $0.178/van). qwen sinh 8 tok/quyet dinh, grok tuong tu -> khong can.
MAX_OUT = {"claude-haiku-4-5-20251001": 3000}

# 14 ACCOUNT SONG (probe 10-09-2026). chiboiz + chinguyentran auth 403 "chua verify
# danh tinh" -> LOAI. trnnguynchis da bi loai tu truoc, cung ly do.
#
# (model, account, reps, rep_start). Hai rang buoc:
#   - cost/shard < $10  (tran budget/account/ngay)
#   - 1 shard / account (2 shard cung account dung chung ten task -> dung do)
# Rep phan bo NGHICH voi gia: model re duoc lay mau nhieu hon, vi do chinh xac
# mua duoc bang tien re hon. n/cell: haiku 24, luna 36, flash-lite 44, grok 31, qwen 90.
PLAN = [
    # haiku dat nhat ($0.1765/van) -> 6 shard, moi shard sat tran
    ("claude-haiku-4-5-20251001", "chisboiz",      4,  0),
    ("claude-haiku-4-5-20251001", "chunaiu",       4,  4),
    ("claude-haiku-4-5-20251001", "trunkdabest",   4,  8),
    ("claude-haiku-4-5-20251001", "vinhdinhthien", 4, 12),
    ("claude-haiku-4-5-20251001", "acc1",          4, 16),
    ("claude-haiku-4-5-20251001", "acc2",          4, 20),
    # luna -> 4 shard
    ("gpt-5.6-luna",              "acc3",          9,  0),
    ("gpt-5.6-luna",              "acc4",          9,  9),
    ("gpt-5.6-luna",              "acc5",          9, 18),
    ("gpt-5.6-luna",              "trungkiet",     9, 27),
    # flash-lite -> 2 shard
    ("gemini-3.5-flash-lite",     "foundnotkiet", 22,  0),
    ("gemini-3.5-flash-lite",     "kit567",       22, 22),
    # re nhat -> lay mau day nhat
    ("grok-4.20-0309-non-reasoning",  "hunhtrungkit", 31, 0),
    ("qwen3-235b-a22b-instruct-2507", "tnkiet",       90, 0),
]

MAX_PUSH_CONCURRENT = 3   # vuot la push bi tu choi im lang
MAX_RUN_CONCURRENT = 14


def short(model: str) -> str:
    return model.replace("-instruct", "").replace("-20251001", "")[:22]


def label(model: str, rep_start: int) -> str:
    return f"dg_{short(model)}_s{rep_start:02d}"


def shards():
    out = []
    for model, account, reps, rep_start in PLAN:
        games = reps * N_RISKS
        out.append({
            "label": label(model, rep_start),
            "model": model,
            "account": account,
            "reps": reps,
            "rep_start": rep_start,
            "games": games,
            "cost": round(games * COST[model], 2),
            "hours": round(games * SECS[model] / SPEEDUP / 3600.0, 1),
        })
    return out


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {}


def save_state(st):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, indent=2, sort_keys=True), encoding="utf-8")


def run_one(sh, phase, wait, dry):
    args = [
        sys.executable, str(LAUNCH),
        "--account", sh["account"],
        "--model", sh["model"],
        "--risks", RISKS,
        "--langs", LANGS,
        "--reps", str(sh["reps"]),
        "--rep-start", str(sh["rep_start"]),
        "--label", sh["label"],
        "--wait", str(wait),
        "--concurrency", str(CONCURRENCY),
    ]
    if sh["model"] in MAX_OUT:
        args += ["--max-out", str(MAX_OUT[sh["model"]])]
    if phase == "push":
        args.append("--push-only")
    elif phase == "run":
        args.append("--run-only")
    elif phase == "download":
        args.append("--download-only")

    if dry:
        return sh["label"], 0, " ".join(args)

    env = dict(os.environ)
    env["CRG_TASK_SRC"] = str(TASK_SRC)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    t0 = time.time()
    p = subprocess.run(args, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    dt = int(time.time() - t0)
    tail = (p.stdout or "")[-600:] + (p.stderr or "")[-600:]
    return sh["label"], p.returncode, f"[{dt}s] {tail}"


def do_phase(phase, dry, only=None, retries=1):
    sh_all = shards()
    if only:
        sh_all = [s for s in sh_all if s["label"] in only]
    st = load_state()
    todo = [s for s in sh_all if st.get(s["label"], {}).get(phase) != "ok"]

    if not todo:
        print(f"[{phase}] tat ca da xong.")
        return 0

    cap = MAX_PUSH_CONCURRENT if phase == "push" else MAX_RUN_CONCURRENT
    wait = 1800 if phase == "push" else 21600
    print(f"[{phase}] {len(todo)} shard, toi da {cap} luc, wait={wait}s")

    failed = []
    with ThreadPoolExecutor(max_workers=cap) as ex:
        futs = {ex.submit(run_one, s, phase, wait, dry): s for s in todo}
        for f in as_completed(futs):
            s = futs[f]
            lbl, rc, out = f.result()
            ok = (rc == 0)
            if not dry:      # dry-run KHONG duoc ghi state, neu khong push that se bo qua het
                st.setdefault(lbl, {})[phase] = "ok" if ok else f"rc={rc}"
                st[lbl]["model"] = s["model"]
                st[lbl]["account"] = s["account"]
                st[lbl]["games"] = s["games"]
                st[lbl]["cost_est"] = s["cost"]
                save_state(st)
            print(f"  {'OK ' if ok else 'ERR'} {lbl:28s} {out[:200]}")
            if not ok:
                failed.append(s)

    if failed and retries > 0 and not dry:
        print(f"\n[{phase}] thu lai {len(failed)} shard hong (con {retries} luot)...")
        time.sleep(60)
        return do_phase(phase, dry, only=[s["label"] for s in failed], retries=retries - 1)

    return len(failed)


def show_status():
    st = load_state()
    sh = shards()
    print(f"{'shard':30s} {'model':24s} {'acc':14s} {'van':>5s} {'$':>6s} {'gio':>5s}  push  run   dl")
    print("-" * 105)
    tc = tg = 0.0
    for s in sh:
        r = st.get(s["label"], {})
        tc += s["cost"]; tg += s["games"]
        print(f"{s['label']:30s} {short(s['model']):24s} {s['account']:14s} "
              f"{s['games']:5d} {s['cost']:6.2f} {s['hours']:5.1f}  "
              f"{r.get('push','-'):5s} {r.get('run','-'):5s} {r.get('download','-'):5s}")
    print("-" * 105)
    print(f"{'TONG':30s} {'':24s} {'':14s} {int(tg):5d} {tc:6.2f}")
    per_model = {}
    for s in sh:
        per_model.setdefault(s["model"], [0, 0.0])
        per_model[s["model"]][0] += s["games"]
        per_model[s["model"]][1] += s["cost"]
    print("\nTheo model:")
    for m, (g, c) in sorted(per_model.items(), key=lambda kv: -kv[1][1]):
        print(f"  {short(m):26s} {g:5d} van  ${c:7.2f}")
    mx = max(s["hours"] for s in sh)
    print(f"\nShard lau nhat: {mx:.1f} gio (wall-clock du kien neu chay song song het)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["push", "run", "download"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--only", nargs="*", help="chi chay cac label nay")
    a = ap.parse_args()

    if a.status or not a.phase:
        show_status()
        return 0
    if not TASK_SRC.exists():
        raise SystemExit(f"Khong thay task snapshot: {TASK_SRC}")
    return do_phase(a.phase, a.dry_run, only=a.only)


if __name__ == "__main__":
    sys.exit(main())
