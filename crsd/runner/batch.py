"""Chạy nhiều game lockstep để batch lời gọi LLM (tối ưu throughput offline).

Trong một vòng, các agent chỉ thấy lịch sử các vòng TRƯỚC, và các game độc lập
nhau, nên ở mỗi bước ta gom (n_games × n_players) prompt và gọi LLM một lần.
"""
from __future__ import annotations

from typing import Callable, List, Union

from ..engine.round import parse_contribution

# Đổi seed khi gọi lại: vLLM với CÙNG seed sinh ra output Y HỆT, nên muốn lấy mẫu
# khác (mong parse được) thì phải đổi seed. Vẫn tất định theo (seed gốc, lần thử)
# nên chạy lại toàn bộ vẫn tái lập được.
_RETRY_SEED_MOD = 2_147_483_647  # 2**31 - 1, giữ seed trong int32 dương
_RETRY_SEED_STEP = 1_000_003     # số nguyên tố, tách xa seed các slot khác


def _resp_text(resp: Union[str, dict]) -> str:
    """Lấy phần text từ phản hồi (chuỗi hoặc dict có khoá 'text')."""
    if isinstance(resp, dict):
        return resp.get("text", "") or ""
    return resp or ""


def _failed_slots(responses, options_per_prompt) -> List[int]:
    """Chỉ số các slot mà output KHÔNG parse được CONTRIBUTION (cần gọi lại)."""
    out = []
    for i, r in enumerate(responses):
        _, failed = parse_contribution(_resp_text(r), options_per_prompt[i])
        if failed:
            out.append(i)
    return out


def run_games_batched(
    games,
    send_batch: Callable[..., List[Union[str, dict]]],
    verbose: bool = False,
    max_parse_retries: int = 3,
    probe_builder: Callable = None,
):
    """Chạy tất cả ``games`` đến hết. Trả về list GameResult (đúng thứ tự games).

    ``max_parse_retries``: nếu output của một slot không parse được CONTRIBUTION
    (rỗng / sai định dạng / số ngoài tập), gọi lại RIÊNG slot đó với seed mới, tối đa
    ngần này lần, để kéo tỉ lệ parse_failed về ~0. Đặt 0 để tắt (vd mock/API).

    ``probe_builder``: nếu khác None, là hàm ``probe_builder(game) -> (prompts, seeds,
    metas)`` sinh các prompt ĐỌC-HIỂU cho game ở vòng hiện tại. Chúng được gửi ở MỘT
    lời gọi ``send_batch`` RIÊNG (sau khi quyết định đã gửi & retry xong, TRƯỚC khi áp
    kết quả) -> KHÔNG ảnh hưởng quyết định (model stateless giữa các lần gọi). Mặc định
    None -> đường chạy hành vi y nguyên (giữ tái lập run cũ).
    """
    while True:
        active = [g for g in games if not g.is_done()]
        if not active:
            break

        prompts: List[str] = []
        seeds: List[int] = []
        options_per_prompt = []  # tập lựa chọn đóng góp của từng prompt (để parse)
        meta = []  # (game, count)
        for g in active:
            ps = g.build_round_prompts()
            meta.append((g, len(ps)))
            prompts.extend(ps)
            seeds.extend(g.build_round_sampling_seeds())
            options_per_prompt.extend([g.config.contribution_options] * len(ps))

        if verbose:
            print(f"[batch] {len(active)} games active, {len(prompts)} prompts")

        responses = send_batch(prompts, seeds)
        if len(responses) != len(prompts):
            raise RuntimeError(
                f"send_batch trả về {len(responses)} phản hồi cho {len(prompts)} prompt"
            )

        # Gọi lại các slot parse-fail với seed mới cho tới khi sạch hoặc cạn lượt thử.
        for attempt in range(1, max_parse_retries + 1):
            fail_idx = _failed_slots(responses, options_per_prompt)
            if not fail_idx:
                break
            if verbose:
                print(f"[batch]   retry {attempt}/{max_parse_retries}: "
                      f"{len(fail_idx)} prompt parse-fail")
            retry_prompts = [prompts[i] for i in fail_idx]
            retry_seeds = [(seeds[i] + attempt * _RETRY_SEED_STEP) % _RETRY_SEED_MOD
                           for i in fail_idx]
            retry_resp = send_batch(retry_prompts, retry_seeds)
            if len(retry_resp) != len(retry_prompts):
                raise RuntimeError(
                    f"send_batch (retry) trả về {len(retry_resp)} cho "
                    f"{len(retry_prompts)} prompt"
                )
            for j, i in enumerate(fail_idx):
                responses[i] = retry_resp[j]

        if verbose:
            remain = len(_failed_slots(responses, options_per_prompt))
            if remain:
                print(f"[batch]   còn {remain} prompt parse-fail sau {max_parse_retries} "
                      f"lượt (fallback về lựa chọn nhỏ nhất)")

        # Probe đọc-hiểu (in-situ): hỏi trên ĐÚNG trạng thái vừa quyết định, gửi RIÊNG.
        # Quyết định đã gửi xong ở trên nên byte-identical với run không probe.
        if probe_builder is not None:
            probe_prompts: List[str] = []
            probe_seeds: List[int] = []
            probe_meta = []  # (game, metas, count)
            for g, _ in meta:
                pps, pseeds, pmetas = probe_builder(g)
                if pps:
                    probe_prompts.extend(pps)
                    probe_seeds.extend(pseeds)
                    probe_meta.append((g, pmetas, len(pps)))
            if probe_prompts:
                if verbose:
                    print(f"[batch]   probe đọc-hiểu: {len(probe_prompts)} prompt")
                probe_resp = send_batch(probe_prompts, probe_seeds)
                if len(probe_resp) != len(probe_prompts):
                    raise RuntimeError(
                        f"send_batch (probe) trả về {len(probe_resp)} cho {len(probe_prompts)} prompt"
                    )
                j = 0
                for g, pmetas, k in probe_meta:
                    g.record_comprehension(pmetas, probe_resp[j : j + k])
                    j += k

        i = 0
        for g, n in meta:
            g.apply_round_responses(responses[i : i + n])
            i += n

    return [g.finalize() for g in games]
