#!/bin/bash
# Generalisation wave day 2 (plan in plan/scripts/launch_gen.py docstring): base self-play at p = 0.1 / 0.9,
# 10 games each, one Kaggle user per shard. Grok 4.7 (p = 0 still running, 503s) and Gemini 3.8 Flash
# (server validation model: push-only/download-only route) are left out.
set -u
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO"
export CRG_DL_ROOT="$REPO/plan/runs/_dl"
PY=~/miniforge3/envs/ai/bin/python
run() { $PY plan/scripts/launch_shard.py --account $1 --model $2 --langs en --max-out $3 --concurrency 2 --on-game-error skip --wait 7200 --task crg-gen-selfplay-p$5 --risks $4 --reps 10 --label gen_self_$6_p$5_d2 > plan/runs/gen_self_$6_p$5_d2.driver.log 2>&1; echo "$(date +%T) $6 p$4 rc=$?"; }
run foundnotkiet claude-haiku-5-5 3000 0.1 01 haiku55 &
run trungkiet claude-haiku-5-5 3000 0.9 09 haiku55 &
run tonngohan gpt-6-luna 6000 0.1 01 luna6 &
run kit567 gpt-6-luna 6000 0.9 09 luna6 &
run hunhtrungkit gpt-oss-120b 6000 0.9 09 oss120 &
wait
