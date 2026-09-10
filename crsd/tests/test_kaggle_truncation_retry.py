"""Reply bị CẮT ở trần output phải được retry với cap cao hơn, và nếu vẫn không cứu
được thì phải bị gắn cờ `parse_failed` — không được lặng lẽ nhận một con số bịa.

Đây là hồi quy cho lỗi làm hỏng 39,5% số ván `qwen3-235b` trong data 10-09-2026. Cơ chế:
model tính nhẩm dài, bị cắt TRƯỚC dòng `CONTRIBUTION:`, rồi `parse_contribution` rơi
xuống quy tắc quét-prose (bước 2 trong docstring của nó — hành vi CÓ CHỦ Ý, không phải
bug) và nhặt một chữ số ra từ chính đoạn suy luận, trả `parse_failed=False`. Vòng retry cũ
canh trên `failed` nên không bao giờ chạy.

Vì sao không thể phát hiện bằng chỉ số trung bình: qwen trung bình 8 token/quyết định
trên cap 512 — mọi cổng dựa trên `usage_output_tokens / n_decisions` đều xanh. Chỉ có
ĐUÔI phân bố vượt trần, nên phải kiểm từng lượt.
"""
import importlib.util
import pathlib

import pytest

TASK_PATH = pathlib.Path(__file__).resolve().parents[2] / "kaggle" / "benchmarks" / "crg_task_server.py"


@pytest.fixture
def task(monkeypatch):
    """Nạp crg_task_server.py như module, KHÔNG chạy sweep.

    Cùng khuôn với test_kaggle_seat_models.py: `CRG_SKIP_RUN=1` là cái chặn sweep chạy
    lúc import, và pin CRG_MODEL/LLM_DEFAULT qua monkeypatch để lần ghi vào os.environ
    lúc import được hoàn tác ở teardown thay vì rò sang module test kế tiếp.
    """
    monkeypatch.setenv("CRG_SKIP_RUN", "1")
    for key in ("CRG_SEAT_MODELS", "CRG_TEMPLATE", "CRG_PROMPT_VARIANT", "CRG_PROBE",
                "CRG_PROBE_SEATS", "CRG_PROBE_ROUNDS", "CRG_MAX_OUT", "CRG_OUT"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("CRG_MODEL", "test-model-a")
    monkeypatch.setenv("LLM_DEFAULT", "test-model-a")
    spec = importlib.util.spec_from_file_location("crg_task_server_trunc_test", TASK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "_emit_error", lambda *a, **k: None)
    return module


class _Usage:
    def __init__(self, out):
        self.input_tokens = 10
        self.output_tokens = out
        self.total_cost_nanodollars = 1


# Reply thật lấy từ data hỏng: đứt giữa câu, KHÔNG có dòng CONTRIBUTION, nhưng đầy
# chữ số thuộc {0, 2, 4} để quy tắc quét-prose bám vào.
TRUNCATED = ("Total contributions so far:\n\n- Rounds 1-8: Each player contributed 2 "
             "per round -> 8 rounds x 2 = 16, and 6 players gives 96 in the pool. "
             "If I contribute 0 and others do 2, total = 110 + 10 + 0 = 120 -> still "
             "exactly 1")
COMPLETE = "After weighing the risk I will keep pace with the group.\nCONTRIBUTION: 4"


def test_prose_scan_returns_a_number_with_no_failure_flag(task):
    """Nền của bug: parser một mình KHÔNG phát hiện được reply bị cắt."""
    value, failed = task.parse_contribution(TRUNCATED)
    assert value in (0, 2, 4)
    assert failed is False, "quy tac quet-prose van tra parse_failed=False — day la ly do phai kiem cap"


def test_hit_output_cap_flags_only_the_truncated_reply(task):
    assert task._hit_output_cap(_Usage(512), 512) is True
    assert task._hit_output_cap(_Usage(511), 512) is True      # dung sai cap-1
    assert task._hit_output_cap(_Usage(8), 512) is False
    assert task._hit_output_cap(_Usage(None), 512) is False


def test_truncated_reply_is_retried_at_a_higher_cap(task, monkeypatch):
    """Lượt bị cắt phải gọi lại, và cap phải TĂNG — retry cùng cap thì cắt lại y hệt."""
    calls = []

    def fake_call(model_slug, prompt, seed, ctx=None, max_attempts=None, cap_override=None):
        cap = cap_override or task._max_out_for(model_slug)
        calls.append(cap)
        # Lần đầu bị cắt; sau khi nâng cap thì trả lời trọn vẹn.
        if len(calls) == 1:
            return TRUNCATED, _Usage(cap)
        return COMPLETE, _Usage(120)

    monkeypatch.setattr(task, "_call_llm", fake_call)

    text, value, failed, _, _, _ = task.decide(None, "prompt", 1234)

    assert len(calls) == 2, "phai retry dung 1 lan"
    assert calls[1] > calls[0], f"cap phai TANG khi retry, nhung {calls}"
    assert value == 4 and failed is False
    assert "CONTRIBUTION" in text


def test_still_truncated_after_every_retry_is_recorded_as_parse_failed(task, monkeypatch):
    """Cắt hoài không cứu được thì PHẢI gắn cờ, không được nhận số bịa."""
    caps = []

    def always_truncated(model_slug, prompt, seed, ctx=None, max_attempts=None,
                        cap_override=None):
        cap = cap_override or task._max_out_for(model_slug)
        caps.append(cap)
        return TRUNCATED, _Usage(cap)

    monkeypatch.setattr(task, "_call_llm", always_truncated)

    _, _, failed, _, _, _ = task.decide(None, "prompt", 1234)

    assert failed is True, "reply bi cat ma parse_failed=False -> dung la bug cu quay lai"
    assert len(caps) == task.MAX_PARSE_RETRIES + 1
    assert caps[-1] <= task.MAX_RETRY_CAP, "khong duoc nang cap vuot tran (tien coc proxy)"


def test_complete_reply_is_not_retried(task, monkeypatch):
    """Trả lời gọn (qwen bình thường ~15 ký tự) không được đụng tới."""
    calls = []

    def fake_call(model_slug, prompt, seed, ctx=None, max_attempts=None, cap_override=None):
        calls.append(cap_override)
        return COMPLETE, _Usage(12)

    monkeypatch.setattr(task, "_call_llm", fake_call)

    _, value, failed, _, _, _ = task.decide(None, "prompt", 1234)
    assert (len(calls), value, failed) == (1, 4, False)
