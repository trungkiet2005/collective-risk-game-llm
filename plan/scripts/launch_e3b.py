"""E3b — quần thể hỗn hợp: k agent model A + (6−k) agent model B (§7.4).

Round-robin đủ **C(5,2) = 10 cặp** × **k = 1…5** × 3 risk × 10 rep = **1.500 ván**.
Chi phí **~$97 gọi model + ~$6 phí validate = ~$103** (giá đo thật, xem bảng `COST`).
Mỗi model có mặt ở đúng 4 cặp → 600 ván và 1.800 ghế-ván cho **cả 5 model như nhau**; cân
bằng là tính chất của đồ thị đầy đủ K₅ chứ không phải thứ phải canh tay (§7.1).

Khác E3a ở bốn chỗ, và cả bốn đều ảnh hưởng tới cách chia shard:

1. **Cả 6 ghế đều gọi API** (E3a chỉ 1/6) → 60 lượt/ván thay vì 10, đắt gấp 6.
2. **Một shard chỉ chở được MỘT cấu hình ghế.** `CRG_SEAT_MODELS` được nướng cứng vào file
   lúc `push`, nên mỗi `k` phải là một shard riêng — không gộp k=1…5 vào một lệnh được.
   Shard tự nhiên vì thế là **1 cặp × 1 k × 3 risk × 10 rep = 30 ván**; các cặp đắt bị chẻ
   thêm theo `--max-cost` nên tổng ra **62 shard**.
3. **Slug ghế lạ PHẢI có tiền tố nhà cung cấp.** Đo bằng pilot 11-09-2026: proxy chuẩn hoá
   slug của model `-m` (`qwen3-…` → `qwen/qwen3-…`) nhưng **không** chuẩn hoá slug ghế lạ.
   Viết `grok-4.20-…` thì `seat_model` ghi đúng chuỗi đó, ra tag `grok-4.20-…` ≠ tag thư
   mục `xai-grok-4.20-…`, tức **một model mang hai tag** và cổng panel sẽ đếm ra 6 model.
   Viết `xai/grok-4.20-…` thì ra đúng tag. Nên bảng `SLUG` dưới đây luôn có tiền tố nhà.
4. **Gom kết quả phải ép `--experiment exp_mixed`.** Tên mặc định của shard E3b là
   `exp_baseline_seats-LLLMMM-<hash>` (34 ký tự); cộng với `mix__<A>__<B>__kN` lặp hai lần
   trong đường dẫn là **261 ký tự > trần 260 của Windows**. `to_wide_csv.py` có cổng chặn
   sớm, nhưng đặt tên ngắn ngay từ đầu thì không phải gặp nó.

Dùng:

    python plan/scripts/launch_e3b.py --dry-run              # xem ke hoach, khong ton gi
    python plan/scripts/launch_e3b.py --smoke --accounts a   # vai xu, kiem tien to nha o ghe la
    python plan/scripts/launch_e3b.py --accounts a,b,c       # chay that, theo dot re-truoc

Gom về `results/` sau khi tải — `--src` phải trỏ ĐÚNG thư mục task E3b. `--experiment` là
**ép tên cho mọi shard tìm thấy**, không phải bộ lọc, nên quét bừa `plan/runs` sẽ đổ 131
`games.csv` không phải E3b (kể cả model ngoài panel) vào `results/exp_mixed/`:

    python plan/scripts/to_wide_csv.py --experiment exp_mixed         --src D:/tmp/crgdl/*/crg-e3b-haiku-* D:/tmp/crgdl/*/crg-e3b-flash-*               D:/tmp/crgdl/*/crg-e3b-luna-*  D:/tmp/crgdl/*/crg-e3b-qwen-*
    python plan/scripts/verify_wide.py --expect-reps 10

Lệnh chạy in ra ở cuối mỗi lần chạy thật, không phải nhớ.
"""
import argparse
import csv
import glob
import itertools
import subprocess
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from crsd.dataio.wide_csv import canonical_model_tag  # noqa: E402

LAUNCH = REPO / "plan" / "scripts" / "launch_shard.py"
DL = "D:/tmp/crgdl"
PUSH_CONC = 3          # §12 muc 2: push qua 3 cai mot luc la bi tu choi im lang

# Slug gọi proxy, LUÔN có tiền tố nhà cung cấp — xem lý do 3 ở đầu file.
SLUG = {
    "anthropic-claude-haiku-4-5-20251001": "anthropic/claude-haiku-4-5-20251001",
    "google-gemini-3.5-flash-lite":        "google/gemini-3.5-flash-lite",
    "openai-gpt-5.6-luna":                 "openai/gpt-5.6-luna",
    "qwen-qwen3-235b-a22b-instruct-2507":  "qwen/qwen3-235b-a22b-instruct-2507",
    "xai-grok-4.20-0309-non-reasoning":    "xai/grok-4.20-0309-non-reasoning",
}
# Slug TRẦN, chỉ dùng cho `kaggle b t run -m <slug>`. Mọi launcher khác trong repo truyền
# dạng trần ở đây và server tự thêm tiền tố nhà, nên giữ nguyên cho khỏi phải kiểm lại xem
# `-m` có nhận dạng có tiền tố hay không. Tiền tố CHỈ cần cho ghế lạ (xem lý do 3 đầu file).
BARE = {t: s.split("/", 1)[1] for t, s in SLUG.items()}
SHORT = {
    "anthropic-claude-haiku-4-5-20251001": "haiku",
    "google-gemini-3.5-flash-lite":        "flash",
    "openai-gpt-5.6-luna":                 "luna",
    "qwen-qwen3-235b-a22b-instruct-2507":  "qwen",
    "xai-grok-4.20-0309-non-reasoning":    "grok",
}
# $/ván của bàn ĐỒNG NHẤT. Đây là giá **đo thật** quy từ log E3a trong `plan/runs/*/shard.log`
# (E3a chỉ 1/6 ghế gọi API nên nhân 6), KHÔNG phải giá ước lượng ở plan §5 — bảng đó lệch
# tới +34% cho haiku, và haiku một mình chiếm quá nửa ngân sách E3b nên sai ở đó là sai to.
# Ba điểm đo trực tiếp trên E3b xác nhận cách quy đổi này đúng cho bàn hỗn hợp:
#   luna×qwen k3   đo $0,0459   (dự báo $0,049)
#   flash×qwen k3  đo $0,0198   (dự báo $0,0217)
#   qwen×grok k3   đo $0,0183-0,0211
# Repo có hai bảng giá mâu thuẫn cho haiku (0,125 ở plan §5; 0,178 ở fill_wave_e12.py);
# số đo thật nằm giữa. Dùng số đo.
COST = {
    "anthropic-claude-haiku-4-5-20251001": 0.1673,
    "openai-gpt-5.6-luna":                 0.0900,
    "google-gemini-3.5-flash-lite":        0.0355,
    "xai-grok-4.20-0309-non-reasoning":    0.0221,
    "qwen-qwen3-235b-a22b-instruct-2507":  0.0079,
}
# `kaggle b t push` chạy MỘT VÁN THẬT để validate, và ở E3b ván đó có đủ 6 ghế LLM (E3a chỉ
# 1 ghế nên chuyện này chưa bao giờ đắt). ~$0,10 mỗi lần push, trừ vào đúng quota của account
# đang push — phải tính vào dự toán chứ không phải phát hiện lúc hết tiền.
PUSH_VALIDATE_COST = 0.10
PANEL = sorted(SLUG)
PAIRS = [tuple(sorted(p)) for p in itertools.combinations(PANEL, 2)]   # A < B theo từ điển
KS = (1, 2, 3, 4, 5)
RISKS = ("0.1", "0.5", "0.9")
REPS = 10
N_SEATS = 6
SELF = "self"


def leads_a(pair_idx: int, k: int) -> bool:
    """Cặp này, mức k này thì model A ngồi những ghế ĐẦU hay ghế CUỐI?

    Nếu A luôn chiếm ghế P1…Pk thì "lợi thế của A" lẫn hoàn toàn với "lợi thế của ghế
    đầu" — prompt có nói *mỗi người luôn ở một vị trí cố định*, nên reviewer hỏi được và ta
    không có gì để trả lời. Đảo theo chẵn lẻ của (số thứ tự cặp + k) thì mỗi model đều có
    lượt ngồi ghế đầu, và nó **miễn phí**: tập hợp ghế không đổi, chỉ thứ tự đổi.

    Không đổi tập hợp nghĩa là không đổi ba thứ quan trọng: tên `mix__A__B__kN` (đặt theo
    SỐ ĐẾM chứ không theo vị trí, và đã có test khẳng định tên bất biến qua hoán vị), số
    ván có mặt, và số ghế-ván. Nên cổng cân bằng không hề biết chuyện này xảy ra.
    """
    return (pair_idx + k) % 2 == 0


def seat_spec(a: str, b: str, k: int, lead_a: bool) -> str:
    """6 mục, ghế P1 trước. `-m` là a nên a viết `self`; b phải là slug CÓ tiền tố nhà."""
    seats = [SELF] * k + [SLUG[b]] * (N_SEATS - k)
    if not lead_a:
        seats = [SLUG[b]] * (N_SEATS - k) + [SELF] * k
    return ",".join(seats)


def shard_cost(a: str, b: str, k: int, n_games: int) -> float:
    """k ghế của a + (6−k) ghế của b, chia đều 6 ghế."""
    return n_games * (k * COST[a] + (N_SEATS - k) * COST[b]) / N_SEATS


def task_of(a: str, b: str) -> str:
    """Mỗi cặp một task. Push vào HAI task khác nhau chạy song song được; push vào CÙNG
    một task thì bị từ chối im lặng khi bản trước còn validate (§12 mục 2)."""
    return f"crg-e3b-{SHORT[a]}-{SHORT[b]}"


def have():
    """(a, b, k) -> {risk: set(rep)} đã tải về.

    Đọc `seat_models` của `games.csv` rồi chuẩn hoá từng slug — KHÔNG đọc tên thư mục, vì
    tên thư mục chỉ mang model `-m` chứ không mang cặp. Chuẩn hoá là bắt buộc: shard chạy
    trước bản sửa 11-09 ghi slug ghế lạ không có tiền tố nhà.
    """
    got = defaultdict(lambda: defaultdict(set))
    for f in glob.glob(f"{DL}/**/crg-e3b-*/**/games.csv", recursive=True):
        # Ván pilot/smoke KHÔNG được tính là ô đã xong. Chúng nằm trong `D:/tmp/crgdl`
        # (gitignore, máy khác không có), nên nếu tính thì tính đầy đủ của wave phụ thuộc
        # vào rác tạm: dọn thư mục đó đi là 3 ô biến mất khỏi thiết kế mà không ai biết ô
        # nào, và cổng cân bằng nổ sau khi đã tiêu hết tiền. Chạy lại 3 ván tốn $0,07.
        if "crg-e3b-pilot" in f or "crg-e3b-smoke" in f:
            continue
        with open(f, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                spec = r.get("seat_models") or ""
                if not spec:
                    continue
                tags = [canonical_model_tag(s) for s in spec.split("|")]
                counts = defaultdict(int)
                for t in tags:
                    counts[t] += 1
                if len(counts) != 2:
                    continue                      # ván đồng nhất lọt vào — bỏ qua
                a, b = sorted(counts)
                got[(a, b, counts[a])][r["risk_probability"]].add(int(r["rep"]))
    return got


def runs(missing):
    """Tập rep rời rạc -> danh sách dải LIÊN TỤC (start, n), để gộp thành ít shard nhất."""
    out, seq, i = [], sorted(missing), 0
    while i < len(seq):
        j = i
        while j + 1 < len(seq) and seq[j + 1] == seq[j] + 1:
            j += 1
        out.append((seq[i], seq[j] - seq[i] + 1))
        i = j + 1
    return out


def missing_shards(max_cost: float):
    """[(a, b, k, risks, rep_start, n, $)] — rẻ trước.

    Rẻ trước là thứ tự đã chứng minh đúng ở đợt E1+E2: quota cạn dần trong lúc chạy, nên
    vét xong những cái rẻ trước rồi mới tới cái đắt thì số ô đóng được nhiều nhất.
    """
    got, out = have(), []
    for idx, (a, b) in enumerate(PAIRS):
        for k in KS:
            d = got.get((a, b, k), {})
            by_run = defaultdict(list)                 # (start, n) -> [risk, ...]
            for p in RISKS:
                for start, n in runs(set(range(REPS)) - d.get(p, set())):
                    by_run[(start, n)].append(p)
            for (start, n), ps in sorted(by_run.items()):
                # Chẻ theo rep nếu một shard vượt trần. Mỗi shard phải ≤ nửa trần $10 của
                # account, chừa chỗ cho một cú đắt bất ngờ — đã mất 3 shard vì tin probe
                # "còn quota" rồi đẩy shard $7,80 vào.
                #
                # Tính SỐ REP TỐI ĐA mỗi shard chứ đừng chia n cho số phần: `ceil(n/parts)`
                # làm phần lớn nhất vượt trần (brute force tìm ra 331 tổ hợp (n, giá, trần)
                # sinh shard vượt). Ở đây trần là trần CỨNG.
                per_rep = shard_cost(a, b, k, len(ps))
                step = max(1, min(n, int(max_cost // per_rep) if per_rep else n))
                for s0 in range(start, start + n, step):
                    m = min(step, start + n - s0)
                    out.append((a, b, k, ",".join(ps), s0, m,
                                shard_cost(a, b, k, m * len(ps))))
    return sorted(out, key=lambda s: s[6])


def take_batch(todo, n_slots, conc, cap):
    """Chọn shard cho MỘT đợt sao cho không model nào bị quá tải.

    §12 mục 3 đo thật: **shard song song × concurrency > ~8 request vào CÙNG một model là
    bão 429** — 4 shard × concurrency 4 = 16 làm 2/4 shard chết sau 72 giây. Với E3b thì
    nguy hơn E1/E2/E3a vì mỗi shard đánh vào HAI model, và thứ tự rẻ-trước **gom cụm** các
    shard cùng model: đếm thử đợt 1 với 19 account ra qwen ~31, grok ~25 request đồng thời.

    Nên vẫn giữ rẻ-trước (nó là thứ vét được nhiều ô nhất khi quota cạn dần), nhưng bỏ qua
    shard nào làm một model vượt trần, để dành nó cho đợt sau. Shard bị bỏ qua KHÔNG mất
    thứ tự ưu tiên — nó vẫn nằm đầu hàng đợi.
    """
    load, batch, rest = defaultdict(int), [], []
    for sh in todo:
        a, b = sh[0], sh[1]
        if len(batch) >= n_slots or load[a] + conc > cap or load[b] + conc > cap:
            rest.append(sh)
            continue
        load[a] += conc
        load[b] += conc
        batch.append(sh)
    return batch, rest


def label(sh) -> str:
    a, b, k, p, start, _, _ = sh
    ps = p.replace(",", "-") if p.count(",") < 2 else f"x{p.count(',') + 1}"
    return f"e3b_{SHORT[a]}x{SHORT[b]}_k{k}_p{ps}_s{start:02d}"


def one(sh, account: str, phase: str, wait: str, conc: str = "4") -> int:
    a, b, k, p, start, n, _ = sh
    lab = label(sh)
    idx = PAIRS.index((a, b))
    cmd = [sys.executable, str(LAUNCH), "--account", account, "--model", BARE[a],
           "--risks", p, "--langs", "en", "--reps", str(n), "--rep-start", str(start),
           "--max-out", "3000", "--concurrency", conc, "--task", task_of(a, b),
           "--seat-models", seat_spec(a, b, k, leads_a(idx, k)),
           "--label", lab, f"--{phase}-only"]
    if phase == "run":
        cmd += ["--wait", wait]
    logf = REPO / "plan" / "runs" / f"{lab}.{phase}.log"
    logf.parent.mkdir(parents=True, exist_ok=True)
    with open(logf, "w", encoding="utf-8") as fh:
        rc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT,
                            cwd=str(REPO)).returncode
    print(f"  {phase:<5} {lab:<34} {account:<14} rc={rc}", flush=True)
    return rc


def smoke(accounts, wait, dry):
    """1 ván cho mỗi tiền tố nhà sẽ được dùng ở GHẾ LẠ mà chưa ai xác nhận (~$0,07).

    Chỉ ghế lạ mới cần tiền tố đúng: slug của model `-m` được server tự chuẩn hoá (đo bằng
    pilot 11-09 — truyền `qwen3-…` thì `seat_model` ghi `qwen/qwen3-…`).

    Trong wave thật, ghế lạ luôn là vế SAU của cặp đã sắp xếp từ điển, nên tập nhà cần kiểm
    là các nhà xuất hiện ở vế sau: google, openai, qwen, xai. Pilot đã chứng minh `xai/`
    được chấp nhận và `qwen/` là dạng server tự sinh, nên chỉ còn **google và openai**.
    `anthropic/` KHÔNG bao giờ cần kiểm: haiku đứng đầu bảng từ điển nên nó luôn là `-m`.

    Sai một tiền tố là cả wave $82 chạy ra data mang tag sai — vài xu ở đây là rẻ.
    """
    # Chỉ liệt kê nhà đã được chứng minh Ở GHẾ LẠ. `qwen/` từng bị xếp nhầm vào đây: pilot
    # chỉ cho thấy server TỰ đặt tên client `-m` của nó là `qwen/qwen3-…`, mà ghế lạ đi
    # đường hoàn toàn khác (dựng client riêng rồi qua cổng `model_drift`). 3/10 cặp đặt
    # qwen ở ghế lạ = 450 ván, nên $0,02 kiểm là rẻ.
    VERIFIED = {"xai", "google", "openai"}          # pilot + smoke 11-09-2026
    foreign = {b for _, b in PAIRS}                 # vế sau = ghế lạ
    todo = sorted(b for b in foreign if SLUG[b].split("/")[0] not in VERIFIED)
    if not todo:
        print("SMOKE: moi tien to nha deu da duoc xac nhan.")
        return 0
    qwen = "qwen-qwen3-235b-a22b-instruct-2507"
    grok = "xai-grok-4.20-0309-non-reasoning"
    print(f"SMOKE {len(todo)} tien to nha chua xac nhan o GHE LA: "
          f"{', '.join(SLUG[b].split('/')[0] for b in todo)}")
    for b in todo:
        # Ghép với qwen và ép qwen làm `-m` (rẻ nhất, và đã xác nhận), để model cần kiểm
        # rơi vào ghế lạ. Cặp sắp xếp từ điển luôn cho qwen ở vế SAU với google/openai,
        # nên phải gọi launch_shard trực tiếp thay vì qua one().
        k = 3
        # `-m` chỉ cần là model nào đó KHÁC b — slug của nó được server tự chuẩn hoá nên
        # nó không phải thứ đang kiểm. Dùng qwen cho rẻ, trừ khi chính qwen là model cần
        # kiểm thì mượn grok.
        host = grok if b == qwen else qwen
        spec = ",".join([SLUG[b]] * k + [SELF] * (N_SEATS - k))
        lab = f"e3b_smoke_{SHORT[b]}_k{k}"
        cost = shard_cost(b, host, k, 1)
        print(f"  {lab:<28} ${cost:.3f}  -m={BARE[host]}  ghe la={SLUG[b]}")
        if dry:
            continue
        for phase in ("push", "run"):
            cmd = [sys.executable, str(LAUNCH), "--account", accounts[0],
                   "--model", BARE[host], "--risks", "0.9", "--langs", "en",
                   "--reps", "1", "--max-out", "3000", "--concurrency", "4",
                   "--task", "crg-e3b-smoke", "--seat-models", spec,
                   "--label", lab, f"--{phase}-only"]
            if phase == "run":
                cmd += ["--wait", wait]
            logf = REPO / "plan" / "runs" / f"{lab}.{phase}.log"
            logf.parent.mkdir(parents=True, exist_ok=True)
            with open(logf, "w", encoding="utf-8") as fh:
                rc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT,
                                    cwd=str(REPO)).returncode
            print(f"    {phase:<5} rc={rc}")
            if rc != 0:
                print(f"    !! hong o pha {phase} -> account het quota, HOAC proxy tu choi "
                      f"slug '{SLUG[b]}'. Xem {logf}")
                return 1
    if dry:
        print("(dry-run: chua goi lenh nao)")
        return 0
    print("SMOKE xanh: moi tien to nha deu duoc chap nhan o ghe la.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--accounts", default=None, help="cach nhau bang dau phay")
    ap.add_argument("--wait", default="21600")
    ap.add_argument("--max-rounds", type=int, default=20,
                    help="tran so dot. Tran tai/model cho ~5 shard/dot nen 62 shard can "
                         "~13 dot — de 8 la dung giua chung ma khong bao gi")
    ap.add_argument("--net-wait", type=int, default=300,
                    help="giay cho khi CA dot hong cung luc (ha tang, khong phai quota)")
    ap.add_argument("--concurrency", default="4",
                    help="so ghe goi song song trong 1 vong (mac dinh 4)")
    ap.add_argument("--model-cap", type=int, default=8,
                    help="tran TONG request dong thoi vao MOT model (§12 muc 3, mac dinh 8)")
    ap.add_argument("--max-cost", type=float, default=3.0,
                    help="tran $ moi shard; vuot thi che theo rep (mac dinh 3.0)")
    ap.add_argument("--smoke", action="store_true",
                    help="1 van moi tien to nha chua xac nhan (~$0,15)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    accounts = [a.strip() for a in (args.accounts or "").split(",") if a.strip()]

    if args.smoke:
        if not accounts and not args.dry_run:
            print("--smoke can --accounts <mot account>")
            return 2
        return smoke(accounts, args.wait, args.dry_run)

    shards = missing_shards(args.max_cost)
    if not shards:
        print("E3b: khong thieu o nao.")
        return 0
    n_games = sum(s[5] * len(s[3].split(",")) for s in shards)
    print(f"E3b: thieu {n_games} van · {len(shards)} shard · ~${sum(s[6] for s in shards):.2f}")
    print(f"     shard dat nhat ${max(s[6] for s in shards):.2f} (tran --max-cost {args.max_cost})")
    per = defaultdict(int)
    for a, b, k, p, _, n, _ in shards:
        g = n * len(p.split(","))
        per[a] += g
        per[b] += g
    print("     van co mat con thieu, theo model:")
    for t, n in sorted(per.items(), key=lambda x: -x[1]):
        print(f"       {SHORT[t]:<6} {n:>4}")
    if args.dry_run:
        return 0
    if not accounts:
        print("Can --accounts")
        return 2

    todo, rnd, acc_ptr = list(shards), 0, 0
    fails = defaultdict(int)          # label shard -> so lan push hong
    parked = []
    while todo and rnd < args.max_rounds:
        rnd += 1
        picked, todo = take_batch(todo, len(accounts), int(args.concurrency), args.model_cap)
        if not picked:
            print("Khong shard nao lot duoi tran tai/model. DUNG.")
            break
        # XOAY account qua từng đợt. Trần tải/model cắt mỗi đợt xuống ~5 shard, nên nếu cứ
        # lấy `accounts[i]` thì 5 account đầu gánh toàn bộ 62 shard (~$19/account, gấp đôi
        # trần $10) còn 14 account kia ngồi không — rồi wave chết vì 403 giữa chừng trong
        # khi quota tổng vẫn còn dư gấp mấy lần.
        batch = [(sh, accounts[(acc_ptr + i) % len(accounts)]) for i, sh in enumerate(picked)]
        acc_ptr = (acc_ptr + len(picked)) % len(accounts)
        load = defaultdict(int)
        for sh, _ in batch:
            load[SHORT[sh[0]]] += int(args.concurrency)
            load[SHORT[sh[1]]] += int(args.concurrency)
        print(f"\n=== DOT {rnd}: {len(batch)} shard, ${sum(b[0][6] for b in batch):.2f} ===")
        print("     tai/model: " + "  ".join(f"{m}={n}" for m, n in sorted(load.items())))
        print("PHA PUSH")
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=PUSH_CONC) as pool:
            pushed = list(pool.map(
                lambda b: (b, one(b[0], b[1], "push", args.wait, args.concurrency)), batch))
        ok = [b for b, rc in pushed if rc == 0]
        print(f"push {len(ok)}/{len(batch)} OK sau {(time.time() - t0) / 60:.0f} phut")

        # Push hỏng thì THỦ PHẠM có thể là account (hết quota) HOẶC shard (proxy từ chối
        # một slug ghế lạ — ở E3b bước validate chạy ván THẬT với đủ 6 ghế nên nó chạm tới
        # ghế lạ). `launch_shard.py` trả cùng một mã lỗi cho cả hai. Quy kết mù quáng cho
        # account nghĩa là MỘT shard xấu có thể xoá sổ 8 account khoẻ qua 8 đợt.
        # Nên: hỏng lần đầu -> nghi cho account; hỏng lần hai trên account KHÁC -> lỗi nằm
        # ở shard, park nó lại và trả account về.
        # TOÀN BỘ đợt hỏng cùng lúc thì thủ phạm KHÔNG phải quota. Quota cạn theo từng
        # account, không thể làm 5/5 hỏng trong cùng một giây. Đo thật 11-09-2026: mất DNS
        # (`Failed to resolve 'api.kaggle.com'`) làm cả 5 auth hỏng trong 2 giây, và bản
        # đầu của vòng lặp này đã loại sạch 5 account khoẻ rồi dừng wave.
        # Hạ tầng hỏng thì KHÔNG được loại account nào — chờ rồi thử lại.
        if not ok and len(pushed) > 1:
            print(f"  !! CA {len(pushed)}/{len(pushed)} shard hong cung luc -> khong phai "
                  f"quota ma la HA TANG (mang/DNS/Kaggle). Khong loai account nao.")
            print(f"     doi {args.net_wait}s roi thu lai dot nay.")
            todo = [b[0] for b, _ in pushed] + todo
            time.sleep(args.net_wait)
            rnd -= 1                      # đợt này không tính, thử lại nguyên vẹn
            continue

        retry = []
        for b, rc in pushed:
            if rc == 0:
                continue
            sh, acc = b
            lab = label(sh)
            fails[lab] += 1
            if fails[lab] >= 2:
                print(f"  !! {lab} hong tren {fails[lab]} account khac nhau "
                      f"-> LOI O SHARD, park lai")
                parked.append(sh)
            else:
                print(f"  het quota? loai {acc} (shard {lab} tra ve hang doi)")
                accounts = [a for a in accounts if a != acc]
                retry.append(sh)
        todo = retry + todo
        if not ok:
            print("Khong shard nao push duoc. DUNG.")
            break
        print("PHA RUN")
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=len(ok)) as pool:
            ran = list(pool.map(
                lambda b: (b, one(b[0], b[1], "run", args.wait, args.concurrency)), ok))
        bad_run = [label(b[0]) for b, rc in ran if rc != 0]
        print(f"run {sum(1 for _, rc in ran if rc == 0)}/{len(ok)} OK sau "
              f"{(time.time() - t0) / 60:.0f} phut")
        if bad_run:
            # Ô của shard hỏng ở pha RUN vẫn còn thiếu, và `--dry-run` tìm lại được (have()
            # đọc data ĐÃ TẢI VỀ chứ không đọc ý định). Nhưng vứt im lặng thì không ai biết
            # là phải chạy lại — nên in ra.
            print(f"  run hong ({len(bad_run)}): {' '.join(bad_run)}")
            print("  -> chay lai chinh lenh nay; --dry-run liet ke o con thieu")
        if not accounts:
            print("Het account. DUNG.")
            break

    if parked:
        print(f"\n!! {len(parked)} shard bi park (hong tren >=2 account khac nhau):")
        for sh in parked:
            idx = PAIRS.index((sh[0], sh[1]))
            print(f"   {label(sh)}  seats={seat_spec(sh[0], sh[1], sh[2], leads_a(idx, sh[2]))}")
        print("   Nhieu kha nang proxy tu choi mot slug ghe la. Doc log truoc khi chay lai.")

    # `--experiment` EP ten cho MOI shard tim thay chu KHONG loc. Quet ca `plan/runs` va
    # `D:/tmp/crgdl` se do 131 games.csv KHONG phai E3b (baseline, E1, E2, E3a, va ca
    # gpt-5.6-sol / claude-opus-5 NGOAI panel) vao `results/exp_mixed/` — cong danh tinh
    # panel se no, va cay `results/` da commit bi ban. Nen `--src` phai tro DUNG task E3b.
    print("\nGom ve results/ — CHI tro --src vao thu muc task E3b:")
    print(f"  python plan/scripts/to_wide_csv.py --experiment exp_mixed \\")
    print(f"      --src {DL}/*/crg-e3b-haiku-* {DL}/*/crg-e3b-flash-* \\")
    print(f"            {DL}/*/crg-e3b-luna-* {DL}/*/crg-e3b-qwen-*")
    print("  python plan/scripts/verify_wide.py --expect-reps 10")
    print("  # KHONG dung --src plan/runs D:/tmp/crgdl (quet bua -> lam ban results/)")
    print("Kiem con thieu: python plan/scripts/launch_e3b.py --dry-run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
