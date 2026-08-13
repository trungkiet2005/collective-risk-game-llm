"""Đẩy và chạy MỘT shard exp_baseline server-side trên MỘT account Kaggle.

`kaggle b t run` không nhận biến môi trường, nên kích thước sweep phải nướng cứng vào
file lúc push. Script này sinh bản copy của crg_task_server.py với RISKS/LANGS/REPS đã
thay, push, run, rồi tải kết quả về — ghi log đầy đủ ra file (KHÔNG pipe qua head:
SIGPIPE có thể giết run giữa đường).

Ví dụ:
    # smoke 1 ván, 4 model trên 1 account
    python plan/scripts/launch_shard.py --account chiboiz --task crg-top-smoke \
        --risks 0.9 --langs en --reps 1 \
        --model claude-opus-5-default --model gemini-3.1-pro-preview

    # một shard thật: risk 0.9, cả 2 ngôn ngữ, 10 rep = 20 ván
    python plan/scripts/launch_shard.py --account chinguyentran \
        --model gpt-5.6-sol --risks 0.9 --langs en,vn --reps 10

    # chỉ tải lại kết quả của shard đã chạy xong
    python plan/scripts/launch_shard.py --account chinguyentran \
        --model gpt-5.6-sol --download-only
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TASK_SRC = REPO / "kaggle" / "benchmarks" / "crg_task_server.py"
CRED_ROOT = Path("D:/AI_PhD/GameTheory/kaggle_for_research")
WORK = REPO / "plan" / "runs"          # log + file shard
# Kết quả tải về PHẢI nằm ở đường dẫn ngắn: cây thư mục Kaggle sinh ra đã 174 ký tự,
# đặt trong plan/runs/<label>/ là vượt giới hạn 260 của Windows và download chết.
DL_ROOT = Path("D:/tmp/crgdl")

# account -> (kiểu, đường dẫn credential). BỎ trnnguynchis: xin proxy key bị 403
# thiếu xác minh SĐT (xem CLAUDE.md).
ACCOUNTS = {
    **{n: ("token_txt", CRED_ROOT / "kaggle-api" / f"{n}.txt") for n in (
        "chiboiz", "chinguyentran", "chisboiz", "chunaiu", "trunkdabest",
        "vinhdinhthien")},
    **{n: ("token_md", CRED_ROOT / "kaggle-api-2" / f"{n}.md") for n in (
        "acc1", "acc2", "acc3", "acc4", "acc5")},
    "trungkiet":    ("json", CRED_ROOT / "kaggle.json"),
    "foundnotkiet": ("json", CRED_ROOT / "kaggle (1).json"),
    "kit567":       ("json", CRED_ROOT / "kaggle (2).json"),
    "hunhtrungkit": ("json", CRED_ROOT / "kaggle (3).json"),
    "tnkiet":       ("json", CRED_ROOT / "kaggle (4).json"),
}


def log(handle, msg):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    handle.write(line + "\n")
    handle.flush()


def build_env(account, config_root):
    """Nạp credential cho account, trả về env dict để truyền cho subprocess."""
    if account not in ACCOUNTS:
        raise SystemExit(f"Account '{account}' khong co trong danh sach. "
                         f"Chon 1 trong: {', '.join(sorted(ACCOUNTS))}")
    kind, path = ACCOUNTS[account]
    if not path.is_file():
        raise SystemExit(f"Khong tim thay credential: {path}")

    cfg = Path(config_root) / account
    cfg.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["KAGGLE_CONFIG_DIR"] = str(cfg)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    # Mỗi account một config dir riêng, nếu không credential đè lẫn nhau.
    env.pop("KAGGLE_API_TOKEN", None)
    env.pop("KAGGLE_USERNAME", None)
    env.pop("KAGGLE_KEY", None)

    if kind == "token_txt":
        env["KAGGLE_API_TOKEN"] = path.read_text(encoding="utf-8").strip()
    elif kind == "token_md":
        m = re.search(r"KGAT_[A-Za-z0-9_-]+", path.read_text(encoding="utf-8"))
        if not m:
            raise SystemExit(f"Khong thay token KGAT_ trong {path}")
        env["KAGGLE_API_TOKEN"] = m.group(0)
    else:                                   # json kiểu cũ
        shutil.copyfile(path, cfg / "kaggle.json")
    return env


def run_cmd(handle, env, args, timeout=None):
    """Chạy lệnh, ghi TOÀN BỘ output ra log. Trả về (returncode, output)."""
    log(handle, f"$ {' '.join(args)}")
    try:
        p = subprocess.run(args, env=env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        log(handle, f"!! TIMEOUT sau {timeout}s")
        return 124, ""
    out = (p.stdout or "") + (p.stderr or "")
    handle.write(out + "\n")
    handle.flush()
    return p.returncode, out


TASK_NAME_IN_FILE = "collective-risk-baseline-srv"


def make_shard_file(dest, risks, langs, reps, task=None, rep_start="0"):
    """Copy task, thay 3 dòng sweep (83-85) bằng giá trị của shard này.

    Nếu `task` khác tên khai trong file thì đổi luôn `@kbench.task(name=...)`:
    `kaggle b t push <task>` BẮT BUỘC khớp tên khai bên trong, nếu không nó báo
    "Task '<task>' not found in <file>".
    """
    src = TASK_SRC.read_text(encoding="utf-8")
    new, n_r = re.subn(r'os\.environ\.get\("CRG_RISKS", "[^"]*"\)',
                       f'os.environ.get("CRG_RISKS", "{risks}")', src)
    new, n_l = re.subn(r'os\.environ\.get\("CRG_LANGS", "[^"]*"\)',
                       f'os.environ.get("CRG_LANGS", "{langs}")', new)
    new, n_p = re.subn(r'os\.environ\.get\("CRG_REPS", "[^"]*"\)',
                       f'os.environ.get("CRG_REPS", "{reps}")', new)
    new, n_s = re.subn(r'os\.environ\.get\("CRG_REP_START", "[^"]*"\)',
                       f'os.environ.get("CRG_REP_START", "{rep_start}")', new)
    if n_s != 1:
        raise SystemExit(f"Thay CRG_REP_START that bai ({n_s} cho) - kiem dong ~90.")
    if (n_r, n_l, n_p) != (1, 1, 1):
        raise SystemExit(f"Thay sweep that bai (risks={n_r} langs={n_l} reps={n_p}) "
                         f"- crg_task_server.py da doi cau truc? Kiem dong 83-85.")
    if task and task != TASK_NAME_IN_FILE:
        new, n_t = re.subn(rf'name="{re.escape(TASK_NAME_IN_FILE)}"',
                           f'name="{task}"', new)
        if n_t != 1:
            raise SystemExit(f"Khong doi duoc ten task thanh '{task}' "
                             f"(thay {n_t} cho). Kiem @kbench.task o dong ~605.")
    dest.write_text(new, encoding="utf-8")
    return dest


def wait_push_complete(handle, env, task, timeout=1800):
    """Push chạy task 1 lần trên model mặc định để validate; đợi tới Completed."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        rc, out = run_cmd(handle, env, ["kaggle", "b", "t", "status", task], timeout=300)
        if re.search(r"Status:\s*Completed", out):
            return True
        if re.search(r"Status:\s*(Errored|Failed|Cancelled)", out):
            log(handle, "!! push validate THAT BAI - xem log tren")
            return False
        log(handle, "   push dang validate, doi 30s ...")
        time.sleep(30)
    log(handle, "!! het thoi gian doi push")
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", required=True, help=f"1 trong: {', '.join(sorted(ACCOUNTS))}")
    ap.add_argument("--model", action="append", required=True,
                    help="slug model (lap lai duoc, toi da 7 - qua 7 API tra 400)")
    ap.add_argument("--risks", default="0.9,0.5,0.1")
    ap.add_argument("--langs", default="en,vn")
    ap.add_argument("--reps", default="10")
    ap.add_argument("--rep-start", default="0",
                    help="rep bat dau (chia shard theo rep): REP_START=5 --reps 5 -> rep 5..9")
    ap.add_argument("--task", default="collective-risk-baseline-srv")
    ap.add_argument("--wait", default="7200", help="giay cho `run --wait`")
    ap.add_argument("--label", default=None, help="ten shard dung cho thu muc log/ket qua")
    ap.add_argument("--download-only", action="store_true",
                    help="bo qua push/run, chi tai ket qua ve")
    # Tach 2 pha: push cua N shard KHONG duoc chay dong thoi (moi push chay 1 van
    # validate tren CUNG model mac dinh cua server -> 429 -> validate Errored ->
    # push huy; 12/15 shard Ngay B chet kieu nay). Nen: push tuan tu/it song song
    # truoc, roi moi phong toan bo run song song.
    ap.add_argument("--push-only", action="store_true",
                    help="chi push + doi validate xong, KHONG run")
    ap.add_argument("--run-only", action="store_true",
                    help="chi run + download, gia dinh da push xong")
    ap.add_argument("--skip-download", action="store_true")
    args = ap.parse_args()

    if len(args.model) > 7:
        raise SystemExit("Toi da 7 --model moi lenh (API tra 400 neu qua).")

    label = args.label or f"{args.account}__{args.model[0]}__r{args.risks}__l{args.langs}"
    label = re.sub(r"[^A-Za-z0-9._-]+", "-", label)
    shard_dir = WORK / label
    shard_dir.mkdir(parents=True, exist_ok=True)
    log_path = shard_dir / "shard.log"

    with open(log_path, "a", encoding="utf-8") as h:
        log(h, "=" * 78)
        log(h, f"SHARD {label}")
        log(h, f"account={args.account} models={args.model} risks={args.risks} "
               f"langs={args.langs} reps={args.reps} task={args.task}")
        n_games = len(args.risks.split(",")) * len(args.langs.split(",")) * int(args.reps)
        log(h, f"so van moi model = {n_games} (rep {args.rep_start}.."
               f"{int(args.rep_start) + int(args.reps) - 1})")

        env = build_env(args.account, WORK / "_kcfg")

        # Xác nhận account sống + lấy proxy key trước khi làm gì khác.
        rc, out = run_cmd(h, env, ["kaggle", "b", "auth", "-y",
                                   "--env-file", str(shard_dir / "account.env")], timeout=300)
        if rc != 0:
            log(h, f"!! auth THAT BAI (rc={rc}) - account co the chua verify. DUNG.")
            return 2

        if not args.download_only and not args.run_only:
            shard_py = make_shard_file(shard_dir / "shard_task.py",
                                       args.risks, args.langs, args.reps, args.task,
                                       args.rep_start)
            log(h, f"da sinh {shard_py}")

            # `push` chạy task 1 ván để validate, trên model mặc định của server. Khi
            # phóng nhiều shard cùng lúc, các lần validate này đập vào CÙNG một model
            # -> 429 heavy load -> validate Errored -> push hủy. Đó là lỗi phóng song
            # song, không phải lỗi task, nên retry là đúng cách (gặp thật: 7/15 shard
            # Ngày B chết kiểu này với stagger 20s).
            pushed = False
            for attempt in range(1, 4):
                rc, _ = run_cmd(h, env, ["kaggle", "b", "t", "push", args.task,
                                         "-f", str(shard_py)], timeout=3600)
                if rc != 0:
                    log(h, f"!! push lan {attempt} loi rc={rc}")
                elif wait_push_complete(h, env, args.task):
                    pushed = True
                    break
                if attempt < 3:
                    wait_s = 120 * attempt
                    log(h, f"   thu lai push sau {wait_s}s (lan {attempt + 1}/3) ...")
                    time.sleep(wait_s)
            if not pushed:
                log(h, "!! push THAT BAI sau 3 lan. DUNG.")
                return 3
            if args.push_only:
                log(h, f"PUSH XONG shard {label} (--push-only, chua run)")
                print(f"log: {log_path}")
                return 0

        if not args.download_only:
            cmd = ["kaggle", "b", "t", "run", args.task]
            for m in args.model:
                cmd += ["-m", m]
            cmd += ["--wait", str(args.wait)]
            rc, out = run_cmd(h, env, cmd, timeout=int(args.wait) + 900)
            log(h, f"run ket thuc rc={rc}")
            for line in out.splitlines():
                if re.search(r"(COMPLETED|ERRORED|Error code|quota|parse_fail)", line):
                    log(h, f"   >> {line.strip()}")

        # Trạng thái + log chi tiết từng model
        run_cmd(h, env, ["kaggle", "b", "t", "status", args.task], timeout=300)
        for m in args.model:
            rc, out = run_cmd(h, env, ["kaggle", "b", "t", "log", args.task, "-m", m],
                              timeout=600)
            (shard_dir / f"log__{re.sub(r'[^A-Za-z0-9._-]+', '-', m)}.txt").write_text(
                out, encoding="utf-8")
            for line in out.splitlines():
                if re.search(r"\[cfg\]|\[game|parse_fail|cost_usd|SUMMARY|games_per", line):
                    log(h, f"   {m}: {line.strip()}")

        dl_failed = []
        if not args.skip_download:
            for m in args.model:
                # PHẢI dùng đường dẫn NGẮN. Kaggle tạo cây rất sâu bên trong:
                #   <out>/<task>/<ver>/<model>/<runid>.download/results/frontier/
                #   <model_tag>/exp_baseline/checkpoints/risk-0p9__lang-en__rep-000.json
                # riêng phần đuôi đó đã 174 ký tự. Để `-o` trong plan/runs/<label>/
                # cho tổng 273 > giới hạn 260 của Windows -> download CHẾT dù run
                # đã thành công (gặp thật với gemini-3.1-pro 13-08-2026).
                dest = Path(DL_ROOT) / args.account
                dest.mkdir(parents=True, exist_ok=True)
                rc, out = run_cmd(h, env, ["kaggle", "b", "t", "download", args.task,
                                           "-m", m, "-o", str(dest), "-f"], timeout=1800)
                got = list(dest.rglob("games.csv"))
                if rc != 0 or not got:
                    dl_failed.append(m)
                    log(h, f"!! download {m} THAT BAI rc={rc}, games.csv={len(got)}")
                    if "No such file or directory" in out:
                        log(h, "   -> gan nhu chac chan do do dai duong dan Windows (260). "
                               "Data VAN CON tren server: tai lai bang duong dan ngan hon.")
                else:
                    log(h, f"download {m} OK -> {dest} ({len(got)} games.csv)")

        if dl_failed:
            # Không được ghi XONG: check_runs.py sẽ báo xanh trong khi không có data.
            log(h, f"!! SHARD CHUA XONG - download loi: {dl_failed}")
            print(f"\nlog: {log_path}")
            return 4

        log(h, f"XONG shard {label}")
    print(f"\nlog: {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
