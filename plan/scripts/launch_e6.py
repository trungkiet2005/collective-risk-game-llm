"""E6 -- robustness: hai ban paraphrase + mot nhanh temperature 0.

Tra loi dung mot cau hoi cua reviewer: "ket qua nay co phai artifact cua cach ban dien
dat prompt, hoac cua cach ban giai ma khong?" (W6 va W7 trong so rui ro). Ba nhanh chay
lai DUNG hai o then chot cua luoi B:

    p = 0.1  va  p = 0.9

Vi sao dung hai muc do, khong phai hai muc bat ky: luan diem chinh cua paper la hop tac
KHONG phu thuoc rui ro, nen phep thu phai danh vao dung hai diem ma EV doi hanh vi trai
NGUOC nhau (p* = 0.5 la diem bang quan). Neu hop tac van phang giua 0.1 va 0.9 duoi ca
hai cach dien dat va ca o temperature 0, thi luan diem song; neu no gay o day, no gay o
cho de thay nhat.

Ba nhanh, moi nhanh 2 risk x 10 rep = 20 van/model, 5 model = 300 van:

    para1   CRG_TEMPLATE=para1      -> results/exp_para1/
    para2   CRG_TEMPLATE=para2      -> results/exp_para2/
    temp0   CRG_TEMPERATURE=0       -> results/exp_baseline_temp0/

Nhanh thu tu, them 17-09-2026 theo review AAMAS (mot reviewer hoi: "hop tac co phai chi la
lam theo chu 'must' trong prompt?"). Nhanh nay co TAP RISK RIENG, vi phep thu habit sach
nhat nam o p = 0 (dong gop o do bi troi hoan toan):

    neutral CRG_TEMPLATE=neutral    -> results/exp_neutral/   p = 0, 0.1, 0.9

    python plan/scripts/launch_e6.py --arms neutral --dry-run

Nhanh temp0 choi DUNG prompt baseline, nen neu khong co TEMP_SUFFIX no se ghi thang vao
results/exp_baseline/ va tron vao chinh cai luoi ma no phai duoc so sanh voi. Hau to do
nam trong crg_task_server.py; test hoi quy: crsd/tests/test_e6_robustness.py.

CAN crg_task_server.py da co ho tro E6 (TEMPLATE para1/para2 + CRG_TEMPERATURE) va
launch_shard.py da co co --temperature. Chay --dry-run truoc, no se noi neu thieu.

    python plan/scripts/launch_e6.py --dry-run
    python plan/scripts/launch_e6.py --accounts acc1,acc2,...

Nhu launch_e3b.py: tu tinh o CON THIEU tu data DA TAI VE, nen chay lai lenh nay bao
nhieu lan cung duoc -- no khong bao gio chay lai mot o da co.
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
# Dung CHUNG bo quy ket voi launch_e3b.py, khong chep lai: mot ban sao thu hai
# se troi lech, va day la cho quyet dinh co vut mot account con tien hay khong.
# Do that 12-09-2026: quy ket mu quang lam mat 2 account khoe trong MOT dot.
from launch_e3b import classify_push_fail  # noqa: E402
LAUNCH = REPO / "plan" / "scripts" / "launch_shard.py"
DL = "D:/tmp/crgdl"

RISKS = ["0.1", "0.9"]        # hai dau doi nghich cua luoi B -- xem docstring
# Nhanh nao khong co trong day thi dung RISKS.
ARM_RISKS = {"neutral": ["0", "0.1", "0.9"]}
LANGS = "en"                  # CHI TIENG ANH (§5.1)
REPS = 10
CONCURRENCY = "4"
MAX_OUT = "3000"              # phu DUOI phan bo, khong phu trung binh (CLAUDE.md)
PUSH_CONC = 3                 # >3 la push bi tu choi im lang o buoc validate
MODEL_CAP = 8                 # >8 request dong thoi vao mot model = bao 429

# Slug tran de truyen cho `-m`. Bang dong nhat: ca 6 ghe deu la model nay.
MODELS = [
    "qwen3-235b-a22b-instruct-2507",
    "grok-4.20-0309-non-reasoning",
    "gemini-3.5-flash-lite",
    "gpt-5.6-luna",
    "claude-haiku-4-5-20251001",
]
# Tag chuan hoa nhu no xuat hien trong cot `model` cua games.csv.
TAG = {
    "qwen3-235b-a22b-instruct-2507": "qwen-qwen3-235b-a22b-instruct-2507",
    "grok-4.20-0309-non-reasoning": "xai-grok-4.20-0309-non-reasoning",
    "gemini-3.5-flash-lite": "google-gemini-3.5-flash-lite",
    "gpt-5.6-luna": "openai-gpt-5.6-luna",
    "claude-haiku-4-5-20251001": "anthropic-claude-haiku-4-5-20251001",
}
SHORT = {
    "qwen3-235b-a22b-instruct-2507": "qwen",
    "grok-4.20-0309-non-reasoning": "grok",
    "gemini-3.5-flash-lite": "flash",
    "gpt-5.6-luna": "luna",
    "claude-haiku-4-5-20251001": "haiku",
}
# $/van DO THAT (smoke 10-09-2026, cell 0.9/en). Ban dong nhat 6 ghe.
COST = {
    "qwen3-235b-a22b-instruct-2507": 0.0078,
    "grok-4.20-0309-non-reasoning": 0.0230,
    "gemini-3.5-flash-lite": 0.0327,
    "gpt-5.6-luna": 0.0787,
    "claude-haiku-4-5-20251001": 0.1780,
}
PUSH_VALIDATE_COST = 0.10     # buoc validate chay mot van that

# arm -> (task kaggle, co truyen cho launch_shard.py, hau to trong game_id)
ARMS = {
    "para1": ("crg-e6-para1", ["--template", "para1"], "_para1"),
    "para2": ("crg-e6-para2", ["--template", "para2"], "_para2"),
    "temp0": ("crg-e6-temp0", ["--temperature", "0"], "_temp0"),
    "neutral": ("crg-e6-neutral", ["--template", "neutral"], "_neutral"),
}


def risks_of(arm):
    return ARM_RISKS.get(arm, RISKS)


def label(arm, model, rep_start):
    return "e6_%s_%s_s%02d" % (arm, SHORT[model], rep_start)


def have():
    """(arm, model_tag) -> {risk: set(rep)} da tai ve.

    Doc `game_id` de biet NHANH, khong doc ten thu muc: mot task E6 duoc day len nhieu
    account khac nhau va ten thu muc chi mang ten task, con `game_id` mang hau to that
    su do server sinh ra -- tuc la mang dung cai nhanh da CHOI, khong phai cai nhanh ta
    dinh choi. Hai thu do lech nhau la loai loi im lang dat nhat o day.
    """
    got = defaultdict(lambda: defaultdict(set))
    for f in glob.glob("%s/**/crg-e6-*/**/games.csv" % DL, recursive=True):
        if "crg-e6-smoke" in f:
            continue
        with open(f, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                gid = r.get("game_id") or ""
                arm = next((a for a, (_, _, sfx) in ARMS.items() if sfx in gid), None)
                if arm is None:
                    continue
                got[(arm, r["model"])][r["risk_probability"]].add(int(r["rep"]))
    return got


def missing_shards(max_cost, arms=None):
    """[(arm, model, rep_start, n, $)] -- re truoc.

    Chia theo REP chu khong theo risk: mot shard luon chay ca hai muc risk cho cung mot
    dai rep, nen moi shard tu no da can bang tren truc risk. Neu chia theo risk thi mot
    shard chet se lam lech luoi va cong can bang no sau khi da tieu tien.
    """
    got = have()
    out = []
    for arm in (arms or ARMS):
        for m in MODELS:
            done = got.get((arm, TAG[m]), {})
            # rep con thieu o BAT KY muc risk nao -> phai chay lai ca rep do.
            # games.csv ghi risk dang float ("0.0", "0.1"), nen so bang float.
            done_f = {float(k): v for k, v in done.items()}
            need = sorted(r for r in range(REPS)
                          if any(r not in done_f.get(float(p), set())
                                 for p in risks_of(arm)))
            if not need:
                continue
            per_rep = COST[m] * len(risks_of(arm))
            step = max(1, int(max_cost // per_rep) if per_rep else len(need))
            # gom cac rep lien tiep thanh lo, giu nguyen thu tu
            i = 0
            while i < len(need):
                lot = need[i:i + step]
                # `--rep-start` + `--reps` la mot DAI lien tuc, nen chi gom duoc khi
                # cac rep lien nhau; cat lo tai cho dut quang.
                cut = 1
                while cut < len(lot) and lot[cut] == lot[cut - 1] + 1:
                    cut += 1
                lot = lot[:cut]
                out.append((arm, m, lot[0], len(lot),
                            len(lot) * per_rep + PUSH_VALIDATE_COST))
                i += len(lot)
    out.sort(key=lambda s: s[4])
    return out


def take_batch(todo, n_slots, cap):
    """Chon shard cho MOT dot sao cho khong model nao vuot tran tai.

    Ban dong nhat nen mot shard = `CONCURRENCY` request vao DUNG MOT model (khac E3b,
    noi moi shard danh vao hai model). Tran 8 do that: 16 request dong thoi vao cung
    mot model lam 2/4 shard chet sau 72 giay.
    """
    load, batch, rest = defaultdict(int), [], []
    for sh in todo:
        m = sh[1]
        if len(batch) >= n_slots or load[m] + int(CONCURRENCY) > cap:
            rest.append(sh)
            continue
        load[m] += int(CONCURRENCY)
        batch.append(sh)
    return batch, rest


def one(sh, account, phase, wait):
    arm, model, rep_start, n, _ = sh
    task, flag, _ = ARMS[arm]
    lab = label(arm, model, rep_start)
    cmd = [sys.executable, str(LAUNCH), "--account", account, "--model", model,
           "--risks", ",".join(risks_of(arm)), "--langs", LANGS,
           "--reps", str(n), "--rep-start", str(rep_start),
           "--max-out", MAX_OUT, "--concurrency", CONCURRENCY,
           "--task", task, "--label", lab,
           # Mot cu 429 thoang qua khong duoc lam mat ca shard (do that o wave E3b:
           # 'abort' vut 27/30 van chua chay vi mot loi o van thu 4).
           "--on-game-error", "skip",
           "--%s-only" % phase]
    cmd += flag
    if phase == "run":
        cmd += ["--wait", wait]
    logf = REPO / "plan" / "runs" / ("%s.%s.log" % (lab, phase))
    logf.parent.mkdir(parents=True, exist_ok=True)
    with open(logf, "w", encoding="utf-8") as fh:
        rc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT,
                            cwd=str(REPO)).returncode
    print("  %-5s %-30s %-14s rc=%d" % (phase, lab, account, rc), flush=True)
    return rc


def preflight():
    """Khong cho phong khi thiet bi chua san sang -- re, va chay truoc moi dong nao."""
    bad = []
    srv = (REPO / "kaggle" / "benchmarks" / "crg_task_server.py").read_text(
        encoding="utf-8", errors="replace")
    if '"neutral"' not in srv or "FRAMING_VARIANTS" not in srv:
        bad.append("crg_task_server.py CHUA co template neutral -- nhanh neutral se bi "
                   "tu choi luc import (CRG_TEMPLATE la)")
    if '"para1"' not in srv or "TEMP_SUFFIX" not in srv:
        bad.append("crg_task_server.py CHUA co ho tro E6 (thieu template para1/para2 "
                   "hoac TEMP_SUFFIX) -- nhanh temp0 se ghi de len results/exp_baseline/")
    sh = LAUNCH.read_text(encoding="utf-8", errors="replace")
    if "--temperature" not in sh:
        bad.append("launch_shard.py CHUA co co --temperature -- nhanh temp0 se chay o "
                   "0.7 va lang le tra ve mot ban sao cua baseline")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--accounts", default="")
    ap.add_argument("--wait", default="21600")
    ap.add_argument("--max-rounds", type=int, default=12)
    ap.add_argument("--net-wait", type=int, default=300)
    ap.add_argument("--model-cap", type=int, default=MODEL_CAP)
    ap.add_argument("--max-cost", type=float, default=3.0)
    ap.add_argument("--arms", default="",
                    help="chi xet cac nhanh nay, vd 'neutral'. Mac dinh: moi nhanh")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    arms = [a.strip() for a in args.arms.split(",") if a.strip()] or list(ARMS)
    unknown = [a for a in arms if a not in ARMS]
    if unknown:
        print("Nhanh la: %s (co: %s)" % (unknown, ", ".join(ARMS)))
        return 2

    for msg in preflight():
        print("!! " + msg)
    if preflight() and not args.dry_run:
        print("DUNG. Sua thiet bi truoc khi phong.")
        return 2

    shards = missing_shards(args.max_cost, arms)
    if not shards:
        print("E6: khong thieu o nao.")
        return 0
    n_games = sum(s[3] * len(risks_of(s[0])) for s in shards)
    print("E6: thieu %d van · %d shard · ~$%.2f"
          % (n_games, len(shards), sum(s[4] for s in shards)))
    per = defaultdict(int)
    for arm, m, _, n, _ in shards:
        per[SHORT[m]] += n * len(risks_of(arm))
    print("     van con thieu, theo model: "
          + "  ".join("%s=%d" % (k, v) for k, v in sorted(per.items())))
    per_arm = defaultdict(int)
    for arm, _, _, n, _ in shards:
        per_arm[arm] += n * len(risks_of(arm))
    print("     theo nhanh: "
          + "  ".join("%s=%d" % (k, v) for k, v in sorted(per_arm.items())))
    if args.dry_run:
        for s in shards:
            print("       %-30s $%.2f" % (label(s[0], s[1], s[2]), s[4]))
        return 0

    accounts = [a.strip() for a in args.accounts.split(",") if a.strip()]
    if not accounts:
        print("Can --accounts")
        return 2

    todo, rnd, acc_ptr = list(shards), 0, 0
    fails = defaultdict(int)
    parked = []
    while todo and rnd < args.max_rounds:
        rnd += 1
        picked, todo = take_batch(todo, len(accounts), args.model_cap)
        if not picked:
            print("Khong shard nao lot duoi tran tai/model. DUNG.")
            break
        # XOAY account: tran tai/model cat moi dot xuong it shard, nen lay accounts[i]
        # se doc mot nhum account nho gong het wave roi chet vi 403 giua chung.
        batch = [(sh, accounts[(acc_ptr + i) % len(accounts)])
                 for i, sh in enumerate(picked)]
        acc_ptr = (acc_ptr + len(picked)) % len(accounts)
        print("\n=== DOT %d: %d shard, $%.2f ==="
              % (rnd, len(batch), sum(b[0][4] for b in batch)))
        print("PHA PUSH")
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=PUSH_CONC) as pool:
            pushed = list(pool.map(lambda b: (b, one(b[0], b[1], "push", args.wait)),
                                   batch))
        ok = [b for b, rc in pushed if rc == 0]
        print("push %d/%d OK sau %.0f phut" % (len(ok), len(batch),
                                               (time.time() - t0) / 60))

        # TOAN BO dot hong cung luc thi thu pham KHONG phai quota -- quota can theo tung
        # account, khong the lam ca dot hong trong cung mot giay. Do that 11-09-2026:
        # mat DNS lam ca 5 auth hong trong 2 giay va mot ban truoc cua vong lap nay da
        # loai sach 5 account khoe roi dung wave.
        if not ok and len(pushed) > 1:
            print("  !! CA %d/%d shard hong cung luc -> HA TANG, khong loai account nao."
                  % (len(pushed), len(pushed)))
            print("     doi %ds roi thu lai dot nay." % args.net_wait)
            todo = [b[0] for b, _ in pushed] + todo
            time.sleep(args.net_wait)
            rnd -= 1
            continue

        retry = []
        for b, rc in pushed:
            if rc == 0:
                continue
            sh, acc = b
            lab = label(sh[0], sh[1], sh[2])
            cause = classify_push_fail(lab)
            # 429/503/DNS: thoang qua o phia proxy hoac Kaggle, account van con tien.
            if cause == "busy":
                print("  proxy/ha tang ban (%s tren %s) -> giu account, shard tra ve "
                      "hang doi" % (lab, acc))
                retry.append(sh)
                continue
            fails[lab] += 1
            if cause == "shard" or fails[lab] >= 2:
                print("  !! %s hong (%s, lan %d) -> LOI O SHARD, park lai"
                      % (lab, cause, fails[lab]))
                parked.append(sh)
            else:
                print("  %s: loai %s (shard %s tra ve hang doi)" % (cause, acc, lab))
                accounts = [a for a in accounts if a != acc]
                retry.append(sh)
        todo = retry + todo
        if not ok:
            print("Khong shard nao push duoc. DUNG.")
            break
        print("PHA RUN")
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=len(ok)) as pool:
            ran = list(pool.map(lambda b: (b, one(b[0], b[1], "run", args.wait)), ok))
        bad = [label(b[0][0], b[0][1], b[0][2]) for b, rc in ran if rc != 0]
        print("run %d/%d OK sau %.0f phut"
              % (sum(1 for _, rc in ran if rc == 0), len(ok), (time.time() - t0) / 60))
        if bad:
            print("  run hong (%d): %s" % (len(bad), " ".join(bad)))
            print("  -> chay lai chinh lenh nay; --dry-run liet ke o con thieu")
        if not accounts:
            print("Het account. DUNG.")
            break

    if parked:
        print("\n!! %d shard bi park (hong tren >=2 account khac nhau):" % len(parked))
        for sh in parked:
            print("   " + label(sh[0], sh[1], sh[2]))

    print("\nGom ket qua (--src HEP, khong bao gio quet ca plan/runs):")
    print("  python plan/scripts/to_wide_csv.py --src D:/tmp/crgdl/*/crg-e6-*")
    print("  python plan/scripts/verify_wide.py --expect-reps 10")
    return 0


if __name__ == "__main__":
    sys.exit(main())
