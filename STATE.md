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
Three responses final 2026-11-21 14:50 after audit (mechanical gates clean, every number checked against followups/*.csv, two P-value ranges corrected); kept outside git in docs/rebuttal_aamas2027/FINAL_TO_POST.md.

Generalisation wave (started 2026-11-21 15:14, `plan/scripts/launch_gen.py`, log
`plan/runs/gen_wave.log`): six served models (Claude Haiku 5.5, GPT-6 Luna, Grok 4.7,
Gemini 3.8 Flash, Gemma 4 31B, gpt-oss-120b), day 1 = probe + base self-play p = 0 on
acc1, acc2, acc3, acc4, acc11, chisboiz; day 2 (after 2026-11-22 16:00) = self-play
p = 0.1 and 0.9, fill DAY2 in the script from probe_accounts.py. Data stays in plan/runs.
Traps met on day 1 (2026-11-21): (a) the push-validation guard cut Gemma to 3 of 185 items
because the server runs `gemma-4-31b-it` as `google/gemma-4-31b`; guard fixed and tested
(commit "Fix push-validation guard..."), Gemma redone via `plan/runs/gemma_redo.sh`;
(b) the server's validation model is now `gemini-3.8-flash`, so a Flash 3.8 shard validates
over its whole sweep: use --push-only then --download-only for that model, never `run`;
(c) acc1 ran out of quota after 2 of 10 Haiku 5.5 p = 0 games: fill reps 2-9 on day 2.
Day-1 follow-up chains: `plan/runs/gen_follow.sh` (log gen_follow.log). Day 2 is scheduled
in-session for 2026-11-22 16:23; if the session is gone, run it by hand from this note.

Update 2026-11-21 16:30: target probe (target 240 makes paying never worth it) run on five models:
Haiku 4.5 and Flash pay the split from the target (4) in 78 of 80 calls; Luna and gpt-oss in part;
Haiku 5.5 refuses (0 in 39 of 40). Results `paper/AAMAS/analysis/followups/rb_target.csv`. The mTF6
response was rewritten with it (v3, predicted move 4 -> 5 by a simulated reviewer before the target
probe); JJ3F response now adds the two newer models. Private drafts updated in
technoob05/crg-aamas2027-rebuttal.

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

- 2026-11-21: share the rebuttal drafts with Trung Kiet through a private repo (technoob05/crg-aamas2027-rebuttal), never the public code repo. (user)

- 2026-11-21: use the remaining benchmark quota on six newer/open models to answer the generalisation question. (user)

## Manual steps for the user

- Post the three responses at https://openreview.net/forum?id= (the submission page),
  one under each review, after the drafts are marked final.
