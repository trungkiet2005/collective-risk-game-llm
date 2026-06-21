# PROJECT — CRSD-LLM

Tài liệu trạng thái & lộ trình. Cập nhật khi đổi hướng.

## Mục tiêu

Paper nghiên cứu: cho LLM chơi **collective-risk social dilemma** (Milinski et al. 2008),
phân tích hành vi hợp tác dưới các mức rủi ro, **so sánh ngôn ngữ EN vs VN**, free-riding/
công bằng, và ảnh hưởng persona.

## Quyết định kiến trúc (chốt)

- **Kiến trúc kiểu FairGame**, config-driven, đa ngôn ngữ, offline-first.
- **FAIRGAME giữ ở top-level**, import dạng `FAIRGAME.src...` (đã sửa từ `legacy.FAIRGAME`),
  dùng như thư viện connector. Package nghiên cứu mới = `crsd/`.
- **Engine riêng cho CRSD** (threshold + xổ số rủi ro) — KHÔNG dùng payoff-matrix của FairGame
  vì CRSD là game N người, tích luỹ, có ngưỡng + thảm hoạ xác suất.
- **Model**: phase 1 open-source nhỏ (Qwen/Llama/Gemma 7–8B) chạy offline trên RTX 6000 PRO 96GB
  (qua `local_vllm_connector`); phase 2 API (Claude/OpenAI) tính tiền sau, cùng một interface.

## Tham số replicate Milinski 2008 (mặc định)

6 người · endowment 40 · đóng 0/2/4 mỗi vòng · target 120 · 10 vòng · risk 10/50/90% ·
10 nhóm/điều kiện. Xem [docs/design/replication-plan.md](docs/design/replication-plan.md).

## Trạng thái

- [x] Init project, vá import FAIRGAME, dựng package `crsd`.
- [x] Engine CRSD (scoring/round/game), config-driven, prompt EN+VN.
- [x] Model factory tái dùng connector offline; runner lockstep-batched; logging turns/games.
- [x] Unit test (17 test, pass) + smoke-test mock end-to-end (60 ván) chạy được.
- [x] Docs: 4 paper.md + 4 design.md.
- [ ] Chạy thật với 1 model offline (Qwen2.5-7B) — kiểm tra parse rate thực tế.
- [ ] Module phân tích/biểu đồ (target-reach theo risk, EN-vs-VN, Gini) → bảng/hình cho paper.
- [ ] Mở rộng: persona sweep, communication giữa các vòng, thêm model & API.

## Việc tiếp theo gợi ý

1. Cài `vllm`, đặt `modelPath`, chạy `exp_baseline.json` với `repetitions` nhỏ (vd 2)
   để kiểm tra **parse rate** (`parse_failed` trong turns.jsonl) và chất lượng reasoning.
2. Nếu parse rate thấp ở VN, tinh chỉnh template VN / nới `parse_contribution`.
3. Viết notebook phân tích đọc `games.csv` + `turns.jsonl` → dùng `crsd/analysis/metrics.py`.
