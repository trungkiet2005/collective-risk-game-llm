"""Xem nhanh trạng thái mọi shard trong plan/runs/ — đọc log, không gọi API.

Dùng:
    python plan/scripts/check_runs.py
    python plan/scripts/check_runs.py --watch      # tự làm mới mỗi 60s
"""
import argparse
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUNS = REPO / "plan" / "runs"


def shard_state(d):
    log = d / "shard.log"
    if not log.is_file():
        return "?", "chua co log", 0, 0, None
    text = log.read_text(encoding="utf-8", errors="replace")

    games = len(re.findall(r"\[game \d+/", text)) or None
    # dòng tiến độ do task in ra: "[12/20] risk=... disaster=... parse_fail=0"
    prog = re.findall(r"\[(\d+)/(\d+)\]", text)
    done, total = (int(prog[-1][0]), int(prog[-1][1])) if prog else (0, 0)

    cost = None
    m = re.findall(r"cost_usd[\"']?[:=]\s*\$?([0-9.]+)", text)
    if m:
        cost = float(m[-1])

    pf = sum(int(x) for x in re.findall(r"parse_fail=(\d+)", text))

    if "XONG shard" in text:
        state = "XONG"
    elif "SHARD CHUA XONG" in text or re.search(r"!! download .* THAT BAI", text):
        # Run xong + tốn tiền rồi nhưng KHÔNG có data trên máy. Data vẫn còn trên
        # server -> tải lại bằng `launch_shard.py --download-only`, KHÔNG chạy lại run.
        state = "CAN-TAI-LAI"
    elif re.search(r"!! (push|auth) THAT BAI|DUNG\.", text):
        state = "LOI"
    elif "ERRORED" in text:
        state = "ERRORED"
    elif "COMPLETED" in text:
        state = "run-xong"
    elif "kaggle b t run" in text:
        state = "dang-chay"
    elif "kaggle b t push" in text:
        state = "dang-push"
    else:
        state = "moi-bat-dau"

    note = ""
    for pat, label in ((r"available quota|max estimated cost", "403 QUOTA"),
                       (r"429|heavy load", "429"),
                       (r"503|unavailable", "503"),
                       (r"empty-content", "CONTENT RONG"),
                       (r"TIMEOUT", "TIMEOUT")):
        if re.search(pat, text, re.I):
            note = label
            break
    return state, note, done, total, cost


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", action="store_true")
    args = ap.parse_args()

    while True:
        if not RUNS.is_dir():
            print(f"chua co {RUNS}")
            return 1
        dirs = sorted(d for d in RUNS.iterdir() if d.is_dir() and not d.name.startswith("_"))
        print(f"\n{'shard':<52} {'trang thai':<12} {'tien do':>9} {'$':>7}  ghi chu")
        print("-" * 100)
        n_done = 0
        total_cost = 0.0
        for d in dirs:
            state, note, done, total, cost = shard_state(d)
            if state == "XONG":
                n_done += 1
            if cost:
                total_cost += cost
            prog = f"{done}/{total}" if total else "-"
            print(f"{d.name[:52]:<52} {state:<12} {prog:>9} "
                  f"{('%.2f' % cost) if cost else '-':>7}  {note}")
        print("-" * 100)
        print(f"{n_done}/{len(dirs)} shard XONG · tong chi phi thay trong log: "
              f"${total_cost:.2f}")
        if not args.watch:
            return 0
        time.sleep(60)


if __name__ == "__main__":
    sys.exit(main())
