"""Một vòng CRSD: dựng prompt cho tất cả người chơi (đồng thời) và parse đóng góp."""
from __future__ import annotations

import re
from typing import List, Tuple

from .prompt import build_prompt


_CONTRIB_LINE_RE = re.compile(
    r"^\s*CONTRIBUTION\s*[:=]\s*(\d+)", flags=re.IGNORECASE | re.MULTILINE
)


def parse_contribution(response: str, options) -> Tuple[int, bool]:
    """Trích mức đóng góp từ phản hồi LLM.

    Thứ tự ưu tiên:
      1. Dòng ``CONTRIBUTION: <n>`` ĐỊNH DẠNG — neo vào ĐẦU DÒNG (``^`` + MULTILINE)
         và lấy match CUỐI cùng, GIỐNG ``parse_note``. Lý do: prompt yêu cầu model
         "suy nghĩ rồi mới chốt", nên nó hay nhắc chữ 'CONTRIBUTION' giữa phần lập
         luận (vd "CONTRIBUTION should stay low... CONTRIBUTION: 4"); bắt match đầu/
         không neo dòng sẽ ghi nhầm con số giữa chừng làm SAI biến phụ thuộc.
         - Nếu giá trị dòng định dạng cuối THUỘC tập lựa chọn -> nhận, parse_failed=False.
         - Nếu NGOÀI tập (vd "CONTRIBUTION: 3" khi opts={0,2,4}) -> đây là vi phạm
           protocol: gắn cờ parse_failed=True (KHÔNG quét prose để "cứu" một con số
           khác), để phân tích lọc theo parse_failed phát hiện được.
      2. Khi KHÔNG có dòng CONTRIBUTION định dạng nào: số hợp lệ xuất hiện sau cùng
         trong văn bản (gần kết luận nhất).
      3. Fallback an toàn = lựa chọn nhỏ nhất, gắn cờ parse_failed.

    Returns:
        (value, parse_failed)
    """
    opts = [int(o) for o in options]
    if not response:
        return opts[0], True

    line_matches = _CONTRIB_LINE_RE.findall(response)
    if line_matches:
        v = int(line_matches[-1])          # dòng định dạng cuối = câu trả lời chốt
        if v in opts:
            return v, False
        return opts[0], True               # có dòng nhưng giá trị ngoài tập -> FAIL (không quét prose)

    nums = [int(x) for x in re.findall(r"\d+", response)]
    valid = [n for n in nums if n in opts]
    if valid:
        return valid[-1], False

    return opts[0], True


_NOTE_LINE_RE = re.compile(r"^\s*NOTE\s*[:=]\s*(.+)$", flags=re.IGNORECASE | re.MULTILINE)


def parse_note(response: str) -> str:
    """Trích ghi chú riêng (chế độ scratchpad) từ dòng ``NOTE: ...``.

    QUAN TRỌNG: phải neo vào ĐẦU DÒNG (``^ ... $`` + MULTILINE) và lấy match CUỐI
    cùng. Lý do: prompt yêu cầu model "viết ghi chú rồi mới quyết định", nên model
    hay dùng chữ 'note' trong phần lập luận trước đó (vd "I should note: ..."); nếu
    bắt match đầu tiên ở bất kỳ đâu sẽ nuốt nhầm văn xuôi đó thay vì dòng ``NOTE:``
    định dạng ở cuối — làm hỏng đúng trí nhớ scratchpad mà thí nghiệm đang đo.

    Trả về chuỗi rỗng nếu model không tuân theo định dạng — đây là một phần của
    "trí nhớ không hoàn hảo" (giống người quên ghi chú), không phải lỗi cứng.
    """
    if not response:
        return ""
    matches = _NOTE_LINE_RE.findall(response)
    if not matches:
        return ""
    # Dòng NOTE định dạng là dòng NOTE cuối cùng (NOTE đứng trước CONTRIBUTION).
    return matches[-1].strip()


class CrsdRound:
    """Helper dựng prompt cho một vòng của một game."""

    def __init__(self, game, round_number: int):
        self.game = game
        self.round_number = round_number

    def build_prompts(self) -> List[str]:
        cfg = self.game.config
        prompts: List[str] = []
        for idx, agent in enumerate(self.game.agents):
            prompts.append(
                build_prompt(
                    self.game.template,
                    cfg,
                    agent.name,
                    idx,
                    agent.persona_text,
                    self.round_number,
                    self.game.history,
                    cfg.language,
                    agent_notes=agent.notes,
                )
            )
        return prompts
