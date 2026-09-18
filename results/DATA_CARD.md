# Data card — `results/`

This directory contains the current AAMAS 2027 collective-risk-game results. The
authoritative experiment plan is [`plan/aamas2027-plan.md`](../plan/aamas2027-plan.md),
and source/run provenance is recorded in [`PROVENANCE.json`](PROVENANCE.json). The
separate [`Legacy_Results/`](../Legacy_Results/) tree is not part of the counts below.

## Snapshot

The directory currently contains 3,950 game-level wide CSV rows in 395 CSV files. All
rows use the same CRSD game: six players, ten rounds, endowment 40 per player, legal
contributions `{0, 2, 4}`, and a group target of 120. All recorded games are English
(`language = en`). A game has 60 seat-round decisions, so the wide CSVs represent
237,000 seat-round decisions.
There are 741 recorded catastrophes. Two agent-level parse/truncation events are flagged
in E6 `exp_para1`; details and their retained rows are documented below.

The five model tags are:

| `agent1_llm` / model tag | Short name |
|---|---|
| `anthropic-claude-haiku-4-5-20251001` | Haiku |
| `google-gemini-3.5-flash-lite` | Flash-Lite |
| `openai-gpt-5.6-luna` | Luna |
| `qwen-qwen3-235b-a22b-instruct-2507` | Qwen |
| `xai-grok-4.20-0309-non-reasoning` | Grok |

## Experiment inventory

| Directory | Role | Games | Risk cells | Repetitions |
|---|---|---:|---|---:|
| `exp_baseline` | Main self-play risk grid | 550 | 0.0–1.0 by 0.1 (11) | 10 |
| `exp_nohint` | E1: equal-split wording removed | 150 | 0.1, 0.5, 0.9 | 10 |
| `exp_evprobe` | E2: in-game comprehension/value probes | 150 | 0.1, 0.5, 0.9 | 10 |
| `exp_bestresponse_defect` | E3a: five scripted all-defect opponents | 250 | 0.1, 0.3, 0.5, 0.7, 0.9 | 10 |
| `exp_bestresponse_coop` | E3a: five scripted always-2 opponents | 250 | same as above | 10 |
| `exp_bestresponse_carry` | E3a: five scripted always-4 opponents | 250 | same as above | 10 |
| `exp_bestresponse_cond` | E3a: five scripted conditional cooperators | 250 | same as above | 10 |
| `exp_mixed` | E3b: mixed-population round robin | 1,500 | 0.1, 0.5, 0.9 | 10 |
| `exp_para1` | E6: prompt paraphrase 1 | 100 | 0.1, 0.9 | 10 |
| `exp_para2` | E6: prompt paraphrase 2 | 100 | 0.1, 0.9 | 10 |
| `exp_baseline_temp0` | E6: baseline prompt, temperature 0 | 100 | 0.1, 0.9 | 10 |
| `exp_wording` | Neutral wording, objective not stated | 150 | 0, 0.1, 0.9 | 10 |
| `exp_neutral` | Neutral wording plus own-cash objective stated | 150 | 0, 0.1, 0.9 | 10 |
| **Total wide CSVs** |  | **3,950** |  |  |

E7 is an offline scripted-reference experiment. Its 2,640 games are represented by
the generated artifacts in `paper/AAMAS/` rather than by rows under `results/`; see
[`paper/AAMAS/analysis/e7_reference.py`](../paper/AAMAS/analysis/e7_reference.py).
There are currently no E5 results in this directory.

The E2 probe answers are not stored in the game CSVs. They are stored at the root of
`results/` in `exp_evprobe_probes.jsonl` and `exp_evprobe_probes.csv` (4,500 probe
records: 3,600 rule questions and 900 value questions). Probe calls were separate from
the game history, so `exp_evprobe/` remains a baseline game condition.

## Directory layout

```text
results/
├── DATA_CARD.md
├── PROVENANCE.json
├── exp_evprobe_probes.jsonl
├── exp_evprobe_probes.csv
└── <experiment>/<risk>/<model-tag>/*.csv
```

Under each experiment, risk directory names are numeric strings (`0`, `0.1`, …, `1`),
and each model directory contains one wide CSV. The risk directory name and the `p...`
part of the filename must use the same literal string. Do not place README files inside
an experiment directory: loaders sort risk directories with `float(p.name)`.

The canonical game key is
`(experiment, model tag, risk_probability, rep)`. In mixed experiments, the model
directory is a composition slug; inspect `agent1_llm` through `agent6_llm` to determine
which model or scripted policy occupies each seat.

## Schema — 82 columns

Every wide CSV currently has 82 columns, divided into four blocks:

| Block | Columns | Meaning |
|---|---:|---|
| A: identity/design | 12 | `game_id`, `experiment`, `language`, `rep`, `seed`, persona and framing fields |
| B: game rules | 9 | `n_players`, `endowment`, `contribution_options`, `target`, risk and round fields |
| C: group outcome | 7 | `group_contributions`, `pot_cumulative`, `group_total`, target/catastrophe, payoff and parse QA |
| D: agents 1–6 | 54 | nine `agent{i}_...` fields per seat |

## AI analysis context

This section is intended to make this card usable as a standalone context for an
analysis agent. Paths are relative to the repository root.

### Complete schema and types

The exact CSV header is:

```text
game_id, experiment, language, rep, seed, persona_set, persona_seats, memory_mode,
opponent_profile, framing, risk_framing, show_computed_totals, n_players, endowment,
contribution_options, target, risk_probability, n_rounds_is_known, max_rounds,
played_rounds, agents_communicate, group_contributions, pot_cumulative, group_total,
target_reached, catastrophe, mean_payoff, n_parse_failures,
agent{i}_name, agent{i}_llm, agent{i}_personality,
agent{i}_knows_opponent_with_prob, agent{i}_strategies, agent{i}_scores,
agent{i}_messages, agent{i}_payoff, agent{i}_parse_failures  (i = 1,...,6)
```

The last template expands to 54 columns, nine per seat; the first block has 28
columns, for 82 total. Scalar fields are strings, integers, floats, or booleans as
named by the field. `contribution_options`, `group_contributions`, `pot_cumulative`,
`agent{i}_strategies`, `agent{i}_scores`, and `agent{i}_messages` are Python literal
lists, not JSON; decode them with `ast.literal_eval`. Empty list fields are `[]`.
Missing values must not be silently converted to zero.

Identity/design fields: `game_id` identifies a game; `experiment` is the authoritative
condition label; `language` is currently always `en`; `rep` and `seed` identify the
repetition and game-level randomization; `persona_set` and `persona_seats` describe
the realized persona assignment; `memory_mode`, `framing`, `risk_framing`, and
`show_computed_totals` describe prompt/game controls; `opponent_profile` is used by
E3a. `agents_communicate` is currently false; do not infer E5 results from it.

Rule fields mean: `n_players=6`, `endowment=40`, legal actions are `{0,2,4}`,
`target=120`, `risk_probability=p`, `max_rounds=10`, and normally
`played_rounds=10`. `contribution_options` is the observed support in a game, not the
legal action set. `n_rounds_is_known` records whether the prompt disclosed the round
count.

For seat `i`, `agent{i}_llm` is the actual model or scripted policy in that seat;
`agent{i}_strategies[t]` is its contribution in round `t`; `agent{i}_scores[t]` is
its remaining private account after round `t`, not a per-round payoff;
`agent{i}_messages[t]` is the message/trace slot (normally empty);
`agent{i}_payoff` is final payoff after the group lottery; and
`agent{i}_parse_failures` counts missing/truncated contribution markers.

### Mechanics and derived quantities

Let `x[i,t] = agent{i}_strategies[t]` and `G[t] = group_contributions[t]`:

```text
G[t] = sum_i x[i,t]
pot_cumulative[t] = sum_{s <= t} G[s]
group_total = pot_cumulative[-1]
target_reached = (group_total >= target)
private_score[i,t] = endowment - sum_{s <= t} x[i,s]
agent{i}_payoff = 0 if catastrophe == 1 else private_score[i,-1]
mean_payoff = mean(agent{i}_payoff for i=1,...,6)
```

The catastrophe lottery is evaluated only if the target is missed. Thus
`catastrophe=0` whenever `target_reached=1`; there is no intermediate payoff or
learning payoff. Money is settled once at the end of the game.

The equal-share total is 120 and the fair share is 2 per seat per round. Under the
risk-neutral benchmark, the theoretical pivot is `p*=0.5` because certain payoff 20
from contributing the fair share equals `(1-p)*40` from contributing zero. The paper's
attainable benchmark and derived welfare metrics are:

```text
optimal_payoff(p) = max((1-p) * endowment, endowment - target / n_players)
expected_payoff = (endowment - group_total / n_players) * (1 if target_reached else 1-p)
welfare_gap = optimal_payoff(p) - expected_payoff
welfare_loss_pct = 100 * welfare_gap / optimal_payoff(p)
```

At `p=0`, contributing is strictly dominated under any increasing utility. Realized
catastrophe counts are noisy end-of-game outcomes and should be separated from
contribution and target-rate analyses.

### Experiment-specific context

| Experiment | Meaning |
|---|---|
| `exp_baseline` | Five-model self-play; `p=0,0.1,...,1.0`; 10 repetitions per cell. |
| `exp_nohint` | E1: `p=0.1,0.5,0.9`; removes both explicit equal-split wording spans while retaining target, group size, and round count. |
| `exp_evprobe` | E2: same game condition at three risks. Separate rule/value probe calls occur at rounds 1, 5, and 10 and do not enter game history. Probe results are in the root probe files, not wide rows. |
| `exp_bestresponse_defect` | E3a: one LLM in `agent1` against five scripted `always_0` seats. |
| `exp_bestresponse_coop` | E3a: one LLM against five scripted `always_2` seats. |
| `exp_bestresponse_carry` | E3a: one LLM against five scripted `always_4` seats. |
| `exp_bestresponse_cond` | E3a: one LLM against five scripted conditional cooperators. |
| `exp_mixed` | E3b: all model pairs, ten compositions from one through five seats of model A, `p=0.1,0.5,0.9`, 10 repetitions. Inspect all six `agent{i}_llm` fields; the slug alone is not the seat truth. |
| `exp_para1`, `exp_para2` | E6: endpoint cells `p=0.1,0.9` under two baseline-prompt paraphrases. |
| `exp_baseline_temp0` | E6: endpoint cells under the baseline prompt at temperature 0. |
| `exp_neutral` | Demand-effect control, `p=0,0.1,0.9`. Baseline prompt with "collective-risk social dilemma", "climate account", "must reach" and "disaster" replaced by neutral wording, and the objective sentence "the only thing that matters to you is your own final cash payoff" switched on (`framing = 1`). The equal-split hint is kept. Compare with `exp_baseline` at the same `p`; read it together with `exp_wording`. |
| `exp_wording` | The same neutral wording as `exp_neutral` with the objective sentence left off (`framing = 0`). `exp_baseline` to `exp_wording` isolates the words; `exp_wording` to `exp_neutral` isolates the stated objective. |
| E7 | Offline scripted reference; not represented by rows in `results/`. Use `paper/AAMAS/analysis/e7_reference.py` and its generated artifacts. |
| E5 | No current results. Do not infer them from the schema. |

In E3a, `agent1_*` is the LLM seat and `agent2_*` through `agent6_*` are scripted;
their `agent{i}_llm` values contain `scripted:<policy>`. Main runs use English prompts,
temperature 0.7, and `max_out=3000` where recorded by provenance; the E6 temp-zero arm
is the exception. Seeds reproduce game randomization/design, not necessarily model text.

### Statistical conventions

The default independent unit is the game, not a seat-round decision: six seats and ten
rounds within a game share history, pool, and lottery. Do not treat 60 decisions per
game as 60 independent observations. Report `n_games` and denominators for all rates.
Target rate is `mean(target_reached)`, catastrophe rate is `mean(catastrophe)`, and
per-seat contribution is total contribution divided by six, averaged at the game/model
level. The paper uses game-level percentile bootstrap intervals and permutation tests
over game-level labels; use the relevant analysis script for the exact resample count
and seed. Retain the two known parse-failure rows by default and report them; do not
silently drop them.

### Authoritative analysis entry points

```text
paper/AAMAS/analysis/crsd_data.py    # shared loader; expected payoffs; macro writer
paper/AAMAS/analysis/crsd_style.py   # figure style (palette, fonts, size gates)
paper/AAMAS/analysis/selfplay.py     # baseline grid, no-cue arm, E6 robustness
paper/AAMAS/analysis/probes.py       # E2 in-game questions vs play
paper/AAMAS/analysis/scripted.py     # E3a scripted partners, exact best response
paper/AAMAS/analysis/mixed.py        # E3b slack and partner response
paper/AAMAS/analysis/advantage.py    # E3b same-table payoff edge and group success
paper/AAMAS/analysis/selection.py    # E3b alpha-Rank selection within vs across tables
paper/AAMAS/analysis/e7_reference.py # E7 scripted reference (not used in the paper)
plan/scripts/verify_wide.py          # structural/balance validation
```

Welfare numbers in the paper use the EXPECTED payoff over the lottery, not
`mean_payoff`: the lottery is keyed on `rep`, so the corpus holds ten draws reused in
every cell, all below 0.47, and every missed game at `p >= 0.5` ended in catastrophe.

When a derived value conflicts with an informal calculation, prefer the corresponding
analysis script and generated tables under `paper/AAMAS/tables/`. `results/` contains
wide game summaries only; prompts, reasoning traces, and server shard logs are not
stored here.

The important outcome fields are:

- `group_contributions`: string representation of a length-10 list containing the group
  contribution in each round.
- `pot_cumulative`: string representation of the cumulative group total after each round.
- `group_total`: final value of `pot_cumulative`.
- `target_reached`: 1 exactly when `group_total >= target`.
- `catastrophe`: the group lottery outcome; it can be 1 only when the target was missed.
- `mean_payoff`: mean final payoff across the six seats.
- `agent{i}_strategies`: that seat's ten round contributions.
- `agent{i}_scores`: that seat's remaining private account after each round, not a
  per-round payoff.
- `agent{i}_payoff`: final payoff after the group lottery.
- `agent{i}_parse_failures`: round-level missing-marker/truncation count for that seat.

`contribution_options` is an observed-support field, not the game rule. The legal action
set is always `{0, 2, 4}`, but a particular game may contain only `[2]`, for example, if
all seats chose 2 in every round. Across the 3,950 wide rows, the observed supports are:

| Value | Games | Share |
|---|---:|---:|
| `[0, 2, 4]` | 1,990 | 50.4% |
| `[2]` | 891 | 22.6% |
| `[0, 2]` | 533 | 13.5% |
| `[2, 4]` | 355 | 9.0% |
| `[4]` | 92 | 2.3% |
| `[0, 4]` | 64 | 1.6% |
| `[0]` | 25 | 0.6% |

## Loading the wide CSVs

The list-valued columns are Python literals, not JSON. Use `ast.literal_eval` rather
than `json.loads`.

```python
import ast
import pathlib
import pandas as pd

ROOT = pathlib.Path("results")
LIST_COLS = (
    ["group_contributions", "pot_cumulative"]
    + [f"agent{i}_{k}" for i in range(1, 7)
       for k in ("strategies", "scores", "messages")]
)

def load(experiment="exp_baseline"):
    frames = []
    files = sorted((ROOT / experiment).glob("*/*/*.csv"),
                   key=lambda p: float(p.parent.parent.name))
    for path in files:
        frame = pd.read_csv(path)
        for column in LIST_COLS:
            frame[column] = frame[column].map(ast.literal_eval)
        frame["model_tag"] = path.parent.name
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)

df = load()
print(df.groupby(["model_tag", "risk_probability"])
        ["target_reached"].mean().unstack())
```

For E6, load `exp_para1`, `exp_para2`, and `exp_baseline_temp0` separately. For E2,
load the probe files with `pd.read_json(..., lines=True)` or `pd.read_csv(...)`.

## Integrity and known exceptions

`python plan/scripts/verify_wide.py --expect-reps 10` currently checks all 3,950 games
and reports two known violations. Both are one missing/truncated contribution marker in
`agent2` of Grok games in `exp_para1`:

| File | Risk | Rep | Issue |
|---|---:|---:|---|
| `exp_para1/0.1/xai-grok-4.20-0309-non-reasoning/...csv` | 0.1 | 3 | one `agent2_parse_failures` |
| `exp_para1/0.9/xai-grok-4.20-0309-non-reasoning/...csv` | 0.9 | 8 | one `agent2_parse_failures` |

The affected rows are retained in the dataset. At the game level, `n_parse_failures`
sums to 2; the apparent sum of 4 across all `*_parse_failures` columns double-counts the
same events in the game total and seat-level column. These are the only current parse/
truncation exceptions reported by `verify_wide.py`.

The structural checks enforce the following invariants for every row:

- all list lengths equal `played_rounds`;
- the six seat contributions sum to `group_contributions` in every round;
- `pot_cumulative` is the cumulative sum and `group_total` is its final value;
- `target_reached` agrees with `group_total >= target`;
- catastrophe is zero whenever the target is reached;
- each private score is non-increasing and equals the endowment minus cumulative own
  contributions;
- each final payoff agrees with the catastrophe outcome and final private score;
- language is `en`, risk matches the directory, and repetition/model keys are unique;
- every experiment is balanced across the five models, except that mixed compositions
  are validated by seat counts rather than by the directory name.

## Provenance and reproducibility

Four models' baseline-grid rows were imported from `Legacy_Results`; Qwen's 110 baseline
rows were rerun because the earlier corpus contained truncation-related silent parse
errors. Baseline and E1–E3 provenance is recorded in `PROVENANCE.json`; mixed-population
and E6 details are recorded in the corresponding launch scripts and plan under
`plan/scripts/` and `plan/aamas2027-plan.md`.

The game-level RNG is reproducible from the recorded seed and repetition design, including
catastrophe draws and persona assignment. Model-generated text is not guaranteed to be
reproducible at the same seed: replaying a cell is a new observation, not a byte-identical
copy. Prompts, configuration, code, and seeds support reproduction of the design, not an
identical transcript.

`results/` contains wide game summaries only. Reasoning traces, prompts, and server shard
artifacts are not stored here; they remain in the ignored run/download locations described
in the project runbook.
