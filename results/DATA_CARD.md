# Data card — `results/`

This directory contains the current AAMAS 2027 collective-risk-game results. The
authoritative experiment plan is [`plan/aamas2027-plan.md`](../plan/aamas2027-plan.md),
and source/run provenance is recorded in [`PROVENANCE.json`](PROVENANCE.json). The
separate [`Legacy_Results/`](../Legacy_Results/) tree is not part of the counts below.

## Snapshot

The directory currently contains 3,650 game-level wide CSV rows in 365 CSV files. All
rows use the same CRSD game: six players, ten rounds, endowment 40 per player, legal
contributions `{0, 2, 4}`, and a group target of 120. All recorded games are English
(`language = en`). A game has 60 seat-round decisions, so the wide CSVs represent
219,000 seat-round decisions.
There are 706 recorded catastrophes. Two agent-level parse/truncation events are flagged
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
| **Total wide CSVs** |  | **3,650** |  |  |

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
all seats chose 2 in every round. Across the 3,650 wide rows, the observed supports are:

| Value | Games | Share |
|---|---:|---:|
| `[0, 2, 4]` | 1,867 | 51.2% |
| `[2]` | 849 | 23.3% |
| `[0, 2]` | 477 | 13.1% |
| `[2, 4]` | 348 | 9.5% |
| `[4]` | 69 | 1.9% |
| `[0, 4]` | 30 | 0.8% |
| `[0]` | 10 | 0.3% |

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

`python plan/scripts/verify_wide.py --expect-reps 10` currently checks all 3,650 games
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
