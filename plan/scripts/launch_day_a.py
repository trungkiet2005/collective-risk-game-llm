"""Phóng toàn bộ shard của Ngày A song song — mỗi shard một account, một tiến trình.

Mỗi shard gọi launch_shard.py trong tiến trình riêng, ghi log riêng vào
plan/runs/<label>/shard.log. Các shard độc lập nhau (account khác nhau) nên chạy
song song an toàn: tiền cọc proxy chỉ cộng dồn TRONG một account.

Dùng:
    python plan/scripts/launch_day_a.py --dry-run     # xem sẽ chạy gì
    python plan/scripts/launch_day_a.py              # phóng thật
    python plan/scripts/launch_day_a.py --only gemini # chỉ shard khớp chuỗi
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LAUNCH = REPO / "plan" / "scripts" / "launch_shard.py"

# (account, model, risks, langs, reps, $ ước tính)
# chiboiz để trống: dùng cho smoke. Dự phòng còn lại để chạy lại shard lỗi:
# kit567, hunhtrungkit, tnkiet.
# $/ván ĐO THẬT từ smoke server-side 12-08-2026 (1 ván/model, risk 0.9, en):
#   grok-4.20-reasoning 0.141571 | gpt-5.6-sol 0.32409
#   gemini-3.1-pro      0.433008 | claude-opus-5 0.58516  (opus-5 = Ngày B)
# Ước tính cũ lệch: grok đắt hơn 2.45x (probe toàn input -> ước thấp cho model
# reasoning sinh nhiều output), sol đắt hơn 1.34x, pro và opus rẻ hơn ~0.9x.
COST = {
    "grok-4.20-0309-reasoning": 0.141571,
    "gpt-5.6-sol": 0.32409,
    "gemini-3.1-pro-preview": 0.433008,
}

SHARDS = [
    # grok-reasoning: 3 shard x 20 ván = $2.83/shard. Chia 3 thay vì 1 run 60 ván:
    # tiền vẫn vừa ($8.49) nhưng 60 ván tuần tự = ~3600 lượt gọi trên model
    # reasoning -> rủi ro vượt giới hạn thời gian kernel, mà run đứt là mất sạch
    # data shard đó (CRG_RESUME không cứu được qua run).
    ("chinguyentran", "grok-4.20-0309-reasoning", "0.9", "en,vn", "10"),
    ("chisboiz",      "grok-4.20-0309-reasoning", "0.5", "en,vn", "10"),
    ("chunaiu",       "grok-4.20-0309-reasoning", "0.1", "en,vn", "10"),
    # gpt-5.6-sol: 6 shard x 10 ván = $3.24/shard. Ban đầu định 3 shard x 20 ván,
    # nhưng giá thật cao hơn 1.34x -> $6.48/shard = 65% trần, quá sát khi prompt
    # tiếng Việt dài hơn. Chia 6 cho an toàn.
    ("trunkdabest",   "gpt-5.6-sol", "0.9", "en", "10"),
    ("vinhdinhthien", "gpt-5.6-sol", "0.9", "vn", "10"),
    ("acc1",          "gpt-5.6-sol", "0.5", "en", "10"),
    ("acc2",          "gpt-5.6-sol", "0.5", "vn", "10"),
    ("acc3",          "gpt-5.6-sol", "0.1", "en", "10"),
    ("acc4",          "gpt-5.6-sol", "0.1", "vn", "10"),
    # gemini-3.1-pro: 6 shard x 10 ván = $4.33/shard. KHÔNG chia theo lang (30 ván
    # = $12.99) -> vượt trần $10 và run sẽ chết giữa đường.
    ("acc5",          "gemini-3.1-pro-preview", "0.9", "en", "10"),
    ("trungkiet",     "gemini-3.1-pro-preview", "0.9", "vn", "10"),
    ("foundnotkiet",  "gemini-3.1-pro-preview", "0.5", "en", "10"),
    ("kit567",        "gemini-3.1-pro-preview", "0.5", "vn", "10"),
    ("hunhtrungkit",  "gemini-3.1-pro-preview", "0.1", "en", "10"),
    ("tnkiet",        "gemini-3.1-pro-preview", "0.1", "vn", "10"),
]


def label_of(account, model, risks, langs):
    return f"{account}__{model}__r{risks.replace(',', '-')}__l{langs.replace(',', '-')}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default=None, help="chi shard co account/model khop chuoi nay")
    ap.add_argument("--wait", default="21600", help="giay cho moi run (mac dinh 6h)")
    ap.add_argument("--stagger", type=int, default=20,
                    help="giay giua 2 lan phong (tranh dap API cung luc)")
    args = ap.parse_args()

    shards = [s for s in SHARDS
              if not args.only or args.only in s[0] or args.only in s[1]]

    def n_games(s):
        return len(s[2].split(",")) * len(s[3].split(",")) * int(s[4])

    def cost_of(s):
        return n_games(s) * COST[s[1]]

    total_games = sum(n_games(s) for s in shards)
    total_cost = sum(cost_of(s) for s in shards)

    print(f"{len(shards)} shard · {total_games} van · ~${total_cost:.2f} "
          f"(gia DO THAT tu smoke)\n")
    over = []
    for s in shards:
        acc, model, risks, langs, reps = s
        c = cost_of(s)
        flag = ""
        if c > 8:
            flag = "  <-- QUA SAT TRAN $10, chia nho hon!"
            over.append(acc)
        print(f"  {acc:<15} {model:<28} risk={risks:<8} lang={langs:<6} "
              f"{n_games(s):>2} van  ${c:>5.2f}{flag}")
    if over:
        print(f"\n!! {len(over)} shard vuot nguong an toan $8: {over}")
        return 2
    if args.dry_run:
        print("\n--dry-run: khong phong gi.")
        return 0

    procs = []
    logdir = REPO / "plan" / "runs"
    logdir.mkdir(parents=True, exist_ok=True)
    for acc, model, risks, langs, reps in shards:
        label = label_of(acc, model, risks, langs)
        cmd = [sys.executable, str(LAUNCH), "--account", acc, "--model", model,
               "--risks", risks, "--langs", langs, "--reps", reps,
               "--wait", args.wait, "--label", label]
        outer = logdir / f"{label}.driver.log"
        fh = open(outer, "w", encoding="utf-8")
        p = subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT, cwd=str(REPO))
        procs.append((label, p, fh))
        print(f"phong {label} (pid {p.pid})")
        time.sleep(args.stagger)

    print(f"\nDa phong {len(procs)} shard. Theo doi:")
    print("  python plan/scripts/check_runs.py")
    print("\nDang doi tat ca ket thuc ...")
    fails = []
    for label, p, fh in procs:
        rc = p.wait()
        fh.close()
        print(f"  {label}: rc={rc}")
        if rc != 0:
            fails.append(label)
    if fails:
        print(f"\n{len(fails)} shard LOI: {fails}")
        print("Chay lai bang account du phong: trungkiet, foundnotkiet, kit567, "
              "hunhtrungkit, tnkiet")
        return 1
    print("\nTat ca shard xong. Gom ket qua:")
    print("  python plan/scripts/merge_shards.py --src plan/runs --dry-run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
