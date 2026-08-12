# Kaggle Model Proxy — 38 slug: cái nào sống, sống ở đâu, giá bao nhiêu

**Ngày probe: 12-08-2026.** Danh mục lấy từ `kaggle b t models`.
Probe lại bằng script trong [scripts/](scripts/) nếu cần cập nhật.

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

## Chết hoặc không dùng được — 10 slug

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

**Sai số ±3×.** Đối chiếu 2 model đã đo end-to-end:

| Model | Ước tính | Đo thật | Lệch |
|---|---|---|---|
| `gemini-3.1-flash-lite` | $0.0151/ván | $0.0220/ván | thấp 1.5× |
| `gpt-5.4-nano` | $0.0201/ván | $0.0073/ván | cao 2.8× |

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
