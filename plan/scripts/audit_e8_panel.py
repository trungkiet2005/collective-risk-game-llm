"""Fail-closed E8 acceptance gate; never select by model outcomes.

Select the fewest complete source runs, then lexicographic remote IDs, as fixed
in e8-control-protocol.md. No incomplete sweep or overlap is silently admitted.
The default exit status is nonzero until all 350 games pass. --allow-incomplete
writes a diagnostic report without using that report as an acceptance signal.
"""
from pathlib import Path
from collections import defaultdict
import argparse
import csv
import itertools
import json
import math
import re
import audit_e8_inventory as inventory
import launch_e8 as design


def jsonlines(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def check_raw(record):
    errors = list(record['errors'])
    if errors: return errors
    root = Path(record['run'])
    defaults, _ = inventory.notebook_defaults(root / '__notebook__.ipynb')
    arm = record['arm']; spec = design.ARMS[arm]
    flags = dict(zip(spec['flags'][::2], spec['flags'][1::2]))
    required = {'CRG_TEMPLATE': flags.get('--template', 'baseline'),
                'CRG_PROBE': flags.get('--probe', ''), 'CRG_MAX_OUT': '3000',
                'CRG_SEAT_MODELS': spec['seats'] or ''}
    if any(str(defaults.get(k, '')) != value for k, value in required.items()):
        errors.append('source_arm_configuration')
    start = int(defaults.get('CRG_REP_START', '-1'))
    reps = int(defaults.get('CRG_REPS', '0'))
    configured = {(float(p), r) for p in str(defaults.get('CRG_RISKS', '')).split(',')
                  for r in range(start, start + reps)}
    if configured != {tuple(c) for c in record['cells']}:
        errors.append('incomplete_configured_sweep')
    raw = Path(record['raw_directory'])
    with (raw / 'games.csv').open() as stream: games = list(csv.DictReader(stream))
    turns = jsonlines(raw / 'turns.jsonl')
    by_game = defaultdict(list)
    for turn in turns: by_game[turn['game_id']].append(turn)
    if set(by_game) != {g['game_id'] for g in games}: errors.append('orphan_turns')
    for game in games:
        records = by_game[game['game_id']]
        keys = [(t['round'], t['player']) for t in records]
        expected = {(r, 'Player_' + str(i)) for r in range(1, 11) for i in range(1, 7)}
        if len(keys) != 60 or set(keys) != expected:
            errors.append('turn_grid'); continue
        if any(type(t['contribution']) is not int or t['contribution'] not in (0, 2, 4) for t in records):
            errors.append('illegal_action')
        total = sum(t['contribution'] for t in records)
        if total != float(game['group_total']): errors.append('group_total_replay')
        reached = str(game['target_reached']).lower() in ('1', 'true')
        if float(game['target']) != 120 or reached != (total >= 120): errors.append('target_replay')
        for turn in records:
            if (float(turn.get('risk_probability', -1)) != float(game['risk_probability'])
                    or int(turn.get('rep', -1)) != int(game['rep'])
                    or turn.get('language') != 'en'): errors.append('turn_identity')
            if arm.startswith('showpool'):
                match = re.search(r'The climate account so far holds (\d+) of the 120 target', turn['prompt'])
                prior = sum(t['contribution'] for t in records if t['round'] < turn['round'])
                if not match or int(match[1]) != prior: errors.append('pool_prompt_replay')
            if arm == 'groupgoal' and 'total final cash of the whole group' not in turn['prompt']:
                errors.append('group_objective_prompt')
            if arm in ('showpool_carry', 'showpool_defect') and turn['player'] != 'Player_1':
                value = 4 if arm == 'showpool_carry' else 0
                if (turn['contribution'] != value or
                        turn.get('seat_model') != 'scripted:always_' + str(value)):
                    errors.append('scripted_seat_replay')
    if arm == 'evprobe_p0':
        probes = jsonlines(raw / 'probes.jsonl')
        expected = {(g['game_id'], r, question) for g in games for r in (1, 5, 10)
                    for question in ('value_defect_ev', 'value_compare')}
        actual = [(p['game_id'], p['round'], p['question_id']) for p in probes]
        if len(actual) != len(expected) or set(actual) != expected: errors.append('probe_grid')
        for p in probes:
            truth = 40 if p['question_id'] == 'value_defect_ev' else 2
            answer = p.get('parsed_answer')
            if (p.get('ground_truth') != truth or p.get('player') != 'Player_1'
                    or p.get('model') != design.TAG[record['model']]
                    or p.get('category') != 'value' or float(p.get('risk_probability', -1)) != 0):
                errors.append('probe_identity_or_ground_truth')
            if type(answer) not in (int, float) or not math.isfinite(answer):
                errors.append('probe_not_finite_numeric')
            elif p.get('correct') != (answer == truth): errors.append('probe_correctness_flag')
    return sorted(set(errors))


def minimum_cover(candidates, expected):
    candidates = sorted(candidates, key=lambda r: (Path(r['run']).name, r['run']))
    for size in range(1, len(candidates) + 1):
        covers = []
        for combo in itertools.combinations(candidates, size):
            cells = [tuple(c) for r in combo for c in r['cells']]
            if len(cells) == len(set(cells)) and set(cells) == expected:
                covers.append(combo)
        if covers:
            return min(covers, key=lambda c: tuple(sorted(Path(r['run']).name for r in c)))
    return ()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('downloads', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--allow-incomplete', action='store_true')
    args = parser.parse_args()
    records = []
    for path in sorted(args.downloads.rglob('*.run.json')):
        record = inventory.inspect_run(path)
        if record is not None:
            record['errors'] = check_raw(record)
            records.append(record)
    selected, missing = [], []
    for arm in design.ARMS:
        expected = {(float(p), r) for p in design.risks_of(arm) for r in range(10)}
        for model in design.MODELS:
            eligible = [r for r in records if not r['errors'] and r.get('arm') == arm and r['model'] == model]
            cover = minimum_cover(eligible, expected)
            if cover: selected.extend(cover)
            else: missing.append(dict(arm=arm, model=model, games=len(expected)))
    counts = {k: sum(r[k] for r in selected) for k in ('games', 'turns', 'probes')}
    complete = not missing and counts == {'games': 350, 'turns': 21000, 'probes': 300}
    report = dict(protocol='plan/e8-control-protocol.md', complete=complete,
                  expected={'games': 350, 'turns': 21000, 'probes': 300}, counts=counts,
                  selection='Fewest non-overlapping complete runs, then lexicographic remote IDs; not outcomes',
                  missing=missing, selected=selected,
                  excluded=[r for r in records if r not in selected])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('selected', 'excluded')}, indent=2))
    print('Selected source runs:', len(selected), 'Excluded:', len(records) - len(selected))
    return 0 if complete or args.allow_incomplete else 1


if __name__ == '__main__':
    raise SystemExit(main())
