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
| `sampling.seedBase` | int | offset TOÀN CỤC cho seed sinh văn bản (mặc định 0); seed per-lượt vẫn suy từ `exp.seed + rep + round + agent` (xem `CrsdGame.sampling_seed`) |
| `engine.maxModelLen` | int | context tối đa (vLLM) |
| `engine.gpuMemoryUtilization` | float | tỉ lệ VRAM dùng (vLLM) |
| `engine.tensorParallelSize` | int | số GPU (1 = đơn GPU) |
| `engine.dtype` | str | `"auto"` (mặc định — theo checkpoint; AWQ/GPTQ → float16) / `"bfloat16"` / `"float16"`. CHỈ ép khi cố ý: ép bfloat16 lên checkpoint AWQ fp16 có thể bị vLLM từ chối |
| `engine.quantization` | str\|null | `null` = **tự nhận từ checkpoint** (AWQ/GPTQ quantize sẵn cứ để null); `"fp8"` = quantize on-the-fly checkpoint bf16; `"bitsandbytes"` = on-the-fly bf16 HOẶC checkpoint bnb-4bit quantize sẵn; ép `"awq"`/`"gptq"` chỉ khi kernel auto lỗi. Backend transformers: `"bnb-4bit"`/`"bnb-8bit"` |
| `engine.kvCacheDtype` | str\|null | `"fp8"` nén KV-cache khi VRAM sát nút; null/`"auto"` = mặc định |
| `engine.maxNumSeqs` | int\|null | giới hạn sequence chạy đồng thời (ghìm VRAM) |
| `engine.cpuOffloadGb` | number | >0 = đẩy bớt trọng số sang RAM (chậm — van xả cuối) |
| `engine.trustRemoteCode` | bool | cho model cần code tuỳ biến (mặc định `true`; áp cho cả vLLM lẫn transformers/tokenizer) |
| `batchSize` | int | 0 = batch cả list một lần |

> Lưu ý: với `backend="transformers"`, factory chỉ truyền
> `temperature/maxTokens/quantization/trustRemoteCode` (các knob vLLM bị bỏ qua).
> Knob quantize chỉ được truyền xuống engine khi đặt tường minh (khác
> null/"auto"/0) — config cũ chạy y hệt trước.

## 5. Model preset — `crsd/configs/offline/models_*.json`

| Field | Kiểu | Ý nghĩa |
|---|---|---|
| `abstractName` | str | tên trong `MODEL_PROVIDER_MAP` (vd `LocalQwen`) |
| `modelPath` | str | tên HF hoặc **đường dẫn local** để chạy offline |
| `engine` | dict (tuỳ chọn) | override đè lên `engine` của offline_settings — vd model 72B AWQ mang `quantization`/`gpuMemoryUtilization` riêng (xem `models_qwen2.5-72b-awq.json`) |
| `note` | str | ghi chú |

Preset 70B+ có sẵn: `models_qwen2.5-72b-awq` · `models_llama3.1-70b-awq` ·
`models_qwen2.5-72b-gptq-int4` · `models_qwen2.5-72b-bnb4bit` (bf16 72B ≈ 140GB
không vừa 96GB VRAM — bắt buộc 4-bit; AWQ int4 ≈ 41GB, còn ~45GB cho KV-cache).
