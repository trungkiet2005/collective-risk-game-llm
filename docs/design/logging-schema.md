# Logging schema

Mỗi experiment ghi vào `results/<experiment_name>/`:

## `turns.jsonl` — một dòng JSON / lượt quyết định

Dành cho phân tích reasoning / XAI. Một dòng = 1 agent ở 1 vòng của 1 ván.

| Field | Kiểu | Ý nghĩa |
|---|---|---|
| `game_id` | str | `<game>__<model>__<lang>__rep<k>` |
| `round` | int | số vòng (1..nRounds) |
| `player` | str | tên agent |
| `contribution` | number | mức đóng đã parse (0/2/4) |
| `parse_failed` | bool | true nếu không parse được (đã fallback) |
| `reasoning` | str | phản hồi trừ dòng CONTRIBUTION |
| `raw_response` | str | phản hồi thô đầy đủ của LLM |
| `prompt` | str | prompt đã gửi (đầy đủ, để tái lập/kiểm tra) |
| `logprobs` | dict\|null | `{token_logprobs, cumulative_logprob, top_alternatives}` nếu bật (vLLM) |
| `latency_ms` | number\|null | (chừa sẵn) |

## `games.csv` — một dòng / ván

Bảng tổng hợp để phân tích thống kê.

| Cột | Ý nghĩa |
|---|---|
| `game_id` | định danh ván |
| `model` | model dùng |
| `language` | `en` / `vn` / ... |
| `risk_probability` | 0.9 / 0.5 / 0.1 |
| `persona_set` | preset agent |
| `group_total` | tổng đóng góp cả nhóm |
| `target` | ngưỡng |
| `target_reached` | 1/0 |
| `catastrophe` | 1/0 (thảm hoạ có xảy ra không) |
| `mean_payoff` | payoff trung bình/người |
| `seed` | seed của ván |

## Gợi ý phân tích

`crsd/analysis/metrics.py` nhận list `GameResult` (hoặc đọc lại CSV) và cung cấp:

- `target_reach_rate(results)` → `{(lang, risk): tỉ lệ đạt}` — so với
  `HUMAN_BASELINE_REACH_RATE = {0.9: 0.50, 0.5: 0.10, 0.1: 0.00}` (Milinski 2008).
- `language_comparison(results)` → reach_rate & mean_group_total theo `(lang, risk)`.
- `contribution_gini(result)`, `free_riding_rate(result)`, `last_round_drop(result)`.

> Đầy đủ chi tiết từng người (per-player payoffs, per-round contributions) nằm trong
> `GameResult` (giữ trong bộ nhớ khi chạy). Nếu cần lưu xuống đĩa để phân tích sâu,
> mở rộng `recorder.py` ghi thêm một `games.jsonl` từ `GameResult.to_dict()`.
