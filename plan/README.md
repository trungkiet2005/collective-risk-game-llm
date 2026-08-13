# plan/ — kế hoạch đang chạy của CRSD-LLM

Thư mục này giữ kế hoạch **đang thực thi**, để một session/chat sau mở ra là biết
đang ở đâu và làm gì tiếp. Khác với [PROJECT.md](../PROJECT.md) (lộ trình tổng, hiện
đã lạc hậu so với thực tế) và [CLAUDE.md](../CLAUDE.md) (quy ước code + credential).

## Đang làm gì: mở rộng nhánh frontier từ 1 model lên panel nhiều model

Đọc theo thứ tự này:

| File | Nội dung |
|---|---|
| [findings-top-tier.md](findings-top-tier.md) | **🔥 KẾT QUẢ.** `gpt-5.6-sol` PHẢN ỨNG với risk (+118.2 điểm) — đảo ngược claim trung tâm của paper |
| [runbook-top-tier.md](runbook-top-tier.md) | **⚡ ĐANG CHẠY.** Hướng dẫn thực thi bậc đỉnh: phân account, chia shard, gom result, sự cố |
| [frontier-run-plan.md](frontier-run-plan.md) | Kế hoạch tổng: panel theo lưới nhà cung cấp × bậc, Ngày 1→4 |
| [model-availability.md](model-availability.md) | 38 slug trên Kaggle Model Proxy: cái nào sống, sống ở đâu, giá bao nhiêu |
| [scripts/](scripts/) | xem bảng script dưới |

### Script

| Script | Việc |
|---|---|
| `launch_day_a.py` | phóng cả 12 shard Ngày A song song (`--dry-run` để xem trước) |
| `launch_shard.py` | chạy 1 shard trên 1 account: auth → sinh file shard → push → run → download |
| `check_runs.py` | xem trạng thái mọi shard (đọc log, không gọi API), `--watch` để tự làm mới |
| `merge_shards.py` | gom shard thành dataset, kiểm phủ đủ 60 cell + `parse_failed=0` |
| `probe_all_models.py` | probe liveness song song ở local (staging proxy) |
| `probe_crg_prompt.py` | kiểm model trả lời được 1 lượt CRG thật và parse được |

Kết quả + log của mỗi shard nằm ở `plan/runs/<label>/` (đã gitignore, không commit).

**Người dùng đã chọn chạy bậc đỉnh (top tier) TRƯỚC**, không screen trước — 4 model
`claude-opus-5` · `gemini-3.1-pro-preview` · `gpt-5.6-sol` · `grok-4.20-reasoning`, ~$88.
Rủi ro (cả 4 có thể cán trần) đã được nêu và người dùng vẫn chọn. **Đừng tự ý đổi sang
screen-trước**; muốn đổi thì hỏi.

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

## 🌅 Việc đầu tiên sáng 13-08-2026

Ngày A đã chạy đêm 12→13/08. **14/16 shard xong, $49.54.** Làm đúng 3 lệnh này:

```bash
# 1) Shard nào run xong mà chưa có data trên máy -> tải lại. KHÔNG chạy lại run.
python plan/scripts/redownload_all.py

# 2) Kiểm phủ đủ 60 cell chưa (exit 1 + liệt kê cell thiếu nếu chưa)
python plan/scripts/merge_shards.py --src plan/runs D:/tmp/crgdl --dry-run

# 3) Ghi vào results/frontier/
python plan/scripts/merge_shards.py --src plan/runs D:/tmp/crgdl --out results/frontier
```

**Mọi shard phóng trước 03:00 ngày 13/08 đều bị lỗi download do đường dẫn Windows 260 ký
tự** — run thành công, đã tốn tiền, nhưng data không xuống máy. Data VẪN CÒN trên server,
`redownload_all.py` lấy về. Đừng chạy lại run.

Kết quả đã có: xem [findings-top-tier.md](findings-top-tier.md).
`gpt-5.6-sol` và `grok-4.20-reasoning` đã đủ 60 ván và nằm trong `results/frontier/`.
Còn 2 shard `gemini-3.1-pro` risk 0.1 (`hunhtrungkit`, `tnkiet`) — nếu chúng lỗi thì chạy
lại bằng `launch_shard.py` với account dự phòng `chiboiz`.

Sau đó: Ngày B (`claude-opus-5`, 6 shard × 10 ván × $5.85 = $35.11), và phép thử rẻ giá trị
cao **`grok-4.20-0309-non-reasoning`** (~$1.7) — xem lý do trong findings.

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
