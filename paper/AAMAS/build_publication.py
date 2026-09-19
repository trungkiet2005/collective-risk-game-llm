"""Rebuild the publication figures and both anonymous PDFs from stored evidence.

No network, model inference, dataset filtering, or statistical re-estimation.
Idempotent source migrations keep the captions and documentation consistent with
the equilibrium check and the expected-payoff analysis.
"""
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def replace_once(path, old, new):
    text = path.read_text(encoding='utf-8')
    # A replacement may contain the old heading; check the finished state first.
    if new in text:
        return
    if old not in text or text.count(old) != 1:
        raise ValueError(f'source has changed; review migration in {path}')
    path.write_text(text.replace(old, new), encoding='utf-8')


def migrate_sources():
    # Figure 3's caption and description were rewritten for the arrow plot (19-09-2026);
    # the two migrations to its former percentage-point axis no longer apply.
    replace_once(HERE / 'main.tex',
        'p = 1 is excluded on purpose: at p = 1 every profile that misses the target is a weak equilibrium.',
        'p = 1 is checked separately: a failed pool is an equilibrium only when no player can reach the target while retaining positive cash.')
    replace_once(HERE / 'main.tex',
        'all symmetric profiles plus 6,000 asymmetric ones at 11 risk levels',
        'all symmetric profiles plus 3,000 sampled profiles at each of ten risks below one; the certainty boundary is checked separately')
    replace_once(ROOT / 'results/DATA_CARD.md',
        'optimal_payoff(p) = max((1-p) * endowment, target / n_players)\nwelfare_gap = optimal_payoff(p) - observed mean_payoff',
        'optimal_payoff(p) = max((1-p) * endowment, endowment - target / n_players)\nexpected_payoff = (endowment - group_total / n_players) * (1 if target_reached else 1-p)\nwelfare_gap = optimal_payoff(p) - expected_payoff')
    replace_once(HERE / 'REPRODUCE.md',
        'python paper/AAMAS/analysis/mixed.py --figure-only\n```',
        'python paper/AAMAS/analysis/mixed.py --figure-only\npython paper/AAMAS/analysis/publication_figures.py\n```')
    replace_once(HERE / 'REPRODUCE.md',
        'Each script writes vector PDF, PNG, exact plotted estimates in CSV, and a greyscale/colour-vision proof.',
        'The statistical scripts write exact plotted estimates in CSV. Run `publication_figures.py` LAST: it reads those CSVs without re-estimating them and writes editable standalone TikZ, vector PDF, PNG, a CSV/source-hash manifest, and a greyscale/colour-vision proof. It requires `pdflatex`, the standalone/PGF/Libertine TeX packages and PyMuPDF. Re-running the older plotting scripts afterwards overwrites the typeset PDFs.')
    replace_once(HERE / 'REPRODUCE.md',
        '## Build and package\n',
        '## Build and package\n\nFor the typeset Figures 3 and 5 and both PDFs, run `python paper/AAMAS/build_publication.py` from the repository root. This uses stored estimates and performs the existing packaging gates; it does not claim that pending experiments are complete. The September 18 Linux figure check used Python 3.11, NumPy 2.3.5, pandas 2.3.3, Matplotlib 3.10.8, PyMuPDF 1.28.2 and TeX Live 2026 with Type 1 Libertine fonts.\n')


def run(command, cwd=ROOT):
    print('+', ' '.join(map(str, command)), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def main():
    migrate_sources()
    run([sys.executable, str(HERE / 'analysis/publication_figures.py')])
    for folder, name in ((HERE, 'main.tex'), (HERE / 'supplement', 'supplement.tex')):
        for _ in range(2):
            run(['pdflatex', '-interaction=nonstopmode', '-halt-on-error', name], folder)
    run([sys.executable, str(HERE / 'make_submission.py')])


if __name__ == '__main__':
    main()
