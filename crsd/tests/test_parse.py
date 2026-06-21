"""Test parse mức đóng góp từ phản hồi LLM."""
from crsd.engine.round import parse_contribution

OPTS = [0, 2, 4]


def test_parse_contribution_line():
    v, failed = parse_contribution("I'll cooperate this round.\nCONTRIBUTION: 4", OPTS)
    assert v == 4 and failed is False


def test_parse_fallback_numeric():
    v, failed = parse_contribution("I decide to give 2 this time.", OPTS)
    assert v == 2 and failed is False


def test_parse_contribution_line_wins_over_noise():
    # Có '1' và '10' nhưng dòng CONTRIBUTION quyết định.
    v, failed = parse_contribution("Round 1 of 10.\nCONTRIBUTION: 0", OPTS)
    assert v == 0 and failed is False


def test_parse_invalid_falls_back():
    v, failed = parse_contribution("I refuse to answer.", OPTS)
    assert v == 0 and failed is True


def test_parse_empty():
    v, failed = parse_contribution("", OPTS)
    assert v == 0 and failed is True


def test_parse_ignores_inline_keyword_in_reasoning():
    # Nhắc 'CONTRIBUTION:' giữa lập luận KHÔNG được ghi nhầm; dòng định dạng cuối thắng.
    v, failed = parse_contribution(
        "Maybe CONTRIBUTION: 0 is too stingy here.\nLet me reconsider.\nCONTRIBUTION: 4", OPTS)
    assert v == 4 and failed is False


def test_parse_last_formatted_line_wins():
    v, failed = parse_contribution("CONTRIBUTION: 0\nactually no, raise it.\nCONTRIBUTION: 4", OPTS)
    assert v == 4 and failed is False


def test_parse_out_of_set_value_marks_failed():
    # Dòng định dạng có giá trị ngoài {0,2,4} -> FAIL, KHÔNG cứu '4' từ prose.
    v, failed = parse_contribution("I considered 4 but will give 3.\nCONTRIBUTION: 3", OPTS)
    assert failed is True and v == 0
