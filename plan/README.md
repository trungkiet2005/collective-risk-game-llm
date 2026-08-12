# plan/ — kế hoạch đang chạy của CRSD-LLM

Thư mục này giữ kế hoạch **đang thực thi**, để một session/chat sau mở ra là biết
đang ở đâu và làm gì tiếp. Khác với [PROJECT.md](../PROJECT.md) (lộ trình tổng, hiện
đã lạc hậu so với thực tế) và [CLAUDE.md](../CLAUDE.md) (quy ước code + credential).

## Đang làm gì: mở rộng nhánh frontier từ 1 model lên panel nhiều model

Đọc theo thứ tự này:

| File | Nội dung |
|---|---|
| [frontier-run-plan.md](frontier-run-plan.md) | **Kế hoạch chính.** Ngày 1→4, model nào chạy, lệnh cụ thể, checkbox tiến độ |
| [model-availability.md](model-availability.md) | 38 slug trên Kaggle Model Proxy: cái nào sống, sống ở đâu, giá bao nhiêu |
| [scripts/](scripts/) | Script probe tái sử dụng — chạy lại khi cần kiểm tra availability |

## Trạng thái tính đến 13-08-2026

**Data đã có:**

| Arm | Model | Experiment | Số ván |
|---|---|---|---|
| open_source | 7 model (Qwen2.5 7/32/72B, Llama-3.1 8/70B, Gemma-2 9/27B) | exp_baseline | 60 mỗi model |
| open_source | 5 model | exp_comprehension | 120 mỗi model |
| open_source | 7 model | exp_riskframing | 60 mỗi model |
| open_source | 3 model nhỏ | exp_persona | 420 mỗi model |
| frontier | `gemini-3.1-flash-lite-preview` | exp_baseline | 60 (10 rep) |
| frontier | `gpt-5.4-nano` | exp_baseline | 30 (5 rep) — **chạy qua OpenAI API, không qua Kaggle proxy** |
| frontier | `gpt-5.4-nano` | exp_persona | 210 |
| frontier | `claude-haiku-4-5` | — | 1 ván smoke trong `archive/`, chưa có data thật |

**Việc tiếp theo:** Ngày 1 trong [frontier-run-plan.md](frontier-run-plan.md) — sửa 2 chỗ
trong `kaggle/benchmarks/crg_task_server.py` rồi smoke 4 họ model chưa từng chạy.

**Panel đang nhắm tới:** lưới **nhà cung cấp × bậc năng lực** — 13 model / 4 nhà cung cấp
(Anthropic 3, Google 4 gồm 1 open-weight, OpenAI 4, xAI 2). Proxy chỉ còn 4 nhà cung cấp;
ba nhà đã chết sạch đều là lab Trung Quốc (Alibaba/Qwen3, DeepSeek, Zhipu/GLM-5) nên nhánh
frontier hiện không có đại diện lab Trung Quốc — cần probe lại định kỳ.

## Ba sự thật đắt tiền, đừng phát hiện lại

1. **Local và server-side dùng 2 proxy khác nhau.** Local (`.env` → `mp-staging`) chỉ
   phục vụ 6 model. Server-side (`kaggle b t run`) phục vụ 28. Model báo 503 ở local
   hoàn toàn có thể chạy tốt server-side — đừng kết luận nó chết.

2. **503 là lỗi phía Kaggle, không phải hết quota.** Đã kiểm chứng bằng 3 account độc
   lập cho ra đúng cùng một tập 503. Đổi account không cứu được.

3. **Proxy đặt cọc tiền trước theo `max_output_tokens`, không theo token thực tiêu.**
   Không set cap tường minh thì model đắt bị 403 dù thực tế chỉ tốn vài xu. Xem chi
   tiết trong [frontier-run-plan.md](frontier-run-plan.md#ngày-1).

## Quy ước cập nhật thư mục này

- Chạy xong một bước thì **tick checkbox** trong `frontier-run-plan.md` và ghi số thật
  (chi phí, số ván, reach) vào cột kết quả — số ước tính trong plan sai tới ±3×.
- Availability thay đổi (model sống lại / chết đi) thì cập nhật `model-availability.md`
  kèm ngày probe.
- Kế hoạch đổi hướng thì sửa thẳng file, đừng tạo file `-v2`.
