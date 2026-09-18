# E8 acceptance audit and certainty-boundary check

## Registered design, unchanged

The controlling specification is `e8-control-protocol.md` and `launch_e8.py`:
350 games, 21,000 turn records, 300 numeric value-probe records. Group-goal framing
uses p=0, 0.1, 0.9; the visible-pool self-play control and the numeric probes use
p=0; visible-pool scripted-partner controls use p=0.9. There are five original
models and ten games per cell. Extra risks, validation models, and failed sweeps
are not automatically appended to this design.

## Acceptance code

`audit_e8_inventory.py` reads historical run metadata and notebook source without
executing downloaded code. `audit_e8_panel.py` checks the original provider/model,
source configuration, full configured seed range, server assertions, raw turn
identity and 60-turn grid, legal actions, totals/target replay, every printed
cumulative pool, scripted-seat actions, and the six value probes per game.
A parsed incorrect answer is retained; correctness is an outcome, not an exclusion
criterion. Source notebook, games, turns, and probes receive SHA-256 hashes.

Selection follows the registered rule: fewest complete non-overlapping source
runs, then lexicographically ordered remote IDs. Do not pick favourable outcomes
or splice cells out of failed runs. The audit exits nonzero until the complete
panel passes; `--allow-incomplete` is only a diagnostic mode.

```sh
python plan/scripts/audit_e8_panel.py /path/to/owner-separated/downloads \
  --output plan/runs/e8_acceptance.json
```

The first raw/source audit on 18 September 2026 accepted 310 games from 22 source
runs (18,600 turns, 240 numeric probes), excluding 18 other original-panel runs.
Four whole ten-game sweeps were scheduled for replacement: Grok visible-pool
self-play at p=0, Grok visible-pool always-zero partners at p=0.9, Grok numeric
probes at p=0, and Haiku visible-pool always-four partners at p=0.9. They use one
authorized existing profile, no quota-driven alias rotation, no new credits, the
original 3,000-token cap and registered concurrency. A submitted task is not an
accepted result. The machine-readable final acceptance manifest supersedes this
initial inventory once every check has passed.

## Game-theoretic boundary

The printed main proposition explicitly assumes p<1; retain that restriction.
An old source/test comment incorrectly said every failed pool is a weak Nash
equilibrium at p=1. Counterexample in the static totals game: six players paying
18 each fail with payoff zero, but one player can pay 30, reach 120 and keep 10.
For p=1, the static pure equilibria are exactly X=T, or X<T with every player's
opponents contributing at most T-e. At equality the player would need to spend its
entire endowment to reach the target and earns zero, so the deviation is not
strictly profitable. This is not a claim of subgame perfection.

`test_p_one_equilibrium_boundary.py` independently checks this boundary against
unilateral-deviation enumeration for all 230,230 unordered total profiles,
covering all 21^6 labelled profiles up to permutation of exchangeable players.
The seven E8 gate tests and eight certainty-boundary tests passed locally before
this audit was committed. Full-suite results should be read from the final
revision's test log, not inferred by adding partial test counts.
