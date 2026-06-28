"""CLI chạy experiment ĐỌC-HIỂU (in-situ prompt comprehension).

  # smoke-test toàn bộ pipeline KHÔNG cần GPU:
  python -m crsd.runner.run_comprehension crsd/configs/experiment/exp_comprehension.json --mock=random

  # chạy thật (offline GPU):
  python -m crsd.runner.run_comprehension crsd/configs/experiment/exp_comprehension.json

Chạy các ván BASELINE thật; mỗi vòng bắn THÊM các prompt đọc-hiểu (Rules/Time/State)
gửi ở MỘT lời gọi RIÊNG -> KHÔNG đụng quyết định (xem ``batch.run_games_batched``).
Mỗi probe được chấm so ground truth của engine. Xuất ``comprehension.jsonl`` +
``comprehension_summary.csv`` (kèm ``turns.jsonl``/``games.csv`` của phần hành vi).

Lưu ý decoding: probe dùng CÙNG cấu hình sampling như quyết định (đi qua cùng
``send_batch``). Muốn benchmark đọc-hiểu TẤT ĐỊNH (greedy), đặt
``offline_settings.sampling.temperature = 0`` cho run này — khi đó cả lịch sử lẫn
probe đều tất định; CRN seed vẫn giữ tái lập ở mọi nhiệt độ.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

from ..dataio.config_loader import load_json
from ..dataio.recorder import (
    write_comprehension_jsonl,
    write_comprehension_summary_csv,
    write_games_csv,
    write_turns_jsonl,
)
from ..models.factory import get_send_batch, init_offline_backend
from ..paths import CONFIGS_DIR, RESULTS_DIR
from .batch import run_games_batched
from .run_experiment import build_games_for_model, load_template


def make_probe_builder(comp_templates, probe_players, max_seats, max_past_rounds, rules_checkpoints):
    """Trả về ``probe_builder(game) -> (prompts, seeds, metas)`` cho ``run_games_batched``.

    Mỗi vòng, với mỗi ghế trong ``probe_players``, sinh toàn bộ câu hỏi đọc-hiểu trên
    ĐÚNG trạng thái hiện tại. ``rules_checkpoints`` (nếu có) giới hạn nhóm Rules vào
    vài vòng cố định (đáp án Rules bất biến nên không cần hỏi mỗi vòng)."""
    base_caps = {"max_seats": int(max_seats), "max_past_rounds": max_past_rounds}

    def builder(game):
        prompts, seeds, metas = [], [], []
        tmpl = comp_templates[game.config.language]
        caps = dict(base_caps)
        if rules_checkpoints is not None:
            caps["include_rules"] = game.current_round in set(rules_checkpoints)
        for pi in probe_players:
            pps, pseeds, pmetas = game.build_comprehension_prompts(tmpl, pi, caps)
            prompts.extend(pps)
            seeds.extend(pseeds)
            metas.extend(pmetas)
        return prompts, seeds, metas

    return builder


def make_mock_send(strategy="fair", seed=0):
    """Mock cho CẢ quyết định (CONTRIBUTION) lẫn probe (ANSWER) — smoke-test không GPU.

    Phân biệt prompt đọc-hiểu bằng neo ``ANSWER:`` (chỉ template comprehension có).
    Trả lời probe bằng hằng số -> đủ để kiểm pipeline & cho ra HỖN HỢP đúng/sai khi chấm.
    """
    rng = random.Random(seed)

    def send(prompts, seeds=None):
        out = []
        for i, p in enumerate(prompts):
            if "ANSWER:" in p:  # prompt đọc-hiểu
                out.append("(mock comprehension reasoning)\nANSWER: 4")
            else:
                if strategy == "random":
                    c = random.Random(seeds[i]).choice([0, 2, 4]) if seeds is not None else rng.choice([0, 2, 4])
                else:
                    c = 2
                out.append(f"(mock reasoning)\nNOTE: mock\nCONTRIBUTION: {c}")
        return out

    return send


def _parse_mock_flag(argv):
    for a in argv:
        if a == "--mock":
            return "fair"
        if a.startswith("--mock="):
            return a.split("=", 1)[1]
    return None


def main(argv):
    pos = [a for a in argv[1:] if not a.startswith("--")]
    exp_path = Path(pos[0]) if pos else CONFIGS_DIR / "experiment" / "exp_comprehension.json"
    mock_strategy = _parse_mock_flag(argv)

    exp = load_json(exp_path)
    models = exp.get("models", ["LocalQwen"])
    use_offline = bool(exp.get("useOffline", True))
    languages = exp.get("languages", ["en"])
    agents_name = exp.get("agents", "personas_default")
    agents_cfg = load_json(CONFIGS_DIR / "agents" / f"{agents_name}.json")
    out_dir = RESULTS_DIR / exp.get("name", "exp_comprehension")

    comp_cfg = exp.get("comprehension", {})
    comp_template_name = comp_cfg.get("template", "crsd_comprehension")
    comp_templates = {lang: load_template(comp_template_name, lang) for lang in languages}
    probe_builder = make_probe_builder(
        comp_templates,
        comp_cfg.get("probePlayers", [0]),
        comp_cfg.get("maxSeats", 4),
        comp_cfg.get("maxPastRounds", None),
        comp_cfg.get("rulesCheckpoints", None),
    )

    offline_settings = None
    if use_offline and not mock_strategy:
        offline_settings = load_json(
            CONFIGS_DIR / "offline" / f"{exp.get('offlineSettings', 'offline_settings')}.json"
        )
    sampling_seed_base = int(
        ((offline_settings or {}).get("sampling", {}) or {}).get("seedBase", 0)
    )
    if mock_strategy:
        sampling_seeds_applied = (mock_strategy == "random")
    else:
        sampling_seeds_applied = bool(use_offline)

    all_results, all_turns, all_comp = [], [], []

    for model in models:
        if mock_strategy:
            send_batch = make_mock_send(mock_strategy, seed=int(exp.get("seed", 0)))
        elif use_offline:
            preset = load_json(CONFIGS_DIR / "offline" / f"{offline_settings['modelPreset']}.json")
            init_offline_backend(offline_settings, preset)
            send_batch = get_send_batch(
                model, offline=True, batch_size=int(offline_settings.get("batchSize", 0))
            )
        else:
            send_batch = get_send_batch(model, offline=False)

        games = build_games_for_model(
            exp, model, agents_cfg, agents_name,
            sampling_seed_base=sampling_seed_base,
            sampling_seeds_applied=sampling_seeds_applied,
        )
        max_parse_retries = int((offline_settings or {}).get("maxParseRetries", 3)) if (use_offline and not mock_strategy) else 0
        results = run_games_batched(
            games, send_batch, verbose=True,
            max_parse_retries=max_parse_retries, probe_builder=probe_builder,
        )
        all_results.extend(results)
        for g in games:
            all_turns.extend(g.turns)
            all_comp.extend(g.comprehension_records)

    write_turns_jsonl(all_turns, out_dir / "turns.jsonl")
    write_games_csv(all_results, out_dir / "games.csv")
    write_comprehension_jsonl(all_comp, out_dir / "comprehension.jsonl")
    write_comprehension_summary_csv(all_comp, out_dir / "comprehension_summary.csv")
    print(
        f"\nSaved {len(all_results)} games, {len(all_turns)} turns, "
        f"{len(all_comp)} probes -> {out_dir}"
    )


if __name__ == "__main__":
    main(sys.argv)
