"""Test cho loader phát hiện dữ liệu vòng revision (`paper/revision/_data.py`).

Hai script phân tích mới (`r8_nohint_ablation.py`, `r9_ev_probe.py`) đọc kết quả
`exp_nohint` / `exp_evprobe` — thứ được TẢI VỀ dưới dạng zip Kaggle rồi giải nén
bằng tay, nên bố cục thư mục KHÔNG cố định:

  results/raw/crsd_results/<model>/<experiment>/   (bố cục trong zip)
  results/open_source/archive/<experiment>/<model>/ (kho open-weight)
  results/frontier/<model>/<experiment>/            (nhánh proxy)

Loader đoán đâu là model, đâu là experiment theo tiền tố ``exp_``. Nếu đoán sai
thì script chỉ báo "chưa có dữ liệu" trong khi data đang nằm trên đĩa — hỏng âm
thầm, đúng loại lỗi phải có test. Test dựng cả ba bố cục trong tmp_path rồi
monkeypatch ``_data.RESULTS``.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "paper" / "revision"))
import _data as D  # noqa: E402


GAMES_HEADER = "game_id,model,language,risk_probability,group_total,target_reached,rep,seed\n"


def _write_games(d: Path, model: str, risks=(0.1, 0.5, 0.9)) -> None:
    d.mkdir(parents=True, exist_ok=True)
    rows = [GAMES_HEADER]
    for i, p in enumerate(risks):
        rows.append(f"g{i}__{model},{model},en,{p},120,1,{i},999\n")
    (d / "games.csv").write_text("".join(rows), encoding="utf-8")


def _write_turns(d: Path, model: str, risk: float = 0.5) -> None:
    d.mkdir(parents=True, exist_ok=True)
    rec = {"game_id": f"g0__{model}", "round": 1, "player": "Player_1",
           "contribution": 2, "parse_failed": False, "risk_probability": risk,
           "language": "en", "persona_set": "personas_default",
           "disposition": "neutral"}
    (d / "turns.jsonl").write_text(json.dumps(rec) + "\n", encoding="utf-8")


def _write_comprehension(d: Path, model: str, category: str = "value") -> None:
    d.mkdir(parents=True, exist_ok=True)
    rec = {"game_id": f"g0__{model}", "round": 1, "player": "Player_1",
           "player_index": 0, "question_id": "value_compare", "category": category,
           "params": {}, "question_text": "?", "raw_response": "ANSWER: 2",
           "parsed_answer": 2, "ground_truth": 2, "correct": True,
           "parse_failed": False, "answer_kind": "int",
           "answerable_from_prompt": False, "language": "en",
           "risk_probability": 0.1, "model": model, "show_cumulative": False}
    (d / "comprehension.jsonl").write_text(json.dumps(rec) + "\n", encoding="utf-8")


@pytest.fixture()
def fake_results(tmp_path, monkeypatch):
    """Dựng cả ba bố cục + một thư mục frontier/archive PHẢI bị bỏ qua."""
    r = tmp_path / "results"
    _write_games(r / "raw" / "crsd_results" / "model-zip" / "exp_nohint", "model-zip")
    _write_games(r / "open_source" / "archive" / "exp_nohint" / "model-archive",
                 "model-archive")
    _write_games(r / "frontier" / "model-frontier" / "exp_nohint", "model-frontier")
    # bản cũ đã bị loại khỏi panel: các glob sẵn có cũng không đọc nó
    _write_games(r / "frontier" / "archive" / "model-old" / "exp_nohint", "model-old")
    # nghiên cứu phụ nằm sâu thêm một tầng dưới frontier/ (vd lưới risk dày của
    # nhánh AAMAS) cũng dùng tên experiment y hệt -> phải bị loại theo ĐỘ SÂU
    _write_games(r / "frontier" / "dense_grid" / "model-dense" / "exp_nohint",
                 "model-dense")
    monkeypatch.setattr(D, "RESULTS", r)
    return r


def test_model_and_experiment_handles_both_directory_orders(tmp_path):
    a = tmp_path / "m1" / "exp_nohint" / "games.csv"
    b = tmp_path / "exp_nohint" / "m2" / "games.csv"
    assert D._model_and_experiment(a) == ("m1", "exp_nohint")
    assert D._model_and_experiment(b) == ("m2", "exp_nohint")


def test_discover_files_finds_every_layout_and_skips_frontier_archive(fake_results):
    hits = D.discover_files("games.csv", "exp_nohint")
    assert {m for _, m, _ in hits} == {"model-zip", "model-archive", "model-frontier"}
    assert all(e == "exp_nohint" for _, _, e in hits)


def test_discover_files_skips_side_studies_nested_under_frontier(fake_results):
    """`results/frontier/<gì đó>/<model>/<exp>/` KHÔNG thuộc panel 14 cấu hình.

    Các glob của r1–r7 chỉ nhận đúng `frontier/<model>/<exp>/`, nên nghiên cứu phụ
    nằm sâu hơn một tầng vô hình với chúng. Loader đệ quy phải áp lại đúng luật đó,
    nếu không nó lặng lẽ gộp một nghiên cứu khác vào số liệu của paper — đúng loại
    lỗi đã vấp với CORE_RISKS.
    """
    models = {m for _, m, _ in D.discover_files("games.csv", "exp_nohint")}
    assert "model-dense" not in models          # frontier/dense_grid/...
    assert "model-old" not in models            # frontier/archive/...
    assert "model-frontier" in models           # frontier/<model>/<exp>/ thì nhận
    # bố cục ngoài frontier/ vẫn được phép sâu tuỳ ý (zip Kaggle giải nén tay)
    assert {"model-zip", "model-archive"} <= models


def test_discover_files_filters_by_experiment(fake_results):
    assert D.discover_files("games.csv", "exp_evprobe") == []


def test_discover_games_labels_arm_and_dedupes(fake_results):
    df = D.discover_games("exp_nohint")
    assert sorted(df["model"].unique()) == ["model-archive", "model-frontier",
                                            "model-zip"]
    assert set(df["experiment"]) == {"exp_nohint"}
    assert set(df[df.model == "model-frontier"]["arm"]) == {"commercial"}
    assert set(df[df.model == "model-zip"]["arm"]) == {"open_source"}
    assert len(df) == 9                       # 3 model x 3 mức risk, không trùng lặp
    assert "model-dense" not in set(df["model"])


def test_discover_games_applies_core_risk_filter(tmp_path, monkeypatch):
    r = tmp_path / "results"
    _write_games(r / "raw" / "crsd_results" / "m" / "exp_nohint", "m",
                 risks=(0.1, 0.3, 0.9))
    monkeypatch.setattr(D, "RESULTS", r)
    assert sorted(D.discover_games("exp_nohint")["risk_probability"]) == [0.1, 0.9]
    assert len(D.discover_games("exp_nohint", all_risks=True)) == 3


def test_discover_games_returns_empty_frame_when_run_has_not_landed(fake_results):
    df = D.discover_games("exp_evprobe")
    assert df.empty                            # rỗng, KHÔNG ném lỗi


def test_discover_turns_infers_model_from_the_path(tmp_path, monkeypatch):
    r = tmp_path / "results"
    _write_turns(r / "raw" / "crsd_results" / "m-zip" / "exp_evprobe", "m-zip")
    _write_turns(r / "open_source" / "archive" / "exp_evprobe" / "m-arch", "m-arch")
    monkeypatch.setattr(D, "RESULTS", r)
    t = D.discover_turns("exp_evprobe")
    assert sorted(t["model"].unique()) == ["m-arch", "m-zip"]
    assert D.discover_turns("exp_nohint").empty


def test_discover_comprehension_reads_the_new_value_axis(tmp_path, monkeypatch):
    r = tmp_path / "results"
    _write_comprehension(r / "raw" / "crsd_results" / "m" / "exp_evprobe", "m")
    _write_comprehension(r / "open_source" / "archive" / "exp_comprehension" / "m",
                         "m", category="rules")
    monkeypatch.setattr(D, "RESULTS", r)
    c = D.discover_comprehension()
    assert set(c["category"]) == {"value", "rules"}
    assert set(c["experiment"]) == {"exp_evprobe", "exp_comprehension"}
    only = D.discover_comprehension("exp_evprobe")
    assert list(only["category"]) == ["value"]
    assert D.discover_comprehension("exp_nohint").empty


def test_discover_comprehension_can_skip_unwanted_axes(tmp_path, monkeypatch):
    """Lọc theo category: bộ probe đầy đủ ~380k dòng, parse hết mất vài phút."""
    r = tmp_path / "results"
    _write_comprehension(r / "raw" / "crsd_results" / "m" / "exp_evprobe", "m")
    _write_comprehension(r / "open_source" / "archive" / "exp_comprehension" / "m",
                         "m", category="state")
    monkeypatch.setattr(D, "RESULTS", r)
    kept = D.discover_comprehension(categories=("value",))
    assert list(kept["category"]) == ["value"]
    assert len(D.discover_comprehension()) == 2


def test_comprehension_categories_counts_without_parsing(tmp_path, monkeypatch):
    r = tmp_path / "results"
    _write_comprehension(r / "raw" / "crsd_results" / "m" / "exp_evprobe", "m")
    monkeypatch.setattr(D, "RESULTS", r)
    inv = D.comprehension_categories()
    assert len(inv) == 1
    assert inv[0]["experiment"] == "exp_evprobe"
    assert inv[0]["model"] == "m"
    assert inv[0]["categories"] == {"value": 1}
