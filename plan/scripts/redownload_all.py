"""Tải lại kết quả cho mọi shard đã chạy xong nhưng CHƯA có data trên máy.

Vì sao cần: các shard phóng trước 13-08-2026 03:00 dùng bản launch_shard.py cũ, tải về
`plan/runs/<label>/download/` — cộng với cây thư mục Kaggle sinh ra (174 ký tự) thì vượt
giới hạn 260 ký tự của Windows nên download CHẾT dù run đã thành công và đã tốn tiền.

Data VẪN CÒN trên server Kaggle, nên chỉ cần tải lại vào đường dẫn ngắn (D:/tmp/crgdl).
KHÔNG chạy lại run — sẽ mất tiền lần nữa vô ích.

Dùng:
    python plan/scripts/redownload_all.py --dry-run
    python plan/scripts/redownload_all.py
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from launch_shard import DL_ROOT                      # noqa: E402
from launch_day_a import SHARDS, label_of             # noqa: E402

REPO = Path(__file__).resolve().parents[2]
LAUNCH = REPO / "plan" / "scripts" / "launch_shard.py"


def has_data(account, model, risks, langs):
    """Có data ở BẤT KỲ đâu chưa: đường dẫn ngắn mới, hay plan/runs/<label>/download
    của bản launcher cũ (những shard tên ngắn vẫn tải về được ở đó)."""
    for d in (DL_ROOT / account,
              REPO / "plan" / "runs" / label_of(account, model, risks, langs) / "download"):
        if d.is_dir() and any(d.rglob("games.csv")):
            return True
    return False


def run_finished(account, model, risks, langs):
    """Log của shard cho biết run đã COMPLETED chưa."""
    log = REPO / "plan" / "runs" / label_of(account, model, risks, langs) / "shard.log"
    if not log.is_file():
        return False
    return "COMPLETED" in log.read_text(encoding="utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    todo, skip_nodata, skip_have = [], [], []
    for acc, model, risks, langs, reps in SHARDS:
        if has_data(acc, model, risks, langs):
            skip_have.append(acc)
        elif run_finished(acc, model, risks, langs):
            todo.append((acc, model, risks, langs))
        else:
            skip_nodata.append(acc)

    print(f"da co data      : {len(skip_have)} {skip_have}")
    print(f"run chua xong    : {len(skip_nodata)} {skip_nodata}")
    print(f"CAN TAI LAI      : {len(todo)} {[t[0] for t in todo]}")
    if args.dry_run or not todo:
        return 0

    fails = []
    for acc, model, risks, langs in todo:
        print(f"\n--- tai lai {acc} / {model}")
        rc = subprocess.run(
            [sys.executable, str(LAUNCH), "--account", acc, "--model", model,
             "--risks", risks, "--langs", langs,
             "--label", label_of(acc, model, risks, langs), "--download-only"],
            cwd=str(REPO)).returncode
        ok = has_data(acc, model, risks, langs)
        print(f"    rc={rc} data={'CO' if ok else 'KHONG'}")
        if not ok:
            fails.append(acc)
    if fails:
        print(f"\nVAN THIEU DATA: {fails}")
        return 1
    print("\nXong. Gom lai:")
    print("  python plan/scripts/merge_shards.py --src plan/runs D:/tmp/crgdl --dry-run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
