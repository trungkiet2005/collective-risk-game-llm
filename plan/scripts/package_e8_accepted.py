"""Stage a complete accepted E8 panel without mutating the original results.

Exports native wide CSVs, numeric probe records and portable source provenance.
The raw prompts and full provider notebooks remain in the owner-separated archive.
Run verify_wide.py on the staged results before promoting the archive.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
import launch_e8 as design


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--downloads', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.manifest.read_text())
    if not report['complete'] or report['counts'] != {'games': 350, 'turns': 21000, 'probes': 300}:
        raise ValueError('Cannot package an incomplete E8 panel')
    if args.out.exists(): raise FileExistsError('Use a new staging directory')
    args.out.mkdir(parents=True)
    sources = []; probes = []
    for record in report['selected']:
        raw = Path(record['raw_directory'])
        for name, key in [('games.csv', 'csv_sha256'), ('turns.jsonl', 'turns_sha256')]:
            if hashlib.sha256((raw/name).read_bytes()).hexdigest() != record[key]:
                raise ValueError('Source changed since acceptance')
        source = {k: v for k, v in record.items() if k not in ('run', 'raw_directory', 'errors')}
        source['archive_run'] = str(Path(record['run']).relative_to(args.downloads))
        source['archive_raw'] = str(raw.relative_to(args.downloads))
        sources.append(source)
        if record['arm'] == 'evprobe_p0':
            if hashlib.sha256((raw/'probes.jsonl').read_bytes()).hexdigest() != record['probes_sha256']:
                raise ValueError('Probe source changed since acceptance')
            for line in (raw/'probes.jsonl').read_text().splitlines():
                p = json.loads(line)
                probes.append({k: p[k] for k in ['game_id', 'round', 'question_id', 'model',
                              'player', 'risk_probability', 'rep', 'ground_truth',
                              'parsed_answer', 'correct', 'parse_failed']})
    for arm, spec in design.ARMS.items():
        directories = [r['raw_directory'] for r in report['selected'] if r['arm'] == arm]
        subprocess.run([sys.executable, str(Path(__file__).with_name('to_wide_csv.py')),
                        '--src', *directories, '--out', str(args.out/'results'),
                        '--experiment', spec['results']], check=True)
    metadata = args.out/'results/e8_acceptance'; metadata.mkdir()
    (metadata/'probes.jsonl').write_text(''.join(json.dumps(p, sort_keys=True)+'\n' for p in probes))
    portable = {k: report[k] for k in ['protocol', 'complete', 'expected', 'counts', 'selection', 'missing']}
    portable['sources'] = sources
    portable['excluded'] = [dict(archive_run=str(Path(r['run']).relative_to(args.downloads)),
                                errors=r['errors'], arm=r.get('arm'), model=r['model'])
                            for r in report['excluded']]
    portable['files'] = {str(p.relative_to(args.out)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in sorted((args.out/'results').rglob('*')) if p.is_file()}
    (metadata/'manifest.json').write_text(json.dumps(portable, indent=2)+'\n')
    archive = args.out.with_suffix('.zip')
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as out:
        for path in sorted(args.out.rglob('*')):
            if path.is_file():
                info = zipfile.ZipInfo(str(path.relative_to(args.out)), (2026, 9, 18, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                out.writestr(info, path.read_bytes())
    print('ARCHIVE', archive, archive.stat().st_size, hashlib.sha256(archive.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
