"""Read-only E8 run inventory; no outcome-based selection or inference calls."""
from pathlib import Path
import argparse
import ast
import csv
import hashlib
import json
import launch_e8 as protocol


def notebook_defaults(path):
    notebook = json.loads(path.read_text(encoding='utf-8'))
    source = '\n'.join(''.join(c.get('source', [])) for c in notebook['cells']
                       if c['cell_type'] == 'code')
    defaults = {}
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and len(node.args) >= 2:
            name = node.args[0]
            if isinstance(name, ast.Constant) and isinstance(name.value, str):
                if name.value.startswith('CRG_'):
                    try: defaults[name.value] = ast.literal_eval(node.args[1])
                    except (ValueError, TypeError): pass
    return defaults, hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_run(path):
    metadata = json.loads(path.read_text(encoding='utf-8'))
    slug = metadata.get('modelVersion', {}).get('slug', '')
    model = slug.split('/')[-1].replace('@', '-')
    if model not in protocol.MODELS:
        return None
    result = next((r.get('dictResult', {}) for r in metadata.get('results', [])
                   if r.get('type') == 'AGGREGATED'), {})
    root = path.parent
    invalid = dict(run=str(root), model=model, arm=None, cells=[], games=0, turns=0, probes=0)
    if not (root / '__notebook__.ipynb').is_file():
        return dict(invalid, errors=['missing_notebook_source'])
    defaults, source_hash = notebook_defaults(root / '__notebook__.ipynb')
    datafiles = list(root.glob('results/frontier/*/*/games.csv'))
    if len(datafiles) != 1:
        return dict(invalid, errors=['game_file_count'])
    file = datafiles[0]
    with file.open(encoding='utf-8') as stream:
        games = list(csv.DictReader(stream))
    cells = [(float(g['risk_probability']), int(g['rep'])) for g in games]
    experiment = result.get('experiment', file.parent.name)
    arm = next((a for a, s in protocol.ARMS.items()
                if experiment.startswith(s['server']) and
                (s['seats'] or '_seats-' not in experiment)), None)
    turns_file = file.with_name('turns.jsonl')
    if not turns_file.is_file(): return dict(invalid, errors=['missing_turn_records'])
    turns = [json.loads(s) for s in turns_file.read_text().splitlines() if s.strip()]
    probe_file = file.with_name('probes.jsonl')
    probes = [json.loads(s) for s in probe_file.read_text().splitlines() if s.strip()] if probe_file.exists() else []
    errors = []
    if not metadata.get('state', '').endswith('_COMPLETED'): errors.append('run_not_completed')
    assertions = metadata.get('assertions', [])
    if len(assertions) < 2 or any(not a.get('status', '').endswith('_PASSED') for a in assertions):
        errors.append('server_assertion_failed_or_missing')
    if result.get('failed_games') != 0: errors.append('failed_games')
    if result.get('parse_fail_rate') != 0: errors.append('reported_parse_failures')
    if len(cells) != len(set(cells)): errors.append('duplicate_cells')
    if len(turns) != 60 * len(games): errors.append('turn_count')
    if any(t.get('parse_failed') is not False for t in turns): errors.append('raw_turn_parse_failures')
    if any(p.get('parse_failed') is not False for p in probes): errors.append('raw_probe_parse_failures')
    if result.get('n_games') != len(games) or result.get('n_decisions') != len(turns):
        errors.append('summary_raw_count_mismatch')
    if arm is None: errors.append('not_registered_arm')
    else:
        allowed = {(float(p), r) for p in protocol.risks_of(arm) for r in range(10)}
        if not set(cells) <= allowed: errors.append('outside_registered_cells')
        if any(not (protocol._suffix_of(g['game_id']) or '').startswith(protocol.ARMS[arm]['suffix']) for g in games):
            errors.append('wrong_game_suffix')
    if any(g.get('model') != protocol.TAG[model] or g.get('language') != 'en' for g in games):
        errors.append('wrong_raw_model_or_language')
    if slug.replace('@', '-').replace('/', '-') != protocol.TAG[model]:
        errors.append('wrong_provider')
    expected_model = str(defaults.get('CRG_EXPECT_MODEL', ''))
    if model not in expected_model and slug not in expected_model:
        errors.append('source_selected_model_mismatch')
    return dict(run=str(root), model=model, arm=arm, experiment=experiment,
                source_defaults={k: v for k, v in defaults.items() if k in {
                    'CRG_EXPECT_MODEL', 'CRG_REPS', 'CRG_REP_START', 'CRG_RISKS',
                    'CRG_TEMPLATE', 'CRG_MAX_OUT', 'CRG_PROBE', 'CRG_SEAT_MODELS'}},
                cells=sorted(cells), games=len(games), turns=len(turns), probes=len(probes),
                source_sha256=source_hash, csv_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
                turns_sha256=hashlib.sha256(turns_file.read_bytes()).hexdigest(),
                probes_sha256=hashlib.sha256(probe_file.read_bytes()).hexdigest() if probe_file.exists() else None,
                errors=errors, raw_directory=str(file.parent),
                start=metadata.get('startTime'), end=metadata.get('endTime'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('downloads', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    records = []
    for path in sorted(args.downloads.rglob('*.run.json')):
        record = inspect_run(path)
        if record is not None: records.append(record)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(records, indent=2) + '\n')
    for record in records:
        rel = Path(record['run']).relative_to(args.downloads)
        print(str(rel), record.get('arm'), record.get('games'),
              sorted({c[0] for c in record.get('cells', [])}),
              record.get('probes'), ';'.join(record['errors']) or 'eligible-stage1')
    print('original-panel runs:', len(records))


if __name__ == '__main__':
    main()
