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

**Tổng 17 account. Test 2026-08-12: 16 gọi inference OK, 1 hỏng.**
- ❌ **BỎ QUA `trnnguynchis`** (kaggle-api\trnnguynchis.txt): login + xem model list được
  nhưng xin Model Proxy key bị **403 "missing phone/identity verification"**. Chỉ dùng lại
  sau khi verify SĐT/danh tính trên Kaggle.
- 16 account còn lại: đăng nhập OK, thấy đủ 38 model, chạy inference thật OK.

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
