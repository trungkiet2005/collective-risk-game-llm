"""
=====================================================================
CRSD (package `crsd`) — Kaggle OFFLINE notebook — exp_comprehension | MODEL LỚN (32B/27B)
=====================================================================
BIẾN THỂ MODEL LỚN của kaggle_exp_comprehension.py: chạy CÙNG bài đọc-hiểu (Exp 6)
nhưng trên qwen2.5-32B-instruct + gemma-2-27b-it (thay cho 3 model nhỏ 7/9/8B), để
trả lời: scaling lên 27/32B có sửa được lỗi CỘNG DỒN cumulative state (axis State,
"read≠add") hay không. Config Exp 6 giữ NGUYÊN — chỉ đổi MODELS[] + GPU_UTIL.

Chạy bài kiểm tra ĐỌC-HIỂU (prompt comprehension, phỏng theo "Nicer Than Humans")
trên GPU Kaggle, offline. Probe IN-SITU trong các ván BASELINE thật: mỗi vòng bắn
THÊM các câu hỏi Rules/Time/State (gửi RIÊNG -> KHÔNG đụng quyết định) và chấm so
ground truth của engine. Hai nhánh A/B showCumulative (pool ẩn vs hiện) đã nằm sẵn
trong exp_comprehension.json (3 game baseline + 3 game *_showcum).

Tái dùng TRỰC TIẾP runner đã test: `run_comprehension.make_probe_builder`,
`build_games_for_model`, `run_games_batched(..., probe_builder=...)`,
`recorder.write_comprehension_*` -> seed/CRN giống hệt local.

CÁCH CHẠY: như kaggle_exp_baseline_large.py — GPU RTX PRO 6000 (96GB, 1 card), Internet OFF;
  + Add Input: (a) repo (crsd/ + FAIRGAME/), (b) Qwen2.5-32B-Instruct, (c) Gemma-2-27B-it.
  Kiểm path thực bằng "!ls /kaggle/input/". Model lớn nạp CHẬM hơn (~2-3h/model ở chế độ B);
  nếu sợ vượt giờ, hạ REPS_OVERRIDE (vd 5) hoặc LANGUAGES_OVERRIDE=["en"] ở Cell 1.
Output: /kaggle/working/crsd_results/<model_short>/exp_comprehension/
        {turns.jsonl, games.csv, comprehension.jsonl, comprehension_summary.csv}
  + crsd_comprehension_all_models.csv gộp + run_manifest.json + crsd_results.zip.
=====================================================================
"""

# =====================================================================
# CELL 1: CẤU HÌNH — SỬA Ở ĐÂY
# =====================================================================
MODELS = [
    {
        "path": "/kaggle/input/models/qwen-lm/qwen2.5/transformers/32b-instruct/1",
        "short_name": "qwen25-32b-instruct",
        "engine": "vllm",
    },
    {
        "path": "/kaggle/input/models/google/gemma-2/transformers/gemma-2-27b-it/2",
        "short_name": "gemma2-27b-it",
        "engine": "vllm",
    },
]

# Experiment đọc-hiểu (in-situ, 2 nhánh A/B showCumulative, EN+VN).
EXPERIMENTS = ["exp_comprehension"]

# --- Tham số sinh MẶC ĐỊNH --- #
DEFAULT_ENGINE = "vllm"
MAX_MODEL_LEN = 4096
# HAI CHẾ ĐỘ (chọn 1 cặp TEMPERATURE × REPS_OVERRIDE cho NHẤT QUÁN):
#   A) GREEDY benchmark (NHANH ~50p/3 model): TEMPERATURE=0.0 + REPS_OVERRIDE=1.
#      Greedy bỏ qua seed -> mọi rep cho lịch sử & câu trả lời Y HỆT, nên reps>1 chỉ
#      tính LẶP vô ích. 1 rep = đủ bộ dữ liệu tất định.
#   B) STOCHASTIC FULL (ĐANG CHỌN, ~6-8h/3 model, khớp regime run-2, CI chặt nhất):
#      TEMPERATURE=0.7 + REPS_OVERRIDE=None (10 rep) -> 120 quỹ đạo/model, ~62k gen/model.
TEMPERATURE = 0.7         # chế độ B: stochastic, 6 agent ra quyết định khác nhau (giống run-2)
MAX_TOKENS = 512          # ÁP CHO CẢ decision lẫn probe. 512 = an toàn khỏi cắt cụt dòng
                          # CONTRIBUTION:/ANSWER: (model phát EOS sớm nên không tốn thêm giờ).
GPU_UTIL = 0.92           # model lớn (32B/27B) cần để trọng số vừa; nâng 0.95 nếu vẫn thiếu chỗ.
TP_SIZE = 1               # RTX PRO 6000 = 1 GPU 96GB -> 1. Chỉ >1 nếu accelerator NHIỀU GPU.
BATCH_SIZE = 256          # probe thêm nhiều prompt/vòng -> batch giúp throughput
SAMPLING_SEED_BASE = 0

# --- Nút TRIM --- #
LANGUAGES_OVERRIDE = None   # vd ["en"] để chỉ chạy 1 ngôn ngữ
REPS_OVERRIDE = None        # chế độ B FULL: None = 10 rep theo config (~6-8h). Muốn nửa: 5 (~3-4h).
ENFORCE_EAGER = True

from pathlib import Path  # noqa: E402

OUTPUT_DIR = Path("/kaggle/working/crsd_results")
SMOKE_TEST = True
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
import importlib.util
import subprocess


def find_wheels_dir(root="/kaggle/input", max_depth=6):
    root = Path(root)
    if not root.is_dir():
        return None
    stack = [(root, 0)]
    while stack:
        d, depth = stack.pop()
        try:
            if any(d.glob("vllm*.whl")):
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


VLLM_WHEELS_DIR = find_wheels_dir("/kaggle/input") or Path("/kaggle/input/vllm-offline-wheels")
VLLM_VERSION = ""

_want_vllm = (DEFAULT_ENGINE == "vllm") or any(
    m.get("engine", DEFAULT_ENGINE) == "vllm" for m in MODELS)
_have_vllm = importlib.util.find_spec("vllm") is not None

if _want_vllm:
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
    print(f"Cài vLLM offline từ {VLLM_WHEELS_DIR} ... (ẩn log pip, chỉ hiện khi lỗi)")
    _r = subprocess.run(_cmd, capture_output=True, text=True)
    if _r.returncode != 0:
        print(_r.stdout[-3000:])
        print(_r.stderr[-3000:])
        raise RuntimeError("pip install vllm offline thất bại — xem log phía trên.")
    importlib.invalidate_caches()
    _probe = ("import torch; torch.zeros(1).cuda(); print('GPU_OK', torch.__version__)")
    _rp = subprocess.run([sys.executable, "-c", _probe], capture_output=True, text=True)
    if _rp.returncode != 0:
        print(_rp.stdout)
        print(_rp.stderr)
        raise RuntimeError(
            "torch vừa cài KHÔNG init được GPU — gần như chắc do wheels build SAI CUDA so với "
            "driver Kaggle. Build lại wheels khớp torch của Kaggle, hoặc tạm đổi engine='transformers'.")
    print(_rp.stdout.strip())
    print("vLLM đã cài từ wheels và torch init GPU OK.")

# =====================================================================
# CELL 3: Setup source (copy repo, đặt marker)
# =====================================================================
import shutil


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

_need = [REPO_ROOT / "crsd" / "runner" / "run_comprehension.py",
         REPO_ROOT / "crsd" / "prompts" / "crsd_comprehension_en.txt",
         REPO_ROOT / "crsd" / "prompts" / "crsd_comprehension_vn.txt",
         REPO_ROOT / "crsd" / "configs" / "experiment" / "exp_comprehension.json",
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
    print("OK — crsd/ + FAIRGAME/ + template/config đọc-hiểu đầy đủ.")

# =====================================================================
# CELL 4: Import runner + đếm kế hoạch
# =====================================================================
ensure_importable()

from crsd.dataio.config_loader import load_json                      # noqa: E402
from crsd.dataio.recorder import (                                   # noqa: E402
    write_comprehension_jsonl, write_comprehension_summary_csv,
    write_games_csv, write_turns_jsonl,
)
from crsd.runner.run_experiment import build_games_for_model, load_template  # noqa: E402
from crsd.runner.run_comprehension import make_probe_builder         # noqa: E402
from crsd.runner.batch import run_games_batched                      # noqa: E402
from crsd.engine.round import parse_contribution                     # noqa: E402
from crsd.engine.comprehension import parse_answer                   # noqa: E402
from crsd.models import factory                                      # noqa: E402
from crsd.paths import CONFIGS_DIR                                    # noqa: E402
import FAIRGAME.src.llm_connectors.local_vllm_connector as conn      # noqa: E402
import json                                                          # noqa: E402


def load_experiment(name):
    exp = load_json(CONFIGS_DIR / "experiment" / f"{name}.json")
    if LANGUAGES_OVERRIDE:
        exp["languages"] = list(LANGUAGES_OVERRIDE)
    if REPS_OVERRIDE:
        exp["repetitions"] = int(REPS_OVERRIDE)
    return exp


def agents_cfg_for(exp):
    name = exp.get("agents") or (exp.get("agentsConditions") or ["personas_default"])[0]
    return name, load_json(CONFIGS_DIR / "agents" / f"{name}.json")


def build_probe_builder(exp):
    """Dựng probe_builder từ khối exp['comprehension'] (template/ghế/cap/checkpoint)."""
    comp_cfg = exp.get("comprehension", {})
    langs = exp.get("languages", ["en"])
    comp_templates = {lang: load_template(comp_cfg.get("template", "crsd_comprehension"), lang)
                      for lang in langs}
    return make_probe_builder(
        comp_templates,
        comp_cfg.get("probePlayers", [0]),
        comp_cfg.get("maxSeats", 4),
        comp_cfg.get("maxPastRounds", None),
        comp_cfg.get("rulesCheckpoints", None),
    )


_plan = []
for _en in EXPERIMENTS:
    _exp = load_experiment(_en)
    _n = (len(_exp["games"]) * len(_exp.get("languages", ["en"]))
          * int(_exp.get("repetitions", 1)))
    _plan.append((_en, _n))
    # ~450 probe/game (probePlayers=[0], rulesCheckpoints) — ước lượng thô.
    print(f"Experiment {_en}: {_n} games/model "
          f"(~{_n * 6 * 10} quyết định + ~{_n * 450} probe đọc-hiểu / model).")
print(f"Tổng {len(MODELS)} model × {sum(n for _, n in _plan)} games.")


def offline_settings_for(model_cfg):
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


GEN_PER_MODEL = sum(n for _, n in _plan) * 6 * 10

# =====================================================================
# CELL 5: Helpers — load model, smoke test, chạy 1 experiment, lưu
# =====================================================================
def load_model(model_cfg):
    osettings = offline_settings_for(model_cfg)
    print(f"Loading {model_cfg['short_name']} ({osettings['backend']}) <- {model_cfg['path']}")
    factory.init_offline_backend(osettings, {"modelPath": model_cfg["path"]}, force=True)
    print(f"{model_cfg['short_name']} loaded.")


def smoke_test(model_cfg, exp, agents_cfg, agents_name):
    """Kiểm 1 quyết định (CONTRIBUTION) + 1 probe đọc-hiểu (ANSWER) trên model thật."""
    import time
    send_batch = factory.get_send_batch(model_cfg["short_name"], offline=True, batch_size=0)
    games = build_games_for_model(exp, model_cfg["short_name"], agents_cfg, agents_name,
                                  sampling_seed_base=SAMPLING_SEED_BASE)
    g = games[0]
    # 1) quyết định
    dprompt = g.build_round_prompts()[:1]
    dseeds = g.build_round_sampling_seeds()[:1]
    t0 = time.time()
    dresp = send_batch(dprompt, dseeds)
    dt = time.time() - t0
    val, failed = parse_contribution(dresp[0], g.config.contribution_options)
    print(f"[{model_cfg['short_name']}] decision reply (last 200 chars):\n", dresp[0][-200:])
    print(f"Parsed CONTRIBUTION = {val} (parse_failed={failed})")
    # 2) probe đọc-hiểu (vòng 1 -> Rules + state vô hướng)
    builder = build_probe_builder(exp)
    pprompts, pseeds, pmetas = builder(g)
    if pprompts:
        presp = send_batch(pprompts[:1], pseeds[:1])
        pa, pf = parse_answer(presp[0], pmetas[0]["answer_kind"])
        print(f"[{model_cfg['short_name']}] probe '{pmetas[0]['question_id']}' reply (last 200):\n", presp[0][-200:])
        print(f"Parsed ANSWER = {pa} (parse_failed={pf}) | ground_truth = {pmetas[0]['ground_truth']}")
    _n_probe = int(_plan[0][1] * 454)                 # ~454 probe/game (probePlayers=[0])
    _total_gen = GEN_PER_MODEL + _n_probe             # decision + probe = tải THẬT/model
    print(f"ETA THÔ: 1 gen ~{dt:.1f}s -> ~{dt * _total_gen / 3600:.1f} h/model "
          f"({GEN_PER_MODEL} decision + ~{_n_probe} probe = {_total_gen} gen). "
          f"CẬN TRÊN — batching {BATCH_SIZE} nhanh hơn NHIỀU (baseline thực tế ~30p/3 model). "
          f"Quá lâu thì hạ REPS_OVERRIDE (vd 5) / LANGUAGES_OVERRIDE ở Cell 1.")


def run_comprehension_for_model(model_cfg, exp_name):
    """Chạy MỘT experiment đọc-hiểu cho MỘT model. Lưu turns/games + comprehension."""
    short = model_cfg["short_name"]
    exp = load_experiment(exp_name)
    agents_name, agents_cfg = agents_cfg_for(exp)
    probe_builder = build_probe_builder(exp)

    send_batch = factory.get_send_batch(short, offline=True, batch_size=BATCH_SIZE)
    games = build_games_for_model(exp, short, agents_cfg, agents_name,
                                  sampling_seed_base=SAMPLING_SEED_BASE,
                                  sampling_seeds_applied=True)

    print(f"[{short}/{exp_name}] chạy {len(games)} games + probe đọc-hiểu...")
    results = run_games_batched(games, send_batch, verbose=True, probe_builder=probe_builder)

    out_dir = OUTPUT_DIR / short / exp_name
    all_turns = [t for g in games for t in g.turns]
    all_comp = [c for g in games for c in g.comprehension_records]
    write_turns_jsonl(all_turns, out_dir / "turns.jsonl")
    write_games_csv(results, out_dir / "games.csv")
    write_comprehension_jsonl(all_comp, out_dir / "comprehension.jsonl")
    write_comprehension_summary_csv(all_comp, out_dir / "comprehension_summary.csv")

    # tóm tắt nhanh: accuracy theo category × show_cumulative + parse_fail toàn cục
    import pandas as pd
    sdf = pd.read_csv(out_dir / "comprehension_summary.csv")
    pf = (sdf.n_parse_failed.sum() / sdf.n.sum()) if sdf.n.sum() else 0.0
    _a = sdf.groupby(["category", "show_cumulative"]).agg(n=("n", "sum"), nc=("n_correct", "sum"))
    _a["accuracy"] = _a.nc / _a.n.replace(0, pd.NA)
    print(f"[{short}/{exp_name}] parse_fail_rate={pf:.3f}; accuracy theo category×show_cumulative:")
    print(_a["accuracy"].unstack("show_cumulative").round(3).to_string())
    print(f"[{short}/{exp_name}] xong: {len(all_comp)} probe -> {out_dir}")
    return {"model": short, "experiment": exp_name, "n_games": len(results),
            "n_probes": len(all_comp), "parse_fail_rate": round(float(pf), 4),
            "output_dir": str(out_dir)}


def run_one_model(model_cfg):
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
        summaries.append(run_comprehension_for_model(model_cfg, exp_name))
    return summaries

# =====================================================================
# CELL 6: Chạy LẦN LƯỢT tất cả model
# =====================================================================
import traceback  # noqa: E402

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
manifest = {"sampling_seed_base": SAMPLING_SEED_BASE, "experiments": EXPERIMENTS,
            "batch_size": BATCH_SIZE, "temperature": TEMPERATURE, "runs": []}


def _write_manifest():
    (OUTPUT_DIR / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


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
        _write_manifest()

_done = sum(1 for r in manifest["runs"] if r.get("n_probes"))
print(f"\nHoàn tất {_done} lượt (model × experiment). Chi tiết: run_manifest.json")

# =====================================================================
# CELL 7: Gộp comprehension_summary + accuracy headline (Figure-1 analog + A/B)
# =====================================================================
import pandas as pd  # noqa: E402

_frames = []
for csv_path in OUTPUT_DIR.rglob("comprehension_summary.csv"):
    rel = csv_path.relative_to(OUTPUT_DIR)            # <model>/<experiment>/comprehension_summary.csv
    df = pd.read_csv(csv_path)
    df.insert(0, "experiment", rel.parts[1] if len(rel.parts) >= 2 else "")
    _frames.append(df)

if _frames:
    comb = pd.concat(_frames, ignore_index=True)
    comb.to_csv(OUTPUT_DIR / "crsd_comprehension_all_models.csv", index=False)
    print(f"Gộp {len(_frames)} file -> crsd_comprehension_all_models.csv ({len(comb)} ô).")

    def acc_by(df, by, col):
        """accuracy = Σn_correct/Σn theo nhóm ``by``, trải cột ``col`` (bền mọi pandas)."""
        a = df.groupby(by).agg(n=("n", "sum"), nc=("n_correct", "sum"))
        a["acc"] = a.nc / a.n.replace(0, pd.NA)
        return a["acc"].unstack(col)

    # A/B HEADLINE: accuracy theo category × show_cumulative (cú nhảy State = Fig A7)
    print("\n=== Accuracy theo model × category × show_cumulative (0=pool ẩn, 1=pool hiện) ===")
    print(acc_by(comb, ["model", "category", "show_cumulative"], "show_cumulative")
          .to_string(float_format=lambda x: f"{x:.3f}"))

    # CỔNG hành vi: rules_risk_pct accuracy theo model × risk × language
    rr = comb[comb.question_id == "rules_risk_pct"]
    if len(rr):
        print("\n=== rules_risk_pct accuracy theo model × language × risk (CỔNG diễn giải risk-insensitivity) ===")
        print(acc_by(rr, ["model", "language", "risk_probability"], "risk_probability")
              .to_string(float_format=lambda x: f"{x:.3f}"))

    # EN vs VN tổng thể (RQ ngôn ngữ)
    print("\n=== Accuracy EN vs VN theo model × category ===")
    print(acc_by(comb, ["model", "category", "language"], "language")
          .to_string(float_format=lambda x: f"{x:.3f}"))
else:
    print("Không có comprehension_summary.csv — kiểm tra path MODELS[] / EXPERIMENTS.")

# Gộp games.csv (phần hành vi đi kèm — đối chiếu reach-rate như baseline)
_bf = []
for csv_path in OUTPUT_DIR.rglob("games.csv"):
    rel = csv_path.relative_to(OUTPUT_DIR)
    df = pd.read_csv(csv_path)
    df.insert(0, "experiment", rel.parts[1] if len(rel.parts) >= 2 else "")
    _bf.append(df)
if _bf:
    pd.concat(_bf, ignore_index=True).to_csv(OUTPUT_DIR / "crsd_all_models.csv", index=False)
    print(f"\n(Phần hành vi) gộp games.csv -> crsd_all_models.csv.")

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
