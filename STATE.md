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
| dynamic partners: 5 x `switch_to_0` / `switch_to_4` (pay 2 in rounds 1-5, then 0 / 4), Haiku, Flash, Luna, p=0.1, 0.9 | R1 | done 2026-11-21 from the Windows copy: 6 shards clean (`crg-rb-switch`, `plan/scripts/launch_rb_switch.py`), `results/exp_bestresponse_switch{0,4}` (3 models x 20 games, verify_wide balanced; panel gate flags Qwen/Grok as missing on purpose), `followups/rb_switch.csv` from `paper/AAMAS/analysis/rebuttal_switch.py`. acc2, acc3, acc4 had no quota left. On Windows set `CRSD_CRED_ROOT=D:/AI_PhD/GameTheory/kaggle_for_research` |
| probe wave 2, independent replication at n = 20 per cell (cf + explain, no recognition), Haiku, Flash, Luna | R1, R2 | done 2026-11-21 from Windows: 3 shards x 420 calls clean, every reply carries the CONTRIBUTION line (`crg-rb-probe2`, `plan/scripts/launch_rb2.py`, accounts foundnotkiet / trungkiet / kakagotto), `followups/rb_{counterfactual,explain}_w2.csv` via `rebuttal_probes.py --task crg-rb-probe2 --tag _w2`. Haiku pays in 7 of 40 settled cf calls (wave 1: 0 of 20); Luna pays 0 once against fair partners at p = 0.1 |
| output cap of the exp_baseline grid | R1 | Flash-Lite, Luna, Grok grid ran at 6000 (code default), not 3000 as Supp. S3.2 says; README_code.md fixed, S3.2 to fix at camera-ready |
| responses | all | drafts kept outside git (`.git/info/exclude`: `docs/rebuttal_aamas2027/`); a second set drafted on Windows in `rebuttal/` (also untracked), to merge |

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

Two response sets exist (outside git): FINAL_TO_POST.md (each under 2,500 characters, core
SkyPart moves) and FINAL_TO_POST_FULL.md (each under 5,000, full SkyPart layout with tables,
interpretation and scope sentences, References). Post the set that fits the form's real limit.

Risk dose-response probe (Minh, started 2026-11-21 18:26, pre-registered in
`plan/rb-risk-probe-20261121.md`): `plan/scripts/launch_rb_risk.sh` from the main checkout, log
`plan/runs/rb_risk_wave.log`, task `crg-rb-risk`, 440 calls per model on acc5 (Haiku 4.5), kit567
(Flash-Lite), vinhdinhthien (Luna), trunkdabest (Haiku 5.5), chunaiu (gpt-oss-120b). Analyse with
`python paper/AAMAS/analysis/rebuttal_risk.py plan/runs/_dl`. Reviewer simulation of the final
responses: `SIM_ALL_20261121.md` in the private rebuttal repo.

Update 2026-11-21 20:15: risk sweep done for Luna, Haiku 5.5, gpt-oss (all flat by the pre-registered
gate, largest step 0.70); Haiku 4.5 and Flash-Lite shards stuck on 503 (acc5, kit567), not used.
Final responses in the private repo got a slop/accuracy pass and the sweep line (JJ3F 2488, mTF6 2496,
6GLf 2432 characters with CRLF).

## Next steps

1. Final responses live in the private repo `technoob05/crg-aamas2027-rebuttal` (`FINAL_TO_POST.md`,
   commit 4f3b0ac, Kiet merged PR 1 on 2026-11-21). `docs/rebuttal_aamas2027/` is now a clone of it
   (git pull there, never edit the old copies). Lengths with CRLF: JJ3F 2489, mTF6 2495, 6GLf 2432.
2. Audit 2026-11-21 18:00: target-240, generalisation and pool numbers match `followups/*.csv`; the
   6,000 cap correction matches the code (`_REASONING_HINTS` in `crg_task_server.py`, only Haiku forced to
   3,000 in `run_dense_grid.py`). NOT traceable in either repo yet (Kiet's runs): dynamic-partner arm
   (`rb_switch.csv`, `results/exp_bestresponse_switch0/4`), the 20-call replication of the same-history probe
   (173/180, 1 of 90, 178 of 180, P < 0.001), the 40-call explained decisions, the full-grid Haiku reasons
   (`rb_grid_reasons.csv`, 60/60, 49/60), and the per-folder cap list in `README_code.md`. Kiet to push them
   to this repo before posting.
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
