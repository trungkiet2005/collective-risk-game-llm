"""Analyse only a fully accepted E8 panel, retaining every registered game.

Each confidence interval resamples games, never individual turns/probes. Arm
contrasts use independent game bootstraps: API runs sharing a seed are not paired.
This is a follow-up analysis, not a replacement for the original 3,950-game panel.
Intervals are pointwise percentile bootstrap intervals, not multiplicity-adjusted
simultaneous confidence sets; a degenerate empirical interval is not certainty.
"""
from pathlib import Path
from collections import defaultdict
import argparse
import csv
import hashlib
import json
import numpy as np
import crsd_data as cd

BASELINES = {'groupgoal': 'exp_baseline', 'showpool': 'exp_baseline',
             'showpool_defect': 'exp_bestresponse_defect',
             'showpool_carry': 'exp_bestresponse_carry', 'evprobe_p0': 'exp_baseline'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_lines(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def extract(manifest):
    if not manifest.get('complete') or manifest['counts'] != {'games': 350, 'turns': 21000, 'probes': 300}:
        raise ValueError('E8 acceptance gate is incomplete; do not analyse/promote a partial panel')
    games, probe_games = [], []
    for record in manifest['selected']:
        root = Path(record['raw_directory'])
        for filename, key in [('games.csv', 'csv_sha256'), ('turns.jsonl', 'turns_sha256')]:
            if sha(root / filename) != record[key]: raise ValueError('raw file changed after acceptance')
        turns = defaultdict(list)
        for turn in read_lines(root / 'turns.jsonl'): turns[turn['game_id']].append(turn)
        with (root / 'games.csv').open() as stream: raw_games = list(csv.DictReader(stream))
        for game in raw_games:
            ts = turns[game['game_id']]
            seats = [f'Player_{i}' for i in range(1, 7)]
            if record['arm'] in ('showpool_defect', 'showpool_carry'): seats = ['Player_1']
            own = sum(t['contribution'] for t in ts if t['player'] in seats) / len(seats)
            p = float(game['risk_probability']); reached = int(float(game['group_total']) >= 120)
            games.append(dict(arm=record['arm'], model=game['model'], p=p, rep=int(game['rep']),
                              own=own, expected_pay=(40-own)*(1 if reached else 1-p),
                              reached=reached, group_total=float(game['group_total']),
                              source_run=Path(record['run']).name, game_id=game['game_id']))
        if record['arm'] == 'evprobe_p0':
            if sha(root/'probes.jsonl') != record['probes_sha256']: raise ValueError('probe file changed')
            by_question = defaultdict(list)
            for probe in read_lines(root/'probes.jsonl'):
                by_question[(probe['game_id'], probe['question_id'])].append(probe)
            for (gid, question), probes in sorted(by_question.items()):
                if len(probes) != 3: raise ValueError('bad probe cluster')
                probe_games.append(dict(model=probes[0]['model'], game_id=gid,
                                        question=question, correct=sum(p['correct'] for p in probes)/3))
    if len(games) != 350 or len(probe_games) != 100: raise ValueError('incomplete extracted panel')
    return games, probe_games


def estimate(values, key):
    x = np.asarray(values, dtype=float)
    seed = int.from_bytes(hashlib.sha256(str(key).encode()).digest()[:8], 'little')
    rng = np.random.default_rng(seed)
    boot = x[rng.integers(0, len(x), (5000, len(x)))].mean(axis=1)
    low, high = np.quantile(boot, [.025, .975])
    return float(x.mean()), float(low), float(high), boot


def summarise(games, probes):
    _, base_units, _ = cd.build(sorted(set(BASELINES.values())))
    groups = defaultdict(list)
    for game in games: groups[(game['arm'], game['model'], game['p'])].append(game)
    rows = []
    for (arm, model, p), group in sorted(groups.items()):
        if len(group) != 10 or {g['rep'] for g in group} != set(range(10)):
            raise ValueError('bad model/arm/risk game grid')
        x = [g['own'] for g in group]
        base = base_units[(base_units.exp == BASELINES[arm]) &
                          (base_units.model == cd.SLUG[model]) & (base_units.p == p)]
        if len(base) != 10: raise ValueError('missing baseline comparison')
        mean, lo, hi, boot = estimate(x, (arm, model, p, 'followup'))
        bm, _, _, bb = estimate(base.own, (arm, model, p, 'baseline'))
        dl, dh = np.quantile(boot-bb, [.025, .975])
        rows.append(dict(arm=arm, model=model, p=p, n=10, own_mean=mean,
                         own_lo=lo, own_hi=hi, baseline_mean=bm, delta=mean-bm,
                         delta_lo=float(dl), delta_hi=float(dh),
                         expected_pay_mean=float(np.mean([g['expected_pay'] for g in group])),
                         target_reached=sum(g['reached'] for g in group)))
    groups = defaultdict(list)
    for probe in probes: groups[(probe['model'], probe['question'])].append(probe['correct'])
    prows = []
    for key, values in sorted(groups.items()):
        if len(values) != 10: raise ValueError('bad probe game count')
        mean, lo, hi, _ = estimate(values, key)
        prows.append(dict(model=key[0], question=key[1], games=10, answers=30,
                          accuracy=mean, lo=lo, hi=hi))
    return rows, prows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    games, probes = extract(manifest)
    rows, prows = summarise(games, probes)
    args.output.mkdir(parents=True, exist_ok=True)
    for name, values in [('games', games), ('probe_games', probes),
                         ('contrasts', rows), ('probes', prows)]:
        write_csv(args.output/f'e8_{name}.csv', values)
    print('350 games; 35 arm-model-risk cells; 300 probes in 50 independent games')
    for row in rows:
        print(row['arm'], cd.SLUG[row['model']], row['p'],
              'own', round(row['own_mean'], 3), 'baseline', round(row['baseline_mean'], 3),
              'deltaCI', round(row['delta_lo'], 3), round(row['delta_hi'], 3))
    for row in prows: print(row)


if __name__ == '__main__':
    main()
