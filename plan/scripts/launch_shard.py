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
import json
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
# Cho phep ghim mot ban task DA QUA SMOKE khi file goc dang bi sua song song.
# Dat CRG_TASK_SRC=<duong dan> hoac dung --task-src. Mac dinh: file goc.
if os.environ.get("CRG_TASK_SRC"):
    TASK_SRC = Path(os.environ["CRG_TASK_SRC"])
# kbench ghi .task.json/.run.json ra CWD -> ghim CWD vao day (xem run_cmd).
ARTIFACTS = REPO / "kaggle" / "benchmarks" / "artifacts"
CRED_ROOT = Path(os.environ.get(
    "CRSD_CRED_ROOT", str(REPO.parents[1] / "infra" / "kaggle_for_research")))
WORK = REPO / "plan" / "runs"          # log + file shard
# Kết quả tải về PHẢI nằm ở đường dẫn ngắn: cây thư mục Kaggle sinh ra đã 174 ký tự,
# đặt trong plan/runs/<label>/ là vượt giới hạn 260 của Windows và download chết.
DL_ROOT = Path("D:/tmp/crgdl")

# account -> (kiểu, đường dẫn credential).
#
# Bảng này chỉ ánh xạ TÊN -> CREDENTIAL, nó KHÔNG nói account còn sống hay không. Sức
# khoẻ account trôi theo thời gian (mất 2 account trong 4 tuần, cùng lỗi 403 "missing
# phone/identity verification"), nên đừng hardcode danh sách sống ở đây — chạy
# `plan/scripts/probe_accounts.py` trước mỗi đợt lớn, nó là nguồn đúng duy nhất.
# Các account từng hỏng VẪN nằm trong bảng để probe kiểm lại được: một account bị 403
# vì chưa xác minh SĐT có thể sống lại sau khi người dùng xác minh.
#
# ⚠️ NHÃN ≠ USER KAGGLE. Đo 17-09-2026 từ URL task trong log: bốn cặp nhãn là CÙNG một user
# (cùng token gốc, cùng quota 24h, cùng không gian tên task):
#     acc06 = acc1 (minh2duy) · acc07 = acc2 (boymagic) · acc08 = acc3 (trngthtnhi)
#     acc09 = acc4 (osduyminh)
# Hai shard CÙNG tên task trên hai nhãn của một user sẽ PUSH ĐÈ nhau: shard sau thay file
# sweep của shard trước (rep_start/reps khác nhau -> chạy nhầm rep), validate lại lần nữa,
# và cùng rút một quota. Đừng bao giờ giao hai nhãn trong ALIASES cho cùng một đợt.
ALIASES = {"acc1": "acc06", "acc2": "acc07", "acc3": "acc08", "acc4": "acc09"}
ACCOUNTS = {
    **{n: ("token_txt", CRED_ROOT / "kaggle-api" / f"{n}.txt") for n in (
        "chiboiz", "chinguyentran", "chisboiz", "chunaiu", "trnnguynchis",
        "trunkdabest", "vinhdinhthien")},
    **{n: ("token_md", CRED_ROOT / "kaggle-api-2" / f"{n}.md") for n in (
        "acc1", "acc2", "acc3", "acc4", "acc5")},
    # Lô bổ sung 10-09-2026 (kaggle-api-3/): cùng định dạng token thô như kaggle-api/.
    **{n: ("token_txt", CRED_ROOT / "kaggle-api-3" / f"{n}.txt") for n in (
        "acc06", "acc07", "acc08", "acc09", "acc10", "acc11")},
    # Lô bổ sung 11-09-2026 (kaggle-api-4/). Người dùng thả token vào
    # D:/AI_PhD/kaggle_for_research/ (KHÁC CRED_ROOT) rồi copy vào đây — xem CLAUDE.md.
    **{n: ("token_txt", CRED_ROOT / "kaggle-api" / f"{n}.txt") for n in (
        "kakagotto", "tonngohan")},
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
    """Chạy lệnh, ghi TOÀN BỘ output ra log. Trả về (returncode, output).

    Chạy trong `kaggle/benchmarks/artifacts/` chứ KHÔNG phải CWD của tiến trình cha.
    Lý do: `kaggle b t push` / `run` ghi `<task>.task.json` và
    `<task>-run_id_*.run.json` ra **thư mục đang đứng**, không phải cạnh file task. Mà
    các launcher (`run_fill.py`, `launch_e3a.py`, `stage_day_b.py`) đều gọi script này
    với `cwd=REPO`, nên artifact rơi thẳng ra gốc repo — đúng cái bẫy CLAUDE.md đã mô
    tả, và nó vẫn tái diễn chừng nào còn phải nhớ `cd` bằng tay. Ghim CWD ở đây là chỗ
    DUY NHẤT sửa được một lần cho mọi launcher.

    An toàn vì mọi đường dẫn truyền cho kbench đều TUYỆT ĐỐI (`-f <shard_py>`,
    `-o <dest>`, `--env-file <...>`), nên không lệnh nào phụ thuộc CWD.
    """
    log(handle, f"$ {' '.join(args)}")
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    try:
        p = subprocess.run(args, env=env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout,
                           cwd=str(ARTIFACTS))
    except subprocess.TimeoutExpired:
        log(handle, f"!! TIMEOUT sau {timeout}s")
        return 124, ""
    out = (p.stdout or "") + (p.stderr or "")
    handle.write(out + "\n")
    handle.flush()
    return p.returncode, out


TASK_NAME_IN_FILE = "collective-risk-baseline-srv"


def make_shard_file(dest, risks, langs, reps, task=None, rep_start="0",
                    max_out=None, concurrency=None, overrides=None):
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
    if max_out:
        # Nướng cứng cap vào file: server KHONG nhan bien moi truong, nen dat
        # CRG_MAX_OUT o shell la vo ich. Can khi cap mac dinh 6000 khong du va
        # model tra content RONG (opus-5 tieng Viet: 16/16 cell thieu deu la vn).
        new, n_m = re.subn(r'os\.environ\.get\("CRG_MAX_OUT", "[^"]*"\)',
                           f'os.environ.get("CRG_MAX_OUT", "{max_out}")', new)
        if n_m != 1:
            raise SystemExit(f"Thay CRG_MAX_OUT that bai ({n_m} cho).")
    if concurrency:
        # Song song hoa 6 ghe trong MOT vong. ThreadPoolExecutor.map giu nguyen thu
        # tu input -> output byte-identical voi duong tuan tu. Day la don bay wall-clock
        # duy nhat: chi phi khong doi, chi nhanh len.
        new, n_c = re.subn(r'os\.environ\.get\("CRG_CONCURRENCY", "[^"]*"\)',
                           f'os.environ.get("CRG_CONCURRENCY", "{concurrency}")', new)
        if n_c != 1:
            raise SystemExit(f"Thay CRG_CONCURRENCY that bai ({n_c} cho).")
    # Bien CRG_* khac (CRG_TEMPLATE cho E1, CRG_PROBE cho E2, CRG_SEAT_MODELS cho
    # E3a/E3b). Cung ly do voi CRG_MAX_OUT: server KHONG nhan bien moi truong tu
    # shell, nen phai nuong thang mac dinh vao file shard.
    for name, value in (overrides or {}).items():
        new, n_o = re.subn(rf'os\.environ\.get\("{re.escape(name)}", "[^"]*"\)',
                           f'os.environ.get("{name}", "{value}")', new)
        if n_o != 1:
            raise SystemExit(f"Thay {name} that bai ({n_o} cho) - "
                             f"crg_task_server.py co doc bien nay voi mac dinh chuoi khong?")

    if task and task != TASK_NAME_IN_FILE:
        new, n_t = re.subn(rf'name="{re.escape(TASK_NAME_IN_FILE)}"',
                           f'name="{task}"', new)
        if n_t != 1:
            raise SystemExit(f"Khong doi duoc ten task thanh '{task}' "
                             f"(thay {n_t} cho). Kiem @kbench.task o dong ~605.")
    dest.write_text(new, encoding="utf-8")
    return dest


def task_status(handle, env, task):
    """Trả về trạng thái task ('Running'/'Completed'/'Errored'/None nếu chưa có)."""
    rc, out = run_cmd(handle, env, ["kaggle", "b", "t", "status", task], timeout=300)
    m = re.search(r"Status:\s*(\w+)", out)
    return m.group(1) if m else None


def wait_task_idle(handle, env, task, timeout=2400):
    """Đợi tới khi task KHÔNG còn Running.

    `kaggle b t push` bị TỪ CHỐI NGAY (rc=1, output RỖNG, ~3 giây) nếu version
    trước còn đang validate. Không có thông báo lỗi nào, nên rất dễ chẩn đoán sai
    thành 429/quota. Đây là nguyên nhân thật của việc 12/15 shard Ngày B chết.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = task_status(handle, env, task)
        if st != "Running":
            log(handle, f"   task idle (status={st}) -> push duoc")
            return True
        log(handle, "   task dang Running (validate version truoc), doi 30s ...")
        time.sleep(30)
    log(handle, "!! task ket Running qua lau")
    return False


def wait_push_complete(handle, env, task, timeout=5400):
    """Push chạy task 1 lần trên model mặc định để validate; đợi tới Completed.

    Trần 5400s, không phải 1800s. Đo thật 17-09-2026: 3 push validate CÙNG LÚC (cùng một
    model mặc định của server) vẫn "Running" sau 38 phút, trong khi các đợt E6 trước chỉ
    ~25 phút. Hết trần thì vòng retry bên dưới PUSH LẠI một version mới, tức là vứt lần
    validate đang chạy dở và bắt đầu lại từ đầu, nên trần quá sát làm chậm hẳn chứ không
    nhanh hơn.
    """
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
    ap.add_argument("--langs", default="en")
    ap.add_argument("--reps", default="10")
    ap.add_argument("--rep-start", default="0",
                    help="rep bat dau (chia shard theo rep): REP_START=5 --reps 5 -> rep 5..9")
    ap.add_argument("--template", default=None,
                    help="CRG_TEMPLATE: 'baseline' (mac dinh) hoac 'nohint' (E1)")
    ap.add_argument("--temperature", default=None,
                    help="CRG_TEMPERATURE: mac dinh 0.7 (moi van da co deu o 0.7). "
                         "E6 dung 0 cho nhanh doi chung giai ma. Dat khac 0.7 se "
                         "them hau to _temp<x> vao ten experiment, nen no KHONG "
                         "roi vao thu muc baseline.")
    ap.add_argument("--probe", default=None,
                    help="CRG_PROBE cho E2, vd 'rules,value'")
    ap.add_argument("--on-game-error", default=None, choices=("abort", "skip"),
                    help="CRG_ON_GAME_ERROR. 'abort' (mac dinh cua task) dung ca shard khi "
                         "MOT o hong; 'skip' bo o do roi quet tiep. Do that 11-09-2026: mot "
                         "cu 429 thoang qua o van thu 4 lam mat 27/30 van cua shard duoi "
                         "'abort'. Duoi 'skip' thi assertion cuoi van danh dau run la hong "
                         "(co y - de shard mat o khong doc thanh sweep sach), nhung cac van "
                         "da xong VAN duoc commit va tai ve duoc.")
    ap.add_argument("--seat-models", default=None,
                    help="CRG_SEAT_MODELS cho E3a/E3b: dung 6 muc, ghe P1 truoc, "
                         "vd 'self,scripted:always_4,...'")
    ap.add_argument("--concurrency", default=None,
                    help="CRG_CONCURRENCY: so ghe goi song song trong 1 vong (mac dinh 1). "
                         "Khong doi chi phi, chi giam wall-clock.")
    ap.add_argument("--max-out", default=None,
                    help="ghi de max_completion_tokens (mac dinh 512/6000 theo model)")
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

        # Luon nuong slug se chay that vao shard: model nao KHAC import file nay (tuc buoc
        # push validate tren model mac dinh cua server) chi choi 1 van. Guard cu so ten
        # "gemini-3-flash-preview" da im lang het tac dung khi server doi sang
        # gemini-3.7-flash -> validate chay CA sweep, rut can 2 account (17-09-2026).
        overrides = {"CRG_EXPECT_MODEL": ",".join(args.model)}
        if args.template:
            overrides["CRG_TEMPLATE"] = args.template
        if args.probe:
            overrides["CRG_PROBE"] = args.probe
        if args.seat_models:
            overrides["CRG_SEAT_MODELS"] = args.seat_models
        if args.temperature:
            overrides["CRG_TEMPERATURE"] = args.temperature
        if args.on_game_error:
            overrides["CRG_ON_GAME_ERROR"] = args.on_game_error
        if overrides:
            log(h, f"overrides={overrides}")

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
                                       args.rep_start, args.max_out, args.concurrency,
                                       overrides)
            log(h, f"da sinh {shard_py}")

            # `push` chạy task 1 ván để validate, trên model mặc định của server. Khi
            # phóng nhiều shard cùng lúc, các lần validate này đập vào CÙNG một model
            # -> 429 heavy load -> validate Errored -> push hủy. Đó là lỗi phóng song
            # song, không phải lỗi task, nên retry là đúng cách (gặp thật: 7/15 shard
            # Ngày B chết kiểu này với stagger 20s).
            pushed = False
            for attempt in range(1, 4):
                # Bắt buộc: task còn Running thì push bị từ chối ngay, không có
                # thông báo. Chờ rảnh rồi mới push.
                wait_task_idle(h, env, args.task)
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
            run_rc, out = run_cmd(h, env, cmd, timeout=int(args.wait) + 900)
            log(h, f"run ket thuc rc={run_rc}")
            if run_rc != 0:
                # Đo thật 11-09-2026: `kaggle b t run` trả 503 ngay lúc submit (lỗi phía
                # Kaggle - sự thật số 2 trong CLAUDE.md, đổi account vô ích) nên run KHÔNG
                # HỀ khởi động. Trước đây rc này chỉ được ghi log rồi bỏ đó, và cổng
                # download bên dưới lại đếm games.csv của task KHÁC nên shard báo XONG
                # trong khi không có ván nào. Vẫn đi tiếp để tải phần data đã có (run có
                # thể chết GIỮA đường và để lại data một phần), nhưng phải kêu to.
                log(h, "!! `kaggle b t run` LOI - run co the CHUA HE khoi dong. "
                       "Cong download ben duoi se quyet dinh shard co XONG hay khong.")
            for line in out.splitlines():
                if re.search(r"(COMPLETED|ERRORED|Error code|quota|parse_fail)", line):
                    log(h, f"   >> {line.strip()}")

        # Trạng thái + log chi tiết từng model.
        # PHẢI kiểm Errored ở đây: run có thể chết giữa đường (ví dụ guard
        # empty-content kích hoạt) mà vẫn để lại data MỘT PHẦN tải về được -> nếu chỉ
        # dựa vào download thành công thì shard bị báo rc=0 trong khi thiếu ván.
        # Đã bị đúng lỗi này ở Ngày B: 15/15 rc=0 nhưng opus-5 chỉ có 44/60 ván.
        _, status_out = run_cmd(h, env, ["kaggle", "b", "t", "status", args.task],
                                timeout=300)
        errored = [m for m in args.model
                   if re.search(rf"{re.escape(m)}\s+Errored", status_out)]
        done_info = {}
        for m in args.model:
            rc, out = run_cmd(h, env, ["kaggle", "b", "t", "log", args.task, "-m", m],
                              timeout=600)
            (shard_dir / f"log__{re.sub(r'[^A-Za-z0-9._-]+', '-', m)}.txt").write_text(
                out, encoding="utf-8")
            # Bao cao cuoi sweep cua CHINH server. Day la nguon duy nhat noi dung
            # ve viec run VUA ROI lam duoc gi. Moi cach dem file deu co the bi data
            # cua mot run TRUOC do tren cung task qua mat.
            for line in out.splitlines():
                i = line.find("[CRG_DONE]")
                if i == -1:
                    continue
                try:
                    done_info[m] = json.loads(line[i + len("[CRG_DONE]"):].strip())
                except ValueError:
                    pass
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
                # PHẢI đếm trong ĐÚNG thư mục task. `dest` là gốc của ACCOUNT, nên
                # rglob ở đây vét cả games.csv của mọi task khác account này từng tải
                # (E1/E2/E3a). Đo thật 11-09-2026 trên e3b_flashxqwen_k4: download in ra
                # "Done: 0 runs downloaded" nhưng 5 games.csv cũ của task khác làm `got`
                # khác rỗng -> shard báo XONG dù KHÔNG tải về ván nào.
                got = list((dest / args.task).rglob("games.csv"))
                # Hai chuỗi này là tín hiệu KHÔNG THỂ nhầm của kaggle CLI: không có run
                # nào để tải. Kiểm chuỗi thay vì chỉ kiểm rc vì `download` trả rc=0 kể cả
                # khi nó chẳng tải gì.
                empty = ("Done: 0 runs downloaded" in out
                         or "No runs found for task" in out)
                if rc != 0 or empty or not got:
                    dl_failed.append(m)
                    log(h, f"!! download {m} THAT BAI rc={rc}, games.csv={len(got)}, "
                           f"khong-co-run-nao={empty}")
                    if "No such file or directory" in out:
                        log(h, "   -> gan nhu chac chan do do dai duong dan Windows (260). "
                               "Data VAN CON tren server: tai lai bang duong dan ngan hon.")
                else:
                    log(h, f"download {m} OK -> {dest} ({len(got)} games.csv)")

        # Cong kiem THEO BAO CAO CUA SERVER. Dat SAU buoc download (dong ~435) va
        # truoc phep kiem `dl_failed`: download van phai chay truoc, vi mot sweep
        # hong mot phan (CRG_ON_GAME_ERROR=skip) VAN commit nhung van da xong va
        # chung phai ve dia. Cong nay chi quyet dinh co ghi XONG hay khong.
        # Do that 12-09-2026: mot task chua NHIEU run (moi gia tri k cua cung mot
        # cap la mot run rieng), nen dem games.csv theo thu muc task van thay data
        # cua run TRUOC do va cho qua mot run hong toan bo. acc08/crg-e3b-flash-grok:
        # run cu de lai 30 van sach, run moi hong ca 30 o vi 403 quota, shard bao
        # rc=0. `n_games` = resumed + new, nen shard resume dung han van qua cong nay.
        bad_sweep = []
        for m in args.model:
            info = done_info.get(m)
            if info is None:
                bad_sweep.append("%s: khong co [CRG_DONE] -> run CHUA HE ket thuc" % m)
            elif (info.get("failed_games") or 0) > 0:
                cells = info.get("failed_cells") or []
                first = str(cells[0])[:200] if cells else ""
                bad_sweep.append("%s: %d o hong%s"
                                 % (m, int(info["failed_games"]),
                                    (" - " + first) if first else ""))
            elif not (info.get("n_games") or 0):
                bad_sweep.append("%s: n_games=0 -> khong sinh duoc van nao" % m)
        if bad_sweep:
            log(h, "!! SHARD CHUA XONG - server bao sweep KHONG sach:")
            for b in bad_sweep:
                log(h, "   " + b)
            print("log: %s" % log_path)
            return 6

        if dl_failed:
            # Không được ghi XONG: check_runs.py sẽ báo xanh trong khi không có data.
            log(h, f"!! SHARD CHUA XONG - download loi: {dl_failed}")
            print(f"\nlog: {log_path}")
            return 4
        if errored:
            log(h, f"!! SHARD CHUA XONG - run ERRORED: {errored} "
                   f"(data tai ve chi la MOT PHAN, thieu van)")
            print(f"\nlog: {log_path}")
            return 5

        log(h, f"XONG shard {label}")
    print(f"\nlog: {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
