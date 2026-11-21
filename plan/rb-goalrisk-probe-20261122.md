# Goal-prompt risk sweep: the positive control (rebuttal, JJ3F C1/Q1), fixed 2026-11-22 00:20 before any call

Question: would the risk sweep detect risk adaptation if a model had it? The 11-level sweep under the base
prompt found every model flat (`plan/rb-risk-probe-20261121.md`). The submitted paper (Table 4, Goal rows)
shows that stating the own-cash objective makes GPT-5.6 Luna pay little at p = 0.1 (7.7) and the fair share
at p = 0.9 (20.1). The same sweep under that Goal prompt is therefore the natural positive control.

Task source `kaggle/benchmarks/crg_rb_goalrisk_task.py` (`CRG_RB_SET` default `goalrisk`), task
`crg-rb-goalrisk`. Template `neutral` with the framing block ON, i.e. exactly the paper's Goal prompt.
11 risk levels, histories `r1` and `fair`, 10 calls per cell: 220 calls per model. Seeds offset 170,000,000.
Models: Claude Haiku 4.5, Gemini 3.5 Flash-Lite, GPT-5.6 Luna, Claude Haiku 5.5, gpt-oss-120b.

Gates (the same as the base sweep, so the two are comparable): step = mean above the pivot minus below
(fair: {0.4..1.0} vs {0.1..0.3}; r1: {0.6..1.0} vs {0.1..0.4}), 95% bootstrap CI; "risk-responsive" iff
step >= 1.0 and CI excludes 0. Prediction written now: Luna risk-responsive in at least one history;
if no model is, the sweep has no demonstrated sensitivity and the response must say so.
Analysis: `python paper/AAMAS/analysis/rebuttal_risk.py plan/runs/_dl --task crg-rb-goalrisk --tag _goal`.
