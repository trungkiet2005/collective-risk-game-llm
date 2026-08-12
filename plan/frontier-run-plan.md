# Kế hoạch mở rộng nhánh frontier

Lập 13-08-2026, dựa trên đợt probe 38 model ngày 12-08-2026.
Ngân sách: **16 account × $10/ngày, tự nạp lại mỗi ngày** (~$160/ngày).

## Mục tiêu và hai tiêu chí chọn model

Mục tiêu **không phải** thêm nhiều model cho đẹp bảng. Có hai tiêu chí, và cả hai đều
loại bỏ cách chọn "lấy model mạnh nhất".

### Tiêu chí 1 — model không được bị trần

`gemini-3.1-flash-lite` đạt target 100% ở cả 3 mức risk × 2 ngôn ngữ. Một biến đã dính
trần thì về mặt toán học không thể biểu diễn phản ứng với risk — bất kể model có nhạy
risk hay không. Paper hiện tại phải dựng khái niệm "uncensored cell" để lách, và chỉ
**3 trong 14 cell** của nhánh frontier đủ điều kiện.

Hệ quả ngược trực giác: **đừng ưu tiên model mạnh nhất.** Opus 5 rất có thể cũng cán trần
100% như flash-lite, tốn ~$39 để thu về một hàng vô dụng về mặt thống kê. Ở nhánh
open-weight, `llama-3.1-70B` (reach 50%, catastrophe 36.7%) có giá trị hơn 6 model reach
100% cộng lại.

### Tiêu chí 2 — đa dạng nhà cung cấp, không phải đa dạng biến thể

Claim của paper là về LLM agent nói chung, nên phải chống được phản biện "đây chỉ là nét
riêng của quy trình post-training một lab". Hai biến thể cùng một họ (`gemma-4-31b` vs
`gemma-4-26b-a4b`, hay `gpt-5.4-nano` vs `gpt-5.4-mini`) gần như không thêm gì cho lập
luận đó — đó là tiêu tiền cho phương sai giữa các bản vá.

**Trần cứng phải biết:** proxy hiện chỉ còn **4 nhà cung cấp** — Google (10 slug),
Anthropic (9), OpenAI (7), xAI (2). Ba nhà đã chết sạch **đều là lab Trung Quốc**:
Alibaba (4 slug Qwen3), DeepSeek (2), Zhipu (GLM-5). Nên nhánh frontier hiện **không thể**
có đại diện lab Trung Quốc, và đó là một hạn chế thật cần ghi vào paper — kèm việc
probe lại định kỳ xem chúng sống lại chưa.

## Ràng buộc thật

Vì quota nạp lại mỗi ngày, **tiền không còn là ràng buộc**. Còn lại hai thứ:

1. **Trần ~$10 cho mỗi run đơn lẻ.** Một run không chia được qua nhiều account. Baseline
   60 ván trên `claude-opus-4-1` (~$75) bất khả thi trong một run — phải cắt sweep thành
   nhiều run nhỏ rồi ghép data.
2. **Thời gian.** `CRG_CONCURRENCY` mặc định 1 (tuần tự, tránh 429) → 60 ván ≈ 2–3h.
   Nhiều account chạy song song thì vẫn xong trong một buổi.

---

## Panel: lưới nhà cung cấp × bậc năng lực

Thay vì một danh sách phẳng, panel là một lưới. Cách này vừa cân nhà cung cấp, vừa cho
thêm một thứ danh sách phẳng không có: **thang năng lực trong cùng một lab**, tức kiểm
được "model xịn hơn của cùng một lab có nhạy risk hơn không" trong khi giữ nguyên phong
cách post-training. Đó chính là câu hỏi scaling của paper, đặt ở mức frontier.

| Nhà cung cấp | Bậc rẻ | Bậc giữa | Bậc đỉnh |
|---|---|---|---|
| **Anthropic** | `claude-haiku-4-5-20251001` · $5.01 | `claude-sonnet-4-6-default` · $15.02 | `claude-opus-5-default` · $39.07 |
| **Google** | `gemini-3.5-flash-lite` · $1.51 | `gemini-3.6-flash` · $19.22 | `gemini-3.1-pro-preview` · $30.66 |
| **OpenAI** | `gpt-5.4-nano-2026-03-17` · $0.44 | `gpt-5.6-luna` · $2.91 | `gpt-5.6-sol` · $14.53 |
| **xAI** | `grok-4.20-0309-non-reasoning` · $0.69 | — | `grok-4.20-0309-reasoning` · $3.47 |
| **Google, open-weight** | `gemma-4-31b-it` · $1.45 | — | — |

Giá là **$/60 ván, ước tính, sai số ±3×**.

Ba ô có lý do riêng ngoài việc lấp lưới:

- **Cặp `grok-4.20` reasoning / non-reasoning** — cùng model gốc, chỉ bật tắt reasoning.
  Đối chứng sạch nhất cho câu "suy luận nhiều hơn có làm agent nhạy risk hơn không".
  Không nhà nào khác trên proxy cho cặp này. xAI chỉ có 2 slug nên không có bậc giữa.
- **`gemma-4-31b`** — open-weight, nối trực tiếp nhánh vLLM, và vá được vụ `gemma2` hỏng
  chat-template ở run 1 (cùng họ Gemma nhưng chạy qua proxy nên không dính bug đó).
- **Anthropic đủ 3 bậc** vì nó là nhà duy nhất có thang giá rõ ràng cả 3 mức mà vẫn cùng
  một phong cách post-training.

### Đã bỏ khỏi panel cũ, vì trùng lặp

| Bỏ | Lý do |
|---|---|
| `gemma-4-26b-a4b-it` | biến thể MoE của `gemma-4-31b` — cùng họ, cùng lab, gần như không thêm gì cho claim |
| `gpt-5.4-mini` | bậc kề trực tiếp của `gpt-5.4-nano` cùng họ; `gpt-5.6-luna` khác **thế hệ** nên thông tin hơn |
| `gemini-2.5-flash` | Google đã có 3 ô; thêm nữa là làm lệch panel |
| `gemini-3-flash-preview` | Google đã đủ; lại là model ước giá không chắc |

---

## Ngày 1 — sửa code + smoke 4 họ model

**Chi phí:** ~$1 · **Cần:** 1 account

### Hai chỗ phải sửa trong `kaggle/benchmarks/crg_task_server.py`

- [ ] **Cap `max_output_tokens` theo từng model.** Bắt buộc. Proxy đặt cọc trước =
  `max_output_tokens × giá output`, nên không cap thì model đắt bị 403 dù thực tế tốn
  vài xu. Bằng chứng: `claude-opus-4-7` trả
  `403 "max estimated cost of operation ($3.200045) exceeds your available quota (based on max_output_tokens)"`
  — $3.20 ứng với ~64k token output mặc định.

  Cap khác nhau theo model, **không dùng một số chung**:
  - Model thường: `512`
  - Model reasoning (`grok-*-reasoning`, `gemini-3.x-flash`, `opus-5`, `gpt-5.5/5.6`): `6000`

  Lý do phải cao cho reasoning: `gemini-3.6-flash` trả về **rỗng** ở mức 64 token, và
  `gemini-3.5-flash` không sinh nổi JSON hợp lệ ở mức 2000. Phải ≥6000.

- [ ] **Chặn `reply == ""`.** Task hiện raise khi có exception, nhưng content rỗng đi theo
  nhánh khác và có thể bị ghi thành ván đóng góp 0 — đúng loại lỗi đã tạo ra "ván giả toàn
  số 0" ở run 1. Với model reasoning, output rỗng là chuyện thật: `gpt-oss-120b` báo
  Completed nhưng `reply` rỗng hoàn toàn.

### Smoke 1 ván cho mỗi họ chưa từng chạy CRG server-side

Tới giờ **chỉ `gpt-5.4-nano`** từng chạy thật qua đường này. Bốn họ dưới đây chưa có ván
nào — rủi ro `parse_fail` do định dạng trả lời khác.

- [ ] `claude-haiku-4-5-20251001`
- [ ] `grok-4.20-0309-non-reasoning`
- [ ] `gemma-4-31b-it`
- [ ] `gemini-3.6-flash` (đại diện nhóm reasoning — kiểm cap 6000 có đủ)

### Hiệu chuẩn giá 2 điểm (nên làm)

Ước tính trong plan sai tới **±3×** (flash-lite thực $0.022/ván vs ước $0.015; nano thực
$0.0073 vs ước $0.020). Nguyên nhân: mỗi probe chỉ cho 1 phương trình với 2 ẩn.

- [ ] Gọi mỗi model 2 lần với tỉ lệ in/out khác nhau (prompt dài + output ngắn, rồi prompt
  ngắn + output dài) → giải hệ 2 ẩn ra giá thật. Tốn vài xu.

---

## Ngày 2 — chạy thẳng full 60 ván cho hàng "bậc rẻ" + 2 ô rẻ khác

**Chi phí:** ~$15.5 · **Cần:** 7 account (mỗi model 1 account, để tiền cọc không cộng dồn)

Không screen. Với model ≤$8 thì screen 12 ván tốn $0.14–1.00 mà full 60 ván chỉ $0.44–5.01
— chênh không đáng để mất một bước. **Screening chỉ có lý do tồn tại cho model đắt.**

Sweep mặc định trong `crg_task_server.py` đã đúng chuẩn `exp_baseline`
(`RISKS=0.9,0.5,0.1`, `LANGS=en,vn`, `REPS=10` → 60 ván) — **không cần sửa gì thêm**.

| ✓ | Model | Nhà cung cấp | $/60 ván (ước) | Chi phí thật |
|---|---|---|---|---|
| [ ] | `gpt-5.4-nano-2026-03-17` | OpenAI | 0.44 | |
| [ ] | `grok-4.20-0309-non-reasoning` | xAI | 0.69 | |
| [ ] | `gemma-4-31b-it` | Google (open) | 1.45 | |
| [ ] | `gemini-3.5-flash-lite` | Google | 1.51 | |
| [ ] | `gpt-5.6-luna` | OpenAI | 2.91 | |
| [ ] | `grok-4.20-0309-reasoning` | xAI | 3.47 | |
| [ ] | `claude-haiku-4-5-20251001` | Anthropic | 5.01 | |

Cân nhà cung cấp ở đợt này: Anthropic 1 · Google 2 · OpenAI 2 · xAI 2. Anthropic chỉ được
1 vì **nó không có model thứ hai nào dưới $8** — bậc kế tiếp là sonnet ở $15. Đó là dữ kiện
về danh mục, không phải thiếu sót của kế hoạch; Anthropic được bù ở Ngày 3.

`gpt-5.4-nano` chạy lại dù đã có 30 ván: data cũ đi qua **OpenAI API trực tiếp**, không qua
Kaggle proxy. Trộn 2 đường nhà cung cấp trong cùng một bảng là confound không cần thiết,
mà chạy lại chỉ $0.44.

### Lệnh

```bash
# Mỗi account cần KAGGLE_CONFIG_DIR riêng (creds không đè nhau) — xem CLAUDE.md
export KAGGLE_CONFIG_DIR=/path/rieng/cho/account-nay
export KAGGLE_API_TOKEN=KGAT_xxxxxxxx
export PYTHONIOENCODING=utf-8      # SDK in emoji, cp1252 sẽ crash

# Task thuộc từng account → account nào cũng phải tự push trước khi run
kaggle b t push collective-risk-baseline-srv -f kaggle/benchmarks/crg_task_server.py
kaggle b t run  collective-risk-baseline-srv -m <slug> --wait
kaggle b t download collective-risk-baseline-srv -m <slug> -o results/frontier/
```

---

## Ngày 3 — screen 12 ván cho hàng "bậc giữa" và "bậc đỉnh"

**Chi phí:** ~$26.6 · **Cần:** 6 account

Sweep rút gọn: 3 risk × 2 lang × 2 rep = 12 ván/model. Mục đích duy nhất là biết model có
dính trần hay không, trước khi bỏ $15–39 cho một full run.

| ✓ | Model | Nhà cung cấp | Bậc | Screen 12 ván | Full 60 ván | Kết quả screen |
|---|---|---|---|---|---|---|
| [ ] | `gpt-5.6-sol` | OpenAI | đỉnh | 2.91 | 14.53 | |
| [ ] | `claude-sonnet-4-6-default` | Anthropic | giữa | 3.00 | 15.02 | |
| [ ] | `gpt-5.4-2026-03-05` | OpenAI | giữa | 2.87 | 14.35 | |
| [ ] | `gemini-3.6-flash` | Google | giữa | 3.84 | 19.22 | |
| [ ] | `gemini-3.1-pro-preview` | Google | đỉnh | 6.13 | 30.66 | |
| [ ] | `claude-opus-5-default` | Anthropic | đỉnh | 7.81 | 39.07 | |

### Quy tắc lên tuyển

Dùng **`group_total`**, không dùng reach. Ở 2 rep, reach mỗi cell chỉ nhận 0 / 0.5 / 1 —
quá thô để phân loại trần. `group_total` liên tục nên ở n nhỏ vẫn phân biệt được model
đóng góp ~240 (trần tuyệt đối), ~60 (sụp sàn) và ~120 (đúng vùng thông tin).

> **Lên full run** nếu mean `group_total` nằm trong **120 ± 40** ở *ít nhất một* cell
> risk×lang, **và** phương sai trong cell > 0 (không phải mọi ván ra cùng một số),
> **và** `parse_fail = 0`.
>
> **Loại** nếu mọi cell đều ≥ 200 (trần) hoặc ≤ 80 (sàn). Ghi lại số liệu, không chạy tiếp.

---

## Ngày 4+ — full run cho model đã lên tuyển

Model tầng C/D cắt sweep theo risk thành 3 run × 20 ván (mỗi run ≤$10) trên 3 account rồi
ghép data. Vì quota nạp lại mỗi ngày, kể cả `claude-opus-5` ($39, chia 6 run) cũng xong
trong một ngày.

Kích thước sweep phải **nướng cứng vào file lúc push** — `kaggle b t run` không nhận biến
môi trường, nên chia run = push nhiều version, mỗi version một mức risk.

Panel đầy đủ nếu mọi ô đều lên tuyển: **13 model / 4 nhà cung cấp** — Anthropic 3,
Google 4 (gồm 1 open-weight), OpenAI 4, xAI 2.

---

## Sau khi panel chốt: ba mở rộng

- [ ] **Probe lại lab Trung Quốc.** Qwen3 (4 slug), DeepSeek (2), GLM-5 đều 503/429 ngày
  12-08-2026. Nếu sống lại thì panel có thêm một trục nhà cung cấp hoàn toàn mới — đáng
  kiểm hàng tuần bằng `plan/scripts/probe_all_models.py`, rẻ và nhanh.
- [ ] **Comprehension cho frontier.** Hiện chưa có một điểm dữ liệu nào — paper tự ghi
  *"The frontier arm has no comprehension data at all."* Cần viết task server-side mới,
  chưa tồn tại.
- [ ] **Mở 5 ngôn ngữ (fr/zh/ar).** Config `exp_baseline.json` + `exp_comprehension.json`
  đã khai báo 5 ngôn ngữ và template `crsd/prompts/crsd_{fr,zh,ar}.txt` đã có, nhưng
  `kaggle/benchmarks/crg_task.py` đang hardcode `CRG_LANGS="en,vn"` và **nhúng cứng prompt
  EN/VN inline** → đường Kaggle chưa chạy được fr/zh/ar. Đây là hiệu ứng mạnh nhất cả paper
  (146.8 điểm, lật reach 100%→0%), nên xứng đáng một study riêng.

---

## Không chạy, và vì sao

| Model | Lý do |
|---|---|
| `gemma-4-26b-a4b-it`, `gpt-5.4-mini`, `gemini-2.5-flash`, `gemini-3-flash-preview` | trùng nhà cung cấp / trùng họ với ô đã có trong lưới — xem [bảng đã bỏ](#đã-bỏ-khỏi-panel-cũ-vì-trùng-lặp) |
| `claude-opus-4-1` | đắt nhất bảng (~$75/baseline) mà là bản Opus cũ nhất — trả giá cao nhất cho model lỗi thời nhất |
| `opus-4-5` / `4-6` / `4-8`, `sonnet-4` / `4-5`, `gpt-5.5`, `gemini-2.5-pro`, `gemini-3.5-flash`, `gpt-5.6-terra` | bản vá hoặc biến thể của ô đã có trong lưới; giữ bản mới nhất mỗi bậc là đủ |
| `gpt-oss-120b` | báo Completed nhưng `reply` rỗng — token chảy vào reasoning channel, content không có gì. Trạng thái xanh che mất lỗi |
| `gpt-oss-20b`, `glm-5`, `deepseek-r1-0528`, cả 4 Qwen3 | 503 trên cả hai proxy, không phải vấn đề quota |
| `deepseek-v3.1` | 429 quá tải mọi lần thử; còn sống nhưng không đặt lịch được |
| `claude-opus-4-7-default` | chỉ 403 do tiền cọc, không phải chết. Xem lại sau khi set `max_output_tokens` ở Ngày 1 |

---

## Bẫy vận hành

- **Task thuộc từng account** — account nào cũng phải tự `push` trước khi `run`.
- **Tối đa 7 `-m` mỗi lệnh `run`** — quá thì API trả `400 BatchScheduleBenchmarkTaskRuns`.
- **`download` sau mỗi run.** `CRG_RESUME` chỉ hoạt động trong nội bộ một run; server-side
  mỗi run khởi động sạch nên run đứt giữa đường là mất data nếu chưa tải về.
- **Đừng xếp nhiều run đắt song song trên cùng một account** — tiền cọc cộng dồn. Đây là
  nguyên nhân khả dĩ nhất của lỗi 403 ở `opus-4-7`: 7 run song song trên một account, nó
  đến sau và hết chỗ cọc.
- **Proxy key hết hạn sau ~1h** (`kaggle b auth -y` để làm mới), nhưng run server-side tự
  lo phần auth của nó.
