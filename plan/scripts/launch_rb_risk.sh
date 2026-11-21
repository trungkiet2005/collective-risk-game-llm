#!/bin/bash
# Risk dose-response probe (plan/rb-risk-probe-20261121.md). One Kaggle user per model,
# none of the users Kiet's replication or dynamic-partner shards ran on (2026-11-21).
set -u
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO"
export CRG_DL_ROOT="$REPO/plan/runs/_dl" CRG_TASK_SRC="$REPO/kaggle/benchmarks/crg_rb_risk_task.py"
PY=~/miniforge3/envs/ai/bin/python
run() { $PY plan/scripts/launch_shard.py --account $1 --model $2 --langs en --max-out $3 --concurrency $5 --on-game-error skip --wait 7200 --task crg-rb-risk --risks 0.9 --reps 1 --label rb_risk_$4 > plan/runs/rb_risk_$4.driver.log 2>&1; echo "$(date +%T) $4 rc=$?"; }
run acc5 claude-haiku-4-5-20251001 3000 haiku 3 &
run kit567 gemini-3.5-flash-lite 3000 flash 1 &
run vinhdinhthien gpt-5.6-luna 3000 luna 2 &
run trunkdabest claude-haiku-5-5 3000 haiku55 2 &
run chunaiu gpt-oss-120b 6000 oss120 2 &
wait
