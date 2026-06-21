# Config schema

Tất cả config là **JSON thuần** (không comment). Mô tả field ở đây.

## 1. Game — `crsd/configs/game/*.json`

| Field | Kiểu | Ý nghĩa | Mặc định Milinski |
|---|---|---|---|
| `name` | str | tên ván (= tên file) | — |
| `engine` | str | bộ engine | `"collective_risk"` |
| `nPlayers` | int | số người chơi | `6` |
| `endowment` | number | vốn ban đầu mỗi người | `40` |
| `contributionOptions` | list[number] | mức đóng cho phép mỗi vòng | `[0, 2, 4]` |
| `target` | number | ngưỡng tổng đóng góp của nhóm | `120` |
| `nRounds` | int | số vòng | `10` |
| `nRoundsIsKnown` | bool | agent có biết số vòng không | `true` |
| `riskProbability` | float [0,1] | xác suất thảm hoạ nếu KHÔNG đạt target | `0.90 / 0.50 / 0.10` |
| `showIndividualContributions` | bool | cho thấy đóng góp từng người ở lịch sử | `true` |
| `agentsCommunicate` | bool | có phase giao tiếp không (chưa bật ở init) | `false` |
| `promptTemplate` | str | tên template (→ `prompts/<name>_<lang>.txt`) | `"crsd"` |
| `agents` | str | preset agent mặc định | `"personas_default"` |

## 2. Agents/personas — `crsd/configs/agents/*.json`

| Field | Kiểu | Ý nghĩa |
|---|---|---|
| `name` | str | tên preset |
| `nPlayers` | int | số người (khớp game) |
| `names` | list[str] | tên từng agent |
| `personas` | dict[lang → list[str]] | câu mô tả tính cách theo ngôn ngữ; rỗng `""` = trung tính (bỏ block persona) |
| `description` | str | ghi chú |

`personas_default` = 6 agent trung tính (replicate). `personas_mixed` = trộn selfish/altruist/fair/risk-averse.

## 3. Experiment — `crsd/configs/experiment/*.json`

| Field | Kiểu | Ý nghĩa |
|---|---|---|
| `name` | str | tên campaign (→ thư mục output) |
| `games` | list[str] | danh sách tên game config |
| `agents` | str | preset agent |
| `languages` | list[str] | ngôn ngữ chạy (vd `["en","vn"]`) |
| `models` | list[str] | tên model trừu tượng (vd `["LocalQwen"]`) |
| `useOffline` | bool | true = connector offline; false = API |
| `offlineSettings` | str | tên file trong `configs/offline/` |
| `repetitions` | int | số lần lặp/điều kiện (Milinski: 10 nhóm) |
| `seed` | int | seed gốc; ván rep k dùng `seed+k` |
| `captureReasoning` | bool | lưu reasoning (luôn lưu raw_response) |
| `captureLogprobs` | bool | lưu logprobs (chỉ vLLM, qua send_prompt_with_details) |

Ma trận chạy = `games × languages × models × repetitions`.

## 4. Offline settings — `crsd/configs/offline/offline_settings.json`

| Field | Kiểu | Ý nghĩa |
|---|---|---|
| `backend` | str | `"vllm"` (ưu tiên) hoặc `"transformers"` |
| `modelPreset` | str | tên file preset model (mục 5) |
| `sampling.temperature` | float | nhiệt độ sinh |
| `sampling.maxTokens` | int | token tối đa mỗi phản hồi |
| `sampling.seed` | int | seed sampling (tuỳ backend) |
| `engine.maxModelLen` | int | context tối đa (vLLM) |
| `engine.gpuMemoryUtilization` | float | tỉ lệ VRAM dùng (vLLM) |
| `engine.tensorParallelSize` | int | số GPU (1 = đơn GPU) |
| `engine.dtype` | str | vd `"bfloat16"` |
| `engine.trustRemoteCode` | bool | cho model cần code tuỳ biến |
| `batchSize` | int | 0 = batch cả list một lần |

> Lưu ý: với `backend="transformers"`, factory chỉ truyền `temperature/maxTokens`
> (các knob vLLM bị bỏ qua) để khớp chữ ký `init_local_llm`.

## 5. Model preset — `crsd/configs/offline/models_*.json`

| Field | Kiểu | Ý nghĩa |
|---|---|---|
| `abstractName` | str | tên trong `MODEL_PROVIDER_MAP` (vd `LocalQwen`) |
| `modelPath` | str | tên HF hoặc **đường dẫn local** để chạy offline |
| `note` | str | ghi chú |
