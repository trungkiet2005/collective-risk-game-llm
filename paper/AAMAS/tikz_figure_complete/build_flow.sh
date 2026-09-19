#!/usr/bin/env bash
# Build the flow-layout variant of Figure 1 (figure_flow.tex) and copy it to
# paper/AAMAS/figures/fig_game_designs_flow.pdf, where main.tex would include it.
# fig_game_designs.pdf (the card layout, built by palettes/build_palettes.sh) is not touched.
set -euo pipefail
cd "$(dirname "$0")"               # \includegraphics reads assets/ from here
pdflatex -interaction=nonstopmode -halt-on-error figure_flow.tex >/dev/null
rm -f figure_flow.aux figure_flow.log
FIG=../figures/fig_game_designs_flow
cp figure_flow.pdf "$FIG.pdf"
printf 'Built figure_flow.pdf and copied it to %s.pdf\n' "$FIG"
if command -v pdftoppm >/dev/null 2>&1; then
  pdftoppm -png -r 200 -singlefile "$FIG.pdf" "$FIG"
  printf 'Rendered %s.png\n' "$FIG"
fi
