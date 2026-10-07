# Game code

`crg_game.py` runs the six-player collective-risk game (endowment 40, contributions 0, 2 or
4, ten rounds, target 120): it builds each player's prompt, parses the `CONTRIBUTION:` line of
the reply (retrying with a larger output cap if a reply is cut off), plays the scripted
partners, asks the in-game questions and draws the catastrophe lottery. It needs only the
Python standard library.

Models are called through one OpenAI-compatible chat-completions endpoint, so a single key
reaches every provider. The default is [OpenRouter](https://openrouter.ai); set
`CRG_ROUTER_URL` to use a LiteLLM proxy, a vLLM server or a provider's own OpenAI-compatible
API instead.

```sh
export OPENROUTER_API_KEY=...            # or CRG_ROUTER_KEY for another router
CRG_MODEL=anthropic/claude-haiku-4.5 CRG_RISKS=0.1,0.5,0.9 CRG_REPS=10 python crg_game.py
```

Set the output cap for the longest replies, not the average one: a reply cut off before its
`CONTRIBUTION:` line is retried at four times the cap, so `CRG_MAX_OUT=3000` avoids most
retries. Routers that reserve credit by the cap (OpenRouter does) need enough credit for it.

Results go to `CRG_OUT` (default `results/frontier/<model>/<experiment>/`): `games.csv`
(one row per game), `turns.jsonl` (every prompt and reply) and, with questions,
`probes.jsonl`. A finished game is checkpointed, so an interrupted sweep resumes where it
stopped.

| Variable | Meaning | Default |
|---|---|---|
| `CRG_MODEL` | model of the run, as the router names it | `anthropic/claude-haiku-4.5` |
| `CRG_ROUTER_URL` | OpenAI-compatible base URL | `https://openrouter.ai/api/v1` |
| `CRG_ROUTER_KEY` | API key (else `OPENROUTER_API_KEY`, else `OPENAI_API_KEY`) | |
| `CRG_ROUTER_CAP_FIELD` | name of the output-cap field (`max_completion_tokens` for OpenAI reasoning models) | `max_tokens` |
| `CRG_RISKS`, `CRG_REPS` | catastrophe probabilities; games per cell | `0.9,0.5,0.1`; `10` |
| `CRG_TEMPLATE` | prompt variant | `baseline` |
| `CRG_TEMPERATURE` | sampling temperature | `0.7` |
| `CRG_PROBE` | in-game question categories | off |
| `CRG_SEAT_MODELS` | six comma-separated seats: `self`, another model, or `scripted:<policy>` | all `self` |
| `CRG_MAX_OUT` | output cap per reply | 512, or 6000 for reasoning models |

Settings of each data folder in `../data/`:

| Data folder | Settings |
|---|---|
| `exp_baseline` | `CRG_RISKS=0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1` |
| `exp_nohint` | `CRG_TEMPLATE=nohint CRG_RISKS=0.1,0.5,0.9` |
| `exp_wording` | `CRG_TEMPLATE=wording CRG_RISKS=0,0.1,0.9` |
| `exp_neutral` | `CRG_TEMPLATE=neutral CRG_RISKS=0,0.1,0.9` |
| `exp_para1`, `exp_para2` | `CRG_TEMPLATE=para1` or `para2`, `CRG_RISKS=0.1,0.9` |
| `exp_baseline_temp0` | `CRG_TEMPERATURE=0 CRG_RISKS=0.1,0.9` |
| `exp_evprobe` | `CRG_PROBE=rules,value CRG_RISKS=0.1,0.5,0.9` |
| `exp_bestresponse_<x>` | `CRG_SEAT_MODELS=self,scripted:<p>,scripted:<p>,scripted:<p>,scripted:<p>,scripted:<p>` with `<p>` = `always_0` (defect), `always_2` (coop), `always_4` (carry) or `conditional_cooperator` (cond); `CRG_RISKS=0.1,0.3,0.5,0.7,0.9` |
| `exp_mixed` | `CRG_SEAT_MODELS` lists `k` seats of model A, then `6-k` seats of model B (`k` = 1 to 5); `CRG_RISKS=0.1,0.5,0.9` |

The paper's models are Claude Haiku 4.5 (20251001), Gemini 3.5 Flash-Lite, GPT-5.6 Luna,
Qwen3-235B-A22B-Instruct-2507 and Grok 4.20 (0309, non-reasoning); routers name them
differently, so look up each name in the router's model list.

The recorded games were played through a hosted evaluation service that called these
models; this release replaces only that service's client with the router call above. The
prompts, parser, retry rule, seeds, lottery and scripted partners are the code that played
the games. The lottery draws and seat layouts depend only on the repetition index, so every
cell has the same design as in `../data/`. Model text is not reproducible: services accept a
sampling seed but do not return identical text for it, so a rerun is a new sample of the
same design.
