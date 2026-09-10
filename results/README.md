# results/ — data của vòng chạy MỚI

Thư mục này **rỗng từ 10-09-2026**. Data cũ đã dời sang
[`Lagecy_Results/results/`](../Lagecy_Results/README.md) và bị đóng băng.

Mọi thứ đổ vào đây phải thoả 2 điều kiện:

1. **Chạy server-side.** Sinh bằng `kaggle b t push` + `kaggle b t run` (qua
   `plan/scripts/launch_shard.py` hoặc các script `launch_*.py` gọi nó). **Không** nhận
   output của `python kaggle/benchmarks/crg_task_server.py` chạy ở máy local — local dùng
   proxy staging chỉ có 6/38 model nên data không so sánh được. Kết quả của
   `probe_all_models.py` / `probe_crg_prompt.py` là probe, không phải data, cũng không ghi
   vào đây.
2. **Gom bằng `merge_shards.py`**, có kiểm phủ đủ cell và `parse_failed == 0`:

   ```bash
   python plan/scripts/merge_shards.py --src plan/runs D:/tmp/crgdl --dry-run
   python plan/scripts/merge_shards.py --src plan/runs D:/tmp/crgdl --out results/frontier
   ```

Cấu trúc giữ nguyên như cũ để script phân tích đọc được:
`results/<arm>/<model_tag>/<experiment>/{games.csv,turns.jsonl}`.

Quy ước đầy đủ: xem [CLAUDE.md](../CLAUDE.md).
