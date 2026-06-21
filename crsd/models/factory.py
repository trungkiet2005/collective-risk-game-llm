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


def init_offline_backend(offline_settings: dict, model_preset: dict, force: bool = False) -> None:
    """Khởi tạo engine offline dựa trên offline_settings + model preset.

    ``force=True`` để nạp lại model khác trong cùng tiến trình (vd quét nhiều model
    trên một GPU Kaggle: load → run → free → model kế tiếp).
    """
    from FAIRGAME.src.llm_connectors.local_vllm_connector import init_local_llm

    backend = offline_settings.get("backend", "vllm")
    samp = offline_settings.get("sampling", {})
    eng = offline_settings.get("engine", {})
    model_path = model_preset["modelPath"]

    if backend == "vllm":
        init_local_llm(
            model_path,
            engine="vllm",
            force=force,
            max_model_len=int(eng.get("maxModelLen", 4096)),
            temperature=float(samp.get("temperature", 0.7)),
            max_tokens=int(samp.get("maxTokens", 512)),
            gpu_memory_utilization=float(eng.get("gpuMemoryUtilization", 0.90)),
            tensor_parallel_size=int(eng.get("tensorParallelSize", 1)),
            enforce_eager=bool(eng.get("enforceEager", True)),
        )
    elif backend == "transformers":
        init_local_llm(
            model_path,
            engine="transformers",
            force=force,
            temperature=float(samp.get("temperature", 0.7)),
            max_tokens=int(samp.get("maxTokens", 512)),
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
