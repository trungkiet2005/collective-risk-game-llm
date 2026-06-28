"""Các kiểu dữ liệu (dataclass) mô tả cấu hình & kết quả một game CRSD."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, List, Optional


@dataclass
class GameConfig:
    """Tham số cơ chế của một ván CRSD (đọc từ configs/game/*.json)."""

    name: str
    engine: str = "collective_risk"
    n_players: int = 6
    endowment: float = 40.0
    contribution_options: List[float] = field(default_factory=lambda: [0, 2, 4])
    target: float = 120.0
    n_rounds: int = 10
    n_rounds_known: bool = True
    risk_probability: float = 0.90
    show_individual_contributions: bool = True
    show_cumulative: bool = False
    agents_communicate: bool = False
    # --- chế độ trí nhớ (memory mode) ---
    #   "full_history" : nạp lại toàn bộ đóng góp từng vòng mỗi lượt (mặc định,
    #                    = "người ghi chú hoàn hảo", trung thành với thông tin
    #                    mà một người chăm chỉ có thể giữ qua giấy bút).
    #   "scratchpad"   : chỉ cho xem `memory_window` vòng gần nhất + ghi chú
    #                    riêng do chính agent tự viết (mô phỏng "pen & paper"
    #                    có sai số — gần với điều kiện con người hơn).
    memory_mode: str = "full_history"
    memory_window: int = 1  # số vòng gần nhất được hiển thị ở chế độ scratchpad
    # Ghi chú tự viết (scratchpad) mang sang vòng sau như "cuốn sổ tay":
    #   0  = TÍCH LUỸ tất cả ghi chú đã viết (giống tờ giấy đầy dần — mặc định),
    #   k  = chỉ k dòng ghi chú gần nhất,
    #   1  = chỉ dòng gần nhất (ghi đè/overwrite — biến thể trí nhớ siêu nén).
    note_window: int = 0
    # Khung dẫn nhập trung lập (thay cho "tiền thật" mà LLM không có) — KHÔNG kê
    # toa chiến lược, chỉ neo mục tiêu là payoff của chính mình.
    framing: bool = False
    language: str = "en"
    prompt_template: str = "crsd"
    agents_ref: str = "personas_default"
    model: str = "LocalQwen"

    @classmethod
    def from_dict(
        cls,
        d: dict,
        language: Optional[str] = None,
        model: Optional[str] = None,
    ) -> "GameConfig":
        """Tạo từ dict JSON (key kiểu camelCase như FairGame)."""
        return cls(
            name=d["name"],
            engine=d.get("engine", "collective_risk"),
            n_players=int(d.get("nPlayers", 6)),
            endowment=float(d.get("endowment", 40)),
            contribution_options=list(d.get("contributionOptions", [0, 2, 4])),
            target=float(d.get("target", 120)),
            n_rounds=int(d.get("nRounds", 10)),
            n_rounds_known=bool(d.get("nRoundsIsKnown", True)),
            risk_probability=float(d.get("riskProbability", 0.90)),
            show_individual_contributions=bool(d.get("showIndividualContributions", True)),
            show_cumulative=bool(d.get("showCumulative", False)),
            agents_communicate=bool(d.get("agentsCommunicate", False)),
            memory_mode=str(d.get("memoryMode", "full_history")),
            memory_window=int(d.get("historyWindow", 1)),
            note_window=int(d.get("noteWindow", 0)),
            framing=bool(d.get("framing", False)),
            language=language or d.get("language", "en"),
            prompt_template=d.get("promptTemplate", "crsd"),
            agents_ref=d.get("agents", "personas_default"),
            model=model or d.get("model", "LocalQwen"),
        )

    def snapshot(self) -> dict:
        return asdict(self)


@dataclass
class TurnRecord:
    """Một lượt quyết định: agent X ở vòng R (cho phân tích reasoning/XAI)."""

    game_id: str
    round: int
    player: str
    contribution: float
    parse_failed: bool
    reasoning: str
    raw_response: str
    prompt: str
    logprobs: Optional[dict] = None
    latency_ms: Optional[float] = None
    note: Optional[str] = None          # ghi chú agent tự viết (chế độ scratchpad)
    sampling_seed: Optional[int] = None  # seed sinh văn bản cho lượt này (reproducible)
    disposition: Optional[str] = None    # tính cách ghế này (selfish/cooperative/neutral) — phân tích within-group
    # Định danh ô thí nghiệm — denormalize để turns.jsonl TỰ MÔ TẢ (khỏi phải parse game_id).
    risk_probability: Optional[float] = None
    language: Optional[str] = None
    persona_set: Optional[str] = None
    memory_mode: Optional[str] = None
    framing: Optional[bool] = None
    rep: Optional[int] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class GameResult:
    """Kết quả tổng hợp một ván."""

    game_id: str
    config: dict
    language: str
    model: str
    risk_probability: float
    persona_set: str
    per_round_contributions: List[List[float]]
    per_player_totals: List[float]
    group_total: float
    target: float
    target_reached: bool
    catastrophe: bool
    payoffs: List[float]
    player_names: List[str]
    seed: int
    dispositions: List[str] = field(default_factory=list)  # tính cách theo ghế (thứ tự player_names)
    rep: int = -1                                          # lần lặp — khoá join với đối chứng baseline

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ComprehensionRecord:
    """Một lượt KIỂM TRA ĐỌC-HIỂU (probe): hỏi 1 câu về trạng thái game, chấm so
    với ground truth của engine. Tự mô tả (denormalize) để comprehension.jsonl
    phân tích được mà không cần parse game_id.

    ``parsed_answer``/``ground_truth`` đã được chuyển về dạng JSON-friendly (set ->
    list đã sắp xếp) trước khi tạo record.
    """

    game_id: str
    round: int
    player: str
    player_index: int
    question_id: str
    category: str                 # rules | time | state
    params: dict                  # tham số câu hỏi (vd {"i":3,"x":2}; {} cho Rules)
    question_text: str
    raw_response: str
    parsed_answer: Any
    ground_truth: Any
    correct: bool
    parse_failed: bool
    answer_kind: str              # int | int_set | yesno
    answerable_from_prompt: bool  # đáp án IN SẴN (đọc) hay phải TỰ TÍNH (số học)
    language: str
    risk_probability: float
    model: str
    show_cumulative: bool         # nhánh A/B (False=ẩn pool, True=hiện) — Fig A7
    sampling_seed: Optional[int] = None

    def to_dict(self) -> dict:
        return asdict(self)
