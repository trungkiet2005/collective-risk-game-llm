# Kaggle Model Proxy — cái nào sống, sống ở đâu, giá bao nhiêu

**Bảng giá/liveness bên dưới: probe 12-08-2026.** Danh mục lấy từ `kaggle b t models`.
Probe lại bằng script trong [scripts/](scripts/) nếu cần cập nhật.

## ⚠️ Danh mục đã đổi — kiểm lại 09-09-2026 (account `chisboiz`)

**38 → 42 slug.** Danh mục **trôi khoảng 1 model/tuần**, nên đừng tin bảng cũ quá 2 tuần.

**🔴 BIẾN MẤT — `gpt-5.6-sol`.** Đây là một trong **hai model EV-optimal** của paper
(hiệu ứng risk +118.2). Dữ liệu 140 ván đã có vẫn dùng được, nhưng **không chạy thêm được
gì trên nó nữa** — mọi thí nghiệm cần model đó (E3b cặp 3, E6 robustness, staircase E4)
phải đổi sang model khác. Model EV-optimal duy nhất còn lại là **`gemini-3.1-pro-preview`**.

**🟢 MỚI — 5 slug:**

| Slug | Nhà | Đáng chú ý |
|---|---|---|
| `claude-sonnet-5-default` | Anthropic | bậc giữa thế hệ 5, chưa probe |
| `gemini-3.7-flash` | Google | chưa probe |
| `gemini-3.8-flash` | Google | chưa probe |
| `grok-4.5-0708` | xAI | thế hệ mới sau 4.20 |
| `grok-4.6` | xAI | thế hệ mới nhất của xAI |

Bốn slug Qwen3 + `glm-5` + `deepseek-*` **vẫn còn trong danh mục** (danh mục liệt kê ≠ phục vụ
được — chúng 503 ở lần probe 12-08). Xem [§Qwen probe 09-09](#qwen-probe-server-side-09-09-2026).

## Sự thật quan trọng nhất: local và server-side là 2 proxy khác nhau

| Đường chạy | Proxy | Số model phục vụ |
|---|---|---|
| Local (`python task.py`, đọc `.env`) | `https://mp-staging.kaggle.net/models` | **6 / 38** |
| Server-side (`kaggle b t run -m <slug>`) | proxy production | **28 / 38** |

Model báo 503 ở local **hoàn toàn có thể chạy tốt server-side** — đừng kết luận nó chết.
Đây là lý do `claude-haiku` từng bị tưởng là "backend Anthropic sập".

**503 là lỗi phía Kaggle, không phải hết quota.** Đã kiểm chứng bằng 3 account độc lập
(`chiboiz`, `acc1`, `kaggle.json`) cho ra **đúng cùng một tập 503**. Đổi account không cứu được.

---

## Sống ở local (staging) — 6 model

Chỉ 6 slug này chạy được khi dev/iterate trên máy.

| Slug | out_tok cho 1 chữ "OK" | Ghi chú |
|---|---|---|
| `gemini-3.1-flash-lite-preview` | 1 | rẻ nhất, không reasoning overhead |
| `gemini-3.5-flash-lite` | 1 | như trên |
| `gpt-5.4-nano-2026-03-17` | 4 | **đã unblock** — tháng 7/2026 còn 503 ở local |
| `gemini-3-flash-preview` | 51–4534 | reasoning nặng |
| `gemini-3.5-flash` | 68 | cần budget ≥2000 mới ra JSON hợp lệ |
| `gemini-3.6-flash` | 105 | trả **rỗng** ở budget 64 |

Cả 6 đã kiểm bằng prompt CRG thật (1 lượt quyết định) → đều parse ra
`{"contribution": 4, ...}` khi budget đủ.

`gpt-oss-120b` chạy được **1 lần** rồi 429 liên tục ~13 lần thử → coi như không dùng được ở local.

---

## Sống server-side — 28 model, đã kiểm reply thật

Tất cả đều trả về đúng chuỗi `OK` (trừ `gpt-oss-120b`, xem mục lỗi bên dưới).
Cột `$/60 ván` là **ước tính, sai số ±3×** — xem [phần phương pháp](#phương-pháp-tính-giá).

| Slug | probe $ | $/ván (ước) | $/60 ván (ước) | Tầng |
|---|---|---|---|---|
| `grok-4.20-0309-non-reasoning` | 0.000085 | 0.0115 | 0.69 | A |
| `gpt-5.4-nano-2026-03-17` | 0.000008 | **0.0073 đo thật** | **0.44 đo thật** | A |
| `gemini-3.1-flash-lite-preview` | 0.000003 | **0.0220 đo thật** | **1.32 đo thật** | A |
| `gemma-4-31b-it` | 0.000032 | 0.0242 | 1.45 | A |
| `gemma-4-26b-a4b-it` | 0.000034 | 0.0244 | 1.47 | A |
| `gemini-3.5-flash-lite` | 0.000005 | 0.0252 | 1.51 | A |
| `gpt-5.6-luna` | 0.000386 | 0.0484 | 2.91 | B |
| `grok-4.20-0309-reasoning` | 0.000788 | 0.0578 | 3.47 | B |
| `gpt-5.4-mini-2026-03-17` | 0.000029 | 0.0730 | 4.38 | B |
| `claude-haiku-4-5-20251001` | 0.000035 | 0.0834 | 5.01 | B |
| `gemini-2.5-flash` | 0.000067 | 0.0893 | 5.36 | B |
| `gemini-3-flash-preview` | 0.000157 | 0.1205 | 7.23 | B |
| `gpt-5.6-terra` | 0.000965 | 0.1211 | 7.27 | B |
| `gpt-5.4-2026-03-05` | 0.000095 | 0.2391 | 14.35 | C |
| `gpt-5.6-sol` | 0.001930 | 0.2422 | 14.53 | C |
| `claude-sonnet-4-6-default` | 0.000105 | 0.2503 | 15.02 | C |
| `claude-sonnet-4-5-20250929` | 0.000105 | 0.2503 | 15.02 | C |
| `claude-sonnet-4-20250514` | 0.000105 | 0.2503 | 15.02 | C |
| `gemini-3.6-flash` | 0.000799 | 0.3203 | 19.22 | C |
| `gemini-3.5-flash` | 0.000624 | 0.3719 | 22.32 | C |
| `claude-opus-4-8-default` | 0.000185 | 0.3991 | 23.94 | C |
| `claude-opus-4-5-20251101` | 0.000175 | 0.4172 | 25.03 | C |
| `claude-opus-4-6-default` | 0.000175 | 0.4172 | 25.03 | C |
| `gemini-2.5-pro` | 0.001770 | 0.4358 | 26.15 | C |
| `gemini-3.1-pro-preview` | 0.001252 | 0.5110 | 30.66 | C |
| `claude-opus-5-default` | 0.000460 | 0.6512 | 39.07 | D |
| `gpt-5.5-2026-04-23` | 0.000550 | 0.8305 | 49.83 | D |
| `claude-opus-4-1-20250805` | 0.000525 | 1.2517 | 75.10 | D |

Tầng: **A** ≤$2 · **B** $2–8 (vừa 1 account) · **C** $14–31 (chia 2–4 run) · **D** >$39 (chia 5+ run)

---

## Qwen probe server-side 09-09-2026

Probe thật bằng `crg-proxy-probe` trên account `chisboiz`, production proxy:

| Slug | Kết quả | Chi tiết |
|---|---|---|
| `qwen3-235b-a22b-instruct-2507` | ✅ **COMPLETED — SỐNG LẠI** | `reply: 'OK'`, 16 in / 2 out, cost $0.000005 → **~$0.019/ván, ~$1.13/60 ván (tầng A)** |
| `qwen3-coder-480b-a35b-instruct` | ⚠️ **ERRORED — 429** | `RateLimitError: The model is currently experiencing heavy load. Try again later.` |

**Hai kết luận:**

1. **`qwen3-235b` không còn chết.** Ngày 12-08 nó 503 ở cả hai proxy; ngày 09-09 nó trả lời
   bình thường server-side. Nhánh frontier **giờ có đại diện lab Trung Quốc** — trước đó
   panel chỉ có 4 nhà phương Tây. Và nó rẻ (tầng A).
2. **`qwen3-coder-480b` KHÔNG chết, nó quá tải.** 429 ≠ 503: 503 là "model không được phục vụ",
   429 là "đang phục vụ nhưng hết chỗ". Giống hệt `deepseek-v3.1`. Coi như **không đặt lịch
   được**, đừng đưa vào kế hoạch cần chạy đúng hạn, nhưng thử lại thì có thể trúng.

**Bài học đắt tiền thứ tư (bổ sung cho ba cái ở [README.md](README.md)): đọc MÃ LỖI, đừng đọc
"Errored".** Bốn mã lỗi khác hẳn nhau đều hiện ra là **cùng một chữ `Errored`** trong
`kaggle b t status`, mà cách xử lý thì ngược nhau hoàn toàn:

| Mã | Nghĩa | Xử lý | Ví dụ gặp thật |
|---|---|---|---|
| **503** | proxy không phục vụ model này | **bỏ hẳn** | `glm-5`, `deepseek-r1` |
| **429** | sống nhưng quá tải | **thử lại**, đừng đưa vào kế hoạch có hạn | `qwen3-coder-480b`, `deepseek-v3.1` |
| **403** | tiền cọc theo `max_output_tokens` vượt quota | **hạ cap**, model vẫn tốt | `claude-opus-4-7-default` |
| **404** | có trong danh mục nhưng backend không biết | **đợi**, danh mục chạy trước backend | `grok-4.5-0708`, `grok-4.6` |

Phải mở phần `Errors:` của `kaggle b t status` (hoặc `kaggle b t log`) mới phân biệt được.
`kaggle b t log -m <slug>` của một run ERRORED **không in mã lỗi** — chỉ có dòng header;
mã lỗi nằm ở `status`.

## Probe đầy đủ 09-09-2026 — 10 model, account `chisboiz`

Giá tính bằng công thức `(probe_cost / probe_tokens) × 45.300`, rồi **×1,5** theo quy tắc
hiệu chỉnh mới. Cột "60 ván" là chi phí một sweep chuẩn (3 risk × 10 rep, tiếng Anh).

| Slug | Nhà | Kết quả | $/ván | $/60 ván | Tầng |
|---|---|---|---|---|---|
| `qwen3-235b-a22b-instruct-2507` | Alibaba | ✅ OK | **0,019** | 1,13 | A |
| `grok-4.20-0309-non-reasoning` | xAI | ✅ OK | **0,023 đo thật** | 1,36 | A |
| `gemini-3.5-flash-lite` | Google | ✅ OK | **0,034** | 2,04 | A |
| `gpt-5.6-luna` | OpenAI | ✅ OK | **0,073** | 4,36 | B |
| `claude-haiku-4-5-20251001` | Anthropic | ✅ OK | **0,125** | 7,51 | B |
| `gemini-3.8-flash` 🆕 | Google | ✅ OK | 0,241 ⚠️ | 14,5 | C |
| `claude-sonnet-5-default` 🆕 | Anthropic | ✅ OK | **0,359** | 21,5 | C |
| `gemini-3.7-flash` 🆕 | Google | ✅ OK | 0,464 ⚠️ | 27,8 | C |
| `qwen3-coder-480b-a35b-instruct` | Alibaba | ❌ 429 ×2 lần | — | — | không đặt lịch được |
| `grok-4.5-0708` 🆕 | xAI | ❌ 404 | — | — | danh mục có, backend chưa có |
| `grok-4.6` 🆕 | xAI | ❌ 404 | — | — | danh mục có, backend chưa có |

⚠️ **Hai model `gemini-3.x-flash` có giá ĐÁNG NGỜ CAO.** Probe của chúng trả 70 và 127 token
output cho một câu trả lời một chữ — reasoning token. Theo chính phần
[phương pháp](#phương-pháp-tính-giá), probe nặng output làm **ước tính lệch CAO**, nên giá
thật nhiều khả năng thấp hơn con số trên. Muốn dùng thì phải đo thật trước, và nhớ đặt
`max_completion_tokens` ≥ 6000 nếu không chúng trả về rỗng.

**Phát hiện đáng giá nhất: Anthropic giờ có thang 3 nấc sạch** —
`claude-haiku-4-5` ($0,125) → `claude-sonnet-5-default` ($0,359) → `claude-opus-5` ($0,682 đo thật),
cùng nhà, ba bậc năng lực rõ ràng. Đây là **thang thay thế tốt nhất cho thang `gpt-5.6`
luna/terra/sol đã mất một nấc** khi `gpt-5.6-sol` bị gỡ khỏi danh mục.

## ⚠️ Bẫy `CRG_MAX_OUT`: cổng `parse_failed` KHÔNG bảo vệ được bạn (10-09-2026)

`crg_task_server.py` đặt cap output theo heuristic tên model:
`MAX_OUT = 6000 nếu tên chứa "reasoning hint", ngược lại 512`.

Đo thật (smoke 2 ván/model, 120 quyết định):

| Model | out_tok / quyết định | Cap được cấp | Sát cap? |
|---|---|---|---|
| `claude-haiku-4-5` | **476,4** | **512** | 🚨 **93%** |
| `gemini-3.5-flash-lite` | 149,4 | 6000 | không |
| `gpt-5.6-luna` | 71,2 | 6000 | không |
| `qwen3-235b` | **8,0** | 512 | không |

**Vì sao nguy hiểm:** khi output bị cắt trước dòng `CONTRIBUTION: n`, `parse_contribution`
rơi xuống nhánh **quét mọi chữ số trong văn bản** rồi lấy số cuối thuộc {0,2,4} — và trả
`parse_failed=False`. Nên **`parse_fail_rate = 0.0` vẫn xanh trong khi dữ liệu là bịa.**
Mọi cổng kiểm tra sức khoẻ của repo đều dựa vào chỉ số này.

**Độ lớn thực tế:** so cap 512 với cap 3000 trên cùng seed, out_tok/quyết định chỉ đổi
471,3 → 476,4. Tính ngược từ độ hụt 5 token ⇒ tỉ lệ bị cắt khoảng **1–3%**, không phải
hàng chục phần trăm. Nhưng hành vi có đổi (GT 122 → 131 ở n=2).

**Cách xử lý:** nâng cap là **gần như miễn phí** — $0,1765 → $0,178/ván, trong sai số.
Cứ đặt `--max-out 3000` cho mọi model không có "reasoning hint" mà sinh > ~300 token/quyết
định. Kiểm bằng `usage_output_tokens / n_decisions` trong summary của mọi run.

## 💰 Cách đo QUOTA CÒN LẠI của từng account (10-09-2026)

Không có API hỏi quota. Nhưng vì proxy **đặt cọc theo `max_output_tokens`**, ta lợi dụng chính
cơ chế đó: gọi một request rẻ với cap LỚN. Nếu account hết quota, nó trả 403 kèm số tiền cọc.

```python
# body: {"model":"gemini-3.5-flash-lite","messages":[...],"max_completion_tokens":6000}
# -> 200 = con quota ; 403 "max estimated cost of operation ($0.015) exceeds your
#    available quota" = con it hon $0.015
```

**⚠️ Phải dùng model CÓ TRÊN LOCAL STAGING PROXY** (6 model: `gemini-3.1-flash-lite-preview`,
`gemini-3.5-flash-lite`, `gemini-3-flash-preview`, `gemini-3.5-flash`, `gemini-3.6-flash`,
`gpt-5.4-nano`). Probe bằng `gpt-5.6-luna` trả **404 "model not found" cho CẢ 14 account** —
không phải hết quota, mà là model đó chỉ có server-side. Đây đúng là bẫy "hai proxy khác nhau"
ở đầu file, rất dễ đọc nhầm 404 thành "account hỏng".

**Kết quả 10-09-2026 sau sweep lưới dày:** 12/14 account "còn quota"; `acc5` và `trungkiet` cạn
(cả hai chạy shard `gpt-5.6-luna` — shard đắt nhất, $8.60). Quota **KHÔNG reset theo lịch ngày**:
acc5 vẫn 403 sau 5 tiếng và sau nửa đêm UTC → nhiều khả năng là cửa sổ trượt 24h.

### ⚠️ Probe này chỉ trả lời ĐÚNG/SAI, KHÔNG trả lời CÒN BAO NHIÊU

Bài học trả giá bằng 3 lần shard hỏng (10-09): probe với cap 6000 chỉ đặt cọc **$0.015**, nên
account còn **$0.02** cũng báo "CÒN QUOTA". Tôi tin nó rồi chuyển shard `gpt-5.6-luna` ($7.80)
sang `trunkdabest` — account vừa báo còn quota — và nó vẫn 403 sau 12 phút.

Sự thật: sau một sweep tiêu ~$7.7/account, **mọi account chỉ còn ~$2–3**, không cái nào chứa
nổi một shard $7.8. "Còn quota" ≠ "đủ cho shard của bạn".

**Cách probe đúng khi cần biết ngưỡng:** dò nhị phân trên `max_completion_tokens` — tăng cap
tới khi 403, tiền cọc ở ngưỡng đó xấp xỉ quota còn lại. Hoặc đơn giản hơn: **ước quota đã tiêu
bằng chính chi phí shard đã chạy trên account đó** (`usage_total_cost_usd` trong log), rồi lấy
$10 trừ đi. Rẻ hơn và chính xác hơn probe.

## ⚡ `--concurrency`: đòn bẩy wall-clock miễn phí

`CRG_CONCURRENCY` song song hoá 6 ghế trong MỘT vòng (`ThreadPoolExecutor.map` giữ nguyên
thứ tự input ⇒ output byte-identical với đường tuần tự). **Không đổi chi phí, chỉ giảm thời
gian.** Đo thật trên haiku, 2 ván: `concurrency=1` 626,5s → `concurrency=4` **207,5s (3,0×)**.

Trước 10-09 `launch_shard.py` không truyền được biến này; đã thêm cờ `--concurrency`.

## Chết hoặc không dùng được — 10 slug (probe 12-08, xem mục trên để biết cập nhật)

| Slug | Lỗi | Đánh giá |
|---|---|---|
| `qwen3-next-80b-a3b-instruct` | 503 cả 2 proxy | chết |
| `qwen3-next-80b-a3b-thinking` | 503 cả 2 proxy | chết |
| `qwen3-235b-a22b-instruct-2507` | 503 cả 2 proxy | chết |
| `qwen3-coder-480b-a35b-instruct` | 503 cả 2 proxy | chết |
| `glm-5` | 503 cả 2 proxy | chết |
| `gpt-oss-20b` | 503 cả 2 proxy | chết |
| `deepseek-r1-0528` | 503 | chết |
| `deepseek-v3.1` | 429 heavy load, mọi lần thử | còn sống nhưng không đặt lịch được |
| `gpt-oss-120b` | Completed nhưng `reply` rỗng | **không dùng được** — token chảy vào reasoning channel, content trống. Status xanh che mất lỗi |
| `claude-opus-4-7-default` | 403 tiền cọc | **không chết** — sẽ chạy được sau khi set `max_output_tokens` |

Ghi chú quan trọng: **cả nhánh "scaling >32B" bằng Qwen3 80B–480B hiện không chạy được
chút nào.** `deepseek-v3.2` (từng được chọn làm open arm) **không còn trong danh mục** — chỉ còn v3.1.

---

## Hai lỗi ẩn phải phòng trong code

1. **Content rỗng nhưng status xanh.** `gpt-oss-120b` trả `reply: ''`, tokens vẫn bị tính.
   Task phải fail to tiếng khi `reply == ""`, không được ghi thành ván đóng góp 0.

2. **Reasoning token ăn hết budget.** `gemini-3.6-flash` trả rỗng ở `max_completion_tokens=64`;
   `gemini-3.5-flash` không sinh nổi JSON hợp lệ ở 2000. Ở 6000 thì cả 3 model flash đều
   trả lời đúng một lượt CRG thật. Cap phải đặt theo model, không dùng số chung.

3. **Tiền cọc theo `max_output_tokens`.** Proxy giữ trước `max_output_tokens × giá output`.
   Lỗi thật gặp phải:
   `403 "max estimated cost of operation ($3.200045) exceeds your available quota (based on max_output_tokens)"`.
   Tiền cọc **cộng dồn** khi nhiều run song song trên cùng account.

---

## Phương pháp tính giá

Công thức: `$/ván ≈ (probe_cost / probe_tokens) × 45,300`

45,300 token/ván = **36.8k input + 8.5k output**, đo từ chính run 60 ván của
`gemini-3.1-flash-lite` (2.21M in / 0.51M out). Input chiếm 81%.

**Sai số ±3×.** Đối chiếu **7** model nay đã đo end-to-end (cập nhật 09-09-2026, sau khi
nhánh frontier chạy xong 37 shard / $110.50):

| Model | Ước tính $/ván | **Đo thật $/ván** | Ước / thật |
|---|---|---|---|
| `gpt-5.4-nano` | 0.0201 | **0.0073** | 0.36× (ước CAO) |
| `claude-opus-5-default` | 0.6512 | **0.682** | 1.05× |
| `gemini-3.1-pro-preview` | 0.5110 | **0.609** | 1.19× |
| `gpt-5.6-sol` | 0.2422 | **0.348** | 1.44× |
| `gemini-3.1-flash-lite` | 0.0151 | **0.0220** | 1.46× |
| `grok-4.20-non-reasoning` | 0.0115 | **0.023** | 2.00× |
| `grok-4.20-reasoning` | 0.0578 | **0.131** | 2.27× |

**Quy tắc hiệu chỉnh mới: nhân ước tính với ×1.5 để ra giá thực tế** (trung vị 1.44,
6/7 điểm nằm trong [1.05, 2.27], chỉ `gpt-5.4-nano` ước cao). **Lập ngân sách thì dùng ×2**
cho an toàn. Bảng ước tính bên trên **chưa** áp hệ số này — tự nhân khi dùng.

Nguyên nhân: mỗi probe chỉ cho **1 phương trình với 2 ẩn** (giá input, giá output).
Probe nặng output → ước quá cao; probe gần như toàn input → ước quá thấp.

**Cách xoá sai số:** gọi mỗi model 2 lần với tỉ lệ in/out khác nhau → giải hệ 2 ẩn ra giá
thật. Đây là bước hiệu chuẩn ở Ngày 1 của [frontier-run-plan.md](frontier-run-plan.md).

Bảng này dùng để **phân tầng**, không dùng để chốt ngân sách.

---

## Cách probe lại

```bash
# 1. Nạp credential cho 1 account (xem CLAUDE.md để biết kho token)
export KAGGLE_CONFIG_DIR=/path/rieng
export KAGGLE_API_TOKEN=KGAT_xxxxxxxx
export PYTHONIOENCODING=utf-8

# 2. Lấy danh mục + proxy key
kaggle b t models > models_raw.txt
kaggle b init -y --env-file probe.env

# 3. Probe liveness song song ở LOCAL (staging)
python plan/scripts/probe_all_models.py \
    --env-file probe.env --models-file models_raw.txt \
    --workers 13 --max-tokens 512

# 4. Kiểm bằng prompt CRG thật (đúng 1 lượt quyết định, check parse được)
python plan/scripts/probe_crg_prompt.py probe.env "slug1,slug2,slug3"

# 5. Probe SERVER-SIDE (khác proxy, nhiều model hơn) — tối đa 7 -m mỗi lệnh
kaggle b t push crg-proxy-probe -f kaggle/benchmarks/proxy_probe_task.py
kaggle b t run crg-proxy-probe -m slug1 -m slug2 ... --wait 900
kaggle b t status crg-proxy-probe          # xem Completed/Errored + lý do lỗi
kaggle b t log crg-proxy-probe -m <slug>   # grep "PROBE RESULT" để lấy reply + cost thật
```

Lưu ý khi lấy log hàng loạt: fetch song song >3 luồng sẽ bị rate-limit và trả về log
rỗng (im lặng, không báo lỗi). Giữ concurrency ≤3.
