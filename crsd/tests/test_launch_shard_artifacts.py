"""kbench artifact phai roi vao kaggle/benchmarks/artifacts/, khong roi ra goc repo.

Bay nay da xay ra hai lan. `kaggle b t push` / `run` ghi `<task>.task.json` va
`<task>-run_id_*.run.json` ra **thu muc dang dung (CWD)**, chu khong phai canh file
task. Cac launcher deu goi `launch_shard.py` voi `cwd=REPO`, nen khong ghim CWD thi
artifact rai ra goc repo — va cach sua bang tay ("nho cd truoc khi chay") that bai
dung mot lan thi la tai dien.

Test kiem DUNG mot thu: `run_cmd` chay lenh trong thu muc artifacts.
"""
import importlib.util
import io
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _load():
    spec = importlib.util.spec_from_file_location(
        "launch_shard", REPO / "plan" / "scripts" / "launch_shard.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_artifacts_dir_is_the_documented_one():
    mod = _load()
    assert mod.ARTIFACTS == REPO / "kaggle" / "benchmarks" / "artifacts"


def test_run_cmd_executes_inside_the_artifacts_dir(monkeypatch):
    """Lenh kbench phai chay voi cwd=artifacts du tien trinh cha dung o dau."""
    mod = _load()
    seen = {}

    class _Done:
        returncode, stdout, stderr = 0, "", ""

    def fake_run(args, **kw):
        seen.update(kw)
        return _Done()

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    rc, _ = mod.run_cmd(io.StringIO(), {}, ["kaggle", "b", "t", "status", "x"])
    assert rc == 0
    assert seen.get("cwd") == str(mod.ARTIFACTS)
    assert mod.ARTIFACTS.is_dir()


def test_no_kbench_artifact_sits_at_the_repo_root():
    """Cong chan: khong file .task.json/.run.json nao duoc nam o goc repo."""
    stray = [p.name for p in REPO.glob("*.task.json")] + \
            [p.name for p in REPO.glob("*.run.json")]
    assert not stray, (f"artifact kbench nam o goc repo: {stray}. "
                       f"Chuyen vao {mod_artifacts()} bang `git mv`.")


def mod_artifacts():
    return "kaggle/benchmarks/artifacts/"
