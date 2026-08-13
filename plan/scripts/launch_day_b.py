"""Ngày B — `claude-opus-5` + `grok-4.20-non-reasoning`, phóng song song mỗi shard 1 account.

Khác Ngày A: opus-5 chia theo risk×lang×NỬA REP (5 ván/shard) chứ không 10 ván/shard.
Lý do là bài học đo được ở Ngày A: giá/ván KHÔNG suy ra được giữa các cell — cell
risk 0.1 + tiếng Việt đắt gấp ~2× cell risk 0.9 + tiếng Anh (gemini-3.1-pro:
$0.419/ván ở 0.9/en lên $0.864/ván ở 0.1/vn). Với opus-5 smoke $0.585/ván ở 0.9/en thì
cell 0.1/vn có thể ~$1.17/ván → shard 10 ván = $11.7, VỠ trần $10/account.

Dùng:
    python plan/scripts/launch_day_b.py --dry-run
    python plan/scripts/launch_day_b.py
    python plan/scripts/launch_day_b.py --only grok
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LAUNCH = REPO / "plan" / "scripts" / "launch_shard.py"

# $/ván đo thật. opus-5 từ smoke Ngày A (risk 0.9/en); nhân hệ số cell để ước
# worst case. grok-non-reasoning: cập nhật sau smoke Ngày B.
# Giá cơ sở = $/ván ở cell 0.9/en (mốc). Cả hai ĐO THẬT:
#   opus-5: smoke Ngày A 0.9/en = $0.585/ván; smoke Ngày B 0.1/vn = $1.40289/ván -> mult 2.40
#   grok-non-reasoning: smoke Ngày B 0.1/vn = $0.040894/ván -> base = 0.0409/2.40 = 0.0170
#   (grok-non RE HON 3.5x ban reasoning $0.142 — dung nhu du doan: khong sinh reasoning token)
COST = {
    "claude-opus-5-default": 0.585,
    "grok-4.20-0309-non-reasoning": 0.0170,
}
# Hệ số giá theo cell, đo từ Ngày A (gemini-3.1-pro & gpt-5.6-sol):
#   0.9/en = 1.0 (mốc) · 0.9/vn ≈ 1.45 · 0.5/en ≈ 1.02 · 0.5/vn ≈ 1.45
#   0.1/en ≈ 1.73 · 0.1/vn ≈ 2.06
# HIEU CHINH sau smoke Ngày B: opus-5 0.1/vn do duoc 2.40x (khong phai 2.06x) -> nang
# ca hai cell risk 0.1 len theo ti le en/vn = 0.84 giu tu gemini.
CELL_MULT = {("0.9", "en"): 1.00, ("0.9", "vn"): 1.45,
             ("0.5", "en"): 1.02, ("0.5", "vn"): 1.45,
             ("0.1", "en"): 2.02, ("0.1", "vn"): 2.40}

# (account, model, risks, langs, reps, rep_start)
SHARDS = [
    # grok-4.20-non-reasoning: 3 shard × 20 ván, chia theo risk. Rẻ nên không cần
    # chia nhỏ hơn. Đối chứng với bản reasoning (null hoàn hảo +0.2) — cùng model
    # gốc, chỉ tắt reasoning.
    ("tnkiet",        "grok-4.20-0309-non-reasoning", "0.9", "en,vn", "10", "0"),
    ("chinguyentran", "grok-4.20-0309-non-reasoning", "0.5", "en,vn", "10", "0"),
    ("chisboiz",      "grok-4.20-0309-non-reasoning", "0.1", "en,vn", "10", "0"),
    # claude-opus-5: 12 shard × 5 ván (risk × lang × nửa rep).
    ("chunaiu",       "claude-opus-5-default", "0.9", "en", "5", "0"),
    ("trunkdabest",   "claude-opus-5-default", "0.9", "en", "5", "5"),
    ("vinhdinhthien", "claude-opus-5-default", "0.9", "vn", "5", "0"),
    ("acc1",          "claude-opus-5-default", "0.9", "vn", "5", "5"),
    ("acc2",          "claude-opus-5-default", "0.5", "en", "5", "0"),
    ("acc3",          "claude-opus-5-default", "0.5", "en", "5", "5"),
    ("acc4",          "claude-opus-5-default", "0.5", "vn", "5", "0"),
    ("acc5",          "claude-opus-5-default", "0.5", "vn", "5", "5"),
    ("trungkiet",     "claude-opus-5-default", "0.1", "en", "5", "0"),
    ("foundnotkiet",  "claude-opus-5-default", "0.1", "en", "5", "5"),
    ("kit567",        "claude-opus-5-default", "0.1", "vn", "5", "0"),
    ("hunhtrungkit",  "claude-opus-5-default", "0.1", "vn", "5", "5"),
]
SAFE_LIMIT = 8.0        # $/shard: dưới mức này thì kể cả lệch thêm vẫn không vỡ $10


def n_games(s):
    return len(s[2].split(",")) * len(s[3].split(",")) * int(s[4])


def cost_of(s):
    base = COST[s[1]]
    mult = max(CELL_MULT.get((r, l), 1.0)
               for r in s[2].split(",") for l in s[3].split(","))
    return n_games(s) * base * mult


def label_of(account, model, risks, langs, rep_start):
    return (f"{account}__{model}__r{risks.replace(',', '-')}"
            f"__l{langs.replace(',', '-')}__s{rep_start}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default=None)
    ap.add_argument("--wait", default="21600")
    # 150s, KHONG 20s: `push` chay 1 van validate tren model mac dinh cua server, nen
    # nhieu push dong thoi dap vao cung model do -> 429 -> validate Errored -> push huy.
    # Voi stagger 20s thi 7/15 shard Ngay B chet kieu nay.
    ap.add_argument("--stagger", type=int, default=150)
    args = ap.parse_args()

    shards = [s for s in SHARDS
              if not args.only or args.only in s[0] or args.only in s[1]]
    print(f"{len(shards)} shard · {sum(n_games(s) for s in shards)} van · "
          f"~${sum(cost_of(s) for s in shards):.2f} (uoc worst-case theo cell)\n")
    over = []
    for s in shards:
        acc, model, risks, langs, reps, start = s
        c = cost_of(s)
        flag = ""
        if c > SAFE_LIMIT:
            flag = f"  <-- ${c:.2f} > ${SAFE_LIMIT}, chia nho hon!"
            over.append(acc)
        print(f"  {acc:<15} {model:<30} r={risks:<8} l={langs:<6} "
              f"rep {start}..{int(start) + int(reps) - 1}  {n_games(s):>2} van  "
              f"${c:>5.2f}{flag}")
    if over:
        print(f"\n!! {len(over)} shard vuot nguong an toan: {over}")
        return 2
    if args.dry_run:
        print("\n--dry-run: khong phong gi.")
        return 0

    procs = []
    logdir = REPO / "plan" / "runs"
    logdir.mkdir(parents=True, exist_ok=True)
    for acc, model, risks, langs, reps, start in shards:
        label = label_of(acc, model, risks, langs, start)
        cmd = [sys.executable, str(LAUNCH), "--account", acc, "--model", model,
               "--risks", risks, "--langs", langs, "--reps", reps,
               "--rep-start", start, "--wait", args.wait, "--label", label]
        fh = open(logdir / f"{label}.driver.log", "w", encoding="utf-8")
        p = subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT, cwd=str(REPO))
        procs.append((label, p, fh))
        print(f"phong {label} (pid {p.pid})")
        time.sleep(args.stagger)

    print(f"\nDa phong {len(procs)} shard. Theo doi: python plan/scripts/check_runs.py")
    fails = []
    for label, p, fh in procs:
        rc = p.wait()
        fh.close()
        print(f"  {label}: rc={rc}")
        if rc != 0:
            fails.append(label)
    if fails:
        print(f"\n{len(fails)} shard LOI: {fails}")
        return 1
    print("\nXong. Gom: python plan/scripts/merge_shards.py "
          "--src plan/runs D:/tmp/crgdl --out results/frontier")
    return 0


if __name__ == "__main__":
    sys.exit(main())
