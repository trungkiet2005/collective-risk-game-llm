"""Chay moi test trong mot thu muc tam, khong phai goc repo.

Ly do: `crg_task_server.py` dang ky task bang decorator `@kbench.task(...)`, va kbench
ghi `<task>.task.json` ra **thu muc dang dung** ngay luc IMPORT. Rat nhieu test o day
import module do, nen chay pytest tu goc repo la rai `collective-risk-baseline-srv.task.json`
ra goc repo moi lan — dung cai bay CLAUDE.md cam.

Cung fixture nay chan luon mot bay thu hai: `CRG_OUT` mac dinh la duong dan TUONG DOI
(`results/frontier/<model>/<experiment>`). Test nao chay sweep ma quen dat `CRG_OUT` se
ghi thang vao `results/` that cua repo. Doi CWD sang thu muc tam bien ca hai loi thanh
rac trong tmp, tu don.

Fixture la autouse nen khong test nao phai nho goi. Moi duong dan ma test that su can
(`TASK_PATH`, `REPO`) deu tinh tu `__file__` nen tuyet doi, khong bi anh huong.
"""
import pytest


@pytest.fixture(autouse=True)
def _run_in_tmp_cwd(tmp_path, monkeypatch):
    # monkeypatch.chdir tu khoi phuc CWD cu o teardown, khong can don tay.
    monkeypatch.chdir(tmp_path)
