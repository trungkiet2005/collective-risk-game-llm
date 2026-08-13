# Kết quả bậc đỉnh — cập nhật liên tục

Ghi khi từng model về đủ 60 ván. Đợt chạy: Ngày A, 12–13/08/2026.
Xem cách chạy ở [runbook-top-tier.md](runbook-top-tier.md).

## Trạng thái

| Model | 60 ván? | Hiệu ứng risk 0.1→0.9 (EN / VN) | Kết luận |
|---|---|---|---|
| `gpt-5.6-sol` | ✅ `parse_failed=0` | **+118.2 / +74.2** | **PHẢN ỨNG** — chơi đúng EV-optimal |
| `grok-4.20-0309-reasoning` | ✅ `parse_failed=0` | **+0.2 / +0.0** | **NULL HOÀN HẢO** — mù risk tuyệt đối |
| `gemini-3.1-pro-preview` | ✅ `parse_failed=0` | **+120.0 / +119.6** | **PHẢN ỨNG** — EV-optimal, bất biến theo ngôn ngữ |
| `claude-opus-5-default` | chưa chạy (Ngày B) | | smoke: 1 ván, GT=128, $0.585/ván |

**Ngày A HOÀN TẤT:** 3 model × 60 ván = 180 ván, 10.800 lượt, `parse_failed = 0` toàn bộ.
Chi phí thật **$65.28** + smoke $1.48 = **$66.76** (ước ban đầu $48.66 — thiếu 34%). Dataset ở `results/frontier/<model_tag>/exp_baseline/`.

## KẾT QUẢ CUỐI Ngày A — 3 model × 60 ván, `parse_failed = 0`, $66.76

| Model | Nhà | Bậc | GT p=0.1 (SD) | GT p=0.5 | GT p=0.9 | risk eff EN | risk eff VN |
|---|---|---|---|---|---|---|---|
| `gemini-3.1-flash-lite` | Google | rẻ | 122.0 (3.8) | 122.4 | 120.2 | **−1.8** | **+0.4** |
| `gemini-3.1-pro-preview` | Google | đỉnh | **0.0** (0.0) | 120.0 | 120.0 | **+120.0** | **+119.6** |
| `gpt-5.4-nano` | OpenAI | rẻ | — | — | — | +7.5 (paper) | — |
| `gpt-5.6-sol` | OpenAI | đỉnh | **1.6** (1.6) | 120.0 | 119.8 | **+118.2** | **+74.2** |
| `grok-4.20-0309-reasoning` | xAI | đỉnh | 120.0 (0.0) | 120.0 | 120.2 | **+0.2** | **+0.0** |

### Công thức đúng: năng lực là điều kiện CẦN nhưng KHÔNG ĐỦ

- **Không model rẻ nào** chơi tối ưu EV (flash-lite −1.8, nano +7.5).
- **Một số nhưng không phải tất cả** model bậc đỉnh làm được: gemini-3.1-pro và gpt-5.6-sol
  có, grok-4.20-reasoning **không** (+0.2 dù cũng là reasoning bậc đỉnh).
- Đối chứng năng lực **sạch nhất trong cả dataset**: `gemini-3.1-flash-lite` vs
  `gemini-3.1-pro` — **cùng nhà cung cấp, cùng thế hệ 3.1, chỉ khác bậc** → một null hoàn
  toàn, một tối ưu EV hoàn hảo.

Claim này mạnh hơn cả "LLM mù risk" lẫn "frontier nhạy risk", và chống được phản biện dễ
nhất: *"các anh chỉ chưa thử model đủ mạnh"*.

### Ở bậc đỉnh, phương sai giữa các ván sụp về 0

Cả 3 model bậc đỉnh có SD ≈ 0 ở gần như mọi cell — mỗi model chọn **một** chiến lược rồi
thi hành y hệt qua 10 lần lặp. Chúng là **hàm tất định**, không phải "hơi nghiêng" về hướng
nào.

**Hệ quả cho phân tích thống kê:** khái niệm "uncensored cell" mà paper dùng để test risk
**không áp dụng được ở bậc đỉnh** — không có cell nào còn phương sai để giải thích. Phương
sai đáng quan tâm đã dời từ *trong* model sang *giữa* các model, nên phép kiểm phải là so
sánh giữa model, không phải hồi quy trong model.

### Hiệu ứng ngôn ngữ cũng là đặc tính từng model

Đừng gộp thành một "hiệu ứng ngôn ngữ" — 3 hướng khác nhau đã đo được:

- `gpt-5.4-nano`: VN → góp **ít** hơn nhiều (chênh 146.8, lật reach 100%→0%)
- `gpt-5.6-sol`: VN → tối ưu EV **suy giảm** (+118.2 → +74.2, SD nhảy 1.6 → **47.7**)
- `gemini-3.1-pro`: VN → **không ảnh hưởng gì** (+120.0 → +119.6, SD 0.0 → 0.8)

Nhận xét trước đó rằng "hình phạt ngôn ngữ chỉ rơi vào cell cần suy luận" **chỉ đúng cho
`gpt-5.6-sol`**, không khái quát được: `gemini-3.1-pro` tính đúng ngưỡng EV ở cả hai ngôn
ngữ. Ngôn ngữ có phá được suy luận hay không **phụ thuộc model**.

---

## ⚠️ Kết luận quan trọng nhất: hiệu ứng thuộc MODEL, không thuộc BẬC

`gpt-5.6-sol` và `grok-4.20-reasoning` **cùng là model reasoning bậc đỉnh**. Một chơi đúng
kỳ vọng toán học (+118.2), một mù risk tuyệt đối (+0.2). Nên:

- **KHÔNG được viết "frontier models phản ứng với risk".** Hiệu ứng là đặc tính của từng
  model, không của bậc năng lực. Nếu chỉ chạy `gpt-5.6-sol` thì sẽ có một kết luận sai mà
  rất khó phát hiện.
- **Năng lực suy luận KHÔNG sinh ra độ nhạy risk.** Đây là bằng chứng sắc hơn nhiều cho câu
  paper đã viết: *"Capability and the disposition to act on incentives are, here, decoupled."*
- Phép thử rẻ có giá trị cao ngay bây giờ: **`grok-4.20-0309-non-reasoning`** (~$1.7). Cùng
  model gốc, chỉ tắt reasoning → đối chứng sạch nhất cho câu "suy luận có giúp gì không".

---

## `grok-4.20-0309-reasoning` — null mạnh nhất trong cả nghiên cứu

60/60 ván, 3600 lượt, `parse_failed = 0`.
Dataset: `results/frontier/xai-grok-4.20-0309-reasoning/exp_baseline/`

| risk | EN: GT (SD) | VN: GT (SD) | reach | payoff |
|---|---|---|---|---|
| 0.1 | **120.0** (0.00) | **120.0** (0.00) | 100% | 20.00 |
| 0.5 | 120.0 (0.00) | 120.0 (0.00) | 100% | 20.00 |
| 0.9 | 120.2 (0.63) | 120.0 (0.00) | 100% | 19.97 |

**Hiệu ứng risk: +0.2 (EN) / +0.0 (VN).** Không có hiệu ứng ngôn ngữ. Không có phương sai.

Ở risk 0.1, bỏ mặc cho kỳ vọng **36** còn nó lấy **20** — bỏ lại 16 điểm/người/ván trong cả
20 ván, không lệch một lần. Đúng 120 trong **59/60 ván với SD = 0**: ca tuân thủ
equal-split focal point cực đoan nhất từng đo, mạnh hơn Gemma-2-9B (30/30 tiếng Anh) mà
paper đang dùng làm ví dụ.

Mọi cell đều degenerate (SD ≈ 0) → **không cell nào dùng được cho phân tích phương sai**.
Giá trị của model này là làm đối chứng cho `gpt-5.6-sol`, không phải để test risk.

---

---

## `gpt-5.6-sol` — kết quả đảo ngược claim trung tâm của paper

60/60 ván, 3600 lượt, `parse_failed = 0`.
Dataset: `results/frontier/openai-gpt-5.6-sol/exp_baseline/`

| risk | EN: GT (SD) | EN reach | VN: GT (SD) | VN reach |
|---|---|---|---|---|
| 0.1 | **1.6** (1.58) | 0% | **45.8** (47.67) | 0% |
| 0.5 | 120.0 (0.00) | 100% | 120.0 (0.00) | 100% |
| 0.9 | 119.8 (0.63) | 90% | 120.0 (0.00) | 100% |

**Hiệu ứng risk 0.1 → 0.9: EN +118.2 điểm / 240 · VN +74.2.**
So với paper hiện tại: open-weight panel +0.97 (P=0.54), `gpt-5.4-nano` +7.5 (P=0.26) —
cả hai đều null. Đây là lần đầu hiệu ứng risk KHÔNG null.

### Hành vi trùng khớp EV-optimal ở cả 3 mức risk

Với endowment 40, target 120 (góp 2 mỗi vòng × 10 vòng = 20):

| | Góp đủ target | Không góp gì | Tối ưu | Model làm |
|---|---|---|---|---|
| p=0.1 | chắc chắn 20 | 0.9 × 40 = **36** | bỏ mặc | bỏ mặc ✅ |
| p=0.5 | chắc chắn 20 | 0.5 × 40 = **20** | bằng nhau | hợp tác ✅ |
| p=0.9 | chắc chắn **20** | 0.1 × 40 = 4 | hợp tác | hợp tác ✅ |

Payoff thực nhận ở p=0.1/EN = **31.8**, cao hơn 20 nếu hợp tác → nó thắng thật, không phải
may. Thảm hoạ có nổ ở 2/10 ván (đúng tỉ lệ xổ số p=0.1 keyed theo rep).

### Ba giới hạn phải nói đúng

1. **Vẫn KHÔNG tái tạo pattern người.** Người: reach 0% → 10% → 50% tăng dần.
   `gpt-5.6-sol`: 0% → 100% → 90%. Đó là **hàm bậc thang theo ngưỡng EV**, không phải
   đường tăng dần. Câu "không model nào tái tạo hành vi người" vẫn đúng — nhưng vì lý do
   **ngược lại**: nó lý trí hơn người, không phải mù hơn.
2. **KHÔNG chứng minh được nó *tính* EV.** Trường `reasoning` trong turns.jsonl chỉ chứa
   đúng dòng `CONTRIBUTION: 0` — proxy không trả về reasoning channel. Chỉ kết luận được
   hành vi **trùng khớp** EV-optimal. Muốn bằng chứng nó thật sự tính thì cần thiết kế hỏi
   trực tiếp (đúng follow-up mà Discussion của paper đã nêu).
3. **p=0.5 và p=0.9 là degenerate.** GT = 120.0 với SD = 0.00 — mọi ván ra đúng một số.
   Theo quy tắc lên tuyển (`GT` trong 120±40 **và** phương sai > 0), các cell này trượt.
   Cell dùng được cho phân tích phương sai chỉ có p=0.1 (cả 2 ngôn ngữ) và p=0.9/EN.

### Hiệu ứng ngôn ngữ chỉ đánh vào cell cần suy luận

Ở p=0.5 và p=0.9, **cả hai ngôn ngữ đều cho đúng 120, SD = 0** — hành vi focal-point miễn
nhiễm với ngôn ngữ. Chỉ ở p=0.1, nơi model phải thật sự tính ra rằng bỏ mặc lợi hơn, tiếng
Việt mới sụp: GT 45.8 với **SD 47.67** (so với 1.6 ± 1.58 ở EN).

Khớp chính xác ghi chú trong `docs/papers/papers_markdown/language-effects-llm.md`:
*"Functional/reasoning gaps are much larger than static-knowledge gaps."* Ở đây đo được nó
**trong cùng một model, cùng một game, chỉ khác ô risk**.

Lưu ý hướng ngược dấu: `gpt-5.4-nano` có VN → góp **ít** hơn (chênh 146.8, lật reach
100%→0%). `gpt-5.6-sol` có VN → góp **nhiều** hơn ở risk thấp (45.8 vs 1.6), tức tiếng Việt
kéo nó về "hợp tác mặc định" thay vì tính toán. Hai model cùng nhà cung cấp, hiệu ứng ngôn
ngữ **ngược dấu nhau** — cần nói rõ trong paper, đừng gộp thành một "hiệu ứng ngôn ngữ".

### Chi phí thật

$0.32409/ván ở smoke, nhưng biến động theo cell: shard risk 0.9/0.5 tốn $2.56–3.00 cho 10
ván, còn risk 0.1 tốn **$4.24 (EN) và $5.52 (VN)** — cell risk thấp đắt hơn ~1.8× vì model
tiêu nhiều token suy luận hơn khi phải quyết định có nên bỏ mặc. Tổng 6 shard ≈ $21.8
(ước ban đầu $19.45).

**Hệ quả cho việc lập ngân sách:** giá/ván đo ở một cell KHÔNG suy ra được cho cell khác.
Đo ở risk 0.9 rồi nhân cho cả sweep sẽ thiếu ~20%.

---

## Việc tiếp theo khi các model còn lại về

- [ ] Kiểm cùng bảng trên cho `gemini-3.1-pro` và `grok-4.20-reasoning`: hiệu ứng risk có
      xuất hiện ở nhà cung cấp khác không, hay chỉ riêng OpenAI bậc đỉnh?
- [ ] Nếu ≥2 model bậc đỉnh phản ứng với risk → **claim trung tâm của paper phải viết lại**:
      null về risk không phổ quát, nó vỡ ở frontier. Đây là kết quả mạnh hơn null.
- [ ] Chạy Ngày B (`claude-opus-5`, 6 shard × 10 ván × $5.85 = $35.11).
- [ ] Cân nhắc chạy `gpt-5.6-luna` và `gpt-5.6-terra` (bậc rẻ/giữa cùng thế hệ 5.6) để biết
      hiệu ứng này thuộc về **thế hệ 5.6** hay chỉ riêng bậc đỉnh `sol`. Rẻ: $2.91 + $7.27.
