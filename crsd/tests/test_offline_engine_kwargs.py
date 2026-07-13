"""Test logic dựng kwargs engine offline (quantization) — thuần logic, không cần GPU.

Điểm cần chốt:
  1. Config CŨ (không quantize) -> kwargs y hệt trước đây (không lộ knob mới),
     để vLLM đời cũ không vỡ vì kwarg lạ.
  2. Preset model mang block "engine" thì override đè lên offline_settings.
  3. dtype/kvCacheDtype = "auto"/null bị BỎ (vLLM tự chọn — QUAN TRỌNG cho AWQ/GPTQ
     fp16: ép bfloat16 từ settings chung có thể bị vLLM từ chối); giá trị tường minh
     được truyền.
  4. trustRemoteCode được plumb thật (trước đây bị bỏ qua, connector hardcode True).
  5. Backend transformers chỉ nhận temperature/maxTokens/quantization/trust_remote_code.
"""
import json
from pathlib import Path

from crsd.models.factory import (
    merged_engine_settings,
    transformers_init_kwargs,
    vllm_init_kwargs,
)
from crsd.paths import CONFIGS_DIR

BASE_SETTINGS = {
    "backend": "vllm",
    "sampling": {"temperature": 0.7, "maxTokens": 512, "seedBase": 0},
    "engine": {
        "maxModelLen": 4096,
        "gpuMemoryUtilization": 0.90,
        "tensorParallelSize": 1,
        "dtype": "auto",
        "quantization": None,
        "kvCacheDtype": None,
        "maxNumSeqs": None,
        "cpuOffloadGb": 0,
        "trustRemoteCode": True,
    },
}

LEGACY_KEYS = {
    "max_model_len", "temperature", "max_tokens",
    "gpu_memory_utilization", "tensor_parallel_size", "enforce_eager",
    "trust_remote_code",
}


def test_legacy_config_produces_legacy_kwargs():
    """Preset cũ (chỉ modelPath) + settings mặc định -> không knob quantize nào lọt vào."""
    kwargs = vllm_init_kwargs(BASE_SETTINGS, {"modelPath": "Qwen/Qwen2.5-7B-Instruct"})
    assert set(kwargs) == LEGACY_KEYS
    assert kwargs["max_model_len"] == 4096
    assert kwargs["gpu_memory_utilization"] == 0.90
    assert kwargs["tensor_parallel_size"] == 1
    assert kwargs["enforce_eager"] is True
    assert kwargs["trust_remote_code"] is True
    for absent in ("quantization", "dtype", "kv_cache_dtype", "max_num_seqs", "cpu_offload_gb"):
        assert absent not in kwargs


def test_shipped_offline_settings_default_is_legacy():
    """File offline_settings.json trong repo: dtype='auto' -> KHÔNG ép dtype
    (ép bfloat16 mặc định từng làm chết checkpoint AWQ fp16 của user)."""
    settings = json.loads(
        (Path(CONFIGS_DIR) / "offline" / "offline_settings.json").read_text(encoding="utf-8"))
    kwargs = vllm_init_kwargs(settings, {"modelPath": "x"})
    assert set(kwargs) == LEGACY_KEYS
    assert kwargs["trust_remote_code"] is True


def test_preset_engine_block_overrides_settings():
    preset = {
        "modelPath": "x",
        "engine": {"quantization": "awq", "dtype": "auto", "gpuMemoryUtilization": 0.92},
    }
    eng = merged_engine_settings(BASE_SETTINGS, preset)
    assert eng["quantization"] == "awq"
    assert eng["gpuMemoryUtilization"] == 0.92
    assert eng["maxModelLen"] == 4096  # giữ từ settings chung

    kwargs = vllm_init_kwargs(BASE_SETTINGS, preset)
    assert kwargs["quantization"] == "awq"
    assert kwargs["gpu_memory_utilization"] == 0.92
    assert "dtype" not in kwargs  # "auto" -> bỏ, vLLM tự chọn (AWQ -> float16)


def test_explicit_dtype_is_passed_auto_is_dropped():
    settings = json.loads(json.dumps(BASE_SETTINGS))
    settings["engine"].update({"dtype": "bfloat16", "kvCacheDtype": "auto"})
    kwargs = vllm_init_kwargs(settings, {"modelPath": "x"})
    assert kwargs["dtype"] == "bfloat16"   # tường minh -> truyền
    assert "kv_cache_dtype" not in kwargs  # "auto" -> bỏ


def test_trust_remote_code_false_is_plumbed():
    settings = json.loads(json.dumps(BASE_SETTINGS))
    settings["engine"]["trustRemoteCode"] = False
    assert vllm_init_kwargs(settings, {"modelPath": "x"})["trust_remote_code"] is False
    assert transformers_init_kwargs(settings, {"modelPath": "x"})["trust_remote_code"] is False
    # preset override thắng settings
    preset = {"modelPath": "x", "engine": {"trustRemoteCode": False}}
    assert vllm_init_kwargs(BASE_SETTINGS, preset)["trust_remote_code"] is False


def test_explicit_vram_knobs_are_passed():
    preset = {
        "modelPath": "x",
        "engine": {"kvCacheDtype": "fp8", "maxNumSeqs": 64, "cpuOffloadGb": 8},
    }
    kwargs = vllm_init_kwargs(BASE_SETTINGS, preset)
    assert kwargs["kv_cache_dtype"] == "fp8"
    assert kwargs["max_num_seqs"] == 64
    assert kwargs["cpu_offload_gb"] == 8.0


def test_transformers_kwargs_minimal():
    preset = {"modelPath": "x", "engine": {"quantization": "bnb-4bit"}}
    kwargs = transformers_init_kwargs(BASE_SETTINGS, preset)
    assert kwargs == {"temperature": 0.7, "max_tokens": 512,
                      "trust_remote_code": True, "quantization": "bnb-4bit"}
    # không quantize -> không có key quantization
    kwargs2 = transformers_init_kwargs(BASE_SETTINGS, {"modelPath": "x"})
    assert kwargs2 == {"temperature": 0.7, "max_tokens": 512, "trust_remote_code": True}


def test_shipped_72b_presets_are_valid():
    """Các preset 72B trong repo: JSON hợp lệ + block engine đúng schema."""
    names = [
        "models_qwen2.5-72b-awq",
        "models_llama3.1-70b-awq",
        "models_qwen2.5-72b-gptq-int4",
        "models_qwen2.5-72b-bnb4bit",
    ]
    for name in names:
        p = Path(CONFIGS_DIR) / "offline" / f"{name}.json"
        preset = json.loads(p.read_text(encoding="utf-8"))
        assert preset["modelPath"], name
        kwargs = vllm_init_kwargs(BASE_SETTINGS, preset)
        # AWQ/GPTQ quantize sẵn: quantization=null (tự nhận) -> không ép dtype bf16
        if "awq" in name or "gptq" in name:
            assert "quantization" not in kwargs, name
            assert "dtype" not in kwargs, name
        if "bnb4bit" in name:
            assert kwargs["quantization"] == "bitsandbytes", name
        assert kwargs["gpu_memory_utilization"] == 0.92, name
