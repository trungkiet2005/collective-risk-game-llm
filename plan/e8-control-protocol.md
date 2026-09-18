# E8 control completion protocol

This protocol covers the three reviewer controls: a group-total objective, a visible running pool, and value questions at zero risk. It fixes the intended panel before any new outcome is inspected.

The complete design has 350 games: five models each play 30 group-objective games, 10 visible-pool self-play games, 10 visible-pool games beside five always-zero partners, 10 beside five always-four partners, and 10 zero-risk value-probe games. Every condition uses English, ten repetitions, the server-side task, and the existing 3,000-token cap.

## Existing runs and completion

Some downloaded E8 outputs contain independent re-runs with the same `(model, risk, rep)` label. Proxy sampling is not deterministic under a fixed seed, so those are not interchangeable copies and must not be pooled as one panel.

Before launching the remaining work, selection is fixed as follows. For each model and arm, select a non-overlapping cover of the required cells that uses the fewest complete source runs. Break a tie by the lexicographically smallest sorted remote run identifiers. A source is eligible only when it has every expected game and all of its recorded turns have `parse_failed = false`. For intentionally split shards, complementary repetition ranges form one cover. The rule uses coverage and identifiers only, never outcomes.

The selected cover currently contains 250 games. The following missing model-arm sweeps are run in full rather than splicing individual cells into a partially completed model sweep: group-objective Grok (30), group-objective Luna (30), visible-pool Flash-Lite (10), visible-pool Luna (10), zero-risk value-probe Qwen (10), and zero-risk value-probe Flash-Lite (10). This adds 100 games and yields one 350-game panel with exactly ten observations per intended cell.

## Acceptance gates

Do not admit an E8 result to the paper until all of these pass:

1. Each selected model-arm cover has exactly its prespecified cells and no duplicated `(model, risk, rep)` key.
2. Every selected turn parses successfully, and the server reports no failed game.
3. Each game, turn, and probe record carries the arm's own prompt suffix and experiment identity.
4. The value-probe arm contains six probes per game at zero risk, and the visible-pool arm records the correct cumulative pool in every prompt.
5. The merged wide data preserve the source-run manifest and pass the existing coverage validator.

Until these gates pass, E8 is protocol-stage work rather than evidence for the manuscript.
