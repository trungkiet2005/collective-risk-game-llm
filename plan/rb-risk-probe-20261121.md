# Risk dose-response probe (rebuttal, JJ3F C1/C3/Q1 and mTF6 W1), fixed 2026-11-21 before any call

Task source `kaggle/benchmarks/crg_rb_risk_task.py` (= `crg_rb_probe_task.py` with `CRG_RB_SET` default
`risk`, built by `plan/scripts/make_rb_probe.py` from `rb_probe_tail.py`). Task name `crg-rb-risk`.
Single calls, no game is played. 440 calls per model.

Design: the base decision prompt, only the stated risk changes, 11 levels p = 0, 0.1, ..., 1.0.
Two histories: `r1` (round 1, no history) and `fair` (round 6 after five rounds in which all six seats
paid 2). Two wordings: base and no-hint (equal-split phrases removed). 10 calls per cell.

Predictions of a payoff-driven agent (endowment 40, target 120, six players, ten rounds):
- `r1`: the symmetric fair-share equilibrium is worth playing only above p* = 120 / (6 x 40) = 0.5.
- `fair`: the other five keep paying 2, so the group reaches 120 iff the focal seat pays 2 in each of
  the five rounds left (cost 10 of its 30). Pay iff 20 > 30 (1 - p), i.e. p > 1/3: best response 0 at
  p <= 0.3, 2 at p >= 0.4.

Models (one Kaggle user each): Claude Haiku 4.5, Gemini 3.5 Flash-Lite, GPT-5.6 Luna (the served panel),
Claude Haiku 5.5 and gpt-oss-120b (newer models; Haiku 5.5 already drops payment at p = 0).

Gates, fixed now:
- Step: mean payment at levels above the pivot minus below it (fair: {0.4..1.0} vs {0..0.3};
  r1: {0.6..1.0} vs {0..0.4}; p = 0.5 excluded for r1), 95% bootstrap CI over calls.
  The benchmark step is 2. A model is called risk-responsive in a cell set only if the step is at
  least 1.0 and its CI excludes 0; otherwise "flat".
- Best-response share below the pivot (paying 0) reported for every model.
- p = 0 is reported separately (dominated payment), not pooled into the step.
- Every model is reported whatever the result; no level is dropped after the data.
Analysis script: `paper/AAMAS/analysis/rebuttal_risk.py` -> `followups/rb_risk.csv`.
