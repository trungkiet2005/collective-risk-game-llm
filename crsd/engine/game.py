"""Engine CRSD: vòng lặp game, ngưỡng mục tiêu, xổ số rủi ro, payoff.

Cấu trúc mô phỏng FairGame nhưng cơ chế tính điểm là threshold + risk lottery
(KHÔNG dùng payoff matrix như game 2 người của FairGame).

Game được thiết kế để chạy "stepwise" — ``build_round_prompts`` rồi
``apply_round_responses`` — nên cùng một game có thể chạy:
  - tuần tự (``run``), hoặc
  - lockstep cùng nhiều game khác để batch LLM (xem ``crsd.runner.batch``).
"""
from __future__ import annotations

import random
import re
from typing import Callable, List, Union

from . import scoring
from .comprehension import iter_questions, make_record
from .prompt import build_prompt
from .round import CrsdRound, parse_contribution, parse_note
from .state import ComprehensionRecord, GameResult, TurnRecord

# Khoảng cách giữa các seed của hai rep liên tiếp; đủ lớn để (round*100 + agent)
# không bao giờ tràn sang rep kế tiếp (round<100, agent<100 -> <10000 << stride).
_SAMPLING_SEED_STRIDE = 100_000
_SAMPLING_SEED_MOD = 2_147_483_647  # 2**31 - 1, giữ seed trong phạm vi int32 dương

# Seed của probe đọc-hiểu nằm trong KHÔNG GIAN RIÊNG, lệch khỏi seed quyết định
# (offset lớn + stride theo thứ tự câu hỏi) -> tất định & tái lập, không trùng dụng ý.
_PROBE_SEED_OFFSET = 700_000_000
_PROBE_SEED_STRIDE = 10_000


def _unpack(resp: Union[str, dict]):
    """Chuẩn hoá phản hồi: trả (text, logprobs_or_None)."""
    if isinstance(resp, dict):
        logprobs = {
            k: resp[k]
            for k in ("token_logprobs", "cumulative_logprob", "top_alternatives")
            if k in resp
        }
        return resp.get("text", ""), (logprobs or None)
    return resp, None


def _extract_reasoning(text: str) -> str:
    """Giữ phần lập luận, bỏ khối NOTE + dòng CONTRIBUTION.

    Cắt từ dòng ``NOTE:`` định dạng CUỐI CÙNG trở đi — KHỚP với ``parse_note`` (vốn
    giữ NOTE cuối). Nếu model lỡ viết một dòng ``NOTE:`` sớm trong lập luận rồi mới
    tới NOTE/CONTRIBUTION thật ở cuối, cắt ở NOTE đầu sẽ nuốt mất phần lập luận ở giữa
    (thậm chí rỗng); cắt ở NOTE cuối giữ lại đúng phần suy nghĩ. Chế độ full_history
    không có NOTE nên không bị ảnh hưởng; dòng CONTRIBUTION còn lại được lọc tiếp.
    """
    if not text:
        return ""
    matches = list(re.finditer(r"^\s*NOTE\s*[:=]", text, flags=re.IGNORECASE | re.MULTILINE))
    if matches:
        text = text[:matches[-1].start()]
    lines = [
        ln for ln in text.splitlines()
        if not re.match(r"\s*CONTRIBUTION\s*[:=]", ln, flags=re.IGNORECASE)
    ]
    return "\n".join(lines).strip()


class CrsdGame:
    def __init__(self, config, template, agents, game_id, seed=0,
                 persona_set="personas_default", sampling_seed_base=0,
                 sampling_seeds_applied=True, rep=0):
        self.config = config
        self.template = template
        self.agents = agents  # list[CrsdAgent]
        self.game_id = game_id
        self.seed = seed                       # seed cho xổ số thảm hoạ (CRN theo rep)
        self.sampling_seed_base = sampling_seed_base  # offset toàn cục cho seed sinh văn bản
        # backend có THỰC SỰ dùng seed per-request không? offline (vLLM/transformers)
        # và mock 'random' có; API connector hiện chưa -> khi False, KHÔNG ghi
        # sampling_seed vào log để tránh giả tạo "reproducible".
        self.sampling_seeds_applied = sampling_seeds_applied
        self.persona_set = persona_set
        self.rep = rep                         # lần lặp (= seed - base_seed) — khoá join baseline
        self.rng = random.Random(seed)
        self.history: List[List[float]] = []   # [round][player] -> contribution
        self.turns: List[TurnRecord] = []
        self.comprehension_records: List[ComprehensionRecord] = []  # probe đọc-hiểu (in-situ)
        self.current_round = 1

    # --- stepwise API (dùng cho cả run tuần tự lẫn batch lockstep) ---

    def is_done(self) -> bool:
        return self.current_round > self.config.n_rounds

    def build_round_prompts(self) -> List[str]:
        return CrsdRound(self, self.current_round).build_prompts()

    def sampling_seed(self, agent_idx: int, round_number: int) -> int:
        """Seed sinh văn bản cho một (agent, vòng) — tất định & duy nhất.

        Phụ thuộc CHỈ vào (base_seed, rep, vòng, agent) qua ``self.seed`` (= base+rep);
        KHÔNG phụ thuộc mức rủi ro hay ngôn ngữ, nên cùng một (rep, vòng, agent) ở các
        điều kiện khác nhau dùng CHUNG seed (common random numbers) — chỉ prompt khác
        nhau khiến output khác. Vừa reproducible (chạy lại y hệt) vừa độc lập giữa các
        rep (không còn cảnh 10 rep ra quyết định y chang).
        """
        s = (self.sampling_seed_base
             + self.seed * _SAMPLING_SEED_STRIDE
             + round_number * 100
             + agent_idx)
        return s % _SAMPLING_SEED_MOD

    def build_round_sampling_seeds(self) -> List[int]:
        return [self.sampling_seed(i, self.current_round) for i in range(len(self.agents))]

    # --- probe đọc-hiểu (in-situ): hỏi trên ĐÚNG trạng thái agent đang quyết định ---

    def comprehension_seed(self, player_index: int, round_number: int, q_ord: int) -> int:
        """Seed cho 1 probe — suy từ ``sampling_seed`` rồi đẩy sang không gian riêng."""
        base = self.sampling_seed(player_index, round_number)
        return (base + _PROBE_SEED_OFFSET + q_ord * _PROBE_SEED_STRIDE) % _SAMPLING_SEED_MOD

    def build_comprehension_prompts(self, comp_template, player_index: int, caps=None):
        """Dựng prompt + seed + meta cho mọi câu hỏi đọc-hiểu ở vòng hiện tại, từ góc
        nhìn ghế ``player_index``. Dùng CÙNG luật/state/lịch sử như prompt quyết định
        (chỉ khác đuôi = câu hỏi). KHÔNG đổi state game. Trả về ``(prompts, seeds, metas)``.
        """
        cfg = self.config
        agent = self.agents[player_index]
        items = iter_questions(cfg, self.history, self.current_round, player_index, caps)
        prompts: List[str] = []
        seeds: List[int] = []
        metas: List[dict] = []
        for q_ord, (spec, params) in enumerate(items):
            qtext = spec.render(cfg, self.history, self.current_round, player_index, params, cfg.language)
            prompts.append(
                build_prompt(
                    comp_template, cfg, agent.name, player_index, agent.persona_text,
                    self.current_round, self.history, cfg.language,
                    agent_notes=agent.notes, question_text=qtext,
                )
            )
            seed = self.comprehension_seed(player_index, self.current_round, q_ord)
            seeds.append(seed)
            metas.append({
                "game_id": self.game_id,
                "round": self.current_round,
                "player": agent.name,
                "player_index": player_index,
                "question_id": spec.id,
                "category": spec.category,
                "params": dict(params),
                "question_text": qtext,
                "ground_truth": spec.ground_truth(cfg, self.history, self.current_round, player_index, params),
                "answer_kind": spec.answer_kind,
                "answerable_from_prompt": bool(spec.answerable(cfg)),
                "language": cfg.language,
                "risk_probability": cfg.risk_probability,
                "model": cfg.model,
                "show_cumulative": bool(getattr(cfg, "show_cumulative", False)),
                "sampling_seed": seed if self.sampling_seeds_applied else None,
            })
        return prompts, seeds, metas

    def record_comprehension(self, metas, responses) -> None:
        """Chấm & lưu các probe (responses khớp thứ tự ``metas``)."""
        for m, resp in zip(metas, responses):
            text = resp.get("text", "") if isinstance(resp, dict) else (resp or "")
            self.comprehension_records.append(make_record(m, text))

    def apply_round_responses(self, responses: List[Union[str, dict]]) -> None:
        cfg = self.config
        is_scratchpad = getattr(cfg, "memory_mode", "full_history") == "scratchpad"
        round_contribs: List[float] = []
        # Dựng lại prompt (dùng ghi chú của vòng TRƯỚC) để log — phải làm trước khi
        # ghi note mới, nếu không prompt log sẽ lệch so với prompt agent thực sự thấy.
        prompts = CrsdRound(self, self.current_round).build_prompts()  # khớp thứ tự agent
        seeds = self.build_round_sampling_seeds()
        logged_seeds = seeds if self.sampling_seeds_applied else [None] * len(seeds)
        for idx, (agent, resp) in enumerate(zip(self.agents, responses)):
            text, logprobs = _unpack(resp)
            value, failed = parse_contribution(text, cfg.contribution_options)

            # Không cho đóng quá phần còn lại (chốt an toàn — thường không xảy ra
            # vì max 4/vòng * 10 vòng = 40 = endowment).
            remaining = cfg.endowment - agent.total_contribution()
            if value > remaining:
                allowed = [o for o in cfg.contribution_options if o <= remaining]
                value = max(allowed) if allowed else 0

            note = parse_note(text) if is_scratchpad else None
            agent.record(value)
            if is_scratchpad:
                agent.record_note(note or "")  # mang sang vòng sau (rỗng nếu model quên)
            round_contribs.append(value)
            self.turns.append(
                TurnRecord(
                    game_id=self.game_id,
                    round=self.current_round,
                    player=agent.name,
                    contribution=value,
                    parse_failed=failed,
                    reasoning=_extract_reasoning(text),
                    raw_response=text,
                    prompt=prompts[idx],
                    logprobs=logprobs,
                    note=note,
                    sampling_seed=logged_seeds[idx],
                    disposition=getattr(agent, "disposition", None),
                    risk_probability=cfg.risk_probability,
                    language=cfg.language,
                    persona_set=self.persona_set,
                    memory_mode=getattr(cfg, "memory_mode", "full_history"),
                    framing=bool(getattr(cfg, "framing", False)),
                    risk_framing=getattr(cfg, "risk_framing", "lottery"),
                    show_computed_totals=bool(getattr(cfg, "show_computed_totals", False)),
                    rep=self.rep,
                )
            )
        self.history.append(round_contribs)
        self.current_round += 1

    def finalize(self) -> GameResult:
        cfg = self.config
        per_player_totals = [a.total_contribution() for a in self.agents]
        outcome = scoring.final_payoffs(
            cfg.endowment, per_player_totals, cfg.target, cfg.risk_probability, self.rng
        )
        return GameResult(
            game_id=self.game_id,
            config=cfg.snapshot(),
            language=cfg.language,
            model=cfg.model,
            risk_probability=cfg.risk_probability,
            persona_set=self.persona_set,
            per_round_contributions=self.history,
            per_player_totals=per_player_totals,
            group_total=outcome["group_total"],
            target=cfg.target,
            target_reached=outcome["target_reached"],
            catastrophe=outcome["catastrophe"],
            payoffs=outcome["payoffs"],
            player_names=[a.name for a in self.agents],
            seed=self.seed,
            dispositions=[getattr(a, "disposition", "neutral") for a in self.agents],
            rep=self.rep,
        )

    # --- chạy tuần tự một game (batch trong từng vòng = n_players prompt) ---

    def run(self, send_batch: Callable[..., List[Union[str, dict]]]) -> GameResult:
        while not self.is_done():
            prompts = self.build_round_prompts()
            seeds = self.build_round_sampling_seeds()
            responses = send_batch(prompts, seeds)
            self.apply_round_responses(responses)
        return self.finalize()
