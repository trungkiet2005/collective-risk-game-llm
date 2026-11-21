"""Build kaggle/gemma_local/gemma_local_kernel.py: preamble + crg_task_server.py helpers (up to the
SWEEP marker) + rb_probe_tail.py helpers (up to its @kbench.task) + the local runner.

    python plan/scripts/make_gemma_local.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
B = ROOT / "kaggle" / "benchmarks"
G = ROOT / "kaggle" / "gemma_local"
MARK = "# %% =====================  SWEEP"
src = (B / "crg_task_server.py").read_text(encoding="utf-8")
if src.count(MARK) != 1:
    raise SystemExit("SWEEP marker not found exactly once")
head = src.split(MARK)[0]
tail = (B / "rb_probe_tail.py").read_text(encoding="utf-8")
if tail.count("@kbench.task(") != 1:
    raise SystemExit("@kbench.task not found exactly once in rb_probe_tail.py")
tail = tail.split("@kbench.task(")[0]
out = ((G / "_preamble.py").read_text(encoding="utf-8") + head + "\n" + tail + "\n"
       + (G / "_runner.py").read_text(encoding="utf-8"))
(G / "gemma_local_kernel.py").write_text(out, encoding="utf-8")
print("wrote", G / "gemma_local_kernel.py", len(out.splitlines()), "lines")
