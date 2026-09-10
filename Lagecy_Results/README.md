# Lagecy_Results/ — data CŨ, ĐÓNG BĂNG

Đây là toàn bộ thư mục `results/` của repo **tính đến 10-09-2026**, được dời sang đây khi
mở vòng chạy mới trên nhánh `aamas2027-e0`.

## Luật

1. **Chỉ đọc.** Không ghi đè, không xoá, không để script gom shard trỏ `--out` vào đây.
2. **Không tự ý phân tích và không tự ý viết vào `paper/`.** Data ở đây chỉ được lôi ra khi
   **người dùng yêu cầu rõ ràng**. Không có yêu cầu thì coi như thư mục này không tồn tại —
   kể cả khi đang thiếu số để điền vào một bảng trong paper.
3. **Đừng trộn với data mới.** Nó trải nhiều panel, nhiều bản prompt và nhiều vòng chạy khác
   nhau; gộp nhầm vào một bảng là lỗi âm thầm, rất khó phát hiện lúc review.

## Có gì bên trong

| Đường dẫn | Nội dung |
|---|---|
| `results/open_source/` | 7 model open-weight chạy vLLM trên Kaggle GPU — `exp_baseline`, `exp_comprehension`, `exp_riskframing`, `exp_persona` |
| `results/frontier/` | Sweep frontier qua Kaggle Model Proxy (Ngày A/B, tháng 8/2026) |
| `results/frontier/dense_grid/` | Lưới risk dày (Q8, 09-09-2026) |
| `results/scripted_reference/` | Baseline agent viết tay (không gọi LLM) |
| `results/raw/` | Zip tải thẳng từ notebook Kaggle, chưa gộp |

Data của vòng chạy MỚI nằm ở `results/` ở gốc repo. Quy ước đầy đủ: xem
[CLAUDE.md](../CLAUDE.md).
