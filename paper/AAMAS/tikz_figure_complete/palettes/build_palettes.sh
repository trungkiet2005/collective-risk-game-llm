#!/usr/bin/env bash
# Build every colour variant of Figure 1 from the one source, figure_biolinum.tex,
# into palettes/pdf/fig1_NN_<name>.pdf, then the side-by-side sheet
# palettes/fig1_palettes_overview.pdf, then copy the paper's palette (PAPER_PALETTE)
# to paper/AAMAS/figures/fig_game_designs.pdf, the file main.tex includes as Figure 1.
# figure_biolinum.pdf (original colours) is not touched.
set -euo pipefail
cd "$(dirname "$0")/.."            # figure directory: \includegraphics reads assets/ from here
OUT=palettes/pdf
PAPER_PALETTE=slate_mono           # the variant the paper uses; change here to switch Figure 1
PAPER_FIG=../figures/fig_game_designs
mkdir -p "$OUT"
NAMES=(vivid white_minimal classic_paper nature science okabe_ito tableau slate_mono modern_soft)
i=0
for name in "${NAMES[@]}"; do
  i=$((i + 1))
  job=$(printf 'fig1_%02d_%s' "$i" "$name")
  pdflatex -interaction=nonstopmode -halt-on-error -output-directory="$OUT" -jobname="$job" \
    "\\def\\FigPalette{palettes/$name.tex}\\input{figure_biolinum.tex}" >/dev/null
  rm -f "$OUT/$job.aux" "$OUT/$job.log"
  printf 'Built %s/%s.pdf\n' "$OUT" "$job"
  if [ "$name" = "$PAPER_PALETTE" ]; then paper_job=$job; fi
done
cp "$OUT/$paper_job.pdf" "$PAPER_FIG.pdf"
printf 'Copied %s.pdf to %s.pdf (Figure 1)\n' "$paper_job" "$PAPER_FIG"
if command -v pdftoppm >/dev/null 2>&1; then
  pdftoppm -png -r 200 -singlefile "$PAPER_FIG.pdf" "$PAPER_FIG"
  printf 'Rendered %s.png\n' "$PAPER_FIG"
fi
cd palettes
pdflatex -interaction=nonstopmode -halt-on-error fig1_palettes_overview.tex >/dev/null
rm -f fig1_palettes_overview.aux fig1_palettes_overview.log
printf 'Built palettes/fig1_palettes_overview.pdf\n'
