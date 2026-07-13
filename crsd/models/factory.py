"""Cầu nối mô hình: tái dùng connector trong package FAIRGAME.

- Offline (open-source, GPU): dùng ``local_vllm_connector`` (vLLM hoặc
  transformers). Engine nạp MỘT lần qua ``init_local_llm`` (singleton trong
  module đó), gọi batch qua ``send_prompts_global``.
- API (phase 2): dùng ``ChatModelFactory`` của FAIRGAME (Claude/OpenAI/Mistral).
  Import lazy nên không cần SDK khi chạy offline.

Lưu ý: ``init_local_llm`` dùng singleton toàn cục — trong MỘT tiến trình chỉ nạp
được một model offline. Muốn so nhiều model offline thì chạy mỗi model một lần
(một process) hoặc mở rộng connector để reset engine.
"""
from __future__ import annotations

from typing import Callable, List, Union

OFFLINE_MODELS = {"LocalQwen", "LocalLlama", "LocalGemma", "LocalMistral", "LocalModel"}


def is_offline_model(name: str) -> bool:
    return name in OFFLINE_MODELS


def merged_engine_settings(offline_settings: dict, model_preset: dict) -> dict:
    """Gộp engine settings: block ``engine`` trong preset model ĐÈ lên offline_settings.

    Cho phép mỗi preset (models_*.json) mang override riêng — vd model 72B AWQ cần
    ``quantization``/``dtype``/``gpuMemoryUtilization`` khác mặc định — mà không phải
    sửa file offline_settings dùng chung cho mọi model.
    """
    eng = dict(offline_settings.get("engine", {}) or {})
    eng.update(model_preset.get("engine", {}) or {})
    return eng


def vllm_init_kwargs(offline_settings: dict, model_preset: dict) -> dict:
    """Dựng kwargs cho ``init_local_llm`` (backend vllm). Thuần logic — test không cần GPU.

    Các knob quantization/dtype/kv-cache CHỈ đưa vào kwargs khi đặt tường minh
    (khác None/"auto"/0), để config cũ chạy y hệt trước đây và vLLM đời cũ (chưa có
    tham số tương ứng) không vỡ khi không dùng tính năng mới.
    """
    samp = offline_settings.get("sampling", {}) or {}
    eng = merged_engine_settings(offline_settings, model_preset)
    kwargs = dict(
        max_model_len=int(eng.get("maxModelLen", 4096)),
        temperature=float(samp.get("temperature", 0.7)),
        max_tokens=int(samp.get("maxTokens", 512)),
        gpu_memory_utilization=float(eng.get("gpuMemoryUtilization", 0.90)),
        tensor_parallel_size=int(eng.get("tensorParallelSize", 1)),
        enforce_eager=bool(eng.get("enforceEager", True)),
        trust_remote_code=bool(eng.get("trustRemoteCode", True)),
    )
    if eng.get("quantization"):
        kwargs["quantization"] = str(eng["quantization"])
    if eng.get("dtype") and str(eng["dtype"]).lower() != "auto":
        kwargs["dtype"] = str(eng["dtype"])
    if eng.get("kvCacheDtype") and str(eng["kvCacheDtype"]).lower() != "auto":
        kwargs["kv_cache_dtype"] = str(eng["kvCacheDtype"])
    if eng.get("maxNumSeqs"):
        kwargs["max_num_seqs"] = int(eng["maxNumSeqs"])
    if eng.get("cpuOffloadGb"):
        kwargs["cpu_offload_gb"] = float(eng["cpuOffloadGb"])
    return kwargs


def transformers_init_kwargs(offline_settings: dict, model_preset: dict) -> dict:
    """Dựng kwargs cho ``init_local_llm`` (backend transformers). Thuần logic.

    Backend này chỉ nhận ``quantization`` dạng bnb ("bnb-4bit"/"bnb-8bit") — connector
    tự validate và báo lỗi rõ nếu nhận giá trị kiểu vLLM (awq/gptq/fp8).
    """
    samp = offline_settings.get("sampling", {}) or {}
    eng = merged_engine_settings(offline_settings, model_preset)
    kwargs = dict(
        temperature=float(samp.get("temperature", 0.7)),
        max_tokens=int(samp.get("maxTokens", 512)),
        trust_remote_code=bool(eng.get("trustRemoteCode", True)),
    )
    if eng.get("quantization"):
        kwargs["quantization"] = str(eng["quantization"])
    return kwargs


def init_offline_backend(offline_settings: dict, model_preset: dict, force: bool = False) -> None:
    """Khởi tạo engine offline dựa trên offline_settings + model preset.

    ``force=True`` để nạp lại model khác trong cùng tiến trình (vd quét nhiều model
    trên một GPU Kaggle: load → run → free → model kế tiếp).

    Preset model có thể mang block ``engine`` override (xem ``merged_engine_settings``)
    — cách khai báo quantization cho model 70B+ mà không đụng settings chung.
    """
    from FAIRGAME.src.llm_connectors.local_vllm_connector import init_local_llm

    backend = offline_settings.get("backend", "vllm")
    model_path = model_preset["modelPath"]

    if backend == "vllm":
        init_local_llm(
            model_path, engine="vllm", force=force,
            **vllm_init_kwargs(offline_settings, model_preset),
        )
    elif backend == "transformers":
        init_local_llm(
            model_path, engine="transformers", force=force,
            **transformers_init_kwargs(offline_settings, model_preset),
        )
    else:
        raise ValueError(
            f"backend offline không hỗ trợ: {backend!r} (dùng 'vllm' hoặc 'transformers')"
        )


def get_send_batch(
    model_name: str, offline: bool = True, batch_size: int = 0
) -> Callable[[List[str]], List[Union[str, dict]]]:
    """Trả về hàm ``send_batch(list[str]) -> list[str]``.

    Với offline, hàm gọi ``send_prompts_global`` (một generate cho cả batch).
    Với API, gọi tuần tự từng prompt (đủ cho phase 2).
    """
    if offline:
        from FAIRGAME.src.llm_connectors.local_vllm_connector import send_prompts_global

        def send(prompts: List[str], seeds=None) -> List[str]:
            return send_prompts_global(prompts, batch_size, seeds=seeds)

        return send

    from FAIRGAME.src.llm_connectors.llm_factory_connector import ChatModelFactory

    model = ChatModelFactory.get_model(model_name)

    def send_api(prompts: List[str], seeds=None) -> List[str]:
        # API connector chưa nhận seed per-request; bỏ qua (phase 2 sẽ bổ sung nếu cần).
        return [model.send_prompt(p) for p in prompts]

    return send_api
