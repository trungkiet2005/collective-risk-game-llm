"""`seat_model_tag` — đặt tên `<model_tag>` từ CẤU HÌNH GHẾ của một ván.

Trước đây `to_wide_csv.py` lấy tên thư mục ông của `games.csv` làm `model_tag`. Với bàn
đồng nhất thì đúng, vì `kaggle b t run -m <slug>` chọn model nào thì server ghi vào thư
mục của model đó. Nhưng bàn hỗn hợp (E3b) chỉ chọn được MỘT trong hai model bằng `-m`,
nên cả bốn cặp có model A đổ về đúng một thư mục và thông tin "đối thủ là ai, mấy ghế"
biến mất khỏi đường dẫn.

Ba nhóm khẳng định mà file này bảo vệ:

1. **Không đổi gì cho dữ liệu đang có.** Bàn đồng nhất và bàn E3a (1 ghế LLM + 5 ghế
   `scripted:`) phải ra ĐÚNG cái tên thư mục hiện tại — 1850 ván đã qua QA không được
   đổi tên dù chỉ một file.
2. **Tên hỗn hợp là CHÍNH TẮC.** Sắp xếp từ điển chứ không lấy thứ tự ghế, nên đổi chỗ
   ghế hay đổi model nào làm `-m` đều cho cùng một tên; nếu không, hai shard đối xứng của
   cùng một cấu hình sẽ đẻ ra hai thư mục và cổng cân bằng của `verify_wide.py` sẽ báo
   lệch ván một cách khó hiểu.
3. **Cấu hình vô nghĩa phải NỔ, không được đoán.** Ba model trong một ván, hay không còn
   model nào, nghĩa là ghế đặt sai; đoán im lặng ở đây sẽ ghi ra một tên không ai truy lại
   được, đúng kiểu lỗi âm thầm mà cây `results/` tồn tại để chặn.
"""
import itertools

import pytest

from crsd.dataio.wide_csv import SCRIPTED_PREFIX, seat_model_tag

# Tag thật của panel 5 model (dạng đã chuẩn hoá, tức y hệt tên thư mục trong `results/`).
HAIKU = "anthropic-claude-haiku-4-5-20251001"
GEMINI = "google-gemini-3.5-flash-lite"
LUNA = "openai-gpt-5.6-luna"
QWEN = "qwen-qwen3-235b-a22b-instruct-2507"
GROK = "xai-grok-4.20-0309-non-reasoning"

# Windows cấm những ký tự này trong tên file; "/" còn tệ hơn vì nó đẻ thêm một cấp thư mục.
FORBIDDEN = r'\/:*?"<>|'


# --- 1. Dữ liệu đang có: tên KHÔNG được đổi -----------------------------------------

@pytest.mark.parametrize("tag", [HAIKU, GEMINI, LUNA, QWEN, GROK])
def test_ban_dong_nhat_giu_nguyen_ten(tag):
    """6 ghế cùng model -> chính tag đó, không thêm tiền tố gì."""
    assert seat_model_tag([tag] * 6) == tag


@pytest.mark.parametrize("policy", ["always_0", "always_2", "always_4",
                                    "conditional_cooperator"])
def test_e3a_mot_ghe_llm_nam_ghe_robot(policy):
    """E3a: 1 ghế LLM + 5 ghế scripted vẫn là bàn ĐỒNG NHẤT.

    Ghế robot không phải model, nên nó không được lọt vào tên — nếu lọt thì 4 profile
    best-response sẽ đẻ ra 4 tên model khác nhau cho cùng một model.
    """
    seats = [GROK] + [SCRIPTED_PREFIX + policy] * 5
    assert seat_model_tag(seats) == GROK


def test_ghe_robot_khong_nhat_thiet_dung_lien_nhau():
    """Ghế LLM nằm giữa đám robot cũng cho cùng kết quả."""
    seats = [SCRIPTED_PREFIX + "always_4", SCRIPTED_PREFIX + "always_4", QWEN,
             SCRIPTED_PREFIX + "always_4", SCRIPTED_PREFIX + "always_4",
             SCRIPTED_PREFIX + "conditional_cooperator"]
    assert seat_model_tag(seats) == QWEN


# --- 2. Bàn hỗn hợp: mix__A__B__kN, chính tắc ----------------------------------------

@pytest.mark.parametrize("k", [1, 2, 3, 4, 5])
def test_mix_k_ghe_dem_theo_tagA(k):
    """k = số ghế của tag ĐỨNG TRƯỚC theo từ điển, không phải của ghế P1.

    Kiểm cả hai chiều: đặt model đứng trước (qwen) ở đầu bàn rồi đặt ở cuối bàn — cùng
    một multiset thì cùng một tên, vì `-m` chọn model nào là chuyện của lúc chạy.
    """
    want = f"mix__{QWEN}__{GROK}__k{k}"
    assert seat_model_tag([QWEN] * k + [GROK] * (6 - k)) == want
    assert seat_model_tag([GROK] * (6 - k) + [QWEN] * k) == want


@pytest.mark.parametrize("k", [1, 2, 3, 4, 5])
def test_mix_khi_model_dung_sau_chiem_da_so(k):
    """Cặp (haiku, qwen): 'a' < 'q' nên tagA = haiku dù qwen giữ nhiều ghế hơn."""
    assert seat_model_tag([HAIKU] * k + [QWEN] * (6 - k)) == f"mix__{HAIKU}__{QWEN}__k{k}"


def test_ten_chinh_tac_khong_phu_thuoc_thu_tu_ghe():
    """Mọi hoán vị của cùng một cấu hình ghế cho đúng một tên.

    Đây là điều kiện để hai shard chạy từ hai phía (một shard `-m qwen`, một shard
    `-m grok`) gộp được vào cùng một file thay vì đẻ ra hai thư mục.
    """
    base = [QWEN, QWEN, GROK, GROK, GROK, QWEN]
    want = f"mix__{QWEN}__{GROK}__k3"
    assert {seat_model_tag(list(p)) for p in itertools.permutations(base)} == {want}


def test_mix_lan_ghe_robot_bi_TU_CHOI():
    """Bàn hỗn hợp mà còn ghế robot thì từ chối đặt tên, không đếm k rồi cho qua.

    Bản đầu của test này khẳng định điều ngược lại — rằng ghế robot bị loại trước khi
    đếm nên `k` vẫn đúng. Đổi 11-09-2026 sau khi vòng phản biện chỉ ra hệ quả: tên
    `mix__` **không mang thông tin ghế robot**, nên `[A,A,A,A,B,B]` và
    `[A,A,A,A,B,scripted:always_4]` cho ra CÙNG một `model_tag` và bị gom vào cùng một
    file — hai cấu hình khác hẳn nhau trộn thành một mà không báo gì.

    Thiết kế E3b không trộn robot vào bàn hỗn hợp, nên cấu hình này chỉ xuất hiện khi
    ai đó gõ sai `--seat-models`. Nổ ngay lúc đặt tên rẻ hơn nhiều so với phát hiện ra
    lúc đọc kết quả, nên chọn từ chối thay vì đặt một cái tên nhập nhằng.
    """
    seats = [QWEN, QWEN, GROK, SCRIPTED_PREFIX + "always_4",
             SCRIPTED_PREFIX + "always_4", SCRIPTED_PREFIX + "always_0"]
    with pytest.raises(ValueError, match="scripted"):
        seat_model_tag(seats)


@pytest.mark.parametrize("seats", [
    [QWEN] * 3 + [GROK] * 3,
    [HAIKU] * 6,
    [GEMINI] + [SCRIPTED_PREFIX + "always_2"] * 5,
])
def test_ten_khong_chua_ky_tu_windows_cam(seats):
    assert not (set(seat_model_tag(seats)) & set(FORBIDDEN))


# --- 3. Cấu hình sai phải NỔ ---------------------------------------------------------

def test_ba_model_tro_len_bao_loi():
    """Thiết kế E3b chỉ có CẶP; ba model nghĩa là ghế đặt sai."""
    with pytest.raises(ValueError, match="CAP"):
        seat_model_tag([QWEN, QWEN, GROK, GROK, HAIKU, HAIKU])


def test_bon_model_cung_bao_loi():
    with pytest.raises(ValueError):
        seat_model_tag([QWEN, GROK, HAIKU, GEMINI, LUNA, LUNA])


def test_toan_ghe_scripted_bao_loi():
    """Không còn model nào thì không có gì để đặt tên — không được lặng lẽ trả rỗng."""
    with pytest.raises(ValueError, match="scripted"):
        seat_model_tag([SCRIPTED_PREFIX + "always_4"] * 6)


def test_o_trong_bao_loi_chu_khong_bi_nuot():
    """Nuốt ô rỗng sẽ làm k lệch âm thầm, mà k chính là biến độc lập của E3b."""
    with pytest.raises(ValueError, match="ghe 3"):
        seat_model_tag([QWEN, QWEN, "", GROK, GROK, GROK])


def test_slug_tho_con_dau_gach_cheo_bao_loi():
    """Slug thô ("qwen/qwen3-…") lọt vào tên sẽ đẻ THÊM một cấp thư mục giữa `<p>/` và
    file, làm vỡ luật "dưới `<experiment>/` chỉ có thư mục tên là số"."""
    with pytest.raises(ValueError, match="cam trong ten file"):
        seat_model_tag(["qwen/qwen3-235b-a22b-instruct-2507"] * 6)


def test_none_cung_la_o_trong():
    with pytest.raises(ValueError, match="ghe 1"):
        seat_model_tag([None] + [QWEN] * 5)
