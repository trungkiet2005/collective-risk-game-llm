"""CLI chạy một experiment campaign.

  # chạy thật (offline GPU):
  python -m crsd.runner.run_experiment crsd/configs/experiment/exp_baseline.json

  # smoke-test toàn bộ pipeline KHÔNG cần GPU (LLM giả lập):
  python -m crsd.runner.run_experiment crsd/configs/experiment/exp_baseline.json --mock
  python -m crsd.runner.run_experiment <exp.json> --mock=random

Mỗi model offline nạp một lần; với mỗi model, mọi (game × ngôn ngữ × lặp lại)
chạy lockstep để batch tối đa (xem crsd.runner.batch).
"""
from __future__ import annotations

import random
import sys
import zlib
from pathlib import Path

from ..dataio.config_loader import load_json, validate_game
from ..dataio.recorder import write_games_csv, write_turns_jsonl
from ..engine.agent import CrsdAgent
from ..engine.game import CrsdGame
from ..engine.state import GameConfig
from ..models.factory import get_send_batch, init_offline_backend
from ..paths import CONFIGS_DIR, PROMPTS_DIR, RESULTS_DIR
from .batch import run_games_batched


def _disposition_of(persona_text):
    """Nhãn ngắn suy từ nội dung persona (EN+VN) để phân tích within-group."""
    t = (persona_text or "").lower()
    if "selfish" in t or "ích kỷ" in t:
        return "selfish"
    if "cooperative" in t or "hợp tác" in t:
        return "cooperative"
    return "neutral"


def _seat_perm(n, cond_name, seed_val):
    """Hoán vị ghế TẤT ĐỊNH cho (điều kiện, rep). KHÔNG phụ thuộc risk/ngôn ngữ nên
    cùng (cond, rep) có CÙNG sắp xếp ở mọi mức rủi ro & EN/VN -> giữ CRN, chỉ biến
    thao tác đổi. Dùng crc32(cond_name) để seed ỔN ĐỊNH giữa các tiến trình (không
    như hash() built-in bị salt theo PYTHONHASHSEED)."""
    perm = list(range(n))
    random.Random(seed_val * 1_000_003 + zlib.crc32(cond_name.encode("utf-8"))).shuffle(perm)
    return perm


def build_agents(agents_cfg, language, perm=None):
    """Dựng 6 agent. ``perm`` (nếu có) hoán vị persona theo ghế: ghế i nhận persona
    của nguồn ``perm[i]`` -> xáo VỊ TRÍ nhưng GIỮ NGUYÊN thành phần (số selfish/coop).
    Tên ghế (Player_1..6) luôn cố định; disposition đi theo persona đã hoán vị."""
    names = agents_cfg["names"]
    personas = agents_cfg.get("personas", {}).get(language, [""] * len(names))

    def persona_for(seat):
        src = perm[seat] if perm is not None else seat
        return personas[src] if src < len(personas) else ""

    return [
        CrsdAgent(name=n, persona_text=persona_for(i), disposition=_disposition_of(persona_for(i)))
        for i, n in enumerate(names)
    ]


def load_template(template_name, language):
    return (PROMPTS_DIR / f"{template_name}_{language}.txt").read_text(encoding="utf-8")


def build_games_for_model(exp, model, agents_cfg=None, agents_name="personas_default",
                          sampling_seed_base=0, sampling_seeds_applied=True):
    """Dựng toàn bộ game cho MỘT model. State-free.

    Tách riêng để cả ``main()`` lẫn notebook Kaggle dùng CHUNG một code path (cùng
    quy tắc seed/CRN), tránh lệch logic. ``exp`` là dict experiment đã load.

    Persona: nếu ``exp["agentsConditions"]`` (list tên persona-set) có mặt -> lặp
    qua TỪNG điều kiện (kiểu FairGame: mỗi điều kiện = một nhóm 6 agent đồng nhất),
    bỏ qua ``agents_cfg`` truyền vào. Ngược lại dùng ``agents_cfg``/``agents_name``
    đơn lẻ (hành vi cũ, game_id giữ nguyên format để không phá experiment hiện có).
    """
    languages = exp.get("languages", ["en"])
    reps = int(exp.get("repetitions", 1))
    base_seed = int(exp.get("seed", 0))
    shuffle_personas = bool(exp.get("shufflePersonas", False))

    conditions = exp.get("agentsConditions")
    if conditions:
        cond_cfgs = [(c, load_json(CONFIGS_DIR / "agents" / f"{c}.json")) for c in conditions]
        tag_persona = True
    else:
        single = agents_cfg if agents_cfg is not None else \
            load_json(CONFIGS_DIR / "agents" / f"{agents_name}.json")
        cond_cfgs = [(agents_name, single)]
        tag_persona = False

    games = []
    for game_name in exp["games"]:
        gd = validate_game(load_json(CONFIGS_DIR / "game" / f"{game_name}.json"))
        for cond_name, cond_cfg in cond_cfgs:
            for language in languages:
                template = load_template(gd.get("promptTemplate", "crsd"), language)
                for rep in range(reps):
                    cfg = GameConfig.from_dict(gd, language=language, model=model)
                    perm = (_seat_perm(len(cond_cfg["names"]), cond_name, base_seed + rep)
                            if shuffle_personas else None)
                    agents = build_agents(cond_cfg, language, perm=perm)
                    gid = (f"{game_name}__{model}__{cond_name}__{language}__rep{rep}"
                           if tag_persona else
                           f"{game_name}__{model}__{language}__rep{rep}")
                    games.append(
                        CrsdGame(
                            cfg, template, agents, gid,
                            seed=base_seed + rep, persona_set=cond_name,
                            sampling_seed_base=sampling_seed_base,
                            sampling_seeds_applied=sampling_seeds_applied,
                            rep=rep,
                        )
                    )
    return games


def make_mock_send_batch(strategy="fair", seed=0):
    """send_batch giả lập (không cần GPU) — smoke-test pipeline.

    strategy: 'fair' (luôn 2), 'free' (0), 'altruist' (4), 'random'.
    Ở strategy 'random', nếu có ``seeds`` per-prompt thì dùng để tất định hoá từng
    lượt (kiểm tra reproducibility); nếu không thì dùng rng chung.
    """
    rng = random.Random(seed)

    def send(prompts, seeds=None):
        out = []
        for i, _ in enumerate(prompts):
            if strategy == "free":
                c = 0
            elif strategy == "altruist":
                c = 4
            elif strategy == "random":
                if seeds is not None:
                    c = random.Random(seeds[i]).choice([0, 2, 4])
                else:
                    c = rng.choice([0, 2, 4])
            else:
                c = 2
            out.append(f"(mock agent reasoning)\nNOTE: mock note\nCONTRIBUTION: {c}")
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
    exp_path = Path(pos[0]) if pos else CONFIGS_DIR / "experiment" / "exp_baseline.json"
    mock_strategy = _parse_mock_flag(argv)

    exp = load_json(exp_path)
    models = exp.get("models", ["LocalQwen"])
    use_offline = bool(exp.get("useOffline", True))
    agents_name = exp.get("agents", "personas_default")
    agents_cfg = load_json(CONFIGS_DIR / "agents" / f"{agents_name}.json")
    out_dir = RESULTS_DIR / exp.get("name", "experiment")

    offline_settings = None
    if use_offline and not mock_strategy:
        offline_settings = load_json(
            CONFIGS_DIR / "offline" / f"{exp.get('offlineSettings', 'offline_settings')}.json"
        )
    # Offset toàn cục cho seed sinh văn bản (mặc định 0). Seed per-lượt vẫn được
    # suy ra từ exp `seed` + rep + vòng + agent (xem CrsdGame.sampling_seed).
    sampling_seed_base = int(
        ((offline_settings or {}).get("sampling", {}) or {}).get("seedBase", 0)
    )
    # Backend có thật sự áp seed per-request không? offline (vLLM/transformers) có;
    # mock 'random' có; API connector hiện chưa. Nếu không, đừng ghi sampling_seed
    # vào log để tránh giả tạo "reproducible".
    if mock_strategy:
        sampling_seeds_applied = (mock_strategy == "random")
    else:
        sampling_seeds_applied = bool(use_offline)

    all_results = []
    all_turns = []

    for model in models:
        if mock_strategy:
            send_batch = make_mock_send_batch(mock_strategy, seed=int(exp.get("seed", 0)))
        elif use_offline:
            preset = load_json(CONFIGS_DIR / "offline" / f"{offline_settings['modelPreset']}.json")
            init_offline_backend(offline_settings, preset)  # nạp 1 lần / process
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

        # Retry chỉ có ý nghĩa khi backend áp seed per-request (offline). Mock luôn
        # parse được; API connector chưa nhận seed -> gọi lại sẽ ra y hệt nên tắt.
        max_parse_retries = int((offline_settings or {}).get("maxParseRetries", 3)) if (use_offline and not mock_strategy) else 0
        results = run_games_batched(
            games, send_batch, verbose=True, max_parse_retries=max_parse_retries
        )
        all_results.extend(results)
        for g in games:
            all_turns.extend(g.turns)
        for r in results:
            print(
                f"[done] {r.game_id}: total={r.group_total} "
                f"reached={r.target_reached} catastrophe={r.catastrophe}"
            )

    write_turns_jsonl(all_turns, out_dir / "turns.jsonl")
    write_games_csv(all_results, out_dir / "games.csv")
    print(f"\nSaved {len(all_results)} games, {len(all_turns)} turns -> {out_dir}")


if __name__ == "__main__":
    main(sys.argv)
