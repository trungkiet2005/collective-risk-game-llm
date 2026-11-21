# STATE: collective-risk-game-llm (AAMAS 2027)

## Now (2026-11-21)

Reviews are in (three reviewers; details stay off this public repo). Rebuttal window
20 to 24 Nov 2026 AoE (about 19:00 on 25 Nov, Vietnam time); reviewers acknowledge by
3 Dec; notification 21 Dec. The AAMAS 2027 pages give no rebuttal length; AAMAS 2025
capped it at 2,500 characters, so every response is written to fit 2,500 (user, 11-21).

Repo moved to the Mac on 2026-11-21: cloned from GitHub into `active/`; the Windows copy
(`D:\PhD_LetGoo\PhD_Farming\archive\collective-risk-game-llm`) was clean and equal to
origin/main. Branch `submission/overview-figure-20260919` (the submitted paper, 13 commits)
merged into main.

## Rebuttal lanes

| lane | asked by | status |
|---|---|---|
| within-model risk trend, offline | R1 | done: `paper/AAMAS/analysis/rebuttal_trend.py`, `followups/rebuttal_trend.csv` |
| running pool shown, self-play p=0.1, 0.9 | R3 | running (`crg-rb-showpool`) |
| same-history counterfactual, explained decisions, game recognition | R1, R2 | running (`crg-rb-probe`, task source `kaggle/benchmarks/crg_rb_probe_task.py`) |
| E8 follow-up (pool shown at p=0 and with scripted partners, p=0 value probe, group goal) | R3, R2 | ran 2026-09-18, numbers in `paper/AAMAS/analysis/followups/e8_*.csv`; raw data was on the retired GreenNode pod |
| responses | all | drafts kept outside git (`.git/info/exclude`: `docs/rebuttal_aamas2027/`) |

## Running jobs

Status 2026-11-21 11:10: 8/15 shards clean. Agent lane "rescue" reruns probe Flash
(503 under concurrency), probe Grok and Qwen (run never finished), showpool Luna p=0.9 reps
1-9 (tnkiet out of quota); notes in `plan/runs/RESCUE_NOTE.md`. Agent lane "recover"
re-downloads the submitted grid's transcripts (reasoning text) from the benchmark server,
no quota; notes in `plan/runs/_recover/RECOVER_NOTE.md`. Analyses:
`paper/AAMAS/analysis/rebuttal_{trend,probes,showpool}.py`.

`plan/scripts/launch_rb.py` (driver log `plan/runs/rb_wave.log`, per-shard logs
`plan/runs/rb_*/shard.log`): 15 shards, one Kaggle user each, plan fixed in the script.
Downloads land in `plan/runs/_dl/<account>/<task>/`.

Update 2026-11-21 11:30: the endpoint now refuses `qwen3-235b-a22b-instruct-2507` and
`grok-4.20-0309-non-reasoning` ("Skipped (Unsupported model version)"), so every new run
covers Haiku, Flash and Luna only; Qwen and Grok evidence for the pool control comes from the
September run. Do not relaunch those two slugs. Submitted-grid transcripts recovered for 308 of
550 games (moves verified), only Haiku writes reasoning: `plan/runs/_recover/`.
Three responses drafted and under audit (kept outside git).

## Next steps

1. Done 2026-11-21: showpool shards converted to `results/exp_showpool/` (3 models x 20 games),
   `verify_wide.py --panel any` clean except the two Grok para1 parse failures already disclosed in
   `results/DATA_CARD.md`; the panel gate flags Qwen and Grok as missing by design (no longer served).
2. Done: audit round on the three responses (numbers traced to `paper/AAMAS/analysis/followups/*.csv`
   and to the submitted text); four wording fixes; lengths LF/CRLF: JJ3F 2387/2414, mTF6 2464/2485,
   6GLf 1958/1979. Responses are final pending the user's read.
3. User posts on OpenReview.

## Decisions ledger

- 2026-11-21: run the medium rebuttal package (showpool self-play, single-call probes);
  about 12k model calls on the Kaggle Benchmarks pool. (user)
- 2026-11-21: write each response to 2,500 characters until the form shows its limit. (user)

## Manual steps for the user

- Post the three responses at https://openreview.net/forum?id= (the submission page),
  one under each review, after the drafts are marked final.
