"""Per-round token encoding for CRSD (N-person collective-risk) traces.

A token is ``<context><amount>`` (two characters):

* ``context`` -- ``'E'`` in round 1 (establishment, no prior round); otherwise
  the digit ``k_prev in {0..N}`` = number of players who contributed a nonzero
  amount in the *previous* round. This is exactly the quantity an ``R_M``
  reciprocator conditions on.
* ``amount``  -- the focal player's own contribution this round, one of the
  allowed levels (``{0, 2, 4}`` for the Milinski high-risk config).

This mirrors the 2-char IPD codebook used in the ClusteringResearch project
(``ED, EC, PC, SC, ...``), generalised from "opponent's last move" to
"how many of the group contributed last round".
"""

from __future__ import annotations

# Defaults match crsd/configs/game/crsd_milinski_high_risk.json
N_PLAYERS = 6
CONTRIB_LEVELS = (0, 2, 4)
ROUND1_CTX = "E"


def contributor_count(round_contribs) -> int:
    """Number of players contributing a nonzero amount in one round."""
    return sum(1 for c in round_contribs if c > 0)


def build_vocab(n_players: int = N_PLAYERS, levels=CONTRIB_LEVELS):
    """Return (token_list, token_to_id) in a stable, documented order."""
    tokens = [ROUND1_CTX + str(a) for a in levels]
    for k in range(n_players + 1):
        for a in levels:
            tokens.append(str(k) + str(a))
    token_to_id = {t: i for i, t in enumerate(tokens)}
    return tokens, token_to_id


TOKENS, TOKEN_TO_ID = build_vocab()


def encode_sequence(own, group):
    """Encode one focal player's trace into a list of string tokens.

    Parameters
    ----------
    own   : sequence of the focal player's own contributions, length T.
    group : list of length T; ``group[t]`` is the list of all N contributions
            in round t (used to compute the previous-round contributor count).
    """
    seq = []
    for t in range(len(own)):
        if t == 0:
            seq.append(ROUND1_CTX + str(own[t]))
        else:
            k_prev = contributor_count(group[t - 1])
            seq.append(str(k_prev) + str(own[t]))
    return seq


def parse_token(tok: str):
    """Return (context, amount): context is 'E' or int k_prev; amount is int."""
    ctx, amt = tok[0], tok[1:]
    return (ROUND1_CTX if ctx == ROUND1_CTX else int(ctx)), int(amt)


def tokens_to_ids(seq):
    return [TOKEN_TO_ID[t] for t in seq]


if __name__ == "__main__":
    print(f"vocab size = {len(TOKENS)}")
    print("tokens:", " ".join(TOKENS))
