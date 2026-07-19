# FairGame — phân tích kiến trúc (bản đã đối chiếu code trong repo này)

Tài liệu này mô tả framework **FairGame** như nó tồn tại trong `FAIRGAME/` của repo,
để hiểu cái gì được **tái dùng** cho project `crsd`. Viết từ việc đọc trực tiếp source.

- Paper: *FAIRGAME: a Framework for AI Agents Bias Recognition using Game Theory*
  (Buscemi, Proverbio, Di Stefano, Han, Castignani, Liò, 2025) — arXiv 2504.14325, ECAI 2025.
- Repo gốc: https://github.com/aira-list/FAIRGAME (Apache-2.0).
- Bản trong repo này là **fork đã mở rộng** để chạy offline + Kaggle.

## 1. Ý tưởng

Cho LLM agents chơi các game lý thuyết trò chơi (Prisoner's Dilemma, Stag Hunt,
Snowdrift, Harmony, Battle of the Sexes, Volunteer's Dilemma), chạy cùng một game
qua nhiều hoán vị (model × ngôn ngữ × tính cách × mức biết luật) rồi so kết quả với
cân bằng lý thuyết để phát hiện **bias** (lệch do yếu tố đáng lẽ vô can: ngôn ngữ,
persona, model).

## 2. Khác biệt quan trọng trong fork này

- **Import**: toàn bộ dùng `FAIRGAME.src...` (đã đổi từ `legacy.FAIRGAME...`). Nghĩa là
  thư mục `FAIRGAME/` nằm ở gốc repo và được import như package `FAIRGAME`.
- **Đã thêm cho chạy offline** (không có trong repo gốc public):
  - `FAIRGAME/src/llm_connectors/local_vllm_connector.py` — connector vLLM/transformers.
  - `FAIRGAME/src/batch_runner.py` — chạy nhiều game lockstep + batch LLM.
  - `FAIRGAME/download_model.py`, `kaggle_notebook*.py`, `offline_patch_assets/`.
  - `requirements.txt` đã rút gọn offline-first (bỏ SDK cloud).

## 3. Cấu trúc engine (game 2 người / N người qua payoff matrix)

| Module | Vai trò |
|---|---|
| `src/fairgame.py` (`FairGame`) | vòng lặp game, gọi payoff matrix, điều kiện dừng |
| `src/game_round.py` (`GameRound`) | 1 vòng: phase communicate + choose, **parse strategy** |
| `src/payoff_matrix.py` (`PayoffMatrix`) | tra cứu tổ hợp strategy → weights (điểm) |
| `src/agent.py` (`Agent`) | một người chơi gắn 1 LLM |
| `src/prompt_creator.py` (`PromptCreator`) | điền template (placeholder + block `{x}: [...]`) |
| `src/fairgame_factory.py` (`FairGameFactory`) | bung hoán vị (model/ngôn ngữ/persona) + chạy |
| `src/io_managers/` | đọc config/template, validate, transform payoff matrix |
| `src/results_processing/` | history dict → DataFrame → CSV |
| `src/template_translation/` | dịch template bằng LLM + kiểm tra cosine |

**Điểm mấu chốt cho CRSD**: `PayoffMatrix` tính điểm bằng **liệt kê tổ hợp** strategy
(`combinations` → `matrix` → `weights`). Cách này hợp game ít người/ít lựa chọn, **không
hợp** Collective-Risk (6 người × 3 lựa chọn = 729 tổ hợp/vòng, lại còn ngưỡng + xổ số rủi ro).
→ `crsd` viết engine scoring riêng, chỉ tái dùng các phần khác.

## 4. Connector mô hình (cái `crsd` tái dùng)

Interface: `AbstractConnector.send_prompt(prompt: str) -> str`.

**`local_vllm_connector.py`** (offline, singleton toàn cục):
- `init_local_llm(model_path, engine="vllm", **kwargs)` — nạp engine MỘT lần.
  - vLLM kwargs: `max_model_len, temperature, max_tokens, gpu_memory_utilization, tensor_parallel_size`.
  - transformers kwargs: `temperature, max_tokens` (flash-attn → SDPA fallback, left-padding để batch).
- `send_prompts_global(prompts, batch_size=0)` — generate cả batch một lần (dùng cho batch_runner).
- `LocalVLLMConnector.send_prompt(prompt)` / `.send_prompt_with_details(prompt)` — bản sau trả
  `{text, cumulative_logprob, token_logprobs, top_alternatives}` (logprobs top-5, cho XAI; chỉ vLLM).

**`llm_factory_connector.py`**:
- `MODEL_PROVIDER_MAP`: ánh xạ tên trừu tượng → (class, model id). Gồm API
  (`Claude35Haiku`, `OpenAIGPT4o`, `MistralLarge`; import lazy) và offline
  (`LocalQwen`, `LocalLlama`, `LocalGemma`, `LocalMistral`, `LocalModel` → `LocalVLLMConnector`).
- `ChatModelFactory.get_model(name)` và `execute_prompt(name, prompt)`.

## 5. Config-driven & đa ngôn ngữ

- Config: 1 JSON/game ở `resources/config/*.json`. `ConfigValidator.REQUIRED_KEYS` =
  `name, nRounds, nRoundsIsKnown, payoffMatrix, allAgentPermutations, agents, llm, languages,
  stopGameWhen, agentsCommunicate`. Có coerce `"llms"`(list)→`"llm"` và string-bool→bool.
- Template prompt: 1 file/game/ngôn ngữ ở `resources/game_templates/{game}_{lang}.txt`.
  Ngôn ngữ có sẵn: `ar, cn, en, fr, vn` — **đã có tiếng Việt**, rất hợp research question EN-vs-VN.
- Placeholder đơn `{x}` + block điều kiện `{name}: [ ... ]` (regex `\{(\w+)\}:\s*\[(.*?)\]`).

## 6. `crsd` tái dùng gì từ FAIRGAME

| Tái dùng trực tiếp | Viết lại trong `crsd` |
|---|---|
| `local_vllm_connector` (init/send/batch/logprobs) | Engine scoring (threshold + risk lottery) |
| Mẫu `MODEL_PROVIDER_MAP` / factory cho API | Cơ chế prompt template (CRSD-specific) |
| Ý tưởng batch lockstep (`batch_runner`) | Round CRSD (đồng thời, parse 0/2/4) |
| Quy ước template `{x}` + block `{name}: [...]` | Logging turns/games, metrics, runner |
