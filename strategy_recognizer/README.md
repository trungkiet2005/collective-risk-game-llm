# CRSD Strategy Recognizer

Recognize / classify the **aspiration-level reciprocator** strategies of the
collective-risk social dilemma (CRSD), following Van Segbroeck, Pacheco,
Lenaerts & Santos, *"Emergence of Fairness in Repeated Group Interactions"*,
Phys. Rev. Lett. **108**, 158104 (2012).

This mirrors the pipeline in `D:\AI_RESEARCH\ClusteringResearch` (synthetic
labelled trajectories → LSTM/ML classifiers → apply to LLM traces), but adapts
it from the 2-person Iterated Prisoner's Dilemma to the **N=6 person**
collective-risk game implemented in `crsd/`.

## Strategy family (the "R_M" reciprocators)

Van Segbroeck et al. define, for a group of size `N`, the strategies `R_M`
(M = 1..N): an `R_M` player **contributes in round 1**, and thereafter
**contributes only if at least `M` players contributed in the previous round**.
Plus `AD` (always defect / never contribute).

With `N = 6` (the size used by `crsd/configs/game/crsd_milinski_high_risk.json`),
the label space is **R1, R2, R3, R4, R5, R6, AD** (7 classes).

| Label | Rule (from round 2 on)                       | Name                          |
|-------|----------------------------------------------|-------------------------------|
| R1    | contribute if ≥1 of the 6 contributed        | Aspiration-1 / *Lenient*      |
| R2    | contribute if ≥2 contributed                 | Aspiration-2 Reciprocator     |
| R3    | contribute if ≥3 (half of the group)         | Aspiration-3 / *Half-quorum*  |
| R4    | contribute if ≥4 contributed                 | Aspiration-4 Reciprocator     |
| R5    | contribute if ≥5 contributed                 | Aspiration-5 Reciprocator     |
| R6    | contribute only if **all 6** contributed     | Aspiration-6 / *Unanimity*    |
| AD    | never contribute                             | Always-Defect / *Free-rider*  |

Optional extra classes (baselines / distractors, off by default): `AC`
(unconditional cooperator = R0) and `RND` (random).

### Design decisions (confirmed)
- **Contribution levels kept at {0, 2, 4}** (not binarised). "Contributed" = a
  nonzero amount. When an `R_M` player is triggered it contributes its
  per-agent `coop_level ∈ {2, 4}` (a within-class nuisance trait, sampled per
  agent so all three levels appear in the data and the classifier must key off
  the *trigger threshold*, not the amount). Fair share = 120 / 6 / 10 = 2/round.
- **Threshold counts the whole group including self** (paper's wording:
  "at least M players did contribute in the previous round").

## Per-round token encoding (codebook)

Analogue of the ClusteringResearch 2-char IPD code (`ED, EC, PC, ...`). Here a
token is `<context><amount>`:
- `context`: `E` in round 1 (establishment); otherwise the digit
  `k_prev ∈ {0..6}` = number of the 6 players who contributed in the previous
  round — this is exactly what `R_M` conditions on.
- `amount`: the focal player's own contribution this round, `∈ {0, 2, 4}`.

Vocabulary = `E0 E2 E4` + `{0..6}×{0,2,4}` = **24 tokens**. See `codebook.py`.

## Files / pipeline (all built and runnable)
- `codebook.py`     — token vocabulary + encode/decode of CRSD traces.
- `strategies.py`   — R_M / AD / AC / RND policies over {0,2,4}.
- `generate_synthetic.py` — group-based synthetic labelled dataset generator
  (mirrors `generate_noise_dataset_30round.py`). `--env-mode exogenous`
  (context-covering, for training) or `endogenous` (realistic group dynamics,
  held-out test); NoNoise/Noise005/Noise01/Noise02.
- `rule_label.py`   — deterministic rule-based labeller (baseline).
- `encode_llm_traces.py` — turns `results/data/**/turns.jsonl` into token
  sequences (`Dataset/llm_traces_encoded.csv`, one row per agent trajectory).
- `data_utils.py` / `torch_models.py` — loading/featurisation + LSTM/GRU/CNN.
- `train_classifiers.py` — rule + LogReg + RandomForest + LSTM + GRU + 1D-CNN,
  at **fine** (R1..R6, AD) and **coarse** (Lenient/Moderate/Strict, AD)
  granularity. Trains on exogenous, evaluates on held-out exogenous + endogenous.
  → `results/metrics.csv`, `results/confusion_*.png`, `saved_models/*`.
- `apply_and_report.py` — applies the trained recogniser to the LLM traces →
  `results/llm_strategy_predictions.csv` + distribution by model/language.

### How to reproduce
```
python generate_synthetic.py --env-mode exogenous  --games-per-strategy 3000 --variants NoNoise Noise005 Noise01
python generate_synthetic.py --env-mode endogenous --games-per-strategy 1500 --variants NoNoise Noise005
python encode_llm_traces.py --glob "../results/data/**/turns.jsonl"
python train_classifiers.py
python apply_and_report.py
```

### Headline results (10-round games, N=6)
- **Fine (7-class)** is capped at ~0.80 accuracy even on clean context-covering
  data — *all* models (rule/LogReg/RF/LSTM/GRU/CNN) land within ~1 point, so the
  ceiling is inherent R_M **identifiability** at a 10-round horizon, not model
  capacity. On realistic endogenous play it falls to ~0.44 (clean) / ~0.56 (noisy).
- **Coarse (Lenient/Moderate/Strict/AD)** is much more robust: ~0.89 on clean
  data, ~0.59 / ~0.73 on endogenous — recommend coarse labels for LLM claims.

## Possible next steps (not done)
- 30-round horizon (better identifiability); Transformer head; per-λ EGT overlay.
