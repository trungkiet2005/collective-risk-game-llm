"""Build kaggle/benchmarks/crg_rb_probe_task.py: crg_task_server.py helpers + rb_probe_tail.py.

    python plan/scripts/make_rb_probe.py
"""
from pathlib import Path

B = Path(__file__).resolve().parents[2] / "kaggle" / "benchmarks"
MARK = "# %% =====================  SWEEP"
src = (B / "crg_task_server.py").read_text(encoding="utf-8")
if src.count(MARK) != 1:
    raise SystemExit("SWEEP marker not found exactly once in crg_task_server.py")
head = src.split(MARK)[0]
out = head + (B / "rb_probe_tail.py").read_text(encoding="utf-8")
(B / "crg_rb_probe_task.py").write_text(out, encoding="utf-8")
print("wrote", B / "crg_rb_probe_task.py", len(out.splitlines()), "lines")
