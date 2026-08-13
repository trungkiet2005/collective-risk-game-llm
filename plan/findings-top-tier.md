# Kết quả nhánh frontier bậc đỉnh — HOÀN TẤT 13-08-2026

**6 model × 60 ván, 3600 lượt/model, `parse_failed = 0` toàn bộ.** Chi phí ~$110.50 / 37 shard.
Dataset: `results/frontier/<model_tag>/exp_baseline/{games.csv,turns.jsonl}` — ghép sạch với
nhánh open-weight. Cách chạy: [runbook-top-tier.md](runbook-top-tier.md).

## Bảng chính — hiệu ứng risk 0.1 → 0.9 (điểm trên 240)

| Model | Nhà | Bậc | GT p=0.1 (en) | GT p=0.9 (en) | **eff EN** | **eff VN** | reach p=0.1 |
|---|---|---|---|---|---|---|---|
| `gemini-3.1-pro-preview` | Google | đỉnh | **0.0** | 120.0 | **+120.0** | **+119.6** | 0% |
| `gpt-5.6-sol` | OpenAI | đỉnh | **1.6** | 119.8 | **+118.2** | **+74.2** | 0% |
| `grok-4.20-non-reasoning` | xAI | đỉnh | 197.2 | 220.8 | +23.6 | +0.0 | 100% |
| `claude-opus-5-default` | Anthropic | đỉnh | 120.0 | 128.0 | +8.0 | +1.2 | 100% |
| `grok-4.20-reasoning` | xAI | đỉnh | 120.0 | 120.2 | +0.2 | +0.0 | 100% |
| `gemini-3.1-flash-lite` | Google | rẻ | 122.0 | 120.2 | −1.8 | +0.4 | 100% |

Đối chiếu paper hiện tại: open-weight panel **+0.97** (P=0.54), `gpt-5.4-nano` **+7.5** (P=0.26).

`reach p=0.1` chia đôi hoàn hảo: **0% cho hai model EV-optimal, 100% cho mọi model null.**
Không có trường hợp trung gian.

---

## Ba kết luận

### 1. Độ nhạy risk thuộc MODEL, không thuộc bậc năng lực — 2/4 chia đôi

Bốn model bậc đỉnh từ **bốn nhà cung cấp khác nhau** chia đúng 2–2: `gemini-3.1-pro` và
`gpt-5.6-sol` chơi tối ưu EV; `claude-opus-5` và `grok-4.20-reasoning` là null.

Không thể quy cho nhà cung cấp, kiến trúc, hay việc có reasoning hay không — cả 4 đều là
model reasoning bậc đỉnh. **ĐỪNG viết "frontier models phản ứng với risk".** Chạy một model
rồi khái quát sẽ cho kết luận sai bất kể chọn model nào.

### 2. Năng lực là điều kiện CẦN nhưng KHÔNG ĐỦ

- Không model rẻ nào chơi tối ưu EV (`flash-lite` −1.8, `gpt-5.4-nano` +7.5).
- Một số nhưng không phải tất cả model bậc đỉnh làm được.
- Đối chứng năng lực **sạch nhất trong cả dataset**: `gemini-3.1-flash-lite` (−1.8) vs
  `gemini-3.1-pro` (+120.0) — **cùng nhà, cùng thế hệ 3.1, chỉ khác bậc.**

Claim này chống được phản biện dễ nhất: *"các anh chỉ chưa thử model đủ mạnh."*

### 3. Reasoning tạo ra TÍNH TIẾT KIỆM, không tạo ra độ nhạy risk

Cặp đối chứng cùng model gốc, chỉ bật/tắt reasoning:

| | GT p=0.1 en | GT p=0.9 en | GT vn | eff EN |
|---|---|---|---|---|
| `grok-4.20-**non**-reasoning` | 197.2 | 220.8 | **239.4** | +23.6 |
| `grok-4.20-**reasoning**` | 120.0 | 120.2 | 120.0 | +0.2 |

Bật reasoning kéo đóng góp từ ~200 xuống **đúng 120** — tiết kiệm 80 điểm trên 240. Ở tiếng
Việt bản non-reasoning chạm **239.4/240**, gần như dốc sạch endowment mọi vòng.

Nhưng **cả hai đều không nhạy risk**: EV-optimal đòi hỏi góp ~0 ở p=0.1, non-reasoning góp
197, reasoning góp 120. Nên reasoning được dùng để tối ưu *chi phí đạt mục tiêu*, chứ không
để hỏi *có nên đạt mục tiêu hay không*. Đây là cách phát biểu sắc hơn cho luận điểm
decoupling mà paper đã có.

---

## Hành vi EV-optimal: hai model làm đúng cả 3 mức

Endowment 40, target 120 (góp 2 × 10 vòng = 20):

| | Góp đủ target | Không góp gì | Tối ưu | gemini-3.1-pro | gpt-5.6-sol |
|---|---|---|---|---|---|
| p=0.1 | chắc chắn 20 | 0.9 × 40 = **36** | bỏ mặc | 0.0 ✅ | 1.6 ✅ |
| p=0.5 | chắc chắn 20 | 0.5 × 40 = **20** | bằng nhau | 120 (hợp tác) | 120 (hợp tác) |
| p=0.9 | chắc chắn **20** | 0.1 × 40 = 4 | hợp tác | 120 ✅ | 119.8 ✅ |

Payoff thực ở p=0.1: `gemini-3.1-pro` 32.0, `gpt-5.6-sol` 31.8 — đều cao hơn 20 nếu hợp tác,
tức thắng thật chứ không phải may. Ở p=0.5 (điểm bất phân EV), **cả 4 model bậc đỉnh** đều
chọn hợp tác ở mức tối thiểu đúng 120.

## Bốn giới hạn phải nói đúng

1. **Không model nào tái tạo pattern người.** Người: reach 0→10→50% tăng dần. Hai model
   EV-optimal: 0→100→100% — **hàm bậc thang theo ngưỡng EV**, lý trí hơn người chứ không mù hơn.
2. **KHÔNG chứng minh được chúng *tính* EV.** `reasoning` trong turns.jsonl chỉ chứa dòng
   `CONTRIBUTION: n`; proxy không trả reasoning channel. Chỉ nói được hành vi **trùng khớp**
   EV-optimal. Muốn bằng chứng cần thiết kế hỏi trực tiếp.
3. **Phương sai giữa các ván sụp về 0 ở bậc đỉnh** (SD ≈ 0 gần như mọi cell) → khái niệm
   "uncensored cell" mà paper dùng **không áp dụng được ở đây**. Phép kiểm phải so sánh
   **giữa** model, không hồi quy **trong** model.
4. **Hiệu ứng ngôn ngữ cũng là đặc tính từng model — 4 hướng khác nhau.** `gpt-5.4-nano`
   VN→góp ít hơn nhiều (146.8, lật reach 100%→0%); `gpt-5.6-sol` VN→tối ưu EV suy giảm
   (+118.2→+74.2, SD 1.6→47.7); `gemini-3.1-pro` VN→không ảnh hưởng (+120.0→+119.6);
   `grok-non-reasoning` VN→bão hòa ở mức tối đa 239.4. **ĐỪNG gộp thành một "hiệu ứng ngôn ngữ".**

---

## Việc tiếp theo

- [ ] Viết lại claim trung tâm của [paper](../paper/main.tex): null về risk **không phổ quát**.
      Công thức đúng là "năng lực cần nhưng không đủ", kèm đối chứng flash-lite vs pro.
- [ ] Chạy `gpt-5.6-luna` / `gpt-5.6-terra` (~$3 + $7): hiệu ứng thuộc **thế hệ 5.6** hay
      riêng bậc `sol`? Rẻ và trả lời một câu hỏi sạch.
- [ ] Comprehension cho frontier — vẫn chưa có điểm dữ liệu nào.
- [ ] Probe lại lab Trung Quốc (Qwen3/DeepSeek/GLM-5) — hiện 503 cả hai proxy.

## Chi phí thật theo model (~$110.50 / 37 shard)

| Model | Shard | $ |
|---|---|---|
| `claude-opus-5-default` | 12 | 40.94 |
| `gemini-3.1-pro-preview` | 6 | 36.54 |
| `gpt-5.6-sol` | 6 | 20.88 |
| `grok-4.20-reasoning` | 3 | 7.85 |
| smoke (2 đợt) | 6 | 2.93 |
| `grok-4.20-non-reasoning` | 4 | 1.36 |

**Bài học ngân sách:** giá/ván KHÔNG suy ra được giữa các cell. Cell risk 0.1 đắt hơn ~1.7×,
tiếng Việt đắt hơn ~1.45×, và tổ hợp 0.1/VN đắt gấp **2.4×** cell mốc 0.9/EN (đo trên
opus-5: $0.585 → $1.403/ván). Đo ở một cell rồi nhân cho cả sweep sẽ thiếu ~20–35%.
