#!/bin/bash
# Goal-prompt risk sweep (plan/rb-goalrisk-probe-20261122.md). Concurrency 1: concurrency 3 gave 503s.
set -u
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO"
export CRG_DL_ROOT="$REPO/plan/runs/_dl" CRG_TASK_SRC="$REPO/kaggle/benchmarks/crg_rb_goalrisk_task.py"
PY=~/miniforge3/envs/ai/bin/python
run() { $PY plan/scripts/launch_shard.py --account $1 --model $2 --langs en --max-out $3 --concurrency 1 --on-game-error skip --wait 7200 --task crg-rb-goalrisk --risks 0.9 --reps 1 --label rb_goal_$4 > plan/runs/rb_goal_$4.driver.log 2>&1; echo "$(date +%T) $4 rc=$?"; }
run acc5 claude-haiku-4-5-20251001 3000 haiku &
run hunhtrungkit gemini-3.5-flash-lite 3000 flash &
run vinhdinhthien gpt-5.6-luna 3000 luna &
run trunkdabest claude-haiku-5-5 3000 haiku55 &
run chunaiu gpt-oss-120b 6000 oss120 &
wait
