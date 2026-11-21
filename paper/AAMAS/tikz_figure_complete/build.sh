#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if ! command -v pdflatex >/dev/null 2>&1; then
  printf '%s\n' 'Missing pdfLaTeX. Install a TeX distribution with standalone, TikZ, lmodern and tgheros.' >&2
  exit 1
fi
pdflatex -interaction=nonstopmode -halt-on-error figure.tex
printf '\nBuilt: %s/figure.pdf\n' "$PWD"
