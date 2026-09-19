# Reproducing the AAMAS analysis

Run Python commands from the repository root. These commands analyse stored games; they do not call language models.

## Figures 3 and 5

```powershell
python paper/AAMAS/analysis/probes.py
python paper/AAMAS/analysis/supp_probes.py
python paper/AAMAS/analysis/mixed.py --figure-only
python paper/AAMAS/analysis/publication_figures.py
```

Figure 3 uses the 150 question-condition games and their recorded answers. Each row draws an arrow from the risk-0.1 level to the risk-0.9 level; its intervals are those of the levels, with the same draws as the supplement's know-do table. That table also gives the 0.1-to-0.9 shifts, whose intervals resample the answer and the contribution from the same game, and it keeps all three risks and the tie at 0.5. The correct-answer reference is not a self-play best-response prediction.

Figure 5 uses mixed games plus self-play from the base grid and the question condition. Each mixed composition pools ten games at each of three risks; self-play pools twenty per risk. Intervals resample games pooled across risks, not within risk strata. Zero-width intervals reflect constant observations, not proof of deterministic behaviour. In panel a an arrow joins two independent estimates of one model, self-play and one Qwen3-235B seat; in panel b lines connect observed composition means; they are not fitted response functions.

The statistical scripts write exact plotted estimates in CSV. Run `publication_figures.py` LAST: it reads those CSVs without re-estimating them and writes editable standalone TikZ, vector PDF, PNG, a CSV/source-hash manifest, and a greyscale/colour-vision proof. It requires `pdflatex`, the standalone/PGF/Libertine TeX packages and PyMuPDF. Re-running the older plotting scripts afterwards overwrites the typeset PDFs. The shared style checks page width, fonts, text collisions and marker bounds. Both figures are drawn at their final column width, with text at least 8 pt after placement in LaTeX.

The figure runs on 18 September 2026 used Python 3.14.0, NumPy 2.3.5, pandas 2.3.3 and Matplotlib 3.10.8 on Windows, with Linux Libertine G installed. Bootstrap seeds and sample counts are defined in the analysis sources; Figure 5 also includes them in its CSV.

## Selection sensitivity checks

```sh
python paper/AAMAS/analysis/review_checks.py
```

This additional, post-hoc analysis uses the existing composition payoffs. It reports every leave-one-model-out panel at both population sizes and all three risks, plus expected-payoff welfare and single-entrant payoff comparisons. Removing a model is not a test of prompt robustness. It requires the dependencies of `selection.py`, including EGTTools; the tested Linux environment has EGTTools 0.1.14.2. No new model outputs are generated.

## Tests

```powershell
python -m pytest crsd/tests/test_paper_equilibrium.py crsd/tests/test_paper_probes.py -q
python -m pytest crsd/tests --ignore=crsd/tests/test_revision_analyses.py --ignore=crsd/tests/test_revision_loaders.py -o addopts='' -q
```

The two excluded files target an older manuscript's moved `paper/revision` modules. They fail collection in this checkout and are not claimed to pass. The new probe tests check row-order invariance, matched resampling and rejection of unmatched or duplicate games.

## Build and package

For the typeset Figures 3 and 5 and both PDFs, run `python paper/AAMAS/build_publication.py` from the repository root. This uses stored estimates and performs the existing packaging gates; it does not claim that pending experiments are complete. The September 18 Linux figure check used Python 3.11, NumPy 2.3.5, pandas 2.3.3, Matplotlib 3.10.8, PyMuPDF 1.28.2 and TeX Live 2026 with Type 1 Libertine fonts.

For Figure 1, from `paper/AAMAS/tikz_figure_complete`, run `bash palettes/build_palettes.sh`; it builds the `figure_biolinum.tex` layout in each palette and copies the slate-mono one (`palettes/slate_mono.tex`) to `figures/fig_game_designs.pdf`, the file `main.tex` includes. It needs the `biolinum` package and the PNGs in `assets/`, and it holds no measured number. From `paper/AAMAS`, run the same command on `main.tex` twice. Then, from `paper/AAMAS/supplement`, run it on `supplement.tex` twice. Use `bibtex main` followed by two more LaTeX passes if citations change. Direct `pdflatex` also works when `latexmk` cannot find Perl.

Finally run from the repository root:

```powershell
python paper/AAMAS/make_submission.py
```

This creates local upload files and checks the eight-page body, reference placement, anonymity strings, font types and archive size. It does not submit anything and does not certify scientific completeness, venue eligibility or the absence of overlap with another manuscript.
