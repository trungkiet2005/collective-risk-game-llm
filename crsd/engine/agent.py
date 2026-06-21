"""Agent CRSD — chỉ giữ trạng thái người chơi (tên, persona, lịch sử đóng góp).

Việc gọi mô hình do runner đảm nhiệm (qua hàm ``send_batch``) để dễ batch nhiều
prompt trong một lần generate (tối ưu throughput khi chạy offline trên GPU).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class CrsdAgent:
    name: str
    persona_text: str = ""
    disposition: str = "neutral"  # nhãn ngắn suy từ persona (selfish/cooperative/neutral) cho phân tích
    contributions: List[float] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)  # ghi chú riêng từng vòng (scratchpad)

    def total_contribution(self) -> float:
        return float(sum(self.contributions))

    def record(self, contribution: float) -> None:
        self.contributions.append(float(contribution))

    def last_note(self) -> str:
        """Ghi chú riêng tư gần nhất do chính agent viết (rỗng nếu chưa có)."""
        return self.notes[-1] if self.notes else ""

    def record_note(self, note: str) -> None:
        self.notes.append(note or "")
