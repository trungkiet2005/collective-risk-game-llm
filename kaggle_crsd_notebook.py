"""
=====================================================================
CRSD (package `crsd`) — Kaggle OFFLINE notebook (Internet OFF, GPU ON) — MULTI-MODEL
=====================================================================
Chạy các experiment CRSD của project này (Milinski 2008 với LLM agents) trên GPU
Kaggle, offline. Nạp LẦN LƯỢT nhiều model, mỗi model chạy các experiment đã chọn,
lưu kết quả RIÊNG theo từng (model × experiment).

Khác bản FAIRGAME-internal: notebook này tái dùng TRỰC TIẾP runner đã test của
project — `crsd.runner.run_experiment.build_games_for_model`, `run_games_batched`,
`crsd.dataio.recorder` — nên seed/CRN/scratchpad/framing giống hệt lúc chạy local.

CÁCH CHẠY:
  1. Tạo notebook Kaggle mới — GPU: ON, Internet: OFF.
  2. + Add Input:
       a) Code/Dataset: repo này (chứa CẢ `crsd/` lẫn `FAIRGAME/` ở cùng một thư mục gốc).
       b) Model(s): add MỖI model làm một input (Qwen2.5-7B, Gemma-2-9B, Llama-3.1-8B...).
  3. Copy file này vào notebook, chia cell theo "# CELL N".
  4. Sửa MODELS[], KAGGLE_CODE_INPUT, EXPERIMENTS ở Cell 1/3.
       Chạy "!ls /kaggle/input/" để xem path thực của repo + từng model.
  5. Run lần lượt Cell 1 → 8.

Output: /kaggle/working/crsd_results/<model_short>/<experiment>/{turns.jsonl, games.csv}
  + crsd_all_models.csv gộp + run_manifest.json + crsd_results.zip ở Output tab.
=====================================================================
"""

# =====================================================================
# CELL 1: CẤU HÌNH — SỬA Ở ĐÂY
# =====================================================================

# --- Danh sách model. Mỗi model đã add làm Kaggle input. -------------------- #
# path:        thư mục model trong /kaggle/input/...  (xem bằng "!ls /kaggle/input/")
# short_name:  tên thư mục output + cột "model" trong CSV (phải DUY NHẤT).
# engine:      "vllm" (throughput cao) | "transformers" (ổn định, free GPU sạch giữa các model).
# (tuỳ chọn)   temperature / max_tokens / max_model_len: override riêng cho model đó.
MODELS = [
    {
        "path": "/kaggle/input/models/qwen-lm/qwen2.5/transformers/7b-instruct/1",
        "short_name": "qwen25-7b-instruct",
        "engine": "vllm",
    },
    {
        "path": "/kaggle/input/models/google/gemma-2/transformers/gemma-2-9b-it/2",
        "short_name": "gemma2-9b-it",
        "engine": "vllm",
    },
    {
        "path": "/kaggle/input/datasets/foundnotkiet/llama-3-1-8b/model_weights",
        "short_name": "llama-3-1-8b",
        "engine": "vllm",
    },
]

# --- Experiment(s) cần chạy (tên file trong crsd/configs/experiment/, KHÔNG .json) --- #
# Có sẵn (tất cả đã EN+VN):
#   exp_baseline        - replicate Milinski thuần (đối chứng; cũng đo hiệu ứng ngôn ngữ sạch nhất)
#   exp_memory_ablation - full_history vs scratchpad
#   exp_framing         - baseline vs framed
#   exp_persona         - neutral vs selfish vs cooperative (kiểu FairGame)
# Lưu ý runtime (đã khử trùng đối chứng, lấy từ exp_baseline): baseline 60; memory 60; framing 120 (full+scratchpad); persona 420 (gradient 0-6 ích kỷ, 7 điều kiện). Bớt bằng nút trim dưới.
EXPERIMENTS = [
    "exp_baseline",
    # "exp_memory_ablation",
    # "exp_framing",
    # "exp_persona",
]

# --- Tham số sinh MẶC ĐỊNH (model có thể override từng cái trong MODELS[]) --- #
DEFAULT_ENGINE = "vllm"   # "vllm" | "transformers"
MAX_MODEL_LEN = 4096
TEMPERATURE = 0.7         # >0 để 6 agent khác nhau; 0.7–1.0
MAX_TOKENS = 512          # đủ cho reasoning ngắn + dòng "CONTRIBUTION: X"
GPU_UTIL = 0.90           # chỉ dùng cho vllm
TP_SIZE = 1               # tensor parallel (vllm); single GPU = 1
BATCH_SIZE = 256          # prompts/forward; 0 = cả batch một lần. 7B trên GPU lớn: 256 an toàn.
SAMPLING_SEED_BASE = 0    # offset toàn cục cho seed sinh văn bản (seed per-lượt vẫn theo exp.seed+rep+round+agent)

# --- Nút TRIM (giảm tải cho vừa 1 phiên Kaggle ~9–12h) --------------------- #
# Cả 3 experiment đã mặc định chạy EN+VN. Nếu sợ vượt giờ (memory/framing = 120
# game × 3 model), hạ tải bằng 1 trong các cách dưới (KHÔNG cần sửa file config):
LANGUAGES_OVERRIDE = None   # None = theo config (en+vn); vd ["en"] để chỉ chạy 1 ngôn ngữ
REPS_OVERRIDE = None        # None = theo config (10 group/điều kiện); vd 5 để chạy nửa
ENFORCE_EAGER = True        # True = an toàn mọi GPU (chậm hơn); False = bật CUDA graph (nhanh hơn cho 9B)

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
# CELL 2.5: (TUỲ CHỌN) Cài vLLM OFFLINE từ wheels đã build sẵn
# =====================================================================
# Chỉ cần khi muốn engine="vllm" mà image Kaggle CHƯA có vllm. Yêu cầu một Dataset
# chứa toàn bộ .whl (build trong notebook Internet ON CÙNG image GPU), đã + Add Input.
import importlib.util
import subprocess

VLLM_WHEELS_DIR = Path("/kaggle/input/vllm-offline-wheels")  # sửa cho đúng tên dataset
VLLM_VERSION = ""   # "" = bản trong wheels; hoặc ghim "0.6.x"

_want_vllm = (DEFAULT_ENGINE == "vllm") or any(
    m.get("engine", DEFAULT_ENGINE) == "vllm" for m in MODELS)
_have_vllm = importlib.util.find_spec("vllm") is not None

if _want_vllm:
    # Tắt FlashInfer sampler: trên GPU mới (Blackwell sm_120) nó JIT-compile và ngã.
    os.environ["VLLM_USE_FLASHINFER_SAMPLER"] = "0"
    print("VLLM_USE_FLASHINFER_SAMPLER=0 (sampler PyTorch-native).")

if not _want_vllm:
    print("Không model nào dùng vllm — bỏ qua cài đặt.")
elif _have_vllm:
    print("vLLM đã có sẵn trên image — không cần cài.")
elif not VLLM_WHEELS_DIR.is_dir():
    raise FileNotFoundError(
        f"Cần engine vllm nhưng không thấy wheels ở {VLLM_WHEELS_DIR}. "
        "Hãy + Add Input dataset wheels, sửa VLLM_WHEELS_DIR, hoặc đổi engine='transformers'.")
else:
    _spec = "vllm" + (f"=={VLLM_VERSION}" if VLLM_VERSION else "")
    _cmd = [sys.executable, "-m", "pip", "install", "--no-index",
            f"--find-links={VLLM_WHEELS_DIR}", _spec]
    print("Cài vLLM offline:", " ".join(_cmd))
    subprocess.run(_cmd, check=True)
    importlib.invalidate_caches()
    _probe = ("import torch; torch.zeros(1).cuda(); print('GPU_OK', torch.__version__)")
    if subprocess.run([sys.executable, "-c", _probe]).returncode != 0:
        raise RuntimeError(
            "torch vừa cài KHÔNG init được GPU — gần như chắc do wheels build SAI CUDA so với "
            "driver Kaggle. Build lại wheels khớp torch của Kaggle, hoặc tạm đổi engine='transformers'.")
    print("vLLM đã cài từ wheels và torch init GPU OK.")

# =====================================================================
# CELL 3: Setup source (copy repo, đặt marker)
# =====================================================================
import shutil

# Repo đã add làm input (read-only). Sửa cho đúng path (xem "!ls /kaggle/input/").
KAGGLE_CODE_INPUT = Path("/kaggle/input/colective-risk-game")

if WORK_COPY.exists():
    shutil.rmtree(WORK_COPY)
shutil.copytree(KAGGLE_CODE_INPUT, WORK_COPY)

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
    print(f"   - {m['short_name']:<22} exists={Path(m['path']).exists()}  ({m['path']})")
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
    """Dựng offline_settings dict cho factory.init_offline_backend (từ Cell 1)."""
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
            "gpuMemoryUtilization": GPU_UTIL,
            "tensorParallelSize": TP_SIZE,
            "enforceEager": bool(model_cfg.get("enforce_eager", ENFORCE_EAGER)),
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
    print(f"Loading {model_cfg['short_name']} ({osettings['backend']}) <- {model_cfg['path']}")
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
            "batch_size": BATCH_SIZE, "runs": []}


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
