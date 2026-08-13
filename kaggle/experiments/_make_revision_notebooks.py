"""Sinh hai notebook Kaggle cho vòng revision, bằng phép biến đổi CÓ KIỂM SOÁT.

Vì sao không chép tay: hai notebook này phải giữ NGUYÊN cell 2/2.5/3/4/5/6/7 của bản
gốc (seed, CRN, cách nạp vLLM, cách dò repo input) — chỉ đổi đúng phần cấu hình. Chép
tay là cách chắc chắn nhất để làm lệch một dòng rồi mất cả phiên GPU mới phát hiện.
Script này thay từng chuỗi tường minh và BÁO LỖI nếu không tìm thấy, nên không có
thay-đổi-âm-thầm.

    python kaggle/experiments/_make_revision_notebooks.py

Sinh ra:
  kaggle/experiments/nohint.py    <- baseline.py            (reviewer Q1)
  kaggle/experiments/evprobe.py   <- archive/comprehension.py (reviewer Q3)
"""
from __future__ import annotations

import pathlib

HERE = pathlib.Path(__file__).resolve().parent

# Llama-3.1-8B: bản gốc trỏ vào dataset riêng của một account khác
# (foundnotkiet/llama-3-1-8b). Đổi sang Kaggle Models hub để notebook chạy được trên
# BẤT KỲ account nào — đã kiểm slug + version bằng API 13-08-2026.
LLAMA_OLD = '"path": "/kaggle/input/datasets/foundnotkiet/llama-3-1-8b/model_weights",'
LLAMA_NEW = '"path": "/kaggle/input/models/metaresearch/llama-3.1/transformers/8b-instruct/2",'

SMALL_THREE = '''MODELS = [
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
        "path": "/kaggle/input/models/metaresearch/llama-3.1/transformers/8b-instruct/2",
        "short_name": "llama-3-1-8b",
        "engine": "vllm",
    },
]
'''


def sub(text: str, old: str, new: str, what: str) -> str:
    if old not in text:
        raise SystemExit(f"KHONG TIM THAY doan can thay ({what}):\n{old[:160]}")
    return text.replace(old, new, 1)


# --------------------------------------------------------------------------- #
# GPU: hai notebook nay chay qua `kaggle kernels push`, KHONG qua UI.
#
# API chi cho chon NvidiaTeslaT4 / NvidiaTeslaP100 / Tpu1VmV38. RTX PRO 6000
# Blackwell 96GB ma project van dung la tuy chon CHI CO TREN UI.
#   - P100 = sm_60. Wheels vLLM trong trungkiet/vllm-wheels build cho sm_120, va
#     torch trong do chi ho tro sm_75/80/86/90/100/120 -> EngineCore chet ngay.
#     Da do thuc te 13-08-2026: ca hai kernel hong o day, 0 van.
#   - T4 = sm_75 -> torch chay duoc. Nhung MOT T4 chi 16GB, khong du cho
#     gemma-2-9b (~18.5GB fp16) hay llama-3.1-8b (~16.1GB) cong KV cache.
#     Kaggle cap T4 x2 -> phai TP_SIZE=2 de trai model qua ca hai card.
# Neu chay lai tren UI voi RTX PRO 6000 96GB thi doi TP_SIZE ve 1.
# --------------------------------------------------------------------------- #
TP_OLD = "TP_SIZE = 1"
TP_NEW = ("TP_SIZE = 2               # T4 x2 qua API (1 card 16GB khong du cho 9B); "
          "ve 1 neu chay UI tren RTX PRO 6000")


def set_tp2(text: str) -> str:
    if TP_OLD not in text:
        raise SystemExit("KHONG TIM THAY TP_SIZE = 1")
    i = text.index(TP_OLD)
    j = text.index("\n", i)
    return text[:i] + TP_NEW + text[j:]


# --------------------------------------------------------------------------- #
# 1. nohint.py  — ablation bo mo neo equal-split (reviewer Q1)
# --------------------------------------------------------------------------- #
NOHINT_DOC = '''"""
=====================================================================
CRSD — Kaggle OFFLINE notebook (Internet OFF, GPU ON)
ABLATION BO MO NEO EQUAL-SPLIT | 3 model nho
=====================================================================
Sinh ra tu `baseline.py` boi `_make_revision_notebooks.py`. DUNG SUA TAY —
sua script sinh roi chay lai, neu khong hai ban se troi khoi nhau.

VI SAO CO NOTEBOOK NAY (reviewer, Interface Focus, 13-08-2026):

  "How sensitive are the main results to removing the equal-split '2 per round'
   exemplar from the decision prompt? Could you report a small ablation (even on a
   subset of models) to assess anchoring effects on 'just-enough' play and risk
   responsiveness?"

Prompt goc noi thang loi giai chia deu: "(an average of 2 per player per round)" va
vi du "(contributing 2 every round leaves you 20 at the end)". Do la mot hanh dong
tieu diem KHONG phu thuoc risk, nen mot agent gop 2 co the dang hop tac, co the chi
dang lam theo con so duy nhat prompt dua ra.

Notebook nay chay DUNG exp_baseline nhung voi template da BO hai manh do
(crsd_nohint_{en,vn}.txt). `diff` xac nhan hai template chi khac dung 2 dong so voi
ban goc; moi thu khac giong tung byte, KE CA seed va lich xo so, nen ghep cap truc
tiep voi ket qua exp_baseline cung model duoc.

  · Game:       crsd_milinski_{low,medium,high}_risk_nohint  (promptTemplate=crsd_nohint)
  · Experiment: exp_nohint
  · Quy mo:     3 risk x 2 lang x 10 rep = 60 van/model, 3 model = 180 van

DOI CHIEU KHI PHAN TICH: exp_nohint vs exp_baseline, cung model, ghep cap theo
(risk, language, rep). Hai dai luong can nhin:
  (a) P(gop 2) — muc bam hanh dong tieu diem. Neu no sup khi bo goi y thi mo neo
      that su dang dieu khien hanh vi.
  (b) Do nhay risk (0.1 -> 0.9). Neu no VAN phang sau khi bo mo neo thi null cua
      paper khong phai do mo neo — day la ket qua quan trong nhat cua run nay.

Da co bang chung offline rang mo neo KHONG phai nguyen nhan cua null
(paper/revision/r4_anchor_strength.py: tuong quan giua P(gop 2) va |Δrisk| = -0.06).
Run nay la phep kiem truc tiep cho ket luan do.

CACH CHAY: giong baseline.py — GPU ON, Internet OFF, + Add Input: repo (crsd/ +
FAIRGAME/), dataset wheels vLLM, va 3 model duoi day.

Output: /kaggle/working/crsd_results/<model>/exp_nohint/{turns.jsonl, games.csv}
  + crsd_all_models.csv + run_manifest.json + nohint_results.zip o Output tab.
=====================================================================
"""
'''

NOHINT_NEED = '''_need = [REPO_ROOT / "crsd" / "runner" / "run_experiment.py",
         REPO_ROOT / "crsd" / "prompts" / "crsd_nohint_en.txt",
         REPO_ROOT / "crsd" / "prompts" / "crsd_nohint_vn.txt",
         REPO_ROOT / "crsd" / "configs" / "experiment" / "exp_nohint.json",
         REPO_ROOT / "crsd" / "configs" / "game" / "crsd_milinski_high_risk_nohint.json",
         REPO_ROOT / "crsd" / "configs" / "game" / "crsd_milinski_medium_risk_nohint.json",
         REPO_ROOT / "crsd" / "configs" / "game" / "crsd_milinski_low_risk_nohint.json",
         REPO_ROOT / "FAIRGAME" / "src" / "llm_connectors" / "local_vllm_connector.py"]'''


def build_nohint() -> None:
    src = (HERE / "baseline.py").read_text(encoding="utf-8")
    # docstring
    end = src.index('"""', src.index('"""') + 3) + 3
    out = NOHINT_DOC + src[end:]
    # models: thay ca khoi MODELS[...] bang 3 model nho
    m0 = out.index("MODELS = [")
    m1 = out.index("\n]\n", m0) + 3
    out = out[:m0] + SMALL_THREE + out[m1:]
    out = sub(
        out,
        'EXPERIMENTS = ["exp_riskframing"]   # 1 điều kiện: plain + computed-totals, '
        '3 risk, EN+VN',
        'EXPERIMENTS = ["exp_nohint"]   # y het exp_baseline (lottery framing, pool AN) '
        'nhung template da bo goi y chia deu',
        "EXPERIMENTS")
    # _need
    n0 = out.index('_need = [REPO_ROOT')
    n1 = out.index(']', out.index('local_vllm_connector.py', n0)) + 1
    out = out[:n0] + NOHINT_NEED + out[n1:]
    out = set_tp2(out)
    out = sub(out, 'print("OK — crsd/ + FAIRGAME/ + configs/prompts + exp_riskframing đầy đủ.")',
              'print("OK — crsd/ + FAIRGAME/ + template nohint + exp_nohint đầy đủ.")',
              "OK message")
    out = sub(out, 'zip_path = Path("/kaggle/working/baseline_results.zip")',
              'zip_path = Path("/kaggle/working/nohint_results.zip")', "zip name")
    (HERE / "nohint.py").write_bytes(out.encode("utf-8"))
    print("wrote kaggle/experiments/nohint.py")


# --------------------------------------------------------------------------- #
# 2. evprobe.py — probe so sanh ky vong (reviewer Q3)
# --------------------------------------------------------------------------- #
EVPROBE_DOC = '''"""
=====================================================================
CRSD — Kaggle OFFLINE notebook (Internet OFF, GPU ON)
PROBE SO SANH KY VONG | 3 model nho
=====================================================================
Sinh ra tu `archive/comprehension.py` boi `_make_revision_notebooks.py`.
DUNG SUA TAY — sua script sinh roi chay lai.

VI SAO CO NOTEBOOK NAY (reviewer, Interface Focus, 13-08-2026):

  "Could you add a simple probe for expected-value comparison (e.g. 'Which action has
   higher expected value for you at the current p?') to the comprehension battery for
   open-weight models...?"

Bo probe cu do BA truc: Rules (luat, in san trong prompt), Time (tra cuu lich su),
State (trang thai tich luy, phai tu cong). Ca ba deu tra loi duoc bang doc hoac cong.
KHONG truc nao hoi agent NHAN XAC SUAT VOI TIEN — dung phep tinh ma hanh vi cua hai
model EV-optimal trung khop. Vong revision them truc thu tu, `value`:

  · value_defect_ev  — "bo mac ca van va nhom truot muc tieu thi TRUNG BINH ban con
                        bao nhieu?"  Dap an (1-p)*40 = 36 / 20 / 4.
  · value_compare    — "hop tac hay bo mac cho tien trung binh cao hon? 1=hop tac,
                        2=bo mac, 0=bang nhau."  Dap an 2 / 0 / 1 o p=0.1/0.5/0.9.

Hai cau nay KHONG doc duoc tu prompt. Ground truth dong, khong phu thuoc lich su.

CHI HOI TRUC `value` + `rules` (onlyCategories trong exp_evprobe.json), va chi o
rulesCheckpoints [1,5,10]: ca hai truc deu TINH trong mot van nen hoi moi vong la
tra tien vo ich. ~1.800 probe/model thay vi ~54.000 cua bo day du. Rules giu lai lam
doi chung — neu Rules tut so voi run cu thi loi la o setup chu khong phai o truc moi.

  · Experiment: exp_evprobe (game giong exp_baseline: pool AN, khong persona)
  · Quy mo:     3 risk x 2 lang x 10 rep = 60 van/model + ~1.800 probe/model

DOC KET QUA: neu accuracy `value_compare` CAO ma hanh vi van phang theo risk thi
model HIEU phep so sanh nhung KHONG hanh dong theo — day la ket qua manh nhat, no
loai tru not gia thiet "chua du nang luc tinh toan". Neu accuracy THAP thi null it
nhat mot phan la thieu nang luc, va phai noi dung nhu vay trong paper.

CACH CHAY: giong comprehension.py — GPU ON, Internet OFF, + Add Input: repo, dataset
wheels vLLM, 3 model duoi day.

Output: /kaggle/working/crsd_results/<model>/exp_evprobe/
  {turns.jsonl, games.csv, comprehension.jsonl, comprehension_summary.csv}
  + evprobe_results.zip o Output tab.
=====================================================================
"""
'''


def build_evprobe() -> None:
    src = (HERE / "archive" / "comprehension.py").read_text(encoding="utf-8")
    end = src.index('"""', src.index('"""') + 3) + 3
    out = EVPROBE_DOC + src[end:]
    out = sub(out, LLAMA_OLD, LLAMA_NEW, "llama path")
    out = sub(out, 'EXPERIMENTS = ["exp_comprehension"]', 'EXPERIMENTS = ["exp_evprobe"]',
              "EXPERIMENTS")
    # truyen onlyCategories xuong make_probe_builder (ban archive chua co tham so nay)
    out = sub(
        out,
        '        comp_cfg.get("rulesCheckpoints", None),\n    )',
        '        comp_cfg.get("rulesCheckpoints", None),\n'
        '        comp_cfg.get("onlyCategories", None),\n    )',
        "onlyCategories passthrough")
    out = sub(out, 'REPO_ROOT / "crsd" / "runner" / "run_comprehension.py"',
              'REPO_ROOT / "crsd" / "runner" / "run_comprehension.py"', "need anchor")
    out = out.replace('"exp_comprehension.json"', '"exp_evprobe.json"')
    out = set_tp2(out)
    out = sub(out, 'zip_path = Path("/kaggle/working/crsd_results.zip")',
              'zip_path = Path("/kaggle/working/evprobe_results.zip")', "zip name")
    (HERE / "evprobe.py").write_bytes(out.encode("utf-8"))
    print("wrote kaggle/experiments/evprobe.py")


if __name__ == "__main__":
    build_nohint()
    build_evprobe()
