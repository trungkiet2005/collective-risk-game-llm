# CLAUDE.md — quy ước làm việc trong repo CRSD-LLM

Tài liệu trạng thái/lộ trình nằm ở [PROJECT.md](PROJECT.md). File này chỉ ghi các
quy ước bắt buộc khi sửa code.

## 👉 Việc đang làm: đọc [plan/README.md](plan/README.md) trước

`plan/` giữ kế hoạch **đang thực thi** + trạng thái data hiện có + checkbox tiến độ.
PROJECT.md đã lạc hậu so với thực tế; `plan/` mới là nguồn đúng cho câu "giờ làm gì tiếp".

- [plan/runbook-top-tier.md](plan/runbook-top-tier.md) — **đang chạy**: hướng dẫn thực thi bậc đỉnh (phân account, chia shard, gom result)
- [plan/frontier-run-plan.md](plan/frontier-run-plan.md) — kế hoạch tổng nhánh frontier
- [plan/model-availability.md](plan/model-availability.md) — 38 slug proxy: sống/chết/giá (probe 12-08-2026)

**Ba sự thật đắt tiền, đừng phát hiện lại:** (1) local và server-side dùng 2 proxy KHÁC
NHAU — local chỉ 6/38 model, server-side 28/38, nên 503 ở local KHÔNG có nghĩa model chết;
(2) 503 là lỗi phía Kaggle chứ không phải hết quota (đã kiểm bằng 3 account cho ra cùng tập
503) → đổi account vô ích; (3) proxy đặt cọc tiền trước theo `max_output_tokens` chứ không
theo token thực tiêu, nên không cap thì model đắt bị 403 dù thực tế tốn vài xu.

## ⛔ Kaggle Benchmarks: CHỈ chạy SERVER-SIDE, KHÔNG chạy local

**Quy ước bắt buộc từ 10-09-2026.** Mọi ván CRSD sinh bằng Kaggle Benchmarks phải chạy
server-side, tức là qua `kaggle b t push` rồi `kaggle b t run` (bọc sẵn trong
`plan/scripts/launch_shard.py` và các script `launch_*.py` / `run_dense_grid.py` gọi nó).
**KHÔNG chạy `python kaggle/benchmarks/crg_task_server.py` trên máy để sinh data**, kể cả
khi chỉ định "chạy thử vài ván cho nhanh".

Lý do — chính là sự thật số (1) ở trên: local đọc `.env` → `mp-staging` và chỉ phục vụ
**6/38 model**, server-side phục vụ **28/38**. Chạy local nghĩa là:

- panel bị cắt xuống còn những model nào tình cờ sống ở staging, tức là **không so sánh
  được** với data server-side đã có;
- gặp 503 rồi tưởng model chết, kết luận sai về availability;
- không có log `kaggle b t status` / artifact `.run.json`, nên không truy lại được run
  nào sinh ra file nào.

**Ngoại lệ duy nhất — probe, KHÔNG phải data.** Được phép gọi proxy local cho việc rẻ và
dùng một lần: `plan/scripts/probe_all_models.py` (liveness), `probe_crg_prompt.py` (kiểm
một lượt CRG parse được không), và `crsd/tests/test_kaggle_*.py`. Kết quả của những lệnh
này **không bao giờ** được ghi vào `results/` hay đưa vào paper.

## Artifact `.task.json` / `.run.json` → `kaggle/benchmarks/artifacts/`

**Mọi file `<task-name>.task.json` và `<task-name>-run_id_*.run.json` phải nằm trong
[`kaggle/benchmarks/artifacts/`](kaggle/benchmarks/artifacts/)** — không để lăn lóc ở root
repo. Đây là nơi duy nhất chứa artifact của Kaggle Benchmarks, và nó được commit vào git
(đó là bản ghi duy nhất truy lại được run nào sinh ra file nào).

**Cái bẫy:** kbench ghi hai file này ra **thư mục đang đứng (CWD)**, chứ không phải cạnh
file task. Nên `python kaggle/benchmarks/crg_task_server.py` chạy từ root sẽ rải artifact
ra root. Muốn nó rơi đúng chỗ thì `cd kaggle/benchmarks/artifacts` rồi mới chạy; lỡ rơi ra
root rồi thì `git mv` vào đây ngay, đừng để tồn.

Trùng tên là chuyện bình thường — cùng một task chạy lại sẽ đè lên `.task.json` cũ. Cứ đè,
vì bản cũ đã được track trong git nên lấy lại từ history được; đừng đẻ thêm hậu tố
`_v2`, `_new` để né trùng.

## Kết quả: `Lagecy_Results/results/` là ĐỒ CŨ, `results/` là đồ đang chạy

**Từ 10-09-2026 thư mục `results/` cũ đã được chuyển sang `Lagecy_Results/results/`.**

| Thư mục | Là gì | Được làm gì với nó |
|---|---|---|
| `Lagecy_Results/results/` | Toàn bộ data cũ tới 10-09-2026: `open_source/`, `frontier/`, `frontier/dense_grid/`, `scripted_reference/`, `raw/` | **ĐÓNG BĂNG.** Chỉ đọc, không ghi đè, không xoá. |
| `results/` | Data của vòng chạy MỚI (nhánh `aamas2027-e0`) — mọi run server-side từ nay đổ về đây | Nơi duy nhất script gom shard được phép ghi |

**Đừng tự ý đọc / phân tích `Lagecy_Results/` rồi viết vào paper.** Data cũ chỉ được lôi ra
khi **người dùng yêu cầu rõ ràng**; lúc đó mới đọc, phân tích, và ghi kết quả vào
`paper/`. Không có yêu cầu thì coi như thư mục đó không tồn tại — kể cả khi đang thiếu số
để điền vào một bảng trong paper. Lý do: data cũ trải nhiều panel/prompt khác nhau, trộn
nhầm vào bảng mới là lỗi âm thầm và rất khó phát hiện lúc review.

⚠️ **Code còn hardcode `results/`** — `plan/scripts/fill_missing.py` và mặc định
`--out results/frontier` của `merge_shards.py`. Với run MỚI thì hai chỗ này ĐÚNG, không
cần sửa.

⚠️ **Pipeline phân tích bản Interface Focus hiện ĐANG HỎNG ĐƯỜNG DẪN, và đó là cố ý để
nguyên.** Hai lần dời thư mục (10-09-2026) làm nó trỏ trượt:

- `paper/Interface_Focus/revision/_data.py` có `ROOT = parents[2]`, tính từ vị trí cũ
  `paper/revision/`. Sau khi dời sang `paper/Interface_Focus/revision/`, `ROOT` ra `paper/`
  nên `RESULTS` thành `paper/results` — không tồn tại.
- `make_figures*.py` glob `../results/open_source/` và `../results/frontier/*/...`, cũng lệch
  một cấp.

Cả hai sẽ **ra kết quả rỗng thay vì báo lỗi**. Đừng sửa và đừng chạy chúng cho tới khi người
dùng yêu cầu dựng lại figure bản IF; lúc đó mới trỏ sang `Lagecy_Results/results/` (data của
bản IF nằm ở đó, không phải ở `results/` mới).

## Notebook Kaggle (`kaggle/experiments/*.py`)

- **Tên file zip output = `<tên file notebook>_results.zip`**, đặt ở
  `/kaggle/working/` (Cell 8 cuối mỗi notebook). Ví dụ:
  - `baseline.py`   → `/kaggle/working/baseline_results.zip`
  - `persona.py`    → `/kaggle/working/persona_results.zip`
  - `comprehension.py` → `/kaggle/working/comprehension_results.zip`

  Lý do: tải nhiều notebook về rồi bỏ vào `results/raw/` thì nhìn tên zip biết ngay
  của experiment nào — KHÔNG dùng tên chung `crsd_results.zip` nữa.

  Thư mục kết quả bên trong zip vẫn giữ `crsd_results/<model_short>/<experiment>/`
  (đừng đổi — script phân tích đang đọc theo cấu trúc này).

- Khi tạo notebook mới bằng cách copy từ notebook cũ: nhớ sửa `zip_path` ở Cell 8
  và dòng "Output:" trong docstring cho khớp tên file mới.

- Các bản trong `kaggle/experiments/archive/` là bản cũ KHÔNG dùng nữa — không cần
  sửa theo quy ước này trừ khi lấy ra dùng lại.

## Kaggle Benchmarks — credential & cách switch khi hết (Model Proxy)

**Kho credential (NGOÀI repo, KHÔNG check vào git — đừng dán key thật vào file này):**
`D:\AI_PhD\GameTheory\kaggle_for_research\`
- `kaggle-api\*.txt`   — 7 token `KGAT_...`, **tên file = tên account** (chiboiz, chinguyentran,
  chisboiz, chunaiu, trnnguynchis, trunkdabest, vinhdinhthien).
- `kaggle-api-2\*.md`  — 5 token `KGAT_...` (acc1–acc5), token là dòng bắt đầu bằng `KGAT_`.
- `kaggle*.json` (root) — 5 cặp `username/key` kiểu cũ (foundnotkiet, kit567, hunhtrungkit,
  tnkiet, trungkiet).

**Tổng 17 account. Probe lại 2026-09-10: chỉ còn 14 sống.**
- ❌ **BỎ QUA 3 account** — cùng một lỗi `403 "missing phone/identity verification"` khi xin
  Model Proxy key (login và xem model list vẫn được, nên đừng tưởng là còn dùng được):
  `trnnguynchis` (từ 12-08), **`chiboiz`** và **`chinguyentran`** (mới hỏng, phát hiện 10-09).
- ✅ **14 account sống:** acc1–acc5, chisboiz, chunaiu, foundnotkiet, hunhtrungkit, kit567,
  tnkiet, trungkiet, trunkdabest, vinhdinhthien.
- **Sức khoẻ account TRÔI theo thời gian** — mất 2 account trong 4 tuần. Probe lại trước mỗi
  đợt chạy lớn; đừng tin danh sách cũ. Probe rẻ và nhanh: `kaggle b auth -y --env-file <tmp>`
  cho từng account, chạy song song 8 luồng, xong trong ~1 phút.

**Cách nạp credential (2 kiểu, chọn 1 theo nguồn):**
```bash
export KAGGLE_CONFIG_DIR=<thư mục riêng cho account này>   # tránh đụng ~/.kaggle
# kiểu token (kaggle-api/, kaggle-api-2/):
export KAGGLE_API_TOKEN=KGAT_xxxxxxxx
# kiểu cũ (kaggle*.json): đặt username/key hoặc copy file thành $KAGGLE_CONFIG_DIR/kaggle.json
export KAGGLE_USERNAME=... ; export KAGGLE_KEY=...
```

**Lấy Model Proxy key rồi gọi (chuẩn OpenAI-compatible):**
```bash
kaggle benchmarks auth -y --env-file account.env   # ghi MODEL_PROXY_URL + MODEL_PROXY_API_KEY
# POST tới: <MODEL_PROXY_URL>/openapi/chat/completions
#   Authorization: Bearer <MODEL_PROXY_API_KEY>
#   body: {"model":"gpt-5.4-nano-2026-03-17","messages":[...],"max_completion_tokens":N}
```
- MODEL_PROXY_URL hiện tại: `https://mp-staging.kaggle.net/models`
- **Proxy key HẾT HẠN sau ~2 tiếng** (`MODEL_PROXY_EXPIRY_TIME`). Hết thì chạy lại
  `kaggle benchmarks auth` cùng account để làm mới — KHÔNG cần đổi account.
- Response trả kèm `usage.cost` (nanodollars) để theo dõi chi phí/quota.

**Khi 1 account hết quota / rate-limit / key hết hạn không xin lại được → switch:**
1. Chuyển sang account kế tiếp trong danh sách 16 account sống (mỗi account 1
   `KAGGLE_CONFIG_DIR` riêng để creds không đè nhau).
2. Chạy lại `kaggle benchmarks auth` để lấy proxy key mới cho account đó.
3. Bỏ qua `trnnguynchis` cho tới khi được verify.
4. Muốn kiểm tra nhanh account nào còn sống: gọi thử `gpt-5.4-nano` với prompt 1 chữ
   (rẻ nhất) — có `"choices"` trong response là OK.
