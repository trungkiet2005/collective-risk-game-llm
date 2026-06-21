"""Chạy nhiều game lockstep để batch lời gọi LLM (tối ưu throughput offline).

Trong một vòng, các agent chỉ thấy lịch sử các vòng TRƯỚC, và các game độc lập
nhau, nên ở mỗi bước ta gom (n_games × n_players) prompt và gọi LLM một lần.
"""
from __future__ import annotations

from typing import Callable, List, Union


def run_games_batched(
    games,
    send_batch: Callable[..., List[Union[str, dict]]],
    verbose: bool = False,
):
    """Chạy tất cả ``games`` đến hết. Trả về list GameResult (đúng thứ tự games)."""
    while True:
        active = [g for g in games if not g.is_done()]
        if not active:
            break

        prompts: List[str] = []
        seeds: List[int] = []
        meta = []  # (game, count)
        for g in active:
            ps = g.build_round_prompts()
            meta.append((g, len(ps)))
            prompts.extend(ps)
            seeds.extend(g.build_round_sampling_seeds())

        if verbose:
            print(f"[batch] {len(active)} games active, {len(prompts)} prompts")

        responses = send_batch(prompts, seeds)
        if len(responses) != len(prompts):
            raise RuntimeError(
                f"send_batch trả về {len(responses)} phản hồi cho {len(prompts)} prompt"
            )

        i = 0
        for g, n in meta:
            g.apply_round_responses(responses[i : i + n])
            i += n

    return [g.finalize() for g in games]
