"""
=====================================================================
CRSD (package `crsd`) — Kaggle OFFLINE notebook (Internet OFF, GPU ON) — exp_baseline | MODEL 70B+ QUANTIZE 4-BIT
=====================================================================
GIỐNG HỆT `kaggle_exp_baseline_large.py` nhưng cấu hình cho model 70B+ chạy bằng
checkpoint QUANTIZE SẴN 4-bit (AWQ/GPTQ) — bf16 72B ≈ 145 GB KHÔNG vừa 96 GB VRAM:
  - Qwen2.5-72B-Instruct-AWQ                    (~41 GB trọng số int4)
  - Meta-Llama-3.1-70B-Instruct-AWQ-INT4        (~40 GB trọng số int4)

Khác bản large ở: Cell 1 (MODELS + knob quantize), Cell 2.5 (dò wheels theo package
cần cài, thêm bitsandbytes nếu cần), Cell 4 (`offline_settings_for` truyền knob
quantize + gpu_util per-model), Cell 5 (log `quant=`), Cell 6 (manifest ghi map
quantization). Cell 2/3/7/8 và toàn bộ runner giữ nguyên (`run_experiment`,
`run_games_batched`) — seed/CRN y hệt các bản trước. Đồng bộ fix từ bản large
thì nhớ giữ lại các khác biệt trên.

⚠️  VRAM 96 GB — SỐ HỌC (đọc kỹ TRƯỚC khi chạy) ─────────────────────
  Trọng số AWQ int4 72B ≈ 41 GB. gpu_memory_utilization 0.92 × 96 ≈ 88 GB
  => còn ~45 GB cho KV-cache: với KV/token ≈ 0.31 MB (GQA 8 head, fp16, 80 layer)
     là ~145k token ≈ 35 sequence 4096-token chạy đồng thời — dư cho batch 256
     (vLLM tự xếp hàng phần dư, không OOM).
  => quantization ĐỂ None: vLLM tự đọc quantization_config trong checkpoint và
     chọn kernel tốt nhất (awq_marlin/gptq_marlin). CHỈ ép ("awq"/"gptq") nếu
     kernel auto lỗi trên GPU lạ. dtype "auto" (AWQ/GPTQ -> float16).
  => Vẫn thiếu VRAM (OOM lúc nạp)? Theo thứ tự: hạ MAX_MODEL_LEN 4096->2048,
     đặt KV_CACHE_DTYPE="fp8", đặt MAX_NUM_SEQS=32, cuối cùng CPU_OFFLOAD_GB=8.
  => RTX PRO 6000 là Blackwell sm_120: GIỮ VLLM_USE_FLASHINFER_SAMPLER=0 (Cell 2.5
     đã set) và wheels vLLM/torch phải là bản mới có kernel sm_120 (cu128).

CÁCH CHẠY:
  1. Chạy `kaggle_build_quant_wheels.py` (Internet ON) -> Output -> New Dataset
     (vd "crsd-quant-wheels").
  2. Chạy `FAIRGAME/download_model.py` (Internet ON) với
     MODEL_ID = "Qwen/Qwen2.5-72B-Instruct-AWQ" -> Output -> New Dataset
     (vd "qwen25-72b-instruct-awq"). Lặp lại cho model AWQ khác nếu cần.
     (Hoặc + Add Model từ Kaggle Models hub nếu có sẵn biến thể AWQ.)
  3. Tạo notebook mới — Accelerator: GPU 96 GB, Internet: OFF. + Add Input:
       a) repo này (chứa CẢ `crsd/` lẫn `FAIRGAME/`),
       b) dataset wheels (bước 1),
       c) dataset model AWQ (bước 2).
  4. Copy file này vào notebook, chia cell theo "# CELL N".
  5. Sửa MODELS[] ở Cell 1 theo path thực (`!ls /kaggle/input/`). Run Cell 1 → 8.

Output: /kaggle/working/crsd_results/<model_short>/<experiment>/{turns.jsonl, games.csv}
  + crsd_all_models.csv gộp + run_manifest.json + crsd_results.zip ở Output tab.
=====================================================================
"""

# =====================================================================
# CELL 1: CẤU HÌNH — SỬA Ở ĐÂY
# =====================================================================

# --- Danh sách model. Mỗi model đã add làm Kaggle input. -------------------- #
# path:          thư mục model trong /kaggle/input/... (xem bằng "!ls /kaggle/input/")
# short_name:    tên thư mục output + cột "model" trong CSV (phải DUY NHẤT).
# engine:        "vllm" (khuyên dùng cho AWQ/GPTQ) | "transformers" (chỉ bnb-4bit/8bit).
# quantization:  None = vLLM TỰ nhận từ checkpoint (đúng cho AWQ/GPTQ quantize sẵn).
#                Ép "awq"/"gptq" nếu kernel auto lỗi; "bitsandbytes" cho checkpoint
#                bnb-4bit; "fp8" quantize on-the-fly checkpoint bf16 (~72GB, chật).
# (tuỳ chọn)     dtype / kv_cache_dtype / max_num_seqs / cpu_offload_gb / gpu_util
#                / temperature / max_tokens / max_model_len: override riêng model đó.
MODELS = [
    {
        "path": "/kaggle/input/qwen25-72b-instruct-awq/model_weights",
        "short_name": "qwen25-72b-instruct-awq",
        "engine": "vllm",
        "quantization": None,     # AWQ quantize sẵn -> vLLM tự nhận
        "dtype": "auto",          # auto -> float16 (chuẩn cho AWQ)
    },
    {
        "path": "/kaggle/input/llama31-70b-instruct-awq/model_weights",
        "short_name": "llama-3-1-70b-instruct-awq",
        "engine": "vllm",
        "quantization": None,
        "dtype": "auto",
    },
]

# --- Experiment(s) cần chạy (tên file trong crsd/configs/experiment/, KHÔNG .json) --- #
EXPERIMENTS = ["exp_baseline"]   # notebook chuyên cho baseline 70B+ (EN + VN)

# --- Tham số sinh MẶC ĐỊNH (model có thể override từng cái trong MODELS[]) --- #
DEFAULT_ENGINE = "vllm"   # "vllm" | "transformers"
MAX_MODEL_LEN = 4096
TEMPERATURE = 0.7         # >0 để 6 agent khác nhau; 0.7–1.0
MAX_TOKENS = 512          # đủ cho reasoning ngắn + dòng "CONTRIBUTION: X"
GPU_UTIL = 0.92           # 0.92×96GB ≈ 88GB: trọng số int4 ~41GB + ~45GB KV-cache
TP_SIZE = 1               # 1 card 96GB -> 1. Chỉ >1 khi accelerator NHIỀU GPU.
BATCH_SIZE = 256          # vLLM tự lên lịch nội bộ -> an toàn kể cả 72B (dư xếp hàng)
SAMPLING_SEED_BASE = 0    # offset toàn cục cho seed sinh văn bản

# --- Knob quantize MẶC ĐỊNH (override per-model trong MODELS[]) ------------- #
QUANTIZATION = None       # None = tự nhận từ checkpoint (AWQ/GPTQ cứ để None)
DTYPE = "auto"            # "auto" | "float16" | "bfloat16" (AWQ/GPTQ: để "auto")
KV_CACHE_DTYPE = None     # None/"auto" | "fp8" (nén KV-cache khi VRAM sát nút)
MAX_NUM_SEQS = None       # None = mặc định vLLM; vd 32 để ghìm VRAM lúc chạy
CPU_OFFLOAD_GB = 0        # >0 = đẩy bớt trọng số sang RAM (chậm — van xả cuối)

# --- Nút TRIM (giảm tải cho vừa 1 phiên Kaggle ~9–12h) --------------------- #
# 72B chậm hơn 32B ~2–2.5×; nếu ETA thô (smoke test) báo quá dài, hạ tải ở đây:
LANGUAGES_OVERRIDE = None   # None = theo config (en+vn); vd ["en"] chỉ chạy 1 ngôn ngữ
REPS_OVERRIDE = None        # None = theo config (10 group/điều kiện); vd 5 chạy nửa
ENFORCE_EAGER = True        # True = an toàn + tiết kiệm VRAM (không CUDA graph)

from pathlib import Path  # noqa: E402

OUTPUT_DIR = Path("/kaggle/working/crsd_results")
SMOKE_TEST = True         # in 1 reply mẫu + parse khi nạp mỗi model
FAIRGAME_VERBOSE_LOGS = "0"

# =====================================================================
# CELL 2: Helpers path (Internet OFF — không pip trừ cell 2.5)
# =====================================================================
import os
import sys

os.environ["FAIRGAME_VERBOSE_LOGS"] = FAIRGAME_VERBOSE_LOGS

WORK_COPY = Path("/kaggle/working/crsd_repo")
MARKER_ROOT = Path("/kaggle/working/.crsd_project_root")


def resolve_repo_root(base: Path) -> Path:
    """Tìm thư mục gốc chứa ĐỒNG THỜI `crsd/` và `FAIRGAME/` (import được cả hai)."""
    cands = [base, base / "Colective_Risk_Game", base / "Collective_Risk_Game"]
    if base.is_dir():
        cands += [c for c in sorted(base.iterdir()) if c.is_dir()]
    for c in cands:
        if (c / "crsd").is_dir() and (c / "FAIRGAME").is_dir():
            return c.resolve()
    hint = [p.name for p in base.iterdir()] if base.is_dir() else []
    raise FileNotFoundError(f"Không thấy thư mục có cả crsd/ + FAIRGAME/ dưới {base}. Mục con: {hint}")


def ensure_importable():
    """chdir + sys.path tới repo root (đọc marker do Cell 3 ghi)."""
    if not MARKER_ROOT.exists():
        raise RuntimeError("Chưa có marker — chạy Cell 3 trước.")
    root = Path(MARKER_ROOT.read_text(encoding="utf-8").strip())
    os.chdir(root)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


print("Internet OFF: dùng thư viện có sẵn trên image Kaggle (trừ cell 2.5 nếu cần vLLM).")

# =====================================================================
# CELL 2.5: Cài vLLM (+bitsandbytes nếu cần) OFFLINE từ wheels dataset
# =====================================================================
# Yêu cầu dataset wheels từ `kaggle_build_quant_wheels.py` (Internet ON) đã + Add Input.
import importlib.util
import subprocess


# TỰ DÒ thư mục wheels dưới /kaggle/input/ theo ĐÚNG các package cần cài (không
# chỉ vllm*.whl — nếu chỉ thiếu bitsandbytes thì dò bitsandbytes*.whl). Thư mục
# hợp lệ = chứa wheel cho TẤT CẢ package cần. Dò trượt thì set VLLM_WHEELS_DIR
# thủ công tới thư mục chứa .whl.
def find_wheels_dir(patterns, root="/kaggle/input", max_depth=6):
    root = Path(root)
    if not root.is_dir() or not patterns:
        return None
    stack = [(root, 0)]
    while stack:
        d, depth = stack.pop()
        try:
            if all(any(d.glob(pat)) for pat in patterns):
                return d
        except OSError:
            pass
        if depth < max_depth:
            try:
                for c in sorted(d.iterdir()):
                    if c.is_dir() and not c.name.startswith("."):
                        stack.append((c, depth + 1))
            except OSError:
                pass
    return None


VLLM_VERSION = ""   # "" = bản trong wheels; hoặc ghim "0.11.0"

_want_vllm = (DEFAULT_ENGINE == "vllm") or any(
    m.get("engine", DEFAULT_ENGINE) == "vllm" for m in MODELS)


def _model_quant(m):
    return str(m.get("quantization", QUANTIZATION) or "").lower()


# bitsandbytes cần khi: quantization "bitsandbytes" (vllm) hoặc "bnb-*" (transformers)
_want_bnb = any(("bnb" in _model_quant(m)) or ("bitsandbytes" in _model_quant(m))
                for m in MODELS)
_have_vllm = importlib.util.find_spec("vllm") is not None
_have_bnb = importlib.util.find_spec("bitsandbytes") is not None

if _want_vllm:
    # Tắt FlashInfer sampler: trên GPU mới (Blackwell sm_120) nó JIT-compile và ngã.
    os.environ["VLLM_USE_FLASHINFER_SAMPLER"] = "0"
    print("VLLM_USE_FLASHINFER_SAMPLER=0 (sampler PyTorch-native).")

_to_install = []
if _want_vllm and not _have_vllm:
    _to_install.append("vllm" + (f"=={VLLM_VERSION}" if VLLM_VERSION else ""))
if _want_bnb and not _have_bnb:
    _to_install.append("bitsandbytes")

# Pattern dò = wheel của từng package cần cài (bỏ phần ==version; '-' trong tên
# package thành '_' trong tên wheel — vllm/bitsandbytes không có '-', replace vô hại).
_pkg_patterns = [p.split("==")[0].replace("-", "_") + "*.whl" for p in _to_install]
VLLM_WHEELS_DIR = (find_wheels_dir(_pkg_patterns)
                   or Path("/kaggle/input/crsd-quant-wheels/quant_wheels"))

if not _to_install:
    print("Đủ thư viện sẵn trên image (vllm"
          + (", bitsandbytes" if _want_bnb else "") + ") — không cần cài.")
elif not VLLM_WHEELS_DIR.is_dir():
    raise FileNotFoundError(
        f"Cần cài {_to_install} nhưng không thấy thư mục wheels chứa đủ "
        f"{_pkg_patterns} (fallback: {VLLM_WHEELS_DIR}). Hãy + Add Input dataset "
        "wheels (từ kaggle_build_quant_wheels.py) hoặc sửa VLLM_WHEELS_DIR.")
else:
    _cmd = [sys.executable, "-m", "pip", "install", "--no-index",
            f"--find-links={VLLM_WHEELS_DIR}"] + _to_install
    print(f"Cài offline {_to_install} từ {VLLM_WHEELS_DIR} ... (ẩn log pip, chỉ hiện khi lỗi)")
    _r = subprocess.run(_cmd, capture_output=True, text=True)
    if _r.returncode != 0:
        print(_r.stdout[-3000:])
        print(_r.stderr[-3000:])
        raise RuntimeError("pip install offline thất bại — xem log phía trên.")
    importlib.invalidate_caches()
    _probe = ("import torch; torch.zeros(1).cuda(); print('GPU_OK', torch.__version__)")
    _rp = subprocess.run([sys.executable, "-c", _probe], capture_output=True, text=True)
    if _rp.returncode != 0:
        print(_rp.stdout)
        print(_rp.stderr)
        raise RuntimeError(
            "torch vừa cài KHÔNG init được GPU — gần như chắc do wheels build SAI CUDA so với "
            "driver Kaggle. Build lại wheels (kaggle_build_quant_wheels.py) trên CÙNG image GPU.")
    print(_rp.stdout.strip())
    print(f"Đã cài {_to_install} từ wheels và torch init GPU OK.")

# =====================================================================
# CELL 3: Setup source (copy repo, đặt marker)
# =====================================================================
import shutil


# Repo đã add làm input (read-only). TỰ DÒ thư mục chứa crsd/ + FAIRGAME/ dưới
# /kaggle/input/. Auto-detect trượt thì sửa KAGGLE_CODE_INPUT thủ công cho đúng path.
def find_repo_input(root="/kaggle/input", max_depth=6):
    root = Path(root)
    if not root.is_dir():
        return None
    stack = [(root, 0)]
    while stack:
        d, depth = stack.pop()
        try:
            if (d / "crsd").is_dir() and (d / "FAIRGAME").is_dir():
                return d
        except OSError:
            pass
        if depth < max_depth:
            try:
                for c in sorted(d.iterdir()):
                    if c.is_dir() and not c.name.startswith("."):
                        stack.append((c, depth + 1))
            except OSError:
                pass
    return None


KAGGLE_CODE_INPUT = find_repo_input("/kaggle/input") or Path("/kaggle/input/colective-risk-game")
print(f"Repo input: {KAGGLE_CODE_INPUT}  (exists={Path(KAGGLE_CODE_INPUT).exists()})")

if WORK_COPY.exists():
    shutil.rmtree(WORK_COPY)
shutil.copytree(KAGGLE_CODE_INPUT, WORK_COPY, ignore=shutil.ignore_patterns(".git"))

REPO_ROOT = resolve_repo_root(WORK_COPY)
os.chdir(REPO_ROOT)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
MARKER_ROOT.write_text(str(REPO_ROOT), encoding="utf-8")

# Kiểm tra các file then chốt có mặt chưa
_need = [REPO_ROOT / "crsd" / "runner" / "run_experiment.py",
         REPO_ROOT / "crsd" / "prompts" / "crsd_en.txt",
         REPO_ROOT / "crsd" / "prompts" / "crsd_scratchpad_en.txt",
         REPO_ROOT / "crsd" / "configs" / "experiment",
         REPO_ROOT / "FAIRGAME" / "src" / "llm_connectors" / "local_vllm_connector.py"]
_missing = [str(p) for p in _need if not p.exists()]
print(f"Repo root: {REPO_ROOT}")
print("Models khai báo:")
for m in MODELS:
    print(f"   - {m['short_name']:<28} exists={Path(m['path']).exists()}  ({m['path']})")
if _missing:
    print("THIẾU file (push & re-add input):")
    for m in _missing:
        print("   -", m)
else:
    print("OK — crsd/ + FAIRGAME/ + configs/prompts đầy đủ.")

# =====================================================================
# CELL 4: Import runner + đếm kế hoạch
# =====================================================================
ensure_importable()

from crsd.dataio.config_loader import load_json                      # noqa: E402
from crsd.dataio.recorder import write_turns_jsonl, write_games_csv  # noqa: E402
from crsd.runner.run_experiment import build_games_for_model         # noqa: E402
from crsd.runner.batch import run_games_batched                      # noqa: E402
from crsd.engine.round import parse_contribution                     # noqa: E402
from crsd.models import factory                                      # noqa: E402
from crsd.paths import CONFIGS_DIR                                    # noqa: E402
import FAIRGAME.src.llm_connectors.local_vllm_connector as conn      # noqa: E402
import json                                                          # noqa: E402


def load_experiment(name):
    exp = load_json(CONFIGS_DIR / "experiment" / f"{name}.json")
    if LANGUAGES_OVERRIDE:               # nút trim: ép số ngôn ngữ
        exp["languages"] = list(LANGUAGES_OVERRIDE)
    if REPS_OVERRIDE:                    # nút trim: ép số rep (group/điều kiện)
        exp["repetitions"] = int(REPS_OVERRIDE)
    return exp


def agents_cfg_for(exp):
    name = exp.get("agents") or (exp.get("agentsConditions") or ["personas_default"])[0]
    return name, load_json(CONFIGS_DIR / "agents" / f"{name}.json")


def _n_conditions(exp):
    return len(exp.get("agentsConditions") or [exp.get("agents", "personas_default")])


_plan = []
for _en in EXPERIMENTS:
    _exp = load_experiment(_en)
    _n = (len(_exp["games"]) * _n_conditions(_exp)
          * len(_exp.get("languages", ["en"])) * int(_exp.get("repetitions", 1)))
    _plan.append((_en, _n))
    print(f"Experiment {_en}: {_n} games/model ({_n * 6 * 10} generations).")
print(f"Tổng {len(MODELS)} model × {sum(n for _, n in _plan)} games = "
      f"{len(MODELS) * sum(n for _, n in _plan)} games.")


def offline_settings_for(model_cfg):
    """Dựng offline_settings dict cho factory.init_offline_backend (từ Cell 1).

    Knob quantize đi qua block "engine" — factory chỉ truyền knob nào đặt tường
    minh (khác None/"auto"/0) nên checkpoint thường chạy y hệt notebook cũ.
    """
    engine = model_cfg.get("engine", DEFAULT_ENGINE)
    return {
        "backend": engine,
        "sampling": {
            "temperature": float(model_cfg.get("temperature", TEMPERATURE)),
            "maxTokens": int(model_cfg.get("max_tokens", MAX_TOKENS)),
            "seedBase": SAMPLING_SEED_BASE,
        },
        "engine": {
            "maxModelLen": int(model_cfg.get("max_model_len", MAX_MODEL_LEN)),
            "gpuMemoryUtilization": float(model_cfg.get("gpu_util", GPU_UTIL)),
            "tensorParallelSize": int(model_cfg.get("tensor_parallel_size", TP_SIZE)),
            "enforceEager": bool(model_cfg.get("enforce_eager", ENFORCE_EAGER)),
            "quantization": model_cfg.get("quantization", QUANTIZATION),
            "dtype": model_cfg.get("dtype", DTYPE),
            "kvCacheDtype": model_cfg.get("kv_cache_dtype", KV_CACHE_DTYPE),
            "maxNumSeqs": model_cfg.get("max_num_seqs", MAX_NUM_SEQS),
            "cpuOffloadGb": model_cfg.get("cpu_offload_gb", CPU_OFFLOAD_GB),
        },
    }


# Tổng generations dự kiến / model (cho ETA thô ở smoke test). 1 game = 6×10 gen.
GEN_PER_MODEL = sum(n for _, n in _plan) * 6 * 10

# =====================================================================
# CELL 5: Helpers — load model, smoke test, chạy 1 experiment, lưu
# =====================================================================
def load_model(model_cfg):
    """Nạp model vào GPU (force=True để thay model trong cùng tiến trình)."""
    osettings = offline_settings_for(model_cfg)
    print(f"Loading {model_cfg['short_name']} ({osettings['backend']}, "
          f"quant={osettings['engine']['quantization'] or 'auto-detect'}, "
          f"TP={osettings['engine']['tensorParallelSize']}) <- {model_cfg['path']}")
    factory.init_offline_backend(osettings, {"modelPath": model_cfg["path"]}, force=True)
    print(f"{model_cfg['short_name']} loaded.")


def smoke_test(model_cfg, exp, agents_cfg, agents_name):
    import time
    send_batch = factory.get_send_batch(model_cfg["short_name"], offline=True, batch_size=0)
    games = build_games_for_model(exp, model_cfg["short_name"], agents_cfg, agents_name,
                                  sampling_seed_base=SAMPLING_SEED_BASE)
    g = games[0]
    prompt = g.build_round_prompts()[:1]
    seeds = g.build_round_sampling_seeds()[:1]
    t0 = time.time()
    resp = send_batch(prompt, seeds)
    dt = time.time() - t0
    val, failed = parse_contribution(resp[0], g.config.contribution_options)
    print(f"[{model_cfg['short_name']}] sample reply (last 400 chars):\n", resp[0][-400:])
    print(f"Parsed CONTRIBUTION = {val}  (parse_failed={failed})")
    print(f"ETA THÔ: 1 gen ~{dt:.1f}s -> ~{dt * GEN_PER_MODEL / 3600:.1f} h/model cho "
          f"{GEN_PER_MODEL} gen (CẬN TRÊN — chưa tính batching {BATCH_SIZE}, thực tế nhanh hơn nhiều). "
          f"Nếu quá lâu: hạ REPS_OVERRIDE / LANGUAGES_OVERRIDE ở Cell 1, hoặc tách model.")


def run_experiment_for_model(model_cfg, exp_name):
    """Chạy MỘT experiment cho MỘT model (model đã nạp sẵn). Lưu turns + games.csv."""
    short = model_cfg["short_name"]
    exp = load_experiment(exp_name)
    agents_name, agents_cfg = agents_cfg_for(exp)

    send_batch = factory.get_send_batch(short, offline=True, batch_size=BATCH_SIZE)
    games = build_games_for_model(exp, short, agents_cfg, agents_name,
                                  sampling_seed_base=SAMPLING_SEED_BASE,
                                  sampling_seeds_applied=True)

    print(f"[{short}/{exp_name}] chạy {len(games)} games...")
    results = run_games_batched(games, send_batch, verbose=True)

    out_dir = OUTPUT_DIR / short / exp_name
    all_turns = [t for g in games for t in g.turns]
    write_turns_jsonl(all_turns, out_dir / "turns.jsonl")
    write_games_csv(results, out_dir / "games.csv")
    reached = sum(int(r.target_reached) for r in results)
    print(f"[{short}/{exp_name}] xong: {reached}/{len(results)} game đạt target -> {out_dir}")
    return {"model": short, "experiment": exp_name, "n_games": len(results),
            "reached": reached, "output_dir": str(out_dir)}


def run_one_model(model_cfg):
    """Nạp -> smoke test -> chạy mọi experiment. KHÔNG free ở đây (Cell 6 free
    trong finally để chắc chắn giải phóng kể cả khi lỗi giữa chừng)."""
    short = model_cfg["short_name"]
    if not Path(model_cfg["path"]).exists():
        print(f"BỎ QUA {short}: path không tồn tại ({model_cfg['path']}).")
        return []
    load_model(model_cfg)
    if SMOKE_TEST:
        _exp0 = load_experiment(EXPERIMENTS[0])
        _an, _ac = agents_cfg_for(_exp0)
        smoke_test(model_cfg, _exp0, _ac, _an)
    summaries = []
    for exp_name in EXPERIMENTS:
        summaries.append(run_experiment_for_model(model_cfg, exp_name))
    return summaries

# =====================================================================
# CELL 6: Chạy LẦN LƯỢT tất cả model
# =====================================================================
import traceback  # noqa: E402

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
manifest = {"sampling_seed_base": SAMPLING_SEED_BASE, "experiments": EXPERIMENTS,
            "batch_size": BATCH_SIZE,
            "quantization": {m["short_name"]: (m.get("quantization", QUANTIZATION) or "auto-detect")
                             for m in MODELS},
            "runs": []}


def _write_manifest():
    (OUTPUT_DIR / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


# Mỗi model bọc try/except/finally: 1 model lỗi (vd OOM) KHÔNG làm hỏng cả run —
# vẫn free GPU, ghi manifest, và chạy tiếp model sau. Dữ liệu model đã xong đã được
# ghi đĩa (turns.jsonl/games.csv) bên trong run_experiment_for_model.
for _cfg in MODELS:
    _short = _cfg["short_name"]
    try:
        _summaries = run_one_model(_cfg)
        if _summaries:
            manifest["runs"].extend(_summaries)
        else:
            manifest["runs"].append({"model": _short, "status": "skipped"})
    except Exception as _e:  # noqa: BLE001
        traceback.print_exc()
        manifest["runs"].append({"model": _short, "status": "failed",
                                 "error": f"{type(_e).__name__}: {_e}"})
        print(f"⚠️  {_short} LỖI — bỏ qua, chạy tiếp model sau.")
    finally:
        try:
            conn.free_local_llm()
        except Exception:  # noqa: BLE001
            pass
        _write_manifest()   # cập nhật manifest sau MỖI model (sống sót cả khi crash muộn)

_done = sum(1 for r in manifest["runs"] if r.get("n_games"))
print(f"\nHoàn tất {_done} lượt (model × experiment). Chi tiết: run_manifest.json")

# =====================================================================
# CELL 7: Gộp mọi games.csv (so sánh chéo model × experiment)
# =====================================================================
import pandas as pd  # noqa: E402

_frames = []
for csv_path in OUTPUT_DIR.rglob("games.csv"):
    rel = csv_path.relative_to(OUTPUT_DIR)            # <model>/<experiment>/games.csv
    df = pd.read_csv(csv_path)
    df.insert(0, "experiment", rel.parts[1] if len(rel.parts) >= 2 else "")
    _frames.append(df)

if _frames:
    combined = pd.concat(_frames, ignore_index=True)
    combined.to_csv(OUTPUT_DIR / "crsd_all_models.csv", index=False)
    print(f"Gộp {len(_frames)} file -> {OUTPUT_DIR / 'crsd_all_models.csv'} ({len(combined)} games).")
    # Success-rate TÁCH theo từng nhánh. PHẢI tách language/memory_mode/framing, nếu
    # không bảng sẽ TRUNG BÌNH NHẦM 2 nhánh ablation (full_history+scratchpad, baseline+framed).
    idx = [c for c in ["model", "experiment", "persona_set", "language", "memory_mode", "framing"]
           if c in combined.columns]
    try:
        piv = combined.pivot_table(index=idx, columns="risk_probability",
                                   values="target_reached", aggfunc="mean")
        print("\n=== Reach-rate theo " + " × ".join(idx) + " × risk ===")
        print(piv.to_string(float_format=lambda x: f"{x:.2f}"))
        print("HUMAN (Milinski 2008) reach-rate:  p0.1=0.00   p0.5=0.10   p0.9=0.50")
    except Exception as e:  # noqa: BLE001
        print("(bỏ qua pivot:", e, ")")
else:
    print("Không có games.csv nào — kiểm tra path trong MODELS[] / EXPERIMENTS.")

# =====================================================================
# CELL 8: Zip để download
# =====================================================================
import zipfile  # noqa: E402

zip_path = Path("/kaggle/working/crsd_results.zip")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for fp in OUTPUT_DIR.rglob("*"):
        if fp.is_file():
            z.write(fp, fp.relative_to(OUTPUT_DIR.parent))
print(f"{zip_path} ({zip_path.stat().st_size / 1024 / 1024:.2f} MB) — tải ở Output tab.")
