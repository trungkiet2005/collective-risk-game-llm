# Kiến trúc `crsd`

Mục tiêu: chạy Collective-Risk Social Dilemma (Milinski 2008) với LLM agents, kiểu
FairGame (config-driven, đa ngôn ngữ, offline-first), tái dùng connector của `FAIRGAME`.

## Luồng tổng quát

```
experiment config (JSON)
        │  (games × languages × models × repetitions)
        ▼
run_experiment ──► build CrsdGame[]  ──►  run_games_batched(games, send_batch)
        │                                         │  mỗi vòng: gom prompt mọi ván → 1 lần generate
        │                                         ▼
        │                                  CrsdGame.apply_round_responses (parse 0/2/4, log turn)
        │                                         ▼
        │                                  CrsdGame.finalize (threshold + xổ số rủi ro → payoff)
        ▼
dataio.recorder ──► results/<exp>/turns.jsonl  +  games.csv
        ▼
analysis.metrics ──► target-reach theo risk, Gini, free-riding, last-round, EN-vs-VN
```

`send_batch(list[str]) -> list[str|dict]` là điểm cắm mô hình:
- offline → `local_vllm_connector.send_prompts_global` (1 generate cho cả batch);
- API → gọi tuần tự `ChatModelFactory`;
- mock → trả CONTRIBUTION giả lập (test không cần GPU).

## Các module

| Module | Vai trò |
|---|---|
| `engine/state.py` | `GameConfig`, `TurnRecord`, `GameResult` (dataclass) |
| `engine/scoring.py` | logic thuần: remaining, group_total, threshold, **draw_catastrophe**, `final_payoffs` |
| `engine/prompt.py` | điền template: placeholder `{x}` + block điều kiện `{name}: [...]` |
| `engine/round.py` | `CrsdRound.build_prompts`, `parse_contribution` (0/2/4) |
| `engine/agent.py` | `CrsdAgent` (tên, persona, lịch sử đóng góp) |
| `engine/game.py` | `CrsdGame`: stepwise (`build_round_prompts`/`apply_round_responses`/`finalize`) + `run` |
| `models/factory.py` | `init_offline_backend`, `get_send_batch` (offline + API) |
| `dataio/config_loader.py` | đọc + validate JSON |
| `dataio/recorder.py` | ghi `turns.jsonl`, `games.csv` |
| `analysis/metrics.py` | Gini, target-reach, free-riding, last-round, language_comparison |
| `runner/batch.py` | `run_games_batched` (lockstep nhiều ván) |
| `runner/run_experiment.py` | CLI driver toàn campaign |

## Quyết định thiết kế

- **Game stepwise** (`build_round_prompts` rồi `apply_round_responses`) để cùng engine chạy
  được cả tuần tự lẫn lockstep-batched — batch là chìa khoá throughput trên GPU 96GB.
- **Engine riêng, không payoff-matrix**: CRSD là N người + ngưỡng + thảm hoạ xác suất; tính
  điểm bằng công thức, không liệt kê tổ hợp (xem [fairgame-framework.md](../papers/fairgame-framework.md) §3).
- **Xổ số rủi ro 1 lần/ván**, qua `random.Random(seed)` → tái lập. Hai ván cùng seed khác mức
  rủi ro dùng chung số uniform (common random numbers) — giảm phương sai khi so theo cặp.
- **Tách reasoning khỏi quyết định**: prompt yêu cầu dòng cuối `CONTRIBUTION: <n>`; parser ưu
  tiên dòng này, lưu cả `raw_response` + `reasoning` để phân tích XAI.
- **i18n**: 1 template/ngôn ngữ ở `prompts/crsd_{lang}.txt`; token `CONTRIBUTION:` giữ tiếng Anh
  để parser nhất quán giữa các ngôn ngữ.

## Mở rộng dự kiến

- `agentsCommunicate=true` → thêm phase chat giữa các vòng (bản gốc không có).
- Parameter sweep (group size, target, options) — đã config-driven nên chỉ thêm file game.
- Thêm model: offline → thêm preset `configs/offline/models_*.json`; API → có sẵn trong
  `MODEL_PROVIDER_MAP` của FAIRGAME.
