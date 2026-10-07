# Recorded games

All 3,950 games analysed in the paper, played by five models in English. Rules: six
players, ten rounds, endowment 40, contributions 0, 2 or 4 per round, target 120.

## Layout

```text
<experiment>/<risk>/<model tag>/p<risk>_en_<model tag>.csv   one row per game
exp_evprobe_probes.csv, exp_evprobe_probes.jsonl              answers to the in-game questions
```

| Folder | Design (paper) | Games | Risks |
|---|---|---:|---|
| `exp_baseline` | 1: self-play over the risk grid | 550 | 0 to 1 by 0.1 |
| `exp_nohint` | 2: equal-split wording removed | 150 | 0.1, 0.5, 0.9 |
| `exp_wording` | 2: neutral wording | 150 | 0, 0.1, 0.9 |
| `exp_neutral` | 2: neutral wording, own-cash objective stated | 150 | 0, 0.1, 0.9 |
| `exp_para1`, `exp_para2` | 2: two paraphrases of the base prompt | 200 | 0.1, 0.9 |
| `exp_baseline_temp0` | 2: base prompt at temperature 0 | 100 | 0.1, 0.9 |
| `exp_evprobe` | 2: in-game value questions | 150 | 0.1, 0.5, 0.9 |
| `exp_bestresponse_defect`, `_coop`, `_carry`, `_cond` | 3: one model beside five scripted partners that always pay 0, 2 or 4, or match the others' mean of the last round | 1,000 | 0.1 to 0.9 by 0.2 |
| `exp_mixed` | 4: `k` seats of model A, `6-k` of model B, every pair, `k` = 1 to 5 | 1,500 | 0.1, 0.5, 0.9 |

Ten games per cell. In `exp_mixed` the folder `mix__<A>__<B>__k<k>` holds the games with
`k` seats of A; `agent1_llm` to `agent6_llm` give the occupant of every seat.

## Columns

Game: `game_id`, `experiment`, `rep`, `seed`, `risk_probability`, `group_contributions`
(per round), `pot_cumulative`, `group_total`, `target_reached`, `catastrophe`,
`mean_payoff`, `n_parse_failures`, plus the fixed rules. Seat `i` = 1 to 6:
`agent{i}_llm` (model or `scripted:<policy>`), `agent{i}_strategies` (contribution in each
round), `agent{i}_scores` (savings left after each round), `agent{i}_payoff` (final, after
the lottery), `agent{i}_parse_failures`.

List columns are Python literals: read them with `ast.literal_eval`, not `json.loads`.

```python
import ast, pathlib, pandas as pd
rows = [pd.read_csv(f) for f in pathlib.Path("exp_baseline").glob("*/*/*.csv")]
df = pd.concat(rows, ignore_index=True)
df["group_contributions"] = df["group_contributions"].map(ast.literal_eval)
print(df.groupby(["agent1_llm", "risk_probability"])["target_reached"].mean().unstack())
```

The lottery is drawn only when the target is missed and is keyed on `rep`, so every cell
reuses the same ten draws; the paper therefore reports expected payoffs. Two games in
`exp_para1` (Grok 4.20, risk 0.1 rep 3 and risk 0.9 rep 8) each contain one seat-round
without a parsable contribution; they are kept and flagged in `n_parse_failures`.
