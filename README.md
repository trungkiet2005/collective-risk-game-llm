# CRSD-LLM — Collective-Risk Social Dilemma cho LLM agents

Mô phỏng lại thí nghiệm của **Milinski et al. (2008, PNAS)** — *"The collective-risk
social dilemma and the prevention of simulated dangerous climate change"* — nhưng
người chơi là **các mô hình ngôn ngữ lớn (LLM)** thay vì con người.

Kiến trúc mô phỏng **FairGame** (config-driven, đa ngôn ngữ, chạy offline), tái dùng
các connector trong `FAIRGAME/` (gồm `local_vllm_connector` để chạy open-source model
trên GPU). Cơ chế tính điểm là **threshold + xổ số rủi ro** (không dùng payoff matrix).

> Trạng thái: **project init** — engine + pipeline đã chạy được end-to-end (mock,
> không cần GPU). Sẵn sàng cắm model offline (Qwen/Llama/Gemma) để chạy thật.

## Câu hỏi nghiên cứu

1. **Ngôn ngữ**: prompt tiếng Anh (EN) vs tiếng Việt (VN) cho kết quả hợp tác khác nhau thế nào?
2. **LLM có giống người không**: tỉ lệ đạt mục tiêu theo mức rủi ro, so với baseline người của Milinski 2008.
3. **Free-riding & công bằng**: phân bố đóng góp, bất bình đẳng (Gini), hiệu ứng vòng cuối.
4. **Persona/prompt**: tính cách gán cho agent ảnh hưởng hợp tác ra sao.

## Cấu trúc thư mục

```
Colective_Risk_Game/
├── crsd/                     # ⭐ package chính (project mới)
│   ├── engine/               # scoring, prompt, round, game, state, agent
│   ├── models/factory.py     # cầu nối connector FAIRGAME (offline + API)
│   ├── dataio/               # đọc config; ghi log (turns.jsonl, games.csv)
│   ├── analysis/metrics.py   # target-reach, Gini, free-riding, last-round, EN-vs-VN
│   ├── runner/               # run_experiment (CLI), batch (lockstep)
│   ├── configs/              # game/ · agents/ · experiment/ · offline/
│   ├── prompts/              # crsd_en.txt, crsd_vn.txt
│   └── tests/                # unit test (không cần GPU)
├── FAIRGAME/                 # framework gốc (đã sửa import -> dùng làm thư viện)
│   └── src/llm_connectors/local_vllm_connector.py   # connector offline tái dùng
├── docs/
│   ├── papers/               # tóm tắt paper dạng .md cho AI đọc
│   └── design/               # tài liệu thiết kế
├── requirements.txt          # offline-first
├── requirements-api.txt      # tuỳ chọn (API phase 2)
└── pyproject.toml
```

## Quickstart

> Chạy **từ thư mục gốc repo** (để `crsd` và `FAIRGAME` import được).

```bash
# 1. cài tối thiểu để chạy test + mock
pip install pandas numpy pytest

# 2. chạy unit test (không cần GPU)
python -m pytest crsd/tests -q

# 3. smoke-test TOÀN BỘ pipeline mà KHÔNG cần GPU (LLM giả lập)
python -m crsd.runner.run_experiment crsd/configs/experiment/exp_baseline.json --mock=random
#   -> kết quả ở results/exp_baseline/{turns.jsonl, games.csv}

# 4. chạy THẬT offline (sau khi cài vllm/torch và đặt modelPath trong configs/offline/)
python -m crsd.runner.run_experiment crsd/configs/experiment/exp_baseline.json
```

## Chạy model offline (RTX 6000 PRO 96GB)

1. Cài backend: `pip install vllm` (ưu tiên) hoặc `transformers torch sentencepiece accelerate`.
2. Sửa `crsd/configs/offline/models_qwen2.5-7b.json` → `modelPath` trỏ tới thư mục model local
   (hoặc tên HF nếu có mạng).
3. Chỉnh `crsd/configs/offline/offline_settings.json` (`backend`, `temperature`, `gpuMemoryUtilization`...).
4. Chạy lệnh ở bước 4 trên. Mọi prompt trong một vòng (của tất cả ván) được **batch** một lần
   generate để tối đa throughput (xem `crsd/runner/batch.py`).

### Chạy model 70B+ bằng quantize 4-bit (96GB VRAM, Kaggle Internet OFF)

bf16 72B ≈ 140GB **không vừa** 96GB → dùng checkpoint **quantize sẵn** (AWQ/GPTQ int4 ≈ 40GB,
còn ~45GB cho KV-cache). vLLM tự nhận quantization từ checkpoint — để `quantization=null`.

1. **Wheels** (notebook Internet ON): chạy [kaggle_build_quant_wheels.py](kaggle_build_quant_wheels.py)
   → Output → *New Dataset* (vd `crsd-quant-wheels`). Tải vllm + bitsandbytes + toàn bộ deps.
2. **Model** (notebook Internet ON): chạy [FAIRGAME/download_model.py](FAIRGAME/download_model.py)
   với `MODEL_ID = "Qwen/Qwen2.5-72B-Instruct-AWQ"` (hoặc
   `hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4`) → Output → *New Dataset*.
3. **Chạy** (notebook GPU 96GB, Internet OFF): dùng [kaggle_exp_baseline_72b.py](kaggle_exp_baseline_72b.py),
   + Add Input: repo + 2 dataset trên. Cell 2.5 tự dò wheels và cài offline.
4. Chạy local thì trỏ experiment tới preset có sẵn: `models_qwen2.5-72b-awq` ·
   `models_llama3.1-70b-awq` · `models_qwen2.5-72b-gptq-int4` · `models_qwen2.5-72b-bnb4bit`
   (đặt `offlineSettings.modelPreset` hoặc thêm block `engine` override — xem
   [docs/design/config-schema.md](docs/design/config-schema.md) mục 4–5).
   OOM? Theo thứ tự: `maxModelLen` 4096→2048 → `kvCacheDtype: "fp8"` → `maxNumSeqs: 32`
   → `cpuOffloadGb: 8`.

## Tài liệu

- Thiết kế: [docs/design/architecture.md](docs/design/architecture.md) ·
  [config-schema.md](docs/design/config-schema.md) ·
  [logging-schema.md](docs/design/logging-schema.md) ·
  [replication-plan.md](docs/design/replication-plan.md)
- Paper (AI-readable): [Milinski 2008](docs/papers/milinski-2008-collective-risk.md) ·
  [FairGame](docs/papers/fairgame-framework.md) ·
  [Related work](docs/papers/related-work-llm-social-dilemma.md) ·
  [Language effects](docs/papers/language-effects-llm.md)
- Lộ trình & trạng thái: [PROJECT.md](PROJECT.md)
