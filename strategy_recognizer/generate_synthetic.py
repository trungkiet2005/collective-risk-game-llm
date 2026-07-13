"""Generate a synthetic, labelled CRSD strategy dataset.

Mirrors ClusteringResearch's ``generate_noise_dataset_30round.py`` but for the
N=6 collective-risk game. Each line of an output file is::

    R3: E2 5c... -> "R3: E2 62 62 40 ..."

i.e. ``<label>: t1 t2 ... tT`` where each token is the ``<context><amount>``
code from ``codebook.py``.

Because ``R_M`` only reveals itself against a *varied* group context, each game
places the focal strategy in seat 0 and fills the other N-1 seats with
strategies drawn at random from the label space, so every strategy is observed
across the full range of previous-round contributor counts.
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

from codebook import CONTRIB_LEVELS, N_PLAYERS, encode_sequence
from strategies import CORE_LABELS, EXTRA_LABELS, decide

COOP_LEVELS = tuple(a for a in CONTRIB_LEVELS if a > 0)  # (2, 4)


def sample_coop_level(rng):
    return rng.choice(COOP_LEVELS)


def flip_noise(action, coop_level, noise_p, rng):
    """With prob noise_p, flip contribute<->defect (0 <-> coop_level)."""
    if noise_p > 0.0 and rng.random() < noise_p:
        return 0 if action > 0 else coop_level
    return action


def simulate_group(seat_labels, coop_levels, n_rounds, noise_p, rng):
    """Endogenous game: all N seats play their strategy. Returns T x N matrix."""
    contribs = []
    for t in range(n_rounds):
        prev = contribs[t - 1] if t > 0 else None
        row = []
        for seat in range(len(seat_labels)):
            a = decide(seat_labels[seat], coop_levels[seat], t, prev, rng)
            a = flip_noise(a, coop_levels[seat], noise_p, rng)
            row.append(a)
        contribs.append(row)
    return contribs


def simulate_exogenous(focal, coop_level, n_rounds, n_players, noise_p, rng):
    """Focal at seat 0 plays its strategy against an exogenous environment in
    which the number of *other* contributors is drawn uniformly on 0..N-1 each
    round, so k_prev sweeps the full range and every threshold M is probed.
    Returns a T x N matrix with the focal in column 0.
    """
    contribs = []
    for t in range(n_rounds):
        prev = contribs[t - 1] if t > 0 else None
        a = flip_noise(decide(focal, coop_level, t, prev, rng),
                       coop_level, noise_p, rng)
        n_others = rng.randint(0, n_players - 1)
        others = [sample_coop_level(rng) for _ in range(n_others)] + \
                 [0] * (n_players - 1 - n_others)
        rng.shuffle(others)
        contribs.append([a] + others)
    return contribs


def generate_file(labels, out_path, n_rounds, noise_p, games_per_strategy,
                  n_players, seed, env_mode):
    rng = random.Random(seed)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n_written = 0
    with out_path.open("w", encoding="utf-8") as f:
        for focal in labels:
            for _ in range(games_per_strategy):
                if env_mode == "exogenous":
                    coop = sample_coop_level(rng)
                    contribs = simulate_exogenous(focal, coop, n_rounds,
                                                  n_players, noise_p, rng)
                else:  # endogenous
                    seat_labels = [focal] + [rng.choice(labels)
                                             for _ in range(n_players - 1)]
                    coop_levels = [sample_coop_level(rng)
                                   for _ in range(n_players)]
                    contribs = simulate_group(seat_labels, coop_levels,
                                              n_rounds, noise_p, rng)
                own = [contribs[t][0] for t in range(n_rounds)]
                seq = encode_sequence(own, contribs)
                f.write(f"{focal}: {' '.join(seq)}\n")
                n_written += 1
    print(f"wrote {out_path} | mode={env_mode} | labels={len(labels)} "
          f"| rounds={n_rounds} | noise={noise_p} "
          f"| per_strategy={games_per_strategy} | lines={n_written}")


NOISE_VARIANTS = {
    "NoNoise": 0.0,
    "Noise005": 0.05,
    "Noise01": 0.10,
    "Noise02": 0.20,
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out-root", default="Dataset/noise_dataset_crsd")
    p.add_argument("--rounds", type=int, default=10)
    p.add_argument("--n-players", type=int, default=N_PLAYERS)
    p.add_argument("--games-per-strategy", type=int, default=5000)
    p.add_argument("--seed", type=int, default=20260712)
    p.add_argument("--include-extra", action="store_true",
                   help="also include AC and RND classes")
    p.add_argument("--env-mode", choices=("exogenous", "endogenous"),
                   default="exogenous",
                   help="exogenous = context-covering (train); "
                        "endogenous = realistic group dynamics (held-out test)")
    p.add_argument("--variants", nargs="*", default=list(NOISE_VARIANTS),
                   help="subset of: " + " ".join(NOISE_VARIANTS))
    args = p.parse_args()

    labels = CORE_LABELS + (EXTRA_LABELS if args.include_extra else [])
    tag = str(len(labels)) + "strats" + "".join(labels)
    out_root = Path(args.out_root) / args.env_mode

    seed = args.seed
    for variant in args.variants:
        noise_p = NOISE_VARIANTS[variant]
        suffix = "nonoise" if variant == "NoNoise" else variant.lower()
        fname = f"{tag}_{suffix}.txt"
        generate_file(labels, out_root / variant / fname, args.rounds, noise_p,
                      args.games_per_strategy, args.n_players, seed,
                      args.env_mode)
        seed += 1


if __name__ == "__main__":
    main()
